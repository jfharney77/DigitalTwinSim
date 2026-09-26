import { useCallback, useEffect, useRef, useState } from "react";
import { fetchAnatomy, fetchPowerOn, fetchScenarios, fetchTour } from "./api";
import { AnatomyPage, KIND_LABEL, KIND_SWATCH } from "./components/AnatomyPage";
import { CatalogPage } from "./components/CatalogPage";
import { UseCasePage } from "./components/UseCasePage";
import { RackView } from "./components/RackView";
import { PowerOnControls } from "./components/PowerOnControls";
import { PowerOnCounters } from "./components/PowerOnCounters";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import type {
  PowerOnState,
  RackAnatomy,
  RegionKind,
  ScenarioId,
  ScenarioInfo,
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

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
function tourStepFromHash(): string | null {
  const m = window.location.hash.match(/^#tour\/([a-z0-9-]+)$/i);
  return m ? m[1] : null;
}

// The power-on page's hash is a small key=value list:
//   #step=N · #phase=<name> · #scenario=<id> · #scenario=<id>&phase=<name>
// All of them fall through pageFromHash() and land on the default page.
function hashParams(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const part of window.location.hash.replace(/^#/, "").split("&")) {
    const m = part.match(/^(step|phase|scenario)=([a-z0-9_-]+)$/i);
    if (m) out[m[1]] = m[2];
  }
  return out;
}

const SCENARIO_IDS: ScenarioId[] = ["nominal", "coolant-fault"];

function scenarioFromHash(): ScenarioId {
  const s = hashParams().scenario as ScenarioId | undefined;
  return s && SCENARIO_IDS.includes(s) ? s : "nominal";
}

function initialStepFromHash(states: { phase: string }[]): number | null {
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

export function App() {
  // Deep-linkable pages: /#anatomy, /#components, /#usecases.
  const [page, setPage] = useState<Page>(pageFromHash);
  const [scenario, setScenario] = useState<ScenarioId>(scenarioFromHash);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  useEffect(() => {
    // Compare pages, not prefixes: the power-on page's hash is empty and
    // every hash starts with "#", so a prefix check never cleared a leftover
    // #anatomy and a reload landed back on the wrong page.
    if (pageFromHash() !== page) {
      // Coming back to the power-on page keeps a chosen failure scenario in
      // the address bar, so the link stays shareable.
      window.location.hash =
        page === "poweron" && scenario !== "nominal"
          ? `scenario=${scenario}`
          : PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);

  const [anatomy, setAnatomy] = useState<RackAnatomy | null>(null);
  const [trace, setTrace] = useState<PowerOnState[]>([]);
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
  // Apply the #step=/#phase= deep-link once per scenario — a reading-level
  // refetch must not yank the cursor back, but a new scenario is a new trace
  // and always starts from the hash's step, or from zero.
  const appliedFor = useRef<ScenarioId | null>(null);
  const loadedOnce = useRef(false);
  // The guided tour pins steps of the nominal trace, so the tour page always
  // plays that one whatever the power-on page has selected.
  const liveScenario: ScenarioId = page === "tour" ? "nominal" : scenario;
  const speedRef = useRef(speed);
  speedRef.current = speed;
  const traceRef = useRef<PowerOnState[]>([]);
  traceRef.current = trace;
  const scenarioRef = useRef(scenario);
  scenarioRef.current = scenario;

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
        if (appliedFor.current !== liveScenario) {
          const start = initialStepFromHash(po.trace);
          if (loadedOnce.current) {
            stop();
            setCursor(start ?? 0);
          } else if (start !== null) {
            // First load: leave the cursor alone unless the link names a
            // step — a #tour/<step> link may already have placed it.
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
      .catch(() => setScenarios([])); // no picker; the nominal trace still plays
  }, [level]);

  // The picker: a new scenario is a new trace, so playback stops and the
  // cursor returns to the first step (the fetch effect above does both).
  const chooseScenario = useCallback((id: ScenarioId) => {
    window.history.replaceState(
      null,
      "",
      id === "nominal" ? window.location.pathname : `#scenario=${id}`,
    );
    appliedFor.current = null;
    setScenario(id);
  }, []);

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
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (GPU init, NVLink fabric training) so their
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

  // Follow the hash after load: in-page links (the use-case page's "Go
  // deeper" buttons), the back button, and a #step=/#phase= link typed into
  // an open tab all change the hash without remounting the app.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      if (pageFromHash() === "poweron") {
        const next = scenarioFromHash();
        if (next !== scenarioRef.current) {
          // A different trace: let the fetch effect place the cursor once it
          // has the right steps to place it in.
          appliedFor.current = null;
          setScenario(next);
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
        <h1>PowerEdge XE9712</h1>
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
            Inside the rack
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
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // RackView draws a 2.5-unit margin and 4 units of labels.
              stageAspect={(tour.mapWidth + 5) / (tour.mapHeight + 9)}
              regions={anatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the power-on page plays.
                stop();
                setCursor(i);
              }}
              renderStage={(stage) => (
                <RackView
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
                      Power-on trace: <strong>{state.label}</strong> · GPUs in
                      NVLink domain {state.gpusInDomain} / 72 · t+
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
              {level <= 2
                ? "What happens when this rack is switched on"
                : "What happens when a GB200 NVL72 rack powers on"}
            </h2>
            {level <= 2 ? (
              <p>
                This is not a computer that goes in a rack — the whole rack is
                one computer. Power shelves at the top turn the building's
                electricity into the kind the machine uses and send it down a
                metal power rail, called a busbar, at the back of the rack.
                Then, before a single chip is allowed to switch on, the
                cooling has to prove itself: coolant is pumped through the
                whole rack first, because these chips run far too hot for
                fans to cope with. Only then do the 18 shelves of computing
                wake up together. Each one carries Grace processors, which
                run the ordinary work, and Blackwell graphics processors
                (GPUs, the chips that do the mathematics behind modern
                artificial intelligence). Last, thousands of copper cables
                link the 72 graphics processors together so tightly that
                software treats them as one enormous processor. Play the
                sequence and watch each step light up the hardware it uses.
              </p>
            ) : (
              <p>
                The XE9712 is not a server in a rack — it is the rack. Power
                shelves energize a DC busbar, and then, before any GPU is
                allowed on, the coolant loop must prove itself: liquid before
                silicon. Eighteen compute trays boot their Grace CPUs in
                lockstep, seventy-two Blackwell GPUs wake on their cold plates,
                and the NVLink links train over thousands of copper cables —
                until the fabric fuses all 72 into a single domain, which NVIDIA
                describes as one giant GPU. Play the trace and watch each stage light up the hardware
                it runs on.
              </p>
            )}
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
                <RackView
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
                {level <= 2 ? (
                  <>
                    The lit blocks are the parts doing work at this step. Two
                    things are worth watching. The cooling loop lights up
                    before any chip does. And the count of joined graphics
                    processors stays at zero the whole way through, then jumps
                    straight to 72 the moment the cables finish linking them —
                    there is no halfway. Click a block to see what it is; the
                    narrated walk-through is under Guided tour.
                    {scenario !== "nominal" &&
                      " In the cooling-fault run, the shelf whose coolant failed is outlined in dashed red and stays dark for as long as the fault lasts."}
                  </>
                ) : (
                  <>
                    Highlighted blocks are the parts doing work at this step.
                    Watch the cooling loop light up before any compute does, and
                    watch the GPUs-in-domain counter: it stays at zero through
                    the whole bring-up, then snaps to 72 when the NVLink fabric
                    fuses. Click a block to pin what it is; the narrated
                    walk-through lives under Guided tour.
                    {scenario !== "nominal" &&
                      " In the coolant-fault scenario a faulted tray is outlined in dashed red and stays unlit while the fault stands."}
                  </>
                )}
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerOnControls
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
            <PowerOnCounters
              state={state}
              stepIndex={cursor}
              stepCount={trace.length}
              fault={scenario !== "nominal"}
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
                {scenario !== "nominal" && (
                  <span className="legend-failed">
                    <i
                      style={{
                        background: "#3a1016",
                        border: "1px dashed var(--dell-error)",
                      }}
                    />
                    faulted
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
