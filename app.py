import streamlit as st

st.set_page_config(
    page_title="Nuclear Source Toolkit",
    page_icon="☢️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("☢️ Nuclear Source Toolkit")
st.markdown("""
Nuclear data is fetched live from the **[IAEA LiveChart of Nuclides](https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html)**,
with a local reference table as fallback when the API is unavailable.
""")

st.divider()

row1_col1, row1_col2 = st.columns(2, gap="large")

with row1_col1:
    st.subheader("📦 Procurement Calculator")
    st.markdown("""
    Calculate the activity you need to **order today** so that the source
    arrives at your required activity on the delivery date,
    accounting for radioactive decay during transit.

    - Any isotope via live IAEA data
    - Configurable order & delivery dates
    - Multi-source inventory table
    - Downloadable results & procurement memo
    """)

with row1_col2:
    st.subheader("📉 Decay Calculator")
    st.markdown("""
    Track and forecast source activity over time
    from a known reference measurement.

    - Activity at any specific future date
    - Interactive decay curve
    - Milestone table (1 y, 5 y, 10 y, ...)
    - Downloadable results
    """)

st.divider()

row2_col1, row2_col2 = st.columns(2, gap="large")

with row2_col1:
    st.subheader("☢️ Dose Rate Calculator")
    st.markdown("""
    Estimate dose rate from **gamma** and **neutron** sources using the
    point-source inverse square law.

    - Gamma isotopes (Co-60, Cs-137, Ir-192, Am-241, and more)
    - Neutron sources: Am-Be and Cf-252 (neutron + gamma components)
    - Detailed nuclear properties from IAEA LiveChart
    - Safe working distance indicators (ICRP 103 / IAEA BSS)
    - Dose rate vs distance plot with occupational/public limit lines
    """)

with row2_col2:
    st.subheader("🛡️ Shielding Calculator")
    st.markdown("""
    Calculate the required shielding thickness to reduce dose rate
    below regulatory limits for gamma and neutron sources.

    - Gamma shielding: lead, concrete, water, steel
    - Neutron shielding: polyethylene, concrete, water
    - Material comparison chart
    - Downloadable shielding summary
    """)

st.divider()

row3_col1, row3_col2 = st.columns(2, gap="large")

with row3_col1:
    st.subheader("⏱️ Working Time Calculator")
    st.markdown("""
    Calculate the **maximum time** a worker can spend near a source
    without exceeding annual dose limits.

    - Calculates from activity or direct dose rate entry
    - Occupational, supervised area, and public dose limits (ICRP 103)
    - Adjustable occupancy factor
    - Working time vs. distance table
    - ALARA design goal (1/10 of limit)
    """)

with row3_col2:
    st.markdown("")  # placeholder for future page

st.divider()
st.caption(
    "**Disclaimer:** This tool is an independent implementation for educational "
    "and laboratory use. It is not an official product of the IAEA. "
    "Data sourced from [IAEA NDS](https://nds.iaea.org)."
)
