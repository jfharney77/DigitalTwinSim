import type { SimState } from "../types";

// The hero chart: logical protected data vs physical stored, full run,
// with the playback cursor. The widening gap between the two lines IS
// the product — and the encrypted-source scenario is the day the gap
// stops widening.

export function CapacityChart({
  trace,
  cursor,
  usableTb,
}: {
  trace: SimState[];
  cursor: number;
  usableTb: number;
}) {
  const W = 560;
  const H = 150;
  const PAD = 4;
  if (trace.length < 2) return null;

  const days = trace[trace.length - 1].day || 1;
  const yMax = Math.max(
    ...trace.map((s) => s.logicalTb),
    usableTb,
    1,
  ) * 1.05;

  const px = (day: number) => PAD + (day / days) * (W - 2 * PAD);
  const py = (tb: number) => H - PAD - (tb / yMax) * (H - 2 * PAD);
  const path = (get: (s: SimState) => number) =>
    trace
      .map((s, i) => `${i === 0 ? "M" : "L"}${px(s.day).toFixed(1)},${py(get(s)).toFixed(1)}`)
      .join(" ");

  const cur = trace[Math.min(cursor, trace.length - 1)];

  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>logical protected vs physical stored (TB)</span>
        <span>
          <span style={{ color: "#2596be" }}>{cur.logicalTb.toFixed(0)} logical</span>
          {" · "}
          <span style={{ color: "#c98f2c" }}>{cur.physicalTb.toFixed(1)} physical</span>
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%" }}>
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935"
          strokeWidth={0.5} />
        {/* Usable-capacity ceiling. */}
        <line x1={PAD} x2={W - PAD} y1={py(usableTb)} y2={py(usableTb)}
          stroke="#c8281e" strokeWidth={0.8} strokeDasharray="4 3" />
        <text x={W - PAD - 2} y={py(usableTb) - 3} fontSize={9} fill="#c8281e"
          textAnchor="end" fontFamily="ui-monospace, monospace">
          usable {usableTb.toFixed(0)} TB
        </text>
        <path d={path((s) => s.logicalTb)} fill="none" stroke="#2596be"
          strokeWidth={1.6} />
        <path d={path((s) => s.physicalTb)} fill="none" stroke="#c98f2c"
          strokeWidth={1.6} />
        {/* Playback cursor. */}
        <line x1={px(cur.day)} x2={px(cur.day)} y1={PAD} y2={H - PAD}
          stroke="#e8ecf1" strokeWidth={0.6} strokeOpacity={0.5} />
      </svg>
      <div className="mini">
        The vertical gap between the lines is deduplication doing its work
        — ratio {cur.dedupeRatio.toFixed(1)}× at the cursor. When the amber
        line bends upward, something (churn, encryption, ransomware) made
        the data novel again.
      </div>
    </div>
  );
}
