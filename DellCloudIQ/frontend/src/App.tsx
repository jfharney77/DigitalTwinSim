import { useCallback, useEffect, useRef, useState } from "react";
import {
  HEALTHY,
  fetchAnatomy,
  fetchPipeline,
  fetchScenarios,
  fetchTour,
} from "./api";
import { ArchitecturePage } from "./components/ArchitecturePage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { PlatformView } from "./components/PlatformView";
import { PipelineControls } from "./components/PipelineControls";
import { PipelineCounters } from "./components/PipelineCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type {
  PlatformMap,
  PipelineState,
  RegionKind,
  ScenarioInfo,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "pipeline" | "architecture" | "capabilities" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#architecture")) return "architecture";
  if (h.startsWith("#capabilities")) return "capabilities";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "pipeline";
}

const PAGE_HASH: Record<Page, string> = {
  pipeline: "",
  architecture: "architecture",
  capabilities: "capabilities",
  usecases: "usecases",
  tour: "tour",
};

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

// The pipeline page's hash is a small parameter list: /#step=N, /#phase=<name>,
// /#scenario=<id>, or a scenario composed with either —
// /#scenario=connected-no-data&phase=stale. Order does not matter.
function hashParam(name: string): string | null {
  const m = window.location.hash.match(
    new RegExp(`[#&]${name}=([a-z0-9_-]+)(?:&|$)`, "i"),
  );
  return m ? m[1] : null;
}

// Which trace the hash asks for. No scenario= means the healthy pipeline.
function scenarioFromHash(): string {
  return hashParam("scenario") ?? HEALTHY;
}

// Returns the starting cursor, or null when the hash names neither a step nor
// a known phase — in which case playback starts at 0 as before.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const step = hashParam("step");
  if (step !== null && /^\d+$/.test(step))
    return Math.min(Number(step), states.length - 1);
  const phase = hashParam("phase");
  if (phase !== null) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

// Keep in sync with KIND_STYLE in PlatformView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  source: "#12233a",
  gateway: "#0f2a30",
  ingest: "#16203a",
  analytics: "#2b2412",
  security: "#2b1a1a",
  insight: "#16281a",
  assistant: "#1f1a33",
  action: "#22290f",
};

const KIND_LABEL: Record<RegionKind, string> = {
  source: "monitored systems",
  gateway: "Secure Connect Gateway",
  ingest: "cloud ingest",
  analytics: "ML analytics",
  security: "cybersecurity",
  insight: "insights & app",
  assistant: "AIOps Assistant",
  action: "notify & integrate",
};

