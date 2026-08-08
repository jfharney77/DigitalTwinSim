import type { SimState } from "../types";

// Shared-time-axis strips: DC power, tokens/s, hottest GPU, and (rack)
// coolant return with its 65 °C throttle line.

const WINDOW_S = 900;

function Path({
  points, yMin, yMax, color, w, h,
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
  title, unit, points, color, yMin, yMax, current, capY,
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
  liquid,
}: {
  trace: SimState[];
  cursor: number;
  liquid: boolean;
}) {
  const upto = trace.slice(0, cursor + 1);
  const from = Math.max(0, upto.length - WINDOW_S);
  const win = upto.slice(from);
  const power: [number, number][] = win.map((s) => [s.t, s.dcPowerW]);
  const tokens: [number, number][] = win.map((s) => [s.t, s.tokensPerS]);
  const hot: [number, number][] = win.map((s) => [s.t, s.gpuTempHotC]);
  const cool: [number, number][] = win.map((s) => [s.t, s.coolantReturnC]);
  const cur = win[win.length - 1];
  const pMax = Math.max(1000, ...power.map(([, y]) => y)) * 1.1;
  const tMax = Math.max(100, ...tokens.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="DC power" unit="W" points={power} color="#e8c33d"
        yMin={0} yMax={pMax}
        current={cur ? cur.dcPowerW.toFixed(0) : "—"}
      />
      <Chart
        title="training throughput" unit="tok/s" points={tokens} color="#7fbf5a"
        yMin={0} yMax={tMax}
        current={cur ? cur.tokensPerS.toFixed(0) : "—"}
      />
      <Chart
        title="hottest GPU" unit="°C" points={hot} color="#e07b28"
        yMin={15} yMax={105} capY={90}
        current={cur ? cur.gpuTempHotC.toFixed(1) : "—"}
      />
      {liquid && (
        <Chart
          title="coolant return" unit="°C" points={cool} color="#2596be"
          yMin={15} yMax={80} capY={65}
          current={cur ? cur.coolantReturnC.toFixed(1) : "—"}
        />
      )}
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. When tokens fall
        but power doesn't, that gap is the data-starvation lesson; the
        dashed lines are the throttle limits.
      </div>
    </div>
  );
}
