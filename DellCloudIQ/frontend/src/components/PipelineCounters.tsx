import type { PipelineState, PipelinePhase } from "../types";

const PHASE_LABEL: Record<PipelinePhase, string> = {
  idle: "idle — connected & healthy",
  collect: "collecting telemetry",
  transmit: "secure transmit",
  ingest: "cloud ingest",
  analyze: "ML analyzing",
  detect: "risk detected",
  surface: "insight surfaced",
  assist: "AIOps Assistant",
  notify: "notify & integrate",
};

export function PipelineCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: PipelineState | null;
  stepIndex: number;
  stepCount: number;
}) {
  // A tiny visual cue: healthy (>=90) reads as normal, a dip reads as an alert.
  const health = state?.healthScore ?? 100;
  const healthColor =
    health >= 90 ? undefined : health >= 75 ? "var(--core-hot)" : "var(--dell-error)";

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
        <span>pipeline progress</span>
        <span>{state ? `${state.progressPercent}%` : "0%"}</span>
      </div>
      <div className="stat">
        <span>health score</span>
        <span style={healthColor ? { color: healthColor } : undefined}>
          {state ? `${state.healthScore} / 100` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>telemetry points</span>
        <span>{state ? state.dataPoints.toLocaleString() : "0"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The Health Score is CloudIQ's signature metric — 100 when healthy, it
        drops when a risk is detected and recovers as remediation begins.
        Counts and timings are illustrative, not a measurement of your fleet.
      </div>
    </div>
  );
}
