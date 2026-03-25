const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// throws error on non-200 responses
async function apiFetch(path, signal) {
  const resp = await fetch(`${API_URL}${path}`, { signal });
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${path}`);
  return resp.json();
}

// called by narrative.py, defined here because it is a public endpoint
export function getDeclarations(lat, lng, radius = 100, incident_type = null) {
  const params = new URLSearchParams({ lat, lng, radius });
  if (incident_type) params.set("incident_type", incident_type);
  return apiFetch(`/api/declarations?${params}`);
}

// called in handleMapClick in App.jsx when user clicks on map
export function getNarrative(lat, lng, signal) {
  return apiFetch(`/api/narrative?lat=${lat}&lng=${lng}`, signal);
}

// called in Map.jsx to fetch county boundaries for clicked location
export function getCounties(lat, lng, radius = 100) {
  return apiFetch(`/api/counties?lat=${lat}&lng=${lng}&radius=${radius}`);
}
