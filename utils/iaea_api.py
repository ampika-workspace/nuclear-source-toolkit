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

# Atomic number → element symbol lookup
ELEMENT_SYMBOLS = {
    1: 'H',  2: 'He', 3: 'Li', 4: 'Be', 5: 'B',  6: 'C',  7: 'N',  8: 'O',
    9: 'F',  10: 'Ne',11: 'Na',12: 'Mg',13: 'Al',14: 'Si',15: 'P', 16: 'S',
    17: 'Cl',18: 'Ar',19: 'K', 20: 'Ca',21: 'Sc',22: 'Ti',23: 'V', 24: 'Cr',
    25: 'Mn',26: 'Fe',27: 'Co',28: 'Ni',29: 'Cu',30: 'Zn',31: 'Ga',32: 'Ge',
    33: 'As',34: 'Se',35: 'Br',36: 'Kr',37: 'Rb',38: 'Sr',39: 'Y', 40: 'Zr',
    41: 'Nb',42: 'Mo',43: 'Tc',44: 'Ru',45: 'Rh',46: 'Pd',47: 'Ag',48: 'Cd',
    49: 'In',50: 'Sn',51: 'Sb',52: 'Te',53: 'I', 54: 'Xe',55: 'Cs',56: 'Ba',
    57: 'La',58: 'Ce',59: 'Pr',60: 'Nd',61: 'Pm',62: 'Sm',63: 'Eu',64: 'Gd',
    65: 'Tb',66: 'Dy',67: 'Ho',68: 'Er',69: 'Tm',70: 'Yb',71: 'Lu',72: 'Hf',
    73: 'Ta',74: 'W', 75: 'Re',76: 'Os',77: 'Ir',78: 'Pt',79: 'Au',80: 'Hg',
    81: 'Tl',82: 'Pb',83: 'Bi',84: 'Po',85: 'At',86: 'Rn',87: 'Fr',88: 'Ra',
    89: 'Ac',90: 'Th',91: 'Pa',92: 'U', 93: 'Np',94: 'Pu',95: 'Am',96: 'Cm',
    97: 'Bk',98: 'Cf',99: 'Es',100:'Fm',101:'Md',102:'No',103:'Lr',104:'Rf',
    105:'Db',106:'Sg',107:'Bh',108:'Hs',109:'Mt',110:'Ds',111:'Rg',112:'Cn',
    113:'Nh',114:'Fl',115:'Mc',116:'Lv',117:'Ts',118:'Og',
}

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


def _parse_isotope(isotope_label: str) -> tuple:
    """Returns (normalised, num, ele, api_nuc)."""
    normalised = isotope_label.strip()
    clean      = normalised.replace('-', '').lower()
    num        = ''.join(filter(str.isdigit, clean))
    ele        = ''.join(filter(str.isalpha, clean)).capitalize()
    return normalised, num, ele, f"{num}{ele}"


def daughter_label(z: int, a: int, decay_mode: str) -> str | None:
    """Infer daughter nuclide label (e.g. 'Ba-137') from parent Z, A and primary decay mode."""
    dm = decay_mode
    if 'SF' in dm:
        return 'Multiple fission products'
    if 'α' in dm or dm == 'A':
        dz, da = z - 2, a - 4
    elif 'β⁻' in dm or dm == 'B-':
        dz, da = z + 1, a
    elif 'β⁺' in dm or 'EC' in dm or dm in ('B+', 'EC'):
        dz, da = z - 1, a
    elif 'IT' in dm:
        dz, da = z, a
    else:
        return None
    sym = ELEMENT_SYMBOLS.get(dz)
    return f"{sym}-{da}" if sym else None


def fetch_iaea_data(isotope_label: str) -> dict:
    """
    Fetch ground-state nuclear data from IAEA LiveChart API.
    Tries multiple URL formats, falls back to local reference table.
    Returns dict with half_life_sec, half_life_hum, decay_mode, source.
    Returns None if isotope is not found anywhere.
    """
    normalised, num, ele, api_nuc = _parse_isotope(isotope_label)

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


def fetch_nuclide_properties(isotope_label: str) -> dict | None:
    """
    Fetch detailed ground-state nuclear properties from IAEA LiveChart API.
    Returns dict with Z, A, N, atomic mass, spin-parity, binding energy,
    all decay modes with branching ratios, daughter nuclide, and Q-values.
    Returns None if not found.
    """
    normalised, num, ele, api_nuc = _parse_isotope(isotope_label)

    for url in _api_urls(api_nuc, ele, num):
        try:
            r = requests.get(url, headers=_HEADERS, timeout=10)
            if r.status_code == 200 and r.text.strip():
                df = pd.read_csv(StringIO(r.text))
                if df.empty:
                    continue

                row = df.iloc[0]

                def sg(col, default=None):
                    if col not in df.columns:
                        return default
                    v = row[col]
                    return default if (isinstance(v, float) and pd.isna(v)) else v

                z = int(sg('z', 0))
                n = int(sg('n', 0))
                a = z + n

                decay_modes = []
                for i in range(1, 5):
                    mode = sg(f'decay_{i}')
                    br   = sg(f'vd_{i}')
                    if mode and str(mode) not in ('nan', ''):
                        try:
                            br_val = round(float(br), 2) if br is not None and str(br) != 'nan' else None
                        except (ValueError, TypeError):
                            br_val = None
                        decay_modes.append({'mode': str(mode), 'branching_pct': br_val})

                primary_mode = decay_modes[0]['mode'] if decay_modes else None
                d_label      = daughter_label(z, a, primary_mode) if primary_mode else None

                def safe_float(col):
                    v = sg(col)
                    try:
                        return round(float(v), 6) if v is not None else None
                    except (ValueError, TypeError):
                        return None

                return {
                    'z':                 z,
                    'n':                 n,
                    'a':                 a,
                    'symbol':            str(sg('symbol', ele)).capitalize(),
                    'spin_parity':       str(sg('jp') or sg('spin') or '—'),
                    'atomic_mass_u':     safe_float('atomic_mass'),
                    'mass_excess_keV':   safe_float('mass_excess'),
                    'binding_keV_per_A': safe_float('binding'),
                    'half_life_sec':     sg('half_life_sec'),
                    'half_life_hum':     str(sg('half_life_hum', '—')),
                    'decay_modes':       decay_modes,
                    'daughter':          d_label,
                    'qa_keV':            safe_float('qa'),
                    'qbm_keV':           safe_float('qbm'),
                    'qec_keV':           safe_float('qec'),
                    'abundance':         sg('abundance'),
                    'source':            'IAEA LiveChart (live)',
                }
        except Exception:
            pass

    return None


def fetch_decay_radiations(isotope_label: str, rad_type: str) -> pd.DataFrame | None:
    """
    Fetch decay radiation data from IAEA LiveChart API.
    rad_type: 'g' (gamma), 'bm' (beta-), 'bp' (beta+/EC), 'x' (x-ray), 'a' (alpha)
    Returns a cleaned DataFrame or None if not available.
    """
    _, num, ele, _ = _parse_isotope(isotope_label)

    urls = [
        f"https://nds.iaea.org/relnsd/v1/data?fields=decay_rads&nuclides={ele}{num}&rad_types={rad_type}",
        f"https://nds.iaea.org/relnsd/v1/data?fields=decay_rads&nuclides={num}{ele}&rad_types={rad_type}",
    ]

    for url in urls:
        try:
            r = requests.get(url, headers=_HEADERS, timeout=15)
            if r.status_code == 200 and r.text.strip():
                df = pd.read_csv(StringIO(r.text))
                if not df.empty:
                    return df
        except Exception:
            pass

    return None
