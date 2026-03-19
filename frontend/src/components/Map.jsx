import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import * as turf from "@turf/turf";
export default function Map({ onMapClick }) {
  const mapContainer = useRef(null);

  useEffect(() => {
    const map = new maplibregl.Map({
      container: mapContainer.current,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-98.5795, 39.8283], // center of US
      zoom: 3,
    });

    map.on("load", () => {
      map.addSource('clicked-point', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });
      map.addSource('query-radius', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      map.addLayer({
        id: 'query-radius',
        type: 'fill',
        source: 'query-radius',
        paint: {
          'fill-color': '#2c6fad',
          'fill-opacity': 0.15,
        }
      });

      map.addLayer({
        id: 'clicked-point',
        type: 'circle',
        source: 'clicked-point',
        paint: {
          'circle-radius': 6,
          'circle-color': '#2c6fad',
        }
      });
    })

    map.on("click", (e) => {
      const { lng, lat } = e.lngLat;
      console.log("Map clicked at", e.lngLat);
      map.flyTo({ center: e.lngLat, zoom: 7, essential: true });
      map.getSource('clicked-point').setData({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [lng, lat]}
      })
      map.getSource('query-radius').setData(
        turf.circle([lng, lat], 100, { units: 'kilometers'})
      )
      onMapClick(e.lngLat.lat, e.lngLat.lng);
    });

    return () => map.remove();
  }, []);

  return <div ref={mapContainer} style={{ width: "100%", height: "100%" }} />;
}
