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
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { ProductView } from "./components/ProductView";
import { StripCharts } from "./components/StripCharts";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  ProductMap,
  Scenario,
  SimEvent,
  SimResponse,
  StorageConfig,
  Workload,
  WorkloadPreset,
} from "./types";

const DEFAULT_CONFIG: StorageConfig = {
  product: "powerstore", units: 2, drivesPerUnit: 12, driveTb: 15.36,
  driveClass: "nvme", protection: "raid6", nicGbps: 25, srdf: "off",
  distanceKm: 0, smallObjects: false, immutable: false,
  lightningUnits: 0, fileUnits: 0, objectUnits: 0, blockUnits: 0,
};
const DEFAULT_WORKLOAD: Workload = {
  iopsDemandK: 300, blockKb: 8, readPct: 70, sequentialPct: 5,
  workingSetFitPct: 80, ingestTbDay: 1, snapshotsPerDay: 0,
  reductionRatio: 3,
};

const SPEEDS = [1, 6, 24];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<ProductMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<StorageConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationH, setDurationH] = useState(168);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(6);
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
  const scaleOut = ["powerscale", "objectscale", "powerflex", "exascale"].includes(config.product);

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Storage Platforms · Capacity &amp; Performance</h1>
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
            ? `h+${state.tH} · ${state.latencyMs.toFixed(2)} ms · ${state.usedPct.toFixed(0)}% full`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>One knee, six architectures</h2>
        <p>
          A shared storage engine — the 1/(1−ρ) queueing knee, the raw →
          usable → effective capacity ladder, rebuild races and their
          exposure windows — parameterized into six Dell platforms:
          PowerStore's controller pair, PowerMax's blip-not-outage and
          speed-of-light replication tax, PowerScale's rebuilds that get
          faster as it grows, ObjectScale's WORM buckets, PowerFlex where
          the network is the array, and the Exascale meta-sim whose only
          real score is the GPU-idle gauge. One sim-tick = one hour;
          capacity stories run for sim-months.
        </p>
      </div>

      <div className="thermal-grid">
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({ ...config, product: p as StorageConfig["product"] })
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
              <ProductView
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
                <div className="mini">No events yet — break something.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  h+{e.tH} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            Legible, not benchmark-accurate — the knee's shape, the
            capacity ladder, and the rebuild race are the lessons.
            Narrated companions: DellPowerStore (:5175), DellPowerMax
            (:5178), DellPowerScale (:5196), DellPowerFlex (:5189),
            DellExascale (:5184). The GPU-idle gauge is PhysicsCompute's
            data-feed slider, seen from the supply side.
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
              IOPS demand {workload.iopsDemandK}k
              <input
                type="range" min={0} max={4000} step={20}
                value={workload.iopsDemandK}
                onChange={(e) =>
                  setWorkload({ ...workload, iopsDemandK: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Read {workload.readPct}%
              <input
                type="range" min={0} max={100} value={workload.readPct}
                onChange={(e) =>
                  setWorkload({ ...workload, readPct: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Working set in cache {workload.workingSetFitPct}%
              <input
                type="range" min={0} max={100} value={workload.workingSetFitPct}
                onChange={(e) =>
                  setWorkload({ ...workload, workingSetFitPct: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Ingest {workload.ingestTbDay} TB/day
              <input
                type="range" min={0} max={100} step={1}
                value={workload.ingestTbDay}
                onChange={(e) =>
                  setWorkload({ ...workload, ingestTbDay: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Snapshots {workload.snapshotsPerDay}/day
              <input
                type="range" min={0} max={48} value={workload.snapshotsPerDay}
                onChange={(e) =>
                  setWorkload({ ...workload, snapshotsPerDay: +e.target.value })
                }
              />
            </label>
          </div>
          <div className="an-panel">
            <h2>Faults &amp; events</h2>
            <div className="btnrow">
              <button onClick={() => nowEvent({ action: "fail-drive" })}>
                Fail a drive
              </button>
              {!scaleOut && (
                <button onClick={() => nowEvent({ action: "fail-controller" })}>
                  Fail a controller
                </button>
              )}
              {scaleOut && (
                <>
                  <button onClick={() => nowEvent({ action: "fail-node" })}>
                    Fail a node
                  </button>
                  <button onClick={() => nowEvent({ action: "add-nodes", value: 5 })}>
                    Add 5 nodes
                  </button>
                </>
              )}
              <button onClick={() => nowEvent({ action: "write-burst", value: 5 })}>
                Write burst ×5
              </button>
              {config.product === "objectscale" && (
                <button onClick={() => nowEvent({ action: "attempt-delete" })}>
                  Attempt delete
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
