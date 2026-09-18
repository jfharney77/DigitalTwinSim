import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchPipeline, fetchTour } from "./api";
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
import type { PlatformMap, PipelineState, RegionKind } from "./types";

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

// Deep-link into the trace: /#step=N or /#phase=<name>. Returns the starting
// cursor, or null when the hash matches neither pattern (or names an unknown
// phase) — in which case playback starts at 0 as before.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const h = window.location.hash;
  const step = h.match(/#step=(\d+)$/);
  if (step) return Math.min(Number(step[1]), states.length - 1);
  const phase = h.match(/#phase=([a-z0-9_-]+)$/i);
  if (phase) {
    const i = states.findIndex((s) => s.phase === phase[1]);
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
  useEffect(() => {
    // The pipeline page's hash is empty (or a #step=/#phase= deep link), so
    // "on the page" means "not on any other page" rather than a prefix match.
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(architecture|capabilities|usecases|tour)/.test(h);
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
    Promise.all([fetchAnatomy(), fetchPipeline()])
      .then(([an, po]) => {
        setAnatomy(an);
        setTrace(po.trace);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(po.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => setError(String(e)));
  }, [level]);

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
      setPage(pageFromHash());
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
            <h2>How telemetry becomes an insight</h2>
            <p>
              CloudIQ has no power button — it is a cloud service. What it does
              have is a pipeline: your monitored Dell systems collect
              telemetry, the Secure Connect Gateway ships it one-way to Dell's
              cloud, machine learning scores health and hunts for anomalies,
              and when something crosses a line the Health Score drops, the
              insight surfaces, the AIOps Assistant explains it, and a
              notification fires. Play the trace and watch each stage light up
              the part of the platform it runs in.
            </p>
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
            />
            <PipelineCounters
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
