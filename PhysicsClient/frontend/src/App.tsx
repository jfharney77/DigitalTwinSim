import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LabPanel } from "./components/LabPanel";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import {
  fetchMedia,
  type ProductMediaWire,
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchIntro,
  fetchScenarios,
  fetchWorkloadPresets,
  simulate,
} from "./api";
import { BrandMapPage } from "./components/BrandMapPage";
import { BuildPanel } from "./components/BuildPanel";
import { ProductGallery } from "./components/ProductGallery";
import { DeviceView } from "./components/DeviceView";
import { Instruments } from "./components/Instruments";
import { ComparePanel } from "./components/ComparePanel";
import { LegTable } from "./components/LegTable";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { Timeline, bandsWhere } from "./components/Timeline";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  DeviceConfig,
  DeviceMap,
  Environment,
  Explain,
  GuidedScenario,
  PageIntro,
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
const DEFAULT_WORKLOAD: Workload = { cpuPct: 70, gpuPct: 100, npuPct: 0, inference: false };
const DEFAULT_ENV: Environment = {
  ambientC: 22, onLap: false, perfMode: "balanced", pluggedIn: true,
  startChargePct: 100,
};

const SPEEDS = [1, 10, 60];

// The header's short name for the limit state; Instruments carries the
// long one.
const PL_SHORT: Record<string, string> = {
  "idle": "idle",
  "pl2-boost": "boost window",
  "pl1": "sustained limits",
  "skin-limited": "skin-limited",
  "budget-limited": "budget-limited",
};

function sameWorkload(a: Workload, b: Workload): boolean {
  return a.cpuPct === b.cpuPct && a.gpuPct === b.gpuPct
    && a.npuPct === b.npuPct && a.inference === b.inference;
}

type Page = "sim" | "brands";

