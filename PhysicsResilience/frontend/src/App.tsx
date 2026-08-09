import { useEffect, useMemo, useRef, useState } from "react";
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
import { ProductGallery } from "./components/ProductGallery";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { ResilienceView } from "./components/ResilienceView";
import { StripCharts } from "./components/StripCharts";
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
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

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

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setEvents(g.scenario.events);
    setDurationH(g.scenario.durationH);
    setCursor(0);
    setRunning(true);
  };

  const clearScript = () => {
    setEvents([]);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.tH <= (state?.tH ?? 0));
  const fz = config.product === "fortzero";

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
        </nav>
        <span className="sub">
          {state
            ? `h+${state.tH} · ${fz ? `${state.reachableAssets} reachable` : `RPO ${state.lastCleanPointAgeH.toFixed(0)} h`}`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Will a copy survive, who will notice, and how fast can you act?</h2>
        <p>
          One timeline engine, four defensive questions: PowerProtect's
          air-gapped vault (which copies survive), Cyber Detect's content
          analysis (which copy to trust, and the false-alarm price of
          knowing sooner), MDR's response clock (blast radius = rate ×
          time-to-contain), and Fort Zero's access graph (what one stolen
          identity can reach). The incident is always an abstract
          corruption rate and a timestamp; scrub the timeline and watch
          the architecture answer.
        </p>
      </div>

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
