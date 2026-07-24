import type { DetectPhase, DetectState } from "../types";

const PHASE_LABEL: Record<DetectPhase, string> = {
  clean: "normal operations",
  intrusion: "intruder inside, dwelling",
  encrypt: "corruption spreading",
  blind: "detectors silent",
  inspect: "reading every byte",
  classify: "scoring each snapshot",
  verdict: "the answer, as a date",
  recover: "restoring the named copy",
  restored: "known-good baseline",
};

export function DetectCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: DetectState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const hidden =
    state !== null &&
    state.snapshotsCorrupted > 0 &&
    state.contentConfidencePercent === 0;
  return (
    <div className="an-panel">
      <h2>Incident</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>snapshots taken</span>
        <span>{state ? state.snapshotsTaken : 0}</span>
      </div>
      <div className="stat">
        <span>snapshots corrupted</span>
        <span>
          {state
            ? `${state.snapshotsCorrupted}${hidden ? " — nobody knows yet" : ""}`
            : 0}
        </span>
      </div>
      <div className="stat">
        <span>metadata alerts</span>
        <span>{state ? state.metadataAlerts : 0}</span>
      </div>
      <div className="stat">
        <span>content confidence</span>
        <span>
          {state
            ? state.contentConfidencePercent > 0
              ? `${state.contentConfidencePercent}%`
              : "—"
            : "—"}
        </span>
      </div>
      <div className="stat">
        <span>last clean copy</span>
        <span>
          {state && state.lastCleanSnapshot > 0
            ? `snapshot ${state.lastCleanSnapshot}`
            : "unknown"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? `t+${state.elapsedHours}h` : "t+0h"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Read the corrupted row against the alert row. Four snapshots are
        ruined and the metadata detectors have raised nothing — not because
        they are broken, but because the attack was shaped to keep them
        quiet: extensions preserved, entropy raised gradually, I/O inside
        the normal range. Everything watching a <em>description</em> of the
        data is satisfied while the data is destroyed. The last row is the
        deliverable, and note how long it stays unknown. Values are typical,
        meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
