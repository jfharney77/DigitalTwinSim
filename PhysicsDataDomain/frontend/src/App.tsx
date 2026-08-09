import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchAppliances,
  fetchDatasetPresets,
  fetchExplain,
  fetchScenarios,
  simulate,
} from "./api";
import { CapacityChart } from "./components/CapacityChart";
import { DatasetPanel } from "./components/DatasetPanel";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { PipelineView } from "./components/PipelineView";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  Appliance,
  ApplianceId,
  Dataset,
  DatasetPreset,
  Explain,
  GuidedScenario,
  PipelineMap,
  Scenario,
  Schedule,
  SimEvent,
  SimResponse,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Mid-run attacks (encrypt the source, start
// ransomware) become timed events at the current cursor day.

const DEFAULT_DATASET: Dataset = { fullTb: 50, dailyChangePct: 1, entropyPct: 30 };
const DEFAULT_SCHEDULE: Schedule = { retentionDays: 30 };

const SPEEDS = [1, 4, 15];
const ALARM_FLOOR = 85; // mirrors entropy_alarm_floor_pct for the chart line

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<PipelineMap | null>(null);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [presets, setPresets] = useState<DatasetPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [applianceId, setApplianceId] = useState<ApplianceId>("dd9910");
  const [dataset, setDataset] = useState<Dataset>(DEFAULT_DATASET);
  const [schedule, setSchedule] = useState<Schedule>(DEFAULT_SCHEDULE);
  const [durationDays, setDurationDays] = useState(90);
  const [events, setEvents] = useState<SimEvent[]>([]);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(4);
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
    Promise.all([fetchAppliances(), fetchDatasetPresets()])
      .then(([ap, pr]) => {
        setAppliances(ap);
        setPresets(pr);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({
      appliance: applianceId,
      dataset,
      schedule,
      durationDays,
      events,
    }),
    [applianceId, dataset, schedule, durationDays, events],
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

  // Playback clock: 500 ms real tick advances `speed` sim days.
  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + speed, trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  const addEventNow = (action: SimEvent["action"], value?: number) => {
    const day = state?.day ?? 0;
    setEvents((evs) => [...evs, { atDay: day, action, value }]);
  };

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setApplianceId(g.scenario.appliance);
    setDataset(g.scenario.dataset);
    setSchedule(g.scenario.schedule);
    setDurationDays(g.scenario.durationDays);
    setEvents(g.scenario.events);
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
  const visibleLog = (result?.log ?? []).filter((e) => e.day <= (state?.day ?? 0));
  const appliance = appliances.find((a) => a.id === applianceId);

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Data Domain · Dedupe Physics</h1>
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
            ? `day ${state.day} · ratio ${state.dedupeRatio.toFixed(1)}× · store ${state.capacityUsedPct.toFixed(0)}% full`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Change rate → chunks → fingerprints → the ratio nobody configured</h2>
        <p>
          Feed a deduplicating backup appliance a dataset and watch its
          headline number emerge: daily change decides what is novel,
          retention multiplies what is logical, and entropy decides whether
          the machinery works at all. Encrypt at the source and the ratio
          collapses to 1:1; let ransomware loose and the entropy of the
          changed data is the alarm that fires while every capacity chart
          still looks fine — the same physics the Cyber Detect twin reads
          from the storage side. Companion to the DellPowerProtect narrative
          twin: that one shows where the vaulted copy lives, this one shows
          why thirty copies fit on one shelf.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — dataset & appliance */}
        <div className="thermal-col">
          <DatasetPanel
            appliances={appliances}
            applianceId={applianceId}
            dataset={dataset}
            schedule={schedule}
            durationDays={durationDays}
            presets={presets}
            validations={result?.validations ?? []}
            onAppliance={(id) => {
              setApplianceId(id);
              setActiveScenario(null);
            }}
            onDataset={setDataset}
            onSchedule={setSchedule}
            onDuration={setDurationDays}
            onPreset={(p) => {
              setApplianceId(p.appliance);
              setDataset(p.dataset);
              setSchedule(p.schedule);
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

        {/* Center — pipeline + capacity chart + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <PipelineView
                anatomy={anatomy}
                state={state}
                selected={regionId}
                onSelect={setRegionId}
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
              <button onClick={reset}>Reset (clear events)</button>
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
              <button
                onClick={() =>
                  state?.hostEncrypted
                    ? addEventNow("disable-host-encryption")
                    : addEventNow("enable-host-encryption")
                }
              >
                {state?.hostEncrypted
                  ? "Disable source encryption"
                  : "Encrypt at the source now"}
              </button>
              <button
                onClick={() =>
                  state?.ransomwareActive
                    ? addEventNow("ransomware-stop")
                    : addEventNow("ransomware-start", 3)
                }
              >
                {state?.ransomwareActive
                  ? "Halt ransomware"
                  : "Unleash ransomware (3%/day)"}
              </button>
            </div>
            {selectedRegion && (
              <div className="mini region-card">
                <strong>{selectedRegion.label}.</strong>{" "}
                {selectedRegion.description}
              </div>
            )}
          </div>
          {appliance && (
            <div className="an-panel">
              <h2>Capacity — the widening gap</h2>
              <CapacityChart
                trace={trace}
                cursor={cursor}
                usableTb={appliance.usableTb}
              />
            </div>
          )}
          <div className="an-panel">
            <h2>Event log</h2>
            <div className="event-log">
              {visibleLog.length === 0 && (
                <div className="mini">No events yet — provoke some.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  day {e.day} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            What we don't model: real hashing or chunk boundaries (novelty
            is closed-form from change rate and entropy), compression-region
            layout, replication, Cloud Tier, or restore paths. Appliance
            capacities follow Dell's data-sheet classes; index RAM, chunk
            size, and every curve are estimates carrying source tags in the
            backend's constants table.
          </div>
        </div>

        {/* Right — instruments & strip charts */}
        <div className="thermal-col">
          <Instruments state={state} explains={explains} explainOn={explainOn} />
          <StripCharts trace={trace} cursor={cursor} alarmThreshold={ALARM_FLOOR} />
        </div>
      </div>
    </div>
  );
}
