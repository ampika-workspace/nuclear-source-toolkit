import streamlit as st
import math
from utils.iaea_api import fetch_iaea_data, fetch_decay_radiations, COMMON_ISOTOPES
from utils.constants import (
    GAMMA_DOSE_CONSTANT, GAMMA_HVL, DOSE_LIMITS, IAEA_D_VALUES_TBQ,
    gamma_dr_from_activity, CI_TO_MBQ,
)
from utils.decay_math import convert_to_ci, UNITS

st.set_page_config(page_title="Field Reference Card", page_icon="🔬", layout="wide")

# IAEA source category per RS-G-1.9 / SS No. 23-G (A/D ratio thresholds)
_CAT_BG  = {1: '#B71C1C', 2: '#E64A19', 3: '#F57C00', 4: '#1565C0', 5: '#388E3C'}
_CAT_LBL = {1: 'Category 1', 2: 'Category 2', 3: 'Category 3',
            4: 'Category 4', 5: 'Category 5'}


def _get_category(act_tbq: float, isotope: str):
    d = IAEA_D_VALUES_TBQ.get(isotope)
    if not d or act_tbq <= 0:
        return None, None
    r   = act_tbq / d
    cat = 1 if r >= 1000 else 2 if r >= 10 else 3 if r >= 1 else 4 if r >= 0.01 else 5
    return cat, r


@st.cache_data(show_spinner=False)
def _fetch_iaea(iso: str):
    return fetch_iaea_data(iso)


@st.cache_data(show_spinner=False)
def _fetch_gammas(iso: str):
    return fetch_decay_radiations(iso, 'g')


# ── Page ───────────────────────────────────────────────────────────────────────
st.title("🔬 Radionuclide Field Reference Card")
st.markdown(
    "Quick-reference card for field use — half-life, decay mode, principal gamma lines, "
    "shielding HVL, and safe working distances per ICRP 103."
)

with st.sidebar:
    st.header("⚙️ Data sources")
    st.info(
        "🛰 Half-life / decay mode: IAEA LiveChart API  \n"
        "📡 Gamma emission lines: IAEA LiveChart API  \n"
        "📐 HVL: NCRP-49 / IAEA Safety Reports No. 37  \n"
        "📏 Dose constants: Delacroix et al.  \n"
        "🏷 Source category: IAEA RS-G-1.9"
    )
    st.divider()
    with st.expander("📋 Isotopes with full data"):
        full_set = sorted(set(GAMMA_HVL.keys()) & set(GAMMA_DOSE_CONSTANT.keys()))
        st.write(", ".join(full_set))
        st.caption(
            "These isotopes have tabulated dose constants and HVL values. "
            "Any other isotope can be typed below — IAEA nuclear data (half-life, "
            "gamma lines) will still be fetched live."
        )
    with st.expander("IAEA source categories"):
        st.markdown(
            "| Cat | A/D ratio | Hazard level |\n"
            "|-----|-----------|----------|\n"
            "| 1 | ≥ 1 000 | Fatal within hours |\n"
            "| 2 | 10 – 1 000 | Fatal within hours–days |\n"
            "| 3 | 1 – 10 | Fatal within weeks–months |\n"
            "| 4 | 0.01 – 1 | Unlikely permanent injury |\n"
            "| 5 | < 0.01 | Minimal hazard |"
        )
        st.caption("D = Dangerous Quantity (RS-G-1.9 Table A-2)")

# ── Inputs ─────────────────────────────────────────────────────────────────────
with st.form("card_form"):
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        iso_sel = st.selectbox(
            "Select isotope",
            [""] + COMMON_ISOTOPES + ["Other (type below)"],
        )
        if iso_sel == "Other (type below)":
            isotope = st.text_input("Isotope name", placeholder="e.g. Tc-99m, Ho-166m, Se-75")
        elif iso_sel == "":
            isotope = ""
        else:
            isotope = iso_sel
    with c2:
        act_val  = st.number_input(
            "Source activity", min_value=0.0, value=100.0, format="%.6f",
            help="Used to compute 1 m dose rate, safe distances, and IAEA source category.",
        )
    with c3:
        act_unit = st.selectbox(
            "Unit", UNITS, index=UNITS.index('MBq') if 'MBq' in UNITS else 0,
        )
    gen_btn = st.form_submit_button("🔬 Generate card", type="primary",
                                     disabled=(isotope == ""))

