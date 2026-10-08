"""Formel 3: Inkubationsende und «spritzen bis»."""
from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd

from core import config


def _as_date(value) -> date | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date()


def incubation_end(inf_date: date, daily: pd.DataFrame, method: str = "B",
                   agrometeo_end=None, target: float = config.INCUBATION_SUM,
                   base: float = config.TEMP_BASE) -> tuple[date | None, bool]:
    """Berechnet das Ende der Inkubation (Ölflecken sichtbar).

    Methoden:
        "A"  Wert aus der Agrometeo-Tabelle (falls vorhanden), sonst B.
        "B"  ab Infektionstag (inklusive) Σ max(Tmittel - base, 0) bis ``target``.
        "ML" Regression der Inkubationsdauer – optional, noch nicht umgesetzt.

    Reichen die Wetterdaten nicht bis ``target``, wird mit dem Mittel der
    letzten 5 Tage hochgerechnet.

    Returns:
        (Datum oder None, geschätzt: bool)
    """
    if method == "ML":
        raise NotImplementedError("Methode ML folgt in Sprint 4 (optional).")
    if method == "A":
        ag = _as_date(agrometeo_end)
        if ag is not None:
            return ag, False

    after = daily[daily["date"] >= pd.Timestamp(inf_date)]
    if after.empty:
        return None, True
    excess = (after["t_mean"].fillna(base) - base).clip(lower=0)
    cum = excess.cumsum()
    reached = after.loc[cum >= target, "date"]
    if not reached.empty:
        return pd.Timestamp(reached.iloc[0]).date(), False

    # Hochrechnung über das Datenende hinaus
    rate = max(excess.tail(5).mean(), 1.0)
    missing_days = math.ceil((target - cum.iloc[-1]) / rate)
    last = pd.Timestamp(after["date"].iloc[-1]).date()
    return last + timedelta(days=missing_days), True


def spray_deadline(inf_date: date, inc_end: date,
                   share: float = config.SPRAY_DEADLINE_SHARE) -> date:
    """Spätester Spritztermin: Infektion + ``share`` der Inkubationsdauer (abgerundet).

    Beispiel: Infektion 07.05., Inkubationsende 20.05. (13 Tage)
    -> 80 % = 10,4 Tage -> 17.05.
    """
    days = (inc_end - inf_date).days
    return inf_date + timedelta(days=math.floor(days * share))
