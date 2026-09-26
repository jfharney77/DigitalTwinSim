import { useCallback, useEffect, useRef, useState } from "react";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import {
  BASELINE_TRACE,
  fetchAnatomy,
  fetchCatalog,
  fetchDefaultProfile,
  fetchScenarios,
  fetchTour,
  simulate,
} from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { AnatomyView } from "./components/AnatomyView";
import { UseCasePage } from "./components/UseCasePage";
import { PowerPathView } from "./components/PowerPathView";
import { PowerControls } from "./components/PowerControls";
import { PowerCounters } from "./components/PowerCounters";
import { Legend } from "./components/Legend";
import { DiagnosticReadout } from "./components/DiagnosticReadout";
import { LevelControl } from "./components/LevelControl";
import { LabPanel } from "./components/LabPanel";
import { fetchExplains, fetchLabs, labFromHash } from "./labs";
import type { Explain, Lab } from "./labs";
import { useLevel } from "./level";
import type {
  Anatomy,
  LaptopProfile,
  PowerPhase,
  PowerState,
  Scenario,
  Summary,
  ThermalMode,
  TraceScenario,
  WorkloadKind,
} from "./types";

const MAX_DWELL = 6; // cap how long the UI lingers on a slow stage (pacing only)

type Page = "sim" | "anatomy" | "usecases" | "tour";

function pageFromHash(): Page {
  const h = window.location.hash;
  if (h.startsWith("#anatomy")) return "anatomy";
  if (h.startsWith("#usecases")) return "usecases";
  if (h.startsWith("#tour")) return "tour";
  return "sim";
}

const PAGE_HASH: Record<Page, string> = {
  sim: "",
  anatomy: "anatomy",
  usecases: "usecases",
  tour: "tour",
};

// The guided tour narrates one fixed scenario, and its trace cursors index
// that scenario's trace. Must match TOUR_SCENARIO in backend/app/tour.py
// (tests/test_tour.py checks this block).
const TOUR_SCENARIO: Scenario = {
  profileId: "m18-r2",
  adapterId: "barrel-280",
  startBatteryPct: 30,
  thermalMode: "fullSpeed",
  workload: "gaming",
};

// Deep-link into the guided tour: /#tour/<stepId>. Read once, at load.
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

const TRACE_IDS = [BASELINE_TRACE, "charge-taper-diagnostics"];

function traceFromHash(): string {
  const s = hashParams().scenario;
  return s && TRACE_IDS.includes(s) ? s : BASELINE_TRACE;
}

// Deep-link into the trace. Returns the starting cursor, or null when the
// hash names neither a step nor a known phase — playback then starts at 0.
function initialStepFromHash(states: { phase: string }[]): number | null {
  if (states.length === 0) return null;
  const { step, phase } = hashParams();
  if (step !== undefined && /^\d+$/.test(step)) {
    return Math.min(Number(step), states.length - 1);
  }
  if (phase !== undefined) {
    const i = states.findIndex((s) => s.phase === phase);
    return i >= 0 ? i : null;
  }
  return null;
}

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "unplugged",
  detect: "plug detect",
  handshake: "PSID handshake",
  budget: "power budget",
  charge: "charging",
  boot: "boot",
  load: "under load",
  steady: "steady state",
  cap: "charge limit",
  taper: "taper",
  heat: "pack too hot",
  resume: "charge resumes",
  swap: "adapter unknown",
};

