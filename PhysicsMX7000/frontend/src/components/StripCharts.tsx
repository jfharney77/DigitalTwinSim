import type { SimState } from "../types";

// Strip charts on a shared time axis: total wall power, hottest-sled
// temperature, and shared fan power for the trailing window — the
// noisy-neighbor causality made visible. Pure SVG, no chart library.

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
  const from = Math.max(0, upto.length - WINDOW_S);
  const win = upto.slice(from);
  const power: [number, number][] = win.map((s) => [s.t, s.acPowerW]);
  const temp: [number, number][] = win.map((s) => [
    s.t,
    s.hottestSlot > 0 ? s.sledTempC[s.hottestSlot - 1] : s.inletC,
  ]);
  const fan: [number, number][] = win.map((s) => [s.t, s.fanPowerW]);
  const cur = win[win.length - 1];
  const pMax = Math.max(500, ...power.map(([, y]) => y)) * 1.1;
  const fMax = Math.max(50, ...fan.map(([, y]) => y)) * 1.15;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="wall power" unit="W" points={power} color="#e8c33d"
        yMin={0} yMax={pMax}
        current={cur ? cur.acPowerW.toFixed(0) : "—"}
      />
      <Chart
        title="hottest sled" unit="°C" points={temp} color="#e07b28"
        yMin={20} yMax={110}
        current={cur && cur.hottestSlot > 0 ? cur.sledTempC[cur.hottestSlot - 1].toFixed(1) : "—"}
      />
      <Chart
        title="shared fan power" unit="W" points={fan} color="#2596be"
        yMin={0} yMax={fMax}
        current={cur ? cur.fanPowerW.toFixed(1) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. Load one sled and
        watch the order: its power first, its temperature second, then the
        <em> chassis-wide</em> fan line — the shared tax, plotted.
      </div>
    </div>
  );
}
