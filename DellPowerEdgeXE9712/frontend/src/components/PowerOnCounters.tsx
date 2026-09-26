import type { PowerOnPhase, PowerOnState } from "../types";

const PHASE_LABEL: Record<PowerOnPhase, string> = {
  off: "off — facility connected",
  power: "busbar energizing",
  coolant: "coolant loop priming",
  trayboot: "compute trays booting",
  gpuinit: "GPUs waking",
  fabric: "NVLink links training",
  fused: "domain fused — 72 GPUs, one domain",
  ready: "accepting jobs",
  flowfault: "branch failed verification",
  isolate: "tray held off, pulled to seal",
  repair: "tray under repair",
  reverify: "all branches re-verifying",
  leak: "leak under load — tray cut",
  traydown: "tray down, survivors idle",
  held: "held for service",
};

function fmtWatts(w: number): string {
  return w >= 10_000 ? `${Math.round(w / 100) / 10} kW` : `${w} W`;
}

export function PowerOnCounters({
  state,
  stepIndex,
  stepCount,
  fault = false,
}: {
  state: PowerOnState | null;
  stepIndex: number;
  stepCount: number;
  // The failure scenario shows the interlock's numbers beside the domain
  // counter; the nominal page reads exactly as it always has.
  fault?: boolean;
}) {
  const failed = (state?.failedRegions.length ?? 0) > 0;
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
        <span>rack power</span>
        <span>{state ? fmtWatts(state.powerWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>GPUs in NVLink domain</span>
        <span>{state ? `${state.gpusInDomain} / 72` : "0 / 72"}</span>
      </div>
      {fault && (
        <>
          <div className="stat">
            <span>GPUs powered</span>
            <span>{state ? `${state.gpusPowered} / 72` : "0 / 72"}</span>
          </div>
          <div className={failed ? "stat stat-fault" : "stat"}>
            <span>coolant branches verified</span>
            <span>{state ? `${state.branchesVerified} / 18` : "0 / 18"}</span>
          </div>
          <div className="stat">
            <span>hottest GPU (illustrative)</span>
            <span>{state ? `${state.gpuTempC} °C` : "—"}</span>
          </div>
        </>
      )}
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      {fault && (
        <div className="mini" style={{ marginTop: 8 }}>
          The number to watch is still the domain counter. It reads 0 or 72
          and nothing else. With one branch down, this site holds all 72
          GPUs off (its policy; the hardware could start 68). After the leak
          68 GPUs stay powered while the domain reads 0.
        </div>
      )}
      <div className="mini" style={{ marginTop: 8 }}>
        Watts are the whole rack — shelves, trays, fabric, and pumps. The
        domain counter is the rack's defining number: it stays at zero all
        through bring-up, then snaps to 72 the moment the NVLink fabric
        fuses. Values are illustrative, meant to show shape and order of
        magnitude — not a measurement of your rack.
      </div>
    </div>
  );
}
