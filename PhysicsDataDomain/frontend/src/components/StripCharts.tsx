import type { SimState } from "../types";

// Strip charts on a shared day axis: stream entropy (with the alarm
// threshold drawn), dedupe ratio, and ingest speed. Pure SVG.

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
  threshold,
  thresholdLabel,
}: {
  title: string;
  unit: string;
  points: [number, number][];
  color: string;
  yMin: number;
  yMax: number;
  current: string;
  threshold?: number;
  thresholdLabel?: string;
}) {
  const W = 260;
  const H = 46;
  const ty =
    threshold !== undefined
      ? H - ((threshold - yMin) / (yMax - yMin)) * H
      : undefined;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {ty !== undefined && (
          <>
            <line x1={0} x2={W} y1={ty} y2={ty} stroke="#c8281e"
              strokeWidth={0.7} strokeDasharray="4 3" />
            {thresholdLabel && (
              <text x={W - 3} y={ty - 2} fontSize={7} fill="#c8281e"
                textAnchor="end" fontFamily="ui-monospace, monospace">
                {thresholdLabel}
              </text>
            )}
          </>
        )}
        <Path points={points} yMin={yMin} yMax={yMax} color={color} w={W} h={H} />
      </svg>
    </div>
  );
}

export function StripCharts({
  trace,
  cursor,
  alarmThreshold,
}: {
  trace: SimState[];
  cursor: number;
  alarmThreshold: number;
}) {
  const upto = trace.slice(0, cursor + 1);
  const entropy: [number, number][] = upto.map((s) => [s.day, s.streamEntropyPct]);
  const ratio: [number, number][] = upto.map((s) => [s.day, s.dedupeRatio]);
  const ingest: [number, number][] = upto.map((s) => [s.day, s.ingestGbps]);
  const cur = upto[upto.length - 1];
  const rMax = Math.max(5, ...ratio.map(([, y]) => y)) * 1.1;
  const iMax = Math.max(1, ...ingest.map(([, y]) => y)) * 1.15;

  return (
    <div className="an-panel">
      <h2>Strip charts — shared day axis</h2>
      <Chart
        title="stream entropy (changed data)" unit="%" points={entropy}
        color="#c8501e" yMin={0} yMax={100}
        current={cur ? cur.streamEntropyPct.toFixed(0) : "—"}
        threshold={alarmThreshold} thresholdLabel="alarm"
      />
      <Chart
        title="dedupe ratio" unit="×" points={ratio} color="#2596be"
        yMin={0} yMax={rMax}
        current={cur ? cur.dedupeRatio.toFixed(1) : "—"}
      />
      <Chart
        title="ingest speed" unit="GB/s" points={ingest} color="#e8c33d"
        yMin={0} yMax={iMax}
        current={cur ? cur.ingestGbps.toFixed(2) : "—"}
      />
      <div className="mini">
        Watch the order in the attack scenarios: entropy first (the smoke
        alarm), ratio second, capacity and ingest long after. The earliest
        honest signal is never the capacity chart.
      </div>
    </div>
  );
}
