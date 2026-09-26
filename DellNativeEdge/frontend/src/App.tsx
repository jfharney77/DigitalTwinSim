import { useCallback, useEffect, useRef, useState } from "react";
import {
  HAPPY_SCENARIO,
  fetchAnatomy,
  fetchOnboard,
  fetchScenarios,
  fetchTour,
} from "./api";
import { ArchitecturePage } from "./components/ArchitecturePage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { PlatformView } from "./components/PlatformView";
import { OnboardControls } from "./components/OnboardControls";
import { OnboardCounters, elapsed } from "./components/OnboardCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type {
  OnboardState,
  PlatformMap,
  RegionKind,
  ScenarioInfo,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "onboard" | "architecture" | "capabilities" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#architecture")) return "architecture";
  if (h.startsWith("#capabilities")) return "capabilities";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "onboard";
}

const PAGE_HASH: Record<Page, string> = {
  onboard: "",
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
//
// Both compose with a scenario: /#scenario=attestation-fails&phase=quarantine.
// The hash is read as key=value pairs joined by "&"; a page hash such as
// #architecture has no "=" and yields no parameters.
function hashParams(): URLSearchParams {
  const h = window.location.hash.replace(/^#/, "");
  return new URLSearchParams(h.includes("=") ? h : "");
}

function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const params = hashParams();
  const step = params.get("step");
  if (step !== null && /^\d+$/.test(step)) {
    return Math.min(Number(step), states.length - 1);
  }
  const phase = params.get("phase");
  if (phase !== null) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

// Which trace the sim page plays: /#scenario=<id>. Absent means the happy
// path. An unknown id is kept as typed; the backend answers 404 and the page
// shows the error rather than silently playing something else.
function scenarioFromHash(): string {
  const id = hashParams().get("scenario");
  return id && /^[a-z0-9-]+$/i.test(id) ? id : HAPPY_SCENARIO;
}

// Shown only until /api/scenarios answers; the leveled introductions for
// each trace live in backend/app/scenarios.py.
const FALLBACK_INTRO =
  "One site, four devices, no IT staff. Each device proves it is the " +
  "machine Dell built and asks the Orchestrator what it should become. " +
  "The only on-site human action is power and a network cable.";

// Keep in sync with KIND_STYLE in PlatformView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  endpoint: "#2b2412",
  network: "#12233a",
  identity: "#0f2a30",
  orchestrator: "#1c1f3f",
  blueprint: "#241f33",
  catalog: "#22290f",
  policy: "#2b1a1a",
  observability: "#16281a",
};

const KIND_LABEL: Record<RegionKind, string> = {
  endpoint: "edge endpoints",
  network: "WAN",
  identity: "secure onboarding",
  orchestrator: "Orchestrator",
  blueprint: "blueprints",
  catalog: "app catalog",
  policy: "Zero Trust policy",
  observability: "observability",
};

export function App() {
  // Deep-linkable pages: /#architecture, /#capabilities, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  useEffect(() => {
    // Compare pages, not hash prefixes: every hash starts with "#", so a
    // prefix test for the onboarding page ("") never rewrote a stale
    // #architecture and a reload reopened the wrong tab. Sub-page suffixes
    // (#architecture/<id>, #usecases/<id>, #step=N) still survive.
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<PlatformMap | null>(null);
  const [trace, setTrace] = useState<OnboardState[]>([]);
  const [scenario, setScenario] = useState<string>(scenarioFromHash);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  // Bumped when a #tour/<stepId> arrives after load (typed into the address
  // bar, or back/forward), so the player remounts on that step; the player
  // reads its starting step only once.
  const [tourKey, setTourKey] = useState(0);

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
  const hashApplied = useRef(false);
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<OnboardState[]>([]);
  traceRef.current = trace;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);

  // The trace is pure data from the backend engine; fetch it once and play
  // it back here — the clock lives in the frontend, never in the engine.
  // A scenario change refetches too, and re-arms the deep link so that
  // #scenario=<id>&phase=<name> lands on that phase of the new trace.
  useEffect(() => {
    let stale = false;
    Promise.all([fetchAnatomy(), fetchOnboard(scenario), fetchScenarios()])
      .then(([an, po, sc]) => {
        if (stale) return;
        setError(null);
        setAnatomy(an);
        setTrace(po.trace);
        setScenarios(sc);
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(po.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => {
        if (stale) return;
        setTrace([]);
        setError(String(e));
      });
    return () => {
      stale = true;
    };
  }, [level, scenario]);

  // Pick a scenario: stop, rewind, and put the choice in the URL. The
  // cursor always resets, because step N of one trace is not step N of
  // another.
  const chooseScenario = useCallback(
    (id: string) => {
      if (id === scenarioRef.current) return;
      stop();
      setCursor(0);
      hashApplied.current = false;
      window.history.replaceState(
        null,
        "",
        id === HAPPY_SCENARIO
          ? window.location.pathname + window.location.search
          : `#scenario=${id}`,
      );
      setScenario(id);
    },
    [stop],
  );

  // The guided tour narrates the happy path and drives this same cursor, so
  // opening it puts the happy path back under it.
  useEffect(() => {
    if (page === "tour" && scenarioRef.current !== HAPPY_SCENARIO) {
      stop();
      setScenario(HAPPY_SCENARIO);
    }
  }, [page, stop]);

  // Follow hash changes after load: in-page links (the use-case page's
  // "Go deeper" buttons), back/forward, and a #step=/#phase= typed into the
  // address bar all have to move the app, not just the URL.
  useEffect(() => {
    const onHash = () => {
      const next = pageFromHash();
      setPage(next);
      if (next === "tour") {
        const id = tourStepFromHash();
        if (id && id !== tourStart.current) {
          tourStart.current = id;
          setTourKey((k) => k + 1);
        }
      }
      if (next === "onboard") {
        const wanted = scenarioFromHash();
        if (wanted !== scenarioRef.current) {
          // A different trace: rewind now, and let the fetch apply any
          // &phase= / &step= once the new trace has arrived.
          stop();
          setCursor(0);
          hashApplied.current = false;
          setScenario(wanted);
          return;
        }
        const start = initialStepFromHash(traceRef.current);
        if (start !== null) {
          stop();
          setCursor(start);
        }
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
  const failed = new Set(state?.failedEndpoints ?? []);
  const scenarioInfo = scenarios.find((s) => s.id === scenario) ?? null;
  const isFailure = scenario !== HAPPY_SCENARIO;
  // A hash naming a scenario the backend does not serve: the fetch 404s and
  // there is no trace to show. The page must say so rather than dress the
  // empty stage in either trace's copy.
  const unknownScenario = isFailure && scenarioInfo === null;
  const showFailure = isFailure && scenarioInfo !== null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on the attestation stage so its real-world cost shows.
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
        <h1>Dell NativeEdge</h1>
        <nav className="nav">
          <button
            className={page === "onboard" ? "active" : ""}
            onClick={() => setPage("onboard")}
          >
            Zero-touch onboarding
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
        {page === "onboard" && (
          <span className="sub">
            {state ? `${state.label} · ${elapsed(state.elapsedSeconds)}` : "—"}
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
              key={tourKey}
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // PlatformView draws the map plus a margin and a label row:
              // (100 + 2*2.5) x (58 + 2*2.5 + 4).
              stageAspect={105 / 67}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the onboarding page plays.
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
                      Onboarding trace: <strong>{state.label}</strong> ·{" "}
                      {elapsed(state.elapsedSeconds)} (illustrative) · operator
                      actions{" "}
                      {state.operatorActions}
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

      {page === "onboard" && (
        <>
          <div className="an-hero">
            <h2>
              {unknownScenario
                ? "No such trace"
                : showFailure && scenarioInfo
                  ? scenarioInfo.title
                  : "Nobody touches the device"}
            </h2>
            <p>
              {unknownScenario
                ? `There is no trace called "${scenario}". Pick one from the ` +
                  "Scenario list below; the traces this twin serves are the " +
                  "zero-touch onboarding and the attestation failure."
                : scenarioInfo?.intro || FALLBACK_INTRO}
            </p>
            {showFailure && scenarioInfo && (
              <details className="mini scenario-note">
                <summary>What is sourced and what is illustrative</summary>
                <p>{scenarioInfo.illustrative}</p>
                <p>
                  Sources:{" "}
                  {scenarioInfo.sources.map((src, i) => (
                    <span key={src.url}>
                      {i > 0 && " · "}
                      <a href={src.url} target="_blank" rel="noreferrer">
                        {src.label}
                      </a>
                    </span>
                  ))}
                </p>
              </details>
            )}
            <button
              className="primary onboard-tour-link"
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
                  failed={failed}
                  selected={regionId}
                  onSelect={setRegionId}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  <strong>{state.label}.</strong> {state.description}
                </div>
              )}
              {!unknownScenario && (
                <div className="mini an-hint">
                  {showFailure &&
                    "A device drawn in red failed attestation and is " +
                      "quarantined: nothing is sent to it and it is not " +
                      "counted online. "}
                  Highlighted blocks are the parts doing work at this step.
                  Watch the dwell on attestation — proving the device is the
                  machine Dell built is the slow part, on purpose — and watch
                  endpoints-online snap from zero to{" "}
                  {showFailure ? "three" : "four"} when the Orchestrator
                  claims the{" "}
                  {showFailure
                    ? "devices that passed"
                    : "site's devices as a set"}
                  . Click a block to pin what it is; the Architecture page
                  describes every block, and the guided tour narrates the
                  whole sequence.
                </div>
              )}
            </div>
          </div>

          <aside className="controls">
            <OnboardControls
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
              onScenario={chooseScenario}
            />
            <OnboardCounters
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
