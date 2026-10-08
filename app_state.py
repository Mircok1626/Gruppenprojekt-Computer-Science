"""Gemeinsamer App-Zustand: Sidebar, Demo-Modus, Datenladen mit Caching.

Alle Seiten holen «heute» ausschliesslich über ``get_today()`` und die Saison
über ``get_season()``. So funktioniert der Demo-Modus überall gleich.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core import agrometeo, config, weather
from core.season import Season, build_season
from db import database as db

DEMO = "Demo (Simulation)"
LIVE = "Live (Open-Meteo)"
CALENDAR_DAYS = 14

STATUS_COLORS = {"grün": "#2e9d4f", "gelb": "#e0a800", "rot": "#d64545"}
LEVEL_COLORS = {1: "#f2c94c", 2: "#f2994a", 3: "#d64545"}


# ---------------------------------------------------------------------------
# Datum und Modus
# ---------------------------------------------------------------------------
def is_demo() -> bool:
    return st.session_state.get("mode", DEMO) == DEMO


def get_today() -> date:
    """Echtes Datum (Live) oder Simulationsdatum (Demo)."""
    if is_demo():
        return st.session_state.get("sim_date", date(2026, 5, 7))
    return date.today()


def fmt(d, with_year: bool = False) -> str:
    """Datum im Schweizer Format, z. B. 07.05."""
    if d is None or pd.isna(d):
        return "–"
    return pd.Timestamp(d).strftime("%d.%m.%Y" if with_year else "%d.%m.")


def _default_sim_date(year: int) -> date:
    return date(year, 5, 7) if year == 2026 else date(year, 6, 1)


def _reset_sim_date():
    st.session_state.sim_date = _default_sim_date(st.session_state.demo_year)


def render_sidebar() -> None:
    """Sidebar auf jeder Seite: Parzelle, Datenquelle, Simulationsdatum."""
    sb = st.sidebar
    sb.markdown("### 🍇 Spritzplaner Rebberg")

    parcels = db.list_parcels()
    if parcels.empty:
        sb.warning("Noch keine Parzelle – bitte unter «Parzellen» anlegen.")
        st.session_state.parcel_id = None
    else:
        ids = parcels["id"].tolist()
        names = dict(zip(parcels["id"], parcels["name"]))
        if st.session_state.get("parcel_id") not in ids:
            st.session_state.parcel_id = ids[0]
        sb.selectbox("Parzelle", ids, format_func=names.get, key="parcel_id")

    sb.radio("Datenquelle", [DEMO, LIVE], key="mode")

    if is_demo():
        years = agrometeo.available_years()
        if not years:
            sb.error("Keine Agrometeo-CSV in data/processed gefunden.")
            return
        if st.session_state.get("demo_year") not in years:
            st.session_state.demo_year = max(years)
        sb.selectbox("Saison", years, key="demo_year", on_change=_reset_sim_date)
        y = st.session_state.demo_year
        lo, hi = date(y, 4, 1), date(y, 9, 30)
        if not (lo <= st.session_state.get("sim_date", lo - timedelta(1)) <= hi):
            st.session_state.sim_date = _default_sim_date(y)
        sb.slider("Heute ist der …", min_value=lo, max_value=hi, key="sim_date",
                  format="DD.MM.YYYY")

    if "inc_method" not in st.session_state:
        st.session_state.inc_method = "A"
    sb.selectbox("Inkubation", ["A", "B"], key="inc_method",
                 format_func={"A": "A – Agrometeo (falls vorhanden)",
                              "B": "B – Σ(Tmittel − 8) bis 70"}.get)
    sb.caption(f"Stichtag: **{fmt(get_today(), True)}**")
    sb.caption("Entscheidungshilfe – ersetzt keine Beratung.")


def current_parcel() -> dict | None:
    pid = st.session_state.get("parcel_id")
    if pid is None:
        return None
    parcels = db.list_parcels()
    row = parcels[parcels["id"] == pid]
    return None if row.empty else row.iloc[0].to_dict()


# ---------------------------------------------------------------------------
# Daten laden (mit Cache)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _agrometeo_year(year: int) -> pd.DataFrame:
    return agrometeo.load_year(year)


@st.cache_data(ttl=24 * 3600, show_spinner="Lade Open-Meteo-Archiv …")
def _archive_daily(lat: float, lon: float, start: date, end: date,
                   spray_from: int, spray_to: int) -> pd.DataFrame:
    hourly = weather.fetch_archive(lat, lon, start, end)
    return weather.daily_from_hourly(hourly, "Open-Meteo Archiv (als Prognose)",
                                     spray_from, spray_to)


@st.cache_data(ttl=1800, show_spinner="Lade Open-Meteo-Prognose …")
def _live_daily(lat: float, lon: float, today: date,
                spray_from: int, spray_to: int) -> pd.DataFrame:
    hourly = weather.fetch_season_live(lat, lon, today)
    daily = weather.daily_from_hourly(hourly, "Open-Meteo", spray_from, spray_to)
    daily.loc[daily["date"] > pd.Timestamp(today), "source"] = "Open-Meteo Prognose"
    return daily


def load_daily(parcel: dict | None) -> tuple[pd.DataFrame, list[str]]:
    """Tageswerte der Saison ab 1.1. bis ca. 14 Tage nach «heute» + Hinweise."""
    today = get_today()
    lat = float(parcel["lat"]) if parcel and parcel.get("lat") else config.ZIZERS_LAT
    lon = float(parcel["lon"]) if parcel and parcel.get("lon") else config.ZIZERS_LON
    s = db.get_settings()
    hours = (int(s["spray_hours_from"]), int(s["spray_hours_to"]))
    notes: list[str] = []
    t_today = pd.Timestamp(today)

    if is_demo():
        ag = _agrometeo_year(today.year)
        past = ag[(ag["date"] <= t_today) & ~ag["is_forecast"]]
        start = today + timedelta(days=1)
        end = min(today + timedelta(days=CALENDAR_DAYS), date.today() - timedelta(days=6))
        fc = pd.DataFrame()
        if start <= end:
            try:
                fc = _archive_daily(lat, lon, start, end, *hours)
                notes.append("Vergangenheit = Agrometeo-Messwerte; «Prognose» = echtes Wetter "
                             "aus dem Open-Meteo-Archiv ab dem Simulationsdatum (Blattnässe geschätzt).")
            except Exception as exc:  # noqa: BLE001 – App soll offline weiterlaufen
                notes.append(f"Open-Meteo nicht erreichbar ({exc.__class__.__name__}) – "
                             "Agrometeo-Werte als Ersatz-Prognose.")
        if fc.empty:
            fc = ag[(ag["date"] > t_today) &
                    (ag["date"] <= t_today + pd.Timedelta(days=CALENDAR_DAYS))]
        daily = pd.concat([past, fc], ignore_index=True)
    else:
        try:
            daily = _live_daily(lat, lon, today, *hours)
        except Exception as exc:  # noqa: BLE001
            st.error(f"Open-Meteo nicht erreichbar: {exc}")
            return pd.DataFrame(), notes
        notes.append("Live: Open-Meteo-Archiv + Prognose, Blattnässe geschätzt "
                     "(Regen > 0,1 mm oder Feuchte ≥ 90 %).")
        if today.year in agrometeo.available_years():
            ag = _agrometeo_year(today.year)[["date", "incubation_end_ag", "infection_level_ag"]]
            daily = daily.merge(ag, on="date", how="left")

    if "incubation_end_ag" not in daily:
        daily["incubation_end_ag"] = pd.NaT
    return daily.sort_values("date").reset_index(drop=True), notes


def get_season() -> tuple[Season | None, list[str]]:
    """Saison-Auswertung für die gewählte Parzelle und den Stichtag."""
    parcel = current_parcel()
    daily, notes = load_daily(parcel)
    if daily.empty:
        return None, notes
    sprays = db.spray_dates(parcel["id"]) if parcel else []
    season = build_season(daily, get_today(), sprays, method=st.session_state.get("inc_method", "A"))
    return season, notes


def show_notes(notes: list[str]) -> None:
    for n in notes:
        st.caption("ℹ️ " + n)
