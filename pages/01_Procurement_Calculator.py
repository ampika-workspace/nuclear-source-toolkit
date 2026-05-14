import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta
from utils.iaea_api import fetch_iaea_data, COMMON_ISOTOPES
from utils.decay_math import (
    required_order_activity, decay_factor,
    convert_activity, convert_to_ci, UNITS,
)

st.set_page_config(page_title="Procurement Calculator", page_icon="📦", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    input_unit   = st.selectbox("Activity input unit",   UNITS, index=0)
    display_unit = st.selectbox("Activity display unit", UNITS, index=0)
    st.divider()
    with st.expander("📋 Supported isotopes"):
        st.write(", ".join(COMMON_ISOTOPES))
        st.caption("Any other isotope can be typed manually — data will be fetched live from IAEA.")
    st.info("🛰 Data: IAEA LiveChart API\n📦 Fallback: local reference table")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📦 Source Procurement Calculator")
st.markdown(
    "Calculate the activity to **order today** to receive your target activity "
    "at delivery, accounting for radioactive decay during transit."
)

# ── Date Configuration ────────────────────────────────────────────────────────
c1, c2, c3 = st.columns([2, 2, 1])
with c1:
    order_date    = st.date_input("Order date", value=date.today())
with c2:
    delivery_date = st.date_input("Delivery date", value=date.today() + timedelta(days=300))
with c3:
    if delivery_date <= order_date:
        st.error("Delivery must be after order date.")
        st.stop()
    transit_days = (delivery_date - order_date).days
    st.metric("Transit time", f"{transit_days} days", f"{transit_days / 365.25:.2f} yr")

st.divider()

# ── Source Inventory ──────────────────────────────────────────────────────────
st.subheader("Source Inventory")
st.caption(
    f"Enter the activity needed **at the delivery date** in **{input_unit}**. "
    "Add or remove rows using the table controls below."
)

if "proc_sources" not in st.session_state:
    st.session_state.proc_sources = pd.DataFrame([
        {"Name": "Item 1", "Isotope": "Am-241", "Activity": 5.5,   "Type / Notes": "Am-Be"},
        {"Name": "Item 2", "Isotope": "Am-241", "Activity": 1.2,   "Type / Notes": "Am-Be"},
        {"Name": "Item 3", "Isotope": "Cf-252", "Activity": 0.063, "Type / Notes": "Neutron"},
        {"Name": "Item 4", "Isotope": "Cs-137", "Activity": 0.12,  "Type / Notes": "Gamma Calibration"},
    ])

edited_df = st.data_editor(
    st.session_state.proc_sources,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Name":         st.column_config.TextColumn("Name", width="small"),
        "Isotope":      st.column_config.TextColumn("Isotope (e.g. Am-241, Cf-252)", width="medium"),
        "Activity":     st.column_config.NumberColumn(
                            f"Activity at delivery ({input_unit})",
                            min_value=0.0, format="%.6f", width="medium",
                        ),
        "Type / Notes": st.column_config.TextColumn("Type / Notes", width="medium"),
    },
    key="proc_editor",
)
st.session_state.proc_sources = edited_df

st.divider()

