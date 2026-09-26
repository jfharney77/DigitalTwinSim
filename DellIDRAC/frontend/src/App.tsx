import { useCallback, useEffect, useRef, useState } from "react";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { fetchAnatomy, fetchBringUp, fetchScenarios, fetchTour } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { BlockView } from "./components/BlockView";
import { BringUpControls } from "./components/BringUpControls";
import { BringUpCounters } from "./components/BringUpCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type {
  BringUpState,
  RegionKind,
  ScenarioId,
  ScenarioInfo,
  SubsystemMap,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "bringup" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "bringup";
}

// The sim page's hash is a small query string: #step=N, #phase=<name>,
// #scenario=<id>, and any of them joined with "&"
// (#scenario=firmware-update-rollback&phase=bootcheck). Other pages' hashes
// (#anatomy/<id>, #tour/<id>) carry no "=" and parse to nothing here.
function hashParams(): URLSearchParams {
  const h = window.location.hash.slice(1);
  return new URLSearchParams(h.includes("=") ? h : "");
}

const SCENARIO_IDS: ScenarioId[] = ["bring-up", "firmware-update-rollback"];
const DEFAULT_SCENARIO: ScenarioId = "bring-up";

function scenarioFromHash(): ScenarioId {
  const want = hashParams().get("scenario") as ScenarioId | null;
  return want && SCENARIO_IDS.includes(want) ? want : DEFAULT_SCENARIO;
}

function scenarioHash(id: ScenarioId): string {
  return id === DEFAULT_SCENARIO ? "" : `scenario=${id}`;
}

const SCENARIO_HERO: Record<ScenarioId, { title: string; body: string }> = {
  "bring-up": {
    title: "What wakes up before the server does",
    body:
      "Plug in a PowerEdge and, seconds before the host can do anything, a " +
      "small always-on computer boots inside it: iDRAC, the management " +
      "controller. Standby power wakes its SoC, a Root of Trust verifies its " +
      "firmware, embedded Linux comes up, and the management services — web " +
      "console, Redfish, Lifecycle Controller, sensor monitoring — come " +
      "online. Only then is the server reachable to be powered on. Play the " +
      "trace and watch each stage light up the block it runs in.",
  },
  "firmware-update-rollback": {
    title: "An update that fails, and a server that does not notice",
    body:
      "An administrator updates iDRAC's firmware while the host runs its " +
      "workload. The package is signature-checked and written to the flash " +
      "partition iDRAC is not running from. iDRAC restarts, the new image " +
      "fails its boot check, and the bootloader goes back to the old " +
      "partition by itself. Management is dark for about two minutes, an " +
      "illustrative figure. The " +
      "host never changes power state. Play the trace and watch which " +
      "numbers move and which do not.",
  },
};

