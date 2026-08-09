import type { SimState } from "../types";

// Strip charts on a shared time axis: served IOPS, latency, and rebuild
// progress for the trailing window, so cause-and-effect alignment is
// visible. Pure SVG — no chart library.

const WINDOW_TICKS = 600;

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
}: {
  title: string;
  unit: string;
  points: [number, number][];
  color: string;
  yMin: number;
  yMax: number;
  current: string;
}) {
  const W = 260;
  const H = 46;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
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
  const from = Math.max(0, upto.length - WINDOW_TICKS);
  const win = upto.slice(from);
  const served: [number, number][] = win.map((s) => [s.t, s.servedKiops]);
  const latency: [number, number][] = win.map((s) => [s.t, s.latencyMs]);
  const rebuild: [number, number][] = win.map((s) => [s.t, s.rebuildPct]);
  const cur = win[win.length - 1];
  const sMax = Math.max(1, ...served.map(([, y]) => y)) * 1.1;
  const lMax = Math.max(10, ...latency.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="served IOPS" unit="k" points={served} color="#2596be"
        yMin={0} yMax={sMax}
        current={cur ? cur.servedKiops.toFixed(2) : "—"}
      />
      <Chart
        title="latency" unit="ms" points={latency} color="#e8c33d"
        yMin={0} yMax={lMax}
        current={cur ? cur.latencyMs.toFixed(2) : "—"}
      />
      <Chart
        title="rebuild" unit="%" points={rebuild} color="#e07b28"
        yMin={0} yMax={100}
        current={cur ? cur.rebuildPct.toFixed(1) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_TICKS, win.length)} ticks. Watch the order
        after a failure: service dips as the reserve is taken, latency
        climbs the queue curve, and the rebuild line crawls — hours where
        the charts show minutes.
      </div>
    </div>
  );
}
