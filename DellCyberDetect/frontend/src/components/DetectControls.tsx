import type { ScenarioInfo } from "../types";

export function DetectControls({
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
                {s.name}
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
      {scenarios
        .filter((s) => s.id === scenario && s.id !== "baseline")
        .map((s) => (
          <div key={s.id} className="mini" style={{ marginTop: 8 }}>
            {s.summary} Retention here is {s.retentionHours} hours, an
            illustrative figure.
          </div>
        ))}
      <div className="mini" style={{ marginTop: 8 }}>
        The incident is a fixed trace computed by the backend; Run only
        plays it back. Stepping is worthwhile here — pause on the blind
        step and look at the timeline before the analysis runs. Every
        snapshot is drawn identically because at that moment they genuinely
        are indistinguishable. The corrupted ones only turn red once
        something has read the bytes inside them.
      </div>
    </div>
  );
}
