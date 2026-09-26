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
  level,
}: {
  state: NamespaceState | null;
  stepIndex: number;
  stepCount: number;
  level: number;
}) {
  // Before the cluster forms there is no file system to count and no pooled
  // capacity to report: the nodes' drives are racked but belong to nothing.
  const unformed = state !== null && state.nodes === 0;
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
          {!state
            ? "—"
            : unformed
              ? "— until the cluster forms"
              : `${state.namespaces} — always`}
        </span>
      </div>
      <div className="stat">
        <span>migrations required</span>
        <span style={{ color: "var(--accent)", fontWeight: 700 }}>
          {state && !unformed ? state.migrationsRequired : "—"}
        </span>
      </div>
      <div className="stat">
        <span>capacity</span>
        <span>
          {!state
            ? "0 TB"
            : unformed
              ? `unjoined (${state.capacityTb} TB racked)`
              : `${state.capacityTb} TB`}
        </span>
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
        {level <= 2 ? (
          <>
            A namespace is one shared file system, and the namespaces row is
            the point of this product. On most NAS (network-attached
            storage) systems that row would count volumes, the walled-off
            sections the space is divided into. Growing would add another
            volume, and then someone would have to copy data into it, which
            is called a migration. Here the row reads 1 with four nodes and
            1 with six, and migrations required reads 0 the whole way,
            because there are no walls for data to be moved across. Both
            rows wait at the first step, when the nodes are racked but not
            yet joined. Watch capacity jump at the addnode step while both
            numbers hold still. Used rises a little at the end because
            people kept saving files. Values are typical, meant to show
            shape and rough size.
          </>
        ) : (
          <>
            The namespaces row is the whole product claim. On a conventional
            NAS it would count volumes, and growing the system would add
            one, plus a migration to fill it. Here it reads 1 at four nodes
            and 1 at six, and the migrations row reads 0 across the
            expansion, because there is no volume boundary for data to be
            moved over. At the first step the nodes are racked but
            unjoined, so there is no namespace or pooled capacity to report
            yet. Watch capacity jump at the addnode step while both hero
            numbers hold still; the small rise in used at the end is client
            ingest during the rebalance. Values are typical, meant to show
            shape and order of magnitude.
          </>
        )}
      </div>
    </div>
  );
}
