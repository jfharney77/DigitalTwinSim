import type { ConfigPreset, FleetConfig, Validation } from "../types";

const PRODUCT_LABEL: Record<FleetConfig["product"], string> = {
  vxrail: "VxRail · HCI lifecycle",
  privatecloud: "Private Cloud · catalog",
  apex: "APEX · consumption",
  nativeedge: "NativeEdge · edge fleet",
  automationstudio: "Automation Studio · pipelines",
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
  config: FleetConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: FleetConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<FleetConfig>) => onChange({ ...config, ...patch });
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
          onChange={(e) => set({ product: e.target.value as FleetConfig["product"] })}
        >
          {Object.entries(PRODUCT_LABEL).map(([id, label]) => (
            <option key={id} value={id}>{label}</option>
          ))}
        </select>
      </Row>
      <Row label="Ops mode">
        <select
          value={config.opsMode}
          onChange={(e) => set({ opsMode: e.target.value as FleetConfig["opsMode"] })}
        >
          <option value="automated">Automated (central)</option>
          <option value="manual">Manual (artisanal)</option>
        </select>
      </Row>
      <Row label={`Sites (${config.sites})`}>
        <input
          type="range" min={1} max={p === "nativeedge" ? 1000 : 10}
          value={config.sites}
          onChange={(e) => set({ sites: +e.target.value })}
        />
      </Row>
      <Row label={`Nodes/site (${config.nodesPerSite})`}>
        <input
          type="range" min={1} max={16} value={config.nodesPerSite}
          onChange={(e) => set({ nodesPerSite: +e.target.value })}
        />
      </Row>
      {p === "vxrail" && (
        <Row label="vSAN FTT">
          <select value={config.ftt} onChange={(e) => set({ ftt: +e.target.value })}>
            <option value={1}>FTT=1 (mirror)</option>
            <option value={2}>FTT=2 (survives two)</option>
          </select>
        </Row>
      )}
      {p === "privatecloud" && (
        <>
          <Row label="Stacks">
            <select value={config.stacks} onChange={(e) => set({ stacks: +e.target.value })}>
              <option value={1}>One (vSphere)</option>
              <option value={2}>Two (vSphere + OpenShift)</option>
            </select>
          </Row>
          <Row label="Catalog">
            <select
              value={config.catalog ? "on" : "off"}
              onChange={(e) => set({ catalog: e.target.value === "on" })}
            >
              <option value="on">Self-service catalog</option>
              <option value="off">Artisanal deploys</option>
            </select>
          </Row>
        </>
      )}
      {p === "apex" && (
        <>
          <Row label={`Committed base (${config.committedVms} VMs)`}>
            <input
              type="range" min={50} max={1000} step={10} value={config.committedVms}
              onChange={(e) => set({ committedVms: +e.target.value })}
            />
          </Row>
          <Row label={`Buffer (${config.bufferPct}%)`}>
            <input
              type="range" min={0} max={100} value={config.bufferPct}
              onChange={(e) => set({ bufferPct: +e.target.value })}
            />
          </Row>
          <Row label="Demand curve">
            <select
              value={config.demandCurve}
              onChange={(e) => set({ demandCurve: e.target.value as FleetConfig["demandCurve"] })}
            >
              <option value="steady">Steady</option>
              <option value="seasonal">Seasonal</option>
              <option value="spiky">Spiky</option>
            </select>
          </Row>
        </>
      )}
      {p === "nativeedge" && (
        <>
          <Row label="Site HA">
            <select
              value={config.twoNodeHa ? "ha" : "solo"}
              onChange={(e) => set({ twoNodeHa: e.target.value === "ha" })}
            >
              <option value="solo">Single node (truck-roll risk)</option>
              <option value="ha">2-node HA + witness</option>
            </select>
          </Row>
          <Row label="Site class">
            <select
              value={config.siteClass}
              onChange={(e) => set({ siteClass: e.target.value as FleetConfig["siteClass"] })}
            >
              <option value="store">Store</option>
              <option value="factory">Factory</option>
              <option value="clinic">Clinic</option>
            </select>
          </Row>
        </>
      )}
      {p === "automationstudio" && (
        <Row label="Test gate">
          <select
            value={config.testGate ? "on" : "off"}
            onChange={(e) => set({ testGate: e.target.value === "on" })}
          >
            <option value="on">Test → prod gate ON</option>
            <option value="off">Straight to prod</option>
          </select>
        </Row>
      )}

      <h2 style={{ marginTop: 12 }}>Configuration rules</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ This fleet passes every rule.</div>
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