if not gen_btn:
    st.info("👆 Select an isotope and enter the source activity, then click **Generate card**.")
    st.stop()

# ── Fetch data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching IAEA nuclear data..."):
    iaea    = _fetch_iaea(isotope)
    df_rads = _fetch_gammas(isotope)

if iaea is None:
    st.error(
        f"Could not fetch nuclear data for **{isotope}**. "
        "Check the isotope name format (e.g. Am-241, Tc-99m) or your network connection."
    )
    st.stop()

# Resolve available local data
has_gamma_c = isotope in GAMMA_DOSE_CONSTANT
has_hvl     = isotope in GAMMA_HVL
gamma_c     = GAMMA_DOSE_CONSTANT.get(isotope)
hvl_data    = GAMMA_HVL.get(isotope)

act_MBq   = convert_to_ci(act_val, act_unit) * CI_TO_MBQ
act_TBq   = act_MBq / 1e6
data_src  = iaea.get("source", "IAEA LiveChart")
act_label = f"{act_val:.6g} {act_unit}"

dr_1m = gamma_dr_from_activity(act_MBq, gamma_c, 1.0) if has_gamma_c else None
cat, a_over_d = _get_category(act_TBq, isotope)

# Safe distances (only if dose constant available)
_limit_hex = {'red': '#E24B4A', 'orange': '#EF9F27', 'green': '#1D9E75'}
safe_rows = []
if has_gamma_c:
    for name, lim in DOSE_LIMITS.items():
        d = math.sqrt(gamma_c * act_MBq / lim['uSvh'])
        safe_rows.append((name, lim['uSvh'], lim['color'], d))

# ── Gamma emissions HTML ────────────────────────────────────────────────────────
gammas_section = ""
if df_rads is not None and not df_rads.empty:
    ecol = next((c for c in df_rads.columns if 'energy' in c.lower()), None)
    icol = next((c for c in df_rads.columns
                 if c in ('iy', 'intensity', 'iy_pct') or 'intensit' in c.lower()), None)
    if ecol and icol:
        top = (df_rads[[ecol, icol]].dropna()
               .sort_values(icol, ascending=False)
               .head(6))
        rows_html = ""
        for i, (_, row) in enumerate(top.iterrows()):
            sep = "border-top:0.5px solid rgba(128,128,128,0.15);" if i else ""
            rows_html += (
                f'<tr>'
                f'<td style="padding:4px 0;{sep}">{float(row[ecol]):.1f}</td>'
                f'<td style="text-align:right;padding:4px 0;{sep}">{float(row[icol]):.1f}%</td>'
                f'</tr>'
            )
        gammas_section = (
            '<div style="border-top:0.5px solid rgba(128,128,128,0.2);'
            'padding-top:12px;margin-bottom:12px;">'
            '<div style="font-size:11px;font-weight:600;color:rgba(128,128,128,0.85);'
            'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">'
            'Principal gamma emissions (IAEA LiveChart)</div>'
            '<table style="width:100%;font-size:12px;border-collapse:collapse;">'
            '<tr style="color:rgba(128,128,128,0.75);font-size:11px;">'
            '<th style="text-align:left;padding:3px 0;font-weight:500;">Energy (keV)</th>'
            '<th style="text-align:right;padding:3px 0;font-weight:500;">Intensity (%)</th>'
            '</tr>'
            + rows_html +
            '</table></div>'
        )
    else:
        gammas_section = (
            '<div style="border-top:0.5px solid rgba(128,128,128,0.2);'
            'padding-top:12px;margin-bottom:12px;'
            'font-size:12px;color:rgba(128,128,128,0.6);">'
            'Gamma line data not available for this isotope.</div>'
        )
