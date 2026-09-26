import { ControlPanel } from "@twinsim/twin-ui";
import type { ScenarioInfo } from "../types";

/**
 * PipelineControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function PipelineControls({
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
  speed: number;
  running: boolean;
  done: boolean;
  phaseLabel: string;
  onSpeed: (s: number) => void;
  onRun: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  scenario: string;
  scenarios: ScenarioInfo[];
  onScenario: (id: string) => void;
}) {
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
        scenario === "healthy" ? (
          <>
            The sequence is a fixed trace computed by the backend; Run only
            plays it back. Step walks one event at a time — the ML analyze
            stage dwells on screen longer because it is the heavy one.
          </>
        ) : (
          <>
            A second fixed trace from the same backend engine. The longest
            dwell is the step where the portal lists the array as not sending
            data. A new system can take up to an hour to show data, so a grey
            dash only counts as a fault after that.
            Changing the scenario rewinds playback.
          </>
        )
      }
    >
      {scenarios.length > 0 && (
        <label className="field" style={{ marginTop: 10 }}>
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
    </ControlPanel>
  );
}
