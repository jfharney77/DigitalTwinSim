import { useMemo } from "react";
import type { SimState } from "../types";

// One strip chart: wall power over the trace, with backlight watts as a
// second line and the playback cursor. Smallest app, one chart.

const W = 320;
const H = 90;
const PAD = 6;

function path(trace: SimState[], pick: (s: SimState) => number, max: number): string {
  if (trace.length < 2 || max <= 0) return "";
  return trace
    .map((s, i) => {
      const x = PAD + (i / (trace.length - 1)) * (W - 2 * PAD);
      const y = H - PAD - (pick(s) / max) * (H - 2 * PAD);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function StripChart({ trace, cursor }: { trace: SimState[]; cursor: number }) {
  const max = useMemo(
    () => Math.max(10, ...trace.map((s) => s.acPowerW)) * 1.1,
    [trace],
  );
  const cx = trace.length > 1
    ? PAD + (cursor / (trace.length - 1)) * (W - 2 * PAD)
    : PAD;
  return (
    <div className="an-panel">
      <h2>Power over time</h2>
      <svg viewBox={`0 0 ${W} ${H}`} className="strip-chart" role="img"
           aria-label="Wall and backlight power over the run">
        <rect x={0} y={0} width={W} height={H} fill="#0b0e13" rx={4} />
        <path d={path(trace, (s) => s.acPowerW, max)} fill="none"
              stroke="#3f8cff" strokeWidth={1.4} />
        <path d={path(trace, (s) => s.backlightW, max)} fill="none"
              stroke="#e0a63a" strokeWidth={1} strokeDasharray="3 2" />
        <line x1={cx} y1={PAD} x2={cx} y2={H - PAD}
              stroke="#ffffff55" strokeWidth={0.8} />
        <text x={PAD} y={10} fontSize={7} fill="#8fa3c0"
              fontFamily="ui-monospace, monospace">
          wall W (solid) · backlight W (dashed) · max {max.toFixed(0)} W
        </text>
      </svg>
    </div>
  );
}
