import { ControlPanel } from "@twinsim/twin-ui";

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
          it back. Step walks one event at a time — and Run holds the longer
          steps on screen longer, in the order the seconds the counter prints
          put them, so memory training sits there while the short stages flick
          past. The dwell is a rank, not a scale: a step that takes ten times
          as long does not sit there ten times as long.
        </>
      }
    />
  );
}
