import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from utils.decay_math import convert_to_ci, UNITS
from utils.iaea_api import fetch_iaea_data

st.set_page_config(page_title="Working Time Calculator", page_icon="⏱️", layout="wide")

# ── Constants ──────────────────────────────────────────────────────────────────
CI_TO_MBQ = 37000.0

GAMMA_DOSE_CONSTANT = {
    'Am-241': 0.0199, 'Ba-133': 0.0819, 'Co-60':  0.3059, 'Cs-137': 0.0965,
    'Eu-152': 0.1697, 'Ge-68':  0.1736, 'Ir-192': 0.1108, 'Mn-54':  0.1242,
    'Na-22':  0.3219, 'Pu-239': 0.0017, 'Ra-226': 0.2387, 'Y-88':   0.3288,
}

NEUTRON_SOURCES = {
    'Am-Be':  {'parent_isotope': 'Am-241', 'neutron_yield_per_MBq': 65.0,
               'h_phi_pSv_cm2': 391.0, 'gamma_dose_constant': 0.0199},
    'Cf-252': {'parent_isotope': 'Cf-252', 'neutron_yield_per_MBq': 116600.0,
               'h_phi_pSv_cm2': 385.0, 'gamma_dose_constant': 0.0},
}

# Annual dose limits (mSv/y) per ICRP 103 / IAEA BSS
ANNUAL_LIMITS_MSV = {
    'Occupational (ICRP 103 — 20 mSv/y)':        20.0,
    'Supervised area (6 mSv/y)':                   6.0,
    'Public / uncontrolled (ICRP 103 — 1 mSv/y)': 1.0,
    'Custom':                                      None,
}

WORK_H_DAY   = 8
WORK_D_WEEK  = 5
WORK_WK_YEAR = 50
WORK_H_YEAR  = WORK_H_DAY * WORK_D_WEEK * WORK_WK_YEAR  # 2000 h/y


# ── Helpers ────────────────────────────────────────────────────────────────────
def gamma_dr_from_activity(act_MBq, gamma_const, dist_m):
    return gamma_const * act_MBq / dist_m ** 2


def neutron_dr_from_activity(act_MBq, yield_per_MBq, h_phi, dist_m):
    S    = act_MBq * yield_per_MBq
    r_cm = dist_m * 100
    return S * h_phi * 3600 / (4 * np.pi * r_cm ** 2 * 1e6)


def fmt_time(hours: float) -> str:
    if hours <= 0:
        return "0 min"
    if hours > WORK_H_YEAR * 100:
        return "> 100 y"
    if hours > WORK_H_YEAR:
        yrs = hours / WORK_H_YEAR
        return f"{yrs:.1f} working years"
    if hours >= 1:
        h = int(hours)
        m = int(round((hours - h) * 60))
        return f"{h} h {m} min" if m > 0 else f"{h} h"
    return f"{hours * 60:.1f} min"


# ── Page layout ────────────────────────────────────────────────────────────────
st.title("⏱️ Working Time Calculator")
st.markdown(
    "Calculate the **maximum time** a worker can spend near a radioactive source "
    "without exceeding regulatory annual dose limits (ICRP 103 / IAEA BSS)."
)

col_in, col_out = st.columns([1, 1], gap="large")

