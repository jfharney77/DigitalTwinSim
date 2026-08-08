import type { ConfigPreset, SystemConfig, Validation } from "../types";
import {
  CPU_TDP_TIERS,
  PCIE_GPU_TDP,
  PSU_7745_W,
  SHELF_KW,
  SXM_GPU_TDP,
} from "../types";

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
  config: SystemConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: SystemConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<SystemConfig>) => onChange({ ...config, ...patch });
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

      <Row label="System">
        <select
          value={p}
          onChange={(e) => set({ product: e.target.value as SystemConfig["product"] })}
        >
          <option value="xe7745">XE7745 · PCIe air</option>
          <option value="xe9680">XE9680 · HGX air</option>
          <option value="xe9712">XE9712 · liquid rack</option>
        </select>
      </Row>

      {p !== "xe9712" && (
        <Row label="CPU TDP tier">
          <select value={config.cpuTdpW} onChange={(e) => set({ cpuTdpW: +e.target.value })}>
            {CPU_TDP_TIERS.map((t) => (
              <option key={t} value={t}>{t} W ×2</option>
            ))}
          </select>
        </Row>
      )}
      {p === "xe7745" && (
        <>
          <Row label={`PCIe GPUs (${config.pcieGpus})`}>
            <input
              type="range" min={0} max={8} value={config.pcieGpus}
              onChange={(e) => set({ pcieGpus: +e.target.value })}
            />
          </Row>
          <Row label="GPU tier">
            <select value={config.pcieGpuTdpW} onChange={(e) => set({ pcieGpuTdpW: +e.target.value })}>
              {PCIE_GPU_TDP.map((t) => (
                <option key={t} value={t}>{t} W</option>
              ))}
            </select>
          </Row>
          <Row label="PSU (×4, N+N)">
            <select value={config.psuCapacityW} onChange={(e) => set({ psuCapacityW: +e.target.value })}>
              {PSU_7745_W.map((t) => (
                <option key={t} value={t}>{t} W</option>
              ))}
            </select>
          </Row>
        </>
      )}
      {p === "xe9680" && (
        <>
          <Row label="SXM GPU tier (×8)">
            <select value={config.sxmGpuTdpW} onChange={(e) => set({ sxmGpuTdpW: +e.target.value })}>
              {SXM_GPU_TDP.map((t) => (
                <option key={t} value={t}>{t === 700 ? "700 W · H100-class" : "1000 W · B200-class"}</option>
              ))}
            </select>
          </Row>
          <Row label={`NICs (${config.nics} × 400G)`}>
            <input
              type="range" min={0} max={10} value={config.nics}
              onChange={(e) => set({ nics: +e.target.value })}
            />
          </Row>
        </>
      )}
      {p === "xe9712" && (
        <>
          <Row label={`Compute trays (${config.trays})`}>
            <input
              type="range" min={1} max={18} value={config.trays}
              onChange={(e) => set({ trays: +e.target.value })}
            />
          </Row>
          <Row label="Power shelves">
            <select value={config.shelfCapacityKw} onChange={(e) => set({ shelfCapacityKw: +e.target.value })}>
              {SHELF_KW.map((t) => (
                <option key={t} value={t}>{t} kW</option>
              ))}
            </select>
          </Row>
          <Row label={`Coolant supply (${config.coolantSupplyC} °C)`}>
            <input
              type="range" min={17} max={45} value={config.coolantSupplyC}
              onChange={(e) => set({ coolantSupplyC: +e.target.value })}
            />
          </Row>
          <Row label={`Design flow (${config.coolantFlowLpm} L/min)`}>
            <input
              type="range" min={30} max={240} step={10} value={config.coolantFlowLpm}
              onChange={(e) => set({ coolantFlowLpm: +e.target.value })}
            />
          </Row>
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
