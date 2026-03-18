-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- County centroids lookup (seeded once from Census TIGER data)
CREATE TABLE counties (
    fips        CHAR(5) PRIMARY KEY,
    name        TEXT NOT NULL,
    state       TEXT NOT NULL,
    population  INTEGER,
    geom        GEOMETRY(Point, 4326) NOT NULL
);
CREATE INDEX counties_geom_idx ON counties USING GIST(geom);

-- Flood disaster declarations (synced nightly from OpenFEMA)
CREATE TABLE flood_declarations (
    disaster_number     INTEGER PRIMARY KEY,
    state               TEXT NOT NULL,
    county_fips         CHAR(5),
    county_name         TEXT,
    incident_begin_date DATE,
    incident_end_date   DATE,
    declaration_date    DATE,
    declaration_type    TEXT,
    programs_declared   TEXT[],
    geom                GEOMETRY(Point, 4326),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX flood_declarations_geom_idx ON flood_declarations USING GIST(geom);
CREATE INDEX flood_declarations_date_idx ON flood_declarations(incident_begin_date);

-- Cached AI narratives (keyed by location hash)
CREATE TABLE ai_narratives (
    id              SERIAL PRIMARY KEY,
    location_hash   TEXT UNIQUE NOT NULL,
    lat             DOUBLE PRECISION NOT NULL,
    lng             DOUBLE PRECISION NOT NULL,
    geom            GEOMETRY(Point, 4326) NOT NULL,
    flood_zone      TEXT,
    narrative       TEXT NOT NULL,
    raw_context     JSONB,
    generated_at    TIMESTAMPTZ DEFAULT NOW(),
    invalidated_at  TIMESTAMPTZ
);
CREATE INDEX ai_narratives_geom_idx ON ai_narratives USING GIST(geom);

-- Sync state (tracks last successful OpenFEMA sync timestamp)
CREATE TABLE sync_state (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);
