import type { ChassisMap, ChassisRegion, SimState } from "../types";

// The MX7000 front elevation as a thermal map: eight sled bays across the
// top, management/fabric at the right, the shared nine-fan wall and the
// six-PSU pool drawn chassis-wide below — because they belong to no bay.
// Regions colored by temperature on a fixed 20–110 °C scale. Clicking a
// fan kills it; clicking a PSU kills it; anything else pins its card.

const MARGIN = 2.5;
const T_MIN = 20;
const T_MAX = 110;

const STOPS: [number, string][] = [
  [0.0, "#2c4fd8"],
  [0.25, "#2596be"],
  [0.5, "#7fbf5a"],
  [0.7, "#e8c33d"],
  [0.85, "#e07b28"],
  [1.0, "#c8281e"],
];

function lerpColor(a: string, b: string, f: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * f));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function tempColor(t: number): string {
  const f = Math.max(0, Math.min(1, (t - T_MIN) / (T_MAX - T_MIN)));
  for (let i = 1; i < STOPS.length; i++) {
    if (f <= STOPS[i][0]) {
      const [f0, c0] = STOPS[i - 1];
      const [f1, c1] = STOPS[i];
      return lerpColor(c0, c1, (f - f0) / (f1 - f0));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

export function ChassisView({
  anatomy,
  state,
  deadFans,
  emptyBays,
  storageBays,
  selected,
  onSelect,
  onToggleFan,
}: {
  anatomy: ChassisMap;
  state: SimState | null;
  deadFans: Set<number>;
  emptyBays: Set<number>;
  storageBays: Set<number>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  onToggleFan?: (index: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: ChassisRegion) => r.x + MARGIN;
  const ry = (r: ChassisRegion) => r.y + MARGIN;
  const rpm = state?.fanRpmPct ?? 0;
  const flowClass = rpm > 66 ? "flow-fast" : rpm > 33 ? "flow-mid" : "flow-slow";

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 10}`}
      aria-label={`${anatomy.name} thermal map`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {/* Airflow arrows: front (bays, top) to rear exhaust (bottom). */}
      {state?.poweredOn && (
        <g
          className={flowClass}
          stroke={tempColor(state.inletC)}
          strokeWidth={0.5}
          strokeDasharray="2.5 2"
          opacity={0.8}
        >
          {[16, 42, 68].map((x) => (
            <line key={x} x1={x} y1={3} x2={x} y2={H - 3} />
          ))}
        </g>
      )}
      {anatomy.regions.map((r) => {
        const temp = state?.regionTemps[r.id] ?? T_MIN;
        const isSel = r.id === selected;
        const isFan = r.kind === "cooling";
        const fanIdx = isFan ? Number(r.id.split("-")[1]) : -1;
        const dead = isFan && deadFans.has(fanIdx);
        const isBay = r.kind === "bay";
        const bayIdx = isBay ? Number(r.id.split("-")[1]) - 1 : -1;
        const empty = isBay && emptyBays.has(bayIdx);
        const isPsu = r.kind === "power";
        const psuDark =
          isPsu && state ? state.regionTemps[r.id] <= state.inletC + 0.2 : false;
        const fill = dead || empty ? "#20242a" : tempColor(temp);
        const hot = state?.hottestSlot === bayIdx + 1 && isBay && !empty;
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              if (isFan && onToggleFan) onToggleFan(fanIdx);
              else onSelect?.(isSel ? null : r.id);
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              stroke={
                isSel ? "var(--accent)"
                : dead ? "#c8281e"
                : hot ? "#e8c33d"
                : "#0d1420"
              }
              strokeWidth={isSel || hot ? 0.6 : 0.3}
              strokeDasharray={empty ? "1.5 1" : undefined}
              opacity={dead || (isPsu && psuDark) ? 0.85 : 1}
            />
            {/* Bay labels rotated vertical (tall thin slots). */}
            {isBay && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={empty ? "#5a6b82" : "#0d1420"}
                fontSize={2.2}
                fontWeight={600}
                transform={`rotate(-90 ${rx(r) + r.w / 2} ${ry(r) + r.h / 2})`}
              >
                {empty
                  ? `Bay ${bayIdx + 1} · empty`
                  : storageBays.has(bayIdx)
                    ? `Sled ${bayIdx + 1} · storage`
                    : r.label}
              </text>
            )}
            {isBay && !empty && state && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.6}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={1.7}
                fontWeight={700}
              >
                {temp.toFixed(0)}°
              </text>
            )}
            {!isBay && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2 + 0.7}
                textAnchor="middle"
                fill={dead ? "#e07b6a" : "#0d1420"}
                fontSize={Math.min(1.8, (r.w - 1) / (r.label.length * 0.62))}
                fontWeight={600}
              >
                {dead ? "✕ dead" : r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Fixed color legend, 20–110 °C. */}
      <g>
        {Array.from({ length: 30 }, (_, i) => (
          <rect
            key={i}
            x={MARGIN + i * 2}
            y={H + 1.2}
            width={2}
            height={2.2}
            fill={tempColor(T_MIN + ((i + 0.5) / 30) * (T_MAX - T_MIN))}
          />
        ))}
        <text x={MARGIN} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          20 °C
        </text>
        <text x={MARGIN + 60} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          110 °C
        </text>
        <text x={W - MARGIN} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          BAYS (intake) → FANS → PSU POOL · click a fan to kill it
        </text>
      </g>
    </svg>
  );
}
