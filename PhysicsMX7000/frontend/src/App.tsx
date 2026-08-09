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
import { ChassisView } from "./components/ChassisView";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ChassisConfig,
  ChassisMap,
  ConfigPreset,
  Environment,
  Explain,
  GuidedScenario,
  Scenario,
  SimEvent,
  SimResponse,
  SledLoad,
  Workload,
  WorkloadPreset,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Interactive mid-run actions (kill a fan, drop a
// feed) become timed events at the current cursor.

const DEFAULT_CONFIG: ChassisConfig = {
  sleds: Array.from({ length: 8 }, () => ({
    kind: "compute" as const, cpuTdpW: 205, dimms: 16, drives: 2, ownerSlot: null,
  })),
  psuCount: 6,
  redundancy: "grid",
  powerCapW: 0,
};
const DEFAULT_LOAD: SledLoad = { cpuPct: 50, memPct: 40, storagePct: 30 };
const DEFAULT_WORKLOAD: Workload = {
  loads: Array.from({ length: 8 }, () => ({ ...DEFAULT_LOAD })),
};
const DEFAULT_ENV: Environment = { inletC: 22 };

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

  const [config, setConfig] = useState<ChassisConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [environment, setEnvironment] = useState<Environment>(DEFAULT_ENV);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(900);
  const [loadSlot, setLoadSlot] = useState(0);

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

  const emptyBays = useMemo(
    () => new Set(config.sleds.flatMap((s, i) => (s.kind === "empty" ? [i] : []))),
    [config],
  );
  const storageBays = useMemo(
    () => new Set(config.sleds.flatMap((s, i) => (s.kind === "storage" ? [i] : []))),
    [config],
  );

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

  const addEvent = (e: Omit<SimEvent, "atS">) => {
    setEvents((evs) => [...evs, { ...e, atS: state?.t ?? 0 }]);
  };

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
  const load = workload.loads[loadSlot] ?? DEFAULT_LOAD;
  const setLoad = (patch: Partial<SledLoad>) => {
    setWorkload({
      loads: workload.loads.map((l, i) => (i === loadSlot ? { ...l, ...patch } : l)),
    });
  };

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>MX7000 Shared Infrastructure</h1>
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
            ? `t+${state.t}s · ${state.poweredOn ? "running" : "DARK"} · ${state.acPowerW.toFixed(0)} W wall`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Eight sleds bring the heat. The chassis brings everything else.</h2>
        <p>
          The PowerEdge MX7000 is a 7U modular chassis: up to eight compute
          or storage sleds sharing nine fans, up to six pooled 3000 W power
          supplies, and two fabrics. Nothing in that list belongs to any
          sled — so one hot neighbor spins the fans for everyone, redundancy
          is a policy about which failure leaves the pool alive, and a
          storage sled follows whichever compute sled owns it. Load the bays
          unevenly, drop an AC feed, reassign the drives, and watch who pays
          for whom. Chassis facts are Dell's; most physics constants are
          labeled estimates.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — build panel + guided scenarios */}
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

        {/* Center — chassis + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <ChassisView
                anatomy={anatomy}
                state={state}
                deadFans={deadFans}
                emptyBays={emptyBays}
                storageBays={storageBays}
                selected={regionId}
                onSelect={setRegionId}
                onToggleFan={toggleFan}
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
            <div className="btnrow">
              <button onClick={() => addEvent({ action: "lose-feed", index: 0 })}>
                Lose feed A now
              </button>
              <button onClick={() => addEvent({ action: "lose-feed", index: 1 })}>
                Lose feed B now
              </button>
              <button onClick={() => addEvent({ action: "kill-psu" })}>
                Kill a PSU now
              </button>
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
            What we don't model: CFD, per-slot airflow steering, fabric
            traffic, sled-level BMCs, acoustics beyond rpm as proxy. Chassis
            facts (8 bays, 9 fans, up to 6× 3000 W PSUs, grid redundancy)
            are from Dell's MX7000 documentation; most physics constants
            are estimates and each carries a source tag in the backend's
            constants table.
          </div>
        </div>

        {/* Right — per-sled workload, environment, instruments, charts */}
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
              Editing sled {loadSlot + 1}
              <input
                type="range" min={0} max={7} value={loadSlot}
                onChange={(e) => setLoadSlot(+e.target.value)}
              />
            </label>
            {(
              [
                ["CPU", "cpuPct"],
                ["Memory", "memPct"],
                ["Storage", "storagePct"],
              ] as const
            ).map(([label, key]) => (
              <label key={key} className="field">
                {label} {load[key]}%
                <input
                  type="range" min={0} max={100} value={load[key]}
                  onChange={(e) => setLoad({ [key]: +e.target.value })}
                />
              </label>
            ))}
            <div className="mini">
              Sled {loadSlot + 1}:{" "}
              {config.sleds[loadSlot]?.kind === "compute"
                ? `compute, ${state ? state.sledPowerW[loadSlot].toFixed(0) : "—"} W`
                : config.sleds[loadSlot]?.kind === "storage"
                  ? `storage — follows sled ${config.sleds[loadSlot]?.ownerSlot ?? "?"}'s storage dial`
                  : "empty bay"}
            </div>
          </div>
          <div className="an-panel">
            <h2>Environment</h2>
            <label className="field">
              Inlet {environment.inletC} °C
              <input
                type="range" min={15} max={45} value={environment.inletC}
                onChange={(e) =>
                  setEnvironment({ ...environment, inletC: +e.target.value })
                }
              />
              <span className="mini">
                ASHRAE A2: recommended ≤27 °C
              </span>
            </label>
            <label className="field">
              Duration {durationS}s
              <input
                type="range" min={120} max={1800} step={60} value={durationS}
                onChange={(e) => setDurationS(+e.target.value)}
              />
            </label>
          </div>
          <Instruments state={state} explains={explains} explainOn={explainOn} />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
