"""Spritzfenster-Ampel grün/gelb/rot pro Tag."""
from __future__ import annotations

import math

import pandas as pd

from core import config

GREEN, YELLOW, RED = "grün", "gelb", "rot"
_RANK = {GREEN: 0, YELLOW: 1, RED: 2}


def _num(value) -> float | None:
    """NaN/None -> None, sonst float."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def day_status(day, settings: dict | None = None,
               heat_sensitive: bool = False) -> tuple[str, list[str]]:
    """Bewertet einen Prognosetag als Spritzfenster.

    Args:
        day: Zeile/Dict mit ``date``, ``rain_mm``, ``rain_6h_min``, ``wind_mean``, ``t_max``.
        settings: Grenzwerte (Standard: ``config.DEFAULT_SETTINGS``).
        heat_sensitive: True, wenn das gewählte Mittel bei Hitze heikel ist.

    Returns:
        (Status, Liste der Begründungen). Der schlechteste Grund bestimmt die Farbe.
        Beispiel: Sonntag -> rot; Regen in den 6 h nach dem Spritzen > 1 mm -> rot.
    """
    s = {**config.DEFAULT_SETTINGS, **(settings or {})}
    status, reasons = GREEN, []

    def worse(new: str, reason: str):
        nonlocal status
        reasons.append(reason)
        if _RANK[new] > _RANK[status]:
            status = new

    weekday = pd.Timestamp(day["date"]).weekday()
    if s["sunday_red"] and weekday == 6:
        worse(RED, "Sonntag")

    # Regen: bestes 6-h-Fenster, falls stündliche Daten vorhanden, sonst Tagessumme
    rain6 = _num(day.get("rain_6h_min"))
    rain = rain6 if rain6 is not None else _num(day.get("rain_mm"))
    label = "Regen in 6 h nach Spritzbeginn" if rain6 is not None else "Regen am Tag"
    if rain is not None:
        if rain > s["rain_red_mm"]:
            worse(RED, f"{label}: {rain:.1f} mm")
        elif rain >= s["rain_yellow_mm"]:
            worse(YELLOW, f"{label}: {rain:.1f} mm")

    wind = _num(day.get("wind_mean"))
    if wind is not None:
        if wind > s["wind_red_kmh"]:
            worse(RED, f"Wind {wind:.0f} km/h")
        elif wind >= s["wind_yellow_kmh"]:
            worse(YELLOW, f"Wind {wind:.0f} km/h")

    tmax = _num(day.get("t_max"))
    if heat_sensitive and tmax is not None:
        if tmax > s["heat_red_c"]:
            worse(RED, f"Hitze {tmax:.0f} °C (Mittel hitzeempfindlich)")
        elif tmax >= s["heat_yellow_c"]:
            worse(YELLOW, f"Warm {tmax:.0f} °C (Mittel hitzeempfindlich)")

    if not reasons:
        reasons.append("gute Bedingungen")
    return status, reasons