const PAGE_HASH: Record<Page, string> = {
  bringup: "",
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

// Deep-link into the trace: /#step=N or /#phase=<name>. Returns the starting
// cursor, or null when the hash matches neither pattern (or names an unknown
// phase) — in which case playback starts at 0 as before.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const params = hashParams();
  const step = params.get("step");
  if (step !== null && /^\d+$/.test(step)) {
    return Math.min(Number(step), states.length - 1);
  }
  const phase = params.get("phase");
  if (phase) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

// Keep in sync with KIND_STYLE in BlockView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  soc: "#2b2412",
  memory: "#241f33",
  network: "#12233a",
  sideband: "#122b2b",
  io: "#16281a",
  power: "#2b1a1a",
  security: "#12282e",
  sensor: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  soc: "service processor (SoC)",
  memory: "working memory & flash",
  network: "management NIC",
  sideband: "host management buses",
  io: "remote presence (console, media)",
  power: "standby power",
  security: "root of trust & security",
  sensor: "monitoring & thermal engine",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  const [scenario, setScenario] = useState<ScenarioId>(scenarioFromHash);
  const scenarioRef = useRef(scenario);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<blockId>).
    // The landing page has an empty hash, so check it explicitly: every hash
    // starts with "#", and a bare prefix test would keep #tour/<id> there.
    const want =
      page === "bringup" ? scenarioHash(scenario) : PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) window.location.hash = want;
    document.body.classList.add("dell-body");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const [anatomy, setAnatomy] = useState<SubsystemMap | null>(null);
  const [trace, setTrace] = useState<BringUpState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply a #step=/#phase= deep link only on the first successful trace load,
  // so a reading-level refetch does not yank the cursor back.
  const hashApplied = useRef(false);
  const traceRef = useRef<BringUpState[]>([]);
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);

  // Follow hash changes made outside the nav (links, "Go deeper" buttons,
  // the back button, a pasted #step=/#phase= link).
  // Switch traces. The cursor always resets; a #phase=/#step= in the hash is
  // applied once the new trace has loaded (hashApplied is re-armed).
  const switchScenario = useCallback(
    (id: ScenarioId) => {
      if (id === scenarioRef.current) return;
      stop();
      setCursor(0);
      dwell.current = 0;
      hashApplied.current = false;
      scenarioRef.current = id;
      setScenario(id);
    },
    [stop],
  );

  const chooseScenario = useCallback(
    (id: ScenarioId) => {
      switchScenario(id);
      window.location.hash = scenarioHash(id);
    },
    [switchScenario],
  );

  // The guided tour narrates the bring-up trace and drives this cursor, so
  // opening it puts the bring-up back.
  useEffect(() => {
    if (page === "tour") switchScenario(DEFAULT_SCENARIO);
  }, [page, switchScenario]);

  useEffect(() => {
    const onHash = () => {
      const nextPage = pageFromHash();
      setPage(nextPage);
      if (nextPage === "bringup") {
        const wanted = scenarioFromHash();
        if (wanted !== scenarioRef.current) {
          // The trace on hand is the old scenario's; the fetch applies
          // #phase=/#step= against the new one.
          switchScenario(wanted);
          return;
        }
      }
      const start = initialStepFromHash(traceRef.current);
      if (start !== null) {
        stop();
        setCursor(start);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [stop, switchScenario]);

  useEffect(() => {
    fetchScenarios()
      .then(setScenarios)
      .catch((e) => setError(String(e)));
  }, [level]);

  // The trace is pure data from the backend engine; fetch it once and play
  // it back here — the clock lives in the frontend, never in the engine.
  useEffect(() => {
    let stale = false;
    Promise.all([fetchAnatomy(), fetchBringUp(scenario)])
      .then(([an, bu]) => {
        if (stale) return;
        setAnatomy(an);
        setTrace(bu.trace);
        traceRef.current = bu.trace;
        if (!hashApplied.current) {
          hashApplied.current = true;
          const start = initialStepFromHash(bu.trace);
          if (start !== null) setCursor(start);
        }
      })
      .catch((e) => {
        if (!stale) setError(String(e));
      });
    return () => {
      stale = true;
    };
  }, [level, scenario]);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (its narration is leveled prose).
  const tourWanted = page === "tour" || tour !== null;
  useEffect(() => {
    if (!tourWanted) return;
    fetchTour()
      .then(setTour)
      .catch((e) => setTourError(String(e)));
  }, [level, tourWanted]);

  const state = trace[cursor] ?? null;
  // Every step is stamped at its end, so a step's length is the difference
  // from the stamp before it. The longest one is named on the counter, which
  // is the evidence for "the longest stage" that the prose claims.
  const stepSeconds = trace.map((s, i) =>
    i === 0 ? 0 : s.elapsedSeconds - trace[i - 1].elapsedSeconds,
  );
  const longestSeconds = Math.max(0, ...stepSeconds);
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on the long stage (Lifecycle Controller init) so its
      // real-world cost is visible.
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
        <h1>iDRAC9</h1>
        <nav className="nav">
          <button
            className={page === "bringup" ? "active" : ""}
            onClick={() => setPage("bringup")}
          >
            Bring-up
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the controller
          </button>
          <button
            className={page === "components" ? "active" : ""}
            onClick={() => setPage("components")}
          >
            Capabilities &amp; options
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
        {page === "bringup" && (
          <span className="sub">
            {state ? `${state.label} · t+${state.elapsedSeconds}s` : "—"}
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
              // BlockView draws the map plus a 2.5-unit outline margin and a
              // 4-unit row of orientation labels.
              stageAspect={
                (tour.mapWidth + 2 * 2.5) / (tour.mapHeight + 2 * 2.5 + 4)
              }
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the bring-up page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <BlockView
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
                      Bring-up trace: <strong>{state.label}</strong> · t+
                      {state.elapsedSeconds}s · {state.powerWatts} W
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

      {page === "bringup" && (
        <>
          <div className="an-hero">
            <h2>{SCENARIO_HERO[scenario].title}</h2>
            <p>
              {scenarios.find((s) => s.id === scenario)?.intro ||
                SCENARIO_HERO[scenario].body}
            </p>
            <button
              className="primary bringup-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <BlockView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  failed={new Set(state?.failedRegions ?? [])}
                  failedTag="B REJECTED"
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
                Highlighted blocks are the parts doing work at this step
                {scenario === DEFAULT_SCENARIO
                  ? ""
                  : "; a red dashed block holds something that failed"}
                . Click
                a block to pin what it is; the full tour lives under Inside the
                controller.
              </div>
            </div>
          </div>

          <aside className="controls">
            <BringUpControls
              scenario={scenario}
              scenarios={scenarios}
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
            <BringUpCounters
              state={state}
              stepIndex={cursor}
              stepCount={trace.length}
              stepSeconds={stepSeconds[cursor] ?? 0}
              longest={
                longestSeconds > 0 && stepSeconds[cursor] === longestSeconds
              }
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
