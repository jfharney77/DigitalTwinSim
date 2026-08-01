import type { NamespacePhase, NamespaceState } from "../types";

const PHASE_LABEL: Record<NamespacePhase, string> = {
  off: "off — nodes unracked",
  form: "cluster forming",
  stripe: "striping across nodes",
  serve: "serving clients",
  fill: "filling up",
  addnode: "nodes joining",
  rebalance: "rebalancing, no outage",
  served: "serving at larger scale",
};

export function NamespaceCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: NamespaceState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const rebalancing = state !== null && state.rebalancing;
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
        <span>nodes</span>
        <span>{state ? state.nodes : 0}</span>
      </div>
      {/* The two hero numbers: what this architecture refuses to have. */}
      <div className="stat">
        <span>namespaces</span>
        <span style={{ color: "var(--accent)", fontWeight: 700 }}>
          {state ? `${state.namespaces} — always` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>migrations required</span>
        <span style={{ color: "var(--accent)", fontWeight: 700 }}>
          {state ? state.migrationsRequired : "—"}
        </span>
      </div>
      <div className="stat">
        <span>capacity</span>
        <span>{state ? `${state.capacityTb} TB` : "0 TB"}</span>
      </div>
      <div className="stat">
        <span>used</span>
        <span>{state ? `${state.usedPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>rebalancing</span>
        <span>{rebalancing ? "yes — clients still served" : "no"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The namespaces row is the whole product claim. On a conventional NAS
        it would count volumes, and growing the system would add one — plus
        a migration to fill it. Here it reads 1 at four nodes and 1 at six,
        and the migrations row reads 0 across the expansion, because there
        is no volume boundary for data to be moved over. Watch capacity
        jump at the addnode step while both hero numbers hold still. Values
        are typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
