import { useState, useRef } from "react";
import Map from "./components/Map";
import NarrativePanel from "./components/NarrativePanel";
import IntroOverlay from "./components/IntroOverlay";
import { getNarrative } from "./api/client";

export default function App() {
  const [showIntro, setShowIntro] = useState(true);
  const [selection, setSelection] = useState(null); // { lat, lng }
  const [narrative, setNarrative] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);

  async function handleMapClick(lat, lng) {
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
      if (err.name !== "AbortError") {
        setError("Failed to load flood data for this location.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-layout">
      {showIntro && <IntroOverlay onDismiss={() => setShowIntro(false)} />}
      <Map onMapClick={handleMapClick} />
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
