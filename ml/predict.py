"""Gespeichertes Modell laden und Infektionsrisiko vorhersagen."""
from __future__ import annotations

import joblib
import pandas as pd

from core import config
from ml.features import build_features


def load_model(path=config.MODEL_PATH) -> dict | None:
    """Lädt das Modell-Bundle aus ``ml/train.py`` oder None, falls nicht vorhanden."""
    if not path.exists():
        return None
    return joblib.load(path)


def predict_risk(bundle: dict, daily: pd.DataFrame) -> pd.DataFrame:
    """Infektionswahrscheinlichkeit pro Tag.

    ``daily`` ist die ganze Saison ab 1.1. (für Temperatursumme und Regen der
    Vortage). Zurück kommen nur Tage mit vollständigen Open-Meteo-Features.
    """
    feats = build_features(daily).dropna(subset=bundle["features"])
    if feats.empty:
        return pd.DataFrame(columns=["date", "proba"])
    proba = bundle["model"].predict_proba(feats[bundle["features"]])[:, 1]
    return pd.DataFrame({"date": feats["date"].values, "proba": proba})