function pageFromHash(): Page {
  return window.location.hash === "#brands" ? "brands" : "sim";
}

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios, e.g. benchmark-lie, on-lap, meeting-room). Returns
// null when the hash names no scenario.
function scenarioIdFromHash(): string | null {
  const m = window.location.hash.match(/#scenario=([a-z0-9_-]+)$/i);
  return m ? m[1] : null;
}

// Keep the address bar pointing at what is loaded without firing hashchange.
function writeHash(hash: string) {
  const url = window.location.pathname + window.location.search + hash;
  window.history.replaceState(null, "", url);
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
  const [intro, setIntro] = useState<PageIntro | null>(null);
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

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
  const [xray, setXray] = useState<"schematic" | "hybrid" | "photo">("schematic");
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  const activeScenario = scenarios.find((g) => g.id === activeScenarioId) ?? null;
  // Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;
  const setActiveScenario = (g: GuidedScenario | null) => {
    setActiveScenarioId(g ? g.id : null);
    // Leaving a guided scenario inside lab mode keeps the lab's deep link.
    const labHash = labFromHash();
    const rest = labHash.open ? (labHash.id ? `#lab=${labHash.id}` : "#labs") : "";
    if (page === "sim") writeHash(g ? `#scenario=${g.id}` : rest);
  };
  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
    // The intro falls back to the built-in standard text if it cannot load.
    fetchIntro().then(setIntro).catch(() => setIntro(null));
  }, [level]);

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

  const [comparePresetId, setComparePresetId] = useState("");
  const [ghost, setGhost] = useState<SimResponse | null>(null);
  useEffect(() => {
    const preset = configPresets.find((p) => p.id === comparePresetId);
    if (!preset) {
      setGhost(null);
      return;
    }
    simulate({ ...scenario, config: preset.config })
      .then(setGhost)
      .catch(() => setGhost(null));
  }, [comparePresetId, scenario, configPresets]);

  const trace = result?.trace ?? [];
  const state = trace[cursor] ?? null;

  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + Math.max(1, Math.round(speed / 2)), trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  // The workload in force at the cursor: the dials' setting until a timed
  // set-workload event overrules it. The panel shows this, so it never
  // contradicts the run on screen.
  const scheduled = [...events]
    .filter((e) => e.action === "set-workload" && e.workload && e.atS <= (state?.t ?? 0))
    .sort((a, b) => a.atS - b.atS)
    .pop();
  const liveWorkload: Workload = scheduled?.workload ?? workload;
  const livePreset = workloadPresets.find((w) => sameWorkload(w.workload, liveWorkload));
  // The engine the live workload is named after, regardless of what the
  // build carries — Instruments compares it with the engine that actually
  // ran and says so when they differ.
  const requestedEngine = liveWorkload.inference
    ? liveWorkload.npuPct > 0
      ? "npu"
      : liveWorkload.gpuPct > 0
        ? "gpu"
        : "cpu"
    : null;

  const nowEvent = (e: Omit<SimEvent, "atS">) => {
    setEvents((evs) => [...evs, { atS: state?.t ?? 0, ...e }]);
  };

  // A hand edit replaces whatever a guided scenario had scheduled for the
  // same control; otherwise the timed event silently overrules the dial.
  const dropEvents = (...actions: SimEvent["action"][]) =>
    setEvents((evs) => evs.filter((e) => !actions.includes(e.action)));
  const setWorkloadByHand = (w: Workload) => {
    setWorkload(w);
    dropEvents("set-workload");
  };

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
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

  const productMedia = media[config.product];
  // The underlay is the laptop service photo; it must not sit under the
  // tower's side-view map.
  const underlay =
    config.formFactor === "laptop" ? productMedia?.underlay ?? null : null;
  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  const pins = (result?.log ?? []).map((e) => ({
    i: e.t,
    severity: e.severity,
    message: e.message,
  }));
  const bands = [
    ...bandsWhere(trace, (s) => s.cpuThrottling || s.gpuThrottling, "#e07b28", "silicon throttling"),
    ...bandsWhere(trace, (s) => s.plState === "skin-limited", "#c8281e", "skin-limited"),
    ...bandsWhere(trace, (s) => s.plState === "pl2-boost", "#2596be", "PL2 boost window"),
  ];

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
          {page === "sim" && (
            <button
              className={labsOpen ? "active nav-labs" : "nav-labs"}
              onClick={() => {
                setLabsOpen(!labsOpen);
                writeHash(labsOpen ? "" : activeLabId ? `#lab=${activeLabId}` : "#labs");
              }}
            >
              Labs
            </button>
          )}
        </nav>
        <span className="sub">
          {page !== "sim" ? "" : state
            ? `t+${state.t}s · ${state.poweredOn ? PL_SHORT[state.plState] ?? state.plState : "OFF"} · ${state.systemPowerW.toFixed(0)} W · ${state.batteryPct.toFixed(0)}%`
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
        <h2>{intro?.heading ?? "Burst, budget, skin, battery — the client-device physics"}</h2>
        <p>
          {intro?.text ??
            "An Alienware laptop or tower and the Pro Max Plus workstation with its discrete NPU. A load step opens a burst window (the CPU at its short-term limit PL2, the GPU above its total graphics power TGP) that fades to the sustained limits; CPU and GPU share one thermal budget; a skin-temperature cap has the final say; battery runtime is watt-hours over watts. Every constant is sourced or marked as an estimate."}
        </p>
        {intro && intro.terms.length > 0 && (
          <details className="mini intro-terms" open={level <= 2}>
            <summary>What the instrument labels mean</summary>
            <dl>
              {intro.terms.map((t) => (
                <div key={t.term}>
                  <dt>{t.term}</dt>
                  <dd>{t.meaning}</dd>
                </div>
              ))}
            </dl>
          </details>
        )}
      </div>

      {activeScenario && (
        <div className="an-panel scenario-banner">
          <h2>{activeScenario.title}</h2>
          <div className="mini scenario-narration">
            {activeScenario.narration.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
            <p className="scenario-question">{activeScenario.question}</p>
          </div>
        </div>
      )}

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
            onChange={(c) => {
              if (c.chargerW !== config.chargerW) dropEvents("set-charger");
              setConfig(c);
            }}
            onPreset={(p) => {
              setConfig(p.config);
              setEvents([]);
              setActiveScenario(null);
              setComparePresetId(p.comparePresetId ?? "");
            }}
          />
          <div className="an-panel">
            <h2>Compare (A/B)</h2>
            <select
              value={comparePresetId}
              onChange={(e) => setComparePresetId(e.target.value)}
              style={{ width: "100%" }}
            >
              <option value="">— off —</option>
              {configPresets.map((p) => (
                <option key={p.id} value={p.id}>vs {p.name}</option>
              ))}
            </select>
          </div>
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
          </div>
        </div>

        {/* Center — device map + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (<>
              <DeviceView
                anatomy={anatomy}
                state={state}
                selected={regionId}
                onSelect={setRegionId}
                underlay={underlay}
                xray={underlay ? xray : "schematic"}
              />
              {underlay && (
                <div className="btnrow xray-row">
                  {(["schematic", "hybrid", "photo"] as const).map((m) => (
                    <button
                      key={m}
                      className={xray === m ? "active" : ""}
                      onClick={() => setXray(m)}
                    >
                      {m === "schematic" ? "Schematic" : m === "hybrid" ? "X-ray" : "Photo"}
                    </button>
                  ))}
                  {xray !== "schematic" && productMedia?.caption && (
                    <span className="mini xray-caption">
                      {productMedia.caption} <em>({productMedia.credit})</em>
                    </span>
                  )}
                </div>
              )}
            </>)}
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
              <Timeline
                length={trace.length}
                cursor={cursor}
                onScrub={(i) => {
                  setRunning(false);
                  setCursor(i);
                }}
                pins={pins}
                bands={bands}
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
            <div className="btnrow workload-presets">
              {workloadPresets.map((w) => (
                <button
                  key={w.id}
                  className={livePreset?.id === w.id ? "active" : ""}
                  onClick={() => setWorkloadByHand(w.workload)}
                >
                  {w.name}
                </button>
              ))}
            </div>
            {scheduled && (
              <div className="mini workload-scheduled">
                The scenario set this workload at t+{scheduled.atS}s
                {livePreset ? `: ${livePreset.name}` : ""}. Moving a dial
                replaces the scenario's schedule.
              </div>
            )}
            {(
              [
                ["CPU", "cpuPct"],
                ["GPU", "gpuPct"],
                ["NPU", "npuPct"],
              ] as const
            ).map(([label, key]) => (
              <label key={key} className="field">
                {label} {liveWorkload[key]}%
                <input
                  type="range" min={0} max={100} value={liveWorkload[key]}
                  onChange={(e) =>
                    setWorkloadByHand({ ...liveWorkload, [key]: +e.target.value })
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
                onChange={(e) => {
                  setEnvironment({ ...environment, ambientC: +e.target.value });
                  dropEvents("set-ambient");
                }}
              />
            </label>
            <label className="field">
              Performance mode
              <select
                value={environment.perfMode}
                onChange={(e) => {
                  const mode = e.target.value as PerfMode;
                  setEnvironment({ ...environment, perfMode: mode });
                  dropEvents("set-mode");
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
          <Instruments
            state={state}
            explains={explains}
            explainOn={explainOn}
            hasBattery={config.formFactor === "laptop"}
            requestedEngine={requestedEngine}
          />
          <LegTable scenario={scenario} trace={trace} cursorT={state?.t ?? 0} />
          {ghost && result && (
            <ComparePanel
              aName="current build"
              bName={configPresets.find((p) => p.id === comparePresetId)?.name ?? "B"}
              headline="system power"
              unit="W"
              a={trace.map((s) => s.systemPowerW)}
              b={ghost.trace.map((s) => s.systemPowerW)}
              deltas={[
                { label: "peak system W", a: result.summary.peakSystemW, b: ghost.summary.peakSystemW, unit: "W" },
                { label: "FPS at min 15", a: result.summary.fpsMinute15, b: ghost.summary.fpsMinute15, unit: "" },
                { label: "throttle seconds", a: result.summary.throttleSeconds, b: ghost.summary.throttleSeconds, unit: "s" },
              ]}
            />
          )}
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
        </>
      )}
    </div>
  );
}
