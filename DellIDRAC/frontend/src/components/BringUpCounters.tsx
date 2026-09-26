import type { BringUpPhase, BringUpState, UpdatePhase } from "../types";

const PHASE_LABEL: Record<BringUpPhase | UpdatePhase, string> = {
  off: "off — no AC",
  standby: "standby power",
  reset: "SoC reset · root of trust",
  bootldr: "bootloader",
  kernel: "embedded Linux",
  services: "services + Lifecycle Controller",
  ready: "ready — watching",
  upload: "package upload",
  verify: "signature verification",
  stage: "staging to the inactive partition",
  reboot: "iDRAC restart",
  bootcheck: "boot check of the new image",
  rollback: "rollback to the previous partition",
  restored: "restored on the old version",
};

export function BringUpCounters({
  state,
  stepIndex,
  stepCount,
  stepSeconds,
  longest,
}: {
  state: BringUpState | null;
  stepIndex: number;
  stepCount: number;
  /** How long this step lasts: its end stamp minus the previous step's. */
  stepSeconds: number;
  /** True on the single longest step of the trace being played. */
  longest: boolean;
}) {
  // The failure scenario's fields are absent from the bring-up trace, so
  // their presence is what selects the second set of readouts.
  const update = state?.hostPowered !== undefined;
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>
          {stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}
        </span>
      </div>
      {update && state ? (
        <>
          <div className="stat tw-hero">
            <span>management outage</span>
            <span>{state.managementOutageSeconds ?? 0} s</span>
          </div>
          <div className="stat">
            <span>host power</span>
            <span>{state.hostPowered ? "on — workload running" : "off"}</span>
          </div>
          <div className="stat">
            <span>management plane</span>
            <span className={state.managementReachable ? "" : "stat-bad"}>
              {state.managementReachable ? "reachable" : "unreachable"}
            </span>
          </div>
          <div className="stat">
            <span>running</span>
            <span>
              {state.runningVersion} · partition {state.activePartition}
            </span>
          </div>
          <div className="stat">
            <span>flash write</span>
            <span>
              {state.writingPartition
                ? `partition ${state.writingPartition} (inactive)`
                : "none"}
            </span>
          </div>
          <div className="stat">
            <span>bootable images, as iDRAC counts them</span>
            <span
              className={
                (state.failedRegions?.length ?? 0) > 0 ? "stat-bad" : ""
              }
            >
              {state.bootableImages} of 2
            </span>
          </div>
          <div className="stat">
            <span>update job</span>
            <span className={state.failedRegions?.length ? "stat-bad" : ""}>
              {state.failedRegions?.length
                ? "failed"
                : state.progressPercent > 0
                  ? "running"
                  : "not started"}
            </span>
          </div>
        </>
      ) : (
        <div className="stat">
          <span>init progress</span>
          <span>{state ? `${state.progressPercent}%` : "0%"}</span>
        </div>
      )}
      <div className="stat">
        <span>BMC domain draw</span>
        <span>{state ? `${state.powerWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>this step takes</span>
        <span>
          {stepSeconds} s{longest ? " · the longest step" : ""}
        </span>
      </div>
      <div className="stat">
        <span>elapsed at the end of this step</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      {update && state?.logEntry && (
        <div className="mini log-entry">{state.logEntry}</div>
      )}
      <div className="mini" style={{ marginTop: 8 }}>
        {update
          ? "The host stays powered on throughout — only the management controller restarts. Seconds, watts, version numbers and partition letters are illustrative, not a measurement of your box."
          : "The host stays powered off throughout — this is the management controller booting itself. Watts and timings are typical values meant to show shape and order of magnitude, not a measurement of your box."}
      </div>
    </div>
  );
}
