const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// throws error on non-200 responses
async function apiFetch(path, signal) {
  const resp = await fetch(`${API_URL}${path}`, { signal });
  if (resp.status === 429) {
    const retryAfter = resp.headers.get("Retry-After");
    const minutes = retryAfter ? Math.ceil(retryAfter / 60) : 60;
    throw new Error(`rate_limited:${minutes}`);
  }
  if (!resp.ok) throw new Error(`API error ${resp.status}: ${path}`);
  return resp.json();
}

// called by narrative.py, defined here because it is a public endpoint
export function getDeclarations(lat, lng, radius = 100, incident_type = null) {
  const params = new URLSearchParams({ lat, lng, radius });
  if (incident_type) params.set("incident_type", incident_type);
  return apiFetch(`/api/declarations?${params}`);
}

// called in handleMapClick in App.jsx when user clicks on map.
// async generator that yields SSE events: { type: 'chunk', text } or { type: 'done', ... }
export async function* streamNarrative(lat, lng, signal) {
  const resp = await fetch(`${API_URL}/api/narrative/stream?lat=${lat}&lng=${lng}`, { signal });
  if (resp.status === 429) {
    const retryAfter = resp.headers.get("Retry-After");
    const minutes = retryAfter ? Math.ceil(retryAfter / 60) : 60;
    throw new Error(`rate_limited:${minutes}`);
  }
  if (!resp.ok) throw new Error(`API error ${resp.status}: /api/narrative/stream`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by double newlines
    const parts = buffer.split("\n\n");
    buffer = parts.pop(); // keep any incomplete trailing chunk

    for (const part of parts) {
      if (part.startsWith("data: ")) {
        yield JSON.parse(part.slice(6));
      }
    }
  }
}

// called in Map.jsx to fetch county boundaries for clicked location
export function getCounties(lat, lng, radius = 100) {
  return apiFetch(`/api/counties?lat=${lat}&lng=${lng}&radius=${radius}`);
}
