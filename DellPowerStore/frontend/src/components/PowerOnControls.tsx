import { ControlPanel } from "@twinsim/twin-ui";
import type { ScenarioInfo } from "../types";

/**
 * PowerOnControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function PowerOnControls({
  speed,
  running,
  done,
  phaseLabel,
  onSpeed,
  onRun,
  onPause,
  onStep,
  onReset,
  scenarios,
  scenarioId,
  onScenario,
}: {
  scenarios: ScenarioInfo[];
  scenarioId: string;
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
  const current = scenarios.find((sc) => sc.id === scenarioId);
  return (
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
          {current && current.id !== "power-on" && (
            <span className="scenario-note">
              {current.summary} {current.basis}
              {current.sources.map((src) => (
                <a key={src.url} href={src.url} target="_blank" rel="noreferrer">
                  {src.label}
                </a>
              ))}
              <br />
            </span>
          )}
          The sequence is a fixed trace computed by the backend; Run only plays
          it back. Step walks one event at a time — longer real-world stages
          (node OS boot, pool assembly) dwell on screen longer.
        </>
      }
    >
      {scenarios.length > 1 && (
        <label className="field" style={{ marginTop: 10 }}>
          Scenario
          <select
            value={scenarioId}
            onChange={(event) => onScenario(event.target.value)}
          >
            {scenarios.map((sc) => (
              <option key={sc.id} value={sc.id}>
                {sc.name}
              </option>
            ))}
          </select>
        </label>
      )}
    </ControlPanel>
  );
}
