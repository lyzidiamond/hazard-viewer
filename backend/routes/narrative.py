# Narrative route: returns the AI-generated narrative for the clicked location
import asyncio
import hashlib
import json
from datetime import datetime, timezone

import anthropic
from anthropic.types import TextBlock
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import StreamingResponse

from db.connection import get_conn
from limiter import limiter
from routes.declarations import fetch_declarations
from routes.zone import get_zone

router = APIRouter()

_anthropic = anthropic.AsyncAnthropic()

# two decimal place rounding gives us ~1km precision, which is good for caching without being too specific
def _location_hash(lat: float, lng: float) -> str:
    key = f"{round(lat, 2)},{round(lng, 2)}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]

# groups declarations into rough time periods to show trends without overfitting to specific years or events
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

# builds the declaration list HTML directly from structured data so Claude doesn't have to.
# groups by incident type, shows 3 per type with a <details> expander for the rest.
def _build_declaration_list(declarations: list[dict]) -> str:
    by_type: dict[str, list] = {}
    for d in declarations:
        t = d.get("incident_type") or "Unknown"
        by_type.setdefault(t, []).append(d)

    def fmt(d) -> str:
        date = d.get("incident_begin_date")
        year = str(date)[:4] if date else "Unknown"
        county = d.get("county_name") or "Unknown County"
        state = d.get("state") or ""
        return f"{year} - {county}, {state}"

    items = []
    for hazard_type, decls in sorted(by_type.items()):
        visible, overflow = decls[:3], decls[3:]
        lis = "".join(f"<li>{fmt(d)}</li>" for d in visible)
        if overflow:
            overflow_lis = "".join(f"<li>{fmt(d)}</li>" for d in overflow)
            lis += f'<li><details><summary>{len(overflow)} more declaration{"s" if len(overflow) != 1 else ""}</summary><ul>{overflow_lis}</ul></details></li>'
        items.append(f"<li>{hazard_type}<ul>{lis}</ul></li>")

    return f"<ul>{''.join(items)}</ul>"

# queries the counties table for the nearest US county to the clicked point.
# returns None if the point is more than 200km from any county (i.e. outside the US).
async def _get_nearest_county(lat: float, lng: float) -> dict | None:
    async with get_conn() as conn:
        row = await conn.fetchrow(
            """
            SELECT name, state,
                ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($2, $1), 4326)::geography) / 1000 AS dist_km
            FROM counties
            ORDER BY geom <-> ST_SetSRID(ST_MakePoint($2, $1), 4326)
            LIMIT 1
            """,
            lat, lng,
        )
    if row and row["dist_km"] < 200:
        return dict(row)
    return None

# computes a risk level algorithmically from declaration counts and trend.
# weights recent declarations (2011-present) 1.5x to reflect increasing hazard frequency.
def _compute_risk(declarations: list[dict], trend: dict) -> tuple[str, str] | None:
    if not declarations:
        return None
    total = len(declarations)
    recent = trend.get("2011_present", 0)
    score = (total - recent) + (recent * 1.5)
    if score >= 50:
        return "Very High", "red"
    elif score >= 30:
        return "High", "red"
    elif score >= 15:
        return "Moderate", "darkorange"
    elif score >= 5:
        return "Low", "green"
    else:
        return "Very Low", "green"

# assembles the Python-generated portion of the narrative: title, risk level, and declaration list.
# returns an empty string for non-US locations (Claude handles those entirely).
def _build_preamble(nearest_county: dict | None, risk: tuple[str, str] | None, list_html: str) -> str:
    if not nearest_county:
        return ""
    name, state = nearest_county["name"], nearest_county["state"]
    title = f"<h2>Natural Hazard Risk Assessment — {name}, {state}</h2>"
    risk_html = ""
    if risk:
        label, color = risk
        risk_html = f'<h3>General risk: <span style="color: {color}">{label}</span></h3>'
    return title + risk_html + list_html

# the prompt sent to Claude to generate the narrative.
# returns (system_prompt, user_message) to keep role and persona separate from the data.
# for US locations, Claude generates only the narrative paragraphs — title, risk, and declaration
# list are all handled by Python. for non-US locations, Claude generates the full response.
def _build_prompt(context: dict, is_us: bool) -> tuple[str, str]:
    lat = context["location"]["lat"]
    lng = context["location"]["lng"]
    data_source_url = f"https://api.fema.gov/open/v2/DisasterDeclarationsSummaries?lat={round(lat, 2)}&lng={round(lng, 2)}&radius=100"

    if is_us:
        system = """You are a natural hazard risk analyst writing plain-English assessments for a general audience. Be factual, direct, and colloquial but professional.

## Output format

Output 3-4 `<p>` paragraph tags only. The title, risk level, and declaration list are generated separately — do not include them. End with a data source paragraph.

<p>[paragraph]</p>
<p>[paragraph]</p>
<p>[paragraph]</p>
<p>Data source: <a href="[data_source_url]">[data_source_url]</a></p>

The very first character must be `<`. Do not use code blocks or backticks.

## Content requirements

Cover historical frequency and trend, most significant events, and overall risk characterization across all hazard types. Max 2 sentences per paragraph.

**Data source:** Use the URL provided in the data exactly as given. Place it only at the end."""
    else:
        system = """You are a natural hazard risk analyst writing plain-English assessments for a general audience. Be factual, direct, and colloquial but professional.

## Output format

This location is outside the United States. Output only:

<h2>Natural Hazard Risk Assessment — [general area name]</h2>
<p>While this location is outside the United States and has no federal disaster declarations, it's important to consider local hazard history and risk factors when assessing natural hazard risk.</p>

The very first character must be `<`. Do not use code blocks or backticks. Do not fabricate any information."""

    user = f"""Generate a natural hazard risk narrative for the following location.

Data:
{json.dumps({**context, "data_source_url": data_source_url}, indent=2, default=str)}"""

    return system, user


