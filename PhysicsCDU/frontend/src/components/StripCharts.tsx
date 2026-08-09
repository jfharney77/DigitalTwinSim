import type { SimState } from "../types";

// Strip charts on a shared time axis: heat moved, coolant supply,
// silicon temperature, flow, and dew margin for the trailing window,
// so cause-and-effect alignment is visible. Pure SVG — no chart library.

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
  const H = 42;
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
  const heat: [number, number][] = win.map((s) => [s.t, s.heatRemovedKw]);
  const supply: [number, number][] = win.map((s) => [s.t, s.secSupplyC]);
  const chip: [number, number][] = win.map((s) => [s.t, s.chipTempC]);
  const cap: [number, number][] = win.map((s) => [s.t, s.capPct]);
  const dew: [number, number][] = win.map((s) => [s.t, s.dewMarginC]);
  const cur = win[win.length - 1];
  const hMax = Math.max(100, ...heat.map(([, y]) => y)) * 1.1;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared time axis</h2>
      <Chart
        title="heat moved" unit="kW" points={heat} color="#e8c33d"
        yMin={0} yMax={hMax}
        current={cur ? cur.heatRemovedKw.toFixed(0) : "—"}
      />
      <Chart
        title="coolant supply" unit="°C" points={supply} color="#2596be"
        yMin={10} yMax={70}
        current={cur ? cur.secSupplyC.toFixed(1) : "—"}
      />
      <Chart
        title="hottest silicon" unit="°C" points={chip} color="#e07b28"
        yMin={20} yMax={80}
        current={cur ? cur.chipTempC.toFixed(1) : "—"}
      />
      <Chart
        title="IRC cap" unit="%" points={cap} color="#7fbf5a"
        yMin={0} yMax={105}
        current={cur ? cur.capPct.toFixed(0) : "—"}
      />
      <Chart
        title="dew margin" unit="K" points={dew} color="#c8281e"
        yMin={0} yMax={30}
        current={cur ? cur.dewMarginC.toFixed(1) : "—"}
      />
      <div className="mini">
        Last {Math.min(WINDOW_S, win.length)} sim-seconds. Watch the order
        after any change: facility water first, coolant supply a minute
        behind it, silicon behind that, and the IRC cap last — the
        controller follows the sensors.
      </div>
    </div>
  );
}
