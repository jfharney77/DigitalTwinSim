import type { CloudPhase, CloudState } from "../types";

const PHASE_LABEL: Record<CloudPhase, string> = {
  off: "separate racks, nothing assembled",
  pools: "pooling resources independently",
  control: "one control plane",
  install: "hypervisor chosen",
  deploy: "workloads landing",
  run: "steady state",
  growstorage: "storage added — compute untouched",
  switch: "migrating to a second hypervisor",
  mixed: "two hypervisors, one console",
};

export function CloudCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: CloudState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const grew = state !== null && state.phase === "growstorage";
  return (
    <div className="an-panel">
      <h2>Estate</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>compute pool</span>
        <span>
          {state
            ? `${state.computeUnits} servers${grew ? " — unchanged" : ""}`
            : "0 servers"}
        </span>
      </div>
      <div className="stat">
        <span>storage pool</span>
        <span>{state ? `${state.storageTb} TB` : "0 TB"}</span>
      </div>
      <div className="stat">
        <span>hypervisors</span>
        <span>{state ? state.hypervisorsActive : 0}</span>
      </div>
      <div className="stat">
        <span>control planes</span>
        <span>{state ? state.controlPlanes : 0}</span>
      </div>
      <div className="stat">
        <span>workloads</span>
        <span>{state ? state.workloads : 0}</span>
      </div>
      <div className="stat">
        <span>workload downtime</span>
        <span>{state ? `${state.workloadDowntimeSeconds}s` : "0s"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedMinutes}m` : "t+0m"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Read the compute row against the storage row at the expansion step:
        capacity doubles and not one server is added. On a hyperconverged
        cluster that same need is met by adding nodes, and a node brings
        processors whether or not anyone wanted them — which is why estates
        so routinely own a third more of one resource than they will ever
        use. Then watch control planes stay at one while hypervisors reach
        two. Values are typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
