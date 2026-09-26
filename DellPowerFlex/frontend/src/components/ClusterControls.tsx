import { ControlPanel } from "@twinsim/twin-ui";
import { useLevel } from "../level";

/**
 * ClusterControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function ClusterControls({
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
  const level = useLevel();
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
        level >= 4 ? (
          <>Fixed backend trace. Run plays it back; Step advances one event.</>
        ) : (
          <>
            The sequence is a fixed trace computed by the backend; Run only
            plays it back. Step walks one event at a time. Playback lingers
            longest on building the pool, not on repairing it: scattering
            chunks everywhere in advance is what makes the repair short.
          </>
        )
      }
    />
  );
}
