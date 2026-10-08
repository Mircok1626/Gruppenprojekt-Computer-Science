"""Jahreslimiten (Kupfer, Anzahl Behandlungen) – für Sprint 4 vorbereitet."""
from __future__ import annotations

import pandas as pd

# Startwert, mit Agroscope-Empfehlungen / ÖLN-Vorgaben und dem Winzer prüfen!
COPPER_LIMIT_KG_HA = 4.0


def copper_kg(amount_product: float, copper_pct: float) -> float:
    """Reinkupfer in kg aus Produktmenge und Kupfergehalt (%)."""
    return amount_product * (copper_pct or 0.0) / 100.0


def yearly_summary(sprays: pd.DataFrame) -> pd.DataFrame:
    """Anzahl Behandlungen und Mengen pro Wirkstoffgruppe.

    Erwartet Spalten ``active_group``, ``amount_total``, ``copper_pct``, ``max_per_year``.
    """
    if sprays.empty:
        return pd.DataFrame(columns=["active_group", "anzahl", "menge_total",
                                     "kupfer_kg", "max_pro_jahr"])
    df = sprays.copy()
    df["kupfer_kg"] = [copper_kg(a, c) for a, c in zip(df["amount_total"], df["copper_pct"])]
    out = df.groupby("active_group").agg(
        anzahl=("id", "count"),
        menge_total=("amount_total", "sum"),
        kupfer_kg=("kupfer_kg", "sum"),
        max_pro_jahr=("max_per_year", "max"),
    )
    return out.reset_index()
