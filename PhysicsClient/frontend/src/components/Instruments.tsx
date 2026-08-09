import { Gauge } from "./Gauge";
import type { Explain, SimState } from "../types";

// The instruments column: live readouts with explain-mode equations
// substituted with live values. The client-device additions over the
// R760 template: pl-state, battery/runtime, noise, FPS, tokens/joule.

function fmtW(w: number): string {
  return w >= 1000 ? `${(w / 1000).toFixed(2)} kW` : `${w.toFixed(0)} W`;
}

const PL_LABEL: Record<SimState["plState"], string> = {
  "idle": "idle",
  "pl2-boost": "PL2 boost — the sprint",
  "pl1": "PL1 sustained",
  "skin-limited": "SKIN-LIMITED — the case has the last word",
  "budget-limited": "BUDGET-LIMITED — CPU and GPU sharing one cooler",
};

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "power-limits":
      return `${s.cpuPowerW.toFixed(0)} W under ${PL_LABEL[s.plState]}`;
    case "thermal-budget":
      return `${s.cpuPowerW.toFixed(0)} + ${s.gpuPowerW.toFixed(0)} + ${s.npuPowerW.toFixed(0)} W allocated`;
    case "skin-cap":
      return `skin ${s.skinTempC.toFixed(1)} °C of 46 °C cap`;
    case "battery-runtime":
      return s.batteryDischargeW > 0
        ? `${s.runtimeMin.toFixed(0)} min at ${s.systemPowerW.toFixed(0)} W`
        : `not discharging`;
    case "energy-identity":
      return `${(s.acInputW * s.psuEfficiency).toFixed(0)} + ${s.batteryDischargeW.toFixed(0)} = ${s.systemPowerW.toFixed(0)} + ${s.chargeW.toFixed(0)} W`;
    case "tokens-per-joule":
      return s.activeEngine
        ? `${s.tokensPerS.toFixed(1)} tok/s ÷ engine W = ${s.tokensPerJoule.toFixed(2)} tok/J (${s.activeEngine.toUpperCase()})`
        : "no inference running";
    default:
      return "";
  }
}

export function Instruments({
  state,
  explains,
  explainOn,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
}) {
  const s = state;
  const ex = (id: string) => explains.find((e) => e.id === id);

  const Info = ({ id }: { id: string }) => {
    const e = ex(id);
    if (!explainOn || !e || !s) return null;
    return (
      <div className="mini explain-card">
        <div className="explain-eq">{e.equation}</div>
        <div className="explain-live">{substituted(id, s)}</div>
        <div>{e.explanation}</div>
        <div className="explain-chain">{e.inputs.join(" → ")}</div>
      </div>
    );
  };

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s && (
        <div className="gauge-row">
          <Gauge label="skin temp" unit="°C" value={s.skinTempC} min={15} max={60}
            bands={[{ to: 42, color: "#2596be" }, { to: 46, color: "#e8c33d" }, { to: 60, color: "#c8281e" }]}
            ticks={[46]} format={(v) => `${v.toFixed(1)}°`} />
          <Gauge label="CPU temp" unit="°C" value={s.cpuTempC} min={15} max={110}
            bands={[{ to: 85, color: "#2596be" }, { to: 100, color: "#e8c33d" }, { to: 110, color: "#c8281e" }]}
            ticks={[100]} format={(v) => `${v.toFixed(0)}°`} />
          <Gauge label="battery" unit="%" value={s.batteryPct} min={0} max={100}
            bands={[{ to: 15, color: "#c8281e" }, { to: 40, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}%`} />
        </div>
      )}
      {s && !s.poweredOn && (
        <div className="mini rule-error">■ POWERED OFF — see the event log</div>
      )}
      {s && (s.plState === "skin-limited" || s.plState === "budget-limited") && (
        <div className="mini rule-warning">▼ {PL_LABEL[s.plState]}</div>
      )}
      <div className="stat"><span>limit state</span><span>{s ? PL_LABEL[s.plState] : "—"}</span></div>
      <Info id="power-limits" />
      <div className="stat"><span>system power</span><span>{s ? fmtW(s.systemPowerW) : "—"}</span></div>
      <div className="stat"><span>wall draw</span><span>{s ? fmtW(s.acInputW) : "—"}</span></div>
      <Info id="energy-identity" />
      <div className="stat">
        <span>CPU · GPU · NPU</span>
        <span>{s ? `${s.cpuPowerW.toFixed(0)} · ${s.gpuPowerW.toFixed(0)} · ${s.npuPowerW.toFixed(0)} W` : "—"}</span>
      </div>
      <Info id="thermal-budget" />
      <div className="stat">
        <span>battery · charge</span>
        <span>
          {s
            ? `${s.batteryPct.toFixed(0)}%${s.chargeW > 0 ? " ⚡" : ""}${s.batteryDischargeW > 0 ? " ▼" : ""}`
            : "—"}
        </span>
      </div>
      <div className="stat">
        <span>runtime left</span>
        <span>{s && s.batteryDischargeW > 0 ? `${s.runtimeMin.toFixed(0)} min` : "—"}</span>
      </div>
      <Info id="battery-runtime" />
      <div className="stat"><span>CPU temp</span><span>{s ? `${s.cpuTempC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>GPU temp</span><span>{s ? `${s.gpuTempC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat">
        <span>skin temp</span>
        <span className={s && s.skinTempC > 44 ? "fan-overhead" : undefined}>
          {s ? `${s.skinTempC.toFixed(1)} °C / 46` : "—"}
        </span>
      </div>
      <Info id="skin-cap" />
      <div className="stat"><span>fans · noise</span><span>{s ? `${s.fanRpmPct.toFixed(0)}% · ${s.noiseDba.toFixed(0)} dB(A)` : "—"}</span></div>
      <div className="stat"><span>FPS proxy</span><span>{s ? s.fpsProxy.toFixed(0) : "—"}</span></div>
      <div className="stat">
        <span>inference</span>
        <span>
          {s && s.activeEngine
            ? `${s.tokensPerS.toFixed(1)} tok/s · ${s.tokensPerJoule.toFixed(2)} tok/J`
            : "—"}
        </span>
      </div>
      <Info id="tokens-per-joule" />
      <div className="mini" style={{ marginTop: 6 }}>
        A proxy model, not a benchmark: most constants are estimates (each
        carries a source tag in the backend table). The relationships are
        the point — watch what limits what.
      </div>
    </div>
  );
}
