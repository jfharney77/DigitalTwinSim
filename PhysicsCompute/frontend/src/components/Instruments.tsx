import type { Explain, SimState } from "../types";

function fmtW(w: number): string {
  return w >= 10000
    ? `${(w / 1000).toFixed(1)} kW`
    : w >= 1000
      ? `${(w / 1000).toFixed(2)} kW`
      : `${w.toFixed(0)} W`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "liquid-balance":
      return `${fmtW(s.liquidWatts)} liquid + ${fmtW(s.airWatts)} air = ${fmtW(s.dcPowerW)};  ΔT ${s.coolantDeltaTC.toFixed(1)} °C`;
    case "starvation":
      return `eff util ${s.effectiveGpuUtilPct.toFixed(0)}% → ${s.tokensPerS.toFixed(0)} tok/s at ${fmtW(s.gpuPowerW)}`;
    case "positional":
      return `hottest ${s.gpuTempHotC.toFixed(1)} °C · coolest ${s.gpuTempCoolC.toFixed(1)} °C · ${s.gpusThrottled} throttled`;
    case "cooling-overhead":
      return `(${fmtW(s.fanPowerW)} + ${fmtW(s.pumpPowerW)}) / IT = ${s.coolingOverheadPct.toFixed(1)}%`;
    case "redfish":
      return `open the iDRAC tab — this state, as Redfish JSON`;
    default:
      return "";
  }
}

export function Instruments({
  state,
  explains,
  explainOn,
  liquid,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
  liquid: boolean;
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
      {s && !s.poweredOn && (
        <div className="mini rule-error">■ SYSTEM OFF — see the event log</div>
      )}
      {s && s.gpusThrottled > 0 && (
        <div className="mini rule-warning">▼ {s.gpusThrottled} GPU(s) throttled</div>
      )}
      <div className="stat"><span>DC power</span><span>{s ? fmtW(s.dcPowerW) : "—"}</span></div>
      <div className="stat"><span>wall / busbar</span><span>{s ? fmtW(s.acPowerW) : "—"}</span></div>
      <div className="stat"><span>GPU power</span><span>{s ? fmtW(s.gpuPowerW) : "—"}</span></div>
      <div className="stat">
        <span>cooling overhead</span>
        <span className="fan-overhead">{s ? `${s.coolingOverheadPct.toFixed(1)}%` : "—"}</span>
      </div>
      <Info id="cooling-overhead" />
      <div className="stat">
        <span>GPU hot · cool</span>
        <span>{s ? `${s.gpuTempHotC.toFixed(0)} · ${s.gpuTempCoolC.toFixed(0)} °C` : "—"}</span>
      </div>
      <Info id="positional" />
      {liquid ? (
        <>
          <div className="stat">
            <span>coolant supply → return</span>
            <span>{s ? `${s.coolantSupplyC.toFixed(0)} → ${s.coolantReturnC.toFixed(1)} °C` : "—"}</span>
          </div>
          <div className="stat"><span>ΔT · flow</span><span>{s ? `${s.coolantDeltaTC.toFixed(1)} °C · ${s.flowLpm.toFixed(0)} L/min` : "—"}</span></div>
          <div className="stat"><span>liquid · air split</span><span>{s ? `${fmtW(s.liquidWatts)} · ${fmtW(s.airWatts)}` : "—"}</span></div>
          <Info id="liquid-balance" />
        </>
      ) : (
        <div className="stat"><span>fans</span><span>{s ? `${s.fanRpmPct.toFixed(0)}% · ${fmtW(s.fanPowerW)}` : "—"}</span></div>
      )}
      <div className="stat">
        <span>effective GPU util</span>
        <span>{s ? `${s.effectiveGpuUtilPct.toFixed(0)}%` : "—"}</span>
      </div>
      <div className="stat"><span>training throughput</span><span>{s ? `${s.tokensPerS.toFixed(0)} tok/s` : "—"}</span></div>
      <Info id="starvation" />
      <div className="stat">
        <span>GPU-hours wasted</span>
        <span className={s && s.gpuHoursWasted > 0.05 ? "fan-overhead" : undefined}>
          {s ? s.gpuHoursWasted.toFixed(2) : "—"}
        </span>
      </div>
      <Info id="redfish" />
      <div className="mini" style={{ marginTop: 6 }}>
        A proxy model, not a benchmark. Tokens/s is a throughput proxy;
        constants carry sources in the backend table, estimates flagged.
      </div>
    </div>
  );
}
