import type { SimState } from "../types";

const WINDOW_H = 720;

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
  const corrupted: [number, number][] = win.map((s) => [s.tH, s.corruptedTb]);
  const rpo: [number, number][] = win.map((s) => [s.tH, s.lastCleanPointAgeH]);
  const backlog: [number, number][] = win.map((s) => [s.tH, s.alertsBacklog]);
  const reach: [number, number][] = win.map((s) => [s.tH, s.reachableAssets]);
  const stale: [number, number][] = win.map((s) => [s.tH, s.staleGrants]);
  const cur = win[win.length - 1];
  const cMax = Math.max(1, ...corrupted.map(([, y]) => y)) * 1.15;
  const rMax = Math.max(48, ...rpo.map(([, y]) => y)) * 1.1;
  const bMax = Math.max(10, ...backlog.map(([, y]) => y)) * 1.1;
  const aMax = Math.max(10, ...reach.map(([, y]) => y), ...stale.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Timeline strips — sim-hours</h2>
      {product !== "fortzero" ? (
        <>
          <Chart
            title="corrupted data" unit="TB"
            series={[{ points: corrupted, color: "#c8281e" }]}
            yMin={0} yMax={cMax}
            current={cur ? cur.corruptedTb.toFixed(1) : "—"}
          />
          <Chart
            title="RPO — clean-point age" unit="h"
            series={[{ points: rpo, color: "#e8c33d" }]}
            yMin={0} yMax={rMax}
            current={cur ? cur.lastCleanPointAgeH.toFixed(0) : "—"}
          />
          <Chart
            title="alert backlog" unit=""
            series={[{ points: backlog, color: "#2596be" }]}
            yMin={0} yMax={bMax}
            current={cur ? String(cur.alertsBacklog) : "—"}
          />
        </>
      ) : (
        <Chart
          title="reachable (solid) · stale grants (dashed)" unit=""
          series={[
            { points: reach, color: "#c8281e" },
            { points: stale, color: "#8fa3bd", dashed: true },
          ]}
          yMin={0} yMax={aMax}
          current={cur ? String(cur.reachableAssets) : "—"}
        />
      )}
      <div className="mini">
        Scrub the timeline: the area under the corruption curve before
        containment is the blast radius, and the RPO strip shows the
        moment retained copies quietly became worthless.
      </div>
    </div>
  );
}
