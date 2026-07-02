import { useEffect, useRef } from "react";
import "../panel.css";

export default function NarrativePanel({ lat, lng, narrativeHtml, narrativeMeta, loading, error, onClose }) {
  const contentRef = useRef(null);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    function handleClick(e) {
      const summary = e.target.closest("summary");
      if (!summary) return;

      // prevent <details> from toggling open — we're replacing it instead
      e.preventDefault();

      const details = summary.closest("details");
      const innerUl = details?.querySelector("ul");
      if (!details || !innerUl) return;

      // <details> may be directly in a <ul> or wrapped in a <li> depending on what Claude generates
      const directParent = details.parentElement;
      const parentUl = directParent.tagName === "UL" ? directParent : directParent.parentElement;
      const removeTarget = directParent.tagName === "UL" ? details : directParent;

      // move remaining items into the parent list, then remove the trigger
      [...innerUl.querySelectorAll(":scope > li")].forEach(item =>
        parentUl.insertBefore(item, removeTarget)
      );
      removeTarget.remove();
    }

    el.addEventListener("click", handleClick);
    return () => el.removeEventListener("click", handleClick);
  }, [narrativeHtml]);

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
        <div
          ref={contentRef}
          className="narrative-content"
          dangerouslySetInnerHTML={{ __html: narrativeHtml }}
        />
      )}

      {narrativeMeta && (
        <small style={{ color: "var(--color-muted)" }}>
          {narrativeMeta.cached ? "Cached" : "Generated"} · {new Date(narrativeMeta.generated_at).toLocaleDateString()}
        </small>
      )}

      <p className="attribution" style={{ marginTop: "auto" }}>
        A project by <a href="https://lyzidiamond.github.io" target="_blank" rel="noreferrer">Lyzi Diamond</a>. The code lives on <a href="https://github.com/lyzidiamond/hazard-viewer" target="_blank" rel="noreferrer">GitHub</a>.
      </p>
    </div>
  );
}
