import type { ConfigPreset, ResilienceConfig, Validation } from "../types";

const PRODUCT_LABEL: Record<ResilienceConfig["product"], string> = {
  powerprotect: "PowerProtect · vault",
  cyberdetect: "Cyber Detect · detection",
  mdr: "MDR · response",
  fortzero: "Fort Zero · access graph",
};

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
  config: ResilienceConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: ResilienceConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<ResilienceConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const p = config.product;

  return (
    <div className="an-panel">
      <h2>Architecture</h2>
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
          onChange={(e) => set({ product: e.target.value as ResilienceConfig["product"] })}
        >
          {Object.entries(PRODUCT_LABEL).map(([id, label]) => (
            <option key={id} value={id}>{label}</option>
          ))}
        </select>
      </Row>
      {p !== "fortzero" && (
        <>
          <Row label={`Estate (${config.estateTb} TB)`}>
            <input
              type="range" min={10} max={1000} step={10} value={config.estateTb}
              onChange={(e) => set({ estateTb: +e.target.value })}
            />
          </Row>
          <Row label={`Backup every (${config.backupEveryH} h)`}>
            <input
              type="range" min={1} max={168} value={config.backupEveryH}
              onChange={(e) => set({ backupEveryH: +e.target.value })}
            />
          </Row>
          <Row label={`Retention (${config.retentionCopies} copies)`}>
            <input
              type="range" min={1} max={90} value={config.retentionCopies}
              onChange={(e) => set({ retentionCopies: +e.target.value })}
            />
          </Row>
          <Row label="Cyber Vault">
            <select
              value={config.vault ? "on" : "off"}
              onChange={(e) => set({ vault: e.target.value === "on" })}
            >
              <option value="on">On (air-gapped, locked)</option>
              <option value="off">Repository only</option>
            </select>
          </Row>
          <Row label={`Restore pipe (${config.restoreGbps} GB/s)`}>
            <input
              type="range" min={0.5} max={8} step={0.5} value={config.restoreGbps}
              onChange={(e) => set({ restoreGbps: +e.target.value })}
            />
          </Row>
          <Row label="Detection">
            <select
              value={config.detection || p === "cyberdetect" ? "on" : "off"}
              onChange={(e) => set({ detection: e.target.value === "on" })}
            >
              <option value="on">Content analysis on</option>
              <option value="off">Off (restore-and-pray)</option>
            </select>
          </Row>
          <Row label={`Sensitivity (${config.sensitivity})`}>
            <input
              type="range" min={1} max={10} value={config.sensitivity}
              onChange={(e) => set({ sensitivity: +e.target.value })}
            />
          </Row>
        </>
      )}
      {p === "mdr" && (
        <>
          <Row label="Response model">
            <select
              value={config.response}
              onChange={(e) => set({ response: e.target.value as ResilienceConfig["response"] })}
            >
              <option value="inhouse">In-house (business hours)</option>
              <option value="mdr">MDR (24/7)</option>
            </select>
          </Row>
          <Row label={`Noise (${config.noiseAlertsDay}/day)`}>
            <input
              type="range" min={0} max={500} step={10} value={config.noiseAlertsDay}
              onChange={(e) => set({ noiseAlertsDay: +e.target.value })}
            />
          </Row>
        </>
      )}
      {p === "fortzero" && (
        <>
          <Row label="Architecture">
            <select
              value={config.architecture}
              onChange={(e) => set({ architecture: e.target.value as ResilienceConfig["architecture"] })}
            >
              <option value="perimeter">Perimeter (inside = trusted)</option>
              <option value="zerotrust">Zero trust (verify each edge)</option>
            </select>
          </Row>
          <Row label={`Assets (${config.assets})`}>
            <input
              type="range" min={20} max={300} step={10} value={config.assets}
              onChange={(e) => set({ assets: +e.target.value })}
            />
          </Row>
          <Row label={`Segments (${config.microsegSegments})`}>
            <input
              type="range" min={1} max={20} value={config.microsegSegments}
              onChange={(e) => set({ microsegSegments: +e.target.value })}
            />
          </Row>
          <Row label={`Review every (${config.reviewCadenceDays || "never"} d)`}>
            <input
              type="range" min={0} max={180} step={30} value={config.reviewCadenceDays}
              onChange={(e) => set({ reviewCadenceDays: +e.target.value })}
            />
          </Row>
        </>
      )}

      <h2 style={{ marginTop: 12 }}>Architecture rules</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ This architecture passes every rule.</div>
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