else:
    gammas_section = (
        '<div style="border-top:0.5px solid rgba(128,128,128,0.2);'
        'padding-top:12px;margin-bottom:12px;'
        'font-size:12px;color:rgba(128,128,128,0.6);">'
        'Gamma emission lines unavailable — IAEA API offline or isotope has no gamma output.</div>'
    )

# ── Badge HTML ─────────────────────────────────────────────────────────────────
dm_str = iaea["decay_mode"]
dm_bg  = ("#7B1FA2" if 'α' in dm_str
          else "#1565C0" if ('β' in dm_str or 'EC' in dm_str)
          else "#E64A19" if 'SF' in dm_str
          else "#455A64")
dm_badge = (
    f'<span style="font-size:11px;background:{dm_bg};color:white;'
    f'padding:3px 10px;border-radius:20px;font-weight:500;">'
    f'{dm_str} emitter</span>'
)
cat_badge = ""
if cat is not None:
    cat_badge = (
        f'<span style="font-size:11px;background:{_CAT_BG[cat]};color:white;'
        f'padding:3px 10px;border-radius:20px;font-weight:500;">'
        f'{_CAT_LBL[cat]} source</span>'
    )

# ── Metrics row HTML ───────────────────────────────────────────────────────────
if has_gamma_c:
    metrics_html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:16px;">'
        '<div style="background:rgba(128,128,128,0.08);border-radius:8px;padding:10px 12px;">'
        '<div style="font-size:11px;color:rgba(128,128,128,0.8);margin-bottom:3px;">Half-life</div>'
        f'<div style="font-size:17px;font-weight:600;">{iaea["half_life_hum"]}</div>'
        '</div>'
        '<div style="background:rgba(128,128,128,0.08);border-radius:8px;padding:10px 12px;">'
        '<div style="font-size:11px;color:rgba(128,128,128,0.8);margin-bottom:3px;">Dose constant Γ</div>'
        f'<div style="font-size:17px;font-weight:600;">{gamma_c:.4f}</div>'
        '<div style="font-size:10px;color:rgba(128,128,128,0.6);">μSv·m²·h⁻¹·MBq⁻¹</div>'
        '</div>'
        '<div style="background:rgba(128,128,128,0.08);border-radius:8px;padding:10px 12px;">'
        '<div style="font-size:11px;color:rgba(128,128,128,0.8);margin-bottom:3px;">1 m dose rate</div>'
        f'<div style="font-size:17px;font-weight:600;">{dr_1m:.2f} μSv/h</div>'
        f'<div style="font-size:10px;color:rgba(128,128,128,0.6);">at {act_label}</div>'
        '</div>'
        '</div>'
    )
else:
    metrics_html = (
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px;">'
        '<div style="background:rgba(128,128,128,0.08);border-radius:8px;padding:10px 12px;">'
        '<div style="font-size:11px;color:rgba(128,128,128,0.8);margin-bottom:3px;">Half-life</div>'
        f'<div style="font-size:17px;font-weight:600;">{iaea["half_life_hum"]}</div>'
        '</div>'
        '<div style="background:rgba(128,128,128,0.08);border-radius:8px;padding:10px 12px;">'
        '<div style="font-size:11px;color:rgba(128,128,128,0.8);margin-bottom:3px;">Decay mode</div>'
        f'<div style="font-size:17px;font-weight:600;">{dm_str}</div>'
        '</div>'
        '</div>'
        '<div style="margin-bottom:14px;padding:8px 12px;'
        'background:rgba(37,99,235,0.07);border-radius:8px;'
        'font-size:12px;color:rgba(37,99,235,0.9);">'
        f'ℹ Dose constant and safe distances are not tabulated for <strong>{isotope}</strong>. '
        'Dose-rate and shielding calculations are available for the 12 common gamma calibration '
        'sources listed in the sidebar.'
        '</div>'
    )

