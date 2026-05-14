# ☢️ Nuclear Source Toolkit

A web-based toolkit for managing radioactive sources, built with [Streamlit](https://streamlit.io) and powered by live nuclear data from the [IAEA LiveChart of Nuclides](https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html).

> Built by a Radiation Safety Officer for practical, day-to-day source management tasks.

---

## Features

### 📦 Procurement Calculator
Calculate the activity you need to **order today** so that a source arrives at your required activity on the delivery date, accounting for radioactive decay during transit.

- Supports any isotope via live IAEA data
- Configurable order & delivery dates
- Multi-source inventory table
- Downloadable results (CSV) and procurement memo (TXT)

### 📉 Decay Calculator
Track and forecast source activity over time from a known reference measurement.

- Activity at any specific future or past date (back-calculation supported)
- Interactive decay curve with milestone markers
- Milestone table (1 y, 3 y, 5 y, 10 y, …)
- Downloadable results (CSV)

### ☢️ Dose Rate Calculator
Estimate dose rate from gamma and neutron sources using the point-source inverse square law.

- Supports gamma isotopes (Co-60, Cs-137, Ir-192, Am-241, and more)
- Supports neutron sources: Am-Be and Cf-252 (neutron + gamma components)
- Safe working distance indicators based on ICRP 103 / IAEA BSS dose limits
- Dose rate vs distance plot (log scale) with occupational/public limit lines
- Downloadable dose rate table (CSV)

### 🛡️ Shielding Calculator
Calculate the required shielding thickness to reduce dose rate below regulatory limits.

- Gamma shielding via Half-Value Layer (HVL) for Lead, Steel, Concrete, Water
- Neutron shielding via relaxation length (λ) for HDPE, Concrete, Water, Paraffin
- Material comparison bar chart and transmission curve (log scale)
- PHITS simulation input file generator
- Downloadable shielding report (CSV)

### ⏱️ Working Time Calculator
Calculate the maximum time a worker can spend near a source without exceeding annual dose limits.

- Supports both activity-based and direct dose rate input
- ICRP 103 / IAEA BSS occupational, supervised area, and public dose limits
- Occupancy factor adjustment
- ALARA design goal (1/10 of limit)
- Working time vs distance table
- Downloadable summary (TXT)

### 🔬 Field Reference Card
Generate a printable quick-reference card for any isotope for use in the field.

- Half-life, decay mode, dose constant (Γ), 1 m dose rate
- HVL shielding data for Lead, Steel, Concrete, Water
- Principal gamma emission lines fetched live from IAEA LiveChart
- Safe working distances per ICRP 103 dose limits
- IAEA source category (RS-G-1.9) based on A/D ratio
- Downloadable text summary; print-ready via browser Ctrl+P

---

## Data Sources

| Data | Source |
|------|--------|
| Half-life, decay mode | IAEA LiveChart API (live) with local fallback |
| Gamma emission lines | IAEA LiveChart API (live) |
| Gamma dose constants Γ | Delacroix et al. / IAEA Safety Reports No. 37 |
| HVL shielding values | NCRP-49 / IAEA Safety Reports No. 37 / Shultis & Faw |
| Dose limits | ICRP 103 / IAEA BSS |
| Source categories | IAEA RS-G-1.9 / SS No. 23-G |

This tool is an independent implementation and is **not an official product of the IAEA**.

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/ampika-workspace/nuclear-source-toolkit.git
cd nuclear-source-toolkit
pip install -r requirements.txt
```

### Run locally

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Deployment

This app is deployable for free on **Streamlit Community Cloud**:

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and set the main file to `app.py`
4. Click Deploy

---

## Project Structure

```
nuclear-source-toolkit/
├── app.py                               # Home page with tool cards
├── pages/
│   ├── 01_Procurement_Calculator.py
│   ├── 02_Decay_Calculator.py
│   ├── 03_Dose_Rate_Calculator.py
│   ├── 04_Shielding_Calculator.py
│   ├── 05_Working_Time_Calculator.py
│   └── 06_Field_Reference_Card.py
├── utils/
│   ├── __init__.py
│   ├── constants.py                     # Shared physics constants & helper functions
│   ├── iaea_api.py                      # IAEA LiveChart API client + fallback table
│   └── decay_math.py                    # Decay calculations and unit conversions
├── requirements.txt
└── README.md
```

---

## Disclaimer

This tool is intended for educational and laboratory use. Always verify critical values against official sources and your institution's radiation protection programme. Nuclear data is sourced from [IAEA NDS](https://nds.iaea.org).

---

## License

MIT License — feel free to use, modify, and share.
