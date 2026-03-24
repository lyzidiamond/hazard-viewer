// overlay shown on load with instructions, dismissed on button click
export default function IntroOverlay({ onDismiss }) {
  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(0,0,0,0.4)",
        zIndex: 10,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "white",
          borderRadius: "8px",
          padding: "32px",
          maxWidth: "400px",
          width: "90%",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <h1 style={{ margin: 0, fontSize: "22px", color: "#333" }}>Hazard Navigator</h1>
        <p style={{ margin: 0, lineHeight: "1.6", color: "#333" }}>
          Click anywhere on the map to see a natural hazards risk assessment.
        </p>
        <button
          onClick={onDismiss}
          style={{
            background: "#2c6fad",
            color: "white",
            border: "none",
            borderRadius: "4px",
            padding: "10px 20px",
            fontSize: "18px",
            cursor: "pointer",
            alignSelf: "flex-start",
          }}
        >
          Explore the map
        </button>
      </div>
    </div>
  );
}
