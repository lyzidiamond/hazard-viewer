"""
Seed the counties table from Census data.

Sources:
  - Census Gazetteer (2023): county FIPS, name, state, and internal point lat/lng
  - Census API (2020 Decennial): county population

Run once after creating the schema:
  python db/seed_counties.py
"""

import csv
import io
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


def seed(conn, counties: dict, population: dict):
    rows = []
    for fips, county in counties.items():
        rows.append((
            fips,
            county["name"],
            county["state"],
            population.get(fips),
            county["lng"],
            county["lat"],
        ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO counties (fips, name, state, population, geom)
            VALUES %s
            ON CONFLICT (fips) DO UPDATE SET
                name       = EXCLUDED.name,
                state      = EXCLUDED.state,
                population = EXCLUDED.population,
                geom       = EXCLUDED.geom
            """,
            rows,
            template="(%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
        )
    conn.commit()
    log.info(f"Seeded {len(rows)} counties")


def main():
    counties = fetch_gazetteer()
    population = fetch_population()

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        seed(conn, counties, population)
    finally:
        conn.close()

    log.info("Done")


if __name__ == "__main__":
    main()
