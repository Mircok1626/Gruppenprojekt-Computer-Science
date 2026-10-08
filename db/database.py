"""SQLite-Zugriff (sqlite3 aus der Standardbibliothek): Parzellen, Mittel, Spritzungen.

Die Datenbankdatei liegt in ``data/spritzplaner.db`` und wird beim ersten
Start aus ``schema.sql`` erzeugt und mit ``products.csv`` / ``stages.csv``
befüllt. Für Tests kann der Pfad überall als Argument ``path`` übergeben werden.
"""
from __future__ import annotations

import csv
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from core import config

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def get_conn(path: Path | str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path or config.DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _none_if_empty(value):
    return None if value in ("", None) else value


def init_db(path: Path | str | None = None) -> None:
    """Erstellt die Tabellen und füllt Stammdaten, falls die DB leer ist."""
    with get_conn(path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))

        if conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            with open(config.DATA_DIR / "products.csv", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    conn.execute(
                        """INSERT INTO products (name, active_group, concentration_pct, unit,
                               max_per_year, copper_pct, heat_sensitive, needs_folpet,
                               protection_days)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (r["name"], r["active_group"], float(r["concentration_pct"]), r["unit"],
                         _none_if_empty(r["max_per_year"]), float(r["copper_pct"] or 0),
                         int(r["heat_sensitive"]), int(r["needs_folpet"]),
                         int(r["protection_days"] or config.PROTECTION_DAYS)),
                    )

        if conn.execute("SELECT COUNT(*) FROM stages").fetchone()[0] == 0:
            with open(config.DATA_DIR / "stages.csv", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    conn.execute("INSERT INTO stages VALUES (?, ?, ?)",
                                 (r["bbch"], r["label"], float(r["base_broth_l_ha"])))

        if conn.execute("SELECT COUNT(*) FROM parcels").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO parcels (name, area_ha, variety, lat, lon, station) VALUES (?,?,?,?,?,?)",
                ("Zizers Halde", 0.8, "Blauburgunder", config.ZIZERS_LAT, config.ZIZERS_LON, "zizers"),
            )


def query_df(sql: str, params: tuple = (), path=None) -> pd.DataFrame:
    with get_conn(path) as conn:
        return pd.read_sql_query(sql, conn, params=params)


# --- Parzellen ---------------------------------------------------------------
def list_parcels(path=None) -> pd.DataFrame:
    return query_df("SELECT * FROM parcels ORDER BY name", path=path)


def add_parcel(name: str, area_ha: float, variety: str, lat: float, lon: float,
               station: str = "zizers", path=None) -> int:
    with get_conn(path) as conn:
        cur = conn.execute(
            "INSERT INTO parcels (name, area_ha, variety, lat, lon, station) VALUES (?,?,?,?,?,?)",
            (name, area_ha, variety, lat, lon, station),
        )
        return cur.lastrowid


def update_parcel(parcel_id: int, name: str, area_ha: float, variety: str, lat: float,
                  lon: float, station: str, path=None) -> None:
    with get_conn(path) as conn:
        conn.execute(
            "UPDATE parcels SET name=?, area_ha=?, variety=?, lat=?, lon=?, station=? WHERE id=?",
            (name, area_ha, variety, lat, lon, station, parcel_id),
        )


def delete_parcel(parcel_id: int, path=None) -> None:
    with get_conn(path) as conn:
        conn.execute("DELETE FROM parcels WHERE id=?", (parcel_id,))


# --- Mittel und Stadien --------------------------------------------------------
def list_products(path=None) -> pd.DataFrame:
    return query_df("SELECT * FROM products ORDER BY name", path=path)


def list_stages(path=None) -> pd.DataFrame:
    return query_df("SELECT * FROM stages ORDER BY base_broth_l_ha, bbch", path=path)


# --- Spritzungen ---------------------------------------------------------------
def add_spray(parcel_id: int, spray_date: date, product_id: int, bbch: str,
              water_l_ha: float, amount_total: float, note: str = "", path=None) -> int:
    with get_conn(path) as conn:
        cur = conn.execute(
            """INSERT INTO sprays (parcel_id, date, product_id, bbch, water_l_ha, amount_total, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (parcel_id, spray_date.isoformat(), product_id, bbch, water_l_ha, amount_total, note),
        )
        return cur.lastrowid


def list_sprays(parcel_id: int | None = None, year: int | None = None, path=None) -> pd.DataFrame:
    """Spritzungen inkl. Mittel-Infos, neueste zuerst."""
    sql = """SELECT s.*, p.name AS product, p.active_group, p.unit, p.copper_pct,
                    p.max_per_year, p.protection_days, pa.name AS parcel
             FROM sprays s
             JOIN products p ON p.id = s.product_id
             JOIN parcels pa ON pa.id = s.parcel_id
             WHERE 1=1"""
    params: list = []
    if parcel_id is not None:
        sql += " AND s.parcel_id = ?"
        params.append(int(parcel_id))
    if year is not None:
        sql += " AND substr(s.date, 1, 4) = ?"
        params.append(str(year))
    sql += " ORDER BY s.date DESC"
    return query_df(sql, tuple(params), path=path)


def spray_dates(parcel_id: int, path=None) -> list[date]:
    df = list_sprays(parcel_id, path=path)
    return [date.fromisoformat(d) for d in df["date"]]


def delete_spray(spray_id: int, path=None) -> None:
    with get_conn(path) as conn:
        conn.execute("DELETE FROM sprays WHERE id=?", (spray_id,))


# --- Einstellungen ---------------------------------------------------------------
def get_settings(path=None) -> dict:
    """Ampel-Grenzwerte etc.; Standardwerte aus config, überschrieben durch die DB."""
    settings = dict(config.DEFAULT_SETTINGS)
    with get_conn(path) as conn:
        for row in conn.execute("SELECT key, value FROM settings"):
            settings[row["key"]] = float(row["value"])
    return settings


def set_setting(key: str, value: float, path=None) -> None:
    with get_conn(path) as conn:
        conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
