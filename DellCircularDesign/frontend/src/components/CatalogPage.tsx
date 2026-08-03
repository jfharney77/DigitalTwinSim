import { useEffect, useState } from "react";
import { fetchAnatomy, fetchCatalog } from "../api";
import { useLevel } from "../level";
import { LoopView } from "./LoopView";
import type { CatalogCategory, LifecycleMap } from "../types";

// The circular-design menu: every category is either a drawn stage of the
// loop (material inputs, packaging, recovery, refurbishment, reclamation) or
// a practice that changes how much material comes back (design for repair,
// service-life extension, reporting). Hovering a category lights up where it
// lives on the mini map.

export function CatalogPage() {
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [anatomy, setAnatomy] = useState<LifecycleMap | null>(null);
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
          These are not parts of a machine; they are levers on a loop. Each
          category changes where material ends up — as a refurbished device,
          as reclaimed feedstock, or as loss — and the honest ordering puts
          the biggest lever first: keeping a device in service longer beats
          any amount of recycling, because it defers the manufacturing step
          that dominates the arithmetic. Hover a category to light up where
          it acts on the loop.
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
            <h2>Where it acts</h2>
            <LoopView
              anatomy={anatomy}
              active={new Set(active?.regionIds ?? [])}
            />
            <div className="mini">
              {active
                ? active.regionIds.length > 0
                  ? `${active.name} — highlighted on the loop.`
                  : `${active.name} — not a drawn stage of the loop (a practice, a service, or reporting).`
                : "Hover a category to highlight where it acts on the loop."}
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
