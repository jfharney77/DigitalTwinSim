// V7 (physics_specs/VISUAL_IMPROVEMENTS.md): the playback slider as a
// true timeline — colored phase bands derived from the trace, event
// pins derived from the log (hover for the log line, click to jump).

export interface TimelinePin {
  i: number;                       // trace index (== sim tick)
  severity: "info" | "warning" | "critical";
  message: string;
}

export interface TimelineBand {
  from: number;
  to: number;
  color: string;
  label: string;
}

/** Contiguous index ranges where `test` holds — the band deriver. */
export function bandsWhere<T>(
  trace: T[],
  test: (s: T) => boolean,
  color: string,
  label: string,
): TimelineBand[] {
  const bands: TimelineBand[] = [];
  let start = -1;
  trace.forEach((s, i) => {
    const on = test(s);
    if (on && start < 0) start = i;
    if (!on && start >= 0) {
      bands.push({ from: start, to: i - 1, color, label });
      start = -1;
    }
  });
  if (start >= 0) bands.push({ from: start, to: trace.length - 1, color, label });
  return bands;
}

const PIN_COLOR: Record<TimelinePin["severity"], string> = {
  info: "#2596be",
  warning: "#e8c33d",
  critical: "#c8281e",
};

const W = 1000;
const H = 34;

export function Timeline({
  length,
  cursor,
  onScrub,
  pins,
  bands,
}: {
  length: number;
  cursor: number;
  onScrub: (i: number) => void;
  pins: TimelinePin[];
  bands: TimelineBand[];
}) {
  const n = Math.max(length - 1, 1);
  const x = (i: number) => (i / n) * W;

  return (
    <div className="timeline" style={{ flex: 1 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        style={{ width: "100%", height: 34, display: "block", cursor: "pointer" }}
        onClick={(e) => {
          const box = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const frac = (e.clientX - box.left) / box.width;
          onScrub(Math.round(Math.max(0, Math.min(1, frac)) * n));
        }}
      >
        <rect x={0} y={12} width={W} height={10} rx={3} fill="#0d1420" stroke="#1f2935" />
        {bands.map((b, i) => (
          <rect
            key={i}
            x={x(b.from)}
            y={12}
            width={Math.max(x(b.to) - x(b.from), 2)}
            height={10}
            fill={b.color}
            opacity={0.7}
          >
            <title>{b.label}</title>
          </rect>
        ))}
        {pins.map((p, i) => (
          <g key={i}>
            <line
              x1={x(p.i)} y1={4} x2={x(p.i)} y2={22}
              stroke={PIN_COLOR[p.severity]} strokeWidth={2.5}
            />
            <circle cx={x(p.i)} cy={4} r={3.4} fill={PIN_COLOR[p.severity]}>
              <title>{`t=${p.i} — ${p.message}`}</title>
            </circle>
          </g>
        ))}
        {/* Played portion + cursor needle. */}
        <rect x={0} y={12} width={x(cursor)} height={10} fill="#0672cb" opacity={0.35} />
        <line x1={x(cursor)} y1={0} x2={x(cursor)} y2={H} stroke="#ffffff" strokeWidth={2} />
      </svg>
      <input
        type="range"
        min={0}
        max={n}
        value={cursor}
        onChange={(e) => onScrub(+e.target.value)}
        style={{ width: "100%", marginTop: -6 }}
        aria-label="timeline scrubber"
      />
    </div>
  );
}
