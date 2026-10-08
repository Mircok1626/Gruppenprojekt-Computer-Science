"""Formel 1 + 2: Temperatursumme, Keimbereitschaft, Gradstunden, Infektionsstufe."""
from __future__ import annotations

from datetime import date

import pandas as pd

from core import config


def temperature_sum(daily: pd.DataFrame, base: float = config.TEMP_BASE) -> pd.Series:
    """Kumulierte Temperatursumme Σ max(Tmittel - base, 0) ab dem ersten Tag.

    ``daily`` muss nach Datum sortiert sein und am 1.1. beginnen.
    Beispiel: Tag mit 14,0 °C -> +6; Tag mit 7,6 °C -> +0.
    """
    excess = (daily["t_mean"].fillna(base) - base).clip(lower=0)
    return excess.cumsum()


def germination_date(daily: pd.DataFrame,
                     threshold: float = config.GERMINATION_THRESHOLD) -> date | None:
    """Erster Tag, an dem die Temperatursumme ``threshold`` erreicht (Keimbereitschaft).

    Zizers 2026 -> 26.04.2026. Gibt ``None`` zurück, wenn noch nicht erreicht.
    """
    tsum = temperature_sum(daily)
    reached = daily.loc[tsum >= threshold, "date"]
    if reached.empty:
        return None
    return pd.Timestamp(reached.iloc[0]).date()


def degree_hours_wet(hourly_temps, wet_flags) -> float:
    """Gradstunden bei Blattnässe: Σ Temperatur aller nassen Stunden.

    Beispiel: 10 nasse Stunden à 12 °C -> 120.
    """
    return float(sum(max(t, 0.0) for t, w in zip(hourly_temps, wet_flags) if w))


def infection_level(degree_hours: float) -> int:
    """Infektionsstufe aus Gradstunden bei Blattnässe.

    Regel aus der Analyse der Agrometeo-Tabelle Zizers 2026
    (43 von 43 Infektionen erkannt, 5 Fehlalarme).

    Returns:
        0 = keine, 1 = gering (!), 2 = mittel (!!), 3 = stark (!!!)
    """
    low, mid, high = config.INFECTION_THRESHOLDS
    if degree_hours >= high:
        return 3
    if degree_hours >= mid:
        return 2
    if degree_hours >= low:
        return 1
    return 0


def add_infections(daily: pd.DataFrame, germ: date | None) -> pd.DataFrame:
    """Ergänzt ``temp_sum`` und ``infection_level`` (0 vor der Keimbereitschaft)."""
    out = daily.copy()
    out["temp_sum"] = temperature_sum(out)
    levels = out["degree_hours_wet"].fillna(0).apply(infection_level)
    if germ is None:
        levels[:] = 0
    else:
        levels[out["date"] < pd.Timestamp(germ)] = 0
    out["infection_level"] = levels.astype(int)
    return out
