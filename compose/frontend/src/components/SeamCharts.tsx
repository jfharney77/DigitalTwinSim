import type { Chart, JoinedTick } from "../types";

// Strip charts on the chain's common time base. The source series is drawn
// directly above — in fact, in the same frame as — the target series it
// became, so the hand-off reads as two curves that lie on top of each other.
// Pure SVG, no chart library.

const W = 520;
const H = 64;

const ROLE_COLOR: Record<string, string> = {
  source: "#2596be",   // the engine the number came from
  target: "#7fbf5a",   // the engine it was carried into
  context: "#8a94a6",  // the same run without the coupling, or a bystander
};

function fmt(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (a >= 10) return v.toFixed(1);
  if (a >= 1) return v.toFixed(2);
  return v.toFixed(3);
}

function Line({
  points,
  yMin,
  yMax,
  color,
  dashed,
}: {
  points: [number, number][];
  yMin: number;
  yMax: number;
  color: string;
  dashed: boolean;
}) {
  if (points.length < 2) return null;
  const x0 = points[0][0];
  const span = Math.max(points[points.length - 1][0] - x0, 1);
  const range = yMax - yMin || 1;
  const d = points
    .map(([x, y], i) => {
      const px = ((x - x0) / span) * W;
      const py = H - ((y - yMin) / range) * H;
      return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${Math.max(0, Math.min(H, py)).toFixed(1)}`;
    })
    .join(" ");
  return (
    <path
      d={d}
      fill="none"
      stroke={color}
      strokeWidth={dashed ? 1.0 : 1.4}
      strokeDasharray={dashed ? "3 2" : undefined}
    />
  );
}

function OneChart({
  chart,
  timeline,
  cursor,
  timeUnit,
}: {
  chart: Chart;
  timeline: JoinedTick[];
  cursor: number;
  timeUnit: string;
}) {
  const present = chart.series.filter((s) =>
    timeline.some((tick) => tick.values[s.key] !== null && tick.values[s.key] !== undefined),
  );
  if (present.length === 0) return null;

  let yMin = Infinity;
  let yMax = -Infinity;
  for (const tick of timeline) {
    for (const s of present) {
      const v = tick.values[s.key];
      if (v === null || v === undefined) continue;
      yMin = Math.min(yMin, v);
      yMax = Math.max(yMax, v);
    }
  }
  if (!Number.isFinite(yMin)) return null;
  if (yMin > 0) yMin = 0;
  if (yMax === yMin) yMax = yMin + 1;
  const pad = (yMax - yMin) * 0.08;
  yMax += pad;

  const at = timeline[Math.min(cursor, timeline.length - 1)];
  const cursorX = (Math.min(cursor, timeline.length - 1) / Math.max(timeline.length - 1, 1)) * W;

  return (
    <div className={`seam-chart${chart.seam ? " is-seam" : ""}`}>
      <div className="mini seam-chart-title">
        <span>
          {chart.title}
          {chart.seam && <span className="seam-tag">the seam</span>}
        </span>
        <span>{chart.unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="seam-chart-svg">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {present.map((s) => (
          <Line
            key={s.key}
            points={timeline
              .map((tick, i) => [i, tick.values[s.key]] as [number, number | null])
              .filter((p): p is [number, number] => p[1] !== null && p[1] !== undefined)}
            yMin={yMin}
            yMax={yMax}
            color={ROLE_COLOR[s.role]}
            dashed={s.role === "context"}
          />
        ))}
        <line x1={cursorX} y1={0} x2={cursorX} y2={H} stroke="#e8c33d" strokeWidth={0.8} />
      </svg>
      <div className="mini seam-chart-legend">
        {present.map((s) => (
          <span key={s.key} className="seam-legend-item">
            <i style={{ background: ROLE_COLOR[s.role] }} />
            {s.label}
            <b>{fmt(at?.values[s.key])}</b>
          </span>
        ))}
        <span className="seam-legend-t">
          t = {fmt(at?.t)} {timeUnit}
        </span>
      </div>
    </div>
  );
}

export function SeamCharts({
  charts,
  timeline,
  cursor,
  timeUnit,
}: {
  charts: Chart[];
  timeline: JoinedTick[];
  cursor: number;
  timeUnit: string;
}) {
  return (
    <div className="an-panel seam-charts">
      <h2>Both engines, one time axis</h2>
      {charts.map((c) => (
        <OneChart key={c.title} chart={c} timeline={timeline} cursor={cursor} timeUnit={timeUnit} />
      ))}
      <div className="mini">
        Blue is the engine the number came from, green the engine it was carried into, dashed
        grey the same run without the coupling. On a seam chart the two solid curves are the
        same quantity read on either side: where they part, the seam is losing something, and
        the connector above says how much.
      </div>
    </div>
  );
}
