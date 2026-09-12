import { ControlPanel } from "@twinsim/twin-ui";

/**
 * AccessControls — the shared {@link ControlPanel} with this twin's own note.
 *
 * The buttons, the speed slider and the phase line were identical in thirteen
 * frontends; only the parenthetical naming this twin's slow stages differed.
 */
export function AccessControls({
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
          plays it back. Two steps repay stepping through slowly. At{" "}
          <em>context</em>, network location is gathered and grants nothing —
          in a perimeter model that step would have been the authorization.
          At <em>breach</em>, an attacker is genuinely inside and the map does
          not open up around them.
        </>
      }
    />
  );
}
