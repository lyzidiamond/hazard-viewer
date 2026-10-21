# Declarations route: gets FEMA disaster declarations within 100km of the clicked point
from typing import Optional

from fastapi import APIRouter, Query

from db.connection import get_conn

router = APIRouter()

# FEMA declaration types that aren't natural hazards (pandemics, human-caused events, fishery economic losses).
# excluded from the narrative and the map. "Other" and "Dam/Levee Break" are kept since they're often weather-driven
NON_NATURAL_TYPES = ["Biological", "Chemical", "Terrorist", "Human Cause", "Toxic Substances", "Fishing Losses"]


async def fetch_declarations(lat: float, lng: float, radius: int = 100, incident_type: Optional[str] = None) -> list[dict]:
    radius_m = radius * 1000 # convert radius from kilometers to meters for PostGIS query

    # query the database for disaster declarations based on the provided latitude, longitude, and radius
    # note: PostGIS queries use longitude first, then latitude (ST_MakePoint(lng, lat))
    # the table has one row per county per disaster, so DISTINCT ON keeps one row per disaster --
    # the nearest affected county -- so a disaster covering many nearby counties is only counted once
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM (
            SELECT DISTINCT ON (disaster_number)
                disaster_number,
                county_name,
                state,
                incident_type,
                incident_begin_date,
                incident_end_date,
                declaration_type,
                programs_declared,
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
                ) / 1000 AS distance_km
            FROM disaster_declarations
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                $3
            )
            AND (incident_type IS NULL OR incident_type <> ALL($5::text[]))
            AND ($4::text IS NULL OR incident_type = $4)
            ORDER BY disaster_number, distance_km
            ) nearest
            ORDER BY incident_begin_date DESC
            """,
            lat, lng, radius_m, incident_type, NON_NATURAL_TYPES,
        )

    return [dict(row) for row in rows] # convert asyncpg Record objects to regular dicts for JSON serialization


@router.get("/declarations")
async def get_declarations(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(100, ge=1, le=500),
    incident_type: Optional[str] = Query(None),
):
    return await fetch_declarations(lat, lng, radius, incident_type)
