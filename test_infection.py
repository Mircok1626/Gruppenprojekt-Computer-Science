from datetime import date

import pandas as pd

from core import agrometeo, infection


def _daily(temps, start="2026-01-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=len(temps)), "t_mean": temps})


def test_temperature_sum_examples():
    tsum = infection.temperature_sum(_daily([14.0, 7.6]))
    assert list(tsum) == [6.0, 6.0]


def test_germination_zizers_2026():
    df = agrometeo.measured_only(agrometeo.load_year(2026))
    assert infection.germination_date(df) == date(2026, 4, 26)


def test_germination_not_reached():
    assert infection.germination_date(_daily([10.0] * 10)) is None


def test_degree_hours_wet():
    assert infection.degree_hours_wet([12.0] * 10, [True] * 10) == 120
    assert infection.degree_hours_wet([12.0, 15.0], [True, False]) == 12


def test_infection_level_examples():
    assert infection.infection_level(106) == 2
    assert infection.infection_level(242) == 3
    assert infection.infection_level(65) == 0
    assert infection.infection_level(70) == 1


def test_all_43_agrometeo_infections_2026_found():
    df = agrometeo.measured_only(agrometeo.load_year(2026))
    out = infection.add_infections(df, infection.germination_date(df))
    ref = out["infection_level_ag"] > 0
    own = out["infection_level"] > 0
    assert ref.sum() == 43
    assert (ref & own).sum() == 43       # alle erkannt
    assert (own & ~ref).sum() == 5       # 5 Fehlalarme
