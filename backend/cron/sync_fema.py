import asyncio
import httpx
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values
from shapely.geometry import Point

# logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# info about FEMA API, how many records to fetch at once, etc.
OPENFEMA_URL = "https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries"
PAGE_SIZE = 1000
BATCH_SIZE = 500


# connect to db
def get_db():
    return psycopg2.connect(os.environ["DATABASE_URL"])

# get the value of the last sync timestamp from the database (in sync_state table)
def get_last_sync(conn) -> Optional[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT value FROM sync_state WHERE key = 'last_fema_sync'")
        row = cur.fetchone()
        return row[0] if row else None

# set value of last sync after successful completion (in sync_state table)
def set_last_sync(conn, ts: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO sync_state (key, value, updated_at)
            VALUES ('last_fema_sync', %s, NOW())
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (ts,),
        )
    conn.commit()

# function to get the FEMA declarations
async def fetch_fema_declarations(since: Optional[str]) -> list[dict]:
    records = []
    skip = 0
    filters = []
    if since:
        filters.append(f"lastRefresh gt '{since}'")

    # fetch records, paginated
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {
                "$top": PAGE_SIZE,
                "$skip": skip,
                "$orderby": "disasterNumber asc",
            }
            if filters:
                params["$filter"] = " and ".join(filters)
            resp = await client.get(OPENFEMA_URL, params=params)
            resp.raise_for_status() # checks if response is 400 or 500
            data = resp.json()
            page = data.get("DisasterDeclarationsSummaries", [])
            records.extend(page)
            if len(page) < PAGE_SIZE:
                break
            skip += PAGE_SIZE
            log.info(f"Fetched {len(records)} records so far...")

    return records

# get county centroids by FIPS code -- takes FIPS code, queries counties table, returns a dict mapping (FIPS --> (lng, lat)). those coordinates then get used to build WKT geometry to get upserted
def get_county_centroids(conn, fips_codes: list[str]) -> dict[str, tuple[float, float]]:
    if not fips_codes:
        return {}
    with conn.cursor() as cur:
        cur.execute(
            "SELECT fips, ST_X(geom), ST_Y(geom) FROM counties WHERE fips = ANY(%s)",
            (fips_codes,),
        )
        return {row[0]: (row[1], row[2]) for row in cur.fetchall()}

# parse date from FEMA declaration
def parse_date(val: Optional[str]) -> Optional[str]:
    return val[:10] if val else None

# type of program: IH (individuals and households), IA (Individual Assistance), PA (public assistance), HM (hazard mitigation)
def build_programs(record: dict) -> list[str]:
    return [
        p for p in [
            "IH" if record.get("ihProgramDeclared") else None,
            "IA" if record.get("iaProgramDeclared") else None,
            "PA" if record.get("paProgramDeclared") else None,
            "HM" if record.get("hmProgramDeclared") else None,
        ] if p
    ]

# the sync function
async def sync():
    log.info("Starting FEMA disaster declaration sync...")
    conn = get_db() # connect to db
    last_sync = get_last_sync(conn) # set last_sync to response from get_last_sync
    sync_start = datetime.now(timezone.utc).isoformat() # set sync_start to now
    log.info(f"Last sync: {last_sync or 'never (full load)'}") # log the time of last sync

    records = await fetch_fema_declarations(since=last_sync) # call fetch_fema_declarations which returns a records array
    log.info(f"Fetched {len(records)} records from OpenFEMA") # log how many records were synced

    # if no new records, log and close connection
    if not records:
        log.info("No new records — sync complete")
        conn.close()
        return

    # bulk fetch all needed county centroids in one query
    fips_codes = list({
        r.get("fipsStateCode", "") + r.get("fipsCountyCode", "")
        for r in records
        if len(r.get("fipsStateCode", "") + r.get("fipsCountyCode", "")) == 5
    })
    centroids = get_county_centroids(conn, fips_codes) # get county centroids

    # build rows for bulk upsert, track centroids separately for invalidation
    rows = []
    delta_centroids = set()
    for record in records:
        fips = record.get("fipsStateCode", "") + record.get("fipsCountyCode", "")
        fips = fips if len(fips) == 5 else None # make sure fips code is 5 digits
        centroid = centroids.get(fips) if fips else None # get fips code from centroids
        lng, lat = centroid if centroid else (None, None)
        geom_wkt = Point(lng, lat).wkt if lng is not None and lat is not None else None # convert lat/lng to shapely wkt

        if lng is not None and lat is not None:
            delta_centroids.add((round(lng, 4), round(lat, 4))) # check if centroid is within 1km of existing narrative, if so invalidate narrative


        rows.append((
            record.get("disasterNumber"),
            record.get("state"),
            fips,
            record.get("designatedArea"),
            record.get("incidentType"),
            parse_date(record.get("incidentBeginDate")),
            parse_date(record.get("incidentEndDate")),
            parse_date(record.get("declarationDate")),
            record.get("declarationType"),
            build_programs(record),
            geom_wkt,
        ))

    # add deduplication by disaster_number before batching to avoid FEMA data duplicates
    seen = {}
    for row in rows:
        seen[row[0]] = row
    rows = list(seen.values())

    # bulk upsert in batches
    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO disaster_declarations (
                    disaster_number, state, county_fips, county_name,
                    incident_type, incident_begin_date, incident_end_date, declaration_date,
                    declaration_type, programs_declared, geom
                ) VALUES %s
                ON CONFLICT (disaster_number) DO UPDATE SET
                    incident_type       = EXCLUDED.incident_type,
                    incident_begin_date = EXCLUDED.incident_begin_date,
                    incident_end_date   = EXCLUDED.incident_end_date,
                    declaration_type    = EXCLUDED.declaration_type,
                    programs_declared   = EXCLUDED.programs_declared,
                    updated_at          = NOW()
                WHERE
                    disaster_declarations.incident_begin_date IS DISTINCT FROM EXCLUDED.incident_begin_date
                    OR disaster_declarations.incident_end_date IS DISTINCT FROM EXCLUDED.incident_end_date
                """,
                batch,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, ST_GeomFromText(%s, 4326))",
            )
        conn.commit()
        log.info(f"Upserted batch {i // BATCH_SIZE + 1}/{-(-len(rows) // BATCH_SIZE)}")

    # invalidate narratives near all records in the delta
    # (all fetched records are new or modified since last sync)
    if delta_centroids:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                UPDATE ai_narratives SET invalidated_at = NOW()
                WHERE invalidated_at IS NULL
                AND EXISTS (
                    SELECT 1 FROM (VALUES %s) AS pts(lng, lat)
                    WHERE ST_DWithin(
                        ai_narratives.geom::geography,
                        ST_SetSRID(ST_MakePoint(pts.lng, pts.lat), 4326)::geography,
                        100000
                    )
                )
                """,
                list(delta_centroids),
            )
        conn.commit()
        log.info(f"Invalidated narratives near {len(delta_centroids)} locations")

    set_last_sync(conn, sync_start)
    conn.close()
    log.info("Sync complete")


if __name__ == "__main__":
    asyncio.run(sync())