# ── Calculate ─────────────────────────────────────────────────────────────────
if st.button("🔬 Calculate procurement activities", type="primary"):

    @st.cache_data(show_spinner=False)
    def cached_iaea(iso: str):
        return fetch_iaea_data(iso)

    results, errors = [], []

    with st.spinner("Fetching IAEA nuclear data..."):
        for _, row in edited_df.iterrows():
            isotope = str(row["Isotope"]).strip()
            if not isotope:
                continue

            activity_ci = convert_to_ci(float(row["Activity"]), input_unit)
            iaea        = cached_iaea(isotope)

            if iaea is None:
                errors.append(f"Could not fetch data for '{isotope}'. Check the isotope name.")
                continue

            t_half_days = iaea["half_life_sec"] / (3600 * 24)
            df_val      = decay_factor(transit_days, t_half_days)
            order_ci    = required_order_activity(activity_ci, transit_days, t_half_days)

            results.append({
                "name":        row["Name"],
                "isotope":     isotope,
                "type":        str(row.get("Type / Notes", "")),
                "half_life":   iaea["half_life_hum"],
                "data_source": iaea["source"],
                "delivery_ci": activity_ci,
                "order_ci":    order_ci,
                "loss_pct":    (1 - df_val) * 100,
            })

    for e in errors:
        st.error(e)

    if not results:
        st.warning("No results. Check that all isotope names are valid.")
        st.stop()

    if errors:
        st.info(
            f"Showing results for **{len(results)}** of **{len(results) + len(errors)}** "
            "source(s). Fix the errors above to include the remaining items."
        )

    # ── Results table ─────────────────────────────────────────────────────────
    st.subheader("Results")

    df_results = pd.DataFrame([{
        "Item":                                r["name"],
        "Isotope":                             r["isotope"],
        "Type":                                r["type"],
        "Half-life":                           r["half_life"],
        f"Need at delivery ({display_unit})":  round(convert_activity(r["delivery_ci"], display_unit), 6),
        f"Must ORDER ({display_unit})":        round(convert_activity(r["order_ci"],    display_unit), 6),
        "Decay loss (%)":                      round(r["loss_pct"], 3),
        "Data source":                         r["data_source"],
    } for r in results])

    st.dataframe(df_results, use_container_width=True, hide_index=True)

    # ── Bar chart ─────────────────────────────────────────────────────────────
    fig = go.Figure()
    labels = [r["name"] for r in results]

    fig.add_trace(go.Bar(
        name=f"Need at delivery ({display_unit})",
        x=labels,
        y=[convert_activity(r["delivery_ci"], display_unit) for r in results],
        marker_color="steelblue",
        text=[f"{convert_activity(r['delivery_ci'], display_unit):.4f}" for r in results],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name=f"Must ORDER ({display_unit})",
        x=labels,
        y=[convert_activity(r["order_ci"], display_unit) for r in results],
        marker_color="tomato",
        text=[f"{convert_activity(r['order_ci'], display_unit):.4f}" for r in results],
        textposition="outside",
    ))

    fig.update_layout(
        title=f"Order vs Delivery Activity<br>"
              f"<sup>Order: {order_date}  →  Delivery: {delivery_date} ({transit_days} days)</sup>",
        yaxis_title=f"Activity ({display_unit})",
        barmode="group",
        template="plotly_white",
        legend=dict(orientation="h", y=-0.25),
        margin=dict(t=80, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Procurement memo ──────────────────────────────────────────────────────
    st.subheader("📋 Procurement Memo")

    memo_lines = [
        "=" * 80,
        "  SOURCE PROCUREMENT MEMO",
        f"  Generated   : {date.today()}",
        f"  Order date  : {order_date}",
        f"  Delivery    : {delivery_date}",
        f"  Transit     : {transit_days} days ({transit_days / 365.25:.2f} yr)",
        "=" * 80,
        f"  {'Item':<12} {'Isotope':<10} {'Half-life':<12}"
        f" {'Need at delivery':>20} {'Must ORDER':>20} {'Loss%':>8}",
        f"  {'':12} {'':10} {'':12}"
        f" {'(' + display_unit + ')':>20} {'(' + display_unit + ')':>20} {'':>8}",
        "-" * 80,
    ]
    for r in results:
        memo_lines.append(
            f"  {r['name']:<12} {r['isotope']:<10} {r['half_life']:<12}"
            f" {convert_activity(r['delivery_ci'], display_unit):>20.4f}"
            f" {convert_activity(r['order_ci'],    display_unit):>20.4f}"
            f" {r['loss_pct']:>7.3f}%"
        )
    memo_lines += ["=" * 80, f"  Unit: {display_unit}"]
    memo_text = "\n".join(memo_lines)

    st.code(memo_text)

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("⬇️ Download results (CSV)", df_results.to_csv(index=False),
                           f"procurement_{order_date}.csv", "text/csv")
    with col2:
        st.download_button("⬇️ Download memo (TXT)", memo_text,
                           f"procurement_memo_{order_date}.txt", "text/plain")
                              