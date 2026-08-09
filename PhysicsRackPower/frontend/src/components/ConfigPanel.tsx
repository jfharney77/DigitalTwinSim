import type {
  Chemistry,
  ConfigPreset,
  Phase,
  RackConfig,
  Validation,
} from "../types";
import { BREAKER_AMP_TIERS, UPS_WH_TIERS } from "../types";
import { PHASE_COLOR } from "./RackView";

// The build panel: per-slot watts + phase feed, breaker rating, and the
// UPS battery — with the validation findings rendered beneath, reading
// like the checklist a facilities engineer runs before energizing.

const PHASES: Phase[] = ["A", "B", "C"];

export function ConfigPanel({
  config,
  presets,
  validations,
  onChange,
  onPreset,
}: {
  config: RackConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: RackConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const setLoad = (i: number, patch: Partial<RackConfig["loads"][number]>) => {
    const loads = config.loads.map((ld, j) => (j === i ? { ...ld, ...patch } : ld));
    onChange({ ...config, loads });
  };

  return (
    <div className="an-panel">
      <h2>Rack build</h2>
      <div className="btnrow">
        {presets.map((p) => (
          <button key={p.id} title={p.blurb} onClick={() => onPreset(p)}>
            {p.name}
          </button>
        ))}
      </div>

      <div className="mini" style={{ margin: "6px 0 2px" }}>
        Loads — watts and phase feed
      </div>
      {config.loads.map((ld, i) => (
        <div key={i} className="load-row">
          <span className="load-label mini">{ld.label}</span>
          <input
            type="range" min={0} max={2000} step={50} value={ld.powerW}
            onChange={(e) => setLoad(i, { powerW: +e.target.value })}
          />
          <span className="mini load-watts">{ld.powerW} W</span>
          <span className="phase-cycle">
            {PHASES.map((p) => (
              <button
                key={p}
                className={ld.phase === p ? "active" : ""}
                style={
                  ld.phase === p
                    ? { borderColor: PHASE_COLOR[p], color: PHASE_COLOR[p] }
                    : undefined
                }
                onClick={() => setLoad(i, { phase: p })}
              >
                {p}
              </button>
            ))}
          </span>
        </div>
      ))}

      <label className="field">
        Breaker rating (per phase)
        <select
          value={config.breakerAmps}
          onChange={(e) => onChange({ ...config, breakerAmps: +e.target.value })}
        >
          {BREAKER_AMP_TIERS.map((a) => (
            <option key={a} value={a}>{a} A</option>
          ))}
        </select>
      </label>

      <div className="mini" style={{ margin: "6px 0 2px" }}>UPS battery</div>
      <label className="field">
        Chemistry
        <select
          value={config.upsChemistry}
          onChange={(e) =>
            onChange({ ...config, upsChemistry: e.target.value as Chemistry })
          }
        >
          <option value="vrla">VRLA (lead-acid)</option>
          <option value="lithium">Lithium</option>
        </select>
      </label>
      <label className="field">
        Nameplate energy
        <select
          value={config.upsNameplateWh}
          onChange={(e) =>
            onChange({ ...config, upsNameplateWh: +e.target.value })
          }
        >
          {UPS_WH_TIERS.map((wh) => (
            <option key={wh} value={wh}>{wh} Wh</option>
          ))}
        </select>
      </label>
      <label className="field">
        Battery age {config.upsAgeYears} y
        <input
          type="range" min={0} max={10} step={0.5} value={config.upsAgeYears}
          onChange={(e) => onChange({ ...config, upsAgeYears: +e.target.value })}
        />
      </label>

      <div className="rules">
        {validations.map((v) => (
          <div key={v.ruleId} className={`mini rule-${v.level}`} title={v.source}>
            {v.level === "error" ? "✕" : v.level === "warning" ? "▲" : "✓"}{" "}
            {v.message}
          </div>
        ))}
      </div>
    </div>
  );
}
