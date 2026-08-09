// V6 (physics_specs/VISUAL_IMPROVEMENTS.md): a compact arc gauge for
// the hero metrics — the numbers each app's tests pin. Bands paint the
// ok/warn/redline zones; ticks mark the thresholds the engine enforces.

export interface GaugeBand {
  to: number;       // band extends from the previous band's end to here
  color: string;
}

const CX = 60;
const CY = 58;
const R = 46;
const A0 = -210;    // sweep from -210° to 30° (240° arc)
const A1 = 30;

function polar(angleDeg: number, r: number): [number, number] {
  const a = (angleDeg * Math.PI) / 180;
  return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
}

function arcPath(fromDeg: number, toDeg: number, r: number): string {
  const [x0, y0] = polar(fromDeg, r);
  const [x1, y1] = polar(toDeg, r);
  const large = toDeg - fromDeg > 180 ? 1 : 0;
  return `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${r} ${r} 0 ${large} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`;
}

export function Gauge({
  label,
  unit,
  value,
  min,
  max,
  bands,
  ticks = [],
  format,
}: {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  bands: GaugeBand[];
  ticks?: number[];
  format?: (v: number) => string;
}) {
  const clamp = Math.max(min, Math.min(max, value));
  const frac = (v: number) => (v - min) / (max - min);
  const angle = (v: number) => A0 + frac(v) * (A1 - A0);
  const needle = angle(clamp);
  const [nx, ny] = polar(needle, R - 8);

  let prev = min;
  const segs = bands.map((b) => {
    const seg = { from: prev, to: Math.min(b.to, max), color: b.color };
    prev = b.to;
    return seg;
  });

  return (
    <div className="gauge" title={`${label}: ${value}${unit}`}>
      <svg viewBox="0 0 120 78" style={{ width: "100%", display: "block" }}>
        {segs.map((s, i) => (
          <path
            key={i}
            d={arcPath(angle(s.from), angle(s.to), R)}
            fill="none"
            stroke={s.color}
            strokeWidth={7}
            strokeLinecap="butt"
            opacity={0.85}
          />
        ))}
        {ticks.map((t, i) => {
          const [x0, y0] = polar(angle(t), R + 5);
          const [x1, y1] = polar(angle(t), R - 5);
          return (
            <line key={i} x1={x0} y1={y0} x2={x1} y2={y1}
              stroke="#ffffff" strokeWidth={1.6} />
          );
        })}
        <line x1={CX} y1={CY} x2={nx} y2={ny} stroke="#ffffff" strokeWidth={2.2} />
        <circle cx={CX} cy={CY} r={3} fill="#ffffff" />
        <text x={CX} y={CY + 14} textAnchor="middle" fill="#e8edf4"
          fontSize={13} fontWeight={700}>
          {format ? format(value) : `${Math.round(value)}${unit}`}
        </text>
        <text x={CX} y={CY + 19 + 6} textAnchor="middle" fill="#8a95a5" fontSize={7.5}>
          {label}
        </text>
      </svg>
    </div>
  );
}
