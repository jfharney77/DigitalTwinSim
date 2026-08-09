import type {
  ConfigPreset,
  ServerConfig,
  Validation,
} from "../types";
import { DIMM_COUNTS, PLATFORM_TDP_TIERS, PSU_CAPACITIES } from "../types";

// The build panel: configuration controls with the validation results
// inline — the mini thermal-restriction (and rugged-deployment) document.

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
  config: ServerConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: ServerConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<ServerConfig>) => {
    const next = { ...config, ...patch };
    // Keep the CPU tier legal when the platform changes.
    const tiers = PLATFORM_TDP_TIERS[next.platform];
    if (!tiers.includes(next.cpuTdpW)) {
      next.cpuTdpW = tiers[tiers.length - 1];
    }
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

      <Row label="Platform">
        <select value={config.platform} onChange={(e) => set({ platform: e.target.value as ServerConfig["platform"] })}>
          <option value="xr8000">XR8000 (sled, Xeon SP)</option>
          <option value="xr4000">XR4000 (stackable, Xeon D)</option>
        </select>
      </Row>
      <Row label="CPU TDP tier">
        <select value={config.cpuTdpW} onChange={(e) => set({ cpuTdpW: +e.target.value })}>
          {PLATFORM_TDP_TIERS[config.platform].map((t) => (
            <option key={t} value={t}>{t} W</option>
          ))}
        </select>
      </Row>
      <Row label="Thermal rating">
        <select value={config.thermalConfig} onChange={(e) => set({ thermalConfig: e.target.value as ServerConfig["thermalConfig"] })}>
          <option value="standard">Standard (−5…55 °C)</option>
          <option value="extended">Extended (−20…65 °C, select)</option>
        </select>
      </Row>
      <Row label="DIMMs">
        <select value={config.dimms} onChange={(e) => set({ dimms: +e.target.value })}>
          {DIMM_COUNTS.map((d) => (
            <option key={d} value={d}>{d}× DDR5</option>
          ))}
        </select>
      </Row>
      <Row label="Drive type">
        <select value={config.driveType} onChange={(e) => set({ driveType: e.target.value as ServerConfig["driveType"] })}>
          <option value="ssd">SSD (no moving parts)</option>
          <option value="hdd">HDD (cheaper, spins)</option>
        </select>
      </Row>
      <Row label={`Drives (${config.drives})`}>
        <input
          type="range" min={0} max={8}
          value={config.drives}
          onChange={(e) => set({ drives: +e.target.value })}
        />
      </Row>
      <Row label="Accelerators">
        <select value={config.accelsSingleWide} onChange={(e) => set({ accelsSingleWide: +e.target.value })}>
          {[0, 1, 2].map((n) => <option key={n} value={n}>{n}× 75 W</option>)}
        </select>
      </Row>
      <Row label={`I/O cards (${config.ioCardW} W)`}>
        <input
          type="range" min={0} max={100} step={5}
          value={config.ioCardW}
          onChange={(e) => set({ ioCardW: +e.target.value })}
        />
      </Row>
      <Row label="PSUs">
        <select
          value={`${config.psuCount}/${config.redundancy}`}
          onChange={(e) => {
            const [count, red] = e.target.value.split("/");
            set({ psuCount: +count, redundancy: red as ServerConfig["redundancy"] });
          }}
        >
          <option value="1/1+0">1 (single feed — edge reality)</option>
          <option value="2/1+1">2 (1+1 redundant)</option>
          <option value="2/1+0">2 (combined, 2+0)</option>
        </select>
      </Row>
      <Row label="PSU capacity">
        <select value={config.psuCapacityW} onChange={(e) => set({ psuCapacityW: +e.target.value })}>
          {PSU_CAPACITIES.map((c) => <option key={c} value={c}>{c} W</option>)}
        </select>
      </Row>

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
