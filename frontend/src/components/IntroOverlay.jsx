// overlay shown on load with instructions, dismissed on button click
import "../panel.css";

export default function IntroOverlay({ onDismiss }) {
  return (
    <div className="intro-overlay">
      <div className="intro-card" onClick={(e) => e.stopPropagation()}>
        <h1>Hazard Navigator</h1>
        <p className="body-text">
          Click anywhere on the map to see a natural hazards risk assessment. Data is based on historical FEMA disaster declarations and flood zone information.
        </p>
        <p className="disclaimer">
          Hazard reports are generated using AI, so results may be inaccurate or incomplete. Use for general reference only.
        </p>
        <button className="intro-btn" onClick={onDismiss}>
          Explore the map
        </button>
      </div>
    </div>
  );
}
