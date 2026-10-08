from datetime import date

import pandas as pd

from core import incubation


def _daily(temp, days=30, start="2026-05-01"):
    return pd.DataFrame({"date": pd.date_range(start, periods=days), "t_mean": [temp] * days})


def test_spray_deadline_example():
    assert incubation.spray_deadline(date(2026, 5, 7), date(2026, 5, 20)) == date(2026, 5, 17)


def test_method_b_constant_temperature():
    # 15 °C -> 7 pro Tag -> 70 nach 10 Tagen (Infektionstag mitgezählt)
    end, estimated = incubation.incubation_end(date(2026, 5, 1), _daily(15.0), method="B")
    assert end == date(2026, 5, 10)
    assert not estimated


def test_method_a_uses_agrometeo_value():
    end, estimated = incubation.incubation_end(date(2026, 5, 7), _daily(15.0), method="A",
                                               agrometeo_end=pd.Timestamp("2026-05-20"))
    assert end == date(2026, 5, 20)
    assert not estimated


def test_method_a_falls_back_to_b():
    end, _ = incubation.incubation_end(date(2026, 5, 1), _daily(15.0), method="A",
                                       agrometeo_end=pd.NaT)
    assert end == date(2026, 5, 10)


def test_extrapolation_beyond_data():
    end, estimated = incubation.incubation_end(date(2026, 5, 1), _daily(15.0, days=5), method="B")
    assert estimated
    assert end == date(2026, 5, 10)
