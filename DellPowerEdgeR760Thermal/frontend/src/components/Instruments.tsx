import type { ConstantInfo, Explain, ServerConfig, SimState } from "../types";

type Constants = Record<string, ConstantInfo> | null;

// The instruments column (spec §7 right): live readouts with throttle
// margin bars, plus explain-mode ⓘ affordances that show the governing
// equation with live values substituted (spec §8 — the key educational
// feature).

function fmtW(w: number): string {
  return w >= 1000 ? `${(w / 1000).toFixed(2)} kW` : `${w.toFixed(0)} W`;
}

// Substitute live values into an equation template for explain mode.
// Every term is a number the reader can check by hand; the constants come
// from the backend's table (GET /api/constants), never a second copy.
// The same substitution in words, for levels 1–2: the reader who asked
// for plain language should not meet ṁ and cp as the first thing on the
// card. Same numbers, same order, no symbols.
function substitutedPlain(id: string, s: SimState): string {
  switch (id) {
    case "cpu-power":
      return `${s.cpuPowerW.toFixed(0)} watts of processor power, with the processors ${s.cpuUtilPct.toFixed(0)}% busy${s.cpuBoosting ? ", sprinting above their rated power" : ""}${s.perfLostPct > 0 ? `, cut back by ${s.perfLostPct.toFixed(0)}% to keep them cool` : ""}`;
    case "zone-outlet":
      return `${s.exhaustC.toFixed(1)} °C out the back = ${s.inletEffectiveC.toFixed(1)} °C going in, plus ${s.airHeatW.toFixed(0)} watts of heat spread across ${s.airflowCfm.toFixed(0)} CFM of moving air`;
    case "fan-power":
      return `${s.fanPowerW.toFixed(1)} watts for ${s.aliveFans} fans running at ${s.fanRpmPct.toFixed(0)}% of full speed`;
    case "wall-power":
      return `${fmtW(s.acPowerW)} drawn from the wall to deliver ${fmtW(s.dcPowerW)} to the parts — the difference is what the power supplies lose converting it`;
    case "recirculation":
      return `the server is breathing ${s.inletEffectiveC.toFixed(1)} °C air while its own exhaust is ${s.exhaustC.toFixed(1)} °C`;
    default:
      return "";
  }
}

function substituted(id: string, s: SimState, cfg: ServerConfig, k: Constants): string {
  const c = (key: string) => k?.[key]?.value;
  switch (id) {
    case "cpu-power": {
      const clamp = (1 - s.perfLostPct / 100).toFixed(2);
      const idleF = c("cpu_idle_fraction");
      const exp = c("cpu_util_exponent");
      const boost = c("cpu_boost_multiplier");
      if (idleF == null || exp == null || boost == null)
        return `${s.cpuPowerW.toFixed(0)} W at ${s.cpuUtilPct.toFixed(0)}% util × clamp ${clamp}`;
      if (s.cpuBoosting)
        return `${s.cpuPowerW.toFixed(0)} W = ${cfg.sockets} × ${cfg.cpuTdpW} W × ${boost} boost × clamp ${clamp}`;
      const idle = idleF * cfg.cpuTdpW;
      return `${s.cpuPowerW.toFixed(0)} W = ${cfg.sockets} × (${idle.toFixed(1)} W + ${(cfg.cpuTdpW - idle).toFixed(1)} W × ${(s.cpuUtilPct / 100).toFixed(2)}^${exp}) × clamp ${clamp}`;
    }
    case "zone-outlet": {
      const cp = c("air_cp") ?? 1005;
      const warming = Math.abs(s.airHeatW - s.dcPowerW) > 0.02 * s.dcPowerW;
      return (
        `${s.exhaustC.toFixed(1)} °C = ${s.inletEffectiveC.toFixed(1)} °C + ${s.airHeatW.toFixed(0)} W / (${s.massFlowKgps.toFixed(4)} kg/s × ${cp} J/kg·K)` +
        ` · ${s.airflowCfm.toFixed(0)} CFM is ${s.massFlowKgps.toFixed(4)} kg/s` +
        (warming
          ? ` · the air carries ${s.airHeatW.toFixed(0)} W of the ${s.dcPowerW.toFixed(0)} W DC while the metal's temperature is still changing`
          : "")
      );
    }
    case "fan-power": {
      const pmax = c(cfg.fanKit === "gold" ? "fan_pmax_gold_w" : "fan_pmax_std_w");
      return `${s.fanPowerW.toFixed(1)} W = ${s.aliveFans} × ${pmax != null ? `${pmax} W` : "P_max"} × (${s.fanRpmPct.toFixed(1)}%)³`;
    }
    case "wall-power":
      return `${fmtW(s.acPowerW)} = ${fmtW(s.dcPowerW)} / ${s.psuEfficiency.toFixed(3)}`;
    case "recirculation":
      return `inlet_eff = ${s.inletEffectiveC.toFixed(1)} °C (exhaust ${s.exhaustC.toFixed(1)} °C)`;
    default:
      return "";
  }
}