# ── LEFT: Inputs ───────────────────────────────────────────────────────────────
with col_in:
    st.markdown("### Dose rate at working position")
    dr_mode = st.radio(
        "Specify dose rate as",
        ["Calculate from activity", "Enter directly"],
        horizontal=True,
        key="wt_dr_mode",
    )

    dr_working = 0.0
    act_MBq    = 0.0
    source_type = "Gamma"
    isotope_sel = list(GAMMA_DOSE_CONSTANT.keys())[0]

    if dr_mode == "Calculate from activity":
        st.markdown("### Source type")
        source_type = st.radio(
            "Source type", ["Gamma", "Neutron"],
            horizontal=True, key="wt_src_type", label_visibility="collapsed",
        )

        if source_type == "Gamma":
            st.markdown("### Isotope")
            isotope_sel = st.selectbox(
                "Isotope", list(GAMMA_DOSE_CONSTANT.keys()),
                key="wt_iso", label_visibility="collapsed",
            )
            _bd = fetch_iaea_data(isotope_sel)
            if _bd:
                st.caption(
                    f"Half-life: **{_bd['half_life_hum']}** · "
                    f"Decay mode: **{_bd['decay_mode']}**"
                )
        else:
            st.markdown("### Neutron source type")
            source_sel = st.selectbox(
                "Neutron source type", list(NEUTRON_SOURCES.keys()),
                key="wt_ns", label_visibility="collapsed",
            )
            ns  = NEUTRON_SOURCES[source_sel]
            _bd = fetch_iaea_data(ns['parent_isotope'])
            if _bd:
                st.caption(
                    f"Matrix isotope: **{ns['parent_isotope']}** · "
                    f"Half-life: **{_bd['half_life_hum']}** · "
                    f"Decay mode: **{_bd['decay_mode']}**"
                )

        a_col, u_col = st.columns([2, 1])
        with a_col:
            act_val = st.number_input(
                "Activity", min_value=0.0, value=1.0, step=0.1, key="wt_act",
            )
        with u_col:
            act_unit = st.selectbox("Unit", UNITS, index=UNITS.index('MBq'), key="wt_unit")

        dist_m = st.number_input(
            "Distance from source (m)",
            min_value=0.1, value=1.0, step=0.1, key="wt_dist",
        )

        act_MBq = convert_to_ci(act_val, act_unit) * CI_TO_MBQ

        if source_type == "Gamma":
            dr_working = gamma_dr_from_activity(act_MBq, GAMMA_DOSE_CONSTANT[isotope_sel], dist_m)
        else:
            nr = neutron_dr_from_activity(
                act_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], dist_m,
            )
            gr = (
                gamma_dr_from_activity(act_MBq, ns['gamma_dose_constant'], dist_m)
                if ns['gamma_dose_constant'] > 0 else 0.0
            )
            dr_working = nr + gr

        st.metric("Dose rate at working position", f"{dr_working:.4f} μSv/h")

    else:
        dr_working = st.number_input(
            "Dose rate at working position (μSv/h)",
            min_value=0.0, value=10.0, step=1.0, key="wt_dr_direct",
        )

    # ── Dose limit ─────────────────────────────────────────────────────────────
    st.markdown("### Dose limit")
    limit_sel = st.selectbox(
        "Dose limit scheme", list(ANNUAL_LIMITS_MSV.keys()), key="wt_limit",
    )
    if limit_sel == "Custom":
        dose_limit_mSv_y = st.number_input(
            "Annual dose limit (mSv/y)",
            min_value=0.1, value=20.0, step=1.0, key="wt_custom",
        )
    else:
        dose_limit_mSv_y = ANNUAL_LIMITS_MSV[limit_sel]
        st.caption(
            f"Annual limit: **{dose_limit_mSv_y} mSv/y** "
            f"({dose_limit_mSv_y * 1000:.0f} μSv/y)"
        )

    # ── Occupancy factor ───────────────────────────────────────────────────────
    st.markdown("### Occupancy factor")
    st.caption(
        "Fraction of work time actually spent at this position. "
        "1.0 = full time, 0.25 = occasional (IAEA T = 1/4)."
    )
    occupancy = st.slider(
        "Occupancy factor", min_value=0.05, max_value=1.0,
        value=1.0, step=0.05, key="wt_occ",
    )

