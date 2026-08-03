import type { MaterialPhase, MaterialState } from "../types";

const PHASE_LABEL: Record<MaterialPhase, string> = {
  materials: "material inputs gathered",
  manufacture: "manufacture",
  ship: "shipping (recycled packaging)",
  deploy: "deployed",
  serve: "in service",
  repair: "repaired, not replaced",
  extend: "service life extended",
  recover: "taken back",
  sort: "sorted — reuse, reclaim, loss",
  reborn: "material back at the start",
};

export const PHASE_ORDER: MaterialPhase[] = [
  "materials",
  "manufacture",
  "ship",
  "deploy",
  "serve",
  "repair",
  "extend",
  "recover",
  "sort",
  "reborn",
];

// Elapsed is calendar time, not machine time: a lifecycle plays out over
// months and years, and showing seconds would make the trace read like a
// boot sequence.
export function fmtElapsed(months: number): string {
  if (months < 12) return `${months} mo`;
  const years = months / 12;
  const y = Number.isInteger(years) ? String(years) : years.toFixed(1);
  return `${y} yr (${months} mo)`;
}

export function LifecycleCounters({
  state,
  stepIndex,
  stepCount,
}: {
  state: MaterialState | null;
  stepIndex: number;
  stepCount: number;
}) {
  const phaseIdx = state ? PHASE_ORDER.indexOf(state.phase) : -1;
  const recovered = phaseIdx >= PHASE_ORDER.indexOf("recover");
  const split = state ? state.reusedKg + state.reclaimedKg + state.lostKg : 0;
  const balanced = state !== null && split === state.massKg;
  return (
    <div className="an-panel">
      <h2>Material ledger</h2>
      <div className="stat">
        <span>phase</span>
        <span>{state ? PHASE_LABEL[state.phase] : "—"}</span>
      </div>
      <div className="stat">
        <span>step</span>
        <span>{stepCount > 0 ? `${stepIndex + 1} / ${stepCount}` : "—"}</span>
      </div>
      <div className="stat">
        <span>cohort mass</span>
        <span>{state ? `${state.massKg} kg` : "0 kg"}</span>
      </div>
      {/* The hero number: the loop never starts from zero, and it ends
          higher than it began. */}
      <div className="stat">
        <span>recycled input</span>
        <span style={{ color: "var(--accent)", fontWeight: 700 }}>
          {state ? `${state.recycledInputPercent}%` : "—"}
        </span>
      </div>
      <div className="stat">
        <span>years in service</span>
        <span>{state ? state.yearsInService : 0}</span>
      </div>
      <div className="stat">
        <span>repairs</span>
        <span>{state ? state.repairs : 0}</span>
      </div>
      <div className="stat">
        <span>reused</span>
        <span>{state ? `${state.reusedKg} kg` : "—"}</span>
      </div>
      <div className="stat">
        <span>reclaimed</span>
        <span>{state ? `${state.reclaimedKg} kg` : "—"}</span>
      </div>
      {/* Lost mass is the honest measure of how circular the design is.
          Neither hidden nor celebrated — just stated, in its own color. */}
      <div className="stat">
        <span>lost</span>
        <span className="ctr-loss">{state ? `${state.lostKg} kg` : "—"}</span>
      </div>
      {recovered && state && (
        <div className={balanced ? "ctr-check ctr-check-ok" : "ctr-check"}>
          {state.reusedKg} + {state.reclaimedKg} + {state.lostKg} = {split} kg
          {balanced ? " — mass is conserved" : ` ≠ ${state.massKg} kg`}
        </div>
      )}
      <div className="stat">
        <span>elapsed (typical)</span>
        <span>{state ? fmtElapsed(state.elapsedMonths) : "0 mo"}</span>
      </div>
      <div className="mini" style={{ marginTop: 8 }}>
        The check line is the whole product claim, borrowed from the
        IR7000 twin: that cooling loop asserts heat in equals heat out with
        no tolerance, and this one asserts the same of matter. From the
        recover step onward every kilogram is accounted for as reused,
        reclaimed, or lost — and lost is never zero, because a claim of a
        perfectly closed loop would be a lie. Masses and timings are
        typical, meant to show shape and order of magnitude.
      </div>
    </div>
  );
}
