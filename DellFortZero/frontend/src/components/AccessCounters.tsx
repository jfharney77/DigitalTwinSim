import { useLevel } from "../level";
import type { AccessPhase, AccessState } from "../types";

const PHASE_LABEL: Record<AccessPhase, string> = {
  idle: "no session — nothing trusted",
  request: "request for one resource",
  verify: "identity and posture",
  context: "location gathered as evidence",
  decide: "policy engine ruling",
  grant: "one resource, leased",
  monitor: "continuous verification",
  expire: "lease expired — back to nothing",
  breach: "attacker inside the network",
  contained: "lateral movement finds nothing",
};

// Implicit trust is defined here because the counter is the only place the
// phrase appears on the page, and the twin exists to show it at zero.
const NOTE_NOVICE =
  "Implicit trust means access given just for being inside: on the office " +
  "network, on a company machine, already signed in. That row stays at " +
  "zero on every step, including the breach step, where an attacker sits " +
  "inside the network, the exact spot a wall-based design calls safe. The " +
  "count of checks never stops climbing: one check at the door is not " +
  "this design. Confidence is how sure the decision-maker is about this " +
  "one request. The request was approved at 88%; at the breach step the " +
  "attacker's request scores 0%. Watch confidence fall back to zero when " +
  "the permission runs out. Values are typical, meant to show shape and " +
  "order of magnitude.";

const NOTE_STANDARD =
  "Two rows carry the architecture. An implicit trust grant is access " +
  "given for position alone, for being inside, with no ruling on the " +
  "request. It stays at zero even at the breach step, where an attacker " +
  "holds a valid position inside the network, the position a perimeter " +
  "design defines as safe. And the verification count never stops " +
  "climbing: one check at the door is not this model. Confidence is the " +
  "policy engine's score for the current request: the grant was ruled at " +
  "88%, 72% had opened nothing, and the attacker's request scores 0%. " +
  "Watch it fall back to zero when the lease expires; trust here is " +
  "something you hold briefly, not something you have. Values are " +
  "typical, meant to show shape and order of magnitude.";

export function AccessCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: AccessState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const level = useLevel();
  const inside =
    state !== null && (state.phase === "breach" || state.phase === "contained");
  return (
    <div className="an-panel">
      <h2>Access</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>resources reachable</span>
        <span>
          {state
            ? `${state.resourcesReachable}${inside ? " — while inside" : ""}`
            : 0}
        </span>
      </div>
      <div className="stat">
        <span>implicit trust grants</span>
        <span>{state ? state.implicitTrustGrants : 0}</span>
      </div>
      <div className="stat">
        <span>confidence in this request</span>
        <span>{state ? `${state.trustScore}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>verifications so far</span>
        <span>{state ? state.verifications : 0}</span>
      </div>
      <div className="stat">
        <span>grant remaining</span>
        <span>
          {state && state.trustTtlSeconds > 0 ? `${state.trustTtlSeconds}s` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {level <= 2 ? NOTE_NOVICE : NOTE_STANDARD}
      </div>
    </div>
  );
}
