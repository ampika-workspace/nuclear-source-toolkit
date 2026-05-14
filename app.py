import re
import streamlit as st
from utils.iaea_api import fetch_iaea_data


def _page_slug(page_path: str) -> str:
    """Derive Streamlit MPA URL from a pages/ file path (e.g. pages/01_Foo.py → /Foo)."""
    name = page_path.split("/")[-1].replace(".py", "")
    return "/" + re.sub(r"^\d+_", "", name)

APP_VERSION = "1.0.0"
APP_UPDATED = "May 2026"

st.set_page_config(
    page_title="Nuclear Source Toolkit",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.tool-card {
    background-color: var(--secondary-background-color, #f8fafc);
    border: 1px solid rgba(128,128,128,0.18);
    border-radius: 12px;
    padding: 22px 24px 18px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s ease;
    margin-bottom: 4px;
    box-sizing: border-box;
    width: 100%;
    overflow: hidden;
}
.tool-card:hover { box-shadow: 0 4px 18px rgba(0,0,0,0.13); }
.coming-soon-card {
    background: repeating-linear-gradient(
        45deg,
        var(--secondary-background-color, #f8fafc) 0px,
        var(--secondary-background-color, #f8fafc) 10px,
        rgba(128,128,128,0.06) 10px,
        rgba(128,128,128,0.06) 20px
    );
    border: 1.5px dashed rgba(128,128,128,0.35);
    border-radius: 12px;
    padding: 22px 24px 18px;
    margin-bottom: 4px;
    box-sizing: border-box;
    width: 100%;
    overflow: hidden;
}
.card-icon  { font-size: 2rem; margin-bottom: 10px; line-height: 1; }
.card-title { font-size: 1.1rem; font-weight: 700; color: var(--text-color, #1e293b); margin-bottom: 6px;
              word-break: break-word; }
.card-desc  { font-size: 0.88rem; color: var(--text-color, #64748b); opacity: 0.75;
              line-height: 1.55; margin-bottom: 14px; word-break: break-word; }
.card-tags  { display: flex; flex-wrap: wrap; gap: 5px; overflow: hidden; }
.tag {
    background: rgba(37,99,235,0.1);
    color: #2563eb;
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 0.76rem;
    font-weight: 500;
    white-space: nowrap;
}
.tag-soon {
    background: rgba(22,163,74,0.1);
    color: #16a34a;
}
</style>
""", unsafe_allow_html=True)


# ── API Status Check ──────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=300)
def _check_api() -> str:
    try:
        result = fetch_iaea_data("Co-60")
        if result and result.get("source") == "IAEA LiveChart (live)":
            return "live"
    except Exception:
        pass
    return "fallback"

api_status = _check_api()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ☢️ Nuclear Source Toolkit")
    st.caption(f"v{APP_VERSION} · Updated {APP_UPDATED}")
    st.divider()

    st.markdown("**Quick Navigation**")
    st.page_link("pages/01_Procurement_Calculator.py", label="📦 Procurement Calculator")
    st.page_link("pages/02_Decay_Calculator.py",       label="📉 Decay Calculator")
    st.page_link("pages/03_Dose_Rate_Calculator.py",   label="☢️ Dose Rate Calculator")
    st.page_link("pages/04_Shielding_Calculator.py",   label="🛡️ Shielding Calculator")
    st.page_link("pages/05_Working_Time_Calculator.py",label="⏱️ Working Time Calculator")
    st.page_link("pages/06_Field_Reference_Card.py",   label="🔬 Field Reference Card")

    st.divider()
    if api_status == "live":
        st.success("🟢 IAEA LiveChart: Online")
    else:
        st.warning("🟡 IAEA API offline — using local fallback data")


# ── Header ────────────────────────────────────────────────────────────────────
hdr_left, hdr_right = st.columns([6, 1])
with hdr_left:
    st.title("☢️ Nuclear Source Toolkit")
    st.markdown(
        "Nuclear data is fetched live from the "
        "**[IAEA LiveChart of Nuclides](https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html)**, "
        "with a local reference table as fallback when the API is unavailable."
    )
with hdr_right:
    if api_status == "live":
        st.markdown(
            '<div style="text-align:right;padding-top:20px;">'
            '<span style="color:#16a34a;font-weight:600;font-size:0.95rem;">● API Live</span>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="text-align:right;padding-top:20px;">'
            '<span style="color:#d97706;font-weight:600;font-size:0.95rem;">● API Offline</span>'
            '</div>',
            unsafe_allow_html=True,
        )

st.divider()


# ── Card helpers ──────────────────────────────────────────────────────────────
def _tags(items: list[str], extra_class: str = "") -> str:
    return "".join(f'<span class="tag {extra_class}">{t}</span>' for t in items)

def tool_card(icon: str, title: str, desc: str, tags: list[str], page_path: str = "") -> str:
    inner = (
        f'<div class="tool-card">'
        f'<div class="card-icon">{icon}</div>'
        f'<div class="card-title">{title}</div>'
        f'<div class="card-desc">{desc}</div>'
        f'<div class="card-tags">{_tags(tags)}</div>'
        f'</div>'
    )
    if page_path:
        href = _page_slug(page_path)
        return (
            f'<a href="{href}" target="_self" '
            f'style="text-decoration:none;display:block;color:inherit;width:100%;max-width:100%;overflow:hidden;">'
            f'{inner}</a>'
        )
    return inner

def coming_soon_card(icon: str, title: str, desc: str, tags: list[str]) -> str:
    return (
        f'<div class="coming-soon-card">'
        f'<div class="card-icon">{icon}</div>'
        f'<div class="card-title" style="opacity:0.65;">{title}</div>'
        f'<div class="card-desc">{desc}</div>'
        f'<div class="card-tags">{_tags(tags, "tag-soon")}</div>'
        f'</div>'
    )


# ── Row 1 ─────────────────────────────────────────────────────────────────────
r1c1, r1c2 = st.columns(2, gap="large")
with r1c1:
    st.markdown(tool_card(
        "📦", "Procurement Calculator",
        "Calculate the activity to order today so the source arrives at the required activity "
        "on the delivery date, accounting for decay during transit.",
        ["Any isotope", "Live IAEA data", "Multi-source inventory", "Procurement memo"],
        page_path="pages/01_Procurement_Calculator.py",
    ), unsafe_allow_html=True)

with r1c2:
    st.markdown(tool_card(
        "📉", "Decay Calculator",
        "Track and forecast source activity over time from a known reference measurement. "
        "Query activity at any future date and visualise the full decay curve.",
        ["Decay curve", "Point query", "Milestone table", "CSV export"],
        page_path="pages/02_Decay_Calculator.py",
    ), unsafe_allow_html=True)

st.divider()

# ── Row 2 ─────────────────────────────────────────────────────────────────────
r2c1, r2c2 = st.columns(2, gap="large")
with r2c1:
    st.markdown(tool_card(
        "☢️", "Dose Rate Calculator",
        "Estimate dose rate from gamma and neutron sources using the point-source inverse "
        "square law, with safe working distance indicators and ICRP 103 limit lines.",
        ["Gamma & neutron", "Am-Be · Cf-252", "ICRP 103 / IAEA BSS", "Dose vs distance plot"],
        page_path="pages/03_Dose_Rate_Calculator.py",
    ), unsafe_allow_html=True)

with r2c2:
    st.markdown(tool_card(
        "🛡️", "Shielding Calculator",
        "Calculate the required shielding thickness to reduce dose rate below regulatory "
        "limits for gamma and neutron sources across common materials.",
        ["Pb · concrete · water · steel", "Neutron shielding", "Material comparison", "Shielding report"],
        page_path="pages/04_Shielding_Calculator.py",
    ), unsafe_allow_html=True)

st.divider()

# ── Row 3 ─────────────────────────────────────────────────────────────────────
r3c1, r3c2 = st.columns(2, gap="large")
with r3c1:
    st.markdown(tool_card(
        "⏱️", "Working Time Calculator",
        "Calculate the maximum time a worker can spend near a source without exceeding annual "
        "dose limits, with ALARA design goals and working time vs. distance tables.",
        ["Occupational limits", "ICRP 103", "Occupancy factor", "ALARA goal"],
        page_path="pages/05_Working_Time_Calculator.py",
    ), unsafe_allow_html=True)

with r3c2:
    st.markdown(tool_card(
        "🔬", "Field Reference Card",
        "Generate a printable quick-reference card for any gamma isotope: half-life, "
        "dose constant, HVL shielding data, principal gamma emissions, and safe working "
        "distances — everything a technician needs in the field.",
        ["Dose constant", "HVL shielding", "Gamma lines", "IAEA category", "Print-ready"],
        page_path="pages/06_Field_Reference_Card.py",
    ), unsafe_allow_html=True)

st.divider()

# ── Footer ────────────────────────────────────────────────────────────────────
st.caption(
    f"**v{APP_VERSION}** · Last updated {APP_UPDATED}  ·  "
    "**Disclaimer:** Independent tool for educational and laboratory use — not an official IAEA product.  "
    "Data sourced from [IAEA NDS](https://nds.iaea.org)."
)
