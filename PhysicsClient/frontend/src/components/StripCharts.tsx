import type { SimState } from "../types";

// Strip charts on a shared time axis: system power, FPS, skin temp (with
// the 46 °C cap line), battery %. The alignment is the lesson — power
// moves first, FPS follows the allocator, skin creeps, battery drains.

const WINDOW_S = 900;

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
  capY,
}: {
  title: string;
  unit: string;
  points: [number, number][];
  color: string;
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
        <span style={{ color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {capPy != null && (
          <line x1={0} y1={capPy} x2={W} y2={capPy} stroke="#c8281e" strokeWidth={0.6} strokeDasharray="4 3" />
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
  const from = Math.max(0, upto.length - WINDOW_S);
  const win = upto.slice(from);
  const power: [number, number][] = win.map((s) => [s.t, s.systemPowerW]);
  const fps: [number, number][] = win.map((s) => [s.t, s.fpsProxy]);
  const skin: [number, number][] = win.map((s) => [s.t, s.skinTempC]);
  const batt: [number, number][] = win.map((s) => [s.t, s.batteryPct]);
  const cur = win[win.length - 1];
  const pMax = Math.max(100, ...power.map(([, y]) => y)) * 1.1;
  const fMax = Math.max(60, ...fps.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="system power" unit="W" points={power} color="#e8c33d"
        yMin={0} yMax={pMax}
        current={cur ? cur.systemPowerW.toFixed(0) : "—"}
      />
      <Chart
        title="FPS proxy" unit="" points={fps} color="#7fbf5a"
        yMin={0} yMax={fMax}
        current={cur ? cur.fpsProxy.toFixed(0) : "—"}
      />
      <Chart
        title="skin temp" unit="°C" points={skin} color="#e07b28"
        yMin={15} yMax={60} capY={46}
        current={cur ? cur.skinTempC.toFixed(1) : "—"}
      />
      <Chart
        title="battery" unit="%" points={batt} color="#2596be"
        yMin={0} yMax={100}
        current={cur ? cur.batteryPct.toFixed(0) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. The burst-then-
        fade shape lives in the first two charts; the dashed line on the
        skin chart is the 46 °C contact cap — the controller silicon
        cannot argue with.
      </div>
    </div>
  );
}
