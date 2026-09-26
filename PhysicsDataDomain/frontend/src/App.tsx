import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchAppliances,
  fetchDatasetPresets,
  fetchExplain,
  fetchScenarios,
  simulate,
} from "./api";
import { CapacityChart } from "./components/CapacityChart";
import { DatasetPanel } from "./components/DatasetPanel";
import { Instruments } from "./components/Instruments";
import { LabPanel } from "./components/LabPanel";
import { LevelControl } from "./components/LevelControl";
import { PipelineView } from "./components/PipelineView";
import { StripCharts } from "./components/StripCharts";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { useLevel } from "./level";
import type {
  Appliance,
  ApplianceId,
  Dataset,
  DatasetPreset,
  Explain,
  GuidedScenario,
  PipelineMap,
  Scenario,
  Schedule,
  SimEvent,
  SimResponse,
} from "./types";

// The simulation is precomputed by the pure backend engine (the repo's
// scenario→trace pattern); this component owns only the playback clock
// and the scenario state. Mid-run attacks (encrypt the source, start
// ransomware) become timed events at the current cursor day.

const DEFAULT_DATASET: Dataset = { fullTb: 50, dailyChangePct: 1, entropyPct: 30 };
const DEFAULT_SCHEDULE: Schedule = { retentionDays: 30 };

