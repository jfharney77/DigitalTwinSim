import type { ReactNode } from "react";

/**
 * Playback controls for a trace.
 *
 * Every twin re-typed this as `PowerOnControls`, `BootControls`,
 * `FirstRunControls`, `ThermalControls`, `JoinControls`, `AccessControls`,
 * `OnboardControls`, ... — the same four buttons, the same speed slider, the
 * same "the trace is fixed, Run only plays it back" note, under a different
 * name each time.
 *
 * The clock stays in the consumer: this component reports intent and renders
 * state, and never owns a timer. That is the repo's oldest invariant and it
 * would be easy to lose here.
 */
export function ControlPanel({
  title = "Playback",
  running,
  done,
  speed,
  speedRange = [1, 20],
  status,
  note,
  onRun,
  onPause,
  onStep,
  onReset,
  onSpeed,
  children,
}: {
  title?: string;
  running: boolean;
  done?: boolean;
  speed: number;
  speedRange?: readonly [number, number];
  /** The current phase, in the twin's own words. */
  status?: ReactNode;
  /** What the reader should know about what they are watching. */
  note?: ReactNode;
  onRun: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
  onSpeed: (speed: number) => void;
  children?: ReactNode;
}) {
  return (
    <div className="an-panel">
      <h2>{title}</h2>
      <div className="btnrow">
        <button className="primary" onClick={running ? onPause : onRun}>
          {running ? "Pause" : "Run"}
        </button>
        <button onClick={onStep}>Step</button>
        <button onClick={onReset}>Reset</button>
      </div>
      <label className="field" style={{ marginTop: 10 }}>
        Speed
        <input
          type="range"
          min={speedRange[0]}
          max={speedRange[1]}
          value={speed}
          onChange={(event) => onSpeed(Number(event.target.value))}
        />
      </label>
      {status !== undefined && (
        <div className="phase">
          {done ? "✓ " : ""}
          {status}
        </div>
      )}
      {children}
      {note && (
        <div className="mini" style={{ marginTop: 8 }}>
          {note}
        </div>
      )}
    </div>
  );
}
