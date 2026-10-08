"""Formel 4: Schutzstatus durch einen Spritzbelag."""
from __future__ import annotations

from datetime import date, timedelta

from core import config


def is_protected(inf_date: date, last_spray: date | None,
                 days: int = config.PROTECTION_DAYS) -> bool:
    """True, wenn die letzte Spritzung vor der Infektion höchstens ``days`` Tage zurückliegt.

    Beispiel: Spritzung 05.05., Infektion 11.05. -> geschützt;
    Infektion 16.05. -> nicht mehr geschützt.
    """
    if last_spray is None or last_spray > inf_date:
        return False
    return (inf_date - last_spray).days <= days


def protected_until(last_spray: date | None, days: int = config.PROTECTION_DAYS) -> date | None:
    """Letzter Tag, an dem der Belag noch schützt."""
    if last_spray is None:
        return None
    return last_spray + timedelta(days=days)


def last_spray_before(spray_dates: list[date], day: date) -> date | None:
    """Jüngste Spritzung am oder vor ``day``."""
    earlier = [d for d in spray_dates if d <= day]
    return max(earlier) if earlier else None


def infection_status(inf_date: date, deadline: date | None, spray_dates: list[date],
                     today: date, days: int = config.PROTECTION_DAYS) -> str:
    """Status einer Infektion für Dashboard und Kalender.

    Returns:
        "geschützt"   Belag war bei der Infektion noch aktiv
        "behandelt"   nach der Infektion, aber vor «spritzen bis» gespritzt
        "offen"       noch nicht behandelt, Frist läuft
        "verpasst"    Frist abgelaufen, Ausbruch zu erwarten
    """
    if is_protected(inf_date, last_spray_before(spray_dates, inf_date), days):
        return "geschützt"
    if deadline is not None and any(inf_date < d <= deadline for d in spray_dates):
        return "behandelt"
    if deadline is None or today <= deadline:
        return "offen"
    return "verpasst"
