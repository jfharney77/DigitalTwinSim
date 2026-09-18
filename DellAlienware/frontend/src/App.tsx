import { useCallback, useEffect, useRef, useState } from "react";
import { TourPlayer } from "@twinsim/twin-ui";
import type { TourResponse } from "@twinsim/twin-ui";
import { fetchAnatomy, fetchCatalog, fetchDefaultProfile, fetchTour, simulate } from "./api";
import { AnatomyPage } from "./components/AnatomyPage";
import { AnatomyView } from "./components/AnatomyView";
import { UseCasePage } from "./components/UseCasePage";
import { PowerPathView } from "./components/PowerPathView";
import { PowerControls } from "./components/PowerControls";
import { PowerCounters } from "./components/PowerCounters";
import { Legend } from "./components/Legend";
import { LevelControl } from "./components/LevelControl";
import { useLevel } from "./level";
import type {
  Anatomy,
  LaptopProfile,
  PowerPhase,
  PowerState,
  Scenario,
  Summary,
  ThermalMode,
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

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "unplugged",
  detect: "plug detect",
  handshake: "PSID handshake",
  budget: "power budget",
  charge: "charging",
  boot: "boot",
  load: "under load",
  steady: "steady state",
};

export function App() {
  // Deep-linkable pages: /#anatomy/<id>, /#usecases/<id>.
  const [page, setPage] = useState<Page>(pageFromHash);
  const pageRef = useRef(page);
  pageRef.current = page;
  useEffect(() => {
    // Only overwrite the hash for top-level switches; pages may append their
    // own deep-link segments (e.g. #anatomy/<anatomyId>).
    // Compare pages rather than prefixes: every hash starts with "#", so a
    // prefix test would leave #anatomy/<id> in the URL after switching back
    // to the power path.
    if (pageFromHash() !== page) {
      window.location.hash = PAGE_HASH[page];
    }
    document.body.classList.add("dell-body");
  }, [page]);
  // Follow back/forward navigation and in-page hash links.
  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
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
  // Apply a #step=/#phase= deep link only on the first successful trace load.
  const hashApplied = useRef(false);
  // The scenario the loaded trace belongs to. A refetch for a new reading
  // level keeps the cursor (numbers and step count are identical across
  // levels); a new scenario starts playback over.
  const loadedScenario = useRef("");
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
    simulate({ profileId, adapterId, startBatteryPct, thermalMode, workload })
      .then((resp) => {
        if (cancelled) return;
        setTrace(resp.trace);
        setSummary(resp.summary);
        setError(null);
        const key = [profileId, adapterId, startBatteryPct, thermalMode, workload].join("|");
        const sameScenario = loadedScenario.current === key;
        loadedScenario.current = key;
        const pinned = pageRef.current === "tour" ? tourCursor.current : null;
        if (!hashApplied.current) {
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
  }, [profileId, adapterId, startBatteryPct, thermalMode, workload, level, stop]);

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
            <h2>What happens when you plug it in</h2>
            <p>
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
          <div className="stage">
            <div className="an-card">
              {error && <div className="mini an-error">{error}</div>}
              <PowerPathView state={state} />
              <div className="mini an-hint">
                Highlighted blocks are the parts doing work at this step; lit
                lines carry power, labelled with live wattage. The full tour of
                the real hardware lives under Inside the m18.
              </div>
            </div>
          </div>

          <aside className="controls">
            <PowerControls
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
              stepIndex={cursor}
              stepCount={trace.length}
            />
            <Legend />
          </aside>
        </>
      )}
    </div>
  );
}
