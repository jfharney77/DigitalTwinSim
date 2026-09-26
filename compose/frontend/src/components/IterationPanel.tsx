import type { CoupledTrace } from "../types";

// A closed chain is a fixed point over whole runs: feed the CDU the rack's
// heat, feed the rack back the CDU's supply temperature and cap, repeat.
// Stepping the scrubber through the iterations shows the loop settling —
// and the residual bars show it settling at a fixed, bounded cost.

const W = 240;
const H = 44;

function Spark({ values, color }: { values: number[]; color: string }) {
  if (values.length < 2) return null;
  const lo = Math.min(0, ...values);
  const hi = Math.max(...values) || 1;
  const d = values
    .map((v, i) => {
      const px = (i / (values.length - 1)) * W;
      const py = H - ((v - lo) / (hi - lo || 1)) * H;
      return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="iter-spark">
      <rect x={0} y={0} width={W} height={H} fill="#f5f6f7" stroke="#d2d2d2" strokeWidth={0.5} />
      <path d={d} fill="none" stroke={color} strokeWidth={1.2} />
    </svg>
  );
}

export function IterationPanel({
  trace,
  iteration,
  onIteration,
}: {
  trace: CoupledTrace;
  iteration: number;
  onIteration: (i: number) => void;
}) {
  if (trace.iterationLog.length === 0) return null;
  const last = trace.iterationLog.length - 1;
  const current = trace.iterationLog[Math.min(iteration, last)];
  const worst = Math.max(...trace.iterationLog.map((r) => r.residual), 1e-9);

  return (
    <div className="controls iteration-panel">
      <h2>The loop settling</h2>
      <div className="mini">
        {trace.iterations} iteration{trace.iterations === 1 ? "" : "s"} ·{" "}
        {trace.converged ? "converged" : "stopped at the cap without settling"}
      </div>
      <div className="iter-bars">
        {trace.iterationLog.map((r) => (
          <button
            key={r.index}
            type="button"
            className={`iter-bar${r.index === current.index ? " active" : ""}`}
            title={`iteration ${r.index}: residual ${r.residual.toExponential(2)}`}
            aria-label={`iteration ${r.index}`}
            onClick={() => onIteration(r.index)}
          >
            <i style={{ height: `${Math.max(3, (r.residual / worst) * 100)}%` }} />
            <span className="mini">{r.index}</span>
          </button>
        ))}
      </div>
      <label className="field">
        <span>Iteration {current.index}</span>
        <input
          type="range"
          min={0}
          max={last}
          value={Math.min(iteration, last)}
          onChange={(e) => onIteration(Number(e.target.value))}
        />
      </label>
      <div className="mini iter-readout">
        residual {current.residual.toExponential(2)} · loop value{" "}
        {current.loopValue.toLocaleString(undefined, { maximumFractionDigits: 1 })}
        {current.note && <> · {current.note}</>}
      </div>
      {Object.entries(current.series).map(([key, values]) => (
        <div key={key} className="iter-series">
          <div className="mini">{key}</div>
          <Spark values={values} color="#0672cb" />
        </div>
      ))}
      <p className="mini">
        Damping and the iteration cap are fixed, and nothing here is random: the same chain
        gives the same iterations, byte for byte.
      </p>
    </div>
  );
}
