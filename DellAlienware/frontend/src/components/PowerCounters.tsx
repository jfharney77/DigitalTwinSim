import type { ChargeStage, PowerState, Regime, Summary } from "../types";

const CHARGE_STAGE_LABEL: Record<ChargeStage, string> = {
  idle: "idle (not charging)",
  precharge: "precharge (gentle)",
  cc: "constant current",
  cv: "constant voltage taper",
  full: "full — hold band",
};

const REGIME_LABEL: Record<Regime, string> = {
  "adapter-limited": "adapter-limited (hybrid power used)",
  "within-budget": "within adapter budget",
  throttled: "throttled (adapter not recognized)",
};

function w(v: number | undefined): string {
  return v === undefined ? "—" : `${Math.round(v * 10) / 10} W`;
}

export function PowerCounters({
  state,
  summary,
  stepIndex,
  stepCount,
}: {
  state: PowerState | null;
  summary: Summary | null;
  stepIndex: number;
  stepCount: number;
}) {
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>AC draw</span>
        <span>{w(state?.acW)}</span>
      </div>
      <div className="stat">
        <span>system (CPU+GPU+rest)</span>
        <span>{w(state?.systemW)}</span>
      </div>
      <div className="stat">
        <span>charging into battery</span>
        <span>{w(state?.chargeW)}</span>
      </div>
      <div className="stat">
        <span>battery supplement</span>
        <span>
          {state?.hybrid ? `${w(state?.batteryW)} (hybrid)` : w(state?.batteryW)}
        </span>
      </div>
      <div className="stat">
        <span>battery level</span>
        <span>{state ? `${Math.round(state.batteryPct * 10) / 10}%` : "—"}</span>
      </div>
      <div className="stat">
        <span>charge stage</span>
        <span>{state ? CHARGE_STAGE_LABEL[state.chargeStage] : "—"}</span>
      </div>
      <div className="stat">
        <span>CPU package</span>
        <span>{w(state?.cpuW)}</span>
      </div>
      <div className="stat">
        <span>GPU package</span>
        <span>{w(state?.gpuW)}</span>
      </div>
      <div className="stat">
        <span>fans</span>
        <span>{state ? `${Math.round(state.fanPct)}%` : "—"}</span>
      </div>

      {summary && (
        <>
          <h2 style={{ marginTop: 16 }}>Summary</h2>
          <div className="stat">
            <span>regime</span>
            <span>{REGIME_LABEL[summary.regime]}</span>
          </div>
          <div className="stat">
            <span>adapter rating</span>
            <span>{summary.adapterW} W</span>
          </div>
          <div className="stat">
            <span>peak system draw</span>
            <span>{w(summary.peakSystemW)}</span>
          </div>
          <div className="stat">
            <span>peak hybrid supplement</span>
            <span>{summary.hybridUsed ? w(summary.peakHybridW) : "not used"}</span>
          </div>
          <div className="stat">
            <span>battery at end</span>
            <span>{Math.round(summary.endBatteryPct * 10) / 10}%</span>
          </div>
          <div className="stat">
            <span>time to 80%</span>
            <span>
              {summary.minutesTo80Pct === null
                ? "not charging"
                : `≈${Math.round(summary.minutesTo80Pct)} min`}
            </span>
          </div>
          {summary.notes.length > 0 && (
            <ul className="notes">
              {summary.notes.map((n, i) => (
                <li className="mini" key={i}>
                  {n}
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      <div className="mini" style={{ marginTop: 8 }}>
        Watts and timings show shape and order of magnitude for this
        configuration — illustrative, not a measurement of your machine.
      </div>
    </div>
  );
}