const SPEEDS = [1, 4, 15];
const ALARM_FLOOR = 85; // mirrors entropy_alarm_floor_pct for the chart line

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: thirty-fulls, encrypted-source, entropy-alarm,
// index-knee, retention-dial). Returns null when the hash names no scenario.
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

  const [anatomy, setAnatomy] = useState<PipelineMap | null>(null);
  const [appliances, setAppliances] = useState<Appliance[]>([]);
  const [presets, setPresets] = useState<DatasetPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-leveled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  const [applianceId, setApplianceId] = useState<ApplianceId>("dd9910");
  const [dataset, setDataset] = useState<Dataset>(DEFAULT_DATASET);
  const [schedule, setSchedule] = useState<Schedule>(DEFAULT_SCHEDULE);
  const [durationDays, setDurationDays] = useState(90);
  const [events, setEvents] = useState<SimEvent[]>([]);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(4);
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
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);

  useEffect(() => {
    Promise.all([fetchAppliances(), fetchDatasetPresets()])
      .then(([ap, pr]) => {
        setAppliances(ap);
        setPresets(pr);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({
      appliance: applianceId,
      dataset,
      schedule,
      durationDays,
      events,
    }),
    [applianceId, dataset, schedule, durationDays, events],
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

  // Playback clock: 500 ms real tick advances `speed` sim days.
  useEffect(() => {
    if (!running || trace.length === 0) return;
    const id = window.setInterval(() => {
      setCursor((c) => Math.min(c + speed, trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  const addEventNow = (action: SimEvent["action"], value?: number) => {
    const day = state?.day ?? 0;
    setEvents((evs) => [...evs, { atDay: day, action, value }]);
  };

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setApplianceId(g.scenario.appliance);
    setDataset(g.scenario.dataset);
    setSchedule(g.scenario.schedule);
    setDurationDays(g.scenario.durationDays);
    setEvents(g.scenario.events);
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
    setApplianceId(lab.start.appliance);
    setDataset(lab.start.dataset);
    setSchedule(lab.start.schedule);
    setDurationDays(lab.start.durationDays);
    setEvents(lab.start.events);
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
  const visibleLog = (result?.log ?? []).filter((e) => e.day <= (state?.day ?? 0));
  const appliance = appliances.find((a) => a.id === applianceId);

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Data Domain · Dedupe Physics</h1>
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
            ? `day ${state.day} · ratio ${state.dedupeRatio.toFixed(1)}× · store ${state.capacityUsedPct.toFixed(0)}% full`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        {/* The lead is the backend's leveled anatomy overview (the same
            prose test_leveling.py guards), so the first paragraph on the
            page reads in the register the reader asked for. The
            hard-coded text below is only the pre-fetch fallback. */}
        <h2>
          {level <= 2
            ? "Why thirty backups can fit in the space of about one"
            : "Change rate → chunks → fingerprints → the ratio nobody configured"}
        </h2>
        {anatomy?.overview ? (
          <p className="overview-lead">{anatomy.overview}</p>
        ) : (
          <p className="overview-lead">
            This is the path a backup takes through a Data Domain
            appliance. Only pieces the appliance has never seen before are
            written to disk; everything else is a reference to a piece
            already stored.
          </p>
        )}
        {level <= 2 ? (
          <p>
            Set the dataset and the number of days to keep, press play, and
            watch the storage used each day. The number the appliance is
            judged on — how much smaller the stored data is than the data
            sent to it — is never typed in anywhere. It is whatever the
            data makes it.
          </p>
        ) : (
          <p>
            Feed a deduplicating backup appliance a dataset and watch its
            headline number emerge: daily change decides what is novel,
            retention multiplies what is logical, and entropy decides whether
            the machinery works at all. Encrypt at the source and the ratio
            collapses to 1:1; let ransomware loose and the entropy of the
            changed data is the alarm that fires while every capacity chart
            still looks fine — the same physics the Cyber Detect twin reads
            from the storage side. Companion to the DellPowerProtect narrative
            twin: that one shows where the vaulted copy lives, this one shows
            why thirty copies fit on one shelf.
          </p>
        )}
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
        {/* Left — dataset & appliance */}
        <div className="thermal-col">
          <DatasetPanel
            appliances={appliances}
            applianceId={applianceId}
            dataset={dataset}
            schedule={schedule}
            durationDays={durationDays}
            presets={presets}
            validations={result?.validations ?? []}
            onAppliance={(id) => {
              setApplianceId(id);
              setActiveScenario(null);
            }}
            onDataset={setDataset}
            onSchedule={setSchedule}
            onDuration={setDurationDays}
            onPreset={(p) => {
              setApplianceId(p.appliance);
              setDataset(p.dataset);
              setSchedule(p.schedule);
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

        {/* Center — pipeline + capacity chart + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <PipelineView
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
              <button onClick={reset}>Reset (clear events)</button>
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
            <div className="btnrow">
              <button
                onClick={() =>
                  state?.hostEncrypted
                    ? addEventNow("disable-host-encryption")
                    : addEventNow("enable-host-encryption")
                }
              >
                {state?.hostEncrypted
                  ? "Disable source encryption"
                  : "Encrypt at the source now"}
              </button>
              <button
                onClick={() =>
                  state?.ransomwareActive
                    ? addEventNow("ransomware-stop")
                    : addEventNow("ransomware-start", 3)
                }
              >
                {state?.ransomwareActive
                  ? "Halt ransomware"
                  : "Unleash ransomware (3%/day)"}
              </button>
            </div>
            {selectedRegion && (
              <div className="mini region-card">
                <strong>{selectedRegion.label}.</strong>{" "}
                {selectedRegion.description}
              </div>
            )}
          </div>
          {appliance && (
            <div className="an-panel">
              <h2>Capacity — the widening gap</h2>
              <CapacityChart
                trace={trace}
                cursor={cursor}
                usableTb={appliance.usableTb}
              />
            </div>
          )}
          <div className="an-panel">
            <h2>Event log</h2>
            <div className="event-log">
              {visibleLog.length === 0 && (
                <div className="mini">No events yet — provoke some.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  day {e.day} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            What we don't model: real hashing or chunk boundaries (novelty
            is closed-form from change rate and entropy), compression-region
            layout, replication, Cloud Tier, or restore paths. Appliance ingest
            time covers the appliance only: the clients' time to read and
            fingerprint every logical byte is not modelled, so a real backup
            window is longer. Encrypted files stop churning, and the capacity
            notice is a 20%-over-trend rule of this simulator's own. Appliance
            capacities follow Dell's data-sheet classes; index RAM, chunk
            size, and every curve are estimates carrying source tags in the
            backend's constants table.
          </div>
        </div>

        {/* Right — instruments & strip charts */}
        <div className="thermal-col">
          <Instruments state={state} explains={explains} explainOn={explainOn} />
          <StripCharts trace={trace} cursor={cursor} alarmThreshold={ALARM_FLOOR} />
        </div>
      </div>
    </div>
  );
}
