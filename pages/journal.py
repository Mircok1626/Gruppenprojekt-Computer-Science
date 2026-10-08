"""Spritzjournal: Spritzungen erfassen (SQLite), Schutzstatus, Jahresmengen."""
import pandas as pd
import streamlit as st

import app_state as S
from core import limits, protection
from db import database as db

st.title("📒 Spritzjournal")

parcel = S.current_parcel()
if parcel is None:
    st.info("Bitte zuerst eine Parzelle anlegen.")
    st.stop()

today = S.get_today()
products = db.list_products()
stages = db.list_stages()
proposal = st.session_state.get("last_dosage", {})

# --- Erfassen ----------------------------------------------------------------------
with st.form("spray_form", clear_on_submit=True):
    st.subheader(f"Spritzung erfassen – {parcel['name']}")
    c1, c2, c3 = st.columns(3)
    spray_date = c1.date_input("Datum", value=today, format="DD.MM.YYYY")
    prod_ids = products["id"].tolist()
    prod_default = prod_ids.index(proposal["product_id"]) if proposal.get("product_id") in prod_ids else 0
    product_id = c2.selectbox("Mittel", prod_ids, index=prod_default,
                              format_func=dict(zip(products["id"], products["name"])).get)
    bbchs = stages["bbch"].tolist()
    bbch_default = bbchs.index(proposal["bbch"]) if proposal.get("bbch") in bbchs else 0
    bbch = c3.selectbox("Stadium (BBCH)", bbchs, index=bbch_default)
    c4, c5 = st.columns(2)
    water = c4.number_input("Wasser (l/ha)", min_value=0.0, step=10.0,
                            value=float(proposal.get("water_l_ha", 300.0)))
    amount = c5.number_input("Mittelmenge total (kg bzw. l)", min_value=0.0, step=0.1,
                             value=float(proposal.get("amount_total", 0.0)))
    note = st.text_input("Bemerkung")
    if st.form_submit_button("Speichern", type="primary"):
        db.add_spray(parcel["id"], spray_date, product_id, bbch, water, amount, note)
        st.success("Spritzung gespeichert.")

if proposal:
    st.caption("Vorschlag aus dem Dosierungsrechner übernommen.")

# --- Schutzstatus -------------------------------------------------------------------
sprays_all = db.list_sprays(parcel["id"])
dates = [pd.Timestamp(d).date() for d in sprays_all["date"]]
last = protection.last_spray_before(dates, today)
until = protection.protected_until(last)
if until and until >= today:
    st.success(f"Geschützt bis {S.fmt(until)} (letzte Spritzung {S.fmt(last)}).")
else:
    st.warning("Kein aktiver Belag." + (f" Letzte Spritzung {S.fmt(last)}." if last else ""))

# --- Liste ----------------------------------------------------------------------------
st.subheader(f"Spritzungen {today.year}")
sprays = db.list_sprays(parcel["id"], year=today.year)
if sprays.empty:
    st.write("Noch keine Spritzungen erfasst.")
else:
    view = sprays[["id", "date", "product", "active_group", "bbch", "water_l_ha", "amount_total",
                   "unit", "note"]].copy()
    view["date"] = view["date"].map(lambda d: S.fmt(d, True))
    view.columns = ["ID", "Datum", "Mittel", "Gruppe", "BBCH", "Wasser l/ha", "Menge", "Einheit", "Bemerkung"]
    st.dataframe(view, hide_index=True, use_container_width=True)

    c1, c2 = st.columns([3, 1])
    to_delete = c1.selectbox("Eintrag löschen", sprays["id"],
                             format_func=lambda i: f"#{i} – " + S.fmt(sprays.set_index('id').at[i, 'date'], True))
    if c2.button("Löschen"):
        db.delete_spray(int(to_delete))
        st.rerun()

    # --- Jahresmengen ------------------------------------------------------------------
    st.subheader("Jahresmengen pro Wirkstoffgruppe")
    summary = limits.yearly_summary(sprays)
    summary["Limite"] = [
        "–" if pd.isna(mx) else ("⚠️ erreicht" if n >= mx else f"{int(n)}/{int(mx)}")
        for n, mx in zip(summary["anzahl"], summary["max_pro_jahr"])
    ]
    st.dataframe(summary.rename(columns={"active_group": "Gruppe", "anzahl": "Anzahl",
                                         "menge_total": "Menge", "kupfer_kg": "Kupfer kg",
                                         "max_pro_jahr": "max/Jahr"}),
                 hide_index=True, use_container_width=True)
    cu_ha = summary["kupfer_kg"].sum() / float(parcel["area_ha"])
    st.metric("Reinkupfer pro ha", f"{cu_ha:.2f} kg", f"Limite {limits.COPPER_LIMIT_KG_HA} kg/ha",
              delta_color="off")
