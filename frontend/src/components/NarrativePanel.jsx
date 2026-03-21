import "@picocss/pico/css/pico.classless.min.css";
import "../panel.css";

export default function NarrativePanel({ lat, lng, narrative, loading, error, onClose }) {
  return (
    <div data-theme="light" className="narrative-panel" style={{
      position: "absolute",
      top: 0,
      right: 0,
      width: "400px",
      height: "100vh",
      background: "var(--pico-background-color)",
      boxShadow: "-2px 0 8px rgba(0,0,0,0.15)",
      overflowY: "auto",
      padding: "24px",
      display: "flex",
      flexDirection: "column",
      gap: "16px",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0, fontSize: "16px" }}>
          {lat.toFixed(4)}, {lng.toFixed(4)}
        </h2>
        <button onClick={onClose} aria-label="Close" className="secondary outline" style={{ width: "auto", padding: "4px 10px" }}>
          ×
        </button>
      </div>

      {loading && <p><em>Analyzing natural hazard history...</em></p>}

      {error && <p style={{ color: "var(--pico-color-red-550)" }}>{error}</p>}

      {narrative && (
        <>
          {/* {narrative.flood_zone && (
            <div style={{
              display: "inline-block",
              padding: "4px 10px",
              borderRadius: "4px",
              background: floodZoneColor(narrative.flood_zone),
              color: "white",
              fontSize: "13px",
              fontWeight: "bold",
              alignSelf: "flex-start",
            }}>
              Zone {narrative.flood_zone}
            </div>
          )} */}
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

// function floodZoneColor(zone) {
//   if (zone.startsWith("A") || zone.startsWith("V")) return "#c0392b";
//   if (zone === "X") return "#27ae60";
//   return "#7f8c8d";
// }
