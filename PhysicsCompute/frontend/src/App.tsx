import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { BuildPanel } from "./components/BuildPanel";
import { ProductGallery } from "./components/ProductGallery";
import { Instruments } from "./components/Instruments";
import { ComparePanel } from "./components/ComparePanel";
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { RedfishPanel } from "./components/RedfishPanel";
import { StripCharts } from "./components/StripCharts";
import { Timeline, bandsWhere } from "./components/Timeline";
import { SystemView } from "./components/SystemView";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  Intro,
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

// How many GPUs a build carries — the A/B panel names it, because two
// builds' absolute watts mean nothing until the reader knows the counts.
// XE7745: one per populated riser slot; XE9680: the HGX board's eight;
// XE9712: four per tray (models.py).
function gpuCount(c: SystemConfig): number {
  if (c.product === "xe7745") return c.pcieGpus;
  if (c.product === "xe9680") return 8;
  return c.trays * 4;
}

// Levels 1-2 read the plain string, 3-5 the standard one — the frontend's
// half of the backend's L(...), for labels the API does not carry.
function lv(level: number, plain: string, standard: string): string {
  return level <= 2 ? plain : standard;
}

type Page = "sim" | "idrac";

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: positional, power-plant, starved, air-vs-liquid,
// populate, warm-water, pump-down). Returns null when the hash names no
// scenario.
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
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [intro, setIntro] = useState<Intro | null>(null);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

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

  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
    fetchIntro().then(setIntro).catch((e) => setError(String(e)));
  }, [level]);

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
  const ghostState = ghost
    ? ghost.trace[Math.min(cursor, ghost.trace.length - 1)] ?? null
    : null;

  // Timed events move the workload without moving the sliders, so show the
  // live data feed beside the slider's starting value.
  const feedNow = useMemo(() => {
    let feed = workload.dataFeedPct;
    const t = state?.t ?? 0;
    for (const e of [...events].sort((x, y) => x.atS - y.atS)) {
      if (e.atS > t) break;
      if (e.action === "set-data-feed" && e.value != null) feed = Math.trunc(e.value);
      if (e.action === "set-workload" && e.workload) feed = e.workload.dataFeedPct;
    }
    return feed;
  }, [events, workload.dataFeedPct, state?.t]);

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

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEnvironment(g.scenario.environment);
    setEvents(g.scenario.events);
    setDurationS(g.scenario.durationS);
    // A scenario whose question is read off the A/B panel opens it.
    if (g.comparePresetId) setComparePresetId(g.comparePresetId);
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

  const liquid = config.product === "xe9712";
  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));

  const pins = (result?.log ?? []).map((e) => ({
    i: e.t,
    severity: e.severity,
    message: e.message,
  }));
  const bands = [
    ...bandsWhere(trace, (s) => s.gpusThrottled > 0, "#e07b28", "GPUs throttled"),
    ...bandsWhere(trace, (s) => s.coolantReturnC > 65, "#c8281e", "coolant over the throttle line"),
  ];

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
          {state
            ? `t+${state.t}s · ${(state.dcPowerW / 1000).toFixed(1)} kW · ${state.tokensPerS.toFixed(0)} tok/s`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>{intro?.title ?? "From one hot slot to a hundred-kilowatt rack"}</h2>
        <p className="intro-text">{intro?.text ?? ""}</p>
      </div>

      {page === "sim" && labsOpen && (
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
            <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({ ...config, product: p as SystemConfig["product"] })
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
              A proxy model, not a benchmark.{" "}
              {lv(
                level,
                "Some of the numbers about how the machine is physically put together — how many boards, cards and drawers it holds — are estimates, pending Dell spec sheets (sources in the constants table). Fan and pump wattages are estimates too.",
                "Sled counts, riser rules, and tray figures are estimates pending Dell spec sheets (sources in the constants table). Fan and pump wattages are estimates.",
              )}{" "}
              The XE9680 settles near 7.6 kW with 700 W GPUs and 11 kW with
              1,000 W GPUs here; the XE9680 twin's 9 to 11 kW figures are
              illustrative and sit in the same range. Companions: DellPowerEdgeXE9680
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
                  {key === "dataFeedPct" && feedNow !== workload.dataFeedPct && (
                    <span className="feed-now"> · now {feedNow}% (timed event)</span>
                  )}
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
            {ghost && result && (() => {
              const bPreset = configPresets.find((p) => p.id === comparePresetId);
              const aGpus = gpuCount(config);
              const bGpus = bPreset ? gpuCount(bPreset.config) : 0;
              return (
              <ComparePanel
                aName={`current build — ${aGpus} GPUs`}
                bName={`${bPreset?.name ?? "B"}${bGpus ? ` — ${bGpus} GPUs` : ""}`}
                headline="training throughput"
                unit="tok/s"
                a={trace.map((s) => s.tokensPerS)}
                b={ghost.trace.map((s) => s.tokensPerS)}
                deltas={[
                  { label: "peak tok/s", a: result.summary.peakTokensPerS, b: ghost.summary.peakTokensPerS, unit: "" },
                  { label: "GPU-hours wasted", a: result.summary.gpuHoursWasted, b: ghost.summary.gpuHoursWasted, unit: "h" },
                  {
                    label: lv(level, "peak power drawn by the parts", "peak DC"),
                    a: result.summary.peakDcW, b: ghost.summary.peakDcW, unit: "W",
                  },
                  ...(state && ghostState
                    ? [
                        {
                          label: "cooling overhead now",
                          a: state.coolingOverheadPct, b: ghostState.coolingOverheadPct,
                          unit: lv(level, "% of the computing power", "% of IT"),
                        },
                        {
                          label: "fans + pumps now (whole machine)",
                          a: state.fanPowerW + state.pumpPowerW,
                          b: ghostState.fanPowerW + ghostState.pumpPowerW,
                          unit: "W",
                        },
                      ]
                    : []),
                ]}
                note={
                  lv(
                    level,
                    "Reading these rows: % of the computing power means fans and pumps measured against the electricity that does computing; the power rows count what the machine's parts actually draw, before the wall meter adds conversion loss.",
                    "Reading these rows: % of IT is fans and pumps over the power that does computing; DC is what the parts draw, before conversion loss at the wall.",
                  ) +
                  ` The watt rows are whole-machine totals, so compare them against the GPU counts in the key above (${aGpus} vs ${bGpus || "?"}): the row that normalises is the overhead percentage. ` +
                  "Tokens/s scales with GPU count only — this model does not credit the larger NVLink domain with faster collectives or a bigger shared memory pool, so a 9× here is 9× the silicon, not a scale-up result."
                }
              />
              );
            })()}
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
