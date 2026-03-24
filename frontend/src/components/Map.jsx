import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import * as turf from "@turf/turf";
import { getCounties } from "../api/client";

const EMPTY_GEOJSON = { type: "FeatureCollection", features: [] };

export default function Map({ onMapClick }) {
  const mapContainer = useRef(null);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-98.5795, 39.8283], // center of US
      zoom: 3,
      attributionControl: false,
    });

    const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false });

    map.on("load", () => {
      map.addSource("county-boundaries", { type: "geojson", data: EMPTY_GEOJSON });
      map.addSource("query-radius", { type: "geojson", data: EMPTY_GEOJSON });
      map.addSource("clicked-point", { type: "geojson", data: EMPTY_GEOJSON });

      // county fill — rendered before the radius and point so it sits underneath
      map.addLayer({
        id: "county-fill",
        type: "fill",
        source: "county-boundaries",
        paint: {
          "fill-color": ["case", ["boolean", ["get", "has_declarations"], false], "#da4545", "#888888"],
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 0.25, 0.2],
        },
      });

      map.addLayer({
        id: "county-line",
        type: "line",
        source: "county-boundaries",
        paint: {
          "line-color": ["case", ["boolean", ["get", "has_declarations"], false], "#da4545", "#888888"],
          "line-width": 1,
          "line-opacity": 0.4,
        },
      });

      map.addLayer({
        id: "query-radius",
        type: "fill",
        source: "query-radius",
        paint: { "fill-color": "#2c6fad", "fill-opacity": 0.35 },
      });

      map.addLayer({
        id: "clicked-point",
        type: "circle",
        source: "clicked-point",
        paint: { "circle-radius": 6, "circle-color": "#2c6fad" },
      });
    });

    // hover state tracking for county fill darkening
    let hoveredFips = null;

    map.on("mousemove", "county-fill", (e) => {
      if (!e.features.length) return;
      map.getCanvas().style.cursor = "pointer";

      const fips = e.features[0].properties.fips;
      if (fips === hoveredFips) return;

      if (hoveredFips) {
        map.setFeatureState({ source: "county-boundaries", id: hoveredFips }, { hover: false });
      }
      hoveredFips = fips;
      map.setFeatureState({ source: "county-boundaries", id: fips }, { hover: true });

      // build popup content from declarations_by_type
      const { name, state, declarations_by_type } = e.features[0].properties;
      const byType = typeof declarations_by_type === "string"
        ? JSON.parse(declarations_by_type)
        : declarations_by_type;

      const items = Object.entries(byType)
        .sort((a, b) => b[1] - a[1])
        .map(([type, count]) => `<li>${type}: ${count}</li>`)
        .join("");

      popup
        .setLngLat(e.lngLat)
        .setHTML(`<strong>${name}, ${state}</strong><ul style="margin:4px 0 0;padding-left:16px">${items}</ul>`)
        .addTo(map);
    });

    map.on("mouseleave", "county-fill", () => {
      map.getCanvas().style.cursor = "";
      if (hoveredFips) {
        map.setFeatureState({ source: "county-boundaries", id: hoveredFips }, { hover: false });
        hoveredFips = null;
      }
      popup.remove();
    });

    map.on("click", (e) => {
      const { lng, lat } = e.lngLat;
      map.flyTo({ center: e.lngLat, zoom: 7, essential: true });

      map.getSource("clicked-point").setData({
        type: "Feature",
        geometry: { type: "Point", coordinates: [lng, lat] },
      });
      map.getSource("query-radius").setData(
        turf.circle([lng, lat], 100, { units: "kilometers" })
      );

      // fetch county boundaries for the clicked location and update the source
      getCounties(lat, lng).then((geojson) => {
        // MapLibre feature state requires a unique id on each feature
        geojson.features = geojson.features.map((f) => ({ ...f, id: f.properties.fips }));
        map.getSource("county-boundaries").setData(geojson);
      });

      onMapClick(lat, lng);
    });

    map.addControl(new maplibregl.AttributionControl(), "top-left");

    return () => map.remove();
  }, []);

  return <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />;
}
