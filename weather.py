"""Wetterdaten von Open-Meteo (Prognose + Archiv) und Blattnässe-Schätzung.

Reine Logik ohne Streamlit. Das Caching übernimmt ``app_state.py`` mit
``st.cache_data``, damit dieses Modul auch in Tests und in ``ml/train.py``
ohne App läuft.

Einheitliches Tagesformat (``daily``), das alle anderen Module erwarten:

    date              pandas Timestamp (00:00)
    t_min/t_mean/t_max  °C
    rain_mm           Tagessumme Niederschlag
    wet_hours         Stunden mit Blattnässe (geschätzt oder gemessen)
    degree_hours_wet  Gradstunden bei Blattnässe (Σ Temperatur der nassen Stunden)
    rain_hours, rh90_hours, dewpoint_spread, wind_mean   (nur Open-Meteo)
    rain_6h_min       kleinste Regenmenge in 6 h nach einem möglichen Spritzbeginn
    best_start_hour   Uhrzeit dieses besten Spritzbeginns
    source            Herkunft der Zeile (Text)
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

from core import config

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "precipitation",
    "wind_speed_10m",
]


# ---------------------------------------------------------------------------
# API-Aufrufe
# ---------------------------------------------------------------------------
def _hourly_to_frame(payload: dict) -> pd.DataFrame:
    """Wandelt die JSON-Antwort von Open-Meteo in ein stündliches DataFrame."""
    h = payload["hourly"]
    df = pd.DataFrame(
        {
            "time": pd.to_datetime(h["time"]),
            "temp": h["temperature_2m"],
            "rh": h["relative_humidity_2m"],
            "dew": h["dew_point_2m"],
            "precip": h["precipitation"],
            "wind": h["wind_speed_10m"],
        }
    )
    return df.dropna(subset=["temp"]).reset_index(drop=True)


def fetch_archive(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    """Stündliche Messwerte (Reanalyse) aus dem Open-Meteo-Archiv.

    Das Archiv hinkt einige Tage hinterher; neuere Tage fehlen einfach.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": ",".join(HOURLY_VARS),
        "timezone": config.TIMEZONE,
        "wind_speed_unit": "kmh",
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=30)
    r.raise_for_status()
    return _hourly_to_frame(r.json())


def fetch_forecast(lat: float, lon: float, past_days: int = 7, forecast_days: int = 16) -> pd.DataFrame:
    """Stündliche Prognose (bis 16 Tage) inkl. der letzten ``past_days`` Tage."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "past_days": past_days,
        "forecast_days": forecast_days,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": config.TIMEZONE,
        "wind_speed_unit": "kmh",
    }
    r = requests.get(FORECAST_URL, params=params, timeout=30)
    r.raise_for_status()
    return _hourly_to_frame(r.json())


def fetch_season_live(lat: float, lon: float, today: date) -> pd.DataFrame:
    """Ganze Saison ab 1.1. bis Prognose-Ende: Archiv + aktuelle Prognose."""
    parts = []
    archive_end = today - timedelta(days=6)
    start = date(today.year, 1, 1)
    if archive_end >= start:
        parts.append(fetch_archive(lat, lon, start, archive_end))
    parts.append(fetch_forecast(lat, lon, past_days=7, forecast_days=16))
    hourly = pd.concat(parts, ignore_index=True)
    hourly = hourly.drop_duplicates("time", keep="last").sort_values("time")
    return hourly.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Blattnässe und Tageswerte
# ---------------------------------------------------------------------------
def estimate_wetness(hourly: pd.DataFrame,
                     rain_mm: float = config.WET_RAIN_MM,
                     rh_pct: float = config.WET_RH_PCT) -> pd.Series:
    """Schätzt pro Stunde, ob das Blatt nass ist.

    Open-Meteo misst keine Blattnässe. Näherung: nass, wenn Regen > ``rain_mm``
    oder relative Feuchte >= ``rh_pct``. Wird gegen die gemessene Blattnässe
    von Agrometeo kalibriert (Seite «Wetter»).
    """
    return (hourly["precip"] > rain_mm) | (hourly["rh"] >= rh_pct)


def daily_from_hourly(hourly: pd.DataFrame, source: str = "Open-Meteo",
                      spray_from: int = 6, spray_to: int = 14) -> pd.DataFrame:
    """Fasst stündliche Werte zu Tageswerten im einheitlichen Format zusammen."""
    h = hourly.sort_values("time").copy()
    h["date"] = h["time"].dt.normalize()
    h["precip"] = h["precip"].fillna(0.0)
    h["wet"] = estimate_wetness(h)
    h["wet_temp"] = np.where(h["wet"], h["temp"].clip(lower=0), 0.0)
    h["spread"] = h["temp"] - h["dew"]
    h["is_rain"] = h["precip"] > config.WET_RAIN_MM
    h["is_rh90"] = h["rh"] >= config.WET_RH_PCT
    # Regen in dieser + den 5 folgenden Stunden (= 6 h nach Spritzbeginn)
    h["rain_next6"] = h["precip"][::-1].rolling(6, min_periods=1).sum()[::-1]

    daily = h.groupby("date").agg(
        t_min=("temp", "min"),
        t_mean=("temp", "mean"),
        t_max=("temp", "max"),
        rain_mm=("precip", "sum"),
        rain_hours=("is_rain", "sum"),
        rh90_hours=("is_rh90", "sum"),
        wet_hours=("wet", "sum"),
        degree_hours_wet=("wet_temp", "sum"),
        dewpoint_spread=("spread", "mean"),
    )

    daytime = h[h["time"].dt.hour.between(6, 20)]
    daily["wind_mean"] = daytime.groupby("date")["wind"].mean()

    cand = h[h["time"].dt.hour.between(spray_from, spray_to)]
    if not cand.empty:
        best = cand.loc[cand.groupby("date")["rain_next6"].idxmin()]
        best = best.set_index("date")
        daily["rain_6h_min"] = best["rain_next6"]
        daily["best_start_hour"] = best["time"].dt.hour
    else:
        daily["rain_6h_min"] = np.nan
        daily["best_start_hour"] = np.nan

    daily = daily.reset_index()
    daily["wet_hours"] = daily["wet_hours"].astype(float)
    daily["degree_hours_wet"] = daily["degree_hours_wet"].round(0)
    daily["source"] = source
    return daily
