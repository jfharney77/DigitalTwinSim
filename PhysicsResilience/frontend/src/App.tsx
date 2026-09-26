import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { warmEngine } from "@twinsim/twin-ui";
import {
  fetchMedia,
  type ProductMediaWire,
  fetchAnatomy,
  fetchConfigPresets,
  fetchExplain,
  fetchScenarios,
  fetchScope,
  simulate,
} from "./api";
import { BuildPanel } from "./components/BuildPanel";
import { LabPanel } from "./components/LabPanel";
import { ProductGallery } from "./components/ProductGallery";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { ResilienceView } from "./components/ResilienceView";
import { StripCharts } from "./components/StripCharts";
import { Timeline, bandsWhere } from "./components/Timeline";
import { fetchLabs, labFromHash } from "./labs";
import type { Lab } from "./labs";
import { useLevel } from "./level";
import type {
  ConfigPreset,
  Explain,
  GuidedScenario,
  ResilienceConfig,
  ResilienceMap,
  Scenario,
  SimEvent,
  SimResponse,
} from "./types";

const DEFAULT_CONFIG: ResilienceConfig = {
  product: "powerprotect", estateTb: 200, changeGbDay: 500,
  backupEveryH: 24, retentionCopies: 14, dedupeRatio: 10,
  vault: true, vaultSyncEveryH: 24, restoreGbps: 1.0,
  detection: false, sensitivity: 5, response: "inhouse",
  noiseAlertsDay: 40, inhouseCapacityDay: 60,
  architecture: "perimeter", assets: 60, grantsPerUser: 3,
  microsegSegments: 1, reviewCadenceDays: 0,
};

const DEFAULT_EVENTS: SimEvent[] = [
  { atH: 240, action: "incident", value: 500 },
  { atH: 280, action: "contain" },
  { atH: 290, action: "attempt-restore" },
];

const SPEEDS = [1, 12, 48];

const EVENT_LABEL: Record<SimEvent["action"], string> = {
  incident: "Corruption (fast)",
  "slow-incident": "Corruption (slow)",
  contain: "Contain",
  "attempt-restore": "Attempt restore",
  compromise: "Identity marked hostile",
  "access-review": "Access review",
};

