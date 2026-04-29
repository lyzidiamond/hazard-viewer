# Hazard Viewer

[Hazard Viewer](https://hazardviewer-frontend-87s3.onrender.com/) is a Python web app that takes a location and uses FEMA data and AI to generate a regional natural hazard risk assessment. Click on the map to see federal disaster declarations within 100km and a summary of the natural hazard risk in the area. The app is currently [deployed on Render](https://hazardviewer-frontend.onrender.com/).

<img width="949" height="684" alt="Screenshot 2026-03-26 at 3 55 39 PM" src="https://github.com/user-attachments/assets/45e4319c-00ce-427d-967e-ea3c9701662c" />


This is a demo app designed to demonstrate how you can [deploy a multiservice AI application to Render](https://render.com/docs/multi-service-architecture) in just a few steps. The special sauce here is the [Render Blueprint](https://render.com/docs/infrastructure-as-code) -- the `render.yaml` file. With a Render Blueprint, all of the services are defined in the YAML file and deployed automatically when you push the file to your codebase.

## Why I built this

My first job out of college was as a GIS Technician at the Oregon Department of Geology and Mineral Industries working on floodplain delineation and mapping contracts for [FEMA's Risk Mapping, Assessment and Planning](https://www.fema.gov/flood-maps/tools-resources/risk-map) program. I worked on two key parts of these projects: I wrote discovery reports on natural hazards in the contract region, and I created the flood zone data to go in the National Flood Hazard Layer dataset. This data is still used to this day (as far as I know Oregon's coastal counties haven't been updated in the last 15 years).

This data is buried in regulatory documents and not super accessible to someone who wants to learn more about their flood risks. The original goal of this project was to create an app that makes flood risks visible and accessible.

The first version of Hazard Viewer was called Flood Report, and it showed the location's flood zone designation and a brief narrative about what that designation means. This was exciting, but didn't go quite far enough -- why limit the risk narrative to just floods when we have access to information about all natural hazards?

And thus Hazard Viewer was born. The app expands on the original logic: instead of just pulling down and storing flood disaster declarations, the database stores all disaster declarations. Instead of the Claude prompt asking for flood risk summaries, the app asks for summaries of all natural hazards. The result is an overall more useful product that gives comprehensive information about natural hazard risks.

## Table of Contents

- [Quickstart: Deploy to Render](#quickstart-deploy-to-render)
- [How the app works](#how-the-app-works)
- [Considerations and tradeoffs](#considerations-and-tradeoffs)
- [How to go further](#how-to-go-further)

## Quickstart: Deploy to Render

You can deploy this app directly to Render without any additional configuration. The Render Blueprint provisions everything you need automatically, getting you up and running in just a couple minutes.

### Prerequisites

The only thing you need outside of this codebase is an [Anthropic API Key](https://platform.claude.com/) so your app can prompt Claude to generate risk summaries. Everything else just works!

### Step 1: Fork this repository

Click "Fork" at the top right of this page to make your own copy of the project.

### Step 2: Deploy to Render

The Render Blueprint tells Render what services to provision and how to configure them.

1. Click the button below to start provisioning immediately. Render will automatically read the Blueprint and give you a list of services to be provisioned.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

2. Review the list of services:
  - `hazardviewer-api` (web service): a FastAPI web service/backend that contains all application logic
  - `hazardviewer-frontend` (static site): a React frontend that displays the map and hazard narrative
  - `hazardviewer-sync` (cron job): a cron job that runs nightly and syncs FEMA disaster designations to the database
  - `hazardviewer-db` (database): a PostgreSQL database that holds counties, FEMA disaster declarations, flood zones, and generated AI narratives
3. Add values for the environment variables:
  - `ANTHROPIC_API_KEY`: the Anthropic API Key you generated for this project
  - `VITE_API_URL`: the URL used by the frontend to query the backend. Leave this blank until all of the services have been provisioned.
4. Click **Deploy Blueprint** to start provisioning.
5. Once the services have been provisioned, go to the dashboard for `hazardviewer-api` and copy the URL at the top. It will look something like `https://hazardviewer-api-xyz.onrender.com`.
6. Go to the dashboard for `hazardviewer-frontend` and click **Environment**. Use the copied URL as the value for `VITE_API_URL` and click **Manual Deploy** at the top of the page.

### Step 3: Trigger the cron job

In the Render dashboard for the `hazardviewer-sync` service, click **Trigger Run**. This initial run of the cron job populates the `disaster_declarations` database table with federal disaster declarations.

### Step 4: The app is live!

In the Render dashboard, go to the `hazardviewer-frontend` service and click the URL at the top of the page to see your live app.

## How the app works

- [What is a natural hazard risk assessment?](#what-is-a-natural-hazard-risk-assessment)
- [Tools used](#tools-used)
- [The database](#the-database)
- [The cron job](#the-cron-job)
- [The web service](#the-web-service)
- [The frontend](#the-frontend)
- [Generating the risk assessment summary](#generating-the-risk-assessment-summary)


### What is a natural hazard risk assessment?

Natural hazards are "environmental phenomena that have the potential to impact societies and the human environment" ([FEMA](https://www.fema.gov/sites/default/files/documents/fema_national-risk-index_technical-documentation.pdf)). These hazards include severe storms, flooding, drought, hurricanes, fire, snow, tornadoes, earthquakes, and other environmental events.

When natural hazards occur in the United States, the President has the option to declare the events as emergencies or major disasters. A declaration from the federal government allows FEMA to provide emergency funding for the affected counties.

Disaster declarations aren't a perfect tracker for natural hazards, but they're a good indicator of major regional events that have affected humans and the environment. This app uses these disaster declarations and other hazard tracking information as indicators of locational risk.

### Tools used

Hazard Viewer uses the following tools:

- [FastAPI](https://fastapi.tiangolo.com/) as the Python web app framework
- [PostgreSQL](https://www.postgresql.org/) as the database with the [PostGIS](https://postgis.net/) extension for spatial queries and indexing
- [React](https://react.dev/) and [Vite](https://vite.dev/) as the frontend framework
- [MapLibre GL JS](https://maplibre.org/projects/gl-js/) for the interactive map
- The [OpenFEMA API](https://www.fema.gov/about/openfema/api) for federal disaster declarations
- [FEMA's ArcGIS REST service](https://www.fema.gov/flood-maps/national-flood-hazard-layer) for flood zone classifications
- [Census Gazetteer](https://www.census.gov/geographies/reference-files/time-series/geo/gazetteer-files.html) and [Plotly datasets](https://github.com/plotly/datasets) for county information and boundaries
- [Anthropic's Claude API (Claude Sonnet)](https://www.anthropic.com/claude/sonnet) to generate the AI narratives
- [Render Blueprint](https://render.com/docs/infrastructure-as-code) to quickly provision all services

### The database

The PostgreSQL database has four tables:

- `counties`: one row for each US county with FIPS codes and geospatial locations
- `disaster_declarations`: United States disaster declarations with incident information and a geospatial location
- `ai_narratives`: cached AI narratives with a location hash for spatial lookup
- `sync_state`: a very small table that tracks the last successful disaster declarations sync

Every table (except `sync_state`) includes geospatial fields enabled by the PostGIS extension. PostGIS allows for spatial queries, which means the app can, for example, request all counties within a certain radius of a point. Doing these calculations via PostGIS means the spatial work happens in the database rather than in Python on the application side -- with 70 years of disaster declarations, the database is the right place for this work.

### The cron job

The nightly cron job ([sync_fema.py](/cron/sync_fema.py)) updates the federal disaster declarations table from the [OpenFEMA API](https://www.fema.gov/about/openfema/api) and invalidates any cached AI narratives in the areas around the new declarations. The script doesn't truncate and reload the data each night, but rather upserts by `disaster_number`. This allows cached narratives to stay valid until there's actually new data nearby, whereas truncating and reloading would clear the cache and invalidate every narrative.

### The web service

The FastAPI web service defines four public routes:

- `/counties`: returns counties that intersect a 100km radius around a point as a [GeoJSON](https://geojson.org/) FeatureCollection. This route is called by the frontend to render county boundaries on the map. 
- `/declarations`: returns disaster declarations in counties within a 100km radius of a point. The `fetch_declarations` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
- `/zone`: returns the [National Flood Hazard Layer](https://www.fema.gov/flood-maps/national-flood-hazard-layer) flood zone for the clicked location. The `get_zone` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
- `/narrative`: generates and returns the hazard narrative displayed to the user. This route is called by the frontend when the map is clicked. It contains the main logic of the app: it generates context using disaster declarations and flood zones and passes them along with a detailed prompt to the LLM, which generates the narrative.

### The frontend

The React frontend displays a clickable map (created with [MapLibre GL JS](https://maplibre.org/projects/gl-js/)) and a natural hazard narrative panel. The frontend defines a `handleMapClick` function that sends the latitude and longitude of the clicked point to the `/narrative` endpoint and displays the returned risk assessment summary in a panel on the page. The map also shows counties within the 100km radius and the flood declarations for those counties.

### Generating the risk assessment summary

The risk assessment summary is generated by Claude. In order to keep the summary consistent and correct, the prompt includes the following instructions:

- **Persona:** writing for a layperson, colloquial but professional
- **Data scope:** all federal disaster declarations within 100km of the clicked point
- **Out-of-US handling:** return a specific canned message, skip US-specific sections, don't fabricate information                                            
- **Declaration list:** bulleted, grouped by hazard type, up to 3 per type in reverse chronological order with an overflow count, formatted as "2023 - Alameda County, CA"
- **Narrative body:** full hazard spectrum, historical frequency and trend, significant events, overall risk characterization — 3–4 paragraphs, max 2 sentences each
- **Risk level:** one of five values (very low → very high), color-coded in the HTML (red/orange/green), US locations only                                            
- **Output format:** semantic HTML starting directly with a tag, no code blocks or backticks — `<h2>` title, `<h3>` risk level, `<p>` paragraphs                          
- **Data source link:** OpenFEMA DisasterDeclarationsSummaries URL with query parameters, at the end only
- **Input data passed:** lat/lng, flood zone + description, total declaration count, count by incident type, full declarations list, decade-bucketed trend counts

## Considerations and tradeoffs

The goal of Hazard Viewer is to show what's possible when deploying a multiservice app with Render. Each decision was made to demonstrate and highlight different deployment decisions and best practices for building Render-deployable apps quickly.

1. **Using all hazard data, not just flood data.** Originally, this app was a flood risk assessment tool. I expanded it to include all natural hazards to make the risk summaries more compelling and useful.
2. **Using PostGIS for spatial queries instead of application-level math.** PostGIS makes sense as the analysis engine for large geospatial queries to decrease application bloat and make the app quicker overall.
3. **Using the best database driver for the runtime.** This app uses both `asyncpg` and `psycopg2` drivers for different purposes. The FastAPI API routes use `asyncpg` to fit FastAPI's async request handling, while the cron job and seed script use `psycopg2` for simplicity and speed.
4. **Querying the National Flood Hazard Layer live instead of storing in the database.** Flood zone polygons are large, change periodically, and are only needed for single point lookup. Storing them would mean managing a large dataset with a refresh cycle. It's faster and creates less database pressure to proxy FEMA's web service on demand.
5. **Caching narratives by location hash.** Instead of calling Claude for every single location, the app caches the risk summary narratives at ~1km precision. This means only making requests to Claude for new locations, increasing the speed of the app and saving tokens. The app also has logic to invalidate cached narratives when there are new disaster declarations in the area, so the narratives always stay fresh and accurate.
6. **Using `sync: false` for `VITE_API_URL` in the Blueprint.** While this adds an additional step to the deploy process, it's important: `fromService` doesn't provide an option that includes the protocol and domain, which the browser needs to fetch from the backend. Having the user include the URL by setting the environment variable manually ensures it works with every fork.
7. **Setting `preDeployCommand` for schema and seed in the Blueprint.** The `preDeployCommand` sets the database schema and seeds the counties table, but the seed script only runs if the counties table hasn't yet been seeded. This saves time and effort and makes sure there's no duplicated data.
8. **Making sure Claude summaries are both quick and accurate.** The app uses Claude Sonnet 4.6 instead of Claude Haiku. I tried both -- Haiku was faster and used fewer tokens, but the narratives were inconsistent and not always correct. Because of the nature of the information, it made sense to use Sonnet, even though it takes longer. The prompt also tells Claude to return semantic HTML instead of adding that logic in the app -- this constrains the output to work specifically with the frontend, but could easily be changed if you wanted to use the `/narrative` endpoint for other applications.

### Some app weirdness

- **Connecticut doesn't work and Virginia looks strange.** Federal data is often inconsistent. Each county has a FIPS code to better categorize and connect data, but those codes aren't static: in 2022, Connecticut started managing its federal data not by county, but by administrative planning region. These regions all have new FIPS codes, which means the federal disaster declarations no longer match the counties. Similarly, Virginia separates its data into both counties and cities, so some declarations are specific to cities.
- **The narrative can take a while to generate.** Using Claude Sonnet is more accurate than Haiku, but makes the narrative generation slower.
- **It doesn't look beautiful on mobile.** This app is designed for desktop, not mobile. It works on mobile, but you can't see the map and the narrative panel at the same time -- you tap a location, the narrative panel appears, and the map is visible when you dismiss it.

## How to go further

One of the nice things about this app is how many different ways you can extend it.

1. **Auth and storage for specific narratives.** Users can log in and see the narratives for the places they care about and when they've been updated. Auth would also enable rate limiting, protecting your Anthropic account from getting hammered with requests.
2. **Deep linking.** Users can share the narratives for specific locations with deep links that include the queried location.
3. **Additional frontend features.** There are several enhancements that can be made on the frontend side to reel users in: add a location lookup instead of just map clicks, make the layout usable on mobile, zoom to current location, etc.
4. **Additional data sources.** FEMA maintains a National Risk Index that reflects its own risk analysis, but it doesn't have a publicly accessible API. Add logic to pull down the data, add it to the database, and use it as part of the risk context sent to Claude to help generate the narrative. Another option is to populate the `population` column in the `counties` table (currently in the table but empty) and use the data to enable per-capita risk normalization.
5. **Fix Connecticut and future-proof against other county changes.** This is some low-hanging fruit but could be fixed by finding or creating a more-frequently-updated county boundary dataset.
