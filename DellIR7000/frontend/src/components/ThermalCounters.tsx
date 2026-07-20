import type { ThermalPhase, ThermalState } from "../types";

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

function kw(w: number): string {
  return w >= 1000 ? `${Math.round(w / 100) / 10} kW` : `${w} W`;
}

export function ThermalCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: ThermalState | null;
  stepIndex: number;
  stepCount: number;
}) {
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
        <span>liquid loop (heat out)</span>
        <span>{state ? kw(state.liquidWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>rear door (heat out)</span>
        <span>{state ? kw(state.airWatts) : "0 W"}</span>
      </div>
      <div className="stat">
        <span>coolant flow</span>
        <span>{state ? `${state.flowLpm} L/min` : "0 L/min"}</span>
      </div>
      <div className="stat">
        <span>books balance</span>
        <span>{state ? (balanced ? "✓ in = out" : "✗") : "—"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        Energy is conserved: liquid plus air heat removal always equals the
        IT load exactly — that identity is this twin's version of the compute
        twins' phase machines, and the backend tests enforce it on every
        step. Values are typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