# ── HVL HTML ───────────────────────────────────────────────────────────────────
if has_hvl:
    hvl_cells = "".join(
        f'<div style="text-align:center;padding:8px 4px;'
        f'border:0.5px solid rgba(128,128,128,0.25);border-radius:8px;">'
        f'<div style="font-size:14px;font-weight:600;">{hvl_data[m]} cm</div>'
        f'<div style="font-size:11px;color:rgba(128,128,128,0.75);">{m}</div>'
        f'</div>'
        for m in ['Lead', 'Steel', 'Concrete', 'Water']
    )
    hvl_section = (
        '<div style="border-top:0.5px solid rgba(128,128,128,0.2);padding-top:12px;margin-bottom:12px;">'
        '<div style="font-size:11px;font-weight:600;color:rgba(128,128,128,0.85);'
        'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">'
        f'Shielding — HVL (cm, broad-beam, E = {hvl_data["dominant_keV"]} keV)</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;">{hvl_cells}</div>'
        '</div>'
    )
else:
    hvl_section = (
        '<div style="border-top:0.5px solid rgba(128,128,128,0.2);padding-top:12px;margin-bottom:12px;'
        'font-size:12px;color:rgba(128,128,128,0.6);">'
        f'HVL shielding data not tabulated for <strong>{isotope}</strong> '
        '(NCRP-49 / IAEA data covers the 12 common gamma calibration sources).'
        '</div>'
    )

# ── Safe distance HTML ─────────────────────────────────────────────────────────
if safe_rows:
    dist_cells = "".join(
        f'<div style="padding:8px 0 8px 10px;border-left:3px solid {_limit_hex.get(color, "#888")};">'
        f'<div style="font-size:15px;font-weight:600;">{d:.2f} m</div>'
        f'<div style="font-size:11px;color:rgba(128,128,128,0.8);">'
        f'{name.split(" (")[0]} ({usvh} μSv/h)</div>'
        f'</div>'
        for name, usvh, color, d in safe_rows
    )
    safe_section = (
        '<div style="border-top:0.5px solid rgba(128,128,128,0.2);padding-top:12px;">'
        '<div style="font-size:11px;font-weight:600;color:rgba(128,128,128,0.85);'
        'text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px;">'
        f'Safe distances (ICRP 103) at {act_label}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;">{dist_cells}</div>'
        '</div>'
    )
else:
    safe_section = ""

# ── Assemble card ──────────────────────────────────────────────────────────────
card_html = (
    '<div style="background:var(--secondary-background-color,#f8fafc);'
    'border:1px solid rgba(128,128,128,0.18);border-radius:12px;'
    'padding:22px 26px;font-family:sans-serif;">'

    # Header
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px;">'
    '<div>'
    f'<div style="font-size:24px;font-weight:600;letter-spacing:-0.5px;">{isotope}</div>'
    f'<div style="font-size:13px;color:rgba(128,128,128,0.85);margin-top:2px;">'
    f't½ = {iaea["half_life_hum"]} · {data_src}</div>'
    '</div>'
    f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px;padding-top:2px;">'
    f'{dm_badge}{cat_badge}'
    '</div></div>'

    + metrics_html
    + hvl_section
    + gammas_section
    + safe_section +

    # Footer
    '<div style="margin-top:16px;padding:8px 12px;background:rgba(128,128,128,0.07);'
    'border-radius:8px;font-size:11px;color:rgba(128,128,128,0.65);">'
    f'Nuclear data: {data_src} · Dose constants: Delacroix et al. · '
    'HVL: NCRP-49 · Limits: ICRP 103 · Nuclear Source Toolkit'
    '</div>'
    '</div>'
)

# ── Render ────────────────────────────────────────────────────────────────────
card_col, info_col = st.columns([3, 1])
with card_col:
    st.markdown(card_html, unsafe_allow_html=True)