async def _generate_narrative(context: dict, nearest_county: dict | None, risk: tuple[str, str] | None) -> str:
    is_us = nearest_county is not None
    system, user = _build_prompt(context, is_us)
    message = await _anthropic.messages.create(
        model="claude-sonnet-4-6", # claude sonnet is a more robust model so it takes longer, but is more consistent than haiku or other faster models
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    if not isinstance(message.content[0], TextBlock):
        raise ValueError("Unexpected response type from Claude")
    preamble = _build_preamble(nearest_county, risk, _build_declaration_list(context["declarations"]))
    return preamble + message.content[0].text


@router.get("/narrative")
@limiter.limit("10/minute")
async def get_narrative(
    request: Request,
    response: Response,
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
    # get flood zone and nearest county in parallel
    zone, nearest_county = await asyncio.gather(
        get_zone(lat=lat, lng=lng),
        _get_nearest_county(lat, lng),
    )

    # group declarations by incident type for richer narrative context
    by_type = {}
    for d in declarations:
        t = d.get("incident_type") or "Unknown"
        by_type.setdefault(t, []).append(d)

    trend = _build_trend(declarations)
    risk = _compute_risk(declarations, trend)

    # create a context object to feed to the model when creating a narrative
    context = {
        "location": {"lat": lat, "lng": lng},
        "flood_zone": zone["flood_zone"],
        "flood_zone_description": zone["description"],
        "declaration_count": len(declarations),
        "declarations_by_type": {t: len(v) for t, v in by_type.items()},
        "declarations": declarations,
        "trend": trend,
    }

    narrative = await _generate_narrative(context, nearest_county, risk)

    # cache the result (add to database)
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

@router.get("/narrative/stream")
@limiter.limit("10/minute")
async def stream_narrative(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
):
    location_hash = _location_hash(lat, lng)

    async def generate():
        # return cached narrative immediately as a single chunk
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
            yield f"data: {json.dumps({'type': 'chunk', 'text': cached['narrative']})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'flood_zone': cached['flood_zone'], 'generated_at': cached['generated_at'].isoformat(), 'cached': True})}\n\n"
            return

        # fetch fresh data
        declarations = await fetch_declarations(lat=lat, lng=lng, radius=100)
        # get flood zone and nearest county in parallel
        zone, nearest_county = await asyncio.gather(
            get_zone(lat=lat, lng=lng),
            _get_nearest_county(lat, lng),
        )

        # group declarations by incident type for richer narrative context
        by_type = {}
        for d in declarations:
            t = d.get("incident_type") or "Unknown"
            by_type.setdefault(t, []).append(d)

        trend = _build_trend(declarations)
        risk = _compute_risk(declarations, trend)

        # create a context object to feed to the model when creating a narrative
        context = {
            "location": {"lat": lat, "lng": lng},
            "flood_zone": zone["flood_zone"],
            "flood_zone_description": zone["description"],
            "declaration_count": len(declarations),
            "declarations_by_type": {t: len(v) for t, v in by_type.items()},
            "declarations": declarations,
            "trend": trend,
        }

        # send the Python-generated preamble (title, risk, list) as the first chunk so it
        # appears immediately while Claude streams the paragraphs
        preamble = _build_preamble(nearest_county, risk, _build_declaration_list(declarations))
        if preamble:
            yield f"data: {json.dumps({'type': 'chunk', 'text': preamble})}\n\n"

        full_paragraphs = ""
        system, user = _build_prompt(context, is_us=nearest_county is not None)
        async with _anthropic.messages.stream(
            model="claude-sonnet-4-6", # claude sonnet is a more robust model so it takes longer, but is more consistent than haiku or other faster models
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                full_paragraphs += text
                yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"

        full_narrative = preamble + full_paragraphs

        # cache the result (add to database)
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
                location_hash, lat, lng, zone["flood_zone"], full_narrative,
                json.dumps(context, default=str)
            )

        yield f"data: {json.dumps({'type': 'done', 'flood_zone': zone['flood_zone'], 'generated_at': datetime.now(timezone.utc).isoformat(), 'cached': False})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# invalidate narrative. called if new disaster declarations are available within 100km
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
