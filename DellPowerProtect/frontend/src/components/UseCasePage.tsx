import { useEffect, useMemo, useState } from "react";
import { fetchAnatomy, fetchCatalog, fetchUseCases } from "../api";
import { useLevel } from "../level";
import { SiteView } from "./SiteView";
import type {
  CatalogCategory,
  SiteAnatomy,
  UseCase,
  UseCaseItem,
} from "../types";

// Resolve a config row's ids against the catalog; fall back to the raw ids so
// a stale reference degrades to something readable instead of a blank row.
function resolve(item: UseCaseItem, catalog: CatalogCategory[]) {
  const cat = catalog.find((c) => c.id === item.categoryId) ?? null;
  const opt = cat?.options.find((o) => o.id === item.optionId) ?? null;
  return {
    category: cat?.name ?? item.categoryId,
    option: opt?.name ?? item.optionId,
    regionIds: cat?.regionIds ?? [],
  };
}

export function UseCasePage() {
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [anatomy, setAnatomy] = useState<SiteAnatomy | null>(null);
  // Honor a /#usecases/<id> deep link for the initial selection.
  const [caseId, setCaseId] = useState<string | null>(
    () => window.location.hash.split("/")[1] ?? null,
  );
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  useEffect(() => {
    Promise.all([fetchUseCases(), fetchCatalog(), fetchAnatomy()])
      .then(([ucs, cats, an]) => {
        setUseCases(ucs);
        setCatalog(cats);
        setAnatomy(an);
        setCaseId((cur) =>
          ucs.some((u) => u.id === cur) ? cur : ucs[0]?.id ?? null,
        );
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    if (caseId) window.location.hash = `usecases/${caseId}`;
  }, [caseId]);

  const uc = useCases.find((u) => u.id === caseId) ?? null;

  const rows = useMemo(
    () => (uc ? uc.config.map((item) => ({ item, ...resolve(item, catalog) })) : []),
    [uc, catalog],
  );

  // Union of every configured part's home regions — the build, on the map.
  const litRegions = useMemo(
    () => new Set(rows.flatMap((r) => r.regionIds)),
    [rows],
  );

  return (
    <>
      {uc && (
        <div className="an-hero">
          <h2>{uc.title}</h2>
          <p>{uc.summary}</p>
        </div>
      )}
      <div className="stage">
        {error && <div className="mini an-error">{error}</div>}
        {useCases.length > 1 && (
          <nav className="uc-tabs">
            {useCases.map((u) => (
              <button
                key={u.id}
                className={u.id === caseId ? "active" : ""}
                onClick={() => setCaseId(u.id)}
              >
                {u.title}
              </button>
            ))}
          </nav>
        )}
        {uc && (
          <div className="an-card">
            {uc.narrative.map((p, i) => (
              <p className="uc-para" key={i}>
                {p}
              </p>
            ))}
          </div>
        )}
        {uc && rows.length > 0 && (
          <div className="an-card uc-build">
            <h3>Build sheet</h3>
            <p className="mini">
              What goes into the deployment for this workload, and why.
              Quantities count the unit named (appliances, sites, vaults).
            </p>
            <table>
              <thead>
                <tr>
                  <th>Qty</th>
                  <th>Component</th>
                  <th>Category</th>
                  <th>Why</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i}>
                    <td className="uc-qty">{r.item.qty}×</td>
                    <td className="uc-part">{r.option}</td>
                    <td className="uc-cat">{r.category}</td>
                    <td className="uc-why">{r.item.rationale}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <aside className="controls">
        {uc && uc.outcomes.length > 0 && (
          <section className="an-panel">
            <h2>What you get</h2>
            {uc.outcomes.map((s) => (
              <div className="stat" key={s.label}>
                <span>{s.label}</span>
                <span>{s.value}</span>
              </div>
            ))}
          </section>
        )}
        {anatomy && (
          <section className="an-panel">
            <h2>This build on the data path</h2>
            <SiteView anatomy={anatomy} active={litRegions} />
            <div className="mini">
              Highlighted blocks hold the parts in the build sheet.
            </div>
          </section>
        )}
        <section className="an-panel">
          <h2>Go deeper</h2>
          <div className="btnrow">
            <button onClick={() => (window.location.hash = "anatomy")}>
              See where these parts live
            </button>
            <button onClick={() => (window.location.hash = "components")}>
              Browse all options
            </button>
          </div>
        </section>
      </aside>
    </>
  );
}
