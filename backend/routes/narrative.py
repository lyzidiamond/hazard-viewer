import hashlib
import json
from datetime import datetime, timezone

import anthropic
from anthropic.types import TextBlock
from fastapi import APIRouter, Query, HTTPException

from db.connection import get_conn
from routes.declarations import fetch_declarations
from routes.zone import get_zone

router = APIRouter()

_anthropic = anthropic.AsyncAnthropic()

# two decimal place rounding gives us ~1km precision, which is good for caching without being too specific
def _location_hash(lat: float, lng: float) -> str:
    key = f"{round(lat, 2)},{round(lng, 2)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

# groups flood declarations into rough time periods to show trends without overfitting to specific years or events
def _build_trend(declarations: list[dict]) -> dict:
    trend = {"1953_1980": 0, "1981_2000": 0, "2001_2010": 0, "2011_present": 0}
    for d in declarations:
        year = d["incident_begin_date"].year if d["incident_begin_date"] else None
        if year is None:
            continue
        if year <= 1980:
            trend["1953_1980"] += 1
        elif year <= 2000:
            trend["1981_2000"] += 1
        elif year <= 2010:
            trend["2001_2010"] += 1
        else:
            trend["2011_present"] += 1
    return trend

# the prompt sent to Claude to generate the narrative
async def _generate_narrative(context: dict) -> str:
    prompt = f"""You are writing a natural hazard risk assessment for a layperson with minimal background in the field. Based on the following data, write a plain-English natural hazard risk narrative for this location. Be colloquial, but professional.

- The data includes all federal disaster declarations within 100km.
- If the selected location is outside of the United States, say "While this location is outside the United States and has no federal disaster declarations, it's important to consider local hazard history and risk factors when assessing natural hazard risk." and do not attempt to generate a narrative based on the provided data. Don't include the "general risk" section or the list of declarations, since those are based on US-specific data. Do not make up any information about the area.
- At the top, provide a bulleted list with all disaster declarations for the 100km area, including: date and county name. Format should be "2023 - Alameda County, CA". Group these by hazard type: top level bullet for hazard type, sub-bullets for each declaration. Include maximum three per type in reverse chronological order. if there are more than three for that type, add a fourth bullet that says "# more declarations" where # is the remaining number of declarations.
- Cover the full spectrum of natural hazard history (floods, hurricanes, tornadoes, severe storms, etc), historical frequency and trend, most significant events, and an overall risk characterization.
- Be factual and direct. 3-4 paragraphs. Paragraphs should not be more than 2 sentences long.
- Return as semantic HTML. Return only valid HTML. No Markdown, no code fences. Avoid using excessive bold and italics. Use <p> for paragraphs. Provide a title in an <h2>.
- ONLY If the area is in the United States, do an assessment of the hazards in that area and determine a risk value: very low, low, moderate, high, or very high. Do not include this if the area is outside the United States. Include that in an <h3> underneath the title in the format: "General risk:" followed by the value. If the area has a high frequency of severe storms and floods, for example, you might characterize it as "high" or "very high". If it has a long history of natural disasters with significant impacts, that would also contribute to a higher risk characterization. Conversely, if the area has few declarations and they are mostly minor events, it might be characterized as "low" or "very low". Use your judgment to synthesize the data into an overall risk assessment. Return "high" and "very high" values with red text, "low" and "very low" values with green text, and "moderate" values with orange text.
- At the end provide a link to the OpenFEMA endpoint you're using to pull hazard data from this specific location. Use the DisasterDeclarationSummaries endpoint. Make sure the query parameters in the URL are valid.

Data:
{json.dumps(context, indent=2, default=str)}"""

    message = await _anthropic.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": "<"},
        ],
    )
    if not isinstance(message.content[0], TextBlock):
        raise ValueError("Unexpected response type from Claude")
    return "<" + message.content[0].text


@router.get("/narrative")
async def get_narrative(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    location_hash = _location_hash(lat, lng)

    # return cached narrative if valid
    async with get_conn() as conn:
        cached = await conn.fetchrow(
            """
            SELECT narrative, flood_zone, generated_at
            FROM ai_narratives
            WHERE location_hash = $1 AND invalidated_at IS NULL
            """,
            location_hash,
        )

    if cached:
        return {
            "narrative": cached["narrative"],
            "flood_zone": cached["flood_zone"],
            "generated_at": cached["generated_at"],
            "cached": True,
        }

    # fetch fresh data
    declarations = await fetch_declarations(lat=lat, lng=lng, radius=100)
    zone = await get_zone(lat=lat, lng=lng)

    # group declarations by incident type for richer narrative context
    by_type = {}
    for d in declarations:
        t = d.get("incident_type") or "Unknown"
        by_type.setdefault(t, []).append(d)

    context = {
        "location": {"lat": lat, "lng": lng},
        "flood_zone": zone["flood_zone"],
        "flood_zone_description": zone["description"],
        "declaration_count": len(declarations),
        "declarations_by_type": {t: len(v) for t, v in by_type.items()},
        "declarations": declarations,
        "trend": _build_trend(declarations),
    }

    narrative = await _generate_narrative(context)

    # cache the result
    async with get_conn() as conn:
        await conn.execute(
            """
            INSERT INTO ai_narratives
                (location_hash, lat, lng, geom, flood_zone, narrative, raw_context)
            VALUES
                ($1, $2, $3, ST_SetSRID(ST_MakePoint($3, $2), 4326), $4, $5, $6)
            ON CONFLICT (location_hash) DO UPDATE SET
                narrative = EXCLUDED.narrative,
                flood_zone = EXCLUDED.flood_zone,
                raw_context = EXCLUDED.raw_context,
                generated_at = NOW(),
                invalidated_at = NULL
            """,
            location_hash, lat, lng, zone["flood_zone"], narrative,
            json.dumps(context, default=str)
        )

    return {
        "narrative": narrative,
        "flood_zone": zone["flood_zone"],
        "generated_at": datetime.now(timezone.utc),
        "cached": False,
    }


@router.post("/narrative/invalidate")
async def invalidate_narratives(lat: float, lng: float, radius_km: float = 100):
    radius_m = radius_km * 1000
    async with get_conn() as conn:
        result = await conn.execute(
            """
            UPDATE ai_narratives
            SET invalidated_at = NOW()
            WHERE invalidated_at IS NULL
            AND ST_DWithin(
                geom::geography,
                ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography,
                $3
            )
            """,
            lat, lng, radius_m,
        )
    # asyncpg returns a status string like "UPDATE 3" — split on space to get the count
    count = int(result.split(" ")[1])
    return {"invalidated": count}
