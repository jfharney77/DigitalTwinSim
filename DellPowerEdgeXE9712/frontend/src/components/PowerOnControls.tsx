import type { ScenarioId, ScenarioInfo } from "../types";

export function PowerOnControls({
  scenarios,
  scenario,
  onScenario,
  speed,
  running,
  done,
  phaseLabel,
  onSpeed,
  onRun,
  onPause,
  onStep,
  onReset,
}: {
  scenarios: ScenarioInfo[];
  scenario: ScenarioId;
  onScenario: (id: ScenarioId) => void;
  speed: number;
  running: boolean;
  done: boolean;
  phaseLabel: string;
  onSpeed: (s: number) => void;
  onRun: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
}) {
  const current = scenarios.find((s) => s.id === scenario);
  return (
    <div className="an-panel">
      <h2>Playback</h2>
      {scenarios.length > 1 && (
        <label className="field" style={{ marginBottom: 10 }}>
          Scenario
          <select
            className="scenario-select"
            value={scenario}
            onChange={(e) => onScenario(e.target.value as ScenarioId)}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {current && scenario !== "nominal" && (
        <div className="mini scenario-summary" style={{ marginBottom: 10 }}>
          {current.summary}
          {current.sources.length > 0 && (
            <>
              {" "}
              Modelled on:{" "}
              {current.sources.map((src, i) => (
                <span key={src.url}>
                  {i > 0 && ", "}
                  <a href={src.url} target="_blank" rel="noreferrer" title={src.label}>
                    {new URL(src.url).hostname.replace(/^www\./, "")} [{i + 1}]
                  </a>
                </span>
              ))}
              .
            </>
          )}
        </div>
      )}
      <div className="btnrow">
        {running ? (
          <button className="primary" onClick={onPause}>
            Pause
          </button>
        ) : (
          <button className="primary" onClick={onRun}>
            Run
          </button>
        )}
        <button onClick={onStep}>Step</button>
        <button onClick={onReset}>Reset</button>
      </div>
      <label className="field" style={{ marginTop: 10 }}>
        Speed
        <input
          type="range"
          min={1}
          max={20}
          value={speed}
          onChange={(e) => onSpeed(Number(e.target.value))}
        />
      </label>
      <div className="phase">
        {done ? "✓ " : ""}
        {phaseLabel}
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The power-on sequence is a fixed trace computed by the backend; Run
        only plays it back. Step walks one event at a time — longer real-world
        stages (GPU init, NVLink fabric training) dwell on screen longer.
      </div>
    </div>
  );
}
