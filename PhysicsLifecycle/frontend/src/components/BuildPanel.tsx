import type { ConfigPreset, LifecycleConfig, Validation } from "../types";

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

function OnOff({
  value, on, off, onChange,
}: {
  value: boolean;
  on: string;
  off: string;
  onChange: (v: boolean) => void;
}) {
  return (
    <select
      value={value ? "on" : "off"}
      onChange={(e) => onChange(e.target.value === "on")}
    >
      <option value="on">{on}</option>
      <option value="off">{off}</option>
    </select>
  );
}

export function BuildPanel({
  config,
  presets,
  validations,
  onChange,
  onPreset,
}: {
  config: LifecycleConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: LifecycleConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<LifecycleConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const telecom = config.product === "telecomblocks";

  return (
    <div className="an-panel">
      <h2>{telecom ? "Build-out" : "Design decisions"}</h2>
      <div className="btnrow cfg-presets">
        {presets.map((pr) => (
          <button key={pr.id} title={pr.blurb} onClick={() => onPreset(pr)}>
            {pr.name}
          </button>
        ))}
      </div>

      <Row label="Product">
        <select
          value={config.product}
          onChange={(e) => set({ product: e.target.value as LifecycleConfig["product"] })}
        >
          <option value="telecomblocks">Telecom Blocks · build-out</option>
          <option value="circulardesign">Circular Design · a laptop's 8 years</option>
        </select>
      </Row>
      {telecom ? (
        <>
          <Row label={`Sites (${config.sites})`}>
            <input
              type="range" min={10} max={500} step={10} value={config.sites}
              onChange={(e) => set({ sites: +e.target.value })}
            />
          </Row>
          <Row label="Deployment">
            <select
              value={config.deployMode}
              onChange={(e) => set({ deployMode: e.target.value as LifecycleConfig["deployMode"] })}
            >
              <option value="blocks">Validated blocks</option>
              <option value="diy">DIY integration</option>
            </select>
          </Row>
          <Row label="Hardware envelope">
            <OnOff
              value={config.extendedTemp}
              on="Extended temp (XR-class)"
              off="Standard temp"
              onChange={(v) => set({ extendedTemp: v })}
            />
          </Row>
          <Row label="Spare capacity">
            <OnOff
              value={config.spareCapacity}
              on="N+1 sites"
              off="None"
              onChange={(v) => set({ spareCapacity: v })}
            />
          </Row>
          <Row label="Remediation">
            <OnOff
              value={config.remoteRemediation}
              on="Remote"
              off="Truck rolls"
              onChange={(v) => set({ remoteRemediation: v })}
            />
          </Row>
        </>
      ) : (
        <>
          <Row label="Battery">
            <OnOff
              value={config.batteryReplaceable}
              on="Screwed (replaceable)"
              off="Glued (sealed)"
              onChange={(v) => set({ batteryReplaceable: v })}
            />
          </Row>
          <Row label="RAM">
            <OnOff
              value={config.ramSocketed}
              on="Socketed"
              off="Soldered"
              onChange={(v) => set({ ramSocketed: v })}
            />
          </Row>
          <Row label="Ports">
            <OnOff
              value={config.portsModular}
              on="Modular"
              off="Integrated"
              onChange={(v) => set({ portsModular: v })}
            />
          </Row>
          <Row label="Chassis">
            <OnOff
              value={config.chassisRecycled}
              on="Recycled content"
              off="Virgin aluminum"
              onChange={(v) => set({ chassisRecycled: v })}
            />
          </Row>
          <Row label="Grid">
            <select
              value={config.grid}
              onChange={(e) => set({ grid: e.target.value as LifecycleConfig["grid"] })}
            >
              <option value="clean">Clean (0.05 kg/kWh)</option>
              <option value="average">Average (0.35)</option>
              <option value="coal">Coal-heavy (0.85)</option>
            </select>
          </Row>
          <Row label={`Annual use (${config.annualKwh} kWh)`}>
            <input
              type="range" min={20} max={200} step={10} value={config.annualKwh}
              onChange={(e) => set({ annualKwh: +e.target.value })}
            />
          </Row>
          <Row label={`First owner (${config.firstOwnerYears} y)`}>
            <input
              type="range" min={3} max={5} value={config.firstOwnerYears}
              onChange={(e) => set({ firstOwnerYears: +e.target.value })}
            />
          </Row>
        </>
      )}

      <h2 style={{ marginTop: 12 }}>Rules &amp; footnotes</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ Nothing to warn about.</div>
      )}
      {problems.map((v) => (
        <div key={v.ruleId} className={`mini rule-${v.level}`} title={v.source}>
          {v.level === "error" ? "✕ " : "△ "}
          {v.message}
        </div>
      ))}
      {validations.filter((v) => v.ruleId === "pcf").map((v) => (
        <div key={v.ruleId} className="mini rule-ok" title={v.source}>
          ⓘ {v.message}
        </div>
      ))}
    </div>
  );
}
