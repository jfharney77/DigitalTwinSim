import type { SimState } from "../types";

// Strip charts on a shared time axis: PDU input, per-phase percent of
// breaker rating, and battery charge for the trailing window, so
// cause-and-effect alignment is visible. Pure SVG — no chart library.

const WINDOW_S = 600; // last 10 sim-minutes

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
  series,
  yMin,
  yMax,
  current,
  guideY,
}: {
  title: string;
  unit: string;
  series: { points: [number, number][]; color: string }[];
  yMin: number;
  yMax: number;
  current: string;
  guideY?: number;
}) {
  const W = 260;
  const H = 46;
  const gy =
    guideY !== undefined
      ? H - ((guideY - yMin) / (yMax - yMin)) * H
      : undefined;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color: series[0]?.color }}>
          {current} {unit}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {gy !== undefined && (
          <line x1={0} y1={gy} x2={W} y2={gy} stroke="#c8281e" strokeWidth={0.6} strokeDasharray="4 3" />
        )}
        {series.map((s, i) => (
          <Path key={i} points={s.points} yMin={yMin} yMax={yMax} color={s.color} w={W} h={H} />
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
  const input: [number, number][] = win.map((s) => [s.t, s.pduInputW]);
  const pa: [number, number][] = win.map((s) => [s.t, s.phaseAPct]);
  const pb: [number, number][] = win.map((s) => [s.t, s.phaseBPct]);
  const pc: [number, number][] = win.map((s) => [s.t, s.phaseCPct]);
  const charge: [number, number][] = win.map((s) => [s.t, s.chargePct]);
  const cur = win[win.length - 1];
  const iMax = Math.max(500, ...input.map(([, y]) => y)) * 1.1;
  const pctMax = Math.max(110, ...pa.map(([, y]) => y), ...pb.map(([, y]) => y), ...pc.map(([, y]) => y)) * 1.05;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="PDU input" unit="W"
        series={[{ points: input, color: "#e8c33d" }]}
        yMin={0} yMax={iMax}
        current={cur ? cur.pduInputW.toFixed(0) : "—"}
      />
      <Chart
        title="phase load (% of breaker · 80% line)" unit="%"
        series={[
          { points: pa, color: "#2596be" },
          { points: pb, color: "#e8c33d" },
          { points: pc, color: "#4caf7d" },
        ]}
        yMin={0} yMax={pctMax}
        current={cur ? Math.max(cur.phaseAPct, cur.phaseBPct, cur.phaseCPct).toFixed(0) : "—"}
        guideY={80}
      />
      <Chart
        title="battery charge" unit="%"
        series={[{ points: charge, color: "#4caf7d" }]}
        yMin={0} yMax={100}
        current={cur ? cur.chargePct.toFixed(0) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. A move between
        phases shifts the middle chart without moving the top one —
        conservation you can see.
      </div>
    </div>
  );
}
