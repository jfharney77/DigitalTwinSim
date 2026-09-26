import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  fetchWorkloadPresets,
  simulate,
} from "./api";
import { ControlPanel } from "./components/ControlPanel";
import { Instruments } from "./components/Instruments";
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { LoopView } from "./components/LoopView";
import { StripCharts } from "./components/StripCharts";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { useLevel } from "./level";
import type {
  CduConfig,
  ConfigPreset,
  Environment,
  Explain,
  GuidedScenario,
  LoopMap,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Any change re-requests the trace; interactive
// mid-run actions (pump kills) become timed events at the current cursor.

const DEFAULT_CONFIG: CduConfig = {
  trayGroups: 5, pumps: 3, flowSetpointLpm: 340, minSupplyC: 32,
  policy: "coordinated",
};
const DEFAULT_WORKLOAD: Workload = { utilPct: 100 };
const DEFAULT_ENV: Environment = { facilitySupplyC: 17, dewPointC: 12 };

const SPEEDS = [1, 10, 60];

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: size-the-cdu, warm-water-day, warm-water-panic,
// one-pump-down, no-spare, humid-morning). Returns null when the hash
// names no scenario.
function scenarioIdFromHash(): string | null {
  const m = window.location.hash.match(/#scenario=([a-z0-9_-]+)$/i);
  return m ? m[1] : null;
}

// Keep the address bar pointing at what is loaded without firing hashchange.
function writeHash(hash: string) {
  const url = window.location.pathname + window.location.search + hash;
  window.history.replaceState(null, "", url);
}

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<LoopMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  const [config, setConfig] = useState<CduConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [environment, setEnvironment] = useState<Environment>(DEFAULT_ENV);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(900);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  const activeScenario = scenarios.find((g) => g.id === activeScenarioId) ?? null;
  // Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;
  const setActiveScenario = (g: GuidedScenario | null) => {
    setActiveScenarioId(g ? g.id : null);
    // Leaving a guided scenario inside lab mode keeps the lab's deep link.
    const labHash = labFromHash();
    const rest = labHash.open ? (labHash.id ? `#lab=${labHash.id}` : "#labs") : "";
    writeHash(g ? `#scenario=${g.id}` : rest);
  };

  // Prose-bearing content refetches on level change.
  useEffect(() => {
    Promise.all([fetchAnatomy(), fetchScenarios(), fetchExplain()])
      .then(([an, sc, ex]) => {
        setAnatomy(an);
        setScenarios(sc);
        setExplains(ex);
      })
      .catch((e) => setError(String(e)));
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    Promise.all([fetchConfigPresets(), fetchWorkloadPresets()])
      .then(([cp, wp]) => {
        setConfigPresets(cp);
        setWorkloadPresets(wp);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, workload, environment, durationS, events }),
    [config, workload, environment, durationS, events],
  );

  // Debounced re-simulation on any scenario change.
  const debounce = useRef<number | null>(null);
  useEffect(() => {
    if (debounce.current !== null) clearTimeout(debounce.current);
    debounce.current = window.setTimeout(() => {
      simulate(scenario)
        .then((r) => {
          setResult(r);
          setCursor((c) => Math.min(c, r.trace.length - 1));
          setError(null);
        })
        .catch((e) => setError(String(e)));
    }, 250);
    return () => {
      if (debounce.current !== null) clearTimeout(debounce.current);
    };
  }, [scenario, level]);

  const trace = result?.trace ?? [];
  const state = trace[cursor] ?? null;

  // Playback clock: 500 ms real tick advances `speed / 2` sim seconds.
  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + Math.max(1, Math.round(speed / 2)), trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  // Dead pumps at the current cursor, derived from the event list.
  const deadPumps = useMemo(() => {
    const dead = new Set<number>();
    const t = state?.t ?? 0;
    for (const e of events) {
      if (e.atS <= t && e.index != null) {
        if (e.action === "fail-pump") dead.add(e.index);
        if (e.action === "restore-pump") dead.delete(e.index);
      }
    }
    return dead;
  }, [events, state]);

  const togglePump = useCallback(
    (index: number) => {
      const t = state?.t ?? 0;
      setEvents((evs) => [
        ...evs,
        {
          atS: t,
          action: deadPumps.has(index) ? "restore-pump" : "fail-pump",
          index,
        },
      ]);
    },
    [state, deadPumps],
  );

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEnvironment(g.scenario.environment);
    setEvents(g.scenario.events);
    setDurationS(g.scenario.durationS);
    setCursor(0);
    setRunning(true);
  }, []);

  // Apply a #scenario= deep link once the scenario list first arrives, and
  // follow the hash afterwards (a link typed into an open tab, back button).
  const hashApplied = useRef(false);
  useEffect(() => {
    if (hashApplied.current || scenarios.length === 0) return;
    hashApplied.current = true;
    const id = scenarioIdFromHash();
    const g = scenarios.find((x) => x.id === id);
    if (g) applyGuided(g);
  }, [scenarios, applyGuided]);
  useEffect(() => {
    const onHash = () => {
      const id = scenarioIdFromHash();
      const g = scenarios.find((x) => x.id === id);
      if (g) applyGuided(g);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [scenarios, applyGuided]);

  // Labs: load a lab's start scenario into the ordinary controls. The start
  // is the naive default — it does not pass — and everything after that is
  // the learner's own work with the same dials every other mode uses.
  const loadLabStart = useCallback((lab: Lab) => {
    setActiveScenarioId(null);
    setConfig(lab.start.config);
    setWorkload(lab.start.workload);
    setEnvironment(lab.start.environment);
    setEvents(lab.start.events);
    setDurationS(lab.start.durationS);
    setCursor(0);
    setRunning(false);
  }, []);
  const selectLab = useCallback(
    (lab: Lab) => {
      setLabsOpen(true);
      setActiveLabId(lab.id);
      writeHash(`#lab=${lab.id}`);
      loadLabStart(lab);
    },
    [loadLabStart],
  );
  // Apply a #lab=<id> deep link once the labs arrive, and follow the hash.
  const labHashApplied = useRef(false);
  useEffect(() => {
    if (labHashApplied.current || labs.length === 0) return;
    labHashApplied.current = true;
    const lab = labs.find((l) => l.id === labFromHash().id);
    if (lab) loadLabStart(lab);
  }, [labs, loadLabStart]);
  useEffect(() => {
    const onHash = () => {
      const h = labFromHash();
      if (!h.open) return;
      setLabsOpen(true);
      setActiveLabId(h.id);
      const lab = labs.find((l) => l.id === h.id);
      if (lab) loadLabStart(lab);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, [labs, loadLabStart]);

  const coldStart = () => {
    // Inside a lab the scripted disturbance (a chiller trip, a pump failure)
    // is part of the problem, so Reset returns to the lab's events rather
    // than deleting them. The UI has no other way to rebuild a timed recovery.
    setEvents(labsOpen && activeLab ? activeLab.start.events : []);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>PowerCool CDU · Loop Physics</h1>
        <nav className="nav">
          <button
            className={explainOn ? "active" : ""}
            onClick={() => setExplainOn(!explainOn)}
          >
            Explain mode
          </button>
          <button
            className={labsOpen ? "active nav-labs" : "nav-labs"}
            onClick={() => {
              setLabsOpen(!labsOpen);
              writeHash(labsOpen ? "" : activeLabId ? `#lab=${activeLabId}` : "#labs");
            }}
          >
            Labs
          </button>
        </nav>
        <span className="sub">
          {state
            ? `t+${state.t}s · ${state.heatRemovedKw.toFixed(0)} kW moved · cap ${config.policy === "uncoordinated" ? "off" : `${state.capPct.toFixed(0)}%`}`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Facility water → heat exchanger → coolant → silicon → policy</h2>
        {/* The anatomy overview is authored at every reading level; the
            static text is only the fallback until it arrives. */}
        <p>
          {anatomy?.overview ??
            "A coolant distribution unit is a wall between two loops: " +
              "facility water on one side, the rack's coolant on the other, " +
              "and the Integrated Rack Controller deciding what gives when " +
              "the loop cannot keep up."}
        </p>
        <p>
          Companions: the DellIR7000 twin (this loop's commissioning story)
          and the DellPowerEdgeXE9712 twin (the trays making the heat). The
          physics is simplified on purpose; every constant is sourced or
          labeled an estimate.
        </p>
      </div>

      {labsOpen && (
        <LabPanel
          labs={labs}
          lab={activeLab}
          scenario={scenario}
          explains={explains}
          onSelect={selectLab}
          onLoadStart={loadLabStart}
          onExplain={() => setExplainOn(true)}
          onClose={() => {
            setLabsOpen(false);
            writeHash("");
          }}
        />
      )}

      <div className="thermal-grid">
        {/* Left — build panel + guided scenarios */}
        <div className="thermal-col">
          <ControlPanel
            config={config}
            presets={configPresets}
            validations={result?.validations ?? []}
            onChange={(c) => setConfig(c)}
            onPreset={(p) => {
              setConfig(p.config);
              setActiveScenario(null);
            }}
          />
          <div className="an-panel">
            <h2>Guided scenarios</h2>
            <div className="scenario-list">
              {scenarios.map((g) => (
                <button
                  key={g.id}
                  className={activeScenario?.id === g.id ? "active" : ""}
                  onClick={() => applyGuided(g)}
                >
                  {g.title}
                </button>
              ))}
            </div>
            {activeScenario && (
              <div className="mini scenario-narration">
                {activeScenario.narration.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
                <p className="scenario-question">? {activeScenario.question}</p>
                {activeScenario.answer && (
                  <details className="scenario-answer" key={activeScenario.id}>
                    <summary>Show the answer</summary>
                    <p>{activeScenario.answer}</p>
                  </details>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Center — loop map + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <LoopView
                anatomy={anatomy}
                state={state}
                deadPumps={deadPumps}
                installedPumps={config.pumps}
                selected={regionId}
                onSelect={setRegionId}
                onTogglePump={togglePump}
              />
            )}
            <div className="btnrow playback-row">
              <button
                className="primary"
                onClick={() => {
                  // Run from the last tick replays rather than doing nothing.
                  if (!running && cursor >= trace.length - 1) setCursor(0);
                  setRunning(!running);
                }}
              >
                {running ? "Pause" : "Run"}
              </button>
              {SPEEDS.map((s) => (
                <button
                  key={s}
                  className={speed === s ? "active" : ""}
                  onClick={() => setSpeed(s)}
                >
                  ×{s}
                </button>
              ))}
              <button onClick={coldStart}>Reset</button>
              <input
                type="range"
                min={0}
                max={Math.max(trace.length - 1, 0)}
                value={cursor}
                onChange={(e) => {
                  setRunning(false);
                  setCursor(+e.target.value);
                }}
                style={{ flex: 1 }}
              />
            </div>
            {selectedRegion && (
              <div className="mini region-card">
                <strong>{selectedRegion.label}.</strong>{" "}
                {selectedRegion.description}
              </div>
            )}
          </div>
          <div className="an-panel">
            <h2>Event log</h2>
            <div className="event-log">
              {visibleLog.length === 0 && (
                <div className="mini">No events yet — provoke some.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  t+{e.t}s — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            {level <= 2 ? (
              <>
                This is a simplified model. It leaves out several real
                effects, and nearly every number in it is an estimate rather
                than a measurement — the backend's constants table says which
                is which. The biggest simplification: the gap between the
                facility water and the coolant is about 30 K here, where a
                real exchanger runs 2–5 K, so do not size a plant from it.
              </>
            ) : (
          <>
            What we don't model: NTU heat-exchanger integration, pump heat
            into the coolant, filter fouling, glycol aging, water-side
            economizer dynamics, tray-level self-throttling (a tray bank here
            is either at full speed or tripped off, so the uncoordinated mode
            is a worst case; real trays slow their own clocks before a hard
            trip), a realistic heat-exchanger approach (this model's is about
            30 K at rated load where real plate exchangers run 2–5 K, set so
            the 220 kW class binds on 17 °C water), leak events (the IRC's headline feature —
            a detection story, not a thermodynamics one), and CFD (computational fluid dynamics) anywhere.
            The C7000 and PowerRack were announced in May 2026 (the IRC in
            November 2025); press-release depth is what's public, so nearly every constant is an estimate and says
            so in the backend's table.
          </>
            )}
          </div>
        </div>

        {/* Right — workload, environment, instruments, charts */}
        <div className="thermal-col">
          <div className="an-panel">
            <h2>Workload</h2>
            <div className="btnrow">
              {workloadPresets.map((w) => (
                <button key={w.id} onClick={() => setWorkload(w.workload)}>
                  {w.name}
                </button>
              ))}
            </div>
            <label className="field">
              Utilization {workload.utilPct}%
              <input
                type="range" min={0} max={100} value={workload.utilPct}
                onChange={(e) => setWorkload({ utilPct: +e.target.value })}
              />
            </label>
          </div>
          <div className="an-panel">
            <h2>Environment</h2>
            <label className="field">
              Facility supply {environment.facilitySupplyC} °C at start
              {state && state.facSupplyC !== environment.facilitySupplyC
                ? ` · now ${state.facSupplyC.toFixed(0)} °C after a timed event`
                : ""}
              <input
                type="range" min={8} max={45} value={environment.facilitySupplyC}
                onChange={(e) =>
                  setEnvironment({ ...environment, facilitySupplyC: +e.target.value })
                }
              />
              <span className="mini">
                ASHRAE classes: W32 ≤32 °C · W40 ≤40 °C · W45 ≤45 °C. Dell states the C7000 accepts up to 40 °C.
              </span>
            </label>
            <label className="field">
              Room dew point {environment.dewPointC} °C at start
              {state && Math.abs(state.secSupplyC - state.dewMarginC - environment.dewPointC) > 0.05
                ? ` · now ${(state.secSupplyC - state.dewMarginC).toFixed(0)} °C after a timed event`
                : ""}
              <input
                type="range" min={2} max={28} value={environment.dewPointC}
                onChange={(e) =>
                  setEnvironment({ ...environment, dewPointC: +e.target.value })
                }
              />
              <span className="mini">
                {level <= 2
                  ? "Pipes colder than the dew point sweat, so the CDU's mixing valve keeps the coolant at least 2 degrees above it."
                  : "The mixing valve holds coolant supply ≥ dew point + 2 K."}
              </span>
            </label>
            <div className="btnrow">
              <button
                onClick={() =>
                  setEvents((evs) => [
                    ...evs,
                    {
                      atS: state?.t ?? 0,
                      action: "set-facility-supply",
                      value: environment.facilitySupplyC + 6,
                    },
                  ])
                }
              >
                Warm-water event (+6 °C) now
              </button>
              <button
                onClick={() =>
                  setEvents((evs) => [
                    ...evs,
                    { atS: state?.t ?? 0, action: "add-tray-group" },
                  ])
                }
              >
                Add a tray bank now
              </button>
            </div>
          </div>
          <Instruments
            state={state}
            explains={explains}
            explainOn={explainOn}
            policy={config.policy}
            level={level}
          />
          <StripCharts
            trace={trace}
            cursor={cursor}
            capOff={config.policy === "uncoordinated"}
          />
        </div>
      </div>
    </div>
  );
}
