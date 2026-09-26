import { useCallback, useEffect, useRef, useState } from "react";
import {
  DEFAULT_SCENARIO,
  fetchAnatomy,
  fetchLifecycle,
  fetchScenarios,
  fetchTour,
} from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { SiteView } from "./components/SiteView";
import { LifecycleControls } from "./components/LifecycleControls";
import { LifecycleCounters } from "./components/LifecycleCounters";
import { CleaningCounters } from "./components/CleaningCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type {
  LifecycleState,
  RegionKind,
  ScenarioInfo,
  SiteAnatomy,
  TraceState,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "lifecycle" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "lifecycle";
}

const PAGE_HASH: Record<Page, string> = {
  lifecycle: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
  tour: "tour",
};

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

// #step=N / #phase=<name> deep-links start playback at a chosen step; both
// fall through pageFromHash() and land on the default page.
// #scenario=<id> picks the trace and composes with either:
// #scenario=cleaning-gc&phase=pinned.
function hashParams(): URLSearchParams {
  const h = window.location.hash.replace(/^#/, "");
  return new URLSearchParams(h.includes("=") ? h : "");
}

function scenarioFromHash(): string {
  const id = hashParams().get("scenario");
  return id && /^[a-z0-9-]+$/i.test(id) ? id : DEFAULT_SCENARIO;
}

function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const p = hashParams();
  const step = p.get("step");
  if (step !== null && /^\d+$/.test(step)) {
    return Math.min(Number(step), states.length - 1);
  }
  const phase = p.get("phase");
  if (phase !== null && /^[a-z0-9_-]+$/i.test(phase)) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (#anatomy/<id>, #tour/<stepId>, #phase=...).
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) {
      window.location.hash =
        page === "lifecycle" && scenarioRef.current !== DEFAULT_SCENARIO
          ? `scenario=${scenarioRef.current}`
          : want;
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<SiteAnatomy | null>(null);
  const [trace, setTrace] = useState<TraceState[]>([]);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [scenario, setScenario] = useState<string>(scenarioFromHash);
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  const traceRef = useRef<TraceState[]>([]);
  traceRef.current = trace;
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply the #step=/#phase= deep-link only on the first load — a
  // reading-level refetch must not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);

  // The trace is pure data from the backend engine; fetch it once and play
  // it back here — the clock lives in the frontend, never in the engine.
  // The guided tour narrates the attack-and-recovery trace, so it always
  // plays against that one whatever the lifecycle page has selected.
  const activeScenario = page === "tour" ? DEFAULT_SCENARIO : scenario;
  useEffect(() => {
    let stale = false;
    Promise.all([
      fetchAnatomy(),
      fetchLifecycle(activeScenario),
      fetchScenarios(),
    ])
      .then(([an, lc, sc]) => {
        if (stale) return;
        setAnatomy(an);
        setTrace(lc.trace);
        setScenarios(sc);
        setError(null);
        if (!hashApplied.current) {
          hashApplied.current = true;
          setCursor(initialStepFromHash(lc.trace) ?? 0);
        }
      })
      .catch((e) => {
        if (!stale) setError(String(e));
      });
    return () => {
      stale = true;
    };
  }, [level, activeScenario]);

  // The picker: a new scenario starts from its first step. The hash is
  // rewritten in place so the address bar holds the link to share.
  const chooseScenario = useCallback(
    (id: string) => {
      stop();
      setCursor(0);
      setRegionId(null);
      setScenario(id);
      window.history.replaceState(
        null,
        "",
        id === DEFAULT_SCENARIO
          ? window.location.pathname + window.location.search
          : `#scenario=${id}`,
      );
    },
    [stop],
  );

  // Follow the hash after load: in-app links (the use-case page's "Go
  // deeper" buttons), the back button, and a pasted #scenario=/#phase=/#step=
  // link all change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      const nextPage = pageFromHash();
      setPage(nextPage);
      const next = scenarioFromHash();
      if (nextPage === "lifecycle" && next !== scenarioRef.current) {
        // A different scenario: reset, and let the fetch apply #phase=/#step=
        // against the trace it brings back.
        stop();
        setCursor(0);
        hashApplied.current = false;
        setScenario(next);
        return;
      }
      const start = initialStepFromHash(traceRef.current);
      if (start !== null) {
        stop();
        setCursor(start);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [stop]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (the narration is leveled prose).
  const tourWanted = page === "tour" || tour !== null;
  useEffect(() => {
    if (!tourWanted) return;
    fetchTour()
      .then(setTour)
      .catch((e) => setTourError(String(e)));
  }, [level, tourWanted]);

  const state = trace[cursor] ?? null;
  const scenarioInfo = scenarios.find((s) => s.id === scenario) ?? null;
  const isCleaning = page === "lifecycle" && scenario !== DEFAULT_SCENARIO;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (the CyberSense scan) so their real-world
      // cost is visible.
      if (dwell.current > 1) {
        dwell.current -= 1;
        return;
      }
      setCursor((c) => {
        const next = c + 1;
        if (next >= trace.length - 1) {
          stop();
          return trace.length - 1;
        }
        dwell.current = Math.min(trace[next]?.cycleCost ?? 1, MAX_DWELL);
        return next;
      });
    };
    const ms = Math.max(40, 600 / speedRef.current);
    timer.current = window.setInterval(tick, ms);
  }, [trace, stop]);

  const step = useCallback(() => {
    stop();
    setCursor((c) => Math.min(c + 1, trace.length - 1));
  }, [trace, stop]);

  const reset = useCallback(() => {
    stop();
    setCursor(0);
  }, [stop]);

  // Retune the interval live when speed changes mid-run.
  useEffect(() => {
    if (timer.current === null) return;
    stop();
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [speed]);

  const selectedRegion =
    anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <div className="app dell">
      <header>
        <h1>PowerProtect</h1>
        <nav className="nav">
          <button
            className={page === "lifecycle" ? "active" : ""}
            onClick={() => setPage("lifecycle")}
          >
            Data lifecycle
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the vault
          </button>
          <button
            className={page === "components" ? "active" : ""}
            onClick={() => setPage("components")}
          >
            Components &amp; options
          </button>
          <button
            className={page === "usecases" ? "active" : ""}
            onClick={() => setPage("usecases")}
          >
            Use cases
          </button>
          <button
            className={page === "tour" ? "active" : ""}
            onClick={() => setPage("tour")}
          >
            Guided tour
          </button>
        </nav>
        {page === "lifecycle" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedHours}h` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "components" && <CatalogPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "tour" && (
        <div className="tour-page">
          {(tourError || error) && (
            <div className="mini an-error">{tourError ?? error}</div>
          )}
          {tour && anatomy && (
            <TourPlayer
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // SiteView draws the map plus a margin and an orientation line.
              stageAspect={
                (tour.mapWidth + 5) / (tour.mapHeight + 9)
              }
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the lifecycle page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <SiteView
                  anatomy={anatomy}
                  active={stage.lit}
                  selected={regionId}
                  onSelect={(id) => {
                    setRegionId(id);
                    if (id) stage.onRegionClick(id);
                  }}
                  camera={stage.viewBox}
                  regionLook={stage.regionLook}
                />
              )}
              aside={
                <>
                  {state && (
                    <p className="tour-trace">
                      Lifecycle trace: <strong>{state.label}</strong> · t+
                      {state.elapsedHours}h (illustrative)
                    </p>
                  )}
                  {state && (
                    <p className="tour-trace">
                      Logical {state.logicalTb} TB · stored {state.storedTb} TB
                    </p>
                  )}
                  {state && (state.copiesScanned ?? 0) > 0 && (
                    <p className="tour-trace">
                      Vault copies scanned {state.copiesScanned} · flagged{" "}
                      {state.copiesFlagged}
                    </p>
                  )}
                  {selectedRegion && (
                    <div>
                      <h2>{selectedRegion.label}</h2>
                      <p className="tour-trace">{selectedRegion.description}</p>
                    </div>
                  )}
                </>
              }
            />
          )}
        </div>
      )}

      {page === "lifecycle" && (
        <>
          <div className="an-hero">
            {isCleaning ? (
              <>
                <h2>{scenarioInfo?.title ?? "Free space keeps shrinking"}</h2>
                <p>
                  {scenarioInfo?.summary} Play the trace and watch the stored
                  figure: it falls in the two cleaning steps and nowhere else.
                </p>
              </>
            ) : (
              <>
            <h2>The life of a backup — through an attack and back</h2>
                <p>
                  {scenarioInfo?.intro ||
                    "This twin follows the data, not a machine. An estate " +
                      "backs up to a PowerProtect Data Domain, deduplication " +
                      "collapses hundreds of terabytes into a few tens, and a " +
                      "copy crosses a briefly-open air gap into a Cyber " +
                      "Recovery vault where it is locked immutable and scanned " +
                      "by CyberSense. Then ransomware detonates in production " +
                      "and finds the vault simply is not there. Play the trace " +
                      "and watch the gap open only when the vault opens it."}
                </p>
              </>
            )}
            <button
              className="primary lifecycle-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <SiteView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  failed={new Set(state?.failedRegions ?? [])}
                  selected={regionId}
                  onSelect={setRegionId}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  <strong>{state.label}.</strong> {state.description}
                </div>
              )}
              {isCleaning ? (
                <div className="mini an-hint">
                  Highlighted blocks are the parts doing work at this step. A
                  block in an alert condition is drawn in red with a dashed
                  outline. The air gap lights once, when replication catches
                  up, and the vault opens it. Click a block to pin what it is.
                </div>
              ) : (
              <div className="mini an-hint">
                  Highlighted blocks are the parts doing work at this step.
                  Watch the air gap: it lights only during replication and
                  recovery — both opened from the vault side — and at the
                  attack step the entire right half of the map stays dark.
                  Click a block to pin what it is. Inside the vault describes
                  every block, and Guided tour narrates the whole story.
                </div>
              )}
            </div>
          </div>

          <aside className="controls">
            <LifecycleControls
              scenarios={scenarios}
              scenario={scenario}
              onScenario={chooseScenario}
              speed={speed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              onSpeed={setSpeed}
              onRun={run}
              onPause={stop}
              onStep={step}
              onReset={reset}
            />
            {isCleaning ? (
              <CleaningCounters
                state={state}
                stepIndex={cursor}
                stepCount={trace.length}
                scenario={scenarioInfo}
              />
            ) : (
              <LifecycleCounters
                state={state as LifecycleState | null}
                stepIndex={cursor}
                stepCount={trace.length}
                note={scenarioInfo?.countersNote}
              />
            )}
            {selectedRegion && (
              <section className="an-panel">
                <h2>{selectedRegion.label}</h2>
                <p className="an-desc">{selectedRegion.description}</p>
              </section>
            )}
            {anatomy && (
              <section className="legend an-panel">
                <h2>Blocks</h2>
                {kinds.map((k) => (
                  <span key={k}>
                    <i
                      style={{
                        background: KIND_SWATCH[k],
                        border: "1px solid var(--sm-edge)",
                      }}
                    />
                    {KIND_LABEL[k]}
                  </span>
                ))}
              </section>
            )}
          </aside>
        </>
      )}
    </div>
  );
}
