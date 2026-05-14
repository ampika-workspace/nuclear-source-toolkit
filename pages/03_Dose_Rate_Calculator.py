import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.decay_math import convert_to_ci, UNITS
from utils.iaea_api import fetch_iaea_data, fetch_nuclide_properties, fetch_decay_radiations
from utils.constants import (
    CI_TO_MBQ, GAMMA_DOSE_CONSTANT, NEUTRON_SOURCES, DOSE_LIMITS,
    gamma_dr_from_activity, neutron_dr_from_activity,
)

st.set_page_config(page_title="Dose Rate Calculator", page_icon="☢️", layout="wide")


# ── Cached API calls ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _props(iso):       return fetch_nuclide_properties(iso)

@st.cache_data(show_spinner=False)
def _rads(iso, rtype): return fetch_decay_radiations(iso, rtype)

@st.cache_data(show_spinner=False)
def _basic(iso):       return fetch_iaea_data(iso)


# ── Physics helper (page-specific) ────────────────────────────────────────────
def safe_distance(dr_at_1m: float, limit_uSvh: float) -> float:
    return np.sqrt(dr_at_1m / limit_uSvh)


# ── Nuclear properties panel ──────────────────────────────────────────────────
def show_nuclear_properties(isotope_label: str, context_label: str = None):
    label = context_label or isotope_label

    with st.spinner(f"Fetching nuclear data for {label} from IAEA..."):
        props = _props(isotope_label)

    if props is None:
        st.warning(f"Nuclear property data not available from IAEA for **{label}**.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Atomic number Z",  props['z'])
    c2.metric("Mass number A",    props['a'])
    c3.metric("Neutron number N", props['n'])
    c4.metric("Spin-parity (Jπ)", str(props['spin_parity']))

    c1, c2, c3, c4 = st.columns(4)
    if props['atomic_mass_u']:
        c1.metric("Atomic mass", f"{props['atomic_mass_u']:.6f} u")
    if props['binding_keV_per_A']:
        c2.metric("Binding energy/A", f"{props['binding_keV_per_A']:.3f} keV")
    if props['mass_excess_keV']:
        c3.metric("Mass excess", f"{props['mass_excess_keV']:.3f} keV")
    if props['abundance'] is not None:
        c4.metric("Natural abundance", f"{props['abundance']} %")

    st.divider()

    col_decay, col_chain = st.columns([1, 1])

    with col_decay:
        st.markdown("**Decay modes**")
        for dm in props['decay_modes']:
            br = f" — {dm['branching_pct']} %" if dm['branching_pct'] is not None else ""
            st.markdown(f"- **{dm['mode']}**{br}")

        st.markdown("**Q-values**")
        q_items = [
            ("Q_α",  props['qa_keV'],  "keV"),
            ("Q_β⁻", props['qbm_keV'], "keV"),
            ("Q_EC", props['qec_keV'], "keV"),
        ]
        shown = [(lbl, v, u) for lbl, v, u in q_items if v is not None]
        if shown:
            for lbl, v, u in shown:
                st.markdown(f"- {lbl} = **{v:.1f}** {u}")
        else:
            st.caption("Q-values not available")

    with col_chain:
        st.markdown("**Decay chain (immediate)**")
        nuclide_name = f"{props['symbol']}-{props['a']}"
        if props['daughter']:
            daughter_basic = _basic(props['daughter'])
            d_hl = f"  (t½ = {daughter_basic['half_life_hum']})" if daughter_basic else ""
            st.markdown(f"**{nuclide_name}** → **{props['daughter']}**{d_hl}")
            if daughter_basic:
                d_stable = daughter_basic.get('half_life_hum', '').lower()
                if 'stable' in d_stable or float(daughter_basic.get('half_life_sec', 0) or 0) > 3e15:
                    st.success(f"Daughter **{props['daughter']}** is stable — no secondary dose contribution.")
                else:
                    st.warning(
                        f"Daughter **{props['daughter']}** is radioactive "
                        f"(t½ = {daughter_basic['half_life_hum']}). "
                        "It may contribute additional dose — consider secular equilibrium effects."
                    )
        else:
            st.caption("Daughter nuclide not determined (stable, SF, or unknown).")

        st.caption(
            "For complete multi-generation chains and parent nuclides, "
            "see [IAEA LiveChart of Nuclides](https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html)."
        )

    st.divider()

    st.markdown("**Decay radiation data** (from IAEA LiveChart)")
    tab_g, tab_bm, tab_x, tab_a = st.tabs(["γ Gamma", "β Beta", "✦ X-ray", "α Alpha"])

    with tab_g:
        with st.spinner("Loading gamma data..."):
            df = _rads(isotope_label, 'g')
        if df is not None and not df.empty:
            cols = [c for c in ['energy', 'unc_e', 'intensity', 'unc_i'] if c in df.columns]
            out  = df[cols].copy().dropna(subset=['energy'])
            out  = out.sort_values('intensity', ascending=False) if 'intensity' in out.columns else out
            out.columns = [{'energy': 'Energy (keV)', 'unc_e': '± Energy',
                            'intensity': 'Intensity (%)', 'unc_i': '± Intensity'}.get(c, c) for c in cols]
            st.dataframe(out.reset_index(drop=True), use_container_width=True, hide_index=True)
            st.caption(f"{len(out)} gamma line(s). Intensity = emissions per 100 decays.")
        else:
            st.info("No gamma line data available from IAEA for this nuclide.")

    with tab_bm:
        with st.spinner("Loading beta data..."):
            df_bm = _rads(isotope_label, 'bm')
            df_bp = _rads(isotope_label, 'bp')
        df_beta = (
            pd.concat([d for d in [df_bm, df_bp] if d is not None and not d.empty], ignore_index=True)
            if any(d is not None for d in [df_bm, df_bp]) else None
        )
        if df_beta is not None and not df_beta.empty:
            cols = [c for c in ['end_point_energy', 'energy', 'intensity', 'unc_i'] if c in df_beta.columns]
            out  = df_beta[cols].copy().dropna(subset=['intensity'] if 'intensity' in cols else cols[:1])
            out  = out.sort_values('intensity', ascending=False) if 'intensity' in out.columns else out
            out.columns = [{'end_point_energy': 'Endpoint energy (keV)', 'energy': 'Mean energy (keV)',
                            'intensity': 'Intensity (%)', 'unc_i': '± Intensity'}.get(c, c) for c in cols]
            st.dataframe(out.reset_index(drop=True), use_container_width=True, hide_index=True)
            st.caption("Endpoint energy = maximum beta energy (Q_β). Mean energy ≈ ⅓ endpoint.")
        else:
            st.info("No beta radiation data available from IAEA for this nuclide.")

    with tab_x:
        with st.spinner("Loading X-ray data..."):
            df = _rads(isotope_label, 'x')
        if df is not None and not df.empty:
            cols = [c for c in ['type', 'energy', 'unc_e', 'intensity', 'unc_i'] if c in df.columns]
            out  = df[cols].copy().dropna(subset=['energy'])
            out  = out.sort_values('intensity', ascending=False) if 'intensity' in out.columns else out
            out.columns = [{'type': 'X-ray type', 'energy': 'Energy (keV)', 'unc_e': '± Energy',
                            'intensity': 'Intensity (%)', 'unc_i': '± Intensity'}.get(c, c) for c in cols]
            st.dataframe(out.reset_index(drop=True), use_container_width=True, hide_index=True)
            st.caption("Characteristic X-rays from electron shell rearrangement after EC or internal conversion.")
        else:
            st.info("No X-ray data available from IAEA for this nuclide.")

    with tab_a:
        with st.spinner("Loading alpha data..."):
            df = _rads(isotope_label, 'a')
        if df is not None and not df.empty:
            cols = [c for c in ['energy', 'unc_e', 'intensity', 'unc_i'] if c in df.columns]
            out  = df[cols].copy().dropna(subset=['energy'])
            out  = out.sort_values('intensity', ascending=False) if 'intensity' in out.columns else out
            out.columns = [{'energy': 'Energy (keV)', 'unc_e': '± Energy',
                            'intensity': 'Intensity (%)', 'unc_i': '± Intensity'}.get(c, c) for c in cols]
            st.dataframe(out.reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.info("No alpha particle data available from IAEA for this nuclide.")

    st.caption(f"Data source: *{props['source']}*")


# ── Page ──────────────────────────────────────────────────────────────────────
st.title("☢️ Dose Rate Calculator")
st.markdown(
    "Estimate dose rate from **gamma** and **neutron** sources. "
    "Includes nuclear properties from IAEA LiveChart and safe working distance indicators (ICRP 103)."
)

input_unit = UNITS[0]  # default; overridden by sidebar selectbox
with st.sidebar:
    st.header("⚙️ Settings")
    input_unit = st.selectbox("Activity unit", UNITS, index=0)
    st.divider()
    st.subheader("📋 Dose limits")
    st.caption("ICRP 103 / IAEA BSS — assuming 2000 working h/yr")
    for label, d in DOSE_LIMITS.items():
        st.metric(label, f"{d['uSvh']} μSv/h")
    st.divider()
    st.caption(
        "**Disclaimer:** Point-source, inverse square law only. "
        "No scatter, buildup, or shielding. "
        "For detailed assessment use Monte Carlo simulation."
    )

# ── Source selection ──────────────────────────────────────────────────────────
st.markdown("### Source type")
source_type = st.radio("Source type", ["Gamma", "Neutron"], horizontal=True,
                        label_visibility="collapsed")
st.divider()

if source_type == "Gamma":
    st.markdown("### Isotope")
    isotope_sel = st.selectbox(
        "Isotope",
        list(GAMMA_DOSE_CONSTANT.keys()) + ["Other (enter Γ manually)"],
        label_visibility="collapsed",
    )
    if isotope_sel == "Other (enter Γ manually)":
        gamma_const   = st.number_input(
            "Dose rate constant Γ (μSv·m²·h⁻¹·MBq⁻¹)",
            min_value=0.0, value=0.1, format="%.4f",
            help="Refer to IAEA Safety Reports No. 37 or Delacroix handbook",
        )
        isotope_label = "Custom"
        props_isotope = None
    else:
        gamma_const   = GAMMA_DOSE_CONSTANT[isotope_sel]
        isotope_label = isotope_sel
        props_isotope = isotope_sel
        st.caption(f"Γ = **{gamma_const}** μSv·m²·h⁻¹·MBq⁻¹  (Delacroix et al.)")
        _bd = _basic(isotope_sel)
        if _bd:
            st.caption(f"Half-life: **{_bd['half_life_hum']}** · Decay mode: **{_bd['decay_mode']}**")
else:
    st.markdown("### Neutron source type")
    source_sel    = st.selectbox("Neutron source type", list(NEUTRON_SOURCES.keys()),
                                  label_visibility="collapsed")
    ns            = NEUTRON_SOURCES[source_sel]
    isotope_label = source_sel
    props_isotope = ns['parent_isotope']
    _bd = _basic(ns['parent_isotope'])
    if _bd:
        st.caption(
            f"Matrix isotope: **{ns['parent_isotope']}** · "
            f"Half-life: **{_bd['half_life_hum']}** · "
            f"Decay mode: **{_bd['decay_mode']}**"
        )

st.divider()

# ── Nuclear properties ─────────────────────────────────────────────────────────
if props_isotope:
    context = (
        f"{props_isotope} (matrix isotope of {source_sel})"
        if source_type == "Neutron" else props_isotope
    )
    with st.expander(f"🔬 Nuclear properties — {context}", expanded=True):
        if source_type == "Neutron":
            st.info(
                f"**Radiation components for {source_sel}:**  \n"
                f"**Neutron** — {ns['neutron_origin']}  \n\n"
                f"**Gamma** — {ns['gamma_origin']}"
            )
            st.divider()
        show_nuclear_properties(props_isotope, context_label=context)

st.divider()

# ── Dose rate inputs + results ────────────────────────────────────────────────
left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("Calculate dose rate")
    activity_val = st.number_input(f"Activity ({input_unit})", min_value=0.0,
                                    value=1.0, format="%.6f")
    distance_m   = st.number_input("Distance from source (m)", min_value=0.01,
                                    value=1.0, format="%.2f", step=0.1)
    calc_btn     = st.button("🔬 Calculate", type="primary")

with right:
    if not calc_btn:
        st.info("👈 Enter activity and distance, then click **Calculate**.")
    else:
        activity_MBq = convert_to_ci(activity_val, input_unit) * CI_TO_MBQ

        if source_type == "Gamma":
            dr       = gamma_dr_from_activity(activity_MBq, gamma_const, distance_m)
            dr_at_1m = gamma_dr_from_activity(activity_MBq, gamma_const, 1.0)
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Dose rate at {distance_m} m",   f"{dr:.4f} μSv/h")
            m2.metric(f"At {distance_m} m (mSv/h)",     f"{dr / 1000:.6f} mSv/h")
            m3.metric("Annual estimate (2000 h)",        f"{dr * 2000 / 1000:.3f} mSv/yr")
        else:
            nr = neutron_dr_from_activity(
                activity_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], distance_m)
            gr = (gamma_dr_from_activity(activity_MBq, ns['gamma_dose_constant'], distance_m)
                  if ns['gamma_dose_constant'] > 0 else 0.0)
            dr = nr + gr
            nr_at_1m = neutron_dr_from_activity(
                activity_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], 1.0)
            gr_at_1m = (gamma_dr_from_activity(activity_MBq, ns['gamma_dose_constant'], 1.0)
                        if ns['gamma_dose_constant'] > 0 else 0.0)
            dr_at_1m = nr_at_1m + gr_at_1m
            m1, m2, m3 = st.columns(3)
            m1.metric("Neutron dose rate", f"{nr:.4f} μSv/h",
                      help="From neutron fluence × ICRP 74 fluence-to-dose factor")
            m2.metric(f"Gamma ({ns['parent_isotope']} intrinsic)", f"{gr:.4f} μSv/h",
                      help=(f"From {ns['parent_isotope']} gamma emission — "
                            "part of the source matrix, not neutron interaction"))
            m3.metric(f"Total at {distance_m} m", f"{dr:.4f} μSv/h")
            st.caption(f"Annual estimate (2000 h): **{dr * 2000 / 1000:.3f} mSv/yr**")

        # Safe working distances
        st.subheader("Safe working distances")
        st.caption("Distance at which dose rate equals each ICRP 103 limit")
        sd_cols = st.columns(len(DOSE_LIMITS))
        for col, (label, d) in zip(sd_cols, DOSE_LIMITS.items()):
            col.metric(label, f"{safe_distance(dr_at_1m, d['uSvh']):.2f} m")

        # Plot
        d_arr = np.linspace(0.1, 10, 400)
        fig   = go.Figure()
        if source_type == "Gamma":
            fig.add_trace(go.Scatter(
                x=d_arr,
                y=[gamma_dr_from_activity(activity_MBq, gamma_const, d) for d in d_arr],
                mode='lines', name=f'{isotope_label} (γ)',
                line=dict(color='steelblue', width=2),
            ))
        else:
            nr_arr = [neutron_dr_from_activity(
                activity_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], d)
                for d in d_arr]
            gr_arr = [(gamma_dr_from_activity(activity_MBq, ns['gamma_dose_constant'], d)
                       if ns['gamma_dose_constant'] > 0 else 0.0)
                      for d in d_arr]
            fig.add_trace(go.Scatter(x=d_arr, y=[n + g for n, g in zip(nr_arr, gr_arr)],
                                      mode='lines', name='Total',
                                      line=dict(color='steelblue', width=2)))
            fig.add_trace(go.Scatter(x=d_arr, y=nr_arr, mode='lines',
                                      name='Neutron [⁹Be(α,n)]' if source_sel == 'Am-Be' else 'Neutron [SF]',
                                      line=dict(color='tomato', width=1.5, dash='dash')))
            if ns['gamma_dose_constant'] > 0:
                fig.add_trace(go.Scatter(x=d_arr, y=gr_arr, mode='lines',
                                          name=f'Gamma [{ns["parent_isotope"]} intrinsic γ]',
                                          line=dict(color='seagreen', width=1.5, dash='dot')))

        for label, d in DOSE_LIMITS.items():
            fig.add_hline(y=d['uSvh'], line_dash='dash', line_color=d['color'],
                          annotation_text=label, annotation_position='bottom right')
        fig.add_scatter(
            x=[distance_m], y=[dr], mode='markers+text',
            marker=dict(size=10, color='gold', symbol='diamond'),
            text=[f'{dr:.3f} μSv/h'], textposition='top right',
            name=f'Selected: {distance_m} m',
        )
        fig.update_layout(
            title=f"Dose Rate vs Distance — {isotope_label} ({activity_val} {input_unit})",
            xaxis_title="Distance (m)", yaxis_title="Dose rate (μSv/h)",
            yaxis_type="log", template="plotly_white", hovermode="x unified",
            legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Distance table
        st.subheader("Dose rate table")
        if source_type == "Neutron" and ns['gamma_dose_constant'] > 0:
            st.caption(
                f"**Neutron** = from {source_sel} neutron fluence (ICRP 74)  |  "
                f"**Gamma** = {ns['parent_isotope']} intrinsic emission  |  "
                f"**Total** = combined, used for compliance"
            )
        rows = []
        for d in [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 7.0, 10.0]:
            if source_type == "Gamma":
                dr_d = gamma_dr_from_activity(activity_MBq, gamma_const, d)
                rows.append({
                    "Distance (m)":             d,
                    "Dose rate (μSv/h)":        round(dr_d, 4),
                    "Dose rate (mSv/h)":        round(dr_d / 1000, 7),
                    "Annual estimate (mSv/yr)": round(dr_d * 2000 / 1000, 4),
                })
            else:
                nr_d = neutron_dr_from_activity(
                    activity_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], d)
                gr_d = (gamma_dr_from_activity(activity_MBq, ns['gamma_dose_constant'], d)
                        if ns['gamma_dose_constant'] > 0 else 0.0)
                rows.append({
                    "Distance (m)":                                     d,
                    "Neutron (μSv/h)":                                  round(nr_d, 4),
                    f"Gamma — {ns['parent_isotope']} intrinsic (μSv/h)": round(gr_d, 4),
                    "Total (μSv/h)":                                    round(nr_d + gr_d, 4),
                    "Annual estimate (mSv/yr)":                         round((nr_d + gr_d) * 2000 / 1000, 4),
                })
        df_table = pd.DataFrame(rows)
        st.dataframe(df_table, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇️ Download table (CSV)", df_table.to_csv(index=False),
            f"dose_rate_{isotope_label}_{activity_val}{input_unit}.csv", "text/csv",
        )