function MarginBar({ value, limit, label }: { value: number; limit: number; label: string }) {
  const pct = Math.max(0, Math.min(100, (value / limit) * 100));
  const hot = value > limit - 8;
  return (
    <div className="margin-bar" title={`${label}: ${value.toFixed(1)} °C of ${limit} °C`}>
      <div
        className="margin-fill"
        style={{
          width: `${pct}%`,
          background: hot ? "#c8281e" : pct > 75 ? "#e8c33d" : "#2596be",
        }}
      />
    </div>
  );
}

export function Instruments({
  level,
  state,
  explains,
  explainOn,
  config,
  constants,
}: {
  level: number;
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
  config: ServerConfig;
  constants: Constants;
}) {
  const s = state;
  const ex = (id: string) => explains.find((e) => e.id === id);

  // At levels 1–2 the prose comes first and the numbers are read out in
  // words: the symbolic line is the last thing a newcomer needs, not the
  // first. The equation itself is leveled by the backend.
  const plain = level <= 2;
  const Info = ({ id }: { id: string }) => {
    const e = ex(id);
    if (!explainOn || !e || !s) return null;
    if (plain) {
      return (
        <div className="mini explain-card">
          <div>{e.explanation}</div>
          <div className="explain-live">{substitutedPlain(id, s)}</div>
          <div className="explain-eq">{e.equation}</div>
          <div className="explain-chain">{e.inputs.join(" → ")}</div>
        </div>
      );
    }
    return (
      <div className="mini explain-card">
        <div className="explain-eq">{e.equation}</div>
        <div className="explain-live">{substituted(id, s, config, constants)}</div>
        <div>{e.explanation}</div>
        <div className="explain-chain">{e.inputs.join(" → ")}</div>
      </div>
    );
  };

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s && !s.poweredOn && (
        <div className="mini rule-error">■ SERVER OFF — see the event log</div>
      )}
      {s?.cpuThrottling && (
        <div className="mini rule-error">
          ▼ THROTTLING — {s.perfLostPct.toFixed(0)}% performance lost
        </div>
      )}
      <div className="stat"><span>total DC power</span><span>{s ? fmtW(s.dcPowerW) : "—"}</span></div>
      <div className="stat"><span>wall (AC) power</span><span>{s ? fmtW(s.acPowerW) : "—"}</span></div>
      <Info id="wall-power" />
      <div className="stat">
        <span>PSU efficiency · load</span>
        <span>{s ? `${(s.psuEfficiency * 100).toFixed(1)}% · ${s.psuLoadPct.toFixed(0)}%` : "—"}</span>
      </div>
      <div className="stat">
        <span>fan power (overhead)</span>
        <span className="fan-overhead">{s ? `${s.fanPowerW.toFixed(1)} W` : "—"}</span>
      </div>
      <Info id="fan-power" />
      <div className="stat">
        <span>CPU power</span>
        <span>
          {s ? fmtW(s.cpuPowerW) : "—"}
          {s?.cpuBoosting
            ? plain ? " · sprinting" : " · turbo boost"
            : s?.cpuThrottling
              ? plain ? " · slowed to stay cool" : " · throttled"
              : s?.poweredOn
                ? plain ? " · steady power" : " · rated"
                : ""}
        </span>
      </div>
      {s?.cpuBoosting && (
        <div className="mini">
          {plain
            ? "The processors are sprinting: at full load they run above their steady power for up to a minute, then settle back to the power they are designed to hold. That settling is not them slowing down to stay cool."
            : "Turbo boost: at 100% load the CPUs run above rated power for up to 60 s, then step down to TDP. That step is not throttling."}
        </div>
      )}
      <Info id="cpu-power" />
      <div className="stat">
        <span>CPU temp</span>
        <span>{s ? `${s.cpuTempC.toFixed(1)} °C` : "—"}</span>
      </div>
      {s && <MarginBar value={s.cpuTempC} limit={98} label="throttle margin" />}
      <div className="stat">
        <span>GPU temp</span>
        <span>{s ? `${s.gpuTempC.toFixed(1)} °C` : "—"}</span>
      </div>
      {s && <MarginBar value={s.gpuTempC} limit={92} label="GPU throttle margin" />}
      <div className="stat"><span>airflow</span><span>{s ? `${s.airflowCfm.toFixed(0)} CFM` : "—"}</span></div>
      <div className="stat">
        <span>fans</span>
        <span>{s ? `${s.fanRpmPct.toFixed(0)}% · ${s.aliveFans}/6 alive` : "—"}</span>
      </div>
      <div className="stat">
        <span>inlet (effective)</span>
        <span>{s ? `${s.inletEffectiveC.toFixed(1)} °C` : "—"}</span>
      </div>
      <Info id="recirculation" />
      <div className="stat"><span>exhaust</span><span>{s ? `${s.exhaustC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>ΔT front→back</span><span>{s ? `${s.deltaTC.toFixed(1)} °C` : "—"}</span></div>
      <Info id="zone-outlet" />
      <div className="mini" style={{ marginTop: 6 }}>
        Every value here is a model estimate, not a measurement: most
        constants are estimates (see the footnote), and the point is the
        relationships. Watch fan power ride the temperature it exists to
        control. Exhaust and ΔT follow the heat the air is carrying, which
        trails power for a minute or so after any change.
      </div>
    </div>
  );
}
