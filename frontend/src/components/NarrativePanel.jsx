import "../panel.css";

export default function NarrativePanel({ lat, lng, narrative, loading, error, onClose }) {
  return (
    <div className="narrative-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 className="coordinates" style={{ margin: 0 }}>
          {lat.toFixed(4)}, {lng.toFixed(4)}
        </h2>
        <button onClick={onClose} aria-label="Close" className="close-btn">
          ×
        </button>
      </div>

      {loading && <p><em>Analyzing natural hazard history. This may take a few moments.</em></p>}

      {error && <p style={{ color: "var(--color-red)" }}>{error}</p>}

      {narrative && (
        <>
          <div className="narrative-content"
            dangerouslySetInnerHTML={{ __html: narrative.narrative }}
          />
          <small style={{ color: "var(--color-muted)" }}>
            {narrative.cached ? "Cached" : "Generated"} · {new Date(narrative.generated_at).toLocaleDateString()}
          </small>
        </>
      )}
    </div>
  );
}
