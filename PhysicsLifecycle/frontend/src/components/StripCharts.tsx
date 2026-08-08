import type { SimState } from "../types";

const WINDOW_D = 2920;

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
  telecom,
}: {
  trace: SimState[];
  cursor: number;
  telecom: boolean;
}) {
  const upto = trace.slice(0, cursor + 1);
  const from = Math.max(0, upto.length - WINDOW_D);
  const win = upto.slice(from);
  const coverage: [number, number][] = win.map((s) => [s.tD, s.coveragePct]);
  const hours: [number, number][] = win.map((s) => [s.tD, s.integrationHoursCum]);
  const embodied: [number, number][] = win.map((s) => [s.tD, s.embodiedKgCum]);
  const use: [number, number][] = win.map((s) => [s.tD, s.useKgCum]);
  const cpy: [number, number][] = win.map((s) => [s.tD, s.carbonPerUsefulYear]);
  const cur = win[win.length - 1];
  const hMax = Math.max(50, ...hours.map(([, y]) => y)) * 1.1;
  const eMax = Math.max(
    100, ...embodied.map(([, y]) => y), ...use.map(([, y]) => y),
  ) * 1.15;
  const cMax = Math.max(60, ...cpy.map(([, y]) => y)) * 1.2;

  return (
    <div className="an-panel">
      <h2>Strip charts — sim-days</h2>
      {telecom ? (
        <>
          <Chart
            title="coverage" unit="%"
            series={[{ points: coverage, color: "#7fbf5a" }]}
            yMin={0} yMax={100}
            current={cur ? cur.coveragePct.toFixed(1) : "—"}
          />
          <Chart
            title="integration hours (cumulative)" unit="h"
            series={[{ points: hours, color: "#e8c33d" }]}
            yMin={0} yMax={hMax}
            current={cur ? cur.integrationHoursCum.toFixed(0) : "—"}
          />
        </>
      ) : (
        <>
          <Chart
            title="embodied (solid) vs use (dashed)" unit="kg"
            series={[
              { points: embodied, color: "#e07b28" },
              { points: use, color: "#2596be", dashed: true },
            ]}
            yMin={0} yMax={eMax}
            current={cur ? cur.embodiedKgCum.toFixed(0) : "—"}
          />
          <Chart
            title="carbon per useful-year" unit="kg/y"
            series={[{ points: cpy, color: "#c8281e" }]}
            yMin={0} yMax={cMax}
            current={cur ? cur.carbonPerUsefulYear.toFixed(0) : "—"}
          />
        </>
      )}
      <div className="mini">
        {telecom
          ? "The coverage dips are decisions: envelopes, spares, remediation mode — never weather alone."
          : "Every step in the embodied line is a lifecycle event resolved by a design checkbox; the use line's slope is the grid."}
      </div>
    </div>
  );
}
