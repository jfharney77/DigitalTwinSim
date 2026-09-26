import { useLevel } from "../level";
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
  const level = useLevel();
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
        <span>
          {state
            ? `${state.allreduceGbps.toLocaleString()} Gb/s (${(state.allreduceGbps / 1000).toFixed(1)} Tb/s)`
            : "0 Gb/s"}
        </span>
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
            ? `${state.stallMicrosPerSec.toLocaleString()} µs/s${stalling ? " — waiting" : ""}`
            : "0 µs/s"}
        </span>
      </div>
      <div className="stat">
        <span>sent without credit</span>
        <span>{state ? state.packetsSentWithoutCredit : 0}</span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {level <= 2 ? (
          <>
            Sent without credit is always zero: on this kind of network a
            sender cannot send until the receiver has promised it room, so
            the counter has nothing to count. The real cost shows in the
            sender stalls row. µs/s means millionths of a second spent
            waiting in each second, averaged over every sender, so 1,800
            µs/s is about two thousandths of each second. It is above zero
            only during the incast burst. Fabric traffic is all the data
            crossing the network. Effective all-reduce is how fast the
            training job gets its numbers added up, shown in Tb/s as well
            so you can compare the two rows. At the SHARP step traffic
            falls while all-reduce rises, because the switches start doing
            the adding. Values are illustrative, meant to show shape and
            rough size.
          </>
        ) : level === 3 ? (
          <>
            Sent-without-credit is zero by construction — InfiniBand's
            link layer cannot express it. The honest cost shows in the
            stall row instead: µs/s is microseconds of credit wait per
            second of running, averaged over every sender, so 1,800 µs/s
            is 0.18% of the time. Effective all-reduce is the rate at
            which the job sees gradient data reduced, summed across the
            whole job, which is why it can exceed any one port; it is
            shown in Tb/s too so it compares with fabric traffic. Watch
            the two cross at the SHARP step: fewer bytes moving, more work
            finishing, because the switches do the arithmetic. Values are
            illustrative: shape and order of magnitude only.
          </>
        ) : (
          <>
            Sent-without-credit: zero by construction, unexpressible at
            the link layer. Sender stalls: mean per-sender credit wait,
            µs per second of wall clock (1,800 µs/s = 0.18%); senders
            into the hot receiver wait far above the mean. Effective
            all-reduce: aggregate algorithm bandwidth across the job
            (payload reduced per second as the GPUs see it), not bus
            bandwidth and not a per-port figure. Fabric traffic: all
            bytes on leaf and spine links, collective plus everything
            else the job moves. The two cross at the SHARP step. Values
            are illustrative: shape and order of magnitude only.
          </>
        )}
      </div>
    </div>
  );
}
