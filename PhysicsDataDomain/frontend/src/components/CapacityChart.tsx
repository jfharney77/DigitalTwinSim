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

  // The zoom strip: physical on its own axis, against the pre-event trend
  // the engine projects once something disturbs the estate. On the shared
  // axis above, a 100 TB bend is a pixel; here it is the whole picture.
  const ZH = 96;
  const physMax = Math.max(
    ...trace.map((s) => Math.max(s.physicalTb, s.capacityTrendTb)),
    1,
  ) * 1.08;
  const zy = (tb: number) => ZH - PAD - (tb / physMax) * (ZH - 2 * PAD);
  const zpath = (rows: SimState[], get: (s: SimState) => number) =>
    rows
      .map((s, i) => `${i === 0 ? "M" : "L"}${px(s.day).toFixed(1)},${zy(get(s)).toFixed(1)}`)
      .join(" ");
  const trended = trace.filter((s) => s.capacityTrendTb > 0);
  const eventDay = trended.length > 0 ? trended[0].day : -1;
  const alarmDay = trace.find((s) => s.entropyAlarm)?.day ?? -1;
  const noticeDay = trace.find((s) => s.capacityNoticed)?.day ?? -1;
  const marker = (day: number, color: string, label: string, row: number) =>
    day >= 0 && day <= cur.day ? (
      <g>
        <line x1={px(day)} x2={px(day)} y1={PAD} y2={ZH - PAD}
          stroke={color} strokeWidth={0.9} strokeDasharray="2 2" />
        <text x={px(day) + (px(day) > W - 120 ? -3 : 3)} y={11 + row * 11} fontSize={9} fill={color}
          textAnchor={px(day) > W - 120 ? "end" : "start"}
          fontFamily="ui-monospace, monospace">
          {label} day {day}
        </text>
      </g>
    ) : null;

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
      <div className="mini strip-title" style={{ marginTop: 8 }}>
        <span>physical stored, own axis (TB) vs pre-event trend</span>
        <span>
          <span style={{ color: "#c98f2c" }}>{cur.physicalTb.toFixed(1)} physical</span>
          {cur.capacityTrendTb > 0 && (
            <>
              {" · "}
              <span style={{ color: "#8a97a8" }}>
                {cur.capacityTrendTb.toFixed(1)} trend (
                {cur.physicalTb >= cur.capacityTrendTb ? "+" : ""}
                {(100 * (cur.physicalTb / cur.capacityTrendTb - 1)).toFixed(0)}%)
              </span>
            </>
          )}
        </span>
      </div>
      <svg viewBox={`0 0 ${W} ${ZH}`} style={{ width: "100%" }} className="capacity-zoom">
        <rect x={0} y={0} width={W} height={ZH} fill="#0d1420" stroke="#1f2935"
          strokeWidth={0.5} />
        {trended.length > 1 && (
          <path d={zpath(trended, (s) => s.capacityTrendTb)} fill="none"
            stroke="#8a97a8" strokeWidth={1} strokeDasharray="5 3" />
        )}
        <path d={zpath(trace, (s) => s.physicalTb)} fill="none" stroke="#c98f2c"
          strokeWidth={1.6} />
        {marker(alarmDay, "#e0564a", "entropy alarm", 0)}
        {marker(noticeDay, "#e6b450", "capacity notice", 1)}
        <line x1={px(cur.day)} x2={px(cur.day)} y1={PAD} y2={ZH - PAD}
          stroke="#e8ecf1" strokeWidth={0.6} strokeOpacity={0.5} />
      </svg>
      <div className="mini">
        {eventDay < 0
          ? "Nothing has disturbed this estate, so there is no trend to leave. Start ransomware or source encryption and a dashed line appears here: the 10 days before the event, projected forward."
          : noticeDay >= 0 && noticeDay <= cur.day
            ? `The dashed line is the 10 days before day ${eventDay}, projected forward. Physical first ran more than 20% above it on day ${noticeDay}, and the log recorded a capacity notice.${alarmDay >= 0 && alarmDay <= noticeDay ? ` The entropy alarm fired on day ${alarmDay}.` : ""} The 20% margin and 10-day window are this simulator's estimates.`
            : `The dashed line is the 10 days before day ${eventDay}, projected forward. The log records a capacity notice on the first day physical runs more than 20% above it. The 20% margin and 10-day window are this simulator's estimates.`}
      </div>
      <div className="mini" style={{ marginTop: 6 }}>
        In the top chart, the vertical gap between the lines is deduplication doing its work
        — ratio {cur.dedupeRatio.toFixed(1)}× at the cursor. When the amber
        line bends upward, something (churn, encryption, ransomware) made
        the data novel again.
      </div>
    </div>
  );
}
