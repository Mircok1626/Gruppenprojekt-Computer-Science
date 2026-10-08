# 🍇 Spritzplaner Rebberg

Streamlit-App, die Winzerinnen und Winzern sagt, **wann gegen Falschen Mehltau
(Plasmopara viticola) gespritzt werden muss**: Infektions-Alarm mit «spritzen bis»,
Ampel-Kalender für Spritzfenster, Brühe- und Mittelrechner, Spritzjournal (SQLite)
und ein eigenes ML-Modell, das Infektionen aus der Wetterprognose vorhersagt.

> Entscheidungshilfe – ersetzt keine Pflanzenschutzberatung.

## Start

```bash
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Tests: `pytest`  ·  Modell trainieren: `python -m ml.train` (oder Button auf der Seite «Modell»)

## Demo-Modus

In der Sidebar «Demo (Simulation)» wählen und mit dem Schieberegler «Heute ist der …»
einen Tag der Saison 2024–2026 einstellen (Standard: 07.05.2026). Vergangene Tage
kommen aus den gemessenen Agrometeo-Tabellen, die «Prognose» der nächsten 14 Tage
aus dem Open-Meteo-Archiv (echtes Wetter, geschätzte Blattnässe).
Alle Seiten verwenden dafür nur `app_state.get_today()`.

## Architektur

Drei Schichten, strikt getrennt:

| Schicht | Ordner | Inhalt |
|---|---|---|
| Daten | `core/weather.py`, `core/agrometeo.py`, `db/` | Open-Meteo-API, Agrometeo-CSV, SQLite |
| Logik | `core/*.py`, `ml/` | reine Python-Funktionen, ohne Streamlit, mit Tests |
| Oberfläche | `app.py`, `app_state.py`, `pages/` | Streamlit-Seiten |

| Modul | Fachlogik |
|---|---|
| `core/infection.py` | Formel 1 + 2: Temperatursumme ≥ 140 → Keimbereitschaft; Gradstunden bei Blattnässe 70/100/200 → Stufe !/!!/!!! |
| `core/incubation.py` | Formel 3: Inkubationsende (A = Agrometeo, B = Σ(Tmittel − 8) bis 70) und «spritzen bis» (80 %) |
| `core/protection.py` | Formel 4: Belag schützt 10 Tage; Status geschützt/behandelt/offen/verpasst |
| `core/dosage.py` | Formel 5: Mittel pro ha, Parzelle, Tankfüllung |
| `core/spray_window.py` | Ampel: Regen im 6-h-Fenster, Wind, Hitze (bei hitzeempfindlichem Mittel), Sonntag |
| `core/season.py` | setzt alles zur Saison-Auswertung zusammen |

Kontrolle gegen Agrometeo Zizers 2026: Keimbereitschaft 26.04.2026, 43 von 43 Infektionen
erkannt, 5 Fehlalarme (`tests/test_infection.py`).

## Datenquellen

- **Open-Meteo** Forecast + Archive (REST, kein Schlüssel): Temperatur, Feuchte, Taupunkt, Regen, Wind (stündlich)
- **Agrometeo / VitiMeteo Plasmopara**, Station Zizers 2024–2026 (`data/processed/zizers_<jahr>.csv`, Original-PDFs in `data/raw/`)
- **Agroscope** Transfer Nr. 626 (Pflanzenschutzmittelliste) – `data/products.csv` und `data/stages.csv` sind **Platzhalter** und müssen noch abgeglichen werden
- **SQLite** (`data/spritzplaner.db`, wird beim ersten Start erzeugt)

## ML

Random Forest (`class_weight="balanced"`) auf Tagesfeatures aus Open-Meteo
(Temperatur, Regen, Stunden mit Feuchte ≥ 90 %, geschätzte Gradstunden, Taupunkt-Differenz,
Temperatursumme, Regen der letzten 3 Tage, Tag im Jahr). Labels = Agrometeo-Infektion ja/nein.
Zeitlicher Split: frühere Jahre = Training, letztes Jahr = Test. Baseline: Regel «geschätzte
Gradstunden ≥ 70». Das Modell wird als `ml/model.joblib` gespeichert; die App lädt es nur.

## Deployment (Streamlit Community Cloud)

Repo verbinden, Main file `app.py`. Vorher lokal `python -m ml.train` ausführen und
`ml/model.joblib` committen. Hinweis: Die SQLite-Datei ist in der Cloud nicht dauerhaft –
Journal-Einträge gehen bei einem Neustart verloren (für die Demo ausreichend).

## Team

Siehe `CONTRIBUTIONS.md`. KI-Nutzung siehe `AI_USAGE.md`.
