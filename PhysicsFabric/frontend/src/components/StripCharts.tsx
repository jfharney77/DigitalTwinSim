import type { SimState } from "../types";

const WINDOW_S = 600;

function Path({
  points, yMin, yMax, color, w, h, dashed,
}: {
  points: [number, number][];
  yMin: number;
  yMax: number;
  color: string;
  w: number;
  h: number;
  dashed?: boolean;
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
  return (
    <path d={d} fill="none" stroke={color} strokeWidth={1.2}
      strokeDasharray={dashed ? "4 3" : undefined} />
  );
}

function Chart({
  title, unit, series, yMin, yMax, current, capY,
}: {
  title: string;
  unit: string;
  series: { points: [number, number][]; color: string; dashed?: boolean }[];
  yMin: number;
  yMax: number;
  current: string;
  capY?: number;
}) {
  const W = 260;
  const H = 46;
  const capPy = capY != null ? H - ((capY - yMin) / (yMax - yMin)) * H : null;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color: series[0].color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {capPy != null && (
          <line x1={0} y1={capPy} x2={W} y2={capPy} stroke="#c8281e" strokeWidth={0.6} strokeDasharray="4 3" />
        )}
        {series.map((sr, i) => (
          <Path key={i} points={sr.points} yMin={yMin} yMax={yMax} color={sr.color} w={W} h={H} dashed={sr.dashed} />
        ))}
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
  const from = Math.max(0, upto.length - WINDOW_S);
  const win = upto.slice(from);
  const worst: [number, number][] = win.map((s) => [s.t, s.worstLinkPct]);
  const mean: [number, number][] = win.map((s) => [s.t, s.meanLinkPct]);
  const delivered: [number, number][] = win.map((s) => [s.t, s.deliveredGbps]);
  const demand: [number, number][] = win.map((s) => [s.t, s.demandedGbps]);
  const fct: [number, number][] = win.map((s) => [s.t, s.fctMs]);
  const cur = win[win.length - 1];
  const gMax = Math.max(100, ...demand.map(([, y]) => y)) * 1.1;
  const fMax = Math.max(2, ...fct.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="worst link (solid) vs mean (dashed)" unit="%"
        series={[
          { points: worst, color: "#e07b28" },
          { points: mean, color: "#8fa3bd", dashed: true },
        ]}
        yMin={0} yMax={150} capY={100}
        current={cur ? cur.worstLinkPct.toFixed(0) : "—"}
      />
      <Chart
        title="delivered (solid) vs demand (dashed)" unit="Gb/s"
        series={[
          { points: delivered, color: "#7fbf5a" },
          { points: demand, color: "#8fa3bd", dashed: true },
        ]}
        yMin={0} yMax={gMax}
        current={cur ? cur.deliveredGbps.toFixed(0) : "—"}
      />
      <Chart
        title="flow completion time" unit="ms"
        series={[{ points: fct, color: "#2596be" }]}
        yMin={0} yMax={fMax}
        current={cur ? cur.fctMs.toFixed(1) : "—"}
      />
      <div className="mini">
        The gap between the worst link and the mean is the hash-collision
        lesson; the gap between delivered and demand is what the
        congestion personality decided to do with the excess.
      </div>
    </div>
  );
}
