import { useEffect, useMemo, useState } from "react";
import { fetchAnatomies, fetchUseCases } from "../api";
import { useLevel } from "../level";
import { AnatomyView } from "./AnatomyView";
import type { Anatomy, UseCase } from "../types";

export function UseCasePage() {
  const [useCases, setUseCases] = useState<UseCase[]>([]);
  const [anatomy, setAnatomy] = useState<Anatomy | null>(null);
  // Honor a /#usecases/<id> deep link for the initial selection.
  const [caseId, setCaseId] = useState<string | null>(
    () => window.location.hash.split("/")[1] ?? null,
  );
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  useEffect(() => {
    Promise.all([fetchUseCases(), fetchAnatomies()])
      .then(([ucs, ans]) => {
        setUseCases(ucs);
        setAnatomy(ans[0] ?? null);
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

  // Union of every step's regions — the walkthrough, on the floorplan.
  const litRegions = useMemo(
    () => new Set(uc?.steps.flatMap((s) => s.regionIds) ?? []),
    [uc],
  );

  const regionLabel = (id: string) =>
    anatomy?.regions.find((r) => r.id === id)?.label ?? id;

  const regionLink = (id: string) => {
    // Deep-link into the anatomy page; the region exists on the floorplan
    // there, so land the reader on the right machine.
    window.location.hash = anatomy ? `anatomy/${anatomy.id}` : "anatomy";
    void id;
  };

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
            <p className="uc-persona">{uc.persona}</p>
            {uc.steps.map((s, i) => (
              <div className="uc-step" key={i}>
                <h3>{s.title}</h3>
                <p className="uc-para">{s.body}</p>
                {s.regionIds.length > 0 && (
                  <div className="uc-tags">
                    {s.regionIds.map((rid) => (
                      <button
                        key={rid}
                        className="uc-tag"
                        title="See this part on the floorplan"
                        onClick={() => regionLink(rid)}
                      >
                        {regionLabel(rid)}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <div className="uc-outcome">
              <h3>Outcome</h3>
              <p className="uc-para">{uc.outcome}</p>
            </div>
          </div>
        )}
      </div>

      <aside className="controls">
        {anatomy && uc && (
          <section className="an-panel">
            <h2>Where this happens</h2>
            <AnatomyView anatomy={anatomy} active={litRegions} />
            <div className="mini">
              Highlighted blocks are the parts this walkthrough touches.
            </div>
          </section>
        )}
        {uc && uc.sources.length > 0 && (
          <section className="an-panel">
            <h2>Sources</h2>
            <div className="an-sources">
              {uc.sources.map((s) => (
                <a key={s.url} href={s.url} target="_blank" rel="noreferrer">
                  {s.label} ↗
                </a>
              ))}
            </div>
          </section>
        )}
        <section className="an-panel">
          <h2>Go deeper</h2>
          <div className="btnrow">
            <button
              onClick={() =>
                (window.location.hash = anatomy ? `anatomy/${anatomy.id}` : "anatomy")
              }
            >
              See inside the machine
            </button>
            <button onClick={() => (window.location.hash = "")}>
              Play the power path
            </button>
          </div>
        </section>
      </aside>
    </>
  );
}
