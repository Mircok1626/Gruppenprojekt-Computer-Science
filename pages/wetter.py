"""Wetter: Temperatur, Regen und Infektionen der Saison, Temperatursumme, Blattnässe-Kalibrierung."""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import app_state as S
from core import agrometeo, config

st.title("🌦️ Wetter und Infektionen")

season, notes = S.get_season()
if season is None:
    st.stop()
today = season.today
d = season.daily

last_day = d["date"].max().date()
start_default = min(date(today.year, 4, 1), last_day)
period = st.slider("Zeitraum", min_value=d["date"].min().date(), max_value=last_day,
                   value=(start_default, last_day), format="DD.MM.")
view = d[(d["date"] >= pd.Timestamp(period[0])) & (d["date"] <= pd.Timestamp(period[1]))]

# --- Temperatur + Regen + Infektionen --------------------------------------------
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Bar(x=view["date"], y=view["rain_mm"], name="Regen (mm)",
                     marker_color="#6fa8dc", opacity=0.6), secondary_y=True)
fig.add_trace(go.Scatter(x=view["date"], y=view["t_max"], name="Tmax",
                         line=dict(color="#d64545", width=1)), secondary_y=False)
fig.add_trace(go.Scatter(x=view["date"], y=view["t_mean"], name="Tmittel",
                         line=dict(color="#444", width=2)), secondary_y=False)
fig.add_trace(go.Scatter(x=view["date"], y=view["t_min"], name="Tmin",
                         line=dict(color="#3d85c6", width=1)), secondary_y=False)
inf_days = view[view["infection_level"] > 0]
for lvl, color in S.LEVEL_COLORS.items():
    sub = inf_days[inf_days["infection_level"] == lvl]
    fig.add_trace(go.Scatter(x=sub["date"], y=sub["t_max"] + 2, mode="markers",
                             marker=dict(symbol="triangle-down", size=11, color=color),
                             name=f"Infektion {config.INFECTION_SYMBOLS[lvl]}"), secondary_y=False)
fig.add_vrect(x0=pd.Timestamp(today), x1=view["date"].max(), fillcolor="gray", opacity=0.1,
              line_width=0)
fig.update_yaxes(title_text="°C", secondary_y=False)
fig.update_yaxes(title_text="mm", secondary_y=True, showgrid=False)
fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10),
                  legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig, use_container_width=True)
st.caption("Grau hinterlegt = Prognose (nach dem Stichtag).")

# --- Temperatursumme ---------------------------------------------------------------
st.subheader("Temperatursumme seit 1.1. (Keimbereitschaft)")
fig2 = px.line(d, x="date", y="temp_sum", labels={"date": "", "temp_sum": "Σ max(Tmittel − 8, 0)"})
fig2.add_hline(y=config.GERMINATION_THRESHOLD, line_dash="dash", line_color="#d64545")
if season.germination:
    fig2.add_vline(x=pd.Timestamp(season.germination), line_dash="dot", line_color="#2e9d4f")
fig2.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig2, use_container_width=True)
st.caption(f"Keimbereitschaft (Schwelle {config.GERMINATION_THRESHOLD}): "
           f"{S.fmt(season.germination, True) if season.germination else 'noch nicht erreicht'}")

# --- Blattnässe-Kalibrierung -------------------------------------------------------
st.subheader("Blattnässe: Schätzung (Open-Meteo) vs. Messung (Agrometeo)")
year = today.year
if year not in agrometeo.available_years():
    st.write("Für dieses Jahr gibt es keine Agrometeo-Referenz.")
elif st.toggle("Vergleich für die Saison laden (Open-Meteo-Archiv)"):
    end = min(date(year, 9, 30), date.today() - timedelta(days=6))
    try:
        om = S._archive_daily(config.ZIZERS_LAT, config.ZIZERS_LON, date(year, 4, 1), end, 6, 14)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Open-Meteo nicht erreichbar: {exc}")
        st.stop()
    ag = agrometeo.measured_only(agrometeo.load_year(year))
    cmp = om[["date", "wet_hours", "degree_hours_wet"]].merge(
        ag[["date", "wet_hours", "degree_hours_wet", "infection_level_ag"]],
        on="date", suffixes=("_om", "_ag"))
    corr = cmp["wet_hours_om"].corr(cmp["wet_hours_ag"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Korrelation Nässestunden", f"{corr:.2f}")
    c2.metric("Ø Abweichung (h/Tag)", f"{(cmp['wet_hours_om'] - cmp['wet_hours_ag']).mean():+.1f}")
    own = cmp["degree_hours_wet_om"] >= config.INFECTION_THRESHOLDS[0]
    ref = cmp["infection_level_ag"] > 0
    c3.metric("Infektionen erkannt (geschätzt)", f"{int((own & ref).sum())} / {int(ref.sum())}",
              f"{int((own & ~ref).sum())} Fehlalarme", delta_color="off")
    fig3 = px.scatter(cmp, x="wet_hours_ag", y="wet_hours_om", opacity=0.6,
                      labels={"wet_hours_ag": "gemessen (Agrometeo) h", "wet_hours_om": "geschätzt (Open-Meteo) h"})
    fig3.add_shape(type="line", x0=0, y0=0, x1=24, y1=24, line=dict(dash="dash", color="gray"))
    fig3.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Regel: Stunde nass, wenn Regen > 0,1 mm oder rel. Feuchte ≥ 90 %. "
               "Abweichungen ehrlich zeigen – sie begrenzen die Prognosegüte.")

S.show_notes(notes)
