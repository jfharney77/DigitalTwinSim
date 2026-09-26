import type { LifecyclePhase, LifecycleState } from "../types";

const PHASE_LABEL: Record<LifecyclePhase, string> = {
  idle: "estate humming",
  backup: "first backup",
  dedupe: "dedupe accumulating",
  replicate: "gap open — replicating",
  airgap: "gap closed — locked",
  scan: "CyberSense scanning",
  attack: "ransomware attack",
  recover: "recovering from vault",
  restored: "estate restored",
};

export function LifecycleCounters({
  state,
  stepIndex,
  stepCount,
  note,
}: {
  state: LifecycleState | null;
  stepIndex: number;
  stepCount: number;
  // The leveled note from the backend; the fallback is the level-3 text.
  note?: string;
}) {
  const ratio =
    state && state.storedTb > 0
      ? `${Math.round((state.logicalTb / state.storedTb) * 10) / 10}:1`
      : "—";
  const gapOpen =
    state !== null && state.activeRegions.includes("gap");
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
        <span>protected (logical)</span>
        <span>{state ? `${state.logicalTb} TB` : "0 TB"}</span>
      </div>
      <div className="stat">
        <span>stored (physical)</span>
        <span>{state ? `${state.storedTb} TB` : "0 TB"}</span>
      </div>
      <div className="stat">
        <span>dedupe ratio</span>
        <span>{ratio}</span>
      </div>
      <div className="stat">
        <span>air gap</span>
        <span>{state ? (gapOpen ? "OPEN" : "closed") : "—"}</span>
      </div>
      <div className="stat">
        <span>copies scanned / flagged</span>
        <span>
          {state && state.copiesScanned > 0
            ? `${state.copiesScanned} / ${state.copiesFlagged}`
            : "none yet"}
        </span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{state ? `t+${state.elapsedHours}h` : "t+0h"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {note ||
          "Logical is what the estate believes it has protected; physical is " +
            "the flash actually consumed. The gap between them is Data " +
            "Domain's deduplication. Watch the air gap row: it opens only " +
            "when the vault itself opens it, and it is closed when the attack " +
            "comes. Values are illustrative, meant to show shape and order of " +
            "magnitude."}
      </div>
    </div>
  );
}
