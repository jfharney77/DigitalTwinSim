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
  const thr: [number, number][] = win.map((s) => [s.tH, s.throughputTbh]);
  const lag: [number, number][] = win.map((s) => [s.tH, s.freshnessLagH]);
  const idle: [number, number][] = win.map((s) => [s.tH, s.gpuIdleDueToDataPct]);
  const fill: [number, number][] = win.map((s) => [s.tH, s.arrayFillPct]);
  const forecast: [number, number][] = win.map((s) => [s.tH, Math.min(s.daysToFullForecast, 120)]);
  const err: [number, number][] = win.map((s) => [s.tH, Math.min(s.forecastErrorDays, 120)]);
  const cur = win[win.length - 1];
  const tMax = Math.max(10, ...thr.map(([, y]) => y)) * 1.2;
  const lMax = Math.max(10, ...lag.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — sim-hours</h2>
      {product === "aidataplatform" ? (
        <>
          <Chart
            title="pipeline throughput" unit="TB/h"
            series={[{ points: thr, color: "#7fbf5a" }]}
            yMin={0} yMax={tMax}
            current={cur ? cur.throughputTbh.toFixed(1) : "—"}
          />
          <Chart
            title="freshness lag" unit="h"
            series={[{ points: lag, color: "#e8c33d" }]}
            yMin={0} yMax={lMax}
            current={cur ? cur.freshnessLagH.toFixed(0) : "—"}
          />
          <Chart
            title="GPU idle due to data" unit="%"
            series={[{ points: idle, color: "#c8281e" }]}
            yMin={0} yMax={100}
            current={cur ? cur.gpuIdleDueToDataPct.toFixed(1) : "—"}
          />
        </>
      ) : (
        <>
          <Chart
            title="array fill" unit="%"
            series={[{ points: fill, color: "#e8c33d" }]}
            yMin={0} yMax={100}
            current={cur ? cur.arrayFillPct.toFixed(1) : "—"}
          />
          <Chart
            title="days-to-full forecast (solid) · error (dashed)" unit="d"
            series={[
              { points: forecast, color: "#2596be" },
              { points: err, color: "#c8281e", dashed: true },
            ]}
            yMin={0} yMax={120}
            current={cur ? cur.daysToFullForecast.toFixed(1) : "—"}
          />
        </>
      )}
      <div className="mini">
        {product === "aidataplatform"
          ? "When the throughput step lands, watch which stage the map paints hot next — the constraint moved, it didn't die."
          : "The dashed error line spikes at every slope change and decays as the week-long window relearns — forecast lag, visible."}
      </div>
    </div>
  );
}