export function App() {
  // Deep-linkable pages: /#anatomy/<id>, /#usecases/<id>.
  const [page, setPage] = useState<Page>(pageFromHash);
  const pageRef = useRef(page);
  pageRef.current = page;
  // Which trace the sim page plays: the plug-in path, or a failure walk.
  const [traceId, setTraceId] = useState<string>(traceFromHash);
  const traceIdRef = useRef(traceId);
  traceIdRef.current = traceId;
  const [scenarios, setScenarios] = useState<TraceScenario[]>([]);
  const [traceInfo, setTraceInfo] = useState<TraceScenario | null>(null);
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<anatomyId>).
    // Compare pages rather than prefixes: every hash starts with "#", so a
    // prefix test would leave #anatomy/<id> in the URL after switching back
    // to the power path.
    if (pageFromHash() !== page) {
      // Coming back to the sim page keeps a chosen failure scenario in the
      // address bar, so the link stays shareable.
      window.location.hash =
        page === "sim" && traceIdRef.current !== BASELINE_TRACE
          ? `scenario=${traceIdRef.current}`
          : PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);
  // Follow back/forward navigation and in-page hash links.
  useEffect(() => {
    const onHash = () => {
      setPage(pageFromHash());
      if (pageFromHash() !== "sim") return;
      const next = traceFromHash();
      if (next !== traceIdRef.current) {
        // A different trace: the fetch effect places the cursor once it has
        // the right steps to place it in.
        setTraceId(next);
        return;
      }
      const start = initialStepFromHash(traceRef.current);
      if (start !== null) {
        stopRef.current();
        setCursor(start);
      }
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // --- Scenario controls ---
  const [profiles, setProfiles] = useState<LaptopProfile[]>([]);
  const [profileId, setProfileId] = useState<string>("");
  const [adapterId, setAdapterId] = useState<string>("");
  const [startBatteryPct, setStartBatteryPct] = useState(30);
  const [thermalMode, setThermalMode] = useState<ThermalMode>("balanced");
  const [workload, setWorkload] = useState<WorkloadKind>("gaming");

  // --- Trace playback ---
  const [trace, setTrace] = useState<PowerState[]>([]);
  const traceRef = useRef<PowerState[]>([]);
  const stopRef = useRef<() => void>(() => {});
  const [summary, setSummary] = useState<Summary | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(8);
  const [error, setError] = useState<string | null>(null);

  // --- Guided tour ---
  const [tour, setTour] = useState<TourResponse | null>(null);
  const [tourAnatomy, setTourAnatomy] = useState<Anatomy | null>(null);
  const [tourError, setTourError] = useState<string | null>(null);
  const [regionId, setRegionId] = useState<string | null>(null);
  const tourStart = useRef<string | null>(tourStepFromHash());
  // The trace step the tour last pinned; a trace that arrives while the tour
  // is open lands on it instead of starting over.
  const tourCursor = useRef<number | null>(null);

  const level = useLevel();
  const timer = useRef<number | null>(null);

  // --- Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;
  // Apply a #step=/#phase= deep link only on the first successful trace load.
  const hashApplied = useRef(false);
  // The scenario the loaded trace belongs to. A refetch for a new reading
  // level keeps the cursor (numbers and step count are identical across
  // levels); a new scenario starts playback over.
  const loadedScenario = useRef("");
  const loadedTrace = useRef("");
  const dwell = useRef(0); // ticks remaining on the current (possibly slow) state
  const speedRef = useRef(speed);
  speedRef.current = speed;

  const stop = useCallback(() => {
    if (timer.current !== null) {
      clearInterval(timer.current);
      timer.current = null;
    }
    setRunning(false);
  }, []);
  stopRef.current = stop;

  // The guided tour pins steps of the plug-in trace, so the tour page plays
  // that one whatever the sim page has selected.
  const liveTrace = page === "tour" ? BASELINE_TRACE : traceId;

  // Load the catalog once; start on the backend's default profile.
  useEffect(() => {
    Promise.all([fetchCatalog(), fetchDefaultProfile()])
      .then(([list, def]) => {
        setProfiles(list);
        setProfileId(def.id);
        setAdapterId(def.defaultAdapterId);
      })
      .catch((e) => setError(String(e)));
  }, []);

  // Refetch the trace whenever the scenario changes; reset the cursor. The
  // trace is pure data from the backend engine — the clock lives here.
  useEffect(() => {
    if (!profileId || !adapterId) return;
    let cancelled = false;
    simulate(
      { profileId, adapterId, startBatteryPct, thermalMode, workload },
      liveTrace,
    )
      .then((resp) => {
        if (cancelled) return;
        setTrace(resp.trace);
        traceRef.current = resp.trace;
        setSummary(resp.summary);
        setTraceInfo(resp.traceScenario ?? null);
        setError(null);
        const key = [liveTrace, profileId, adapterId, startBatteryPct, thermalMode, workload].join("|");
        const sameScenario = loadedScenario.current === key;
        // A new trace scenario is a new trace: it starts from the step its
        // link names, or from zero.
        const newTrace = loadedTrace.current !== liveTrace;
        loadedScenario.current = key;
        loadedTrace.current = liveTrace;
        const pinned = pageRef.current === "tour" ? tourCursor.current : null;
        if (!hashApplied.current || newTrace) {
          hashApplied.current = true;
          stop();
          setCursor(pinned ?? initialStepFromHash(resp.trace) ?? 0);
        } else if (!sameScenario) {
          stop();
          setCursor(pinned ?? 0);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [profileId, adapterId, startBatteryPct, thermalMode, workload, level, liveTrace, stop]);

  useEffect(() => {
    fetchScenarios()
      .then(setScenarios)
      .catch(() => setScenarios([])); // no picker; the plug-in trace still plays
  }, [level]);

  // Labs and the equations their criteria cite are leveled prose.
  useEffect(() => {
    Promise.all([fetchLabs(), fetchExplains()])
      .then(([l, e]) => {
        setLabs(l);
        setExplains(e);
      })
      .catch(() => setLabs([])); // no labs; every other mode still works
  }, [level]);

  // A lab's start scenario loads into the ordinary controls, on the plug-in
  // trace, so the lab uses the same dials as every other mode.
  const loadLabStart = useCallback((lab: Lab) => {
    setTraceId(BASELINE_TRACE);
    setProfileId(lab.start.profileId);
    setAdapterId(lab.start.adapterId);
    setStartBatteryPct(lab.start.startBatteryPct);
    setThermalMode(lab.start.thermalMode);
    setWorkload(lab.start.workload);
  }, []);
  const selectLab = useCallback(
    (lab: Lab) => {
      setLabsOpen(true);
      setActiveLabId(lab.id);
      window.history.replaceState(null, "", `#lab=${lab.id}`);
      loadLabStart(lab);
    },
    [loadLabStart],
  );
  // Apply a #lab=<id> deep link once, when both the labs and the catalog have
  // arrived (so the default profile cannot override it), then follow the hash.
  const labHashApplied = useRef(false);
  useEffect(() => {
    if (labHashApplied.current || labs.length === 0 || profiles.length === 0) return;
    labHashApplied.current = true;
    const lab = labs.find((l) => l.id === labFromHash().id);
    if (lab) loadLabStart(lab);
  }, [labs, profiles, loadLabStart]);
  useEffect(() => {
    const onLabHash = () => {
      const h = labFromHash();
      if (!h.open) return;
      setLabsOpen(true);
      setActiveLabId(h.id);
      const lab = labs.find((l) => l.id === h.id);
      if (lab) loadLabStart(lab);
    };
    window.addEventListener("hashchange", onLabHash);
    return () => window.removeEventListener("hashchange", onLabHash);
  }, [labs, loadLabStart]);

  // The picker. The hash is rewritten without a phase or step, so the new
  // trace starts from its first state.
  const chooseTrace = useCallback((id: string) => {
    window.history.replaceState(
      null,
      "",
      id === BASELINE_TRACE
        ? window.location.pathname + window.location.search
        : `#scenario=${id}`,
    );
    setTraceId(id);
  }, []);

  // The tour is fetched the first time its page opens, and again when the
  // reading level changes (the narration is leveled prose).
  const tourWanted = page === "tour" || tour !== null;
  useEffect(() => {
    if (!tourWanted) return;
    fetchTour()
      .then((t) => {
        setTour(t);
        setTourError(null);
        return fetchAnatomy(TOUR_SCENARIO.profileId);
      })
      .then(setTourAnatomy)
      .catch((e) => setTourError(String(e)));
  }, [level, tourWanted]);

  // Opening the tour switches the scenario controls to the one it narrates,
  // once the catalog has loaded (so the default profile cannot override it).
  useEffect(() => {
    if (page !== "tour" || profiles.length === 0) return;
    setProfileId(TOUR_SCENARIO.profileId);
    setAdapterId(TOUR_SCENARIO.adapterId);
    setStartBatteryPct(TOUR_SCENARIO.startBatteryPct);
    setThermalMode(TOUR_SCENARIO.thermalMode);
    setWorkload(TOUR_SCENARIO.workload);
  }, [page, profiles]);

  const state = trace[cursor] ?? null;
  const selectedRegion =
    tourAnatomy?.regions.find((r) => r.id === regionId) ?? null;
  const done = cursor >= trace.length - 1 && trace.length > 0;

  const run = useCallback(() => {
    if (timer.current !== null || trace.length === 0) return;
    // restart if finished
    setCursor((c) => (c >= trace.length - 1 ? 0 : c));
    setRunning(true);
    dwell.current = 0;
    const tick = () => {
      // Linger on long stages (charging, boot) so their real-world cost is
      // visible.
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

  const failure = page === "sim" && traceId !== BASELINE_TRACE;
  const profile = profiles.find((p) => p.id === profileId) ?? null;
  const adapters = profile?.adapters ?? [];

  // Switching machines also switches to that machine's default adapter, so a
  // stale adapter id never rides along into the next simulate call.
  const onProfile = useCallback(
    (id: string) => {
      setProfileId(id);
      const p = profiles.find((x) => x.id === id);
      if (p) setAdapterId(p.defaultAdapterId);
    },
    [profiles],
  );

  return (
    <div className="app dell">
      <header>
        <h1>Alienware m18 — inside the power path</h1>
        <nav className="nav">
          <button
            className={page === "sim" ? "active" : ""}
            onClick={() => setPage("sim")}
          >
            Power path
          </button>
          <button
            className={page === "anatomy" ? "active" : ""}
            onClick={() => setPage("anatomy")}
          >
            Inside the m18
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
          <button
            className={page === "sim" && labsOpen ? "active nav-labs" : "nav-labs"}
            onClick={() => {
              if (page === "sim" && labsOpen) {
                setLabsOpen(false);
                window.history.replaceState(
                  null,
                  "",
                  window.location.pathname + window.location.search,
                );
                return;
              }
              // The lab hashes land on the power-path page; the hashchange
              // listeners switch the page and open the panel.
              setLabsOpen(true);
              window.location.hash = activeLabId ? `#lab=${activeLabId}` : "#labs";
            }}
          >
            Labs
          </button>
        </nav>
        {page === "sim" && state && (
          <span className="badge">{PHASE_LABEL[state.phase]}</span>
        )}
        {page === "sim" && (
          <span className="sub">
            {state
              ? `${state.label} · step ${cursor + 1}/${trace.length}`
              : "—"}
          </span>
        )}
        <LevelControl />
      </header>

      {page === "anatomy" && <AnatomyPage />}
      {page === "usecases" && <UseCasePage />}

      {page === "tour" && (
        <div className="tour-page">
          {(tourError || error) && (
            <div className="mini an-error">{tourError ?? error}</div>
          )}
          {tour && tourAnatomy && (
            <TourPlayer
              tour={tour.tour}
              layers={tour.layers}
              bounds={{ width: tour.mapWidth, height: tour.mapHeight }}
              // AnatomyView draws a 2.5-unit outline margin and a 4-unit
              // orientation strip: 105 x 71 for the 100 x 62 map.
              stageAspect={105 / 71}
              regions={tourAnatomy.regions}
              initialStepId={tourStart.current}
              onStepChange={(id) => {
                tourStart.current = id;
                window.history.replaceState(null, "", `#tour/${id}`);
              }}
              onTraceCursor={(i) => {
                // The tour drives the same cursor the power-path page plays.
                stop();
                tourCursor.current = i;
                setCursor(i);
              }}
              renderStage={(stage) => (
                <AnatomyView
                  anatomy={tourAnatomy}
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
                      Power-path trace: <strong>{state.label}</strong> · adapter{" "}
                      {state.acW} W, battery {state.batteryW > 0 ? `supplying ${state.batteryW} W` : `at ${state.batteryPct}%`}
                      {" "}(illustrative)
                    </p>
                  )}
                  {state && <PowerPathView state={state} />}
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

      {page === "sim" && (
        <>
          <div className="an-hero">
            <h2>
              {failure
                ? "It stopped charging at 80%"
                : "What happens when you plug it in"}
            </h2>
            {failure && (
              <p>
                {traceInfo?.summary ??
                  "One complaint, four causes, and the readouts that tell them apart."}
              </p>
            )}
            <p hidden={failure}>
              A 280 W gaming laptop never just "takes power". The adapter must
              first prove what it is over a 1-Wire ID pin, the EC (embedded
              controller) sets a power budget from that answer, the charger IC
              routes watts between adapter, battery and silicon — and under a
              heavy enough load the battery quietly pitches in even while
              plugged in. Play the trace and watch the flows.
            </p>
            <button
              className="primary sim-tour-link"
              onClick={() => setPage("tour")}
            >
              Guided tour
            </button>
          </div>
          {labsOpen && (
            <LabPanel
              labs={labs}
              lab={activeLab}
              scenario={{ profileId, adapterId, startBatteryPct, thermalMode, workload }}
              explains={explains}
              onSelect={selectLab}
              onLoadStart={loadLabStart}
              onClose={() => {
                setLabsOpen(false);
                window.history.replaceState(
                  null,
                  "",
                  window.location.pathname + window.location.search,
                );
              }}
            />
          )}
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              <PowerPathView state={state} />
              {failure && state && <DiagnosticReadout state={state} info={traceInfo} />}
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step; lit
                lines carry power, labelled with live wattage. The full tour of
                the real hardware lives under Inside the m18.
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerControls
              scenarios={scenarios}
              traceId={traceId}
              onTrace={chooseTrace}
              profiles={profiles}
              profileId={profileId}
              onProfile={onProfile}
              adapters={adapters}
              adapterId={adapterId}
              onAdapter={setAdapterId}
              startBatteryPct={startBatteryPct}
              onStartBatteryPct={setStartBatteryPct}
              thermalMode={thermalMode}
              onThermalMode={setThermalMode}
              workload={workload}
              onWorkload={setWorkload}
              speed={speed}
              onSpeed={setSpeed}
              running={running}
              done={done}
              phaseLabel={state?.label ?? "—"}
              onRun={run}
              onPause={stop}
              onStep={step}
              onReset={reset}
            />
            <PowerCounters
              state={state}
              summary={summary}
              heroLabel={failure ? traceInfo?.heroLabel ?? null : null}
              stepIndex={cursor}
              stepCount={trace.length}
            />
            <Legend failure={failure} />
          </aside>
        </>
      )}
    </div>
  );
}
