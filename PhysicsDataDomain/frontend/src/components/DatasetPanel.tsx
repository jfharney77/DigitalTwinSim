import type {
  Appliance,
  Dataset,
  DatasetPreset,
  Schedule,
  Validation,
} from "../types";

// The scenario panel (left column): appliance choice, the dataset's own
// properties — the entire input to the machine — and the validation
// findings, which read like a miniature capacity-planning review.

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

export function DatasetPanel({
  appliances,
  applianceId,
  dataset,
  schedule,
  durationDays,
  presets,
  validations,
  onAppliance,
  onDataset,
  onSchedule,
  onDuration,
  onPreset,
}: {
  appliances: Appliance[];
  applianceId: string;
  dataset: Dataset;
  schedule: Schedule;
  durationDays: number;
  presets: DatasetPreset[];
  validations: Validation[];
  onAppliance: (id: Appliance["id"]) => void;
  onDataset: (d: Dataset) => void;
  onSchedule: (s: Schedule) => void;
  onDuration: (d: number) => void;
  onPreset: (p: DatasetPreset) => void;
}) {
  const problems = validations.filter((v) => v.level !== "ok");
  const appliance = appliances.find((a) => a.id === applianceId);

  return (
    <div className="an-panel">
      <h2>Dataset &amp; appliance</h2>
      <div className="btnrow cfg-presets">
        {presets.map((p) => (
          <button key={p.id} title={p.blurb} onClick={() => onPreset(p)}>
            {p.name}
          </button>
        ))}
      </div>

      <Row label="Appliance">
        <select
          value={applianceId}
          onChange={(e) => onAppliance(e.target.value as Appliance["id"])}
        >
          {appliances.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </Row>
      {appliance && (
        <div className="mini">
          {appliance.usableTb.toFixed(0)} TB usable ·{" "}
          {appliance.indexRamGb.toFixed(0)} GB index RAM ·{" "}
          {appliance.baseIngestGbps.toFixed(0)} GB/s rated
          {appliance.estimated ? " · figures include estimates" : ""}
        </div>
      )}

      <Row label={`Full backup (${dataset.fullTb} TB)`}>
        <input
          type="range" min={1} max={500} step={1}
          value={dataset.fullTb}
          onChange={(e) => onDataset({ ...dataset, fullTb: +e.target.value })}
        />
      </Row>
      <Row label={`Daily change (${dataset.dailyChangePct}%)`}>
        <input
          type="range" min={0} max={25} step={0.5}
          value={dataset.dailyChangePct}
          onChange={(e) =>
            onDataset({ ...dataset, dailyChangePct: +e.target.value })
          }
        />
      </Row>
      <Row label={`Entropy (${dataset.entropyPct})`}>
        <input
          type="range" min={0} max={100} step={5}
          value={dataset.entropyPct}
          onChange={(e) => onDataset({ ...dataset, entropyPct: +e.target.value })}
        />
      </Row>
      <div className="mini">
        Entropy: 0 is text-like, 100 is encrypted/random. It sets local
        compression; only session-keyed encryption (the event buttons) also
        kills cross-generation dedupe.
      </div>
      <Row label={`Retention (${schedule.retentionDays} gens)`}>
        <input
          type="range" min={1} max={365} step={1}
          value={schedule.retentionDays}
          onChange={(e) => onSchedule({ retentionDays: +e.target.value })}
        />
      </Row>
      <Row label={`Run length (${durationDays} days)`}>
        <input
          type="range" min={10} max={365} step={5}
          value={durationDays}
          onChange={(e) => onDuration(+e.target.value)}
        />
      </Row>

      <h2 style={{ marginTop: 12 }}>Planning review</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ This plan passes every rule.</div>
      )}
      {problems.map((v) => (
        <div key={v.ruleId} className={`mini rule-${v.level}`} title={v.source}>
          {v.level === "error" ? "✕ " : "△ "}
          {v.message}
        </div>
      ))}
    </div>
  );
}
