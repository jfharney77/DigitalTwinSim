import type { SimState } from "../types";

// Strip charts on a shared time axis: tokens/s, facility MW vs budget,
// and GPU-idle-due-to-data %, so cause-and-effect alignment is visible
// across the blocks. Pure SVG — no chart library.

const WINDOW_H = 336; // trailing two sim-weeks

function Path({
  points,
  yMin,
  yMax,
  color,
  w,
  h,
}: {
  points: [number, number][];
  yMin: number;
  yMax: number;
  color: string;
  w: number;
  h: number;
}) {
  if (points.length < 2) return null;
  const x0 = points[0][0];
  const xSpan = Math.max(points[points.length - 1][0] - x0, 1);
  const d = points
    .map(([x, y], i) => {
      const px = ((x - x0) / xSpan) * w;
      const py = h - ((y - yMin) / (yMax - yMin)) * h;
      return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${Math.max(0, Math.min(h, py)).toFixed(1)}`;
    })
    .join(" ");
  return <path d={d} fill="none" stroke={color} strokeWidth={1.2} />;
}

function Chart({
  title,
  unit,
  points,
  color,
  yMin,
  yMax,
  current,
  refY,
}: {
  title: string;
  unit: string;
  points: [number, number][];
  color: string;
  yMin: number;
  yMax: number;
  current: string;
  refY?: number;
}) {
  const W = 260;
  const H = 46;
  const refPy =
    refY !== undefined ? H - ((refY - yMin) / (yMax - yMin)) * H : null;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {refPy !== null && refPy >= 0 && refPy <= H && (
          <line x1={0} y1={refPy} x2={W} y2={refPy} stroke="#c8281e" strokeWidth={0.6} strokeDasharray="3 2" />
        )}
        <Path points={points} yMin={yMin} yMax={yMax} color={color} w={W} h={H} />
      </svg>
    </div>
  );
}

export function StripCharts({
  trace,
  cursor,
}: {
  trace: SimState[];
  cursor: number;
}) {
  const upto = trace.slice(0, cursor + 1);
  const from = Math.max(0, upto.length - WINDOW_H);
  const win = upto.slice(from);
  const tokens: [number, number][] = win.map((s) => [s.tH, s.tokensPerS]);
  const mw: [number, number][] = win.map((s) => [s.tH, s.facilityMw]);
  const idle: [number, number][] = win.map((s) => [s.tH, s.gpuIdleDataPct]);
  const total: [number, number][] = win.map((s) => [s.tH, s.tokensTotalB]);
  const cur = win[win.length - 1];
  const tMax = Math.max(1000, ...tokens.map(([, y]) => y)) * 1.1;
  const mwMax = Math.max(cur?.mwBudget ?? 1, ...mw.map(([, y]) => y)) * 1.15;
  const totMax = Math.max(1, ...total.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="tokens / s" unit="tok/s" points={tokens} color="#7fbf5a"
        yMin={0} yMax={tMax}
        current={cur ? cur.tokensPerS.toLocaleString() : "—"}
      />
      <Chart
        title="facility power (– – budget)" unit="MW" points={mw} color="#e8c33d"
        yMin={0} yMax={mwMax} refY={cur?.mwBudget}
        current={cur ? cur.facilityMw.toFixed(2) : "—"}
      />
      <Chart
        title="GPU idle — data" unit="%" points={idle} color="#e07b28"
        yMin={0} yMax={100}
        current={cur ? cur.gpuIdleDataPct.toFixed(0) : "—"}
      />
      <Chart
        title="tokens total" unit="B" points={total} color="#2596be"
        yMin={0} yMax={totMax}
        current={cur ? cur.tokensTotalB.toFixed(1) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_H, win.length)} sim-hours. A dip in the total
        is a rollback: work redone from the last checkpoint. Watch idle %
        and tokens/s mirror each other — that symmetry is the data
        coupling.
      </div>
    </div>
  );
}
