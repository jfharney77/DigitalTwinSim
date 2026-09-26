import { useCallback, useEffect, useRef, useState } from "react";
import {
  DEFAULT_SCENARIO,
  fetchAnatomy,
  fetchPowerOn,
  fetchScenarios,
  fetchTour,
} from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { ChassisView } from "./components/ChassisView";
import { PowerOnControls } from "./components/PowerOnControls";
import { PowerOnCounters } from "./components/PowerOnCounters";
import { LevelControl } from "./components/LevelControl";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { useLevel } from "./level";
import type {
  ChassisAnatomy,
  RegionKind,
  ScenarioInfo,
  TraceState,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "poweron" | "anatomy" | "components" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#components")) return "components";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "poweron";
}

const PAGE_HASH: Record<Page, string> = {
  poweron: "",
  anatomy: "anatomy",
  components: "components",
  usecases: "usecases",
  tour: "tour",
};

// Deep-link into the guided tour: /#tour/<stepId>. Read at load and again on
// every hash change, so the link works in a tab that is already on the twin.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

// The sim page's hash is a small key=value list:
//   #step=N · #phase=<name> · #scenario=<id> · #scenario=<id>&phase=<name>
// All of them fall through pageFromHash() and land on the sim page.
function hashParams(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of window.location.hash.replace(/^#/, "").split("&")) {
    const m = part.match(/^(step|phase|scenario)=([a-z0-9_-]+)$/i);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

const SCENARIO_IDS = [DEFAULT_SCENARIO, "node-loss-failover"];

function scenarioFromHash(): string {
  const s = hashParams().scenario;
  return s && SCENARIO_IDS.includes(s) ? s : DEFAULT_SCENARIO;
}

// Returns the starting cursor a #step=/#phase= link names, or null when the
// hash names neither (or an unknown phase) and playback starts at 0.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const p = hashParams();
  if (p.step !== undefined && /^\d+$/.test(p.step)) {
    return Math.min(Number(p.step), states.length - 1);
  }
  if (p.phase !== undefined) {
    const i = states.findIndex((s) => s.phase === p.phase);
    return i >= 0 ? i : null;
  }
  return null;
}

// Keep in sync with KIND_STYLE in ChassisView.tsx.
const KIND_SWATCH: Record<RegionKind, string> = {
  storage: "#12233a",
  nvram: "#1c1f3f",
  cpu: "#2b2412",
  memory: "#241f33",
  io: "#16281a",
  power: "#2b1a1a",
  cooling: "#122b2b",
  battery: "#22290f",
  management: "#12282e",
  board: "#1a2433",
};

const KIND_LABEL: Record<RegionKind, string> = {
  storage: "NVMe drive bay",
  nvram: "NVRAM write cache",
  cpu: "node CPU",
  memory: "node DIMMs",
  io: "I/O modules & ports",
  power: "power supply",
  cooling: "fan pack",
  battery: "battery backup (vault)",
  management: "management/service ports",
  board: "node system board",
};

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  const [scenario, setScenario] = useState<string>(scenarioFromHash);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<regionId>).
    const want = PAGE_HASH[page];
    const h = window.location.hash;
    const onPage = want
      ? h.startsWith(`#${want}`)
      : !/^#(anatomy|components|usecases|tour)/.test(h);
    if (!onPage) {
      // Coming back to the sim page keeps a chosen failure scenario in the
      // address bar, so the link stays shareable.
      window.location.hash =
        page === "poweron" && scenario !== DEFAULT_SCENARIO
          ? `scenario=${scenario}`
          : want;
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<ChassisAnatomy | null>(null);
  const [trace, setTrace] = useState<TraceState[]>([]);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  // The player reads initialStepId once, on mount. A later #tour/<id> in the
  // same document is honoured by remounting it on this key.
  const [tourKey, setTourKey] = useState(0);
  const level = useLevel();

  const timer = useRef<number | null>(null);
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  // Apply the #step=/#phase= deep link once per scenario: a reading-level
  // refetch must not yank the cursor back, but a new scenario is a new trace
  // and starts from the hash's step, or from zero.
  const appliedFor = useRef<string | null>(null);
  const loadedOnce = useRef(false);
  // The guided tour pins steps of the power-on trace, so the tour page plays
  // that one whatever the sim page has selected.
  const liveScenario = page === "tour" ? DEFAULT_SCENARIO : scenario;
  const traceRef = useRef<TraceState[]>([]);
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;
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
    Promise.all([fetchAnatomy(), fetchPowerOn(liveScenario)])
      .then(([an, po]) => {
        if (stale) return;
        setAnatomy(an);
        setTrace(po.trace);
        traceRef.current = po.trace;
        if (appliedFor.current !== liveScenario) {
          const start = initialStepFromHash(po.trace);
          if (loadedOnce.current) {
            stop();
            setCursor(start ?? 0);
          } else if (start !== null) {
            // First load: leave the cursor alone unless the link names a
            // step. A #tour/<step> link may already have placed it.
            setCursor(start);
          }
          appliedFor.current = liveScenario;
          loadedOnce.current = true;
        }
      })
      .catch((e) => setError(String(e)));
    return () => {
      stale = true;
    };
  }, [level, liveScenario, stop]);

  useEffect(() => {
    fetchScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([])); // no picker; power-on still plays
  }, [level]);

  // The picker: a new scenario is a new trace, so playback stops and the
  // cursor returns to the first step (the fetch effect above does both).
  const chooseScenario = useCallback((id: string) => {
    window.history.replaceState(
      null,
      "",
      id === DEFAULT_SCENARIO
        ? window.location.pathname + window.location.search
        : `#scenario=${id}`,
    );
    appliedFor.current = null;
    setScenario(id);
  }, []);

  // Follow the hash when it changes under us: back/forward, a pasted link, or
  // an in-page control that sets window.location.hash.
  useEffect(() => {
    const onHash = () => {
      const next = pageFromHash();
      setPage(next);
      if (next === "tour") {
        // A pasted or in-tab #tour/<id> link: open the player on that step
        // rather than silently on step one.
        const id = tourStepFromHash();
        if (id && id !== tourStart.current) {
          tourStart.current = id;
          setTourKey((k) => k + 1);
        }
        return;
      }
      if (next !== "poweron") return;
      const nextScenario = scenarioFromHash();
      if (nextScenario !== scenarioRef.current) {
        // A different trace: the fetch effect places the cursor once it has
        // the right steps to place it in.
        appliedFor.current = null;
        setScenario(nextScenario);
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
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (node OS boot, pool assembly) so their
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

  const failure = scenario !== DEFAULT_SCENARIO;
  const selectedRegion =
    anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const kinds = anatomy
    ? ([...new Set(anatomy.regions.map((r) => r.kind))] as RegionKind[])
    : [];

  return (
    <div className="app dell">
      <header>
        <h1>PowerStore</h1>
        <nav className="nav">
          <button
            className={page === "poweron" ? "active" : ""}
            onClick={() => setPage("poweron")}
          >
            Power-on
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the chassis
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
        {page === "poweron" && (
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
              key={tourKey}
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              stageAspect={2}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                const asked = tourStart.current;
                tourStart.current = id;
                if (
                  asked &&
                  asked !== id &&
                  !tour.tour.steps.some((s) => s.id === asked)
                ) {
                  // The link named a step this tour does not have. Leave the
                  // address bar as it was rather than rewriting it to assert a
                  // step the reader never asked for.
                  return;
                }
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the power-on page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <ChassisView
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
                      Power-on trace: <strong>{state.label}</strong> · t+
                      {state.elapsedSeconds}s (illustrative)
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

      {page === "poweron" && (
        <>
          <div className="an-hero">
            <h2>
              {failure
                ? "What happens when a node fails"
                : "What happens when you plug it in"}
            </h2>
            {failure && level <= 2 && (
              <p>
                The array is already running when one of its two controller
                nodes (the two computers inside the box), node A, stops.
                Every write the array has confirmed is saved on a matched
                pair of cache drives in the shared front bay, outside both
                nodes, so none is lost. The servers using the array resend
                their requests to node B, node B does all the work with less
                room to spare, and node A restarts, rejoins and takes its
                share back. Play the trace and watch the count of
                acknowledged writes lost.
              </p>
            )}
            {failure && level > 2 && (
              <p>
                The array is already serving I/O when node A stops. Every
                acknowledged write is on a mirrored pair of NVRAM drives in
                the shared front bay, so none goes with it. Hosts retry on
                their paths to node B, node B serves every volume with less
                headroom, and node A reboots, rejoins and takes its volumes
                back. Play the trace and watch the count of acknowledged
                writes lost.
              </p>
            )}
            <p hidden={failure || level > 2}>
              A storage array has no power button. It starts up the moment
              mains power arrives. Inside are two controller nodes, two
              complete computers that run the same start-up side by side.
              They check the battery that protects their write cache, find
              the flash drives they both share, and agree to work as a pair,
              both serving at once, before any data is offered to other
              computers. Play the trace and watch each stage light up the
              hardware it runs on.
            </p>
            <p hidden={failure || level <= 2}>
              A storage array has no power button — it starts booting the
              moment AC arrives. Two controller nodes come up side by side,
              check the battery that protects their write cache, discover the
              NVMe drives they both share, and form an active-active pair
              before a single volume goes online. Play the trace and watch
              each stage light up the hardware it runs on.
            </p>
            <button
              className="primary poweron-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              {anatomy && (
                <ChassisView
                  anatomy={anatomy}
                  active={new Set(state?.activeRegions ?? [])}
                  failed={new Set(state?.failedRegions ?? [])}
                  selected={regionId}
                  onSelect={setRegionId}
                />
              )}
              {state && (
                <div className="poweron-desc">
                  {state.description.split("\n\n").map((para, i) =>
                    i === 0 ? (
                      <span key={i}>
                        <strong>{state.label}.</strong> {para}
                      </span>
                    ) : (
                      <p key={i} className="poweron-desc-more">
                        {para}
                      </p>
                    ),
                  )}
                </div>
              )}
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step.
                Click a block to pin what it is; every block is described
                under Inside the chassis.
                {failure &&
                  " Blocks that are down are outlined in red with a dashed edge, and a block is never drawn both down and lit."}
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerOnControls
              scenarios={scenarios}
              scenarioId={scenario}
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
            <PowerOnCounters
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
                {failure && (
                  <span>
                    <i className="failed-swatch" />
                    down at this step
                  </span>
                )}
              </section>
            )}
          </aside>
        </>
      )}
    </div>
  );
}
