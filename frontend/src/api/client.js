const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function apiFetch(path) {
  const resp = await fetch(`${API_URL}${path}`);
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${path}`);
  return resp.json();
}

export function getDeclarations(lat, lng, radius = 100, incident_type = null) {
  const params = new URLSearchParams({ lat, lng, radius });
  if (incident_type) params.set("incident_type", incident_type);
  return apiFetch(`/api/declarations?${params}`);
}

export function getZone(lat, lng) {
  return apiFetch(`/api/zone?lat=${lat}&lng=${lng}`);
}

export function getNarrative(lat, lng) {
  return apiFetch(`/api/narrative?lat=${lat}&lng=${lng}`);
}

export function getCounties(lat, lng, radius = 100) {
  return apiFetch(`/api/counties?lat=${lat}&lng=${lng}&radius=${radius}`);
}
