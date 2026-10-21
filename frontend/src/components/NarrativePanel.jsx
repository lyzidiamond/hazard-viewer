import { useEffect, useMemo, useRef } from "react";
import "../panel.css";

// adds a heading to the declaration list, wraps each hazard type in a collapsed <details> so long
// lists don't push the narrative below the fold, and labels the narrative with "Summary:".
// done client-side so cached narratives get it too.
function formatNarrative(html) {
  const doc = new DOMParser().parseFromString(html, "text/html");

  // only US narratives have a declaration list; non-US ones are left as-is
  const list = doc.body.querySelector(":scope > ul");
  if (!list) return html;

  if (list.children.length) {
    const heading = doc.createElement("h4");
    heading.textContent = "Disaster declarations within 100 km";
    list.before(heading);
  }

  const firstParagraph = doc.body.querySelector(":scope > p");
  if (firstParagraph) {
    const label = doc.createElement("strong");
    label.textContent = "Summary: ";
    firstParagraph.prepend(label);
  }

  list.querySelectorAll(":scope > li").forEach(li => {
    const innerUl = li.querySelector(":scope > ul");
    if (!innerUl) return;

    const hazardType = li.firstChild?.textContent.trim() || "Unknown";
    const count = innerUl.querySelectorAll("li:not(:has(details))").length;

    const details = doc.createElement("details");
    details.className = "hazard-group";
    const summary = doc.createElement("summary");
    summary.textContent = `${hazardType} (${count})`;
    details.append(summary, innerUl);

    li.replaceChildren(details);
  });
  return doc.body.innerHTML;
}

export default function NarrativePanel({ lat, lng, narrativeHtml, narrativeMeta, loading, error, onClose }) {
  const contentRef = useRef(null);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;

    function handleClick(e) {
      // only the nested "N more declarations" expanders; hazard-group accordions toggle normally
      const summary = e.target.closest("details:not(.hazard-group) > summary");
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

  const displayHtml = useMemo(
    () => (narrativeHtml ? formatNarrative(narrativeHtml) : ""),
    [narrativeHtml]
  );

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
          dangerouslySetInnerHTML={{ __html: displayHtml }}
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
