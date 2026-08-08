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
import { FleetView } from "./components/FleetView";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  FleetConfig,
  FleetMap,
  GuidedScenario,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

const DEFAULT_CONFIG: FleetConfig = {
  product: "vxrail", sites: 1, nodesPerSite: 8, opsMode: "automated",
  ftt: 1, stacks: 1, catalog: true, committedVms: 150, bufferPct: 30,
  demandCurve: "steady", siteClass: "store", twoNodeHa: true,
  wanReliable: true, testGate: true,
};
const DEFAULT_WORKLOAD: Workload = {
  vmsPerSite: 20, growthPctMonth: 3, vmSizeCapacity: 10,
};

const SPEEDS = [1, 5, 15];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<FleetMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<FleetConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationD, setDurationD] = useState(180);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(5);
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
    () => ({ config, workload, durationD, events }),
    [config, workload, durationD, events],
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

  const nowEvent = (e: Omit<SimEvent, "atD">) => {
    setEvents((evs) => [...evs, { atD: state?.tD ?? 0, ...e }]);
  };

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEvents(g.scenario.events);
    setDurationD(g.scenario.durationD);
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
  const visibleLog = (result?.log ?? []).filter((e) => e.tD <= (state?.tD ?? 0));

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Cloud &amp; Edge Fleets · Operations</h1>
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
            ? `day ${state.tD} · ${state.adminHoursPerMonth.toFixed(0)} h/mo · ${state.availabilityPct.toFixed(2)}%`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Every click has a price, and it's paid in hours</h2>
        <p>
          One fleet engine — sites, nodes, N+1 math, monthly release
          waves, deterministic wear faults, drift — under five management
          philosophies: VxRail's lifecycle bundle, Private Cloud's
          catalog, APEX's consumption economics, NativeEdge's zero-touch
          estates, and Automation Studio's pipelines. The teaching
          instrument is the admin-hours ledger; automation moves its
          needle by an order of magnitude, and everything else in this
          app is a corollary. Tick = one sim-day.
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
              <FleetView
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
                  ×{s}d
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
                <div className="mini">Quiet so far — operate something.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  day {e.tD} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            Admin-hours and rates are estimates (sources in the constants
            table); the order-of-magnitude gaps are the claims. Narrated
            companions: DellVxRail (:5179), DellPrivateCloud (:5198),
            DellNativeEdge (:5187) — this app is their operations bill.
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
            <label className="field">
              VMs per site {workload.vmsPerSite}
              <input
                type="range" min={1} max={200} value={workload.vmsPerSite}
                onChange={(e) =>
                  setWorkload({ ...workload, vmsPerSite: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Growth {workload.growthPctMonth}%/month
              <input
                type="range" min={0} max={20} value={workload.growthPctMonth}
                onChange={(e) =>
                  setWorkload({ ...workload, growthPctMonth: +e.target.value })
                }
              />
            </label>
          </div>
          <div className="an-panel">
            <h2>Operate</h2>
            <div className="btnrow">
              <button onClick={() => nowEvent({ action: "node-fault" })}>
                Fault a node
              </button>
              <button onClick={() => nowEvent({ action: "cluster-update" })}>
                Run an update
              </button>
              {config.product === "nativeedge" && (
                <>
                  <button onClick={() => nowEvent({ action: "deploy-sites", value: 50 })}>
                    Deploy 50 sites
                  </button>
                  <button onClick={() => nowEvent({ action: "wan-outage", value: 7 })}>
                    WAN down 7 days
                  </button>
                </>
              )}
              {config.product === "automationstudio" && (
                <button onClick={() => nowEvent({ action: "bad-change" })}>
                  Push a bad change
                </button>
              )}
              {config.product === "apex" && (
                <button onClick={() => nowEvent({ action: "demand-spike", value: 2 })}>
                  Demand spike ×2
                </button>
              )}
            </div>
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
