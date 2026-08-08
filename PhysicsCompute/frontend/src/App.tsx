import { useEffect, useMemo, useRef, useState } from "react";
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
import { RedfishPanel } from "./components/RedfishPanel";
import { StripCharts } from "./components/StripCharts";
import { SystemView } from "./components/SystemView";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  Environment,
  Scenario,
  SimEvent,
  SimResponse,
  SystemConfig,
  SystemMap,
  Workload,
  WorkloadPreset,
} from "./types";

const DEFAULT_CONFIG: SystemConfig = {
  product: "xe9680", cpuTdpW: 350, pcieGpus: 8, pcieGpuTdpW: 450,
  psuCapacityW: 2800, sxmGpuTdpW: 700, nics: 8, trays: 18,
  shelfCapacityKw: 132, manifoldCapacityLpm: 200, coolantSupplyC: 25,
  coolantFlowLpm: 120,
};
const DEFAULT_WORKLOAD: Workload = { gpuPct: 100, cpuPct: 50, dataFeedPct: 100 };
const DEFAULT_ENV: Environment = { inletC: 22 };

const SPEEDS = [1, 10, 60];

type Page = "sim" | "idrac";

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [page, setPage] = useState<Page>(
    window.location.hash === "#idrac" ? "idrac" : "sim",
  );
  useEffect(() => {
    const onHash = () =>
      setPage(window.location.hash === "#idrac" ? "idrac" : "sim");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  const [anatomy, setAnatomy] = useState<SystemMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<SystemConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [environment, setEnvironment] = useState<Environment>(DEFAULT_ENV);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(900);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(10);
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

  const nowEvent = (e: Omit<SimEvent, "atS">) => {
    setEvents((evs) => [...evs, { atS: state?.t ?? 0, ...e }]);
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

  const liquid = config.product === "xe9712";
  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>AI Compute · Power &amp; Thermal</h1>
        <nav className="nav">
          <button
            className={page === "sim" ? "active" : ""}
            onClick={() => (window.location.hash = "")}
          >
            Simulator
          </button>
          <button
            className={page === "idrac" ? "active" : ""}
            onClick={() => (window.location.hash = "#idrac")}
          >
            iDRAC
          </button>
          {page === "sim" && (
            <button
              className={explainOn ? "active" : ""}
              onClick={() => setExplainOn(!explainOn)}
            >
              Explain mode
            </button>
          )}
        </nav>
        <span className="sub">
          {state
            ? `t+${state.t}s · ${(state.dcPowerW / 1000).toFixed(1)} kW · ${state.tokensPerS.toFixed(0)} tok/s`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>From one hot slot to a hundred-kilowatt rack</h2>
        <p>
          Three machines on one engine: the XE7745, where eight identical
          GPUs live in unequal seats; the XE9680, whose eight SXM GPUs
          share one thermal fate and starve together when the data
          pipeline lags; and the XE9712 rack in its IR7000, where the heat
          leaves in water and the arithmetic — liquid + air = DC, ΔT =
          Q/(ṁ·cp) — is enforced to the watt. The iDRAC tab closes the
          loop: the sim's state, served as the Redfish JSON a twin would
          read from hardware.
        </p>
      </div>

      {page === "idrac" ? (
        <div className="thermal-grid">
          <div className="thermal-col" />
          <div className="thermal-col thermal-center">
            <RedfishPanel state={state} product={config.product} />
          </div>
          <div className="thermal-col" />
        </div>
      ) : (
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
                <SystemView
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
              A proxy model, not a benchmark; sled counts, riser rules, and
              tray figures are estimates pending Dell spec sheets (sources
              in the constants table). Companions: DellPowerEdgeXE9680
              (:5201), DellPowerEdgeXE9712 (:5181), DellIR7000 (:5182),
              DellIDRAC (:5177).
            </div>
          </div>

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
                  ["GPU", "gpuPct"],
                  ["CPU", "cpuPct"],
                  ["Data feed", "dataFeedPct"],
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
              <h2>Environment &amp; faults</h2>
              {!liquid && (
                <label className="field">
                  Inlet {environment.inletC} °C
                  <input
                    type="range" min={15} max={45} value={environment.inletC}
                    onChange={(e) =>
                      setEnvironment({ ...environment, inletC: +e.target.value })
                    }
                  />
                </label>
              )}
              <div className="btnrow">
                {liquid ? (
                  <>
                    <button onClick={() => nowEvent({ action: "degrade-pump", value: 0.75 })}>
                      Degrade pump now
                    </button>
                    <button onClick={() => nowEvent({ action: "set-coolant-supply", value: 42 })}>
                      Warm-water event
                    </button>
                    <button onClick={() => nowEvent({ action: "restrict-tray", index: config.trays - 1 })}>
                      Restrict last tray
                    </button>
                  </>
                ) : (
                  <button onClick={() => nowEvent({ action: "kill-psu" })}>
                    Kill a PSU now
                  </button>
                )}
                <button onClick={() => nowEvent({ action: "set-data-feed", value: 30 })}>
                  Starve the GPUs
                </button>
              </div>
            </div>
            <Instruments
              state={state}
              explains={explains}
              explainOn={explainOn}
              liquid={liquid}
            />
            <StripCharts trace={trace} cursor={cursor} liquid={liquid} />
          </div>
        </div>
      )}
    </div>
  );
}
