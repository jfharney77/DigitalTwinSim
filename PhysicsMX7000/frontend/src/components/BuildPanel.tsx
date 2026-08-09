import type {
  ChassisConfig,
  ConfigPreset,
  SledConfig,
  Validation,
} from "../types";
import { CPU_TDP_TIERS, DIMM_COUNTS } from "../types";

// The build panel: chassis-level choices (PSU pool + policy + budget) and
// one compact row per bay — the pool arithmetic and the composability
// mapping are the configuration surface of a modular chassis.

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
  config: ChassisConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: ChassisConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const setSled = (i: number, patch: Partial<SledConfig>) => {
    const sleds = config.sleds.map((s, j) => (j === i ? { ...s, ...patch } : s));
    onChange({ ...config, sleds });
  };
  const problems = validations.filter((v) => v.level !== "ok");
  const computeSlots = config.sleds
    .map((s, i) => ({ s, i }))
    .filter(({ s }) => s.kind === "compute")
    .map(({ i }) => i + 1);

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

      <Row label="PSU pool">
        <select
          value={config.psuCount}
          onChange={(e) => onChange({ ...config, psuCount: +e.target.value })}
        >
          {[2, 3, 4, 5, 6].map((n) => (
            <option key={n} value={n}>{n}× 3000 W</option>
          ))}
        </select>
      </Row>
      <Row label="Redundancy">
        <select
          value={config.redundancy}
          onChange={(e) =>
            onChange({ ...config, redundancy: e.target.value as ChassisConfig["redundancy"] })
          }
        >
          <option value="grid">Grid (two feeds)</option>
          <option value="n+1">N+1 (one feed)</option>
          <option value="none">None</option>
        </select>
      </Row>
      <Row label={`Power budget ${config.powerCapW > 0 ? `${config.powerCapW} W` : "off"}`}>
        <input
          type="range" min={0} max={9000} step={250}
          value={config.powerCapW}
          onChange={(e) => onChange({ ...config, powerCapW: +e.target.value })}
        />
      </Row>

      <h2 style={{ marginTop: 12 }}>Bays</h2>
      {config.sleds.map((sled, i) => (
        <div key={i} className="field cfg-row" style={{ alignItems: "center" }}>
          <span className="cfg-label">Bay {i + 1}</span>
          <span style={{ display: "flex", gap: 4, flex: 1, flexWrap: "wrap" }}>
            <select
              value={sled.kind}
              onChange={(e) =>
                setSled(i, {
                  kind: e.target.value as SledConfig["kind"],
                  ownerSlot:
                    e.target.value === "storage"
                      ? (computeSlots.find((s) => s !== i + 1) ?? null)
                      : null,
                })
              }
            >
              <option value="compute">Compute</option>
              <option value="storage">Storage</option>
              <option value="empty">Empty</option>
            </select>
            {sled.kind === "compute" && (
              <>
                <select
                  value={sled.cpuTdpW}
                  onChange={(e) => setSled(i, { cpuTdpW: +e.target.value })}
                >
                  {CPU_TDP_TIERS.map((t) => (
                    <option key={t} value={t}>2× {t} W</option>
                  ))}
                </select>
                <select
                  value={sled.dimms}
                  onChange={(e) => setSled(i, { dimms: +e.target.value })}
                >
                  {DIMM_COUNTS.map((d) => (
                    <option key={d} value={d}>{d} DIMM</option>
                  ))}
                </select>
              </>
            )}
            {sled.kind === "storage" && (
              <select
                value={sled.ownerSlot ?? ""}
                onChange={(e) =>
                  setSled(i, { ownerSlot: e.target.value ? +e.target.value : null })
                }
              >
                <option value="">no owner</option>
                {computeSlots.map((s) => (
                  <option key={s} value={s}>owned by sled {s}</option>
                ))}
              </select>
            )}
          </span>
        </div>
      ))}

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
