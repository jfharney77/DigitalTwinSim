import type { ConfigPreset, DataConfig, Validation } from "../types";

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
  config: DataConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: DataConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<DataConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const p = config.product;

  return (
    <div className="an-panel">
      <h2>Build</h2>
      <div className="btnrow cfg-presets">
        {presets.map((pr) => (
          <button key={pr.id} title={pr.blurb} onClick={() => onPreset(pr)}>
            {pr.name}
          </button>
        ))}
      </div>

      <Row label="Product">
        <select
          value={p}
          onChange={(e) => set({ product: e.target.value as DataConfig["product"] })}
        >
          <option value="aidataplatform">AI Data Platform · pipeline</option>
          <option value="cloudiq">CloudIQ / AIOps · console</option>
        </select>
      </Row>
      {p === "aidataplatform" && (
        <>
          {(
            [
              ["Ingest", "ingestTbh"],
              ["Process", "processTbh"],
              ["Index", "indexTbh"],
              ["Serve", "serveTbh"],
            ] as const
          ).map(([label, key]) => (
            <Row key={key} label={`${label} (${config[key]} TB/h)`}>
              <input
                type="range" min={1} max={60} value={config[key]}
                onChange={(e) => set({ [key]: +e.target.value } as Partial<DataConfig>)}
              />
            </Row>
          ))}
          <Row label="GPU processing">
            <select
              value={config.gpuProcessing ? "on" : "off"}
              onChange={(e) => set({ gpuProcessing: e.target.value === "on" })}
            >
              <option value="off">Off</option>
              <option value="on">On (×6-class, labeled claim)</option>
            </select>
          </Row>
          <Row label="GPU analytics">
            <select
              value={config.gpuAnalytics ? "on" : "off"}
              onChange={(e) => set({ gpuAnalytics: e.target.value === "on" })}
            >
              <option value="off">Off</option>
              <option value="on">On (×6-class scan)</option>
            </select>
          </Row>
          <Row label="KV-cache offload">
            <select
              value={config.kvOffload ? "on" : "off"}
              onChange={(e) => set({ kvOffload: e.target.value === "on" })}
            >
              <option value="off">Off (GPU memory only)</option>
              <option value="on">On (×4 sessions, +12% token)</option>
            </select>
          </Row>
        </>
      )}
      {p === "cloudiq" && (
        <>
          <Row label={`Anomaly k (${config.anomalyK}σ)`}>
            <input
              type="range" min={1} max={6} step={0.5} value={config.anomalyK}
              onChange={(e) => set({ anomalyK: +e.target.value })}
            />
          </Row>
          {(
            [
              ["Weight: capacity", "weightCapacity"],
              ["Weight: performance", "weightPerformance"],
              ["Weight: config", "weightConfig"],
            ] as const
          ).map(([label, key]) => (
            <Row key={key} label={`${label} (${config[key]})`}>
              <input
                type="range" min={0} max={100} value={config[key]}
                onChange={(e) => set({ [key]: +e.target.value } as Partial<DataConfig>)}
              />
            </Row>
          ))}
        </>
      )}

      <h2 style={{ marginTop: 12 }}>Configuration rules</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ Nothing to warn about — yet.</div>
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
