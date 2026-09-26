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
import { FabricView } from "./components/FabricView";
import { Instruments } from "./components/Instruments";
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { Timeline, bandsWhere } from "./components/Timeline";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
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

// The config preset each product starts from when picked.
const PRODUCT_PRESET: Record<FabricConfig["product"], string> = {
  e3200: "campus",
  sn6000: "sn6000-adaptive",
  x800: "x800",
};

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: wire-a-floor, uplink-down, hash-collision,
// lossless-vs-drop, ib-vs-ethernet, sharp, gray-failure). Returns null
// when the hash names no scenario.
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

  const [anatomy, setAnatomy] = useState<FabricMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [workloadPresets, setWorkloadPresets] = useState<WorkloadPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);
  const activeScenario = scenarios.find((g) => g.id === activeScenarioId) ?? null;
  // Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;

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
  const [intro, setIntro] = useState("");

  useEffect(() => {
    fetchIntro().then(setIntro).catch(() => {});
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

  // Lab prose is leveled, so the list refetches with the reading level.
  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);

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

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
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

  const clearScenario = () => {
    setActiveScenarioId(null);
    if (scenarioIdFromHash()) {
      // Leaving a guided scenario inside lab mode keeps the lab's deep link.
      writeHash(labsOpen ? (activeLabId ? `#lab=${activeLabId}` : "#labs") : "");
    }
  };

  // Labs: load a lab's start scenario into the ordinary controls. The start
  // is the naive default — it does not pass — and everything after that is
  // the learner's own work with the same dials every other mode uses.
  const loadLabStart = useCallback((lab: Lab) => {
    setActiveScenarioId(null);
    setConfig(lab.start.config);
    setWorkload(lab.start.workload);
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

  // Switching product loads that product's baseline build: carrying the old
  // one across leaves datacenter features on a campus switch (a validation
  // error), 800 G uplinks the campus menu cannot show, and a demand the
  // traffic slider cannot reach.
  // Campus demand is tens of Gb/s and fabric demand tens of Tb/s; crossing
  // between them swaps in the other side's default traffic.
  const matchWorkload = (p: FabricConfig["product"]) => {
    if ((p === "e3200") === (config.product === "e3200")) return;
    const w = workloadPresets.find(
      (x) => x.id === (p === "e3200" ? "campus-day" : "allreduce"),
    );
    if (w) setWorkload(w.workload);
  };

  const switchProduct = (p: FabricConfig["product"]) => {
    if (p === config.product) return;
    const preset = configPresets.find((c) => c.id === PRODUCT_PRESET[p]);
    setConfig(preset ? preset.config : { ...config, product: p });
    matchWorkload(p);
    setEvents([]);
    clearScenario();
  };

  const coldStart = () => {
    setEvents([]);
    clearScenario();
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));
  const dc = config.product !== "e3200";

  const pins = (result?.log ?? []).map((e) => ({
    i: e.t,
    severity: e.severity,
    message: e.message,
  }));
  // FCT just before the gray failure started, so the instrument can show the
  // before-and-after side by side instead of asking the reader to remember it.
  const grayFrom = trace.findIndex((s) => s.goodputPenaltyPct > 0);
  const baselineFctMs = grayFrom > 0 ? trace[grayFrom - 1].fctMs : null;
  const bands = [
    ...bandsWhere(trace, (s) => s.worstLinkPct > 90, "#e07b28", "worst link past the knee"),
    ...bandsWhere(trace, (s) => s.goodputPenaltyPct > 0, "#8b6cc9", "gray failure active"),
  ];

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
          <button
            className={labsOpen ? "active nav-labs" : "nav-labs"}
            onClick={() => {
              setLabsOpen(!labsOpen);
              writeHash(labsOpen ? "" : activeLabId ? `#lab=${activeLabId}` : "#labs");
            }}
          >
            Labs
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
          {intro}
        </p>
      </div>

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
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) => switchProduct(p as FabricConfig["product"])}
          />
          <BuildPanel
            config={config}
            presets={configPresets}
            validations={result?.validations ?? []}
            onChange={(c) =>
              c.product !== config.product ? switchProduct(c.product) : setConfig(c)
            }
            onPreset={(p) => {
              setConfig(p.config);
              matchWorkload(p.config.product);
              // A preset is a fresh build: the last scenario's faults go too.
              setEvents([]);
              clearScenario();
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
              {workloadPresets
                .filter((w) => (w.id === "campus-day") === !dc)
                .map((w) => (
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
                    Start a gray failure
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
            baselineFctMs={baselineFctMs}
          />
          <StripCharts trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
