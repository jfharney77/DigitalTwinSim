import { useEffect, useState } from "react";
import { fetchBrandMap } from "../api";
import { useLevel } from "../level";
import type { BrandMap } from "../types";

// The client-brand-map explainer (physics_specs/10 §8): a static page,
// not a sim — Dell's January 2025 rebrand and its 2026 corrections, at
// whatever reading level the header control is set to. This page exists
// inside this app because the scheme names both of its products: the
// Alienware personality (the brand the rebrand left alone) and the
// "Pro Max Plus" (the Plus tier of the workstation brand).

export function BrandMapPage() {
  const [map, setMap] = useState<BrandMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  useEffect(() => {
    fetchBrandMap()
      .then((m) => {
        setMap(m);
        setError(null);
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  if (error) return <div className="mini an-error">{error}</div>;
  if (!map) return <div className="mini">Loading…</div>;

  return (
    <div className="thermal-grid brandmap-grid">
      <div className="thermal-col thermal-center" style={{ gridColumn: "1 / -1" }}>
        <div className="an-card">
          <p className="uc-para">{map.overview}</p>
          <div className="cat-grid">
            {map.brands.map((b) => (
              <div key={b.id} className="cat-card">
                <h4>{b.name}</h4>
                <div className="cat-summary">was: {b.formerly}</div>
                <div className="cat-summary">{b.audience}</div>
                <div className="cat-summary">
                  {b.tiers.join(" · ")}
                </div>
                <p className="cat-details">{b.description}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="an-panel">
          <h2>Reading a model name</h2>
          <p className="uc-para">{map.namingNote}</p>
        </div>
        <div className="an-panel">
          <h2>What changed since 2025</h2>
          <p className="uc-para">{map.sinceNote}</p>
        </div>
        <div className="an-panel">
          <h2>Sources &amp; companion twins</h2>
          <div className="an-sources">
            {map.sources.map((s) => (
              <a key={s.url} href={s.url} target="_blank" rel="noreferrer">
                {s.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
