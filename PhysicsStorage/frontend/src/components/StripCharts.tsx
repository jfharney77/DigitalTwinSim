import type { SimState } from "../types";

// Shared-time-axis strips (hours): latency, delivered vs demand, used %,
// and RPO when replicating async.

const WINDOW_H = 336; // two weeks

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
    <path
      d={d} fill="none" stroke={color} strokeWidth={1.2}
      strokeDasharray={dashed ? "4 3" : undefined}
    />
  );
}

function Chart({
  title, unit, series, yMin, yMax, current,
}: {
  title: string;
  unit: string;
  series: { points: [number, number][]; color: string; dashed?: boolean }[];
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
        <span style={{ color: series[0].color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
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
  product,
}: {
  trace: SimState[];
  cursor: number;
  product: string;
}) {
  const upto = trace.slice(0, cursor + 1);
  const from = Math.max(0, upto.length - WINDOW_H);
  const win = upto.slice(from);
  const lat: [number, number][] = win.map((s) => [s.tH, s.latencyMs]);
  const delivered: [number, number][] = win.map((s) => [s.tH, s.iopsDeliveredK]);
  const demand: [number, number][] = win.map((s) => [s.tH, s.iopsDemandK]);
  const used: [number, number][] = win.map((s) => [s.tH, s.usedPct]);
  const rpo: [number, number][] = win.map((s) => [s.tH, s.rpoSeconds / 60]);
  const cur = win[win.length - 1];
  const lMax = Math.max(2, ...lat.map(([, y]) => y)) * 1.1;
  const iMax = Math.max(100, ...demand.map(([, y]) => y)) * 1.1;
  const rMax = Math.max(10, ...rpo.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — sim-hours</h2>
      <Chart
        title="latency" unit="ms"
        series={[{ points: lat, color: "#e07b28" }]}
        yMin={0} yMax={lMax}
        current={cur ? cur.latencyMs.toFixed(2) : "—"}
      />
      <Chart
        title="IOPS: delivered (solid) vs demand (dashed)" unit="k"
        series={[
          { points: delivered, color: "#7fbf5a" },
          { points: demand, color: "#8fa3bd", dashed: true },
        ]}
        yMin={0} yMax={iMax}
        current={cur ? cur.iopsDeliveredK.toFixed(0) : "—"}
      />
      <Chart
        title="capacity used" unit="%"
        series={[{ points: used, color: "#e8c33d" }]}
        yMin={0} yMax={100}
        current={cur ? cur.usedPct.toFixed(1) : "—"}
      />
      {product === "powermax" && (
        <Chart
          title="async RPO" unit="min"
          series={[{ points: rpo, color: "#2596be" }]}
          yMin={0} yMax={rMax}
          current={cur ? (cur.rpoSeconds / 60).toFixed(1) : "—"}
        />
      )}
      <div className="mini">
        Last {Math.min(WINDOW_H, win.length)} sim-hours. The gap between
        the dashed and solid IOPS lines only opens past saturation — the
        queue absorbs everything before that, and charges for it in the
        latency strip.
      </div>
    </div>
  );
}
