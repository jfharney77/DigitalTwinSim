import { useEffect, useState } from "react";
import { fetchAnatomy, fetchCatalog } from "../api";
import { useLevel } from "../level";
import { RackView } from "./RackView";
import type { CatalogCategory, RackAnatomy } from "../types";

// The build-to-order menu: every category is either a physical part of the
// rack or something the rack depends on (external storage, software,
// delivery). Hovering a category lights up where it lives on the mini
// floorplan.

export function CatalogPage() {
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [anatomy, setAnatomy] = useState<RackAnatomy | null>(null);
  const [activeCat, setActiveCat] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  useEffect(() => {
    Promise.all([fetchCatalog(), fetchAnatomy()])
      .then(([cats, an]) => {
        setCatalog(cats);
        setAnatomy(an);
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  const active = catalog.find((c) => c.id === activeCat) ?? null;

  const jump = (id: string) => {
    setActiveCat(id);
    document
      .getElementById(`cat-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <div className="an-hero">
        <h2>Components &amp; options</h2>
        <p>
          An XE9712 is configured as a whole rack: pick the NVIDIA rack-scale
          generation and the scale-out fabric, and the trays, switch trays,
          shelves, and cooling follow — every tray identical by design. What
          surrounds the rack (storage, software, delivery) is part of the
          order too. Hover a category to light up where its parts live in the
          rack.
        </p>
      </div>

      <div className="stage">
        {error && <div className="mini an-error">{error}</div>}
        {catalog.map((cat) => (
          <section
            key={cat.id}
            id={`cat-${cat.id}`}
            className="an-card cat-section"
            onMouseEnter={() => setActiveCat(cat.id)}
          >
            <h3 className="cat-name">{cat.name}</h3>
            <p className="cat-blurb">{cat.blurb}</p>
            {cat.limits && <div className="mini cat-limits">{cat.limits}</div>}
            <div className="cat-grid">
              {cat.options.map((opt) => (
                <article key={opt.id} className="cat-card">
                  <h4>{opt.name}</h4>
                  <div className="cat-summary">{opt.summary}</div>
                  <p className="cat-details">{opt.details}</p>
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>

      <aside className="controls">
        {anatomy && (
          <section className="an-panel cat-map">
            <h2>Where it lives</h2>
            <RackView
              anatomy={anatomy}
              active={new Set(active?.regionIds ?? [])}
            />
            <div className="mini">
              {active
                ? active.regionIds.length > 0
                  ? `${active.name} — highlighted on the rack floorplan.`
                  : `${active.name} — not a physical part of this rack (external storage, software, or services).`
                : "Hover a category to highlight its home in the rack."}
            </div>
          </section>
        )}
        <section className="an-panel">
          <h2>Categories</h2>
          <nav className="cat-index">
            {catalog.map((cat) => (
              <button
                key={cat.id}
                className={cat.id === activeCat ? "active" : ""}
                onClick={() => jump(cat.id)}
              >
                {cat.name}
              </button>
            ))}
          </nav>
        </section>
      </aside>
    </>
  );
}
