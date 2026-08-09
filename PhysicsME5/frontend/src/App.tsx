import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  fetchWorkloadPresets,
  simulate,
} from "./api";
import { ArrayView } from "./components/ArrayView";
import { BuildPanel } from "./components/BuildPanel";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ArrayConfig,
  ArrayMap,
  ConfigPreset,
  Explain,
  GuidedScenario,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Any change re-requests the trace; interactive
// mid-run actions (drive/controller failures) become timed events at the
// current cursor.

const DEFAULT_CONFIG: ArrayConfig = {
  model: "ME5024", driveType: "hdd-10k", driveCount: 24, driveTb: 4,
  raidLevel: "6", spares: 1, controllers: 2, hostInterface: "iSCSI",
};
const DEFAULT_WORKLOAD: Workload = { offeredKiops: 3, readPct: 70, blockKb: 8 };

const SPEEDS = [1, 10, 60];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<ArrayMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<ArrayConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationMin, setDurationMin] = useState(720);
  const [tickMinutes, setTickMinutes] = useState(1);

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
    () => ({ config, workload, durationMin, tickMinutes, events }),
    [config, workload, durationMin, tickMinutes, events],
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

  // Playback clock: 500 ms real tick advances `speed / 2` trace steps.
  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + Math.max(1, Math.round(speed / 2)), trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  const driveClick = useCallback(
    (index: number) => {
      const t = state?.t ?? 0;
      const st = state?.regionStates[`drive-${index}`];
      if (st === "ok" || st === "rebuilding") {
        setEvents((evs) => [...evs, { atMin: t, action: "fail-drive", index }]);
      } else if (st === "failed") {
        setEvents((evs) => [...evs, { atMin: t, action: "replace-drive", index }]);
      }
    },
    [state],
  );

  const controllerClick = useCallback(() => {
    const t = state?.t ?? 0;
    const alive = state?.controllersAlive ?? 2;
    setEvents((evs) => [
      ...evs,
      {
        atMin: t,
        action: alive < config.controllers ? "restore-controller" : "fail-controller",
      },
    ]);
  }, [state, config.controllers]);

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEvents(g.scenario.events);
    setDurationMin(g.scenario.durationMin);
    setTickMinutes(g.scenario.tickMinutes);
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
  const fmtT = (t: number) =>
    t >= 1440 ? `${(t / 1440).toFixed(1)} d` : t >= 60 ? `${(t / 60).toFixed(1)} h` : `${t} min`;

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>PowerVault ME5 · RAID Physics</h1>
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
            ? `t+${fmtT(state.t)} · ${state.online ? (state.degraded ? "DEGRADED" : "online") : "OFFLINE"} · ${state.servedKiops.toFixed(1)}k IOPS`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Drives set the budget · RAID sets the write tax · failures turn time into risk</h2>
        <p>
          Build Dell's entry SAN, load it, and break it. Every host write is
          multiplied by the RAID write penalty before it touches a drive —
          ×2 mirrored, ×4 single-parity, ×6 dual-parity — and every failure
          opens a rebuild window measured in hours or days, during which the
          array is one (or, on RAID 6, two) failures from loss. Classic
          storage physics with nothing else in the way: no dedupe, no
          tiering — that machinery lives in the bigger arrays this sim
          exists to make legible. Constants are estimates and say so.
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

        {/* Center — enclosure + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <ArrayView
                anatomy={anatomy}
                state={state}
                selected={regionId}
                onSelect={setRegionId}
                onDriveClick={driveClick}
                onControllerClick={controllerClick}
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
                <div className="mini">No events yet — fail something.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  t+{fmtT(e.t)} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            What we don't model: caching beyond a flat controller overhead,
            snapshots, thin provisioning, stripe geometry, SAS topology,
            multipathing, and RAID 10's lucky second failures (the model
            takes the unlucky mirror and says so). Drive IOPS, rebuild
            rates, and the controller ceiling are estimates pending
            calibration against Dell's ME5 documentation — every constant
            carries a source tag in the backend's table.
          </div>
        </div>

        {/* Right — workload, run controls, instruments, charts */}
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
              Offered load {workload.offeredKiops} kIOPS
              <input
                type="range" min={0} max={500} step={0.5}
                value={workload.offeredKiops}
                onChange={(e) =>
                  setWorkload({ ...workload, offeredKiops: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Read share {workload.readPct}% (writes {100 - workload.readPct}%)
              <input
                type="range" min={0} max={100} value={workload.readPct}
                onChange={(e) =>
                  setWorkload({ ...workload, readPct: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Block size {workload.blockKb} KB
              <input
                type="range" min={1} max={1024} value={workload.blockKb}
                onChange={(e) =>
                  setWorkload({ ...workload, blockKb: +e.target.value })
                }
              />
            </label>
          </div>
          <div className="an-panel">
            <h2>Run</h2>
            <label className="field">
              Duration {fmtT(durationMin)}
              <input
                type="range" min={60} max={20160} step={60}
                value={durationMin}
                onChange={(e) => setDurationMin(+e.target.value)}
              />
            </label>
            <label className="field">
              Tick {tickMinutes} min
              <input
                type="range" min={1} max={120} value={tickMinutes}
                onChange={(e) => setTickMinutes(+e.target.value)}
              />
              <span className="mini">
                Storage time is long — rebuilds are days. Coarser ticks let
                one run hold a whole rebuild window.
              </span>
            </label>
            <div className="btnrow">
              <button onClick={controllerClick}>
                {state && state.controllersAlive < config.controllers
                  ? "Restore controller"
                  : "Fail a controller now"}
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
