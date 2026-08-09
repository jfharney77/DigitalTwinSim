import type { Explain, SimState } from "../types";

// The instruments column: live readouts with margin bars, plus
// explain-mode cards that show the governing equation with live values
// substituted.

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "approach":
      return `${s.secSupplyC.toFixed(1)} °C = ${s.facSupplyC.toFixed(1)} °C + ${s.approachC.toFixed(1)} K approach`;
    case "loop-dt":
      return `ΔT = ${(s.secReturnC - s.secSupplyC).toFixed(1)} K at ${s.secFlowLpm.toFixed(0)} L/min carrying ${s.heatRemovedKw.toFixed(0)} kW`;
    case "pump-flow":
      return `${s.secFlowLpm.toFixed(0)} L/min from ${s.pumpsAlive} pump(s) at ${s.pumpSpeedPct.toFixed(0)}% → ${s.pumpPowerKw.toFixed(1)} kW`;
    case "chip-temp":
      return `${s.chipTempC.toFixed(1)} °C = ${s.secSupplyC.toFixed(1)} °C supply + rise + cold plate`;
    case "dew-floor":
      return `margin = ${s.dewMarginC.toFixed(1)} K ${s.floorActive ? "(floor holding)" : ""}`;
    default:
      return "";
  }
}

function MarginBar({ value, limit, label }: { value: number; limit: number; label: string }) {
  const pct = Math.max(0, Math.min(100, (value / limit) * 100));
  const hot = value > limit - 3;
  return (
    <div className="margin-bar" title={`${label}: ${value.toFixed(1)} °C of ${limit} °C`}>
      <div
        className="margin-fill"
        style={{
          width: `${pct}%`,
          background: hot ? "#c8281e" : pct > 80 ? "#e8c33d" : "#2596be",
        }}
      />
    </div>
  );
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
      {s?.capping && (
        <div className="mini rule-warning">
          ▼ IRC SHEDDING — caps at {s.capPct.toFixed(0)}%
        </div>
      )}
      {s && s.trips > 0 && (
        <div className="mini rule-error">
          ■ {s.trips} tray bank{s.trips > 1 ? "s" : ""} TRIPPED
        </div>
      )}
      <div className="stat"><span>heat moved</span><span>{s ? `${s.heatRemovedKw.toFixed(0)} kW` : "—"}</span></div>
      <div className="stat"><span>HX load (of 220 kW class)</span><span>{s ? `${s.hxLoadPct.toFixed(0)}%` : "—"}</span></div>
      <Info id="loop-dt" />
      <div className="stat"><span>facility supply → return</span><span>{s ? `${s.facSupplyC.toFixed(1)} → ${s.facReturnC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>coolant supply → return</span><span>{s ? `${s.secSupplyC.toFixed(1)} → ${s.secReturnC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>approach</span><span>{s ? `${s.approachC.toFixed(1)} K` : "—"}</span></div>
      <Info id="approach" />
      <div className="stat"><span>coolant flow</span><span>{s ? `${s.secFlowLpm.toFixed(0)} L/min` : "—"}</span></div>
      <div className="stat">
        <span>pumps</span>
        <span>{s ? `${s.pumpSpeedPct.toFixed(0)}% · ${s.pumpsAlive} alive · ${s.pumpPowerKw.toFixed(1)} kW` : "—"}</span>
      </div>
      <Info id="pump-flow" />
      <div className="stat"><span>hottest silicon</span><span>{s ? `${s.chipTempC.toFixed(1)} °C` : "—"}</span></div>
      {s && <MarginBar value={s.chipTempC} limit={65} label="trip margin" />}
      <Info id="chip-temp" />
      <div className="stat"><span>IRC cap</span><span>{s ? `${s.capPct.toFixed(0)}%` : "—"}</span></div>
      <div className="stat"><span>banks online</span><span>{s ? `${s.groupsOnline}/${s.groupsPresent}` : "—"}</span></div>
      <div className="stat">
        <span>dew-point margin</span>
        <span>{s ? `${s.dewMarginC.toFixed(1)} K${s.floorActive ? " · floor" : ""}` : "—"}</span>
      </div>
      <Info id="dew-floor" />
      <div className="mini" style={{ marginTop: 6 }}>
        A simplified model: the C7000's 220 kW class is sourced from
        Dell's announcement; nearly every other constant is an estimate
        and labeled so in the backend's constants table. The point is
        the chain — facility water + approach + loop rise + cold plate
        = silicon.
      </div>
    </div>
  );
}
