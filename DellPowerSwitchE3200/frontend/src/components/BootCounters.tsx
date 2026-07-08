import type { BootPhase, BootState } from "../types";

const PHASE_LABEL: Record<BootPhase, string> = {
  off: "off — AC only",
  standby: "standby power",
  poweron: "power-on · CPU · fans",
  onie: "ONIE bootloader",
  nos: "network OS booting",
  dataplane: "programming the ASIC",
  ports: "ports & PoE",
  forwarding: "forwarding traffic",
};

export function BootCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: BootState | null;
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
        <span>total draw (incl. PoE)</span>
        <span>{state ? `${state.powerWatts} W` : "0 W"}</span>
      </div>
      <div className="stat">
        <span>fan speed</span>
        <span>{state ? `${state.fanPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>forwarding</span>
        <span>{state ? `${state.dataRateGbps} Gbps` : "0 Gbps"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Watts and timings are typical values meant to show shape and order of
        magnitude, not a measurement of your switch. Most of the wattage is the
        PoE budget handed to attached devices, so total draw jumps when PoE
        powers up.
      </div>
    </div>
  );
}
