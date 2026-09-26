import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { hostedHref } from "@twinsim/twin-ui";
import {
  fetchAnatomy,
  fetchExplain,
  fetchFactoryPresets,
  fetchJobPresets,
  fetchScenarios,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { FactoryView } from "./components/FactoryView";
import { Headline } from "./components/Headline";
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { StripCharts } from "./components/StripCharts";
import { FedControl } from "./components/FedControl";
import { fetchFedRun } from "./fed";
import type { FedRun } from "./fed";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { useLevel } from "./level";
import type {
  Explain,
  FactoryConfig,
  FactoryMap,
  FactoryPreset,
  GuidedScenario,
  JobPreset,
  Scenario,
  SimEvent,
  SimResponse,
  TrainingJob,
} from "./types";

// The trace is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Mid-run interventions (storage loss, weather,
// node failures) become timed events at the current cursor.

const DEFAULT_CONFIG: FactoryConfig = {
  compute: { racks: 8, gpusPerRack: 72, gpuPeakW: 1200 },
  fabric: { type: "quantum-ib", oversubscription: 1.0 },
  data: { storageGbps: 1200 },
  facility: { mwBudget: 1.2, cooling: "liquid" },
  resilience: { checkpointIntervalMin: 60, restartMin: 15, gpuMtbfH: 50000 },
  costs: { usdPerKwh: 0.08, capexMusdPerRack: 3.0, amortizationYears: 4.0 },
};
const DEFAULT_JOB: TrainingJob = {
  tokensPerGpuS: 200,
  dataGbpsPerGpu: 1.5,
  stateGbPerGpu: 10,
  rampH: 24,
};

const SPEEDS = [2, 12, 48]; // sim-hours advanced per second of playback

const TWIN_LINKS: { name: string; dir: string; port: number; note: string }[] = [
  { name: "PowerEdge XE9712", dir: "DellPowerEdgeXE9712", port: 5181, note: "the compute rack — 72 GPUs fuse into one domain" },
  { name: "PowerSwitch SN6000", dir: "DellPowerSwitchSN6000", port: 5185, note: "the Ethernet fabric — losslessness under congestion" },
  { name: "Quantum-X800", dir: "DellQuantumX800", port: 5202, note: "the InfiniBand fabric — lossless by construction" },
  { name: "IR7000", dir: "DellIR7000", port: 5182, note: "the cooling loop — heat in equals heat out" },
  { name: "Exascale", dir: "DellExascale", port: 5184, note: "the data platform — metadata leaves the data path" },
  { name: "GPU", dir: "GPU", port: 5173, note: "one die — the roofline this factory inherits" },
];

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: stand-up, starved-cluster, checkpoint-goldilocks,
// warm-day). Returns null when the hash names no scenario.
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

  const [anatomy, setAnatomy] = useState<FactoryMap | null>(null);
  const [presets, setPresets] = useState<FactoryPreset[]>([]);
  const [jobPresets, setJobPresets] = useState<JobPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-levelled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  const [config, setConfig] = useState<FactoryConfig>(DEFAULT_CONFIG);
  const [job, setJob] = useState<TrainingJob>(DEFAULT_JOB);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationH, setDurationH] = useState(480);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(12);
  const [regionId, setRegionId] = useState<string | null>(null);
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
    writeHash(g ? `#scenario=${g.id}` : rest);
  };

  // Prose-bearing content refetches on level change.
  useEffect(() => {
    Promise.all([fetchAnatomy(), fetchScenarios(), fetchExplain()])
      .then(([an, sc, ex]) => {
        setAnatomy(an);
        setScenarios(sc);
        setExplains(ex);
      })
      .catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    Promise.all([fetchFactoryPresets(), fetchJobPresets()])
      .then(([cp, jp]) => {
        setPresets(cp);
        setJobPresets(jp);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, job, durationH, events }),
    [config, job, durationH, events],
  );

  // Debounced re-simulation on any scenario change.
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

  // "Fed by engines" (docs/COMPOSITION_DESIGN.md §7): the same engine, its
  // inputs computed by the detailed twins and carried in across tested seams.
  // Off by default, and nothing else on the page depends on it.
  const [fedMode, setFedMode] = useState<"aggregate" | "fed">("aggregate");
  const [fed, setFed] = useState<FedRun | null>(null);
  const [fedError, setFedError] = useState<string | null>(null);
  const [fedLoading, setFedLoading] = useState(false);
  useEffect(() => {
    if (fedMode !== "fed" || fed || fedLoading) return;
    setFedLoading(true);
    fetchFedRun()
      .then((run) => {
        setFed(run);
        setFedError(null);
      })
      .catch((e) => {
        setFedError(String(e));
        setFedMode("aggregate");
      })
      .finally(() => setFedLoading(false));
  }, [fedMode, fed, fedLoading]);
  const fedOn = fedMode === "fed" && fed !== null;
  const shownTrace = fedOn ? fed!.trace : trace;
  const shownState = shownTrace[Math.min(cursor, shownTrace.length - 1)] ?? state;

  // Playback clock: 500 ms real tick advances speed/2 sim-hours.
  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + Math.max(1, Math.round(speed / 2)), trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  const addEvent = (action: SimEvent["action"], value?: number) => {
    setEvents((evs) => [...evs, { atH: state?.tH ?? 0, action, value }]);
  };

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
    setJob(g.scenario.job);
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
    setJob(lab.start.job);
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

  const reset = () => {
    setEvents([]);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.tH <= (state?.tH ?? 0));
  const summary = result?.summary ?? null;

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Dell AI Factory — Capstone</h1>
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
            ? `hour ${state.tH} · day ${(state.tH / 24).toFixed(1)} · ${state.phase} · ${state.facilityMw.toFixed(2)} MW`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Stand up an AI factory — every earlier lesson, as a line item</h2>
        {/* Served by the backend so it follows the reading level. */}
        <p>{anatomy?.intro ?? ""}</p>
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

      <Headline
        state={shownState}
        summary={summary}
        explains={explains}
        explainOn={explainOn}
      />

      <div className="thermal-grid">
        {/* Left — sizing + guided scenarios */}
        <div className="thermal-col">
          <BuildPanel
            config={config}
            job={job}
            presets={presets}
            jobPresets={jobPresets}
            validations={result?.validations ?? []}
            onChange={setConfig}
            onJobChange={setJob}
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

        {/* Center — factory diagram + playback + events + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <FactoryView
                anatomy={anatomy}
                state={state}
                racks={config.compute.racks}
                gpusPerRack={config.compute.gpusPerRack}
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
                  ×{s / 2} h
                </button>
              ))}
              <button onClick={reset}>Reset</button>
            </div>
            {/* The cursor is an hour, and everything that asks you to
                read it — scenario questions, the event log's t+NNNh —
                speaks in hours, so the scrubber says which hour it is. */}
            <label className="field scrub-field">
              <span className="mini">
                hour {state?.tH ?? 0} of {Math.max(trace.length - 1, 0)}
                {state ? ` · day ${(state.tH / 24).toFixed(1)} · ${state.phase}` : ""}
              </span>
              <input
                type="range"
                aria-label="timeline scrubber — the hour of the run"
                min={0}
                max={Math.max(trace.length - 1, 0)}
                value={cursor}
                onChange={(e) => {
                  setRunning(false);
                  setCursor(+e.target.value);
                }}
              />
            </label>
            <div className="btnrow">
              <button onClick={() => addEvent("degrade-storage", 25)}>
                Degrade storage to 25%
              </button>
              <button onClick={() => addEvent("restore-storage")}>Restore</button>
              <button onClick={() => addEvent("warm-day", 0.2)}>Warm day</button>
              <button onClick={() => addEvent("end-warm-day")}>Weather breaks</button>
              <button onClick={() => addEvent("fail-gpus", 144)}>
                Fail 2 racks of GPUs
              </button>
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
                <div className="mini">Nothing yet — the factory is being born.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  t+{e.tH}h — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            What we don't model: parallelism strategy, network topology
            below one efficiency number, storage below one bandwidth
            number, batch-size dynamics, spot failures beyond MTBF
            arithmetic, or real prices. Every block is a first-order
            aggregate whose full physics belongs to a per-product sim;
            constants carry sources in the backend table, and the
            estimates say so.
          </div>
          <div className="an-panel">
            <h2>Explore the pieces</h2>
            <div className="mini">
              Each block of this dashboard is a twin in this repo (start
              its app locally to follow a link):
            </div>
            {TWIN_LINKS.map((t) => (
              <div className="mini" key={t.port}>
                <a href={hostedHref(t.dir, t.port)}>{t.name}</a> — {t.note}
              </div>
            ))}
          </div>
        </div>

        {/* Right — charts + run summary */}
        <div className="thermal-col">
          <StripCharts trace={shownTrace} cursor={cursor} />
          <FedControl
            mode={fedMode}
            fed={fed}
            error={fedError}
            loading={fedLoading}
            onMode={setFedMode}
          />
          <div className="an-panel">
            <h2>Run summary — the whole {durationH} h run, not the cursor</h2>
            <div className="mini">
              End-of-run figures, computed from the entire trace. They are
              filled in before you press play, and they do not follow the
              playback cursor — the tiles above do.
            </div>
            <div className="stat"><span>time to first training token</span><span>{summary && summary.timeToFirstTokenH >= 0 ? `${summary.timeToFirstTokenH} h` : "—"}</span></div>
            <div className="stat"><span>tokens produced</span><span>{summary ? `${summary.tokensTotalB.toFixed(1)} B` : "—"}</span></div>
            <div className="stat"><span>avg idle (data)</span><span>{summary ? `${summary.avgIdleDataPct.toFixed(1)}%` : "—"}</span></div>
            <div className="stat"><span>avg PUE</span><span>{summary ? summary.avgPue.toFixed(2) : "—"}</span></div>
            <div className="stat"><span>$ / Mtok (illustrative)</span><span>{summary ? `$${summary.usdPerMtok.toFixed(2)}` : "—"}</span></div>
            <div className="stat"><span>peak facility</span><span>{summary ? `${summary.peakFacilityMw.toFixed(2)} MW` : "—"}</span></div>
            <div className="stat"><span>failures</span><span>{summary ? summary.failures : "—"}</span></div>
            <div className="stat"><span>hours power-capped</span><span>{summary ? summary.powerCappedHours : "—"}</span></div>
            <label className="field" style={{ marginTop: 8 }}>
              Run length · {durationH} h ({(durationH / 24).toFixed(0)} days)
              <input
                type="range" min={120} max={2160} step={24} value={durationH}
                onChange={(e) => setDurationH(+e.target.value)}
              />
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}
