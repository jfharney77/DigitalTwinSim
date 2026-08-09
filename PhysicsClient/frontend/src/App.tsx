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
import { BrandMapPage } from "./components/BrandMapPage";
import { BuildPanel } from "./components/BuildPanel";
import { ProductGallery } from "./components/ProductGallery";
import { DeviceView } from "./components/DeviceView";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  DeviceConfig,
  DeviceMap,
  Environment,
  Explain,
  GuidedScenario,
  PerfMode,
  Scenario,
  SimEvent,
  SimResponse,
  Workload,
  WorkloadPreset,
} from "./types";

// Scenario → pure backend trace → frontend playback clock: the repo's
// pattern. Interactive mid-run actions (unplug, mode change) become
// timed events at the current cursor.

const DEFAULT_CONFIG: DeviceConfig = {
  product: "alienware", formFactor: "laptop", cpuPl1W: 55, gpuTgpW: 140,
  npu: false, ramGb: 32, nvmeCount: 1, batteryWh: 90, batteryHealthPct: 100,
  chargerW: 240, psuCapacityW: 1000,
};
const DEFAULT_WORKLOAD: Workload = { cpuPct: 70, gpuPct: 100, npuPct: 0 };
const DEFAULT_ENV: Environment = {
  ambientC: 22, onLap: false, perfMode: "balanced", pluggedIn: true,
  startChargePct: 100,
};

const SPEEDS = [1, 10, 60];

type Page = "sim" | "brands";

function pageFromHash(): Page {
  return window.location.hash === "#brands" ? "brands" : "sim";
}

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [page, setPage] = useState<Page>(pageFromHash());
  useEffect(() => {
    const onHash = () => setPage(pageFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goto = (p: Page) => {
    window.location.hash = p === "brands" ? "#brands" : "";
  };

  const [anatomy, setAnatomy] = useState<DeviceMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<DeviceConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [environment, setEnvironment] = useState<Environment>(DEFAULT_ENV);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(1200);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(10);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

  // Prose-bearing content refetches on level or product change.
  useEffect(() => {
    Promise.all([
      fetchAnatomy(config.product, config.formFactor),
      fetchScenarios(),
      fetchExplain(),
    ])
      .then(([an, sc, ex]) => {
        setAnatomy(an);
        setScenarios(sc);
        setExplains(ex);
      })
      .catch((e) => setError(String(e)));
  }, [level, config.product, config.formFactor]);

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

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Client Devices · Power &amp; Thermal</h1>
        <nav className="nav">
          <button
            className={page === "sim" ? "active" : ""}
            onClick={() => goto("sim")}
          >
            Simulator
          </button>
          <button
            className={page === "brands" ? "active" : ""}
            onClick={() => goto("brands")}
          >
            Brand map
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
            ? `t+${state.t}s · ${state.poweredOn ? state.plState : "OFF"} · ${state.systemPowerW.toFixed(0)} W · ${state.batteryPct.toFixed(0)}%`
            : "—"}
        </span>
        <LevelControl />
      </header>

      {page === "brands" ? (
        <>
          <div className="an-hero">
            <h2>Dell's client brands, mapped</h2>
            <p>
              The January 2025 rebrand named the machines this simulator
              models: three audience brands with a Base/Plus/Premium
              ladder, Alienware left as itself — and the 2026 course
              corrections, labeled by how well they are sourced. The
              reading-level control above applies here too.
            </p>
          </div>
          <BrandMapPage />
        </>
      ) : (
        <>
      <div className="an-hero">
        <h2>Burst, budget, skin, battery — the client-device physics</h2>
        <p>
          The R760 thermal twin's engine, shrunk to the machines that sit
          on desks and laps: an Alienware laptop or tower and the Pro Max
          Plus workstation with its discrete NPU. Three mechanics servers
          never meet — PL2 burst windows that fade to PL1, one shared
          thermal budget that CPU and GPU fight over, and a skin-
          temperature cap with the final say — plus a battery whose
          runtime is honest division. Every constant is sourced or marked
          as an estimate.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — build panel + guided scenarios */}
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({
                ...config,
                product: p as DeviceConfig["product"],
                ...(p === "promax" ? { formFactor: "laptop" as const } : { npu: false }),
              })
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

        {/* Center — device map + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <DeviceView
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
            What we don't model: per-core DVFS, real game engines (FPS is
            a power proxy), charge chemistry beyond a taper, hinge and
            keyboard hot spots. Companion twins: DellAlienware (:5176)
            walks the same machine's AC power path; DellProMaxPlus
            (:5186) walks the NPU's data path.
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
                ["GPU", "gpuPct"],
                ["NPU", "npuPct"],
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
              Ambient {environment.ambientC} °C
              <input
                type="range" min={10} max={45} value={environment.ambientC}
                onChange={(e) =>
                  setEnvironment({ ...environment, ambientC: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Performance mode
              <select
                value={environment.perfMode}
                onChange={(e) => {
                  const mode = e.target.value as PerfMode;
                  setEnvironment({ ...environment, perfMode: mode });
                }}
              >
                <option value="quiet">Quiet</option>
                <option value="balanced">Balanced</option>
                <option value="performance">Performance</option>
              </select>
            </label>
            {config.formFactor === "laptop" && (
              <div className="btnrow">
                <button onClick={() => nowEvent({ action: "set-on-lap", value: 1 })}>
                  Move on-lap now
                </button>
                <button onClick={() => nowEvent({ action: "set-on-lap", value: 0 })}>
                  Back on desk
                </button>
                <button onClick={() => nowEvent({ action: "unplug" })}>
                  Unplug now
                </button>
                <button onClick={() => nowEvent({ action: "plug-in" })}>
                  Plug in
                </button>
              </div>
            )}
          </div>
          <Instruments state={state} explains={explains} explainOn={explainOn} />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
        </>
      )}
    </div>
  );
}
