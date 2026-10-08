"""Agrometeo/VitiMeteo-Plasmopara-Tabellen laden (Referenz und ML-Labels).

Die PDFs von agrometeo.ch wurden einmalig in CSV umgewandelt
(``data/processed/<station>_<jahr>.csv``). Agrometeo hat keine offizielle API;
das inoffizielle JSON-Backend nutzen wir höchstens als Bonus.

Spalten der CSV:
    datum, sporulation, sporangiendichte, infektion_staerke,
    inkubation_aktuell, inkubation_prognose, temp_min, temp_mittel, temp_max,
    niederschlag_mm, blattnaesse_std, gradstunden_bn, blattzahl,
    blattflaeche_cm2, aus_wettervorhersage
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from core import config

_DATE_RE = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.?\s*$")


def csv_path(year: int, station: str = "zizers") -> Path:
    return config.PROCESSED_DIR / f"{station.lower()}_{year}.csv"


def available_years(station: str = "zizers") -> list[int]:
    """Alle Jahre, für die eine Agrometeo-CSV vorhanden ist."""
    years = []
    for p in config.PROCESSED_DIR.glob(f"{station.lower()}_*.csv"):
        suffix = p.stem.split("_")[-1]
        if suffix.isdigit():
            years.append(int(suffix))
    return sorted(years)


def parse_incubation(value, row_date: pd.Timestamp) -> pd.Timestamp:
    """Wandelt «16.05.» in ein Datum um (Jahr aus der Zeile).

    Prozentwerte («79%») bedeuten «Inkubation zu x % abgelaufen» und liefern
    kein Datum (NaT). Liegt der Monat vor dem Infektionsmonat, ist es das
    Folgejahr (Jahreswechsel).
    """
    if not isinstance(value, str):
        return pd.NaT
    m = _DATE_RE.match(value)
    if not m:
        return pd.NaT
    day, month = int(m.group(1)), int(m.group(2))
    year = row_date.year + (1 if month < row_date.month else 0)
    try:
        return pd.Timestamp(year=year, month=month, day=day)
    except ValueError:
        return pd.NaT


def load_year(year: int, station: str = "zizers") -> pd.DataFrame:
    """Lädt eine Agrometeo-Jahrestabelle im einheitlichen Tagesformat."""
    raw = pd.read_csv(csv_path(year, station), dtype={"inkubation_aktuell": str,
                                                       "inkubation_prognose": str})
    df = pd.DataFrame()
    df["date"] = pd.to_datetime(raw["datum"])
    df["sporulation"] = raw["sporulation"].fillna(0).astype(int)
    df["sporangia_density"] = raw["sporangiendichte"]
    df["infection_level_ag"] = raw["infektion_staerke"].fillna(0).astype(int)
    df["incubation_end_ag"] = [
        parse_incubation(v, d) for v, d in zip(raw["inkubation_aktuell"], df["date"])
    ]
    df["t_min"] = raw["temp_min"]
    df["t_mean"] = raw["temp_mittel"]
    df["t_max"] = raw["temp_max"]
    df["rain_mm"] = raw["niederschlag_mm"].fillna(0.0)
    df["wet_hours"] = raw["blattnaesse_std"].fillna(0.0)
    df["degree_hours_wet"] = raw["gradstunden_bn"].fillna(0).astype(float)
    df["leaf_count"] = raw["blattzahl"]
    df["leaf_area_cm2"] = raw["blattflaeche_cm2"]
    df["is_forecast"] = raw["aus_wettervorhersage"].fillna(0).astype(int) == 1
    # Spalten, die nur Open-Meteo liefert, als leer anlegen
    for col in ["rain_hours", "rh90_hours", "dewpoint_spread", "wind_mean",
                "rain_6h_min", "best_start_hour"]:
        df[col] = np.nan
    df["source"] = np.where(df["is_forecast"], "Agrometeo (Prognose)", "Agrometeo (gemessen)")
    return df.sort_values("date").reset_index(drop=True)


def measured_only(df: pd.DataFrame) -> pd.DataFrame:
    """Nur gemessene Tage (ohne Agrometeo-Wettervorhersage), z. B. für Labels."""
    return df[~df["is_forecast"]].reset_index(drop=True)
