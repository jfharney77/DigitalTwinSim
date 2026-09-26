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
import { Timeline, bandsWhere } from "./components/Timeline";
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

// The page intro in three registers, picked by the header's reading level.
// The product paragraph under it is the backend's leveled overview.
function introFor(level: number): string {
  if (level <= 2)
    return (
      "This page is a storage system you can break. Pick a product, set " +
      "how hard it is being used, then press the buttons under Faults & " +
      "events to fail a drive or a controller. Three things are worth " +
      "watching: response time climbing steeply as the system nears its " +
      "limit, how much of the raw disk space you can really use, and how " +
      "long a repair (a rebuild) takes after a drive dies. One step of the " +
      "clock is one hour. The numbers show the shape of the behavior; they " +
      "are not measurements."
    );
  if (level >= 5)
    return (
      "One engine, six personalities: M/M/1-style 1/(1−ρ) knee, raw → " +
      "usable → effective ladder, rebuild rate fixed vs ∝ peers, sync/async " +
      "replication, Exascale pool mix scored by GPU idle. 1 h tick. " +
      "Illustrative constants."
    );
  return (
    "A shared storage engine, parameterized into six Dell platforms. It " +
    "models the 1/(1−ρ) queueing knee (latency rising steeply as " +
    "utilization ρ nears 100%), the raw → usable → effective capacity " +
    "ladder, and rebuild races: PowerStore's controller pair, PowerMax's " +
    "blip-not-outage and speed-of-light replication tax, PowerScale's " +
    "rebuilds that get faster as it grows, ObjectScale's write-once (WORM) " +
    "buckets, PowerFlex where the network is the array, and the Exascale " +
    "meta-sim scored by its GPU-idle gauge. One sim-tick is one hour; " +
    "capacity stories run for sim-months. Numbers are illustrative."
  );
}

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: find-the-knee, controller-failover, snapshot-bill,
// sync-distance, async-rpo, scale-out-rebuild, network-is-the-array,
// immutable-bucket, right-size-the-mix). Returns null when the hash names
// no scenario.
function scenarioIdFromHash(): string | null {
  const m = window.location.hash.match(/#scenario=([a-z0-9_-]+)$/i);
  return m ? m[1] : null;
}

// Keep the address bar pointing at what is loaded without firing hashchange.
function writeHash(hash: string) {
  const url = window.location.pathname + window.location.search + hash;
  window.history.replaceState(null, "", url);
}

// Plain words for a scheduled fault, so the panel can say what is already
// planted rather than leaving the learner to infer it from the log.
const FAULT_WORDS: Record<string, string> = {
  "fail-drive": "a drive failure",
  "fail-controller": "a controller failure",
  "fail-node": "a node failure",
  "add-nodes": "nodes added",
  "write-burst": "a write burst",
  "attempt-delete": "a delete attempt",
};

function faultPhrase(e: SimEvent): string {
  return `${FAULT_WORDS[e.action] ?? e.action} at h+${e.atH}`;
}

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
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  const [config, setConfig] = useState<StorageConfig>(DEFAULT_CONFIG);
  const [workload, setWorkload] = useState<Workload>(DEFAULT_WORKLOAD);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationH, setDurationH] = useState(168);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(6);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [xray, setXray] = useState<"schematic" | "hybrid" | "photo">("schematic");
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();
  // Graded labs (#labs, #lab=<id>): held by id so a level refetch re-levels.
  const [labs, setLabs] = useState<Lab[]>([]);
  const [labsOpen, setLabsOpen] = useState(() => labFromHash().open);
  const [activeLabId, setActiveLabId] = useState<string | null>(() => labFromHash().id);
  const activeLab = labs.find((l) => l.id === activeLabId) ?? null;
  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);
  const activeScenario = scenarios.find((g) => g.id === activeScenarioId) ?? null;
  const setActiveScenario = (g: GuidedScenario | null) => {
    setActiveScenarioId(g ? g.id : null);
    // Leaving a guided scenario inside lab mode keeps the lab's deep link.
    const labHash = labFromHash();
    const rest = labHash.open ? (labHash.id ? `#lab=${labHash.id}` : "#labs") : "";
    writeHash(g ? `#scenario=${g.id}` : rest);
  };

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

  // A fault injected near the end of the run extends the run, so the
  // consequence (a rebuild completing, say) is always on the trace.
  const TAIL_H = 24;
  const MAX_DURATION_H = 2160;
  const nowEvent = (e: Omit<SimEvent, "atH">) => {
    const atH = state?.tH ?? 0;
    setEvents((evs) => [...evs, { atH, ...e }]);
    if (atH + TAIL_H > durationH && durationH < MAX_DURATION_H) {
      setDurationH(Math.min(MAX_DURATION_H, atH + TAIL_H));
      setRunning(true);
    }
  };
  const runIsFull = (state?.tH ?? 0) >= MAX_DURATION_H;

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
    setWorkload(g.scenario.workload);
    setEvents(g.scenario.events);
    setDurationH(g.scenario.durationH);
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
    setEvents(lab.start.events);
    setDurationH(lab.start.durationH);
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

  // Reset rewinds. Inside a guided scenario it reloads that scenario, planted
  // faults included, so the narration still describes what plays; outside
  // one it clears the faults the learner injected.
  const coldStart = () => {
    if (activeScenario) {
      applyGuided(activeScenario);
      return;
    }
    setEvents([]);
    setCursor(0);
    setRunning(true);
  };

  const productMedia = media[config.product];
  const underlay = productMedia?.underlay ?? null;
  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.tH <= (state?.tH ?? 0));
  const scaleOut = ["powerscale", "objectscale", "powerflex", "exascale"].includes(config.product);

  const pins = (result?.log ?? []).map((e) => ({
    i: e.tH,
    severity: e.severity,
    message: e.message,
  }));
  const bands = [
    ...bandsWhere(trace, (s) => s.rebuilding, "#e8c33d", "rebuild running"),
    ...bandsWhere(trace, (s) => s.exposure, "#c8281e", "exposure window"),
    ...bandsWhere(trace, (s) => s.saturated, "#e07b28", "saturated"),
  ];

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
            ? `h+${state.tH} · ${state.latencyMs.toFixed(2)} ms · ${state.usedPct.toFixed(0)}% full`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>One knee, six architectures</h2>
        <p>{introFor(level)}</p>
        {anatomy && <p className="hero-product">{anatomy.overview}</p>}
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
            onSelect={(p) =>
              setConfig({ ...config, product: p as StorageConfig["product"] })
            }
          />
          <BuildPanel
            config={config}
            presets={configPresets}
            validations={result?.validations ?? []}
            onChange={(c) => setConfig(c)}
            // Several scenarios ask the learner to swap the preset and compare,
            // so the scenario card and its planted events stay; Reset restores
            // the scenario's own build.
            onPreset={(p) => setConfig(p.config)}
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
          </div>
        </div>

        <div className="thermal-col thermal-center">
          {activeScenario && (
            <div className="an-panel scenario-card">
              <h2>{activeScenario.title}</h2>
              <div className="mini scenario-narration">
                {activeScenario.narration.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
                <p className="scenario-question">{activeScenario.question}</p>
              </div>
              <div className="btnrow">
                <button onClick={coldStart}>Replay scenario</button>
                <button
                  onClick={() => {
                    setActiveScenario(null);
                    setEvents([]);
                  }}
                >
                  Leave scenario
                </button>
              </div>
            </div>
          )}
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (<>
              <ProductView
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
                  ×{s}h
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
            {runIsFull && (
              <div className="mini">
                The run is at its 90-day limit. Press Reset to inject more faults.
              </div>
            )}
            {events.length > 0 && (
              <div className="mini">
                Already scheduled: {events.map(faultPhrase).join(", ")}. A preset
                swap keeps these, so the same fault replays on the new build —
                no button press needed. Clear them if you would rather break
                something yourself.
                <div className="btnrow" style={{ marginTop: 6 }}>
                  <button
                    onClick={() => {
                      setEvents([]);
                      setCursor(0);
                    }}
                  >
                    Clear scheduled faults
                  </button>
                </div>
              </div>
            )}
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
