import type { OnboardPhase, OnboardState } from "../types";

const PHASE_LABEL: Record<OnboardPhase, string> = {
  crated: "crated — nothing configured",
  power: "plugged in — the one on-site act",
  attest: "proving identity",
  onboard: "claimed into the estate",
  provision: "OS & platform landing",
  blueprint: "blueprint applying",
  workload: "workloads starting",
  managed: "managed — nobody there",
  quarantine: "one device refused",
  replace: "failed unit swapped",
  recovered: "replacement trusted",
};

// One clock format for the header strip, the tour aside and this panel, so
// a reader never has to divide seconds to reconcile them. The failure
// scenario jumps days ahead for the replacement.
export function elapsed(seconds: number): string {
  if (seconds < 60) return `t+${seconds} s`;
  if (seconds < 3_600) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return s === 0 ? `t+${m} min` : `t+${m} min ${s} s`;
  }
  if (seconds < 86_400) {
    const h = Math.floor(seconds / 3_600);
    return `t+${h} h ${Math.floor((seconds % 3_600) / 60)} min`;
  }
  return `t+${(seconds / 86_400).toFixed(1)} days`;
}

export function OnboardCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: OnboardState | null;
  stepIndex: number;
  stepCount: number;
}) {
  // Failure-scenario traces carry per-device fields; the happy path does not.
  const isFailure = state?.endpointTrust !== undefined;
  const quarantined = state?.failedEndpoints?.length ?? 0;
  const trusted = Object.values(state?.endpointTrust ?? {}).filter(Boolean)
    .length;
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
        <span>operator actions</span>
        <span>{state ? state.operatorActions : 0}</span>
      </div>
      {isFailure && state ? (
        <>
          <div className={quarantined > 0 ? "stat stat-failed" : "stat"}>
            <span>quarantined</span>
            <span>{quarantined} / 4</span>
          </div>
          <div className="stat">
            <span>devices trusted</span>
            <span>{trusted} / 4</span>
          </div>
          <div className="stat">
            <span>software delivered to</span>
            <span>{state.deployedTo?.length ?? 0} / 4</span>
          </div>
          <div className="stat">
            <span>recovery actions</span>
            <span>{state.recoveryActions ?? 0}</span>
          </div>
        </>
      ) : (
        <div className="stat">
          <span>trust established</span>
          <span>{state ? (state.trustEstablished ? "yes — held" : "not yet") : "not yet"}</span>
        </div>
      )}
      <div className="stat">
        <span>endpoints online</span>
        <span>{state ? `${state.endpointsOnline} / 4` : "0 / 4"}</span>
      </div>
      <div className="stat">
        <span>site bring-up</span>
        <span>{state ? `${state.progressPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? elapsed(state.elapsedSeconds) : "t+0 s"}</span>
      </div>
      {isFailure && (
        <div className="mini" style={{ marginTop: 8 }}>
          Trust is counted per device here. Software is only ever delivered
          to trusted devices, so "software delivered to" can never exceed
          "devices trusted". On-site human acts are split across two rows:
          operator actions counts the plug-in visit and stays at 1, and
          swapping the failed unit is counted under recovery actions. Add
          the two for everything people at the site did.
        </div>
      )}
      <div className="mini" style={{ marginTop: 8 }}>
        Operator actions counts on-site human acts for this one site, not
        per device: it reaches 1 when someone plugs the four devices into
        power and the network, and onboarding never moves it again. Central
        work, such as loading ownership vouchers and writing the blueprint,
        is done once for the whole estate and is not counted here. Nothing
        comes online before trust is established — zero-touch without
        attestation would just be an unknown machine on your network.
        Values are typical, meant to show shape and order.
      </div>
    </div>
  );
}
