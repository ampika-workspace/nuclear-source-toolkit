import requests
import pandas as pd
from io import StringIO

# IAEA-published reference values — used as fallback when API is unreachable
ISOTOPE_FALLBACK = {
    'Am-241': {'half_life_sec': 1.364e10, 'half_life_hum': '432.2 y',  'decay_mode': 'α'},
    'Cf-252': {'half_life_sec': 8.347e7,  'half_life_hum': '2.645 y',  'decay_mode': 'SF/α'},
    'Cs-137': {'half_life_sec': 9.493e8,  'half_life_hum': '30.08 y',  'decay_mode': 'β⁻'},
    'Co-60':  {'half_life_sec': 1.663e8,  'half_life_hum': '5.271 y',  'decay_mode': 'β⁻'},
    'Ba-133': {'half_life_sec': 3.317e8,  'half_life_hum': '10.51 y',  'decay_mode': 'EC'},
    'Ir-192': {'half_life_sec': 6.379e6,  'half_life_hum': '73.83 d',  'decay_mode': 'β⁻'},
    'Sr-90':  {'half_life_sec': 9.118e8,  'half_life_hum': '28.90 y',  'decay_mode': 'β⁻'},
    'Na-22':  {'half_life_sec': 8.214e7,  'half_life_hum': '2.603 y',  'decay_mode': 'β⁺'},
    'Ra-226': {'half_life_sec': 5.049e10, 'half_life_hum': '1600 y',   'decay_mode': 'α'},
    'Pu-239': {'half_life_sec': 7.610e11, 'half_life_hum': '24110 y',  'decay_mode': 'α'},
    'Mn-54':  {'half_life_sec': 2.697e7,  'half_life_hum': '312.2 d',  'decay_mode': 'EC'},
    'Fe-55':  {'half_life_sec': 8.659e7,  'half_life_hum': '2.744 y',  'decay_mode': 'EC'},
    'Ge-68':  {'half_life_sec': 2.341e7,  'half_life_hum': '270.9 d',  'decay_mode': 'EC'},
    'Y-88':   {'half_life_sec': 9.210e6,  'half_life_hum': '106.6 d',  'decay_mode': 'β⁺'},
    'Eu-152': {'half_life_sec': 4.273e8,  'half_life_hum': '13.54 y',  'decay_mode': 'EC/β⁻'},
}

COMMON_ISOTOPES = sorted(ISOTOPE_FALLBACK.keys())

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}


def _api_urls(api_nuc: str, ele: str, num: str) -> list:
    return [
        f"https://nds.iaea.org/relnsd/vcharthtml/api/v1/metatable/ground_states?nuc={api_nuc}",
        f"https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides={ele}{num}",
        f"https://nds.iaea.org/relnsd/v1/data?fields=ground_states&nuclides={api_nuc}",
    ]


def fetch_iaea_data(isotope_label: str) -> dict:
    """
    Fetch ground-state nuclear data from IAEA LiveChart API.
    Tries multiple URL formats, falls back to local reference table.
    Returns dict with half_life_sec, half_life_hum, decay_mode, source.
    Returns None if isotope is not found anywhere.
    """
    normalised = isotope_label.strip()
    clean      = normalised.replace('-', '').lower()
    num        = ''.join(filter(str.isdigit, clean))
    ele        = ''.join(filter(str.isalpha, clean)).capitalize()
    api_nuc    = f"{num}{ele}"

    for url in _api_urls(api_nuc, ele, num):
        try:
            r = requests.get(url, headers=_HEADERS, timeout=10)
            if r.status_code == 200 and r.text.strip():
                df = pd.read_csv(StringIO(r.text))
                if not df.empty and 'half_life_sec' in df.columns:
                    return {
                        'half_life_sec': float(df['half_life_sec'].iloc[0]),
                        'half_life_hum': str(df['half_life_hum'].iloc[0]),
                        'decay_mode':    str(df['decay_1'].iloc[0]),
                        'source':        'IAEA LiveChart (live)',
                    }
        except Exception:
            pass

    if normalised in ISOTOPE_FALLBACK:
        return {**ISOTOPE_FALLBACK[normalised], 'source': 'Local reference table'}

    return None