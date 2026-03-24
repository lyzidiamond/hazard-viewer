# Counties route: queries database for interesecting counties and returns GeoJSON for frontend rendering with MapLibre
import json

from fastapi import APIRouter, Query

from db.connection import get_conn

router = APIRouter()


@router.get("/counties")
async def get_counties(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(100, ge=1, le=500),
):
    radius_m = radius * 1000

    async with get_conn() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.fips,
                c.name,
                c.state,
                ST_AsGeoJSON(c.boundary) AS geometry,
                json_object_agg(d.incident_type, d.count) AS declarations_by_type
            FROM counties c
            JOIN (
                SELECT
                    county_fips,
                    incident_type,
                    COUNT(*) AS count
                FROM disaster_declarations
                WHERE ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                    $3
                )
                AND county_fips IS NOT NULL
                AND incident_type IS NOT NULL
                GROUP BY county_fips, incident_type
            ) d ON c.fips = d.county_fips
            WHERE c.boundary IS NOT NULL
            GROUP BY c.fips, c.name, c.state, c.boundary
            """,
            lat, lng, radius_m,
        )

    # build a GeoJSON FeatureCollection — MapLibre consumes this directly as a source
    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "fips": row["fips"],
                "name": row["name"],
                "state": row["state"],
                "declarations_by_type": json.loads(row["declarations_by_type"]) if isinstance(row["declarations_by_type"], str) else dict(row["declarations_by_type"]),
            },
        })

    return {"type": "FeatureCollection", "features": features}