export function App() {
  // Deep-linkable pages: /#architecture, /#capabilities, /#usecases, /#tour.
  const [page, setPage] = useState<Page>(pageFromHash);
  // Which trace is playing: the healthy pipeline or a failure scenario. The
  // hash is the source of truth, so the picker writes the hash and this follows.
  const [scenario, setScenario] = useState<string>(scenarioFromHash);
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  useEffect(() => {
    // The pipeline page's hash is empty (or a #step=/#phase=/#scenario= deep
    // link), so "on the page" means "not on any other page" rather than a
    // prefix match. Coming back to it restores the scenario that was playing.
    const want =
      page === "pipeline" && scenarioRef.current !== HEALTHY
        ? `scenario=${scenarioRef.current}`
        : PAGE_HASH[page];
    const h = window.location.hash;
    const elsewhere = /^#(architecture|capabilities|usecases|tour)/.test(h);
    // A scenario deep link may put its parameters in either order
    // (#phase=stale&scenario=...), so match the parameter, not a prefix.
    const onPage =
      page === "pipeline"
        ? !elsewhere && scenarioFromHash() === scenarioRef.current
        : h.startsWith(`#${want}`);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<PlatformMap | null>(null);
  const [trace, setTrace] = useState<PipelineState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
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
  useEffect(() => {
    let stale = false;
    Promise.all([fetchAnatomy(), fetchPipeline(scenario), fetchScenarios()])
      .then(([an, po, sc]) => {
        if (stale) return;
        setAnatomy(an);
        setTrace(po.trace);
        setScenarios(sc);
        if (!hashApplied.current) {
          // First load, or a scenario change: the cursor starts where the hash
          // says, else at the beginning of the new trace.
          hashApplied.current = true;
          setCursor(initialStepFromHash(po.trace) ?? 0);
        }
      })
      .catch((e) => {
        if (stale) return;
        if (scenario !== HEALTHY) {
          // An unknown scenario id in a pasted link: say so, play the healthy trace.
          setError(`Unknown scenario "${scenario}". Showing the healthy pipeline.`);
          window.location.hash = "";
        } else setError(String(e));
      });
    return () => {
      stale = true;
    };
  }, [level, scenario]);

  // The guided tour narrates the healthy trace; its cursors index that trace.
  useEffect(() => {
    if (page === "tour" && scenario !== HEALTHY) {
      hashApplied.current = false;
      setScenario(HEALTHY);
    }
  }, [page, scenario]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes so the narration follows the reader.
  const tourWanted = page === "tour" || tour !== null;
  useEffect(() => {
    if (!tourWanted) return;
    fetchTour()
      .then(setTour)
      .catch((e) => setTourError(String(e)));
  }, [level, tourWanted]);

  // Follow later hash changes too (back/forward, a pasted deep link, a
  // link from another page) — not just the hash present on first load.
  useEffect(() => {
    const onHash = () => {
      const nextPage = pageFromHash();
      setPage(nextPage);
      if (nextPage === "pipeline") {
        const next = scenarioFromHash();
        if (next !== scenarioRef.current) {
          // A different trace: stop, rewind, and let the fetch place the cursor.
          stop();
          hashApplied.current = false;
          setCursor(0);
          setScenario(next);
          return;
        }
      }
      const s = initialStepFromHash(trace);
      if (s !== null) {
        stop();
        setCursor(s);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [trace, stop]);

  const state = trace[cursor] ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on the heavy ML analyze stage so its real-world cost shows.
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

  const pickScenario = useCallback((id: string) => {
    window.location.hash = id === HEALTHY ? "" : `scenario=${id}`;
  }, []);
  const scenarioInfo = scenarios.find((s) => s.id === scenario) ?? null;
  const failing = scenario !== HEALTHY;

  const selectedRegion =
    anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <div className="app dell">
      <header>
        <h1>CloudIQ</h1>
        <nav className="nav">
          <button
            className={page === "pipeline" ? "active" : ""}
            onClick={() => setPage("pipeline")}
          >
            Pipeline
          </button>
          <button
            className={page === "architecture" ? "active" : ""}
            onClick={() => setPage("architecture")}
          >
            Architecture
          </button>
          <button
            className={page === "capabilities" ? "active" : ""}
            onClick={() => setPage("capabilities")}
          >
            Capabilities
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
        {page === "pipeline" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "architecture" && <ArchitecturePage />}
      {page === "capabilities" && <CatalogPage />}
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
              // PlatformView draws a 2.5-unit margin and 4 units of labels:
              // (100 + 5) / (58 + 5 + 4).
              stageAspect={105 / 67}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the pipeline page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <PlatformView
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
                      Pipeline trace: <strong>{state.label}</strong> · Health
                      Score {state.healthScore} · t+{state.elapsedSeconds}s
                      (illustrative)
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

      {page === "pipeline" && (
        <>
          <div className="an-hero">
            <h2>
              {failing
                ? "Connected, but no data arrives"
                : "How telemetry becomes an insight"}
            </h2>
            {/* Leveled prose from /api/scenarios, like the step text below it. */}
            {scenarioInfo?.intro && <p>{scenarioInfo.intro}</p>}
            <button
              className="primary pipeline-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <PlatformView
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
              <div className="mini an-hint">
                {failing &&
                  "Blocks outlined in red are blocked or starved at this step; the break itself, marked with a cross, is the company's proxy between the gateway and the cloud. "}
                Highlighted blocks are the parts doing work at this step.
                Click a block to pin what it is; the full descriptions live
                under Architecture, and Guided tour narrates the whole trip.
              </div>
            </div>
          </div>

          <aside className="controls">
            <PipelineControls
              speed={speed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              onSpeed={setSpeed}
              onRun={run}
              onPause={stop}
              onStep={step}
              onReset={reset}
              scenario={scenario}
              scenarios={scenarios}
              onScenario={pickScenario}
            />
            <PipelineCounters
              failing={failing}
              note={scenarioInfo?.note ?? ""}
              state={state}
              stepIndex={cursor}
              stepCount={trace.length}
            />
            {selectedRegion && (
              <section className="an-panel">
                <h2>{selectedRegion.label}</h2>
                <p className="an-desc">{selectedRegion.description}</p>
              </section>
            )}
            {failing && scenarioInfo && scenarioInfo.sources.length > 0 && (
              <section className="an-panel scenario-sources">
                <h2>What this failure is based on</h2>
                <p className="mini">{scenarioInfo.summary}</p>
                <ul>
                  {scenarioInfo.sources.map((src) => (
                    <li key={src.url}>
                      <a href={src.url} target="_blank" rel="noreferrer">
                        {src.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {anatomy && (
              <section className="legend an-panel">
                <h2>Blocks</h2>
                {failing && (
                  <span>
                    <i
                      style={{
                        background: "#3a1216",
                        border: "1px dashed var(--dell-error)",
                      }}
                    />
                    blocked or starved at this step
                  </span>
                )}
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
