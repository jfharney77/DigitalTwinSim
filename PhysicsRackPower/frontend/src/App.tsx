import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  simulate,
} from "./api";
import { ConfigPanel } from "./components/ConfigPanel";
import { LevelControl } from "./components/LevelControl";
import { PhaseMeters } from "./components/PhaseMeters";
import { RackView } from "./components/RackView";
import { StripCharts } from "./components/StripCharts";
import { UpsPanel } from "./components/UpsPanel";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Environment,
  Explain,
  GuidedScenario,
  Phase,
  RackConfig,
  RackMap,
  Scenario,
  SimEvent,
  SimResponse,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Any change re-requests the trace; interactive
// mid-run actions (utility failure, self-test) become timed events at
// the current cursor.

const DEFAULT_CONFIG: RackConfig = {
  loads: [
    { label: "Web 1", powerW: 300, phase: "A" },
    { label: "Web 2", powerW: 300, phase: "B" },
    { label: "DB 1", powerW: 400, phase: "C" },
    { label: "DB 2", powerW: 400, phase: "A" },
    { label: "App 1", powerW: 300, phase: "B" },
    { label: "App 2", powerW: 300, phase: "C" },
    { label: "Empty 7", powerW: 0, phase: "C" },
    { label: "Empty 8", powerW: 0, phase: "C" },
  ],
  breakerAmps: 16,
  upsChemistry: "vrla",
  upsNameplateWh: 2000,
  upsAgeYears: 1,
  startChargePct: 100,
};

const DEFAULT_ENV: Environment = { roomTempC: 25 };
const NEXT_PHASE: Record<Phase, Phase> = { A: "B", B: "C", C: "A" };
const SPEEDS = [1, 10, 60];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<RackMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<RackConfig>(DEFAULT_CONFIG);
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
    fetchConfigPresets()
      .then(setConfigPresets)
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, environment, durationS, events }),
    [config, environment, durationS, events],
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

  // Current phase of each slot at the cursor, derived from config plus
  // any move-load events that have fired by now.
  const livePhases = useMemo(() => {
    const phases = config.loads.map((ld) => ld.phase);
    const t = state?.t ?? 0;
    for (const e of events) {
      if (e.atS <= t && e.action === "move-load" && e.index != null && e.phase) {
        phases[e.index] = e.phase;
      }
    }
    return phases;
  }, [config, events, state]);

  const liveWatts = useMemo(() => {
    const watts = config.loads.map((ld) => ld.powerW);
    const t = state?.t ?? 0;
    for (const e of events) {
      if (e.atS <= t && e.action === "set-load" && e.index != null && e.value != null) {
        watts[e.index] = e.value;
      }
    }
    return watts;
  }, [config, events, state]);

  const addEvent = (ev: Omit<SimEvent, "atS">) => {
    setEvents((evs) => [...evs, { atS: state?.t ?? 0, ...ev }]);
  };

  const cycleLoad = (index: number) => {
    // Direct config edit: instant, re-simulates from t=0. The guided
    // scenarios show the same thing as timed move-load events.
    const loads = config.loads.map((ld, i) =>
      i === index ? { ...ld, phase: NEXT_PHASE[ld.phase] } : ld,
    );
    setConfig({ ...config, loads });
  };

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setEnvironment(g.scenario.environment);
    setEvents(g.scenario.events);
    setDurationS(g.scenario.durationS);
    setCursor(0);
    setRunning(true);
  };

  const reset = () => {
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
        <h1>Rack PDU &amp; UPS</h1>
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
            ? `t+${state.t}s · ${
                !state.rackPowered
                  ? "DARK"
                  : state.onBattery
                    ? "ON BATTERY"
                    : "on utility"
              } · ${state.pduInputW.toFixed(0)} W`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Three phases, one breaker rule, and a battery that fades</h2>
        <p>
          The power layer under every rack: assign servers to phase feeds
          and balance them, respect the 80% continuous-load rule or watch a
          breaker enforce it, and fail the utility to learn whether the UPS
          front panel's runtime promise survives contact with a battery
          that has quietly aged. Every constant is sourced or honestly
          marked as an estimate.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — build panel + guided scenarios */}
        <div className="thermal-col">
          <ConfigPanel
            config={config}
            presets={configPresets}
            validations={result?.validations ?? []}
            onChange={(c) => {
              setConfig(c);
              setActiveScenario(null);
            }}
            onPreset={(p) => {
              setConfig(p.config);
              setEvents([]);
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

        {/* Center — rack + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <RackView
                anatomy={anatomy}
                state={state}
                phases={livePhases}
                labels={config.loads.map((ld) => ld.label)}
                watts={liveWatts}
                selected={regionId}
                onSelect={setRegionId}
                onCycleLoad={cycleLoad}
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
              <button onClick={reset}>Reset</button>
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
            What we don't model: inrush and transfer-time gaps (the ~4 ms a
            line-interactive UPS takes to switch), harmonics and true
            three-phase vector math, PDU metering electronics (~5 W),
            battery internal resistance under load, and depth-of-discharge
            limits. Fade rates and trip curves are estimates — every
            constant carries a source tag in the backend's constants table.
          </div>
        </div>

        {/* Right — meters, UPS, environment, charts */}
        <div className="thermal-col">
          <PhaseMeters state={state} explains={explains} explainOn={explainOn} />
          <UpsPanel
            state={state}
            summary={result?.summary ?? null}
            explains={explains}
            explainOn={explainOn}
            onUtilityFail={() => addEvent({ action: "utility-fail" })}
            onUtilityRestore={() => addEvent({ action: "utility-restore" })}
            onSelfTest={() => addEvent({ action: "self-test" })}
          />
          <div className="an-panel">
            <h2>Environment</h2>
            <label className="field">
              Room temperature {environment.roomTempC} °C
              <input
                type="range" min={15} max={45} value={environment.roomTempC}
                onChange={(e) =>
                  setEnvironment({ roomTempC: +e.target.value })
                }
              />
              <span className="mini">
                Battery ratings assume 25 °C. VRLA ages ~2× per +10 °C.
              </span>
            </label>
          </div>
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
