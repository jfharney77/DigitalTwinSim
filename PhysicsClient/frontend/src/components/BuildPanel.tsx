import type { ConfigPreset, DeviceConfig, Validation } from "../types";
import {
  BATTERY_WH,
  CHARGER_W,
  DESKTOP_CPU_PL1,
  DESKTOP_GPU_TGP,
  DESKTOP_PSU_W,
  LAPTOP_CPU_PL1,
  LAPTOP_GPU_TGP,
} from "../types";

// The build panel: product, form factor, silicon tiers, battery/PSU —
// with validation results inline.

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
  config: DeviceConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: DeviceConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const laptop = config.formFactor === "laptop";
  const cpuTiers = laptop ? LAPTOP_CPU_PL1 : DESKTOP_CPU_PL1;
  const gpuTiers = laptop ? LAPTOP_GPU_TGP : DESKTOP_GPU_TGP;

  const set = (patch: Partial<DeviceConfig>) => {
    const next = { ...config, ...patch };
    // Keep tiers legal across form-factor / product moves.
    if (next.product === "promax") next.formFactor = "laptop";
    const cps = next.formFactor === "laptop" ? LAPTOP_CPU_PL1 : DESKTOP_CPU_PL1;
    const gps = next.formFactor === "laptop" ? LAPTOP_GPU_TGP : DESKTOP_GPU_TGP;
    if (!cps.includes(next.cpuPl1W)) next.cpuPl1W = cps[Math.floor(cps.length / 2)];
    if (!gps.includes(next.gpuTgpW)) next.gpuTgpW = gps[gps.length - 2];
    if (next.product !== "promax") next.npu = false;
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

      <Row label="Product">
        <select
          value={config.product}
          onChange={(e) => set({ product: e.target.value as DeviceConfig["product"] })}
        >
          <option value="alienware">Alienware</option>
          <option value="promax">Pro Max Plus</option>
        </select>
      </Row>
      {config.product === "alienware" && (
        <Row label="Form factor">
          <select
            value={config.formFactor}
            onChange={(e) =>
              set({ formFactor: e.target.value as DeviceConfig["formFactor"] })
            }
          >
            <option value="laptop">Laptop</option>
            <option value="desktop">Desktop tower</option>
          </select>
        </Row>
      )}
      <Row label={laptop ? "CPU PL1 tier" : "CPU tier"}>
        <select value={config.cpuPl1W} onChange={(e) => set({ cpuPl1W: +e.target.value })}>
          {cpuTiers.map((t) => (
            <option key={t} value={t}>{t} W</option>
          ))}
        </select>
      </Row>
      <Row label={laptop ? "GPU TGP tier" : "GPU tier"}>
        <select value={config.gpuTgpW} onChange={(e) => set({ gpuTgpW: +e.target.value })}>
          {gpuTiers.map((t) => (
            <option key={t} value={t}>{t === 0 ? "none" : `${t} W`}</option>
          ))}
        </select>
      </Row>
      {config.product === "promax" && (
        <Row label="Discrete NPU">
          <select
            value={config.npu ? "yes" : "no"}
            onChange={(e) => set({ npu: e.target.value === "yes" })}
          >
            <option value="no">Not fitted</option>
            <option value="yes">AI-100-class card</option>
          </select>
        </Row>
      )}
      <Row label={`RAM (${config.ramGb} GB)`}>
        <input
          type="range" min={16} max={128} step={16}
          value={config.ramGb}
          onChange={(e) => set({ ramGb: +e.target.value })}
        />
      </Row>
      {laptop && (
        <>
          <Row label="Battery">
            <select value={config.batteryWh} onChange={(e) => set({ batteryWh: +e.target.value })}>
              {BATTERY_WH.map((b) => (
                <option key={b} value={b}>{b} Wh</option>
              ))}
            </select>
          </Row>
          <Row label={`Battery health (${config.batteryHealthPct}%)`}>
            <input
              type="range" min={60} max={100} step={5}
              value={config.batteryHealthPct}
              onChange={(e) => set({ batteryHealthPct: +e.target.value })}
            />
          </Row>
          <Row label="Charger">
            <select value={config.chargerW} onChange={(e) => set({ chargerW: +e.target.value })}>
              {CHARGER_W.map((c) => (
                <option key={c} value={c}>{c} W</option>
              ))}
            </select>
          </Row>
        </>
      )}
      {!laptop && (
        <Row label="PSU">
          <select value={config.psuCapacityW} onChange={(e) => set({ psuCapacityW: +e.target.value })}>
            {DESKTOP_PSU_W.map((c) => (
              <option key={c} value={c}>{c} W</option>
            ))}
          </select>
        </Row>
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
