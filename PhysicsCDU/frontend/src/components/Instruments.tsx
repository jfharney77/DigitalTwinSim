import type { Explain, SimState } from "../types";

// The instruments column: live readouts with margin bars, plus
// explain-mode cards that show the governing equation with live values
// substituted.

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "approach":
      // The equation gives the settled value; the live supply lags it by
      // about a minute, so both are shown rather than a false equality.
      return `settled: ${s.secSupplySteadyC.toFixed(1)} °C = ${s.facSupplyC.toFixed(1)} °C + ${(s.secSupplySteadyC - s.facSupplyC).toFixed(1)} K · now ${s.secSupplyC.toFixed(1)} °C, about a minute behind`;
    case "loop-dt":
      return `ΔT = ${(s.secReturnC - s.secSupplyC).toFixed(1)} K at ${s.secFlowLpm.toFixed(0)} L/min carrying ${s.heatRemovedKw.toFixed(0)} kW`;
    case "pump-flow":
      return `${s.secFlowLpm.toFixed(0)} L/min from ${s.pumpsAlive} pump(s) at ${s.pumpSpeedPct.toFixed(0)}% → ${s.pumpPowerKw.toFixed(1)} kW`;
    case "chip-temp":
      return `settled: ${s.chipSteadyC.toFixed(1)} °C = ${s.secSupplyC.toFixed(1)} °C supply + ${((s.secReturnC - s.secSupplyC) / 2).toFixed(1)} K half rise + ${(s.chipSteadyC - s.secSupplyC - (s.secReturnC - s.secSupplyC) / 2).toFixed(1)} K cold plate · now ${s.chipTempC.toFixed(1)} °C, about 15 s behind`;
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
  policy,
  level,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
  policy: "coordinated" | "uncoordinated";
  level: number;
}) {
  const s = state;
  const plain = level <= 2;
  // With the controller's policy off there is no cap to report; showing
  // 100% would read as "the controller is fine".
  const capOff = policy === "uncoordinated";
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
          ▼ {plain ? "Rack controller slowing every bank" : "IRC shedding"} — caps at {s.capPct.toFixed(0)}%
        </div>
      )}
      {s && s.trips > 0 && (
        <div className="mini rule-error">
          ■ {s.trips} tray bank{s.trips > 1 ? "s" : ""} tripped{plain ? " (shut themselves off)" : ""}
        </div>
      )}
      <div className="stat"><span>heat moved</span><span>{s ? `${s.heatRemovedKw.toFixed(0)} kW` : "—"}</span></div>
      <div className="stat"><span>{plain ? "energy delivered so far (heat moved, added up)" : "energy delivered"}</span><span>{s ? `${s.deliveredKwh.toFixed(1)} kWh` : "—"}</span></div>
      <div className="stat"><span>{plain ? "heat exchanger load (HX, of its 220 kW rating)" : "HX load (of 220 kW class)"}</span><span>{s ? `${s.hxLoadPct.toFixed(0)}%` : "—"}</span></div>
      <Info id="loop-dt" />
      <div className="stat"><span>facility supply → return (across the exchanger)</span><span>{s ? `${s.facSupplyC.toFixed(1)} → ${s.facReturnC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>{plain ? "facility water flow (the valve opens and closes to keep that rise at 6 K)" : "facility flow (valve modulates to hold the 6 K design rise)"}</span><span>{s ? `${s.facFlowLpm.toFixed(0)} L/min` : "—"}</span></div>
      <div className="stat"><span>coolant supply → return</span><span>{s ? `${s.secSupplyC.toFixed(1)} → ${s.secReturnC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>{plain ? "approach (coolant supply minus facility supply)" : "approach (coolant − facility supply, lagging)"}</span><span>{s ? `${s.approachC.toFixed(1)} K` : "—"}</span></div>
      <div className="mini">
        Deliberately wide in this model: about 30 K at rated load, where a
        real plate exchanger runs 2–5 K. Do not size a plant from it.
      </div>
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
      <div className="stat"><span>{plain ? "speed limit set by the rack controller (IRC) — 100% = no slowdown" : "IRC cap (Integrated Rack Controller; 100% = no slowdown)"}</span><span>{!s ? "—" : capOff ? "off" : `${s.capPct.toFixed(0)}%`}</span></div>
      <div className="stat"><span>{plain ? "banks of computers online" : "banks online"}</span><span>{s ? `${s.groupsOnline}/${s.groupsPresent}` : "—"}</span></div>
      <div className="stat">
        <span>{plain ? "dew-point margin (how far the coolant is above the temperature where pipes sweat)" : "dew-point margin"}</span>
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
