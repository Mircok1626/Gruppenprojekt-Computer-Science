"""Parzellen anlegen, bearbeiten und löschen."""
import streamlit as st

from core import config
from db import database as db

st.title("🗺️ Parzellen")

parcels = db.list_parcels()

# --- Bearbeiten als Tabelle -------------------------------------------------------
if parcels.empty:
    st.info("Noch keine Parzellen.")
else:
    st.caption("Werte direkt in der Tabelle ändern und speichern.")
    edited = st.data_editor(
        parcels, hide_index=True, use_container_width=True, disabled=["id"],
        column_config={
            "name": "Name", "area_ha": st.column_config.NumberColumn("Fläche (ha)", min_value=0.01),
            "variety": "Sorte", "lat": "Breite", "lon": "Länge", "station": "Agrometeo-Station",
        },
        key="parcel_editor",
    )
    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("Änderungen speichern"):
        for _, r in edited.iterrows():
            db.update_parcel(int(r["id"]), r["name"], float(r["area_ha"]), r["variety"],
                             float(r["lat"]), float(r["lon"]), r["station"])
        st.success("Gespeichert.")
        st.rerun()
    to_delete = c2.selectbox("Parzelle löschen", parcels["id"],
                             format_func=dict(zip(parcels["id"], parcels["name"])).get)
    if c3.button("Löschen", help="Löscht auch alle Spritzungen dieser Parzelle"):
        db.delete_parcel(int(to_delete))
        st.rerun()

# --- Neue Parzelle ---------------------------------------------------------------
with st.form("new_parcel", clear_on_submit=True):
    st.subheader("Neue Parzelle")
    c1, c2, c3 = st.columns(3)
    name = c1.text_input("Name")
    area = c2.number_input("Fläche (ha)", min_value=0.01, value=0.5, step=0.05)
    variety = c3.text_input("Sorte", value="Blauburgunder")
    c4, c5, c6 = st.columns(3)
    lat = c4.number_input("Breite", value=config.ZIZERS_LAT, format="%.4f")
    lon = c5.number_input("Länge", value=config.ZIZERS_LON, format="%.4f")
    station = c6.text_input("Agrometeo-Station", value="zizers")
    if st.form_submit_button("Anlegen", type="primary"):
        if not name.strip():
            st.error("Bitte einen Namen eingeben.")
        else:
            db.add_parcel(name.strip(), area, variety, lat, lon, station.lower())
            st.success(f"Parzelle «{name}» angelegt.")
            st.rerun()
