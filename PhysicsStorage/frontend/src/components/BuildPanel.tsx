import type { ConfigPreset, StorageConfig, Validation } from "../types";

const PRODUCT_LABEL: Record<StorageConfig["product"], string> = {
  powerstore: "PowerStore · dual-controller",
  powermax: "PowerMax · enterprise",
  powerscale: "PowerScale · scale-out NAS",
  objectscale: "ObjectScale · S3 object",
  powerflex: "PowerFlex · SDS block",
  exascale: "Exascale · AI meta-sim",
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
  config: StorageConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: StorageConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<StorageConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const p = config.product;
  const scaleOut = p === "powerscale" || p === "objectscale" || p === "powerflex" || p === "exascale";

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
          onChange={(e) => set({ product: e.target.value as StorageConfig["product"] })}
        >
          {Object.entries(PRODUCT_LABEL).map(([id, label]) => (
            <option key={id} value={id}>{label}</option>
          ))}
        </select>
      </Row>
      <Row label={`${scaleOut ? "Nodes" : p === "powermax" ? "Bricks" : "Appliances"} (${config.units})`}>
        <input
          type="range" min={1} max={scaleOut ? 60 : 8} value={config.units}
          onChange={(e) => set({ units: +e.target.value })}
        />
      </Row>
      <Row label={`Drives/unit (${config.drivesPerUnit})`}>
        <input
          type="range" min={2} max={24} value={config.drivesPerUnit}
          onChange={(e) => set({ drivesPerUnit: +e.target.value })}
        />
      </Row>
      <Row label="Drive">
        <select
          value={`${config.driveClass}/${config.driveTb}`}
          onChange={(e) => {
            const [cls, tb] = e.target.value.split("/");
            set({ driveClass: cls as StorageConfig["driveClass"], driveTb: +tb });
          }}
        >
          <option value="nvme/7.68">NVMe 7.68 TB</option>
          <option value="nvme/15.36">NVMe 15.36 TB</option>
          <option value="nvme/30.72">NVMe 30.72 TB</option>
          <option value="ssd/7.68">SSD 7.68 TB</option>
          <option value="hdd/20">HDD 20 TB</option>
        </select>
      </Row>
      <Row label="Protection">
        <select
          value={config.protection}
          onChange={(e) => set({ protection: e.target.value as StorageConfig["protection"] })}
        >
          <option value="raid5">RAID 5 (survives 1)</option>
          <option value="raid6">RAID 6 (survives 2)</option>
          <option value="mirror">Mirror (survives 1)</option>
          <option value="ec8+2">EC 8+2 (survives 2)</option>
          <option value="ec16+4">EC 16+4 (survives 4)</option>
        </select>
      </Row>
      {p === "powerflex" && (
        <Row label="Node NICs">
          <select value={config.nicGbps} onChange={(e) => set({ nicGbps: +e.target.value })}>
            {[10, 25, 100].map((g) => (
              <option key={g} value={g}>{g} GbE</option>
            ))}
          </select>
        </Row>
      )}
      {p === "powermax" && (
        <>
          <Row label="SRDF">
            <select
              value={config.srdf}
              onChange={(e) => set({ srdf: e.target.value as StorageConfig["srdf"] })}
            >
              <option value="off">Off</option>
              <option value="sync">Sync (zero RPO)</option>
              <option value="async">Async (RPO gauge)</option>
            </select>
          </Row>
          {config.srdf === "sync" && (
            <Row label={`Distance (${config.distanceKm} km)`}>
              <input
                type="range" min={0} max={1000} step={25} value={config.distanceKm}
                onChange={(e) => set({ distanceKm: +e.target.value })}
              />
            </Row>
          )}
        </>
      )}
      {p === "objectscale" && (
        <>
          <Row label="Object mix">
            <select
              value={config.smallObjects ? "small" : "large"}
              onChange={(e) => set({ smallObjects: e.target.value === "small" })}
            >
              <option value="large">Large objects (streaming)</option>
              <option value="small">Small objects (metadata tax)</option>
            </select>
          </Row>
          <Row label="Object lock">
            <select
              value={config.immutable ? "on" : "off"}
              onChange={(e) => set({ immutable: e.target.value === "on" })}
            >
              <option value="off">Off</option>
              <option value="on">On (WORM)</option>
            </select>
          </Row>
        </>
      )}
      {p === "exascale" && (
        <>
          {(
            [
              ["Lightning", "lightningUnits"],
              ["File", "fileUnits"],
              ["Object", "objectUnits"],
              ["Block", "blockUnits"],
            ] as const
          ).map(([label, key]) => (
            <Row key={key} label={`${label} (${config[key]})`}>
              <input
                type="range" min={0} max={config.units} value={config[key]}
                onChange={(e) => set({ [key]: +e.target.value } as Partial<StorageConfig>)}
              />
            </Row>
          ))}
          <div className="mini">
            Assigned {config.lightningUnits + config.fileUnits + config.objectUnits + config.blockUnits} of {config.units} nodes.
          </div>
        </>
      )}

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