with info_col:
    st.markdown("**Data availability**")
    st.metric("Half-life", iaea["half_life_hum"])
    if has_gamma_c:
        st.metric("Dose constant Γ", f"{gamma_c:.4f}",
                  help="μSv·m²·h⁻¹·MBq⁻¹  (Delacroix et al.)")
        st.metric("1 m dose rate", f"{dr_1m:.4f} μSv/h")
    else:
        st.warning("Dose constant: not tabulated")

    if has_hvl:
        st.success(f"HVL data: available ({hvl_data['dominant_keV']} keV)")
    else:
        st.warning("HVL data: not tabulated")

    if cat is not None:
        d_val = IAEA_D_VALUES_TBQ[isotope]
        st.markdown(
            f"**IAEA Category:** "
            f'<span style="color:{_CAT_BG[cat]};font-weight:600;">{_CAT_LBL[cat]}</span>',
            unsafe_allow_html=True,
        )
        st.caption(f"A/D = {a_over_d:.3f}  (D = {d_val} TBq)")
    else:
        st.caption("IAEA category: D value not tabulated for this isotope.")

    if df_rads is not None and not df_rads.empty:
        st.success("Gamma lines: IAEA LiveChart (live)")
    else:
        st.warning("Gamma lines: IAEA API offline or not applicable")

# ── Download ──────────────────────────────────────────────────────────────────
st.markdown("")
summary_lines = [
    "=" * 60,
    f"RADIONUCLIDE FIELD REFERENCE CARD — {isotope}",
    "Generated by Nuclear Source Toolkit",
    "=" * 60,
    f"Half-life         : {iaea['half_life_hum']}",
    f"Decay mode        : {iaea['decay_mode']}",
    f"Data source       : {data_src}",
    "",
]

if has_gamma_c:
    summary_lines += [
        f"Dose constant Γ   : {gamma_c:.4f} μSv·m²·h⁻¹·MBq⁻¹  (Delacroix et al.)",
        f"Source activity   : {act_label}",
        f"1 m dose rate     : {dr_1m:.4f} μSv/h",
        "",
    ]
else:
    summary_lines.append(f"Dose constant     : not tabulated for {isotope}")
    summary_lines.append("")

if has_hvl:
    summary_lines += [
        "Shielding — Half-Value Layers (cm, broad-beam, NCRP-49)",
        f"  Dominant energy : {hvl_data['dominant_keV']} keV",
    ]
    for mat in ['Lead', 'Steel', 'Concrete', 'Water']:
        summary_lines.append(f"  {mat:<12} : {hvl_data[mat]} cm")
    summary_lines.append("")
else:
    summary_lines.append(f"HVL data          : not tabulated for {isotope}")
    summary_lines.append("")

if safe_rows:
    summary_lines.append("Safe working distances (ICRP 103 / IAEA BSS)")
    for name, usvh, _, d in safe_rows:
        summary_lines.append(f"  {name:<42}: {d:.2f} m  (limit: {usvh} μSv/h)")
    summary_lines.append("")

if cat is not None:
    d_val = IAEA_D_VALUES_TBQ[isotope]
    summary_lines += [
        f"IAEA source category (RS-G-1.9): {_CAT_LBL[cat]}",
        f"  D value: {d_val} TBq  |  A/D = {a_over_d:.3f}",
        "",
    ]

summary_lines += [
    "=" * 60,
    "DISCLAIMER: Estimates based on ICRP 103 / IAEA BSS and",
    "point-source inverse-square-law approximations.",
    "Always verify against your institution's radiation",
    "protection programme and local regulations.",
]

dl_col, hint_col = st.columns([1, 3])
with dl_col:
    st.download_button(
        "⬇ Download summary (TXT)",
        "\n".join(summary_lines),
        f"{isotope.replace('-', '')}_field_card.txt",
        "text/plain",
    )
with hint_col:
    st.caption("🖨️ To print or save as PDF: use **Ctrl+P** / **Cmd+P** in your browser.")

st.divider()
st.caption(
    "**Disclaimer:** HVL values are broad-beam approximations (NCRP-49 / IAEA Safety Reports No. 37). "
    "Safe distances assume an unshielded point source via inverse-square law. "
    "Always verify against your institution's radiation protection programme and local regulations."
)
