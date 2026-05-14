CI_TO_BQ = 3.7e10  # 1 Ci = 3.7 × 10^10 Bq (exact definition)

UNITS = ['Ci', 'mCi', 'µCi', 'Bq', 'kBq', 'MBq', 'GBq', 'TBq']


def decay_factor(transit_days: float, half_life_days: float) -> float:
    return float(0.5 ** (transit_days / half_life_days))


def activity_at_time(a0_ci: float, transit_days: float, half_life_days: float) -> float:
    return a0_ci * decay_factor(transit_days, half_life_days)


def required_order_activity(a_delivery_ci: float, transit_days: float, half_life_days: float) -> float:
    return a_delivery_ci / decay_factor(transit_days, half_life_days)


def convert_to_ci(value: float, from_unit: str) -> float:
    """Convert any activity unit to Ci."""
    table = {
        'Ci':  value,
        'mCi': value * 1e-3,
        'µCi': value * 1e-6,
        'Bq':  value / CI_TO_BQ,
        'kBq': value * 1e3  / CI_TO_BQ,
        'MBq': value * 1e6  / CI_TO_BQ,
        'GBq': value * 1e9  / CI_TO_BQ,
        'TBq': value * 1e12 / CI_TO_BQ,
    }
    return table.get(from_unit, value)


def convert_activity(value_ci: float, to_unit: str) -> float:
    """Convert from Ci to any activity unit."""
    bq = value_ci * CI_TO_BQ
    table = {
        'Ci':  value_ci,
        'mCi': value_ci * 1e3,
        'µCi': value_ci * 1e6,
        'Bq':  bq,
        'kBq': bq / 1e3,
        'MBq': bq / 1e6,
        'GBq': bq / 1e9,
        'TBq': bq / 1e12,
    }
    return table.get(to_unit, value_ci)
