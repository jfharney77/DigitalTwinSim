import type { ArrayConfig, ConfigPreset, Validation } from "../types";
import { DRIVE_TB_OPTIONS, MODEL_MAX_DRIVES, WRITE_PENALTY } from "../types";

// The build panel: array configuration with the validation results
// inline — a miniature of a storage sizing guide.

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

export function BuildPanel({
  config,
  presets,
  validations,
  onChange,
  onPreset,
}: {
  config: ArrayConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: ArrayConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<ArrayConfig>) => {
    const next = { ...config, ...patch };
    // Keep the drive count legal for the enclosure.
    next.driveCount = Math.min(next.driveCount, MODEL_MAX_DRIVES[next.model]);
    next.spares = Math.min(next.spares, Math.max(0, next.driveCount - 2));
    onChange(next);
  };
  const problems = validations.filter((v) => v.level !== "ok");

  return (
    <div className="an-panel">
      <h2>Build</h2>
      <div className="btnrow cfg-presets">
        {presets.map((p) => (
          <button key={p.id} title={p.blurb} onClick={() => onPreset(p)}>
            {p.name}
          </button>
        ))}
      </div>

      <Row label="Enclosure">
        <select
          value={config.model}
          onChange={(e) => set({ model: e.target.value as ArrayConfig["model"] })}
        >
          <option value="ME5012">ME5012 (12× 3.5″)</option>
          <option value="ME5024">ME5024 (24× 2.5″)</option>
        </select>
      </Row>
      <Row label="Drive type">
        <select
          value={config.driveType}
          onChange={(e) => set({ driveType: e.target.value as ArrayConfig["driveType"] })}
        >
          <option value="hdd-7.2k">7.2k NL-SAS HDD (~80 IOPS)</option>
          <option value="hdd-10k">10k SAS HDD (~170 IOPS)</option>
          <option value="ssd">SAS SSD (~20k IOPS)</option>
        </select>
      </Row>
      <Row label={`Drives (${config.driveCount})`}>
        <input
          type="range" min={2} max={MODEL_MAX_DRIVES[config.model]}
          value={config.driveCount}
          onChange={(e) => set({ driveCount: +e.target.value })}
        />
      </Row>
      <Row label="Drive size">
        <select value={config.driveTb} onChange={(e) => set({ driveTb: +e.target.value })}>
          {DRIVE_TB_OPTIONS.map((tb) => (
            <option key={tb} value={tb}>{tb} TB</option>
          ))}
        </select>
      </Row>
      <Row label="RAID level">
        <select
          value={config.raidLevel}
          onChange={(e) => set({ raidLevel: e.target.value as ArrayConfig["raidLevel"] })}
        >
          <option value="1">RAID 1 — mirror pair (write ×2)</option>
          <option value="10">RAID 10 — striped mirrors (write ×2)</option>
          <option value="5">RAID 5 — single parity (write ×4)</option>
          <option value="6">RAID 6 — dual parity (write ×6)</option>
        </select>
      </Row>
      <Row label={`Hot spares (${config.spares})`}>
        <input
          type="range" min={0} max={4} value={config.spares}
          onChange={(e) => set({ spares: +e.target.value })}
        />
      </Row>
      <Row label="Controllers">
        <select value={config.controllers} onChange={(e) => set({ controllers: +e.target.value })}>
          <option value={2}>2 — active-active (standard)</option>
          <option value={1}>1 — no failover partner</option>
        </select>
      </Row>
      <Row label="Host interface">
        <select
          value={config.hostInterface}
          onChange={(e) =>
            set({ hostInterface: e.target.value as ArrayConfig["hostInterface"] })
          }
        >
          <option value="iSCSI">25 GbE iSCSI</option>
          <option value="SAS">12 Gb SAS</option>
          <option value="FC">32 Gb Fibre Channel</option>
        </select>
      </Row>
      <div className="mini">
        Write penalty at this level: ×{WRITE_PENALTY[config.raidLevel]} disk
        I/Os per host write.
      </div>

      <h2 style={{ marginTop: 12 }}>Configuration rules</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ This build passes every rule.</div>
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
