"""Training und Evaluation des Infektionsklassifikators.

Aufruf im Projektordner:

    python -m ml.train

Ablauf:
1. Open-Meteo-Archiv (stündlich) für jedes Jahr mit Agrometeo-CSV holen
   und zu Tagesfeatures verdichten (wird in data/processed/ zwischengespeichert).
2. Mit den Agrometeo-Labels (Infektion ja/nein) per Datum zusammenführen.
   Nur Tage zwischen Keimbereitschaft und Ende September.
3. Zeitlicher Split: letztes Jahr = Test, alle früheren = Training.
4. Baseline (Regel «Gradstunden ≥ 70» auf geschätzter Blattnässe) vs. Random Forest.
5. Modell + Kennzahlen mit joblib speichern; die App lädt es nur.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)

from core import agrometeo, config, infection, weather
from ml.features import FEATURES, build_features


def openmeteo_daily(year: int, lat: float = config.ZIZERS_LAT, lon: float = config.ZIZERS_LON,
                    use_cache: bool = True) -> pd.DataFrame:
    """Tageswerte aus dem Open-Meteo-Archiv für ein Jahr (mit CSV-Cache)."""
    cache = config.PROCESSED_DIR / f"openmeteo_zizers_{year}.csv"
    if use_cache and cache.exists():
        return pd.read_csv(cache, parse_dates=["date"])
    end = min(date(year, 12, 31), date.today() - timedelta(days=6))
    hourly = weather.fetch_archive(lat, lon, date(year, 1, 1), end)
    daily = weather.daily_from_hourly(hourly, source="Open-Meteo Archiv")
    daily.to_csv(cache, index=False)
    return daily


def build_dataset(year: int) -> pd.DataFrame:
    """Features (Open-Meteo) + Labels (Agrometeo) für die Saison eines Jahres."""
    labels = agrometeo.measured_only(agrometeo.load_year(year))
    germ = infection.germination_date(labels) or date(year, 4, 15)
    season_end = date(year, *config.SEASON_END_MONTH_DAY)

    feats = build_features(openmeteo_daily(year))
    df = feats.merge(labels[["date", "infection_level_ag", "degree_hours_wet"]]
                     .rename(columns={"degree_hours_wet": "dh_agrometeo"}),
                     on="date", how="inner")
    df = df[(df["date"] >= pd.Timestamp(germ)) & (df["date"] <= pd.Timestamp(season_end))]
    df = df.dropna(subset=FEATURES)
    df["y"] = (df["infection_level_ag"] > 0).astype(int)
    df["year"] = year
    return df.reset_index(drop=True)


def _scores(y_true, y_pred) -> dict:
    return {
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "accuracy": accuracy_score(y_true, y_pred),
        "confusion": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
    }


def train_and_save(test_year: int | None = None, path=config.MODEL_PATH) -> dict:
    """Trainiert das Modell, vergleicht mit der Baseline und speichert alles."""
    years = agrometeo.available_years()
    if len(years) < 2:
        raise RuntimeError("Mindestens zwei Jahre Agrometeo-CSV nötig (Training + Test).")
    test_year = test_year or max(years)
    train_years = [y for y in years if y != test_year]

    data = pd.concat([build_dataset(y) for y in years], ignore_index=True)
    train = data[data["year"].isin(train_years)]
    test = data[data["year"] == test_year]

    model = RandomForestClassifier(n_estimators=300, min_samples_leaf=3,
                                   class_weight="balanced", random_state=42)
    model.fit(train[FEATURES], train["y"])

    rf_pred = model.predict(test[FEATURES])
    base_pred = (test["degree_hours_wet"] >= config.INFECTION_THRESHOLDS[0]).astype(int)

    test_out = test[["date", "y", "degree_hours_wet", "dh_agrometeo"]].copy()
    test_out["proba"] = model.predict_proba(test[FEATURES])[:, 1]
    test_out["rf_pred"] = rf_pred
    test_out["baseline_pred"] = base_pred.values

    bundle = {
        "model": model,
        "features": FEATURES,
        "train_years": train_years,
        "test_year": test_year,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "positives_train": int(train["y"].sum()),
        "positives_test": int(test["y"].sum()),
        "metrics": {"Random Forest": _scores(test["y"], rf_pred),
                    "Baseline (Gradstunden ≥ 70)": _scores(test["y"], base_pred)},
        "importance": dict(zip(FEATURES, model.feature_importances_.round(4).tolist())),
        "test_predictions": test_out,
        "trained_at": datetime.now().isoformat(timespec="minutes"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    return bundle


if __name__ == "__main__":
    b = train_and_save()
    print(f"Training: {b['train_years']} ({b['n_train']} Tage), Test: {b['test_year']} ({b['n_test']} Tage)")
    for name, m in b["metrics"].items():
        print(f"{name:30s} Recall {m['recall']:.2f}  Precision {m['precision']:.2f}  "
              f"F1 {m['f1']:.2f}  Konfusion {m['confusion']}")
    print(f"Gespeichert: {config.MODEL_PATH}")
