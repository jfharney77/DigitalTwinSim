import { useEffect, useState } from "react";
import { fetchAnatomy, fetchCatalog } from "../api";
import { useLevel } from "../level";
import { ClusterView } from "./ClusterView";
import type { CatalogCategory, ClusterAnatomy } from "../types";

// The build-to-order menu: every category is either a drawn part of the
// data path (appliances, gap, analytics) or something the architecture
// depends on (cloud tiers, services). Hovering a category lights up where
// it lives on the mini map.

export function CatalogPage() {
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [anatomy, setAnatomy] = useState<ClusterAnatomy | null>(null);
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
          There is no controller category here, because there is no
          controller. The first decision is the servers, and the second is
          whether the servers holding the storage are also the servers
          using it — a choice a traditional array never offers. Hover a
          category to light up where its parts live in the pool.
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
            <ClusterView
              anatomy={anatomy}
              active={new Set(active?.regionIds ?? [])}
            />
            <div className="mini">
              {active
                ? active.regionIds.length > 0
                  ? `${active.name} — highlighted in the pool.`
                  : `${active.name} — not a drawn part of the pool map (software, services, or topology).`
                : "Hover a category to highlight its home in the pool."}
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