# ── RIGHT: Results ─────────────────────────────────────────────────────────────
with col_out:
    st.markdown("### Results")

    if dr_working <= 0:
        st.info("Enter a dose rate greater than 0 to see results.")
        st.stop()

    annual_budget_uSv   = dose_limit_mSv_y * 1000.0          # μSv/y (total limit)
    effective_budget    = annual_budget_uSv * occupancy       # adjusted for occupancy

    t_max_year_h  = effective_budget / dr_working             # h/y
    t_max_week_h  = t_max_year_h / WORK_WK_YEAR              # h/wk
    t_max_day_h   = t_max_week_h / WORK_D_WEEK               # h/day
    t_max_day_min = t_max_day_h  * 60                        # min/day

    # ALARA design goal: 1/10 of regulatory limit
    alara_factor  = 0.1
    t_alara_day_h = t_max_day_h  * alara_factor
    t_alara_wk_h  = t_max_week_h * alara_factor

    # Status
    if t_max_day_min >= 480:
        bg, label = "#2E7D32", "No significant time restriction at this position"
    elif t_max_day_min >= 60:
        bg, label = "#F57C00", "Moderate dose rate — monitor cumulative exposure"
    elif t_max_day_min >= 15:
        bg, label = "#E64A19", "High dose rate — strictly limit working time"
    else:
        bg, label = "#B71C1C", "Very high dose rate — minimise time, maximise distance"

    st.markdown(
        f'<div style="background:{bg};color:white;padding:10px 16px;'
        f'border-radius:6px;font-weight:bold;font-size:1rem;">{label}</div>',
        unsafe_allow_html=True,
    )
    st.markdown("")

    # Key metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Max time / day",  fmt_time(t_max_day_h))
    m2.metric("Max time / week", fmt_time(t_max_week_h))
    m3.metric("Max time / year", fmt_time(t_max_year_h))

    st.markdown("")

    # % of working day consumed
    pct_day = min(t_max_day_h / WORK_H_DAY * 100, 100.0)
    st.progress(pct_day / 100.0)
    st.caption(
        f"Max working time = **{pct_day:.1f}%** of a standard 8-hour working day"
    )

    st.markdown("")
    st.markdown(
        f"**ALARA design goal (1/10 of limit):** "
        f"{fmt_time(t_alara_day_h)} / day · "
        f"{fmt_time(t_alara_wk_h)} / week"
    )

    # ── Bar chart: comparison across dose limit schemes ──────────────────────
    st.markdown("### Working time per day — dose limit comparison")
    scheme_names  = [k for k, v in ANNUAL_LIMITS_MSV.items() if v is not None]
    scheme_limits = [ANNUAL_LIMITS_MSV[k] for k in scheme_names]
    times_day_h   = [
        lim * 1000 * occupancy / dr_working / WORK_WK_YEAR / WORK_D_WEEK
        for lim in scheme_limits
    ]
    bar_colors = ['#1565C0', '#E64A19', '#2E7D32']

    fig_bar = go.Figure(go.Bar(
        x=scheme_names,
        y=[min(t, WORK_H_DAY * 1.25) for t in times_day_h],
        text=[fmt_time(t) for t in times_day_h],
        textposition='outside',
        marker_color=bar_colors,
    ))
    fig_bar.add_hline(
        y=WORK_H_DAY, line_dash="dash", line_color="gray",
        annotation_text="8 h working day", annotation_position="top right",
    )
    fig_bar.update_layout(
        yaxis_title="Max working time per day (h)",
        yaxis_range=[0, WORK_H_DAY * 1.6],
        showlegend=False,
        height=340,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ── Distance table (only when activity mode is active) ────────────────────
    if dr_mode == "Calculate from activity":
        st.markdown("### Working time vs. distance")
        distances = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0]
        rows = []
        for d in distances:
            if source_type == "Gamma":
                dr_d = gamma_dr_from_activity(act_MBq, GAMMA_DOSE_CONSTANT[isotope_sel], d)
            else:
                nr_d = neutron_dr_from_activity(
                    act_MBq, ns['neutron_yield_per_MBq'], ns['h_phi_pSv_cm2'], d,
                )
                gr_d = (
                    gamma_dr_from_activity(act_MBq, ns['gamma_dose_constant'], d)
                    if ns['gamma_dose_constant'] > 0 else 0.0
                )
                dr_d = nr_d + gr_d

            t_d_h = effective_budget / dr_d / WORK_WK_YEAR / WORK_D_WEEK
            rows.append({
                'Distance (m)':       d,
                'Dose rate (μSv/h)':  round(dr_d, 4),
                'Max time / day':     fmt_time(t_d_h),
                'Max time / week':    fmt_time(t_d_h * WORK_D_WEEK),
                'ALARA / day':        fmt_time(t_d_h * alara_factor),
            })

        df_dist = pd.DataFrame(rows)
        st.dataframe(df_dist, use_container_width=True, hide_index=True)
        csv = df_dist.to_csv(index=False)
        st.download_button(
            "⬇ Download distance table (CSV)",
            csv,
            "working_time_vs_distance.csv",
            "text/csv",
        )

    # ── Summary download ───────────────────────────────────────────────────────
    src_label = (
        f"{isotope_sel} gamma" if dr_mode == "Calculate from activity" and source_type == "Gamma"
        else source_sel + " neutron" if dr_mode == "Calculate from activity"
        else "direct entry"
    )
    summary_txt = (
        f"Working Time Calculator — Summary\n"
        f"Generated by Nuclear Source Toolkit\n"
        f"{'=' * 50}\n\n"
        f"Source                        : {src_label}\n"
        f"Dose rate at working position : {dr_working:.4f} μSv/h\n"
        f"Dose limit scheme             : {limit_sel}\n"
        f"Annual dose limit             : {dose_limit_mSv_y} mSv/y "
        f"({annual_budget_uSv:.0f} μSv/y)\n"
        f"Occupancy factor              : {occupancy}\n"
        f"Effective annual budget       : {effective_budget:.0f} μSv/y\n\n"
        f"Maximum working time\n"
        f"  Per day   : {fmt_time(t_max_day_h)}\n"
        f"  Per week  : {fmt_time(t_max_week_h)}\n"
        f"  Per year  : {fmt_time(t_max_year_h)}\n\n"
        f"ALARA design goal (1/10 of limit)\n"
        f"  Per day   : {fmt_time(t_alara_day_h)}\n"
        f"  Per week  : {fmt_time(t_alara_wk_h)}\n\n"
        f"Basis: ICRP 103 / IAEA BSS\n"
        f"       {WORK_H_DAY} h/day, {WORK_D_WEEK} days/week, "
        f"{WORK_WK_YEAR} weeks/year ({WORK_H_YEAR} h/y)\n"
    )
    st.download_button(
        "⬇ Download summary (TXT)",
        summary_txt,
        "working_time_summary.txt",
        "text/plain",
    )

st.divider()
st.caption(
    "**Disclaimer:** Results are estimates based on ICRP 103 / IAEA BSS dose limits and "
    "point-source inverse-square-law approximations. Always verify against your "
    "institution's radiation protection programme and local regulations."
)
