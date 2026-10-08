"""Dosierung: Brühe- und Mittelrechner pro ha, Parzelle und Tankfüllung."""
from datetime import timedelta

import pandas as pd
import streamlit as st

import app_state as S
from core import dosage
from db import database as db

st.title("🧪 Brühe- und Mittelrechner")

parcel = S.current_parcel()
products = db.list_products()
stages = db.list_stages()
settings = db.get_settings()

c1, c2 = st.columns(2)
stage_idx = c1.selectbox("Stadium (BBCH)", stages.index,
                         format_func=lambda i: f"BBCH {stages.at[i, 'bbch']} – {stages.at[i, 'label']} "
                                               f"({stages.at[i, 'base_broth_l_ha']:.0f} l/ha Basisbrühe)")
prod_idx = c2.selectbox("Mittel", products.index,
                        format_func=lambda i: f"{products.at[i, 'name']} ({products.at[i, 'concentration_pct']} %)")
stage = stages.loc[stage_idx]
product = products.loc[prod_idx]

c3, c4, c5 = st.columns(3)
area = c3.number_input("Fläche (ha)", min_value=0.01, step=0.05,
                       value=float(parcel["area_ha"]) if parcel else 1.0)
water = c4.number_input("Wassermenge Sprühgerät (l/ha)", min_value=10.0, step=10.0,
                        value=min(300.0, float(stage["base_broth_l_ha"])))
tank = c5.number_input("Tankgrösse (l)", min_value=10.0, step=10.0, value=float(settings["tank_l"]))

unit = product["unit"]
per_ha = dosage.product_per_ha(product["concentration_pct"], stage["base_broth_l_ha"])
total = dosage.per_parcel(per_ha, area)
water_total = dosage.water_per_parcel(water, area)
per_tank = dosage.per_tank(per_ha, water, tank)
fillings = dosage.tank_fillings(water_total, tank)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Mittel pro ha", f"{per_ha:.2f} {unit}")
m2.metric("Mittel für Parzelle", f"{total:.2f} {unit}")
m3.metric("Wasser total", f"{water_total:.0f} l", f"{fillings} Tankfüllung(en)", delta_color="off")
m4.metric("Mittel pro voller Tank", f"{per_tank:.2f} {unit}")

st.caption(f"Konzentrierung {dosage.concentration_factor(stage['base_broth_l_ha'], water):.1f}-fach "
           f"gegenüber der Basisbrühe ({stage['base_broth_l_ha']:.0f} l/ha).")

# --- Hinweise ----------------------------------------------------------------------
if product["needs_folpet"]:
    st.info("Dieses Mittel nur in Mischung mit einem Kontaktpartner (z. B. Folpet) einsetzen.")
if product["heat_sensitive"]:
    season, _ = S.get_season()
    if season is not None:
        next_days = season.daily[(season.daily["date"] > pd.Timestamp(season.today)) &
                                 (season.daily["date"] <= pd.Timestamp(season.today + timedelta(days=3)))]
        hot = next_days[next_days["t_max"] >= settings["heat_yellow_c"]]
        if not hot.empty:
            st.warning(f"Hitzeempfindliches Mittel: Tmax bis {hot['t_max'].max():.0f} °C "
                       f"in den nächsten Tagen – früh am Morgen spritzen oder anderes Mittel wählen.")

st.session_state["last_dosage"] = {"product_id": int(product["id"]), "bbch": stage["bbch"],
                                   "water_l_ha": water, "amount_total": round(total, 3)}
st.caption("Werte werden im Journal als Vorschlag übernommen. Konzentrationen und Basisbrühmengen "
           "sind Platzhalter – mit Agroscope-Liste (Transfer Nr. 626) und Winzer abgleichen.")
