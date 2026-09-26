import { MetricReadout } from "@twinsim/twin-ui";
import { useLevel } from "../level";
import type { PowerOnState, PowerPhase } from "../types";

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "off — AC only",
  standby: "standby power",
  bmc: "iDRAC booting",
  poweron: "host power-on",
  post: "POST",
  boot: "boot device",
  os: "operating system",
};

// Every other phase reads as plain English already; POST is the one bare
// acronym, so a reader at levels 1–2 gets it spelled out. The trace prose is
// leveled on the backend, but this label is the frontend's own string.
const PHASE_LABEL_NOVICE: Partial<Record<PowerPhase, string>> = {
  post: "start-up checks (POST)",
};

/**
 * PowerOnCounters — the shared {@link MetricReadout} with this twin's rows.
 *
 * The `.stat` markup was hand-written once per twin under a different name
 * each time (`PowerOnCounters`, `FabricCounters`, `DetectCounters`,
 * `Instruments`); the rows and the caveat are what actually differ.
 */
export function PowerOnCounters({
  state,
  stepIndex,
  stepCount,
  previousElapsedSeconds,
  longest,
}: {
  state: PowerOnState | null;
  stepIndex: number;
  stepCount: number;
  /** The previous step's stamp; stamps mark the END of a step. */
  previousElapsedSeconds: number;
  /** True on the single longest step of the trace — labelled, as iDRAC's is. */
  longest: boolean;
}) {
  const level = useLevel();
  const took = state ? state.elapsedSeconds - previousElapsedSeconds : 0;
  const phaseLabel = state
    ? (level <= 2 ? PHASE_LABEL_NOVICE[state.phase] : undefined) ??
      PHASE_LABEL[state.phase]
    : "—";
  return (
    <MetricReadout
      metrics={[
        { label: "phase", value: phaseLabel },
        {
          label: "step",
          value: stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—",
        },
        { label: "power draw", value: state ? `${state.powerWatts} W` : "0 W" },
        { label: "fan speed", value: state ? `${state.fanPercent}%` : "0%" },
        {
          label: "this step takes (typical)",
          value: `${took} s${longest ? " · the longest step" : ""}`,
        },
        {
          label: "elapsed at end of step",
          value: state ? `t+${state.elapsedSeconds}s` : "t+0s",
        },
      ]}
      note={
        <>
          Watts and timings are typical values for a mid-range dual-socket
          configuration, meant to show shape and order of magnitude — not a
          measurement of your box. The clock is read when a step finishes, so
          a step's duration is its stamp minus the one before. Run lingers
          longer on the longer steps, ranked by that duration rather than
          scaled to it.
        </>
      }
    />
  );
}
