import { useLevel } from "../level";
import type { InferencePhase, InferenceState } from "../types";

const PHASE_LABEL: Record<InferencePhase, string> = {
  off: "off — model on disk",
  compile: "compiling, ahead of time",
  load: "loading weights over PCIe",
  resident: "resident — bus quiet",
  prefill: "prefill — reading the prompt",
  decode: "decode — generating",
  sustained: "sustained generation",
  offline: "network disconnected",
};

export function InferenceCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: InferenceState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const level = useLevel();
  const busy = state !== null && state.linkGbps > 0;
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
        <span>weights resident</span>
        <span>{state ? `${state.weightsResidentGb} GB / 64 GB` : "0 GB / 64 GB"}</span>
      </div>
      <div className="stat">
        <span>PCIe traffic</span>
        <span>
          {state ? `${state.linkGbps} Gb/s${busy ? " — loading" : ""}` : "0 Gb/s"}
        </span>
      </div>
      <div className="stat">
        <span>generation rate</span>
        <span>{state ? `${state.tokensPerSecond} tok/s` : "0 tok/s"}</span>
      </div>
      <div className="stat">
        <span>card power</span>
        <span>{state ? `${state.npuWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {level <= 2 ? (
          <>
            Watch two rows together. The PCIe row, the traffic on the
            connector between laptop and card, jumps once while the model
            loads and reads zero for every step where the model is
            answering: the model's learned numbers, called weights, are
            already on the card, so there is nothing left to send.
            Meanwhile the resident row climbs to 61 GB and never falls
            again. No part of the model is ever pushed out of the card's
            memory to make room, so no word ever waits for a piece to be
            fetched back. The only slow drift comes from the record of the
            conversation growing as it gets longer. Values are
            illustrative, meant to show shape and rough size, not
            measurements.
          </>
        ) : level >= 4 ? (
          <>
            PCIe is nonzero during load only. Resident climbs to 61 GB and
            never falls: no eviction, so no token waits on a page-in; the
            only latency drift is KV-cache growth with context. Values are
            illustrative.
          </>
        ) : (
          <>
            Watch two rows together. The PCIe row spikes once, during load,
            and reads zero for every step of actual inference — the weights
            are already on the far side of the boundary, so there is
            nothing left to transfer. Meanwhile the resident row climbs to
            61 GB and never falls again: nothing is paged out (moved out of
            the card's memory to make room), so no token ever waits on a
            page-in; the only drift is the KV cache, the record of the
            conversation, growing with context. Values are illustrative,
            meant to show shape and order of magnitude.
          </>
        )}
      </div>
    </div>
  );
}
