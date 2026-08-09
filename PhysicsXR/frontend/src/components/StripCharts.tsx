import type { SimState } from "../types";

// Strip charts on a shared time axis (spec §7): total power, CPU temp,
// and fan rpm for the trailing window, so cause-and-effect alignment is
// visible. Pure SVG — no chart library.

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
  const temp: [number, number][] = win.map((s) => [s.t, s.cpuTempC]);
  const rpm: [number, number][] = win.map((s) => [s.t, s.fanRpmPct]);
  const cur = win[win.length - 1];
  const pMax = Math.max(200, ...power.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="wall power" unit="W" points={power} color="#e8c33d"
        yMin={0} yMax={pMax}
        current={cur ? cur.acPowerW.toFixed(0) : "—"}
      />
      <Chart
        title="CPU temp" unit="°C" points={temp} color="#e07b28"
        yMin={20} yMax={110}
        current={cur ? cur.cpuTempC.toFixed(1) : "—"}
      />
      <Chart
        title="fan rpm" unit="%" points={rpm} color="#2596be"
        yMin={0} yMax={100}
        current={cur ? cur.fanRpmPct.toFixed(0) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. Watch the order
        after any change: power first (instant), temperature second (thermal
        mass), fans third (the controller follows the sensors).
      </div>
    </div>
  );
}
