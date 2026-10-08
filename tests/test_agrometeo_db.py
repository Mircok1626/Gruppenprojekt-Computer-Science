from datetime import date

import pandas as pd

from core import agrometeo
from db import database as db


def test_parse_incubation():
    d = pd.Timestamp("2026-05-07")
    assert agrometeo.parse_incubation("20.05.", d) == pd.Timestamp("2026-05-20")
    assert pd.isna(agrometeo.parse_incubation("79%", d))
    assert pd.isna(agrometeo.parse_incubation(None, d))
    assert agrometeo.parse_incubation("05.01.", pd.Timestamp("2025-12-28")) == pd.Timestamp("2026-01-05")


def test_load_year_2026():
    df = agrometeo.load_year(2026)
    row = df[df["date"] == pd.Timestamp("2026-05-07")].iloc[0]
    assert row["infection_level_ag"] == 2
    assert row["incubation_end_ag"] == pd.Timestamp("2026-05-20")
    assert row["degree_hours_wet"] == 106


def test_database_roundtrip(tmp_path):
    path = tmp_path / "test.db"
    db.init_db(path)
    parcels = db.list_parcels(path=path)
    assert len(parcels) == 1
    pid = int(parcels["id"].iloc[0])
    prod = int(db.list_products(path=path)["id"].iloc[0])
    db.add_spray(pid, date(2026, 5, 5), prod, "13-15", 300, 1.2, path=path)
    assert db.spray_dates(pid, path=path) == [date(2026, 5, 5)]
    db.set_setting("wind_red_kmh", 25, path=path)
    assert db.get_settings(path=path)["wind_red_kmh"] == 25
