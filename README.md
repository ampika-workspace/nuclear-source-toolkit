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

- Activity at any specific future or past date
- Interactive decay curve with milestone markers
- Milestone table (1 y, 3 y, 5 y, 10 y, ...)
- Downloadable results (CSV)

---

## Data Source

Nuclear data (half-lives, decay modes) is fetched live from the **IAEA LiveChart API**:

```
https://nds.iaea.org/relnsd/vcharthtml/VChartHTML.html
```

A local reference table of common isotopes is used as a fallback when the API is unavailable. This tool is an independent implementation and is **not an official product of the IAEA**.

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
├── app.py                          # Home page
├── pages/
│   ├── 01_Procurement_Calculator.py
│   └── 02_Decay_Calculator.py
├── utils/
│   ├── iaea_api.py                 # IAEA LiveChart API client + fallback table
│   └── decay_math.py               # Decay calculations and unit conversions
├── requirements.txt
└── README.md
```

---

## Disclaimer

This tool is intended for educational and laboratory use. Always verify critical values against official sources and your institution's procedures. Nuclear data is sourced from [IAEA NDS](https://nds.iaea.org).

---

## License

MIT License — feel free to use, modify, and share.
