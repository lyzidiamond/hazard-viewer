"""
Seed the counties table from Census data.

Sources:
  - Census Gazetteer (2023): county FIPS, name, state, and internal point lat/lng
  - Census API (2020 Decennial): county population
  - Census Cartographic Boundary (2023): county polygon boundaries

Run once after creating the schema:
  python db/seed_counties.py
"""

import csv
import io
import json
import logging
import os
import zipfile

import httpx
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "2023_Gazetteer/2023_Gaz_counties_national.zip"
)
CENSUS_POP_URL = (
    "https://api.census.gov/data/2020/dec/pl"
    "?get=NAME,P1_001N&for=county:*&in=state:*"
)
# 1:5m cartographic boundary from eric.clst.org — good balance of detail and file size for county display
BOUNDARY_URL = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"


def fetch_gazetteer() -> dict[str, dict]:
    """Download and parse Census Gazetteer counties file.

    Returns a dict keyed by 5-digit FIPS with name, state, lat, lng.
    """
    log.info("Fetching Census Gazetteer...")
    resp = httpx.get(GAZETTEER_URL, timeout=60, follow_redirects=True)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        filename = next(n for n in zf.namelist() if n.endswith(".txt"))
        with zf.open(filename) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8"), delimiter="\t")
            # headers = reader.fieldnames
            # log.info(f"Gazetteer columns: {headers}")
            # normalize header whitespace
            reader.fieldnames = [f.strip() for f in (reader.fieldnames or [])]
            counties = {}
            for row in reader:
                # GEOID is the 5-digit FIPS code
                fips = row["GEOID"].strip().zfill(5)
                counties[fips] = {
                    "fips": fips,
                    "name": row["NAME"].strip(),
                    "state": row["USPS"].strip(),
                    "lat": float(row["INTPTLAT"].strip()),
                    "lng": float(row["INTPTLONG"].strip()),
                }

    log.info(f"Loaded {len(counties)} counties from Gazetteer")
    return counties


def fetch_population() -> dict[str, int]:
    """Fetch 2020 decennial population for all counties.

    Returns a dict keyed by 5-digit FIPS with population count.
    """
    log.info("Fetching Census population data...")
    resp = httpx.get(CENSUS_POP_URL, timeout=60)
    resp.raise_for_status()

    data = resp.json()
    # first row is headers: [NAME, P1_001N, state, county]
    population = {}
    for row in data[1:]:
        fips = row[2].zfill(2) + row[3].zfill(3)
        population[fips] = int(row[1])

    log.info(f"Loaded population for {len(population)} counties")
    return population


def fetch_boundaries() -> dict[str, str]:
    """Download county boundary GeoJSON from eric.clst.org (sourced from 2010 Census cartographic boundary files).

    Returns a dict keyed by 5-digit FIPS with GeoJSON geometry string.
    """
    log.info("Fetching county boundaries...")
    resp = httpx.get(BOUNDARY_URL, timeout=120, follow_redirects=True)
    resp.raise_for_status()

    geojson = resp.json()

    boundaries = {}
    for feature in geojson["features"]:
        # plotly dataset uses feature id as the 5-digit FIPS code
        fips = str(feature["id"]).zfill(5)
        # store geometry as a JSON string for ST_GeomFromGeoJSON insertion
        boundaries[fips] = json.dumps(feature["geometry"])

    log.info(f"Loaded boundaries for {len(boundaries)} counties")
    return boundaries


def seed(conn, counties: dict, population: dict, boundaries: dict):
    rows = []
    for fips, county in counties.items():
        rows.append((
            fips,
            county["name"],
            county["state"],
            population.get(fips),
            county["lng"],
            county["lat"],
            boundaries.get(fips),
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO counties (fips, name, state, population, geom, boundary)
            VALUES %s
            ON CONFLICT (fips) DO UPDATE SET
                name       = EXCLUDED.name,
                state      = EXCLUDED.state,
                population = EXCLUDED.population,
                geom       = EXCLUDED.geom,
                boundary   = EXCLUDED.boundary
            """,
            rows,
            template="(%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), ST_GeomFromGeoJSON(%s))",
        )
    conn.commit()
    log.info(f"Seeded {len(rows)} counties")


def main():
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        with conn.cursor() as cur:
            # check specifically for boundary data — centroids alone aren't enough
            cur.execute("SELECT COUNT(*) FROM counties WHERE boundary IS NOT NULL")
            row = cur.fetchone()
            count = row[0] if row else 0
        if count > 0:
            log.info(f"Counties already seeded with boundaries ({count} rows), skipping")
            return

        counties = fetch_gazetteer()
        population = fetch_population()
        boundaries = fetch_boundaries()
        seed(conn, counties, population, boundaries)
    finally:
        conn.close()

    log.info("Done")


if __name__ == "__main__":
    main()
