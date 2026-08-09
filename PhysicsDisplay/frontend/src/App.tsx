import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchAnatomy,
  fetchExplain,
  fetchModelPresets,
  fetchScenarios,
  simulate,
} from "./api";
import { Instruments } from "./components/Instruments";
import { LevelControl } from "./components/LevelControl";
import { MonitorView } from "./components/MonitorView";
import { StripChart } from "./components/StripChart";
import { useLevel } from "./level";
import type {
  ContentProfile,
  DisplayConfig,
  Explain,
  GuidedScenario,
  Lifecycle,
  ModelPreset,
  PanelMap,
  Scenario,
  SimEvent,
  SimResponse,
} from "./types";

// The trace is precomputed by the pure backend engine; this component
// owns only the playback clock and the scenario state.

const DEFAULT_CONFIG: DisplayConfig = {
  model: "miniled-32", brightnessPct: 75, content: "mixed",
  localDimming: true, hubLaptopW: 0,
};
const DEFAULT_LIFECYCLE: Lifecycle = {
  hoursPerDay: 8, daysPerYear: 230, serviceYears: 6, gridKgco2PerKwh: 0.4,
};

const CONTENTS: ContentProfile[] = ["dark", "mixed", "bright", "hdr"];
const SPEEDS = [1, 5, 20];

