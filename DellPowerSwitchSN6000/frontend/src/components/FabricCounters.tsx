import type { FabricPhase, FabricState } from "../types";

const PHASE_LABEL: Record<FabricPhase, string> = {
  off: "off — cabled, dark",
  power: "switches booting",
  linktrain: "links training",
  topology: "routing converging",
  ready: "fabric ready",
  collective: "all-reduce running",
  congestion: "incast — buffers filling",
  reroute: "adaptive routing",
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
        <span>fabric throughput</span>
        <span>{state ? `${state.fabricTbps} Tb/s` : "0 Tb/s"}</span>
      </div>
      <div className="stat">
        <span>busiest link</span>
        <span>
          {state ? `${state.peakLinkPercent}%${hot ? " — saturated" : ""}` : "0%"}
        </span>
      </div>
      <div className="stat">
        <span>dropped packets</span>
        <span>{state ? state.droppedPackets : 0}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The dropped-packet row is the whole product claim, so watch it during
        the congestion step: the busiest link hits 98% and the counter still
        reads zero. Ordinary Ethernet would be discarding frames there, and
        every retransmission would stall not one flow but every GPU in the
        job. Values are typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
