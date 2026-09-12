import { ControlPanel } from "@twinsim/twin-ui";

/**
 * LifecycleControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function LifecycleControls({
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
          The sequence is a fixed trace computed by the backend; Run only plays
          it back. Step walks one event at a time. Note which stage dwells
          longest — manufacture. Turning material into a working device is the
          expensive step, and that expense is the whole case for repair: every
          repair defers a manufacturing cycle, which is why the dull-looking
          repair and extend steps move the arithmetic more than anything in the
          recycling half of the loop.
        </>
      }
    />
  );
}
