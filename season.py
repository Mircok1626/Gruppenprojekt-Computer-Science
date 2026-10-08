"""Setzt die Formeln 1–4 zu einer Saison-Auswertung zusammen.

Eingabe: einheitliches Tages-DataFrame (siehe ``core/weather.py``) ab 1.1.
Ausgabe: Infektionsliste mit Inkubationsende, «spritzen bis» und Status.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from core import config, infection, incubation, protection


@dataclass
class Season:
    daily: pd.DataFrame          # Tageswerte inkl. temp_sum, infection_level, is_forecast
    infections: pd.DataFrame     # eine Zeile pro Infektionstag
    germination: date | None     # Keimbereitschaft
    today: date


def build_season(daily: pd.DataFrame, today: date, spray_dates: list[date] | None = None,
                 method: str = "A") -> Season:
    """Berechnet Keimbereitschaft, Infektionen, Inkubation und Status.

    Args:
        daily: Tageswerte ab 1.1., sortiert; Zeilen nach ``today`` gelten als Prognose.
        today: Stichtag (echtes Datum oder Simulationsdatum im Demo-Modus).
        spray_dates: Spritzdaten der gewählten Parzelle.
        method: Inkubationsmethode "A" (Agrometeo, sonst B) oder "B".
    """
    spray_dates = spray_dates or []
    daily = daily.sort_values("date").reset_index(drop=True)
    daily["is_forecast"] = daily["date"] > pd.Timestamp(today)

    # Keimbereitschaft nur aus Daten bis heute + Prognose (alles, was bekannt ist)
    germ = infection.germination_date(daily)
    daily = infection.add_infections(daily, germ)

    rows = []
    for _, r in daily[daily["infection_level"] > 0].iterrows():
        inf_day = r["date"].date()
        ag_end = r.get("incubation_end_ag") if method == "A" else None
        inc_end, estimated = incubation.incubation_end(inf_day, daily, method=method,
                                                       agrometeo_end=ag_end)
        deadline = incubation.spray_deadline(inf_day, inc_end) if inc_end else None
        status = protection.infection_status(inf_day, deadline, spray_dates, today)
        rows.append({
            "date": inf_day,
            "level": int(r["infection_level"]),
            "symbol": config.INFECTION_SYMBOLS[int(r["infection_level"])],
            "degree_hours_wet": r["degree_hours_wet"],
            "inc_end": inc_end,
            "inc_estimated": estimated,
            "deadline": deadline,
            "is_forecast": bool(r["is_forecast"]),
            "status": status if not r["is_forecast"] else "Prognose",
        })
    infections = pd.DataFrame(rows, columns=["date", "level", "symbol", "degree_hours_wet",
                                             "inc_end", "inc_estimated", "deadline",
                                             "is_forecast", "status"])
    return Season(daily=daily, infections=infections, germination=germ, today=today)


def running_incubations(season: Season) -> pd.DataFrame:
    """Infektionen bis heute, deren Inkubation noch nicht abgeschlossen ist."""
    inf = season.infections
    if inf.empty:
        return inf
    t = season.today
    mask = (~inf["is_forecast"]) & inf["inc_end"].apply(lambda d: d is None or d >= t)
    return inf[mask]


def open_alarms(season: Season) -> pd.DataFrame:
    """Unbehandelte Infektionen, deren «spritzen bis» heute oder später ist."""
    inf = running_incubations(season)
    return inf[inf["status"] == "offen"].sort_values("deadline")
