# Hazard Viewer

Hazard Viewer takes a location and uses FEMA data and AI to generate a regional natural hazard risk assessment. Click on the map to see federal disaster declarations within 100km and a summary of the natural hazard risk in the area.

## What are natural hazards?

## What does the AI use to generate the risk assessment?

- federal disaster declarations
- flood zones
- adjacent counties
- claude prompt

## How does the app work?

- The Postgres database houses county geometries, federal disaster declarations, and cached AI narratives keyed by location hash. The database uses the PostGIS extension for spatial indexing and queries.
- The nightly cron job updates the federal disaster declarations table from the [OpenFEMA API](https://www.fema.gov/about/openfema/api) and invalidates any cached AI narratives in the areas around the new declarations.
- The FastAPI web service routes different queries:
  - `/counties`: returns counties that intersect a 100km radius around a point as a GeoJSON FeatureCollection. This route is called by the frontend to render county boundaries on the map. 
  - `/declarations`: returns disaster declarations in counties within a 100km radius of a point. The `fetch_declarations` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
  - `/zone`: returns the National Flood Hazard Layer flood zone for the clicked location. The `get_zone` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
  - `/narrative`: generates and returns the hazard narrative displayed to the user. This route is called by the frontend when the map is clicked. It contains the main logic of the app: it generates context using disaster declarations and flood zones and passes them along with a detailed prompt to the LLM, which generates the narrative.
- The React frontend displays a clickable map and a flood hazard narrative panel. The frontend defines a `handleMapClick` function that sends the latitude and longitude of the clicked point to the `/narrative` endpoint and displays the returned narrative in a panel on the page.
- The Render Blueprint (`render.yaml`) defines these four services and provides information for Render to provision and deploy them automatically when the file is pushed to the project.

## Deploy to Render

This app requires an Anthropic API key. Generate one in your Anthropic dashboard.

1. Fork this repo to your GitHub account.
1. Open the Render dashboard and click **New > Blueprint**.
1. Find the forked repo in the list and click **Connect**.
1. Specify a name for the blueprint (e.g. "hazardviewer") and select the branch to link (should be `main`)
1. Review the list of services that Render will create based on the Blueprint. There are four services:
  1. `hazardviewer-api`: a FastAPI web service/backend that contains all application logic
  1. `hazardviewer-frontend`: a React frontend that displays the map and hazard narrative
  1. `hazardviewer-sync`: a cron job that runs nightly and syncs FEMA disaster designations to the database
  1. `hazardviewer-db`: a PostgreSQL database that holds counties, FEMA disaster declarations, flood zones, and generated AI narratives
1. The web service (something like "hazardviewer-api") and static site (something like "hazardviewer-frontend") each require you to set an environment variable.
  1. Set `ANTHROPIC_API_KEY` to the Anthropic API key you created in your Anthropic dashboard.
  1. Set `VITE_API_URL` to `https://[web service name].onrender.com` where `[web service name]` is the name of the web service being created ("hazardviewer-api" or similar).
1. Click **Deploy Blueprint** to start provisioning the project resources.
1. Go to the dashboard for `hazardviewer-sync` and click **Trigger Run** to populate the `declarations` database table with federal disaster declarations.