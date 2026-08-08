import type { ConfigPreset, FabricConfig, Validation } from "../types";

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
  config: FabricConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: FabricConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<FabricConfig>) => onChange({ ...config, ...patch });
  const problems = validations.filter((v) => v.level !== "ok");
  const p = config.product;
  const dc = p !== "e3200";

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

      <Row label="Fabric">
        <select
          value={p}
          onChange={(e) => set({ product: e.target.value as FabricConfig["product"] })}
        >
          <option value="e3200">E3200 · campus</option>
          <option value="sn6000">SN6000 · AI Ethernet</option>
          <option value="x800">Quantum-X800 · InfiniBand</option>
        </select>
      </Row>
      {dc && (
        <>
          <Row label={`Spines (${config.spines})`}>
            <input
              type="range" min={1} max={8} value={config.spines}
              onChange={(e) => set({ spines: +e.target.value })}
            />
          </Row>
          <Row label={`Leaves (${config.leaves})`}>
            <input
              type="range" min={2} max={16} value={config.leaves}
              onChange={(e) => set({ leaves: +e.target.value })}
            />
          </Row>
          <Row label={`Endpoints/leaf (${config.endpointsPerLeaf})`}>
            <input
              type="range" min={1} max={64} value={config.endpointsPerLeaf}
              onChange={(e) => set({ endpointsPerLeaf: +e.target.value })}
            />
          </Row>
          <Row label="Uplink speed">
            <select value={config.uplinkGbps} onChange={(e) => set({ uplinkGbps: +e.target.value })}>
              {[400, 800].map((g) => (
                <option key={g} value={g}>{g} G</option>
              ))}
            </select>
          </Row>
        </>
      )}
      {p === "sn6000" && (
        <>
          <Row label="Adaptive routing">
            <select
              value={config.adaptiveRouting ? "on" : "off"}
              onChange={(e) => set({ adaptiveRouting: e.target.value === "on" })}
            >
              <option value="off">Off (static ECMP)</option>
              <option value="on">On (Spectrum-X)</option>
            </select>
          </Row>
          <Row label="Lossless (RoCE)">
            <select
              value={config.losslessRoce ? "on" : "off"}
              onChange={(e) => set({ losslessRoce: e.target.value === "on" })}
            >
              <option value="off">Off (drop mode)</option>
              <option value="on">On (PFC pauses)</option>
            </select>
          </Row>
          <Row label="Optics">
            <select
              value={config.cpoOptics ? "cpo" : "pluggable"}
              onChange={(e) => set({ cpoOptics: e.target.value === "cpo" })}
            >
              <option value="pluggable">Pluggable (~18 W/port)</option>
              <option value="cpo">Co-packaged (~6 W/port)</option>
            </select>
          </Row>
        </>
      )}
      {p === "x800" && (
        <Row label="SHARP collectives">
          <select
            value={config.sharp ? "on" : "off"}
            onChange={(e) => set({ sharp: e.target.value === "on" })}
          >
            <option value="off">Off</option>
            <option value="on">On (in-network math)</option>
          </select>
        </Row>
      )}
      {p === "e3200" && (
        <>
          <Row label={`Access switches (${config.leaves})`}>
            <input
              type="range" min={2} max={16} value={config.leaves}
              onChange={(e) => set({ leaves: +e.target.value })}
            />
          </Row>
          <Row label="Uplink speed">
            <select value={config.uplinkGbps} onChange={(e) => set({ uplinkGbps: +e.target.value })}>
              {[1, 10, 25].map((g) => (
                <option key={g} value={g}>{g} G</option>
              ))}
            </select>
          </Row>
          <Row label={`Wi-Fi APs (${config.poeAps})`}>
            <input
              type="range" min={0} max={60} value={config.poeAps}
              onChange={(e) => set({ poeAps: +e.target.value })}
            />
          </Row>
          <Row label={`Cameras (${config.poeCameras})`}>
            <input
              type="range" min={0} max={60} value={config.poeCameras}
              onChange={(e) => set({ poeCameras: +e.target.value })}
            />
          </Row>
          <Row label={`Phones (${config.poePhones})`}>
            <input
              type="range" min={0} max={100} value={config.poePhones}
              onChange={(e) => set({ poePhones: +e.target.value })}
            />
          </Row>
          <Row label="PoE budget">
            <select value={config.poeBudgetW} onChange={(e) => set({ poeBudgetW: +e.target.value })}>
              {[370, 740, 1440].map((w) => (
                <option key={w} value={w}>{w} W</option>
              ))}
            </select>
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
