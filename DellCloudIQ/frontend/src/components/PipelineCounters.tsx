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
  register: "registered, no data yet",
  handshake: "gateway test passed",
  blocked: "upload refused at proxy",
  starved: "cloud receiving nothing",
  stale: "listed: not sending data",
  repair: "egress being fixed",
  backfill: "backlog delivered",
  resume: "first real score",
};

export function PipelineCounters({
  state,
  stepIndex,
  stepCount,
  failing = false,
  note = "",
}: {
  // The scenario's panel note, leveled by the backend.
  note?: string;
  // True while a failure scenario is playing: its hero counters are shown.
  failing?: boolean;
  state: PipelineState | null;
  stepIndex: number;
  stepCount: number;
}) {
  // A tiny visual cue: healthy (>=90) reads as normal, a dip reads as an alert.
  const health = state?.healthScore ?? 100;
  // No data means no score: the product draws a grey dash, and so does this.
  const noData = state?.scoreState === "no-data";
  const healthColor = noData
    ? "var(--dell-muted)"
    : health >= 90
      ? undefined
      : health >= 75
        ? "var(--core-hot)"
        : "var(--dell-error)";
  const silent = (state?.minutesWithoutData ?? 0) > 0;

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
          {!state ? "—" : noData ? "— no data" : `${state.healthScore} / 100`}
        </span>
      </div>
      {failing && (
        <>
          <div className="stat hero-stat">
            <span>minutes without data</span>
            <span style={silent ? { color: "var(--dell-error)" } : undefined}>
              {state ? state.minutesWithoutData : 0}
            </span>
          </div>
          <div className="stat">
            <span>waiting on site</span>
            <span>{state ? state.backlogPoints.toLocaleString() : "0"}</span>
          </div>
        </>
      )}
      <div className="stat">
        <span>{failing ? "delivered to cloud" : "telemetry points"}</span>
        <span>{state ? state.dataPoints.toLocaleString() : "0"}</span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedSeconds}s` : "t+0s"}</span>
      </div>
      {note && (
        <div className="mini" style={{ marginTop: 8 }}>
          {note}
        </div>
      )}
    </div>
  );
}
