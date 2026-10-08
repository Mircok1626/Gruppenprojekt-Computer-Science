"""Tagesfeatures für das Infektionsmodell.

Wichtig: Training und Vorhersage nutzen dieselben Open-Meteo-Größen
(geschätzte Blattnässe), nicht die gemessenen Agrometeo-Werte – sonst lernt
das Modell etwas, das in der Prognose gar nicht verfügbar ist.
"""
from __future__ import annotations

import pandas as pd

from core import infection

FEATURES = [
    "t_min", "t_mean", "t_max",
    "rain_mm", "rain_hours", "rh90_hours",
    "wet_hours", "degree_hours_wet", "dewpoint_spread",
    "temp_sum", "rain_3d", "doy",
]

FEATURE_LABELS = {
    "t_min": "Tmin", "t_mean": "Tmittel", "t_max": "Tmax",
    "rain_mm": "Regen (mm)", "rain_hours": "Std. mit Regen",
    "rh90_hours": "Std. mit Feuchte ≥ 90 %", "wet_hours": "Std. Blattnässe (geschätzt)",
    "degree_hours_wet": "Gradstunden BN (geschätzt)", "dewpoint_spread": "Taupunkt-Differenz",
    "temp_sum": "Temperatursumme seit 1.1.", "rain_3d": "Regen letzte 3 Tage",
    "doy": "Tag im Jahr",
}


def build_features(daily: pd.DataFrame) -> pd.DataFrame:
    """Berechnet alle Features für ein lückenloses, sortiertes Tages-DataFrame ab 1.1.

    Gibt ``date`` + ``FEATURES`` zurück. Zeilen ohne Open-Meteo-Werte enthalten NaN.
    """
    d = daily.sort_values("date").reset_index(drop=True).copy()
    if "temp_sum" not in d:
        d["temp_sum"] = infection.temperature_sum(d)
    d["rain_3d"] = d["rain_mm"].fillna(0).shift(1).rolling(3, min_periods=1).sum().fillna(0)
    d["doy"] = d["date"].dt.dayofyear
    return d[["date"] + FEATURES]
