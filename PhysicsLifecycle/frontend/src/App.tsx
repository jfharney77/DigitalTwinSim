import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchMedia,
  type ProductMediaWire,
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { ProductGallery } from "./components/ProductGallery";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { LifecycleView } from "./components/LifecycleView";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  LifecycleConfig,
  LifecycleMap,
  Scenario,
  SimEvent,
  SimResponse,
} from "./types";

const DEFAULT_CONFIG: LifecycleConfig = {
  product: "telecomblocks", sites: 100, deployMode: "blocks",
  extendedTemp: true, spareCapacity: true, remoteRemediation: true,
  subscribersPerSiteK: 20, batteryReplaceable: true, ramSocketed: true,
  chassisRecycled: true, portsModular: true, grid: "average",
  firstOwnerYears: 4, annualKwh: 60,
};

const DEFAULT_EVENTS: SimEvent[] = [
  { atD: 10, action: "deploy-sites", value: 50 },
  { atD: 40, action: "deploy-sites", value: 50 },
];

const SPEEDS = [1, 7, 30];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<LifecycleMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<LifecycleConfig>(DEFAULT_CONFIG);
  const [events, setEvents] = useState<SimEvent[]>(DEFAULT_EVENTS);
  const [durationD, setDurationD] = useState(365);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(7);
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
    fetchConfigPresets()
      .then(setConfigPresets)
      .catch((e) => setError(String(e)));
  }, []);

  // Duration follows the product: rollouts run a year, lifecycles eight.
  useEffect(() => {
    setDurationD(config.product === "circulardesign" ? 2920 : 365);
  }, [config.product]);

  const scenario: Scenario = useMemo(
    () => ({ config, durationD, events }),
    [config, durationD, events],
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
  const telecom = config.product === "telecomblocks";

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Telecom &amp; Sustainability · Lifecycle</h1>
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
            ? telecom
              ? `day ${state.tD} · coverage ${state.coveragePct.toFixed(0)}%`
              : `day ${state.tD} · ${state.carbonPerUsefulYear.toFixed(0)} kg/useful-yr`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Networks built in bundles, laptops judged in decades</h2>
        <p>
          Two lifecycles, one honesty rule. Telecom Infrastructure Blocks
          prices the integration project the bundle replaces (A×B×C
          version combinations always find someone) and lets a heatwave
          separate the extended-temperature fleet from the one that saved
          on the spec sheet. Circular Design makes four design choices —
          screwed or glued, socketed or soldered, modular or integrated,
          recycled or virgin — then accounts eight years of consequences
          into one uncheatable number: carbon per useful-year. Every
          carbon figure is a labeled estimate; Dell's PCF reports are the
          calibration homework.
        </p>
      </div>

      <div className="thermal-grid">
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({ ...config, product: p as LifecycleConfig["product"] })
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
              setEvents(p.config.product === "telecomblocks" ? DEFAULT_EVENTS : []);
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
              <LifecycleView
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
                <div className="mini">Nothing yet.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  day {e.tD} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            All carbon figures are illustrative estimates for education —
            Dell publishes per-product PCF reports, the real calibration
            source. Telecom envelope figures carry verify labels.
            Companions: DellNativeEdge (:5187) — telecom is its most
            extreme fleet; DellCircularDesign/initial_spec.md is the
            narrated-twin spec this half descends from.
          </div>
        </div>

        <div className="thermal-col">
          {telecom && (
            <div className="an-panel">
              <h2>Operate</h2>
              <div className="btnrow">
                <button onClick={() => nowEvent({ action: "deploy-sites", value: 50 })}>
                  Deploy 50 sites
                </button>
                <button onClick={() => nowEvent({ action: "heatwave", value: 48 })}>
                  Heatwave 48 °C
                </button>
                <button onClick={() => nowEvent({ action: "bundle-update" })}>
                  Roll an update
                </button>
              </div>
            </div>
          )}
          <Instruments
            state={state}
            explains={explains}
            explainOn={explainOn}
            telecom={telecom}
          />
          <StripCharts trace={trace} cursor={cursor} telecom={telecom} />
        </div>
      </div>
    </div>
  );
}
