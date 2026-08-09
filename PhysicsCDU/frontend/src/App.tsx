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
import { LevelControl } from "./components/LevelControl";
import { LoopView } from "./components/LoopView";
import { StripCharts } from "./components/StripCharts";
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
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

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

  // Prose-bearing content refetches on level change.
  useEffect(() => {
    Promise.all([fetchAnatomy(), fetchScenarios(), fetchExplain()])
      .then(([an, sc, ex]) => {
        setAnatomy(an);
        setScenarios(sc);
        setExplains(ex);
      })
      .catch((e) => setError(String(e)));
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
  }, [scenario]);

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

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEnvironment(g.scenario.environment);
    setEvents(g.scenario.events);
    setDurationS(g.scenario.durationS);
    setCursor(0);
    setRunning(true);
  };

  const coldStart = () => {
    setEvents([]);
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
        </nav>
        <span className="sub">
          {state
            ? `t+${state.t}s · ${state.heatRemovedKw.toFixed(0)} kW moved · cap ${state.capPct.toFixed(0)}%`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Facility water → heat exchanger → coolant → silicon → policy</h2>
        <p>
          A coolant distribution unit is a wall between two loops, and this
          is the chain that runs through it: facility supply plus the heat
          exchanger's approach makes the coolant supply, the coolant warms
          crossing the rack, and the silicon rides on top. When the water
          runs warm or a pump dies, something must give — and the
          Integrated Rack Controller decides whether the rack sheds load
          together or every tray panics alone. Both loops carry the same
          heat on every tick; the physics is simplified on purpose and
          every constant is sourced or labeled an estimate. Companions:
          the DellIR7000 twin (this loop's commissioning story) and the
          DellPowerEdgeXE9712 twin (the trays making the heat).
        </p>
      </div>

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
              <button className="primary" onClick={() => setRunning(!running)}>
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
            What we don't model: NTU heat-exchanger integration, pump heat
            into the coolant, filter fouling, glycol aging, water-side
            economizer dynamics, leak events (the IRC's headline feature —
            a detection story, not a thermodynamics one), and CFD anywhere.
            The C7000/PowerRack/IRC shipped in 2026; press-release depth is
            what's public, so nearly every constant is an estimate and says
            so in the backend's table.
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
              Facility supply {environment.facilitySupplyC} °C
              <input
                type="range" min={8} max={45} value={environment.facilitySupplyC}
                onChange={(e) =>
                  setEnvironment({ ...environment, facilitySupplyC: +e.target.value })
                }
              />
              <span className="mini">
                ASHRAE classes: W32 ≤32 °C · W45 ≤45 °C
              </span>
            </label>
            <label className="field">
              Room dew point {environment.dewPointC} °C
              <input
                type="range" min={2} max={28} value={environment.dewPointC}
                onChange={(e) =>
                  setEnvironment({ ...environment, dewPointC: +e.target.value })
                }
              />
              <span className="mini">
                The mixing valve holds supply ≥ dew point + 2 K.
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
          <Instruments state={state} explains={explains} explainOn={explainOn} />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
