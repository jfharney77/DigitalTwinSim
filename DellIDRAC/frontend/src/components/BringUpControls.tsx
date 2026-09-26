import { ControlPanel } from "@twinsim/twin-ui";
import type { ScenarioId, ScenarioInfo } from "../types";

/**
 * BringUpControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function BringUpControls({
  speed,
  running,
  done,
  phaseLabel,
  onSpeed,
  onRun,
  onPause,
  onStep,
  onReset,
  scenario,
  scenarios,
  onScenario,
}: {
  scenario: ScenarioId;
  scenarios: ScenarioInfo[];
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
  const info = scenarios.find((s) => s.id === scenario) ?? null;
  const failure = scenario !== "bring-up";
  return (
    <>
    <div className="an-panel scenario-panel">
      <h2>Scenario</h2>
      <label className="field">
        Trace to play
        <select
          aria-label="Scenario"
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
      {info && <p className="mini scenario-summary">{info.summary}</p>}
      {info && failure && (
        <>
          <details className="mini scenario-sources">
            <summary>Sources and what is illustrative</summary>
            <p className="scenario-summary">{info.basis}</p>
            <ul>
              {info.sources.map((src) => (
                <li key={src.url}>
                  <a href={src.url} target="_blank" rel="noreferrer">
                    {src.label}
                  </a>
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
    </div>
    <ControlPanel
      running={running}
      done={done}
      speed={speed}
      status={phaseLabel}
      onRun={onRun}
      onPause={onPause}
      onStep={onStep}
      onReset={onReset}
      onSpeed={onSpeed}
      note={
        <>
          The sequence is a fixed trace computed by the backend; Run only plays
          it back. Step walks one event at a time — the longer real-world stage
          ({failure ? "writing the image to flash" : "Lifecycle Controller init"})
          dwells on screen longer.
        </>
      }
    />
    </>
  );
}
