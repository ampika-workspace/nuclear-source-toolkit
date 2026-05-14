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

col1, col2 = st.columns(2, gap="large")

with col1:
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

with col2:
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
st.caption(
    "**Disclaimer:** This tool is an independent implementation for educational "
    "and laboratory use. It is not an official product of the IAEA. "
    "Data sourced from [IAEA NDS](https://nds.iaea.org)."
)