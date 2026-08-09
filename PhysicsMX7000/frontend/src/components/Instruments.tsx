import type { Explain, SimState } from "../types";

// The instruments column: live readouts with explain-mode ⓘ cards that
// show the governing equation with live values substituted. The fan-power
// line is highlighted — it is the shared tax this simulator exists to
// make visible.

function fmtW(w: number): string {
  return w >= 1000 ? `${(w / 1000).toFixed(2)} kW` : `${w.toFixed(0)} W`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "sled-power": {
      const hot = s.hottestSlot > 0 ? s.sledPowerW[s.hottestSlot - 1] : 0;
      return `hottest sled ${s.hottestSlot || "—"}: ${hot.toFixed(0)} W of ${s.sledPowerW.reduce((a, b) => a + b, 0).toFixed(0)} W total`;
    }
    case "fan-tax":
      return `${s.fanPowerW.toFixed(1)} W = ${s.aliveFans} × P_max × (${s.fanRpmPct.toFixed(0)}%)³ · driven by sled ${s.hottestSlot || "—"}`;
    case "wall-power":
      return `${fmtW(s.acPowerW)} = ${fmtW(s.dcPowerW)} / ${s.psuEfficiency.toFixed(3)}`;
    case "redundancy":
      return `pool: ${s.alivePsus} alive × 3000 W · feed A ${s.feedAUp ? "up" : "DOWN"} · feed B ${s.feedBUp ? "up" : "DOWN"}`;
    case "heat-balance":
      return `${s.exhaustC.toFixed(1)} °C = ${s.inletC.toFixed(1)} °C + ${s.dcPowerW.toFixed(0)} W / (ṁ·cp)`;
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

  const sledTotal = s ? s.sledPowerW.reduce((a, b) => a + b, 0) : 0;
  const throttled = s ? s.sledThrottling.filter(Boolean).length : 0;

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s && !s.poweredOn && (
        <div className="mini rule-error">■ CHASSIS DARK — see the event log</div>
      )}
      {s && throttled > 0 && (
        <div className="mini rule-error">▼ {throttled} sled(s) throttling</div>
      )}
      {s?.chassisCapped && (
        <div className="mini rule-warning">▼ chassis power budget capping all sleds</div>
      )}
      <div className="stat"><span>total DC power</span><span>{s ? fmtW(s.dcPowerW) : "—"}</span></div>
      <div className="stat"><span>wall (AC) power</span><span>{s ? fmtW(s.acPowerW) : "—"}</span></div>
      <Info id="wall-power" />
      <div className="stat"><span>sled power (Σ 8 bays)</span><span>{s ? fmtW(sledTotal) : "—"}</span></div>
      <Info id="sled-power" />
      <div className="stat">
        <span>fan power (shared tax)</span>
        <span className="fan-overhead">{s ? `${s.fanPowerW.toFixed(1)} W` : "—"}</span>
      </div>
      <Info id="fan-tax" />
      <div className="stat">
        <span>fans</span>
        <span>{s ? `${s.fanRpmPct.toFixed(0)}% · ${s.aliveFans}/9 alive` : "—"}</span>
      </div>
      <div className="stat">
        <span>hottest sled</span>
        <span>
          {s && s.hottestSlot > 0
            ? `sled ${s.hottestSlot} · ${s.sledTempC[s.hottestSlot - 1].toFixed(1)} °C`
            : "—"}
        </span>
      </div>
      <div className="stat">
        <span>PSU pool</span>
        <span>{s ? `${s.alivePsus} alive · ${s.psuLoadPct.toFixed(0)}% · η ${(s.psuEfficiency * 100).toFixed(1)}%` : "—"}</span>
      </div>
      <div className="stat">
        <span>AC feeds</span>
        <span>
          {s ? `A ${s.feedAUp ? "up" : "DOWN"} · B ${s.feedBUp ? "up" : "DOWN"}` : "—"}
        </span>
      </div>
      <Info id="redundancy" />
      <div className="stat"><span>fabric + mgmt</span><span>{s ? fmtW(s.fabricPowerW + s.mgmtPowerW) : "—"}</span></div>
      <div className="stat"><span>airflow</span><span>{s ? `${s.airflowCfm.toFixed(0)} CFM` : "—"}</span></div>
      <div className="stat"><span>exhaust</span><span>{s ? `${s.exhaustC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>ΔT intake→exhaust</span><span>{s ? `${s.deltaTC.toFixed(1)} °C` : "—"}</span></div>
      <Info id="heat-balance" />
      <div className="mini" style={{ marginTop: 6 }}>
        Most constants are estimates (see the footnote); the chassis facts —
        8 bays, 9 fans, 6× 3000 W — are Dell's. The point is the
        relationships: watch the shared fan line answer for whichever sled
        is hottest.
      </div>
    </div>
  );
}
