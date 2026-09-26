import { useLevel } from "../level";
import type { ClusterPhase, ClusterState } from "../types";

const PHASE_LABEL: Record<ClusterPhase, string> = {
  off: "off — drives unpooled",
  cluster: "nodes joining",
  pool: "scattering chunks",
  volumes: "volumes presented",
  io: "steady I/O",
  failure: "node lost",
  rebuild: "rebuilding, all nodes",
  rebalanced: "protection restored",
  steady: "steady state",
};

export function ClusterCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: ClusterState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const level = useLevel();
  // Before the pool exists there is nothing to protect, so 0% there is not
  // "degraded" — only a partially protected pool is.
  const pooled = state !== null && state.protectedPercent > 0;
  const degraded = pooled && state.protectedPercent < 100;
  const rebuilding = state !== null && state.rebuildParticipants > 0;
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>nodes online</span>
        <span>{state ? state.nodesOnline : 0}</span>
      </div>
      <div className="stat">
        <span>rebuild participants</span>
        <span>
          {state
            ? rebuilding
              ? `${state.rebuildParticipants} — every survivor`
              : "0"
            : "0"}
        </span>
      </div>
      <div className="stat">
        <span>client I/O</span>
        <span>{state ? `${state.iopsThousands}k IOPS` : "0k IOPS"}</span>
      </div>
      <div className="stat">
        <span>data protected</span>
        <span>
          {state
            ? pooled
              ? `${state.protectedPercent}%${degraded ? " — degraded" : ""}`
              : "— no pool yet"
            : "—"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {level <= 2 ? (
          <>
            Client I/O counts read and write requests per second (IOPS), in
            thousands. Rebuild participants is the row to watch. In a storage
            system built around a pair of controllers, the special computers
            all data passes through, the repair can go no faster than that
            one pair allows, however many drives sit behind it. Here every
            surviving server rebuilds, so the limit grows with the pool:
            about a hundred survivors would repair roughly twenty times
            faster than the five here. During the failure, client I/O falls
            by the lost server's share and never reaches zero. Requests
            headed for the dead server wait a few seconds and are retried,
            which these steps are too coarse to show. Every value and time
            is illustrative: it shows the shape, not a measurement.
          </>
        ) : level >= 4 ? (
          <>
            Rebuild participants equals nodes online: the rebuild budget
            scales with the survivors (100 against 5 is about 20x), where a
            controller pair's fixed budget caps the rate at any size. Node
            loss costs 1/n IOPS, never zero; the seconds-long remap stall is
            below this trace's resolution. Values and clock are illustrative.
          </>
        ) : (
          <>
            Rebuild participants is the product claim. In a controller array
            the rebuild rate is capped by the controller pair's fixed budget
            at any size, however many drives share the work. Here it grows
            with the survivors: about a hundred of them would rebuild
            roughly twenty times faster than the five here. Watch client
            I/O (thousands of operations per second) during the failure
            too: it dips by the lost server's share, with no controller
            failover, and never reaches zero. Requests in flight to the dead
            node wait out a timeout of a few seconds, which these steps are
            too coarse to show. Values and times are illustrative; they show
            the shape, not measurements.
          </>
        )}
      </div>
    </div>
  );
}
