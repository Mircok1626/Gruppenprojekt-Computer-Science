# Konventionen für dieses Repo

- Sprache: Kommentare, Docstrings und UI-Texte auf Deutsch (Schweizer Schreibweise, «ss» statt «ß»).
- Stil: PEP 8, Docstring für jede Funktion mit Beispielwert aus den Unterlagen.
- Drei Schichten: Daten (`core/weather.py`, `core/agrometeo.py`, `db/`) → Logik (`core/`, `ml/`, ohne Streamlit) → Oberfläche (`app.py`, `app_state.py`, `pages/`).
- «Heute» immer über `app_state.get_today()` (Demo-Modus).
- Schwellenwerte nur in `core/config.py` bzw. Tabelle `settings`.
- Zuerst Test schreiben (`tests/`), dann Funktion; `pytest` muss grün sein.
- Keine neuen Bibliotheken ohne Rückfrage im Team.
- KI-generierten Code im Code kennzeichnen (Block «KI-generierter Code») und in `AI_USAGE.md` eintragen.
