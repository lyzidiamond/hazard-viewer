from fastapi import APIRouter, Query
from db.connection import get_conn

router = APIRouter()


@router.get("/floods")
async def get_floods(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(100, ge=1, le=500),
):
    radius_m = radius * 1000 # convert radius from kilometers to meters for PostGIS query

    # query the database for flood declarations based on the provided latitude, longitude, and radius
    # "$1", "$2", etc. are placeholders for the parameters passed after the query string (asyncpg)
    # note: PostGIS queries use longitude first, then latitude (ST_MakePoint(lng, lat))
    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT
                disaster_number,
                county_name,
                state,
                incident_begin_date,
                incident_end_date,
                declaration_type,
                programs_declared,
                ST_Distance(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography
                ) / 1000 AS distance_km
            FROM flood_declarations
            WHERE ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                $3
            )
            ORDER BY incident_begin_date DESC
            """,
            lat, lng, radius_m,
        )

    return [dict(row) for row in rows] # convert asyncpg Record objects to regular dicts for JSON serialization