// Deep link to a guided scenario: /#scenario=<id> (ids from
// GET /api/scenarios: backups-arent-enough, rto-surprise, slow-burn,
// two-am, alert-fatigue, stolen-laptop). Returns null when the hash
// names no scenario.
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

  const [anatomy, setAnatomy] = useState<ResilienceMap | null>(null);
  const [configPresets, setConfigPresets] = useState<ConfigPreset[]>([]);
  const [media, setMedia] = useState<Record<string, ProductMediaWire>>({});
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [scope, setScope] = useState("");
  const [explainOn, setExplainOn] = useState(false);
  // Held by id so a reading-level refetch swaps in the re-leveled narration.
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(null);

  const [config, setConfig] = useState<ResilienceConfig>(DEFAULT_CONFIG);
  const [events, setEvents] = useState<SimEvent[]>(DEFAULT_EVENTS);
  const [durationH, setDurationH] = useState(720);

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

  useEffect(() => {
    fetchLabs().then(setLabs).catch((e) => setError(String(e)));
  }, [level]);

  // Grading runs the engine on a scenario nobody prebaked, so on the hosted
  // static build it needs the in-browser engine. Start that download when the
  // labs open rather than on the first click. A no-op in a normal build.
  useEffect(() => {
    if (labsOpen) warmEngine();
  }, [labsOpen]);

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
    Promise.all([fetchConfigPresets(), fetchScope()])
      .then(([cp, sc]) => {
        setConfigPresets(cp);
        setScope(sc);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, durationH, events }),
    [config, durationH, events],
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

  const applyGuided = useCallback((g: GuidedScenario) => {
    setActiveScenarioId(g.id);
    writeHash(`#scenario=${g.id}`);
    setConfig(g.scenario.config);
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

  // The incident script as an editable list: labs need an event at an exact
  // hour, and the playback cursor is a blunt way to get one.
  const sortedEvents = events
    .map((e, i) => ({ e, i }))
    .sort((a, b) => a.e.atH - b.e.atH || a.i - b.i);
  const moveEvent = (i: number, atH: number) => {
    const h = Math.max(0, Math.min(durationH, Math.round(atH)));
    if (Number.isNaN(h)) return;
    setEvents((evs) => evs.map((e, j) => (j === i ? { ...e, atH: h } : e)));
  };
  const removeEvent = (i: number) => setEvents((evs) => evs.filter((_, j) => j !== i));

  const clearScript = () => {
    setEvents([]);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.tH <= (state?.tH ?? 0));
  const fz = config.product === "fortzero";

  const pins = (result?.log ?? []).map((e) => ({
    i: e.tH,
    severity: e.severity,
    message: e.message,
  }));
  const bands = [
    ...bandsWhere(trace, (s) => s.incidentActive && !s.contained, "#c8281e", "corruption spreading"),
    ...bandsWhere(trace, (s) => s.restoring, "#2596be", "restore running"),
    ...bandsWhere(trace, (s) => s.detected && !s.recovered && !s.restoring, "#e8c33d", "detected, not yet recovered"),
  ];

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>Security &amp; Resilience · Timeline</h1>
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
            ? `h+${state.tH} · ${fz ? `${state.reachableAssets} reachable` : `clean copy ${state.lastCleanPointAgeH.toFixed(0)} h old`}`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Will a copy survive, who will notice, and how fast can you act?</h2>
        {level <= 2 ? (
          <p>
            Something starts damaging a company's data at a set hour and
            spreads at a set speed. That is all this simulator says about
            the incident. Everything else is about the defence, as three
            questions. Does a backup copy survive? Does anyone notice, and
            how soon? How many hours until the systems are back? Pick a
            guided scenario on the left: the run starts on its own, and
            the button reads Pause because of that — press it to stop the
            clock. ×12h moves an hour-by-hour run along faster, and
            dragging the timeline jumps straight to any hour. The four
            product cards below each take one question further.
          </p>
        ) : (
          <p>
            One timeline engine, four defensive questions: PowerProtect's
            air-gapped vault (which copies survive), Cyber Detect's content
            analysis (which copy to trust, and the false-alarm price of
            knowing sooner), MDR's response clock (MDR is managed detection
            and response, an outside team on watch around the clock; blast
            radius, the data corrupted before someone stops the spread, =
            rate × time-to-contain), and Fort Zero's access graph (what one
            stolen identity can reach). The incident is always an abstract
            corruption rate and a timestamp; scrub the timeline and watch
            the architecture answer.
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
        <div className="thermal-col">
          <ProductGallery
            media={media}
            selected={config.product}
            onSelect={(p) =>
              setConfig({ ...config, product: p as ResilienceConfig["product"] })
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
              <ResilienceView
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
              <button onClick={clearScript}>Clear script</button>
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
                <div className="mini">Nothing yet — script an incident.</div>
              )}
              {visibleLog.slice(-12).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  h+{e.tH} — {e.message}
                </div>
              ))}
            </div>
          </div>
          <div className="mini footnote">
            {scope} Narrated companions: DellPowerProtect (:5183),
            DellCyberDetect (:5192), DellFortZero (:5195) — this app runs
            their architectures under a scrubber.
          </div>
        </div>

        <div className="thermal-col">
          <div className="an-panel">
            <h2>Incident script</h2>
            <div className="mini">
              Events land at the playback cursor (h+{state?.tH ?? 0}).
            </div>
            <div className="btnrow">
              {!fz && (
                <>
                  <button onClick={() => nowEvent({ action: "incident", value: 500 })}>
                    Corruption (fast)
                  </button>
                  <button onClick={() => nowEvent({ action: "slow-incident", value: 20 })}>
                    Corruption (slow)
                  </button>
                  <button onClick={() => nowEvent({ action: "contain" })}>
                    Contain
                  </button>
                  <button onClick={() => nowEvent({ action: "attempt-restore" })}>
                    Attempt restore
                  </button>
                </>
              )}
              {fz && (
                <>
                  <button onClick={() => nowEvent({ action: "compromise" })}>
                    Mark identity hostile
                  </button>
                  <button onClick={() => nowEvent({ action: "access-review" })}>
                    Access review
                  </button>
                </>
              )}
            </div>
            <div className="mini" style={{ marginTop: 6 }}>
              {events.length} scripted event{events.length === 1 ? "" : "s"}.
              {events.length > 0 && " Edit an hour to move an event."}
            </div>
            <div className="script-list">
              {sortedEvents.map(({ e, i }) => (
                <div key={i} className="script-row mini">
                  <span className="script-action">
                    {EVENT_LABEL[e.action]}
                    {e.value != null ? ` · ${e.value} GB/h` : ""}
                  </span>
                  <label>
                    h+
                    <input
                      type="number"
                      min={0}
                      max={durationH}
                      value={e.atH}
                      aria-label={`Hour of ${EVENT_LABEL[e.action]}`}
                      onChange={(ev) => moveEvent(i, Number(ev.target.value))}
                    />
                  </label>
                  <button
                    onClick={() => removeEvent(i)}
                    aria-label={`Remove ${EVENT_LABEL[e.action]} at hour ${e.atH}`}
                  >
                    Remove
                  </button>
                </div>
              ))}
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
