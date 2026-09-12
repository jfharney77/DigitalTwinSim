import { MetricReadout } from "@twinsim/twin-ui";
import type { PowerOnState, PowerPhase } from "../types";

const PHASE_LABEL: Record<PowerPhase, string> = {
  off: "off — AC only",
  power: "power & standby",
  vault: "validating vault",
  boot: "directors booting",
  fabric: "fabric forming",
  drives: "drive discovery",
  pool: "pool assembling",
  services: "data services",
  online: "serving I/O",
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
}: {
  state: PowerOnState | null;
  stepIndex: number;
  stepCount: number;
}) {
  return (
    <MetricReadout
      metrics={[
        { label: "phase", value: state ? PHASE_LABEL[state.phase] : "—" },
        {
          label: "step",
          value: stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—",
        },
        { label: "power draw", value: state ? `${state.powerWatts} W` : "0 W" },
        { label: "fan speed", value: state ? `${state.fanPercent}%` : "0%" },
        {
          label: "elapsed (typical)",
          value: state ? `t+${state.elapsedSeconds}s` : "t+0s",
        },
      ]}
      note={
        <>
          Watts and timings are typical values for a single node pair plus one
          drive enclosure, meant to show shape and order of magnitude — not a
          measurement of your array.
        </>
      }
    />
  );
}
