import type { PowerOnPhase, PowerOnState } from "../types";

const PHASE_LABEL: Record<PowerOnPhase, string> = {
  off: "off — racked and cabled",
  power: "PSUs energizing",
  post: "host POST",
  gpuinit: "GPUs waking",
  fuse: "NVSwitch fusing — one domain",
  fabric: "NICs training",
  ready: "accepting jobs",
};

function fmtWatts(w: number): string {
  return w >= 10_000 ? `${Math.round(w / 100) / 10} kW` : `${w} W`;
}

export function PowerOnCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: PowerOnState | null;
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
        <span>server power</span>
        <span>{state ? fmtWatts(state.powerWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>GPUs in NVLink domain</span>
        <span>{state ? `${state.gpusInDomain} / 8` : "0 / 8"}</span>
      </div>
      <div className="stat">
        <span>NICs on the fabric</span>
        <span>{state ? `${state.nicsUp} / 8` : "0 / 8"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts are the whole box — host, GPUs, fans, and NICs. The two
        eight-counters are the architecture: the NVLink domain snaps 0 → 8
        at the fuse and never grows past the chassis wall, and then one NIC
        per GPU joins the fabric that scales past it. Values are typical,
        meant to show shape and order of magnitude — not a measurement of
        your server.
      </div>
    </div>
  );
}
