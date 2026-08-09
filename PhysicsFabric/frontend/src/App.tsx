import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchMedia,
  type ProductMediaWire,
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  fetchWorkloadPresets,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { ProductGallery } from "./components/ProductGallery";
import { FabricView } from "./components/FabricView";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  FabricConfig,
  FabricMap,
  GuidedScenario,
  Pattern,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

const DEFAULT_CONFIG: FabricConfig = {
  product: "sn6000", spines: 4, leaves: 8, endpointsPerLeaf: 16,
  downlinkGbps: 400, uplinkGbps: 800, adaptiveRouting: true,
  losslessRoce: true, cpoOptics: false, sharp: false,
  poeAps: 16, poeCameras: 10, poePhones: 31, poeBudgetW: 740,
  psuRedundant: true,
};
const DEFAULT_WORKLOAD: Workload = {
  demandGbps: 16000, pattern: "alltoall", collectivePct: 70,
};

const SPEEDS = [1, 10, 60];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<FabricMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<FabricConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(600);

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
    fetchMedia().then(setMedia).catch(() => {});
    Promise.all([fetchConfigPresets(), fetchWorkloadPresets()])
      .then(([cp, wp]) => {
        setConfigPresets(cp);
        setWorkloadPresets(wp);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, workload, durationS, events }),
    [config, workload, durationS, events],
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
  const dc = config.product !== "e3200";

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Network Fabrics · Flow &amp; Congestion</h1>
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
            ? `t+${state.t}s · worst link ${state.worstLinkPct.toFixed(0)}% · ${state.deliveredGbps.toFixed(0)} Gb/s`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Where the traffic jam forms, and what each fabric does about it</h2>
        <p>
          One flow-level engine, three answers to congestion: the E3200
          campus tree (where the PoE budget binds before the ports do),
          the SN6000 AI Ethernet fabric (hash collisions, adaptive
          routing, PFC losslessness, and an optics power ledger), and the
          Quantum-X800, whose credit-based InfiniBand cannot express a
          drop and whose switches do the collective's math in flight.
          Oversubscription is arithmetic, the queue curve is the storage
          app's knee wearing a different badge, and the worst link — not
          the average — is always the story.
        </p>
      </div>

      <div className="thermal-grid">
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({ ...config, product: p as FabricConfig["product"] })
            }
          />
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
              <FabricView
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
                <div className="mini">No events yet — break a link.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  t+{e.t}s — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            Flow-level fluid model, no packets. Port counts and per-model
            specs are estimates pending Dell spec sheets. Narrated
            companions: DellPowerSwitchSN6000 (:5185), DellQuantumX800
            (:5202), DellPowerSwitchE3200 (:5178). The endpoints band is
            PhysicsCompute's XE9680s; the incast pattern is
            PhysicsStorage's fan-out reads.
          </div>
        </div>

        <div className="thermal-col">
          <div className="an-panel">
            <h2>Traffic</h2>
            <div className="btnrow">
              {workloadPresets.map((w) => (
                <button key={w.id} onClick={() => setWorkload(w.workload)}>
                  {w.name}
                </button>
              ))}
            </div>
            <label className="field">
              Demand {workload.demandGbps} Gb/s
              <input
                type="range" min={0} max={dc ? 80000 : 200} step={dc ? 500 : 4}
                value={workload.demandGbps}
                onChange={(e) =>
                  setWorkload({ ...workload, demandGbps: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Pattern
              <select
                value={workload.pattern}
                onChange={(e) =>
                  setWorkload({ ...workload, pattern: e.target.value as Pattern })
                }
              >
                <option value="uniform">Uniform</option>
                <option value="incast">Incast</option>
                <option value="alltoall">All-to-all</option>
                <option value="elephant">Elephant flows</option>
              </select>
            </label>
            <label className="field">
              Collective share {workload.collectivePct}%
              <input
                type="range" min={0} max={100} value={workload.collectivePct}
                onChange={(e) =>
                  setWorkload({ ...workload, collectivePct: +e.target.value })
                }
              />
            </label>
          </div>
          <div className="an-panel">
            <h2>Faults &amp; toggles</h2>
            <div className="btnrow">
              {dc && (
                <>
                  <button onClick={() => nowEvent({ action: "kill-spine" })}>
                    Kill a spine
                  </button>
                  <button onClick={() => nowEvent({ action: "gray-failure" })}>
                    Gray failure
                  </button>
                </>
              )}
              {config.product === "sn6000" && (
                <button onClick={() => nowEvent({ action: "toggle-adaptive" })}>
                  Toggle adaptive
                </button>
              )}
              {config.product === "x800" && (
                <button onClick={() => nowEvent({ action: "toggle-sharp" })}>
                  Toggle SHARP
                </button>
              )}
              {config.product === "e3200" && (
                <>
                  <button onClick={() => nowEvent({ action: "kill-uplink" })}>
                    Kill an uplink
                  </button>
                  <button onClick={() => nowEvent({ action: "kill-psu" })}>
                    Kill a PSU
                  </button>
                </>
              )}
            </div>
          </div>
          <Instruments
            state={state}
            explains={explains}
            explainOn={explainOn}
            product={config.product}
          />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
