import type { FabricPhase, FabricState } from "../types";

const PHASE_LABEL: Record<FabricPhase, string> = {
  off: "off — cabled, dark",
  power: "switches booting",
  discover: "SM sweeping the fabric",
  routes: "routes computing centrally",
  credits: "credits arming",
  ready: "fabric ready — SM aside",
  collective: "all-reduce running",
  sharp: "SHARP — switches computing",
  burst: "incast — senders waiting",
  steady: "steady state",
};

export function FabricCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: FabricState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const hot = state !== null && state.peakLinkPercent >= 90;
  const stalling = state !== null && state.stallMicrosPerSec > 0;
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
        <span>fabric traffic</span>
        <span>{state ? `${state.fabricTbps} Tb/s` : "0 Tb/s"}</span>
      </div>
      <div className="stat">
        <span>effective all-reduce</span>
        <span>{state ? `${state.allreduceGbps} Gb/s` : "0 Gb/s"}</span>
      </div>
      <div className="stat">
        <span>busiest link</span>
        <span>
          {state ? `${state.peakLinkPercent}%${hot ? " — saturated" : ""}` : "0%"}
        </span>
      </div>
      <div className="stat">
        <span>sender stalls</span>
        <span>
          {state
            ? `${state.stallMicrosPerSec} µs/s${stalling ? " — waiting" : ""}`
            : "0 µs/s"}
        </span>
      </div>
      <div className="stat">
        <span>sent without credit</span>
        <span>{state ? state.packetsSentWithoutCredit : 0}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Sent-without-credit is zero by construction — InfiniBand's link
        layer cannot express it. The honest cost shows in the stall row
        instead: under the incast burst, senders wait microseconds rather
        than lose anything. And watch traffic versus all-reduce cross at
        the SHARP step: fewer bytes moving, more work finishing, because
        the switches do the arithmetic. Values are typical, meant to show
        shape and order of magnitude.
      </div>
    </div>
  );
}
