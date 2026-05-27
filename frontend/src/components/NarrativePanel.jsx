import "../panel.css";

export default function NarrativePanel({ lat, lng, narrativeHtml, narrativeMeta, loading, error, onClose }) {
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

      {narrativeHtml && (
        <div className="narrative-content"
          dangerouslySetInnerHTML={{ __html: narrativeHtml }}
        />
      )}

      {narrativeMeta && (
        <small style={{ color: "var(--color-muted)" }}>
          {narrativeMeta.cached ? "Cached" : "Generated"} · {new Date(narrativeMeta.generated_at).toLocaleDateString()}
        </small>
      )}
    </div>
  );
}
