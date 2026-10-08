"""Dashboard: Mehltau-Alarm mit «spritzen bis», Schutzstatus und Kennzahlen."""
from datetime import timedelta

import pandas as pd
import streamlit as st

import app_state as S
from core import config, protection
from core.season import open_alarms, running_incubations
from db import database as db

st.title("🚦 Dashboard")

season, notes = S.get_season()
parcel = S.current_parcel()
if season is None or parcel is None:
    st.stop()

today = season.today
st.caption(f"Parzelle **{parcel['name']}** ({parcel['area_ha']} ha, {parcel['variety']}) · "
           f"Stichtag **{S.fmt(today, True)}**")

inf = season.infections
sprays = db.spray_dates(parcel["id"])
last_spray = protection.last_spray_before(sprays, today)
until = protection.protected_until(last_spray)
alarms = open_alarms(season)
running = running_incubations(season)
missed = running[running["status"] == "verpasst"] if not running.empty else running
week_end = today + timedelta(days=config.FORECAST_DAYS)
coming = inf[inf["is_forecast"] & (inf["date"] <= week_end)] if not inf.empty else inf

# --- Hauptmeldung -------------------------------------------------------------
if not alarms.empty:
    a = alarms.iloc[0]
    st.error(f"## Infektion {a['symbol']} am {S.fmt(a['date'])} – spritzen bis {S.fmt(a['deadline'])}")
    est = " (hochgerechnet)" if a["inc_estimated"] else ""
    st.write(f"Stufe {a['level']} ({config.INFECTION_LABELS[a['level']]}), "
             f"{a['degree_hours_wet']:.0f} Gradstunden bei Blattnässe. "
             f"Inkubationsende / Ölflecken ab {S.fmt(a['inc_end'])}{est}.")
    for _, o in alarms.iloc[1:].iterrows():
        st.write(f"• weitere offene Infektion {o['symbol']} am {S.fmt(o['date'])} "
                 f"– spritzen bis {S.fmt(o['deadline'])}")
elif until is not None and until >= today:
    st.success(f"## Geschützt bis {S.fmt(until)}")
    st.write(f"Letzte Spritzung am {S.fmt(last_spray)} – Belag hält ca. {config.PROTECTION_DAYS} Tage.")
elif season.germination is None or today < season.germination:
    st.info("## Noch keine Keimbereitschaft – kein Infektionsrisiko")
else:
    st.success("## Keine offene Infektion")

if not missed.empty:
    m = missed.iloc[0]
    st.warning(f"Frist verpasst: Infektion {m['symbol']} am {S.fmt(m['date'])} wurde nicht behandelt "
               f"– Ölflecken ab {S.fmt(m['inc_end'])} kontrollieren.")

if not coming.empty:
    txt = ", ".join(f"{S.fmt(d)} ({sym})" for d, sym in zip(coming["date"], coming["symbol"]))
    first = coming["date"].min()
    covered = until is not None and until >= first
    hint = "Belag schützt noch." if covered else "Vorbeugend vorher spritzen (siehe Kalender)."
    st.warning(f"Prognose: mögliche Infektion am {txt}. {hint}")

# --- Kennzahlen ------------------------------------------------------------------
past = season.daily[~season.daily["is_forecast"]]
tsum = float(past["temp_sum"].iloc[-1]) if not past.empty else 0.0
past_inf = inf[~inf["is_forecast"]] if not inf.empty else inf

c1, c2, c3, c4 = st.columns(4)
if season.germination and season.germination <= today:
    c1.metric("Keimbereitschaft", "ja", f"seit {S.fmt(season.germination)}")
else:
    c1.metric("Keimbereitschaft", "nein", f"Σ {tsum:.0f} / {config.GERMINATION_THRESHOLD}",
              delta_color="off")
c2.metric("Infektionen bis heute", len(past_inf))
c3.metric("Laufende Inkubationen", len(running))
c4.metric("Letzte Spritzung", S.fmt(last_spray), f"{(today - last_spray).days} Tage her" if last_spray else None,
          delta_color="off")

# --- Vergleich mit Agrometeo (nur wenn Referenz vorhanden) -------------------------
if "infection_level_ag" in season.daily:
    ref = season.daily[~season.daily["is_forecast"]]
    ref = ref[ref["date"] >= pd.Timestamp(season.germination)] if season.germination else ref.iloc[0:0]
    ag_n = int((ref["infection_level_ag"].fillna(0) > 0).sum())
    own_n = int((ref["infection_level"] > 0).sum())
    hits = int(((ref["infection_level_ag"].fillna(0) > 0) & (ref["infection_level"] > 0)).sum())
    st.caption(f"Kontrolle gegen Agrometeo bis heute: unsere Regel {own_n} Infektionen, "
               f"Agrometeo {ag_n}, davon {hits} übereinstimmend.")

# --- Letzte Infektionen ------------------------------------------------------------
st.subheader("Infektionen der letzten 3 Wochen")
recent = inf[inf["date"] >= today - timedelta(days=21)] if not inf.empty else inf
if recent.empty:
    st.write("Keine.")
else:
    view = pd.DataFrame({
        "Datum": recent["date"].map(S.fmt),
        "Stufe": recent["symbol"],
        "Gradstunden": recent["degree_hours_wet"].round(0),
        "Inkubationsende": recent["inc_end"].map(S.fmt),
        "spritzen bis": recent["deadline"].map(S.fmt),
        "Status": recent["status"],
    })
    st.dataframe(view, hide_index=True, use_container_width=True)

S.show_notes(notes)
