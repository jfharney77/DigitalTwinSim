import { ControlPanel } from "@twinsim/twin-ui";

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
          The sequence is a fixed trace computed by the backend; Run only
          plays it back. Step walks one event at a time. Note which stage
          dwells longest — it is building the pool, not repairing it. Every
          other twin here lingers on a recovery-ish stage; this one lingers on
          the setup, because scattering chunks everywhere in advance is
          precisely what makes the repair short.
        </>
      }
    />
  );
}
