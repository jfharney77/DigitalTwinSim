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
  const degraded = state !== null && state.protectedPercent < 100;
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
            ? `${state.protectedPercent}%${degraded ? " — degraded" : ""}`
            : "0%"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The rebuild-participants row is the whole product claim. In a
        controller array it would read 1 whatever the cluster size, because
        one surviving controller does the work. Here it equals the number of
        surviving nodes — so a hundred-node pool rebuilds roughly twenty
        times faster than this six-node one, and recovery gets quicker as
        the system grows. Watch client I/O during the failure too: a dip
        proportional to the lost server, never a failover pause. Values are
        typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
