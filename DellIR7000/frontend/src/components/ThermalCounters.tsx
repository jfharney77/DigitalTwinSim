import type { ThermalPhase, ThermalState } from "../types";
import { useLevel } from "../level";

const PHASE_LABEL: Record<ThermalPhase, string> = {
  off: "off — loop dry",
  fill: "filling & degassing",
  pump: "pumps starting",
  verify: "leak / flow verification",
  airdoor: "rear door online",
  load: "IT load arriving",
  balance: "loop balancing",
  steady: "steady state",
};

// Illustrative PG25 coolant: about 1.02 kg/L x 3.9 kJ/kg·K, which is
// ~66 W carried per L/min for each kelvin of rise. Both heat paths reject
// into the one rack loop, so the rise is the whole IT load over the flow.
const WATTS_PER_LPM_PER_K = 66.3;

// A temperature *difference* of 1 K is a difference of 1 °C, so a reader who
// has not met kelvin loses nothing: at the two plainest levels the same
// number is shown in the degrees the rest of the page uses.
function riseLabel(state: ThermalState, level: number): string {
  if (state.flowLpm === 0) return "—";
  const k = state.itLoadWatts / (state.flowLpm * WATTS_PER_LPM_PER_K);
  const unit = level <= 2 ? "°C warmer" : "K";
  return `~${Math.round(k)} ${unit}`;
}

function kw(w: number): string {
  return w >= 1000 ? `${Math.round(w / 100) / 10} kW` : `${w} W`;
}

export function ThermalCounters({
  state,
  stepIndex,
  stepCount,
  note,
}: {
  state: ThermalState | null;
  stepIndex: number;
  stepCount: number;
  note?: string;
}) {
  const level = useLevel();
  const balanced =
    state !== null &&
    state.liquidWatts + state.airWatts === state.itLoadWatts;
  return (
    <div className="an-panel">
      <h2>Heat balance</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>IT load (heat in)</span>
        <span>{state ? kw(state.itLoadWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>cold plates (direct to liquid)</span>
        <span>{state ? kw(state.liquidWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>rear door (air, then liquid)</span>
        <span>{state ? kw(state.airWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>coolant flow</span>
        <span>{state ? `${state.flowLpm} L/min` : "0 L/min"}</span>
      </div>
      <div className="stat">
        <span>loop temperature rise</span>
        <span>{state ? riseLabel(state, level) : "—"}</span>
      </div>
      <div className="stat">
        <span>books balance</span>
        <span>{state ? (balanced ? "✓ in = out" : "✗") : "—"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        {note ??
          "Cold-plate heat plus rear-door heat equals the IT load exactly, on every step. Values are illustrative."}
      </div>
    </div>
  );
}
