"""Kalender: Spritzfenster-Ampel für 14 Tage + laufende Inkubationen als Balken."""
from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import app_state as S
from core import config, spray_window
from db import database as db

st.title("📅 Spritzkalender")

season, notes = S.get_season()
if season is None:
    st.stop()
today = season.today
settings = db.get_settings()

# --- Einstellungen (Grenzwerte der Ampel) -------------------------------------
with st.expander("Grenzwerte der Ampel anpassen"):
    labels = {
        "rain_yellow_mm": "Regen gelb ab (mm)", "rain_red_mm": "Regen rot über (mm)",
        "wind_yellow_kmh": "Wind gelb ab (km/h)", "wind_red_kmh": "Wind rot über (km/h)",
        "heat_yellow_c": "Tmax gelb ab (°C)", "heat_red_c": "Tmax rot über (°C)",
        "tank_l": "Tankgrösse (l)",
    }
    cols = st.columns(4)
    new = {}
    for i, (key, label) in enumerate(labels.items()):
        new[key] = cols[i % 4].number_input(label, value=float(settings[key]), step=0.5, key=f"set_{key}")
    sunday = st.checkbox("Sonntag ist rot", value=bool(settings["sunday_red"]))
    if st.button("Speichern"):
        for k, v in new.items():
            db.set_setting(k, v)
        db.set_setting("sunday_red", 1.0 if sunday else 0.0)
        st.success("Gespeichert.")
        st.rerun()

products = db.list_products()
prod_name = st.selectbox("Geplantes Mittel (für Hitze-Hinweis)", products["name"])
heat = bool(products.loc[products["name"] == prod_name, "heat_sensitive"].iloc[0])

# --- Ampel-Kacheln -------------------------------------------------------------
days = season.daily[(season.daily["date"] >= pd.Timestamp(today)) &
                    (season.daily["date"] <= pd.Timestamp(today + timedelta(days=S.CALENDAR_DAYS - 1)))]
inf_by_day = {d: sym for d, sym in zip(season.infections["date"], season.infections["symbol"])}
WEEKDAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]

st.subheader("Spritzfenster")
for start in range(0, len(days), 7):
    cols = st.columns(7)
    for col, (_, day) in zip(cols, days.iloc[start:start + 7].iterrows()):
        status, reasons = spray_window.day_status(day, settings, heat_sensitive=heat)
        d = day["date"].date()
        inf_sym = inf_by_day.get(d, "")
        inf_html = f"<div style='font-weight:700'>Infektion {inf_sym}</div>" if inf_sym else ""
        hour = day.get("best_start_hour")
        hour_txt = f"ab {int(hour)} Uhr" if status != "rot" and pd.notna(hour) else ""
        col.markdown(
            f"""<div style="background:{S.STATUS_COLORS[status]};color:white;border-radius:10px;
                 padding:8px;min-height:150px;font-size:0.85rem">
                 <div style="font-size:1.05rem;font-weight:700">{WEEKDAYS[d.weekday()]} {S.fmt(d)}</div>
                 <div>{status.upper()} {hour_txt}</div>
                 <div>{day['t_min']:.0f}–{day['t_max']:.0f} °C · {day['rain_mm']:.1f} mm</div>
                 {inf_html}
                 <div style="opacity:0.9">{'<br>'.join(reasons)}</div></div>""",
            unsafe_allow_html=True,
        )
    st.write("")

st.caption("Tage mit Daten aus der Prognose bzw. dem Archiv. Ohne stündliche Daten "
           "(Agrometeo-Ersatz) wird die Tagesregenmenge statt des besten 6-h-Fensters bewertet.")

# --- Inkubationsbalken -----------------------------------------------------------
st.subheader("Laufende und kommende Inkubationen")
inf = season.infections
inf = inf[(inf["date"] >= today - timedelta(days=21)) & inf["inc_end"].notna()]
if inf.empty:
    st.write("Keine Infektionen in den letzten 3 Wochen.")
else:
    bars = pd.DataFrame({
        "Infektion": [f"{S.fmt(d)} {s}" for d, s in zip(inf["date"], inf["symbol"])],
        "Start": pd.to_datetime(inf["date"]),
        "Ende": pd.to_datetime(inf["inc_end"]),
        "Stufe": inf["level"].astype(str),
        "Status": inf["status"],
    })
    fig = px.timeline(bars, x_start="Start", x_end="Ende", y="Infektion", color="Stufe",
                      hover_data=["Status"],
                      color_discrete_map={str(k): v for k, v in S.LEVEL_COLORS.items()})
    fig.add_trace(go.Scatter(
        x=pd.to_datetime(inf["deadline"]), y=bars["Infektion"], mode="markers",
        marker=dict(symbol="diamond", size=12, color="black"), name="spritzen bis"))
    fig.add_vline(x=pd.Timestamp(today), line_dash="dash", line_color="gray")
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_layout(height=120 + 35 * len(bars), margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Balken = Inkubation bis Ölflecken; ◆ = spritzen bis "
               f"({config.SPRAY_DEADLINE_SHARE:.0%} der Inkubation); gestrichelt = heute.")

S.show_notes(notes)
