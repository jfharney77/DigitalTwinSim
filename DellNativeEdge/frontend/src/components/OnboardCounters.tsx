import type { OnboardPhase, OnboardState } from "../types";

const PHASE_LABEL: Record<OnboardPhase, string> = {
  crated: "crated — nothing configured",
  power: "plugged in — the one human act",
  attest: "proving identity",
  onboard: "claimed into the estate",
  provision: "OS & platform landing",
  blueprint: "blueprint applying",
  workload: "workloads starting",
  managed: "managed — nobody there",
};

export function OnboardCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: OnboardState | null;
  stepIndex: number;
  stepCount: number;
}) {
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
      <div className="stat">
        <span>trust established</span>
        <span>{state ? (state.trustEstablished ? "yes — held" : "not yet") : "not yet"}</span>
      </div>
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
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The operator-actions row is the whole product claim: it reaches 1
        when someone plugs in power and a network cable, and it never moves
        again. Nothing comes online before trust is established — zero-touch
        without attestation would just be an unknown machine on your
        network. Values are typical, meant to show shape and order.
      </div>
    </div>
  );
}