export function App() {
  useEffect(() => {
    document.body.classList.add("dell-body");
  }, []);

  const [anatomy, setAnatomy] = useState<PanelMap | null>(null);
  const [presets, setPresets] = useState<ModelPreset[]>([]);
  const [scenarios, setScenarios] = useState<GuidedScenario[]>([]);
  const [explains, setExplains] = useState<Explain[]>([]);
  const [explainOn, setExplainOn] = useState(false);
  const [activeScenario, setActiveScenario] = useState<GuidedScenario | null>(null);

  const [config, setConfig] = useState<DisplayConfig>(DEFAULT_CONFIG);
  const [lifecycle, setLifecycle] = useState<Lifecycle>(DEFAULT_LIFECYCLE);
  const [events, setEvents] = useState<SimEvent[]>([]);
  const [durationS, setDurationS] = useState(300);

  const [result, setResult] = useState<SimResponse | null>(null);
  const [cursor, setCursor] = useState(0);
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(1);
  const [regionId, setRegionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const level = useLevel();

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
    fetchModelPresets().then(setPresets).catch((e) => setError(String(e)));
  }, []);

  const scenario: Scenario = useMemo(
    () => ({ config, lifecycle, durationS, events }),
    [config, lifecycle, durationS, events],
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
      setCursor((c) => Math.min(c + speed, trace.length - 1));
    }, 500);
    return () => clearInterval(id);
  }, [running, speed, trace.length]);

  // Dimming state at the cursor, derived from the event list.
  const dimmingNow = useMemo(() => {
    let d = config.localDimming;
    const t = state?.t ?? 0;
    for (const e of events) {
      if (e.atS <= t && e.action === "set-dimming" && e.value != null) {
        d = !!e.value;
      }
    }
    return d;
  }, [events, state, config.localDimming]);

  const applyGuided = (g: GuidedScenario) => {
    setActiveScenario(g);
    setConfig(g.scenario.config);
    setLifecycle(g.scenario.lifecycle);
    setEvents(g.scenario.events);
    setDurationS(g.scenario.durationS);
    setCursor(0);
    setRunning(true);
  };

  const reset = () => {
    setEvents([]);
    setActiveScenario(null);
    setCursor(0);
    setRunning(true);
  };

  const addEventNow = (e: Omit<SimEvent, "atS">) => {
    setEvents((evs) => [...evs, { ...e, atS: state?.t ?? 0 }]);
  };

  const selectedRegion = anatomy?.regions.find((r) => r.id === regionId) ?? null;
  const visibleLog = (result?.log ?? []).filter((e) => e.t <= (state?.t ?? 0));
  const isMiniled = config.model === "miniled-32";

  return (
    <div className="app dell thermal-app">
      <header>
        <h1>UltraSharp Display Physics</h1>
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
            ? `t+${state.t}s · ${state.on ? "on" : "standby"} · ${state.acPowerW.toFixed(1)} W wall`
            : "—"}
        </span>
        <LevelControl />
      </header>

      <div className="an-hero">
        <h2>Brightness → backlight → watts → carbon</h2>
        <p>
          A monitor is a light with a computer attached. Panel power is
          maximum backlight × brightness × how much of the picture is lit —
          and whether that last term matters at all depends on the backlight
          architecture: one edge strip, or 2,000 mini-LED zones. No fans, no
          noise, nothing moving: the silent end of the physics suite, where
          the interesting ledger is lifetime carbon — what it cost to build
          versus what it costs to run.
        </p>
      </div>

      <div className="thermal-grid">
        {/* Left — build panel + scenarios */}
        <div className="thermal-col">
          <div className="an-panel">
            <h2>Panel</h2>
            <div className="btnrow">
              {presets.map((p) => (
                <button
                  key={p.id}
                  className={config.model === p.config.model ? "active" : ""}
                  title={p.blurb}
                  onClick={() => {
                    setConfig(p.config);
                    setActiveScenario(null);
                  }}
                >
                  {p.name}
                </button>
              ))}
            </div>
            <label className="field">
              Brightness {config.brightnessPct}%
              <input
                type="range" min={0} max={100} value={config.brightnessPct}
                onChange={(e) =>
                  setConfig({ ...config, brightnessPct: +e.target.value })
                }
              />
            </label>
            <div className="btnrow">
              {CONTENTS.map((c) => (
                <button
                  key={c}
                  className={config.content === c ? "active" : ""}
                  onClick={() => setConfig({ ...config, content: c })}
                >
                  {c}
                </button>
              ))}
            </div>
            {isMiniled && (
              <label className="field">
                <span>
                  Local dimming{" "}
                  <input
                    type="checkbox"
                    checked={config.localDimming}
                    onChange={(e) =>
                      setConfig({ ...config, localDimming: e.target.checked })
                    }
                  />
                </span>
              </label>
            )}
            <label className="field">
              USB-C to laptop {config.hubLaptopW} W
              <input
                type="range" min={0} max={90} step={5} value={config.hubLaptopW}
                onChange={(e) =>
                  setConfig({ ...config, hubLaptopW: +e.target.value })
                }
              />
            </label>
            {(result?.validations ?? [])
              .filter((v) => v.level !== "ok")
              .map((v) => (
                <div key={v.ruleId} className={`mini rule-${v.level}`}>
                  {v.message}
                </div>
              ))}
          </div>

          <div className="an-panel">
            <h2>Lifecycle assumptions</h2>
            <label className="field">
              On-hours per day {lifecycle.hoursPerDay}
              <input
                type="range" min={1} max={24} value={lifecycle.hoursPerDay}
                onChange={(e) =>
                  setLifecycle({ ...lifecycle, hoursPerDay: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Service years {lifecycle.serviceYears}
              <input
                type="range" min={1} max={12} value={lifecycle.serviceYears}
                onChange={(e) =>
                  setLifecycle({ ...lifecycle, serviceYears: +e.target.value })
                }
              />
            </label>
            <label className="field">
              Grid intensity {lifecycle.gridKgco2PerKwh.toFixed(2)} kgCO2e/kWh
              <input
                type="range" min={0.05} max={1.0} step={0.05}
                value={lifecycle.gridKgco2PerKwh}
                onChange={(e) =>
                  setLifecycle({
                    ...lifecycle,
                    gridKgco2PerKwh: +e.target.value,
                  })
                }
              />
              <span className="mini">estimate — set your region's figure</span>
            </label>
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

        {/* Center — monitor + playback + log */}
        <div className="thermal-col thermal-center">
          <div className="an-card">
            {error && <div className="mini an-error">{error}</div>}
            {anatomy && (
              <MonitorView
                anatomy={anatomy}
                state={state}
                isMiniled={isMiniled}
                dimming={dimmingNow}
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
              <button onClick={reset}>Reset</button>
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
              <button onClick={() => addEventNow({ action: "standby" })}>
                Sleep now
              </button>
              <button onClick={() => addEventNow({ action: "wake" })}>
                Wake
              </button>
              <button onClick={() => addEventNow({ action: "hub-plug", value: 90 })}>
                Dock a laptop (90 W)
              </button>
              <button onClick={() => addEventNow({ action: "hub-unplug" })}>
                Undock
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
                <div className="mini">No events yet — provoke some.</div>
              )}
              {visibleLog.slice(-10).map((e, i) => (
                <div key={i} className={`mini log-${e.severity}`}>
                  t+{e.t}s — {e.message}
                </div>
              ))}
            </div>
          </div>

          <div className="mini footnote">
            What we don't model: panel aging and LED lumen depreciation,
            ambient-light sensors, per-zone halo/blooming optics, pixel-level
            content (profiles stand in for real frames), and disposal
            logistics beyond the PCF end-of-life figure. Backlight maxima are
            estimates derived from Dell's published on-mode figures; embodied
            carbon comes from Dell PCF datasheets for the nearest class. The
            portfolio-wide version of the carbon ledger is the Circular
            Design spec (DellCircularDesign/initial_spec.md).
          </div>
        </div>

        {/* Right — instruments + chart */}
        <div className="thermal-col">
          <Instruments
            state={state}
            summary={result?.summary ?? null}
            explains={explains}
            explainOn={explainOn}
          />
          <StripChart trace={trace} cursor={cursor} />
        </div>
      </div>
    </div>
  );
}
