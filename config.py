"""Zentrale Schwellenwerte und Pfade.

Alle Fachwerte stehen hier an einem Ort. Die Ampel-Grenzwerte sind Startwerte
und werden in der Tabelle ``settings`` überschrieben, sobald sie in der App
geändert werden.
"""
from pathlib import Path

# --- Pfade -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
DB_PATH = DATA_DIR / "spritzplaner.db"
MODEL_PATH = ROOT_DIR / "ml" / "model.joblib"

# --- Standort (Agrometeo-Station Zizers, ca.) ---------------------------------
ZIZERS_LAT = 46.93
ZIZERS_LON = 9.56
TIMEZONE = "Europe/Zurich"

# --- Formel 1: Temperatursumme / Keimbereitschaft ----------------------------
TEMP_BASE = 8.0                 # °C, Basistemperatur
GERMINATION_THRESHOLD = 140     # Σ max(Tmittel - 8, 0) ab 1.1.

# --- Formel 2: Infektion aus Gradstunden bei Blattnässe -----------------------
INFECTION_THRESHOLDS = (70, 100, 200)   # Stufe 1 (!), 2 (!!), 3 (!!!)
INFECTION_SYMBOLS = {0: "", 1: "!", 2: "!!", 3: "!!!"}
INFECTION_LABELS = {0: "keine", 1: "gering", 2: "mittel", 3: "stark"}

# --- Formel 3: Inkubation ----------------------------------------------------
INCUBATION_SUM = 70             # Methode B: Σ(Tmittel - 8) ab Infektion
SPRAY_DEADLINE_SHARE = 0.8      # «spritzen bis» = 80 % der Inkubationsdauer

# --- Formel 4: Schutzdauer eines Belags --------------------------------------
PROTECTION_DAYS = 10

# --- Blattnässe-Schätzung aus Open-Meteo -------------------------------------
WET_RAIN_MM = 0.1               # Stunde nass, wenn Regen > 0,1 mm ...
WET_RH_PCT = 90                 # ... oder rel. Feuchte >= 90 %

# --- Spritzfenster-Ampel (Startwerte, vom Winzer zu bestätigen) ---------------
DEFAULT_SETTINGS = {
    "rain_yellow_mm": 0.2,
    "rain_red_mm": 1.0,
    "wind_yellow_kmh": 15.0,
    "wind_red_kmh": 20.0,
    "heat_yellow_c": 28.0,
    "heat_red_c": 30.0,
    "sunday_red": 1.0,          # 1 = Sonntag ist rot
    "tank_l": 200.0,
    "spray_hours_from": 6.0,    # frühester Spritzbeginn (Uhr)
    "spray_hours_to": 14.0,     # spätester Spritzbeginn (Uhr)
}

# --- Saison ------------------------------------------------------------------
SEASON_END_MONTH_DAY = (9, 30)  # ML-Labels nur bis Ende September (≈ BBCH 81)
FORECAST_DAYS = 7
