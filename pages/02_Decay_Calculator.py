import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import date, timedelta
from utils.iaea_api import fetch_iaea_data, COMMON_ISOTOPES
from utils.decay_math import activity_at_time, convert_activity, convert_to_ci, UNITS

st.set_page_config(page_title="Decay Calculator", page_icon="📉", layout="wide")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")
    input_unit   = st.selectbox("Activity input unit",   UNITS, index=0)
    display_unit = st.selectbox("Activity display unit", UNITS, index=0)
    st.divider()
    with st.expander("📋 Supported isotopes"):
        st.write(", ".join(COMMON_ISOTOPES))
        st.caption("Any other isotope can be typed manually.")
    st.info("🛰 Data: IAEA LiveChart API\n📦 Fallback: local reference table")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📉 Activity Decay Calculator")
st.markdown("Forecast source activity over time from a known reference measurement.")

# ── Inputs ────────────────────────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Source")
    isotope_sel = st.selectbox("Select isotope", [""] + COMMON_ISOTOPES + ["Other (type below)"])
    if isotope_sel == "Other (type below)":
        isotope = st.text_input("Isotope name", placeholder="e.g. Pu-238")
    elif isotope_sel == "":
        isotope = ""
    else:
        isotope = isotope_sel

    ref_activity = st.number_input(f"Known activity ({input_unit})",
                                   min_value=0.0, value=1.0, format="%.6f")
    ref_date     = st.date_input("Reference (calibration) date", value=date.today())

    st.subheader("Forecast settings")
    forecast_years = st.slider("Forecast period (years)", 1, 50, 20)
    milestones     = st.multiselect(
        "Milestone years",
        options=[0.5, 1, 2, 3, 5, 10, 15, 20, 25, 30, 50],
        default=[1, 3, 5, 10, 20],
    )

    st.subheader("Point query")
    query_date = st.date_input("Calculate activity at this date",
                               value=date.today() + timedelta(days=365))

    calc_btn = st.button("🔬 Calculate", type="primary", disabled=(isotope == ""))

# ── Results ───────────────────────────────────────────────────────────────────
with right:
    if not isotope:
        st.info("👈 Select an isotope and fill in the source details, then click **Calculate**.")

    elif calc_btn:

        @st.cache_data(show_spinner=False)
        def cached_iaea(iso: str):
            return fetch_iaea_data(iso)

        with st.spinner("Fetching IAEA data..."):
            iaea = cached_iaea(isotope)

        if iaea is None:
            st.error(f"Could not find data for '{isotope}'. Check the name format (e.g. 'Am-241').")
            st.stop()

        ref_ci      = convert_to_ci(ref_activity, input_unit)
        t_half_days = iaea["half_life_sec"] / (3600 * 24)

        st.info(
            f"**{isotope}**  |  Half-life: **{iaea['half_life_hum']}**  |  "
            f"Decay mode: **{iaea['decay_mode']}**  |  Data: *{iaea['source']}*"
        )

        # Key metrics
        days_today    = (date.today() - ref_date).days
        days_query    = (query_date  - ref_date).days
        act_today_ci  = activity_at_time(ref_ci, days_today, t_half_days)
        act_query_ci  = activity_at_time(ref_ci, days_query, t_half_days)

        m1, m2, m3 = st.columns(3)
        m1.metric(f"At reference ({display_unit})",
                  f"{convert_activity(ref_ci, display_unit):.4f}")
        m2.metric(f"Today ({display_unit})",
                  f"{convert_activity(act_today_ci, display_unit):.4f}",
                  f"{(act_today_ci / ref_ci - 1) * 100:.3f}%")
        m3.metric(f"At {query_date} ({display_unit})",
                  f"{convert_activity(act_query_ci, display_unit):.4f}",
                  f"{(act_query_ci / ref_ci - 1) * 100:.3f}%")

        # Decay curve
        days_arr  = np.linspace(0, forecast_years * 365.25, 1000)
        curve_ci  = ref_ci * (0.5) ** (days_arr / t_half_days)
        dates_arr = [ref_date + timedelta(days=float(d)) for d in days_arr]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates_arr,
            y=[convert_activity(v, display_unit) for v in curve_ci],
            mode="lines",
            name=f"{isotope} ({display_unit})",
            line=dict(color="steelblue", width=2),
        ))

        # Today line
        if ref_date <= date.today() <= ref_date + timedelta(days=forecast_years * 365.25):
            fig.add_vline(x=str(date.today()), line_dash="dash", line_color="orange",
                          annotation_text="Today", annotation_position="top right")

        # Query date marker
        fig.add_scatter(
            x=[query_date],
            y=[convert_activity(act_query_ci, display_unit)],
            mode="markers+text",
            marker=dict(size=10, color="green", symbol="diamond"),
            text=[f"{convert_activity(act_query_ci, display_unit):.4f}"],
            textposition="top right",
            name=f"Query: {query_date}",
        )

        # Milestone markers
        for y in milestones:
            ms_date = ref_date + timedelta(days=y * 365.25)
            ms_ci   = activity_at_time(ref_ci, y * 365.25, t_half_days)
            if ms_date <= ref_date + timedelta(days=forecast_years * 365.25):
                fig.add_scatter(
                    x=[ms_date],
                    y=[convert_activity(ms_ci, display_unit)],
                    mode="markers+text",
                    marker=dict(size=8, color="tomato"),
                    text=[f"{y}y"],
                    textposition="top center",
                    showlegend=False,
                )

        fig.update_layout(
            title=f"{isotope} Decay Forecast from {ref_date}  (t½ = {iaea['half_life_hum']})",
            xaxis_title="Date",
            yaxis_title=f"Activity ({display_unit})",
            template="plotly_white",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Milestone table
        st.subheader("Milestone Table")
        ms_rows = []
        for y in sorted(set(milestones + [forecast_years])):
            ms_ci_val = activity_at_time(ref_ci, y * 365.25, t_half_days)
            ms_rows.append({
                "Years from reference":       y,
                "Date":                       (ref_date + timedelta(days=y * 365.25)).strftime("%Y-%m-%d"),
                f"Activity ({display_unit})": round(convert_activity(ms_ci_val, display_unit), 6),
                "Remaining (%)":              round(ms_ci_val / ref_ci * 100, 3),
                "Loss (%)":                   round((1 - ms_ci_val / ref_ci) * 100, 3),
            })

        df_ms = pd.DataFrame(ms_rows)
        st.dataframe(df_ms, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download milestone table (CSV)",
            df_ms.to_csv(index=False),
            f"{isotope}_decay_forecast.csv",
            "text/csv",
        )
