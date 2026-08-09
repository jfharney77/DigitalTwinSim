import type { CduConfig, ConfigPreset, Validation } from "../types";

// The build panel: CDU configuration with the validation results inline
// — the miniature liquid-cooling site-readiness checklist.

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

export function ControlPanel({
  config,
  presets,
  validations,
  onChange,
  onPreset,
}: {
  config: CduConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: CduConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<CduConfig>) => onChange({ ...config, ...patch });
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

      <Row label="Tray banks (~40 kW each)">
        <select
          value={config.trayGroups}
          onChange={(e) => set({ trayGroups: +e.target.value })}
        >
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <option key={n} value={n}>
              {n} — ≈{n * 40} kW
            </option>
          ))}
        </select>
      </Row>

      <Row label="Pumps">
        <select value={config.pumps} onChange={(e) => set({ pumps: +e.target.value })}>
          <option value={2}>2 (N — no spare)</option>
          <option value={3}>3 (N+1)</option>
        </select>
      </Row>

      <Row label={`Flow setpoint ${config.flowSetpointLpm} L/min`}>
        <input
          type="range" min={200} max={400} step={10}
          value={config.flowSetpointLpm}
          onChange={(e) => set({ flowSetpointLpm: +e.target.value })}
        />
      </Row>

      <Row label={`Min supply ${config.minSupplyC} °C`}>
        <input
          type="range" min={15} max={45}
          value={config.minSupplyC}
          onChange={(e) => set({ minSupplyC: +e.target.value })}
        />
      </Row>

      <Row label="IRC policy">
        <select
          value={config.policy}
          onChange={(e) =>
            set({ policy: e.target.value as CduConfig["policy"] })
          }
        >
          <option value="coordinated">Coordinated (IRC caps, together)</option>
          <option value="uncoordinated">Uncoordinated (every tray for itself)</option>
        </select>
      </Row>

      <div className="rules">
        {problems.length === 0 && (
          <div className="mini rule-ok">✓ Configuration passes every rule.</div>
        )}
        {problems.map((v) => (
          <div
            key={v.ruleId}
            className={`mini ${v.level === "error" ? "rule-error" : "rule-warning"}`}
            title={v.source}
          >
            {v.level === "error" ? "■" : "▲"} {v.message}
          </div>
        ))}
      </div>
    </div>
  );
}
