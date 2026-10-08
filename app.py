"""Einstieg der Streamlit-App «Spritzplaner Rebberg».

Start:  streamlit run app.py
"""
import streamlit as st

import app_state
from db import database as db

st.set_page_config(page_title="Spritzplaner Rebberg", page_icon="🍇", layout="wide")

db.init_db()

pages = {
    "Heute": [
        st.Page("pages/dashboard.py", title="Dashboard", icon="🚦", default=True),
        st.Page("pages/kalender.py", title="Kalender", icon="📅"),
        st.Page("pages/wetter.py", title="Wetter", icon="🌦️"),
    ],
    "Arbeit": [
        st.Page("pages/dosierung.py", title="Dosierung", icon="🧪"),
        st.Page("pages/journal.py", title="Journal", icon="📒"),
        st.Page("pages/parzellen.py", title="Parzellen", icon="🗺️"),
    ],
    "Analyse": [
        st.Page("pages/modell.py", title="Modell", icon="🤖"),
    ],
}

nav = st.navigation(pages)
app_state.render_sidebar()
nav.run()
