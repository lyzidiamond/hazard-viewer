# internal route called by narrative.py to get flood zone. provides additional information for narrative generation
import httpx
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

NFHL_URL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"

ZONE_DESCRIPTIONS = {
    "A":   "High risk — 1% annual flood chance (100-year flood zone), no detailed analysis",
    "AE":  "High risk — 1% annual flood chance, base flood elevations determined",
    "AH":  "High risk — shallow flooding (ponding), 1% annual chance",
    "AO":  "High risk — shallow sheet flow, 1% annual chance",
    "VE":  "High risk coastal — 1% annual chance with wave action",
    "X":   "Moderate to low risk — outside the 1% annual chance floodplain",
    "D":   "Undetermined risk — not studied",
}

# server acts as proxy to FEMA NFHL service
@router.get("/zone")
async def get_zone(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY",
        "returnGeometry": "false",
        "f": "json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(NFHL_URL, params=params)
    except httpx.TimeoutException:
        return {"flood_zone": None, "description": "Flood zone data unavailable"}

    if resp.status_code != 200:
        return {"flood_zone": None, "description": "Flood zone data unavailable"}

    data = resp.json()
    features = data.get("features", [])

    if not features:
        return {"flood_zone": None, "description": "No flood zone data for this location"}

    attrs = features[0]["attributes"]
    zone = attrs.get("FLD_ZONE", "").strip()
    subtype = attrs.get("ZONE_SUBTY", "")

    return {
        "flood_zone": zone,
        "zone_subtype": subtype,
        "description": ZONE_DESCRIPTIONS.get(zone, f"Flood zone {zone}"),
    }
