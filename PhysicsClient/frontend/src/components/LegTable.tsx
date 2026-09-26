import type { Scenario, SimState, Workload } from "../types";

// One row per inference leg of the loaded scenario, so a run that rotates
// engines can be compared side by side at the end. A leg's row fills in
// when the cursor reaches the leg's last tick; the running leg shows its
// live values. Every number is read from the trace — nothing is computed
// here beyond picking the tick.

interface Leg {
  from: number;
  to: number; // last tick of the leg, inclusive
}

export function inferenceLegs(scenario: Scenario, lastT: number): Leg[] {
  const steps: { at: number; w: Workload }[] = [
    { at: 0, w: scenario.workload },
    ...scenario.events
      .filter((e) => e.action === "set-workload" && e.workload)
      .map((e) => ({ at: e.atS, w: e.workload as Workload }))
      .sort((a, b) => a.at - b.at),
  ];
  if (steps.length < 2 || !steps.every((s) => s.w.inference)) return [];
  return steps.map((s, i) => ({
    from: s.at,
    to: i + 1 < steps.length ? steps[i + 1].at - 1 : lastT,
  }));
}

export function LegTable({
  scenario,
  trace,
  cursorT,
}: {
  scenario: Scenario;
  trace: SimState[];
  cursorT: number;
}) {
  if (trace.length === 0) return null;
  const legs = inferenceLegs(scenario, trace[trace.length - 1].t);
  if (legs.length === 0) return null;
  const at = (t: number) => trace[Math.min(t, trace.length - 1)];

  return (
    <div className="an-panel leg-table">
      <h2>Results by engine</h2>
      <table>
        <thead>
          <tr>
            <th>engine</th>
            <th>tok/s</th>
            <th>tok/J engine</th>
            <th>tok/J system</th>
            <th>system W</th>
            <th>dB(A)</th>
          </tr>
        </thead>
        <tbody>
          {legs.map((leg) => {
            const started = cursorT >= leg.from;
            const done = cursorT >= leg.to;
            const s = started ? at(done ? leg.to : cursorT) : null;
            const name = at(leg.to).activeEngine?.toUpperCase() ?? "—";
            return (
              <tr key={leg.from} className={started && !done ? "leg-live" : undefined}>
                <td>{name}</td>
                <td>{s ? s.tokensPerS.toFixed(1) : "—"}</td>
                <td>{s ? s.tokensPerJoule.toFixed(2) : "—"}</td>
                <td>{s ? s.systemTokensPerJoule.toFixed(2) : "—"}</td>
                <td>{s ? s.systemPowerW.toFixed(0) : "—"}</td>
                <td>{s ? s.noiseDba.toFixed(0) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mini">
        Every leg runs one model — ~13B-class, 4-bit weights — at the same
        precision, so the rows compare chips rather than quantizations.
        Each row is the last second of that run; the run in progress shows
        live values. Rates and watts are illustrative estimates.
      </div>
    </div>
  );
}
