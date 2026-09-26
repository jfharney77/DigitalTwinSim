import { MetricReadout } from "@twinsim/twin-ui";
import type { Metric } from "@twinsim/twin-ui";
import type { FailoverPhase, PowerPhase, TraceState } from "../types";

const PHASE_LABEL: Record<PowerPhase | FailoverPhase, string> = {
  fault: "node A down",
  failover: "failing over to node B",
  degraded: "single node",
  rejoin: "node A returning",
  resync: "node A catching up",
  rebalance: "failing back",
  restored: "active/active again",
  off: "off — AC only",
  power: "power & standby",
  boot: "nodes booting",
  drives: "drive discovery",
  cluster: "cluster forming",
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
  state: TraceState | null;
  stepIndex: number;
  stepCount: number;
}) {
  // A failure scenario's states carry the failure fields; the power-on
  // trace's do not, and its readout is unchanged.
  const failure = state?.ackedWritesLost !== undefined;
  const common: Metric[] = [
    { label: "phase", value: state ? PHASE_LABEL[state.phase] : "—" },
    {
      label: "step",
      value: stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—",
    },
  ];
  const metrics: Metric[] =
    failure && state
      ? [
          ...common,
          {
            label: "acknowledged writes lost",
            value: `${state.ackedWritesLost}`,
            hero: true,
          },
          { label: "host I/O served", value: `${state.ioPercent}%` },
          { label: "nodes serving", value: `${state.nodesServing} of 2` },
          { label: "node B load", value: `${state.nodeBLoadPercent}%` },
          {
            label: "volumes on optimized paths",
            value: `${state.optimizedPathsPercent}%`,
          },
          {
            label: "writes mirrored in NVRAM",
            value: state.writesMirrored ? "yes" : "no",
          },
          { label: "power draw", value: `${state.powerWatts} W` },
          { label: "since the fault", value: `t+${state.elapsedSeconds}s` },
        ]
      : [
          ...common,
          { label: "power draw", value: state ? `${state.powerWatts} W` : "0 W" },
          { label: "fan speed", value: state ? `${state.fanPercent}%` : "0%" },
          {
            label: "elapsed (typical)",
            value: state ? `t+${state.elapsedSeconds}s` : "t+0s",
          },
        ];
  return (
    <MetricReadout
      metrics={metrics}
      note={
        failure ? (
          <>
            Percentages, watts and timings are illustrative. Dell publishes no
            block failover time; it depends on load and on how many resources
            move. The zero is the claim, and the write path is why it holds.
          </>
        ) : (
          <>
            Watts and timings are typical values for a mid-range dual-node
            appliance, meant to show shape and order of magnitude — not a
            measurement of your array.
          </>
        )
      }
    />
  );
}
