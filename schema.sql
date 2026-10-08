-- Spritzplaner: SQLite-Schema
-- Gegenüber dem Projektplan ergänzt: products.unit (kg oder l)

CREATE TABLE IF NOT EXISTS parcels (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    area_ha   REAL NOT NULL,
    variety   TEXT,
    lat       REAL,
    lon       REAL,
    station   TEXT
);

CREATE TABLE IF NOT EXISTS products (
    id                INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,
    active_group      TEXT,
    concentration_pct REAL NOT NULL,
    unit              TEXT DEFAULT 'kg',
    max_per_year      INTEGER,
    copper_pct        REAL DEFAULT 0,
    heat_sensitive    INTEGER DEFAULT 0,
    needs_folpet      INTEGER DEFAULT 0,
    protection_days   INTEGER DEFAULT 10
);

CREATE TABLE IF NOT EXISTS stages (
    bbch           TEXT PRIMARY KEY,
    label          TEXT NOT NULL,
    base_broth_l_ha REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sprays (
    id           INTEGER PRIMARY KEY,
    parcel_id    INTEGER REFERENCES parcels(id) ON DELETE CASCADE,
    date         TEXT NOT NULL,
    product_id   INTEGER REFERENCES products(id),
    bbch         TEXT,
    water_l_ha   REAL,
    amount_total REAL,
    note         TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);
