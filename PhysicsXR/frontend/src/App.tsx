import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  fetchWorkloadPresets,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { ThermalChassisView } from "./components/ThermalChassisView";
import { useLevel } from "./level";
import type {
  ChassisMap,
  ConfigPreset,
  Environment,
  Explain,
  GuidedScenario,
  Scenario,
  ServerConfig,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Any change re-requests the trace; interactive
// mid-run actions (fan kills, filter changes, voltage sags) become timed
// events at the current cursor.

const DEFAULT_CONFIG: ServerConfig = {
  platform: "xr8000", cpuTdpW: 225, thermalConfig: "standard",
  dimms: 8, driveType: "ssd", drives: 2, accelsSingleWide: 2,
  ioCardW: 100, psuCount: 1, psuCapacityW: 800, redundancy: "1+0",
};
const DEFAULT_WORKLOAD: Workload = { cpuPct: 85, memPct: 50, storagePct: 10, accelPct: 60 };
const DEFAULT_ENV: Environment = {
  inletC: 25, altitudeM: 0, dust: "moderate", filterMonths: 0, vibration: "none",
};

const SPEEDS = [1, 10, 60];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<ChassisMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<ServerConfig>(DEFAULT_CONFIG);
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

  // Dead fans at the current cursor, derived from the event list.
  const deadFans = useMemo(() => {
    const dead = new Set<number>();
    const t = state?.t ?? 0;
    for (const e of events) {
      if (e.atS <= t && e.index != null) {
        if (e.action === "kill-fan") dead.add(e.index);
        if (e.action === "restore-fan") dead.delete(e.index);
      }
    }
    return dead;
  }, [events, state]);

  const toggleFan = useCallback(
    (index: number) => {
      const t = state?.t ?? 0;
      setEvents((evs) => [
        ...evs,
        {
          atS: t,
          action: deadFans.has(index) ? "restore-fan" : "kill-fan",
          index,
        },
      ]);
    },
    [state, deadFans],
  );

  const cleanFilterNow = useCallback(() => {
    const t = state?.t ?? 0;
    setEvents((evs) => [...evs, { atS: t, action: "clean-filter" }]);
  }, [state]);

  const sagNow = useCallback(() => {
    const t = state?.t ?? 0;
    setEvents((evs) => [
      ...evs,
      { atS: t, action: "voltage-sag", value: 65, seconds: 10 },
    ]);
  }, [state]);

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
        <h1>PowerEdge XR · Rugged Edge</h1>
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
            ? `t+${state.t}s · ${state.poweredOn ? "running" : "OFF"} · ${state.acPowerW.toFixed(0)} W wall · ${environment.inletC} °C outside`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>The R760's physics, on hostile ground</h2>
        <p>
          The same causal chain every server lives by — load makes power,
          power makes heat, heat spins the fans — with the environment
          sliders unlocked to where the XR-series actually lives: −25 to
          65 °C ambient, dust that fouls the filter over sim-months,
          vibration that taxes spinning drives, and a single-phase feed
          that browns out. The rated envelopes (−5…55 °C standard, −20…65
          °C on select extended configs) are Dell's documented numbers;
          the fouling and vibration rates are labeled estimates. This is
          a physics companion to the repo's narrative twins, not a
          service manual.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — build panel */}
        <div className="thermal-col">
          <BuildPanel
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

        {/* Center — chassis + charts + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <ThermalChassisView
                anatomy={anatomy}
                state={state}
                deadFans={deadFans}
                selected={regionId}
                onSelect={setRegionId}
                onToggleFan={toggleFan}
                onCleanFilter={cleanFilterNow}
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
              <button onClick={coldStart}>Reset to cold start</button>
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
            What we don't model: CFD, per-core DVFS, condensation and
            material brittleness at the cold end (the real reasons for the
            lower rating), corrosion, filter media chemistry, and the −48 V
            DC telecom feed (the sag model is single-phase AC). PSU
            conversion loss vents outside the front-to-back path. The rated
            envelopes are Dell's documented numbers; most other constants
            are estimates — every one carries a source tag in the backend's
            constants table.
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
            {(
              [
                ["CPU", "cpuPct"],
                ["Memory", "memPct"],
                ["Storage", "storagePct"],
                ["Accelerator", "accelPct"],
              ] as const
            ).map(([label, key]) => (
              <label key={key} className="field">
                {label} {workload[key]}%
                <input
                  type="range" min={0} max={100} value={workload[key]}
                  onChange={(e) =>
                    setWorkload({ ...workload, [key]: +e.target.value })
                  }
                />
              </label>
            ))}
          </div>
          <div className="an-panel">
            <h2>Environment — the unlocked sliders</h2>
            <label className="field">
              Ambient {environment.inletC} °C
              <input
                type="range" min={-25} max={65} value={environment.inletC}
                onChange={(e) =>
                  setEnvironment({ ...environment, inletC: +e.target.value })
                }
              />
              <span className="mini">
                Rated: −5…55 °C standard · −20…65 °C extended (select configs)
              </span>
            </label>
            <label className="field">
              Altitude {environment.altitudeM} m
              <input
                type="range" min={0} max={3000} step={100}
                value={environment.altitudeM}
                onChange={(e) =>
                  setEnvironment({ ...environment, altitudeM: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Site dust
              <select
                value={environment.dust}
                onChange={(e) =>
                  setEnvironment({
                    ...environment,
                    dust: e.target.value as Environment["dust"],
                  })
                }
              >
                <option value="clean">Clean (filtered indoor)</option>
                <option value="moderate">Moderate (roadside cabinet)</option>
                <option value="heavy">Heavy (desert rooftop, factory)</option>
              </select>
            </label>
            <label className="field">
              Months since filter service: {environment.filterMonths}
              <input
                type="range" min={0} max={24}
                value={environment.filterMonths}
                onChange={(e) =>
                  setEnvironment({
                    ...environment,
                    filterMonths: +e.target.value,
                  })
                }
              />
            </label>
            <label className="field">
              Vibration
              <select
                value={environment.vibration}
                onChange={(e) =>
                  setEnvironment({
                    ...environment,
                    vibration: e.target.value as Environment["vibration"],
                  })
                }
              >
                <option value="none">None (on a slab)</option>
                <option value="roadside">Roadside (traffic, wind)</option>
                <option value="vehicle">Vehicle (the rack is moving)</option>
              </select>
            </label>
            <div className="btnrow">
              <button onClick={sagNow}>Sag the feed (65%, 10 s)</button>
              <button onClick={cleanFilterNow}>Change the filter now</button>
              <button
                onClick={() =>
                  setEvents((evs) => [
                    ...evs,
                    { atS: state?.t ?? 0, action: "kill-psu" },
                  ])
                }
              >
                Kill a PSU
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
