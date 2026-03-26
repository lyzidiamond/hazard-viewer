# Hazard Viewer

Hazard Viewer is a Python web app that takes a location in the United States and uses FEMA data and AI to generate a regional natural hazard risk assessment. Click on the map to see federal disaster declarations within 100km and a summary of the natural hazard risk in the area.

This is a demo app designed to demonstrate how you can deploy a multiservice application to Render in just a few steps. The special sauce here is the Render Blueprint -- the `render.yaml` file. With a Render Blueprint, all of the services are defined in the YAML file and deployed automatically when you push the file to your codebase.

- [Quickstart: Deploy to Render](#quickstart-deploy-to-render)
- [How the app works](#how-the-app-works)
- [Considerations and tradeoffs](#considerations-and-tradeoffs)
- [How to take this further](#how-to-go-further)

<!-- Where should I put info about natural hazards, hazard declarations, how the app actually works outside of the tech side? I think "how the app works" in a collapsed section -->

## Quickstart: Deploy to Render

You can deploy this app directly to Render without any additional configuration. The Render Blueprint provisions everything you need automatically.

### Prerequisites

The only thing you need outside of this codebase is an [Anthropic API Key](https://platform.claude.com/) so your app can prompt Claude to generate risk summaries. Everything else just works!

### Step 1: Fork this repository

Click "Fork" at the top right of this page to make your own copy of the project.

### Step 2: Deploy to Render

The Render Blueprint tells Render what services to provision and how to configure them. Click the button below to start provisioning immediately.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

<details>
<summary>If the button doesn't work</summary>
1. Open the Render dashboard and click **New > Blueprint**.
1. Find your newly forked repo in the list and click **Connect**.
1. Specify a name for the blueprint (e.g. "hazardviewer") and select the branch to link (should be `main`)
</details>

1. Review the list of services for Render to create as defined the Blueprint. There are four services:
  - `hazardviewer-api` (web service): a FastAPI web service/backend that contains all application logic
  - `hazardviewer-frontend` (static site): a React frontend that displays the map and hazard narrative
  - `hazardviewer-sync` (cron job): a cron job that runs nightly and syncs FEMA disaster designations to the database
  - `hazardviewer-db` (database): a PostgreSQL database that holds counties, FEMA disaster declarations, flood zones, and generated AI narratives
1. Add values for the two environment variables:
  - `ANTHROPIC_API_KEY`: the Anthropic API Key you generated for this project
  - `VITE_API_URL`: the URL used by the frontend to query the backend. Set to `https://hazardviewer-api.onrender.com`.
1. Click **Deploy Blueprint** to start provisioning.

Note: if you already have services with the same names as defined in your blueprint, Render will append something to the end of each of the services. It'll be the same thing. If that happens, add that appendage to the VITE_API_URL.

### Step 3: Trigger the cron job

In the Render dashboard for the `hazardviewer-sync` service, click **Trigger Run**. This initial run of the cron job populates the `declarations` database table with federal disaster declarations.

## How the app works

### Tech stack and specs

Four services

- The Postgres database houses county geometries, federal disaster declarations, and cached AI narratives keyed by location hash. The database uses the PostGIS extension for spatial indexing and queries.
- The nightly cron job updates the federal disaster declarations table from the [OpenFEMA API](https://www.fema.gov/about/openfema/api) and invalidates any cached AI narratives in the areas around the new declarations.
- The FastAPI web service routes different queries:
  - `/counties`: returns counties that intersect a 100km radius around a point as a GeoJSON FeatureCollection. This route is called by the frontend to render county boundaries on the map. 
  - `/declarations`: returns disaster declarations in counties within a 100km radius of a point. The `fetch_declarations` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
  - `/zone`: returns the National Flood Hazard Layer flood zone for the clicked location. The `get_zone` function defined in this route is called by `narrative.py` as information used to generate the hazard assessment, but it's also available as a public endpoint.
  - `/narrative`: generates and returns the hazard narrative displayed to the user. This route is called by the frontend when the map is clicked. It contains the main logic of the app: it generates context using disaster declarations and flood zones and passes them along with a detailed prompt to the LLM, which generates the narrative.
- The React frontend displays a clickable map and a flood hazard narrative panel. The frontend defines a `handleMapClick` function that sends the latitude and longitude of the clicked point to the `/narrative` endpoint and displays the returned narrative in a panel on the page.
- The Render Blueprint (`render.yaml`) defines these four services and provides information for Render to provision and deploy them automatically when the file is pushed to the project.

## Considerations and tradeoffs

- why I made these choices
- what I didn't include
- things I know that don't work

## How to go further

## What is a natural hazard?

Natural hazards are "environmental phenomena that have the potential to impact societies and the human environment" ([FEMA](https://www.fema.gov/sites/default/files/documents/fema_national-risk-index_technical-documentation.pdf)). These hazards include severe storms, flooding, drought, hurricanes, fire, snow, tornadoes, earthquakes, and other environmental events.

## What is a federal disaster declaration?

When natural hazards occur in the United States, the President has the option to declare the events as emergencies or major disasters. A declaration from the federal government allows FEMA to provide emergency funding for the affected counties.

## How does this app assess natural hazard risk?

Because this is a demo app to show what's possible with Render, 

<details>
<summary>Expand this section for more information about natural hazards and how risk is assessed at the government level</summary>

## How does one assess natural hazard risk?

Short answer: it's complicated. 

## What is a federal disaster declaration?

When natural hazards occur in the United States, the President has the option to declare the events as emergencies or major disasters. A declaration from the federal government 

</details>

## How does one assess natural hazard risk?

Short answer: it's complicated. 

## What is a federal disaster declaration?

When natural hazards occur in the United States, the President has the option to declare the events as emergencies or major disasters. A declaration from the federal government 

## What does the AI use to generate the risk assessment?

- federal disaster declarations
- flood zones
- adjacent counties
- claude prompt
