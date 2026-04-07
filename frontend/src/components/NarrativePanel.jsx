import "@picocss/pico/css/pico.classless.min.css";
import "../panel.css";

export default function NarrativePanel({ lat, lng, narrative, loading, error, onClose }) {
  return (
    <div data-theme="light" className="narrative-panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0, fontSize: "16px" }}>
          {lat.toFixed(4)}, {lng.toFixed(4)}
        </h2>
        <button onClick={onClose} aria-label="Close" className="secondary outline" style={{ width: "auto", padding: "4px 10px" }}>
          ×
        </button>
      </div>

      {loading && <p><em>Analyzing natural hazard history. This may take a few moments.</em></p>}

      {error && <p style={{ color: "var(--pico-color-red-550)" }}>{error}</p>}

      {narrative && (
        <>
          <div style={{ lineHeight: "1.6" }}
            dangerouslySetInnerHTML={{ __html: narrative.narrative }}
          />
          <small style={{ color: "var(--pico-muted-color)" }}>
            {narrative.cached ? "Cached" : "Generated"} · {new Date(narrative.generated_at).toLocaleDateString()}
          </small>
        </>
      )}
    </div>
  );
}
