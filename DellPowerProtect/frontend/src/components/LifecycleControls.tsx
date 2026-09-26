import type { ScenarioInfo } from "../types";

export function LifecycleControls({
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
      {scenarios.length > 0 && (
        <label className="field" style={{ marginBottom: 10 }}>
          Scenario
          <select
            aria-label="Scenario"
            value={scenario}
            onChange={(e) => onScenario(e.target.value)}
          >
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
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
        Each scenario is a fixed trace computed by the backend; Run only
        plays it back. Step walks one event at a time — the long real-world
        stage (the CyberSense content scan, or cleaning's copy pass) dwells
        on screen longer.
      </div>
    </div>
  );
}
