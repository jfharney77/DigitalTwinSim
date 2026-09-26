import type { ScenarioInfo } from "../types";

export function FirstRunControls({
  scenario,
  scenarios,
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
  scenario: string;
  scenarios: ScenarioInfo[];
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
  const current = scenarios.find((s) => s.id === scenario);
  const isFailure = current?.kind === "failure";
  return (
    <div className="an-panel">
      <h2>Playback</h2>
      {scenarios.length > 0 && (
        <label className="field" style={{ marginBottom: 10 }}>
          Scenario
          <select
            className="scenario-select"
            value={current ? scenario : ""}
            onChange={(e) => onScenario(e.target.value)}
          >
            {!current && <option value="">Unknown scenario</option>}
            {scenarios.map((s) => (
              <option key={s.id} value={s.id}>
                {s.title}
              </option>
            ))}
          </select>
        </label>
      )}
      {current && (
        <div className="mini scenario-summary" style={{ marginBottom: 10 }}>
          {current.summary}
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
        {isFailure
          ? "The node add is a fixed trace computed by the backend; Run only plays it back. Step walks one event at a time, and the longer real-world stages (the re-image, the vSAN rebalance) dwell on screen longer."
          : "The first-run sequence is a fixed trace computed by the backend; Run only plays it back. Step walks one event at a time — longer real-world stages (ESXi boot, the VxRail Manager cluster build) dwell on screen longer."}
      </div>
    </div>
  );
}
