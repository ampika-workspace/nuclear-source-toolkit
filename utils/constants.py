import numpy as np

CI_TO_MBQ = 37000.0  # 1 Ci = 37,000 MBq

# Gamma dose rate constants Γ (μSv·m²·h⁻¹·MBq⁻¹) — Delacroix et al. / IAEA Safety Reports No. 37
GAMMA_DOSE_CONSTANT = {
    'Am-241': 0.0199,
    'Ba-133': 0.0819,
    'Co-60':  0.3059,
    'Cs-137': 0.0965,
    'Eu-152': 0.1697,
    'Ge-68':  0.1736,
    'Ir-192': 0.1108,
    'Mn-54':  0.1242,
    'Na-22':  0.3219,
    'Pu-239': 0.0017,
    'Ra-226': 0.2387,
    'Y-88':   0.3288,
}

NEUTRON_SOURCES = {
    'Am-Be': {
        'parent_isotope':        'Am-241',
        'neutron_yield_per_MBq': 65.0,
        'h_phi_pSv_cm2':         391.0,
        'mean_energy_MeV':       4.5,
        'gamma_dose_constant':   0.0199,
        'neutron_origin': (
            "Neutrons are produced by the **⁹Be(α,n)¹²C** reaction. "
            "Alpha particles emitted from **Am-241** decay strike beryllium-9 nuclei, "
            "releasing neutrons with a broad energy spectrum (mean ~4.5 MeV)."
        ),
        'gamma_origin': (
            "**Am-241** simultaneously emits a **59.5 keV gamma ray** with every alpha decay. "
            "This is an intrinsic property of Am-241 — not from neutron interactions. "
            "Although low energy, the high activity of the Am-241 matrix makes this "
            "gamma contribution significant and must not be ignored in dose assessments."
        ),
        'note': 'Neutron yield ~65 n/s per MBq Am-241 (varies by source design ±10%)',
    },
    'Cf-252': {
        'parent_isotope':        'Cf-252',
        'neutron_yield_per_MBq': 116600.0,
        'h_phi_pSv_cm2':         385.0,
        'mean_energy_MeV':       2.35,
        'gamma_dose_constant':   0.0,
        'neutron_origin': (
            "Neutrons are produced by **spontaneous fission** of Cf-252. "
            "Each fission event releases on average **3.77 neutrons** with a "
            "Watt fission energy spectrum (mean ~2.35 MeV)."
        ),
        'gamma_origin': (
            "Cf-252 fission also produces **prompt fission gamma rays**, but their dose "
            "contribution is substantially lower than neutrons at typical working distances "
            "and is not included in this calculation. "
            "For precise assessments, Monte Carlo simulation (PHITS/MCNP) is recommended."
        ),
        'note': 'Spontaneous fission source; yield = 2.314×10⁶ n/s/μg',
    },
}

# ICRP 103 / IAEA BSS instantaneous dose rate limits (μSv/h), assuming 2000 working h/yr
DOSE_LIMITS = {
    'Occupational (20 mSv/yr)':        {'uSvh': 10.0, 'color': 'red'},
    'Supervised area (6 mSv/yr)':       {'uSvh':  3.0, 'color': 'orange'},
    'Public / uncontrolled (1 mSv/yr)': {'uSvh':  0.5, 'color': 'green'},
}


def gamma_dr_from_activity(act_MBq: float, gamma_const: float, dist_m: float) -> float:
    """Point-source gamma dose rate (μSv/h) via inverse-square law."""
    return gamma_const * act_MBq / dist_m ** 2


def neutron_dr_from_activity(act_MBq: float, yield_per_MBq: float,
                              h_phi: float, dist_m: float) -> float:
    """Point-source neutron dose rate (μSv/h) using ICRP 74 fluence-to-dose conversion."""
    S    = act_MBq * yield_per_MBq
    r_cm = dist_m * 100
    return S * h_phi * 3600 / (4 * np.pi * r_cm ** 2 * 1e6)


# Gamma HVL data (cm, broad-beam) ─────────────────────────────────────────────
# Sources: NCRP-49, IAEA Safety Reports No. 37, Shultis & Faw
GAMMA_HVL = {
    'Am-241': {'dominant_keV':   59.5, 'Lead': 0.013, 'Steel': 0.17, 'Concrete': 1.30, 'Water':  3.30},
    'Ba-133': {'dominant_keV':  356.0, 'Lead': 0.20,  'Steel': 1.00, 'Concrete': 4.20, 'Water':  7.00},
    'Co-60':  {'dominant_keV': 1250.0, 'Lead': 1.20,  'Steel': 2.10, 'Concrete': 6.20, 'Water': 10.40},
    'Cs-137': {'dominant_keV':  662.0, 'Lead': 0.65,  'Steel': 1.60, 'Concrete': 4.80, 'Water':  7.40},
    'Eu-152': {'dominant_keV':  800.0, 'Lead': 0.50,  'Steel': 1.60, 'Concrete': 5.80, 'Water':  9.20},
    'Ge-68':  {'dominant_keV':  511.0, 'Lead': 0.40,  'Steel': 1.50, 'Concrete': 5.50, 'Water':  8.50},
    'Ir-192': {'dominant_keV':  380.0, 'Lead': 0.28,  'Steel': 1.20, 'Concrete': 3.80, 'Water':  6.00},
    'Mn-54':  {'dominant_keV':  835.0, 'Lead': 0.80,  'Steel': 2.00, 'Concrete': 6.50, 'Water': 10.50},
    'Na-22':  {'dominant_keV':  900.0, 'Lead': 0.40,  'Steel': 1.50, 'Concrete': 5.60, 'Water':  8.80},
    'Pu-239': {'dominant_keV':  414.0, 'Lead': 0.23,  'Steel': 1.10, 'Concrete': 4.00, 'Water':  6.50},
    'Ra-226': {'dominant_keV':  830.0, 'Lead': 1.30,  'Steel': 2.00, 'Concrete': 6.80, 'Water': 10.80},
    'Y-88':   {'dominant_keV': 1300.0, 'Lead': 1.15,  'Steel': 2.30, 'Concrete': 8.00, 'Water': 12.50},
}

# IAEA Dangerous Quantities — D values (TBq) per RS-G-1.9 / SS No. 23-G (2012)
IAEA_D_VALUES_TBQ = {
    'Am-241': 60.0,
    'Co-60':   3.0,
    'Cs-137': 10.0,
    'Ir-192': 10.0,
    'Pu-239': 60.0,
    'Ra-226':  0.4,
    'Cf-252': 20.0,
}
