import type { BringUpPhase, BringUpState } from "../types";

const PHASE_LABEL: Record<BringUpPhase, string> = {
  off: "off — no AC",
  standby: "standby power",
  reset: "SoC reset · root of trust",
  bootldr: "bootloader",
  kernel: "embedded Linux",
  services: "services + Lifecycle Controller",
  ready: "ready — watching",
};

export function BringUpCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: BringUpState | null;
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
        <span>
          {stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>init progress</span>
        <span>{state ? `${state.progressPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>BMC domain draw</span>
        <span>{state ? `${state.powerWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The host stays powered off throughout — this is the management
        controller booting itself. Watts and timings are typical values meant
        to show shape and order of magnitude, not a measurement of your box.
      </div>
    </div>
  );
}
