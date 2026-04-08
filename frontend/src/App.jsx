import { useState, useRef } from "react";
import Map from "./components/Map";
import NarrativePanel from "./components/NarrativePanel";
import IntroOverlay from "./components/IntroOverlay";
import { getNarrative } from "./api/client";

export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [selection, setSelection] = useState(null); // { lat, lng }
  const [pendingBounds, setPendingBounds] = useState(null);
  const [narrative, setNarrative] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  async function handleMapClick(lat, lng, bbox) {
    setPendingBounds(bbox);
    // cancel any in-flight request before starting a new one
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setSelection({ lat, lng });
    setNarrative(null);
    setError(null);
    setLoading(true);

    try {
      const data = await getNarrative(lat, lng, controller.signal);
      setNarrative(data);
    } catch (err) {
      if (err.name === "AbortError") return;
      if (err.message.startsWith("rate_limited:")) {
        const minutes = err.message.split(":")[1];
        setError(`You've reached the request limit. Try again in ${minutes} minute${minutes === "1" ? "" : "s"}.`);
      } else {
        setError("Failed to load flood data for this location.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-layout">
      {showIntro && <IntroOverlay onDismiss={() => setShowIntro(false)} />}
      <Map onMapClick={handleMapClick} pendingBounds={pendingBounds} />
      {selection && (
        <NarrativePanel
          lat={selection.lat}
          lng={selection.lng}
          narrative={narrative}
          loading={loading}
          error={error}
          onClose={() => setSelection(null)}
        />
      )}
    </div>
  );
}
