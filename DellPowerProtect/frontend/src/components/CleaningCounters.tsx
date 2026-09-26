import type { CleaningPhase, ScenarioInfo, TraceState } from "../types";

const PHASE_LABEL: Record<CleaningPhase, string> = {
  steady: "steady, 80% full",
  expire: "retention expiring",
  ingest: "backups landing",
  alert: "space alert",
  clean: "cleaning running",
  pinned: "finding what holds space",
  release: "releasing references",
  reclean: "second clean",
  settled: "steady again",
};

// Telemetry for the cleaning (garbage collection) scenario. The hero pair is
// what cleaning has returned against what the appliance estimated it would.
export function CleaningCounters({
  state,
  stepIndex,
  stepCount,
  scenario,
}: {
  state: TraceState | null;
  stepIndex: number;
  stepCount: number;
  scenario: ScenarioInfo | null;
}) {
  const s = state;
  const cap = s?.capacityTb ?? 0;
  const usedPct = s && cap > 0 ? Math.round((s.storedTb / cap) * 100) : null;
  // Two different causes, kept apart on purpose. Replication lag and a stale
  // snapshot hold space the catalog has expired; Retention Lock refused the
  // delete, so that space was never expired and never cleanable.
  const heldByRefs = s
    ? (s.heldByReplicationTb ?? 0) + (s.heldBySnapshotTb ?? 0)
    : 0;
  const alert = (s?.alerts ?? []).length > 0;
  return (
    <div className="an-panel">
      <h2>Telemetry</h2>
      <div className="stat">
        <span>phase</span>
        <span>{s ? PHASE_LABEL[s.phase as CleaningPhase] ?? s.phase : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>protected (logical)</span>
        <span>{s ? `${s.logicalTb} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>stored (physical)</span>
        <span className={alert ? "stat-failed" : undefined}>
          {s && usedPct !== null ? `${s.storedTb}/${cap} TB · ${usedPct}%` : "—"}
        </span>
      </div>
      <div className="stat hero-stat">
        <span>reclaimed by cleaning</span>
        <span>{s ? `${s.reclaimedTb ?? 0} TB` : "—"}</span>
      </div>
      <div className="stat hero-stat">
        <span>cleanable (estimate)</span>
        <span>{s ? `${s.cleanableTb ?? 0} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>really reclaimable</span>
        <span>{s ? `${s.reclaimableTb ?? 0} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>held by references</span>
        <span>{s ? `${heldByRefs} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>held by replication lag</span>
        <span>{s ? `${s.heldByReplicationTb ?? 0} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>held by a snapshot</span>
        <span>{s ? `${s.heldBySnapshotTb ?? 0} TB` : "—"}</span>
      </div>
      <div className="stat">
        <span>held by Retention Lock</span>
        <span>
          {s
            ? `${s.heldByLockTb ?? 0} TB${
                (s.heldByLockTb ?? 0) > 0 ? ` · ${s.lockDaysLeft} days left` : ""
              }`
            : "—"}
        </span>
      </div>
      <div className="stat">
        <span>cleaning</span>
        <span>{s ? (s.cleanRunning ? "RUNNING" : "idle") : "—"}</span>
      </div>
      <div className="stat">
        <span>elapsed (illustrative)</span>
        <span>{s ? `t+${s.elapsedHours}h` : "—"}</span>
      </div>
      {(s?.alerts ?? []).map((a) => (
        <div key={a} className="mini an-alert" role="status">
          {a}
        </div>
      ))}
      <div className="mini" style={{ marginTop: 8 }}>
        Stored falls only while cleaning runs. Expiry lowers the logical
        figure and nothing else. Space held by references ({heldByRefs} TB now)
        is expired in the backup catalog but still referenced on the appliance,
        so cleaning skips it. Space under Retention Lock is a separate case: the
        delete was refused, so those terabytes are not expired and were never in
        the cleanable estimate. Terabytes, hours, lock days and the 95% alert
        threshold are
        illustrative; the alert wording, the weekly default schedule and the
        three causes come from Dell's support articles.
      </div>
      {scenario && scenario.sources.length > 0 && (
        <div className="an-sources" style={{ marginTop: 8 }}>
          {scenario.sources.map((src) => (
            <a key={src.url} href={src.url} target="_blank" rel="noreferrer">
              {src.label}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
