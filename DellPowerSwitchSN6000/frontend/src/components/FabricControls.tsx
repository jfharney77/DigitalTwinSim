import type { Scenario } from "../types";

export function FabricControls({
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
  scenarios: Scenario[];
  scenario: string;
  onScenario: (id: string) => void;
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
  return (
    <div className="an-panel">
      <h2>Playback</h2>
      {scenarios.length > 1 && (
        <label className="field" style={{ marginBottom: 10 }}>
          Scenario
          <select
            className="scenario-picker"
            value={scenario}
            onChange={(e) => onScenario(e.target.value)}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </label>
      )}
      {scenarios
        .filter((s) => s.id === scenario && s.id !== "healthy")
        .map((s) => (
          <div key={s.id} className="mini" style={{ marginBottom: 10 }}>
            {s.summary}
          </div>
        ))}
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
        {scenarios.find((s) => s.id === scenario)?.playbackHint ??
          "Run plays back a fixed trace computed by the backend. The longest real-world stage dwells on screen longer."}
      </div>
    </div>
  );
}
