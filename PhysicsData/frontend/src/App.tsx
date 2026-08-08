import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { DataView } from "./components/DataView";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  DataConfig,
  DataMap,
  Explain,
  GuidedScenario,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
} from "./types";

const DEFAULT_CONFIG: DataConfig = {
  product: "aidataplatform", ingestTbh: 20, processTbh: 6, indexTbh: 15,
  serveTbh: 30, gpuProcessing: false, gpuAnalytics: false, kvOffload: false,
  anomalyK: 3.0, weightCapacity: 40, weightPerformance: 40, weightConfig: 20,
};
const DEFAULT_WORKLOAD: Workload = {
  rawArrivalTbh: 8, gpuReadDemandTbh: 10, inferenceSessionsDemand: 60,
  longContextPct: 30, analyticsScanTbh: 20,
};

const SPEEDS = [1, 12, 48];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<DataMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<DataConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationH, setDurationH] = useState(360);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(12);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  useEffect(() => {
    Promise.all([fetchAnatomy(config.product), fetchScenarios(), fetchExplain()])
      .then(([an, sc, ex]) => {
        setAnatomy(an);
        setScenarios(sc);
        setExplains(ex);
      })
      .catch((e) => setError(String(e)));
  }, [level, config.product]);

  useEffect(() => {
    fetchConfigPresets()
      .then(setConfigPresets)
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, workload, durationH, events }),
    [config, workload, durationH, events],
  );

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

  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + Math.max(1, Math.round(speed / 2)), trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  const nowEvent = (e: Omit<SimEvent, "atH">) => {
    setEvents((evs) => [...evs, { atH: state?.tH ?? 0, ...e }]);
  };

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEvents(g.scenario.events);
    setDurationH(g.scenario.durationH);
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
  const visibleLog = (result?.log ?? []).filter((e) => e.tH <= (state?.tH ?? 0));
  const pipeline = config.product === "aidataplatform";

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Data &amp; Observability</h1>
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
            ? pipeline
              ? `h+${state.tH} · ${state.throughputTbh.toFixed(1)} TB/h · idle ${state.gpuIdleDueToDataPct.toFixed(0)}%`
              : `h+${state.tH} · P ${state.precisionPct.toFixed(0)}% · R ${state.recallPct.toFixed(0)}%`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>The dataset's journey, and the console that watches it</h2>
        <p>
          Two halves of one loop: the AI Data Platform pipeline — where
          throughput is min(stage rates), the bottleneck merely relocates
          when you fix it, and the KV-cache offload trades a 12% token
          tax for 4× the long conversations — and the CloudIQ/AIOps
          console, whose anomaly knob is graded against planted ground
          truth and whose capacity forecast is honestly wrong for exactly
          one window after every change. The GPU-idle gauge closes the
          loop with PhysicsCompute; the gray failure pays off
          PhysicsFabric's silent link.
        </p>
      </div>

      <div className="thermal-grid">
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

        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <DataView
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
                  ×{s}h
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
                <div className="mini">Quiet — plant something.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  h+{e.tH} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            The 6×-class GPU claims are labeled to verify against Dell's
            materials. Companions: DellCloudIQ (:5180) narrates the
            telemetry-to-insight pipeline; PhysicsCompute's data-feed
            slider and PhysicsStorage's Exascale gauge are this app's
            neighbors on both sides. Dashboards are the data layer a
            digital twin binds to — the suite's closing loop.
          </div>
        </div>

        <div className="thermal-col">
          <div className="an-panel">
            <h2>{pipeline ? "Demand" : "Inject (ground truth)"}</h2>
            {pipeline ? (
              <>
                <label className="field">
                  Raw arrival {workload.rawArrivalTbh} TB/h
                  <input
                    type="range" min={0} max={40} value={workload.rawArrivalTbh}
                    onChange={(e) =>
                      setWorkload({ ...workload, rawArrivalTbh: +e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  GPU read demand {workload.gpuReadDemandTbh} TB/h
                  <input
                    type="range" min={0} max={60} value={workload.gpuReadDemandTbh}
                    onChange={(e) =>
                      setWorkload({ ...workload, gpuReadDemandTbh: +e.target.value })
                    }
                  />
                </label>
                <label className="field">
                  Long-context sessions {workload.inferenceSessionsDemand}
                  <input
                    type="range" min={0} max={500} step={10}
                    value={workload.inferenceSessionsDemand}
                    onChange={(e) =>
                      setWorkload({ ...workload, inferenceSessionsDemand: +e.target.value })
                    }
                  />
                </label>
                <div className="btnrow">
                  <button onClick={() => nowEvent({ action: "toggle-gpu-process" })}>
                    Toggle GPU processing
                  </button>
                  <button onClick={() => nowEvent({ action: "toggle-kv" })}>
                    Toggle KV offload
                  </button>
                </div>
              </>
            ) : (
              <div className="btnrow">
                <button onClick={() => nowEvent({ action: "inject-capacity" })}>
                  Plant capacity issue
                </button>
                <button onClick={() => nowEvent({ action: "inject-gray" })}>
                  Plant gray failure
                </button>
                <button onClick={() => nowEvent({ action: "inject-fan-drift" })}>
                  Plant fan drift
                </button>
                <button onClick={() => nowEvent({ action: "demand-change" })}>
                  Double demand
                </button>
                <button onClick={() => nowEvent({ action: "expand-capacity" })}>
                  Expand capacity
                </button>
              </div>
            )}
          </div>
          <Instruments
            state={state}
            explains={explains}
            explainOn={explainOn}
            product={config.product}
          />
          <StripCharts trace={trace} cursor={cursor} product={config.product} />
        </div>
      </div>
    </div>
  );
}
