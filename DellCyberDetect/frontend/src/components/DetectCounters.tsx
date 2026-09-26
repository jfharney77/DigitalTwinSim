import { emph } from "./Emph";
import type { DetectPhase, DetectState, ScenarioInfo } from "../types";

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

const SOURCE_LABEL: Record<DetectState["recoverySource"], string> = {
  "": "—",
  "array-snapshot": "snapshot on this array",
  "powerprotect-vault": "PowerProtect vault (off-array)",
};

export function DetectCounters({
  state,
  stepIndex,
  stepCount,
  snapshotLabels = [],
  scenario = null,
}: {
  state: DetectState | null;
  stepIndex: number;
  stepCount: number;
  // Timeline labels, oldest first, so the named copy reads the same here
  // as on the map ("snapshot 3" is the block drawn as "3 · T-4").
  snapshotLabels?: string[];
  // The selected scenario; a failure scenario swaps in its own hero row.
  scenario?: ScenarioInfo | null;
}) {
  const failure = scenario !== null && scenario.id !== "baseline";
  const noCleanCopy = state?.verdict === "no-clean-copy-on-array";
  const retained = state ? state.snapshotsTaken - state.snapshotsExpired : 0;
  const cleanOnArray = state ? retained - state.snapshotsCorrupted : 0;
  const recovering = state !== null && state.recoverySource !== "";
  const hidden =
    state !== null &&
    state.snapshotsCorrupted > 0 &&
    state.contentConfidencePercent === 0;
  return (
    <div className="an-panel">
      <h2>Incident</h2>
      <div className="stat">
        <span>phase</span>
        <span>
          {!state
            ? "—"
            : noCleanCopy && state.phase === "verdict"
              ? "the answer: no clean copy here"
              : noCleanCopy && state.phase === "recover"
                ? "restoring from the vault"
                : PHASE_LABEL[state.phase]}
        </span>
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
      {failure && (
        <>
          {/* Most of these have expired on the retention schedule; at the
              end of the incident the corrupted set is exported for
              forensics and removed, which is not retention doing it — so
              the row counts copies gone, and does not claim a reason. */}
          <div className="stat">
            <span>no longer on the array</span>
            <span>{state ? state.snapshotsExpired : 0}</span>
          </div>
          <div className="stat">
            <span>copies on the array now</span>
            <span>{state ? retained : 0}</span>
          </div>
          <div className="stat">
            <span>{scenario?.heroLabel ?? "clean copies on the array"}</span>
            <span style={cleanOnArray === 0 ? { color: "var(--core-hot)" } : undefined}>
              {state
                ? `${cleanOnArray}${hidden ? " — nobody knows yet" : ""}`
                : "—"}
            </span>
          </div>
        </>
      )}
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
        <span
          style={
            noCleanCopy && cleanOnArray === 0
              ? { color: "var(--core-hot)" }
              : undefined
          }
        >
          {noCleanCopy && cleanOnArray > 0
            ? "none was found; new baseline checked"
            : noCleanCopy
            ? "none on this array"
            : state && state.lastCleanSnapshot > 0
            ? `snapshot ${state.lastCleanSnapshot}${
                snapshotLabels[state.lastCleanSnapshot - 1]
                  ? ` (box ${snapshotLabels[state.lastCleanSnapshot - 1]})`
                  : ""
              }${
                state.lastCleanTakenAtHours !== null &&
                state.lastCleanTakenAtHours !== undefined
                  ? `, taken t+${state.lastCleanTakenAtHours}h`
                  : ""
              }`
            : "unknown"}
        </span>
      </div>
      {/* Always drawn, so the notes below never point at a missing row;
          both read "—" until the recovery step fills them in. */}
      <div className="stat">
        <span>recovery source</span>
        <span>{state ? SOURCE_LABEL[state.recoverySource] : "—"}</span>
      </div>
      <div className="stat">
        <span>restored data age (illustrative)</span>
        <span>
          {recovering && state ? `${state.recoveryPointAgeHours}h` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedHours}h` : "t+0h"}</span>
      </div>
      {scenario?.countersNote && (
        <div className="mini" style={{ marginTop: 8 }}>
          {emph(scenario.countersNote)}
        </div>
      )}
    </div>
  );
}
