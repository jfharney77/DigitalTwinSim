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
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { ThermalChassisView } from "./components/ThermalChassisView";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { fetchConstants } from "./api";
import { useLevel } from "./level";
import type {
  ChassisMap,
  ConfigPreset,
  Environment,
  Explain,
  GuidedScenario,
  ConstantInfo,
  Scenario,
  ServerConfig,
  SimEvent,
  SimResponse,
  SimState,
  Workload,
  WorkloadPreset,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Any change re-requests the trace; interactive
// mid-run actions (fan kills) become timed events at the current cursor.

const DEFAULT_CONFIG: ServerConfig = {
  sockets: 2, cpuTdpW: 250, heatsink: "high-performance", fanKit: "standard",
  dimms: 16, chassis: "24x2.5", drives: 8, gpusDoubleWide: 0,
  accelsSingleWide: 0, ioCardW: 25, psuCount: 2, psuCapacityW: 1400,
  redundancy: "1+1",
};
const DEFAULT_WORKLOAD: Workload = { cpuPct: 60, memPct: 75, storagePct: 70, gpuPct: 0 };
const DEFAULT_ENV: Environment = {
  inletC: 22, altitudeM: 0, recirculationPct: 0, blockedIntakePct: 0,
};

const SPEEDS = [1, 10, 60];

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios, e.g. idle-to-full, kill-a-fan, altitude). Returns
// null when the hash names no scenario.
function scenarioIdFromHash(): string | null {
  const m = window.location.hash.match(/#scenario=([a-z0-9_-]+)$/i);
  return m ? m[1] : null;
}

// Keep the address bar pointing at what is loaded without firing hashchange.
// Shown only until the leveled overview arrives from the backend.
// Shown only until the leveled honesty note arrives from the backend.
const LIMITATIONS_FALLBACK =
  "What we don't model: airflow detail inside the chassis, per-core power " +
  "management, voltage-regulator losses, humidity, acoustics, fan-curve " +
  "and dead-rotor effects, and temperature-dependent CPU leakage.";

const INTRO_FALLBACK =
  "Build a PowerEdge R760, give it work, and watch the chain: work uses " +
  "electricity, electricity turns into heat, heat makes the fans spin, and " +
  "the fans use electricity too.";

// Before/after for a guided scenario's first timed event. The baseline is
// the tick before the event; the second column is the playback cursor.
function BeforeAfter({
  before,
  now,
  eventAt,
  settled,
}: {
  before: SimState;
  now: SimState | null;
  eventAt: number;
  settled: boolean;
}) {
  const rows: [string, (s: SimState) => number, string, number][] = [
    ["wall power", (s) => s.acPowerW, "W", 0],
    // The numerator of the twin's own identity, wall = DC / efficiency.
    // Without it the DC baseline is unrecoverable once the event fires.
    ["total DC power", (s) => s.dcPowerW, "W", 0],
    ["fan power", (s) => s.fanPowerW, "W", 1],
    ["fan speed", (s) => s.fanRpmPct, "%", 0],
    ["CPU power", (s) => s.cpuPowerW, "W", 0],
    ["CPU temp", (s) => s.cpuTempC, "°C", 1],
    ["exhaust", (s) => s.exhaustC, "°C", 1],
  ];
  return (
    <div className="before-after">
      <table>
        <thead>
          <tr>
            <th></th>
            <th>before (t+{before.t}s)</th>
            <th>{now ? `${settled ? "end of run" : "now"} (t+${now.t}s)` : "after"}</th>
            <th>change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, get, unit, dp]) => {
            const b = get(before);
            const n = now ? get(now) : null;
            const d = n == null ? null : n - b;
            return (
              <tr key={label}>
                <td>{label}</td>
                <td>{b.toFixed(dp)} {unit}</td>
                <td>{n == null ? "—" : `${n.toFixed(dp)} ${unit}`}</td>
                <td>{d == null ? "—" : `${d >= 0 ? "+" : "−"}${Math.abs(d).toFixed(dp)} ${unit}`}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div>
        {now
          ? settled
            ? "The run has finished; the change column is the settled answer. Model estimates, not measurements."
            : "The fans are still hunting for a minute or so after the event; let the run finish for the settled figure."
          : `The before column is the recorded baseline from t+${before.t}s — it does not track the live instruments. The second column fills in when the event fires at t+${eventAt}s.`}
      </div>
    </div>
  );
}

function writeHash(hash: string) {
  const url = window.location.pathname + window.location.search + hash;
  window.history.replaceState(null, "", url);
}

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
  const [constants, setConstants] = useState<Record<string, ConstantInfo> | null>(null);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

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
  // Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;
  const activeScenario = scenarios.find((g) => g.id === activeScenarioId) ?? null;
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
  }, [level]);

  useEffect(() => {
    fetchConstants().then((r) => setConstants(r.constants)).catch(() => setConstants(null));
  }, []);

  useEffect(() => {
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
    // `level` is a dependency because the event log is prose: a level
    // change re-requests the trace so the log arrives re-levelled. The
    // cursor is preserved, as everywhere — the numbers do not change.
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

  // Playback stops at the end of the trace; Run from there replays it.
  useEffect(() => {
    if (running && trace.length > 0 && cursor >= trace.length - 1) setRunning(false);
  }, [running, cursor, trace.length]);

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

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenario(g);
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
    setEvents([]);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const atEnd = trace.length > 0 && cursor >= trace.length - 1;
  // Inlet the room is at on this tick: the slider's start value until a
  // timed set-inlet event has fired.
  const inletEvent = [...events]
    .filter((e) => e.action === "set-inlet" && e.value != null && e.atS <= (state?.t ?? 0))
    .sort((a, b) => a.atS - b.atS)
    .pop();
  const inletNow = inletEvent?.value ?? environment.inletC;
  // Before/after for a guided scenario: the tick before its first timed
  // event against the cursor, so nobody has to write the baseline down.
  const firstEventAt = activeScenario?.scenario.events.length
    ? Math.min(...activeScenario.scenario.events.map((e) => e.atS))
    : null;
  const baseline =
    firstEventAt != null && firstEventAt > 0 ? trace[firstEventAt - 1] ?? null : null;
  const afterEvent = baseline != null && state != null && state.t >= (firstEventAt ?? 0);

  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>R760 Power &amp; Thermal</h1>
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
            ? `t+${state.t}s · ${!state.poweredOn ? "OFF" : atEnd ? "finished" : running ? "running" : "paused"} · ${state.acPowerW.toFixed(0)} W wall`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Configuration → load → power → heat → fan response → feedback</h2>
        <p>
          {anatomy ? anatomy.overview : INTRO_FALLBACK}
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
        {/* Left — build panel */}
        <div className="thermal-col">
          <BuildPanel
            level={level}
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
                {baseline && firstEventAt != null && (
                  <BeforeAfter
                    before={baseline}
                    now={afterEvent ? state : null}
                    eventAt={firstEventAt}
                    settled={atEnd}
                  />
                )}
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
              />
            )}
            <div className="btnrow playback-row">
              <button
                className="primary"
                onClick={() => {
                  if (!running && cursor >= trace.length - 1) setCursor(0);
                  setRunning(!running);
                }}
              >
                {running ? "Pause" : atEnd ? "Replay" : "Run"}
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
            {anatomy?.limitations || LIMITATIONS_FALLBACK}
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
                ["GPU", "gpuPct"],
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
            <h2>Environment</h2>
            <label className="field">
              Inlet {inletNow} °C
              {inletEvent && (
                <span className="mini">
                  {" "}set by the scenario at t+{inletEvent.atS}s; the slider
                  holds the starting {environment.inletC} °C
                </span>
              )}
              <input
                type="range" min={15} max={45} value={environment.inletC}
                onChange={(e) =>
                  setEnvironment({ ...environment, inletC: +e.target.value })
                }
              />
              <span className="mini">
                {level <= 2
                  ? "The industry guideline for how warm a server room may get (ASHRAE class A2): aim for 27 °C or cooler at the intake; 35 °C is the most the server is rated to breathe."
                  : "ASHRAE A2: recommended ≤27 °C · allowable ≤35 °C."}
                {inletNow > 35
                  ? ` ${inletNow} °C is above the allowable limit: a cooling-failure condition, not a design point.`
                  : ""}
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
              Recirculation {environment.recirculationPct}%
              <input
                type="range" min={0} max={100}
                value={environment.recirculationPct}
                onChange={(e) =>
                  setEnvironment({
                    ...environment,
                    recirculationPct: +e.target.value,
                  })
                }
              />
            </label>
            <label className="field">
              Blocked intake {environment.blockedIntakePct}%
              <input
                type="range" min={0} max={100}
                value={environment.blockedIntakePct}
                onChange={(e) =>
                  setEnvironment({
                    ...environment,
                    blockedIntakePct: +e.target.value,
                  })
                }
              />
            </label>
            <div className="btnrow">
              <button
                onClick={() =>
                  setEvents((evs) => [
                    ...evs,
                    { atS: state?.t ?? 0, action: "kill-psu" },
                  ])
                }
              >
                Kill a PSU now
              </button>
            </div>
          </div>
          <Instruments
            level={level}
            state={state}
            explains={explains}
            explainOn={explainOn}
            config={config}
            constants={constants}
          />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
