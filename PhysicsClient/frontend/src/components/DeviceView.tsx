import type { DeviceMap, DeviceRegion, SimState } from "../types";

// The device interior, painted as a thermal map on a fixed 15–105 °C
// scale (same color-blind-safe ramp as the R760 thermal twin). The skin
// zone gets its own annotation because its limit (46 °C) sits far below
// the silicon limits — the ramp alone would make a dangerous palm rest
// look reassuringly blue.

const MARGIN = 2.5;
const T_MIN = 15;
const T_MAX = 105;
const SKIN_CAP = 46;

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

export function DeviceView({
  anatomy,
  state,
  selected,
  onSelect,
  underlay,
  xray = "schematic",
}: {
  anatomy: DeviceMap;
  state: SimState | null;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  underlay?: string | null;
  xray?: "schematic" | "hybrid" | "photo";
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: DeviceRegion) => r.x + MARGIN;
  const ry = (r: DeviceRegion) => r.y + MARGIN;

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
      {underlay && xray !== "schematic" && (
        <image
          href={underlay}
          x={MARGIN}
          y={MARGIN}
          width={W - 2 * MARGIN}
          height={H - 2 * MARGIN}
          preserveAspectRatio="xMidYMid slice"
          opacity={xray === "photo" ? 1 : 0.85}
        />
      )}
      <g opacity={xray === "photo" ? 0.12 : xray === "hybrid" ? 0.6 : 1}>
      {anatomy.regions.map((r) => {
        const temp = state?.regionTemps[r.id] ?? T_MIN;
        const isSel = r.id === selected;
        const isSkin = r.kind === "skin";
        const skinHot = isSkin && temp >= SKIN_CAP - 1;
        const fill = tempColor(temp);
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.42, (r.w - 1.4) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.4) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.2 && hSize >= 1.0;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.0;
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(isSel ? null : r.id);
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              stroke={isSel ? "var(--accent)" : skinHot ? "#ffffff" : "#0d1420"}
              strokeWidth={isSel ? 0.6 : skinHot ? 0.5 : 0.3}
              strokeDasharray={skinHot ? "1.2 0.8" : undefined}
            />
            {showLabel && !showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.4)}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={Math.max(hSize, 1.0)}
                fontWeight={600}
                letterSpacing={0.1}
              >
                {skinHot ? `${r.label} — AT CAP` : r.label}
              </text>
            )}
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={vSize}
                fontWeight={600}
                transform={`rotate(-90 ${rx(r) + r.w / 2} ${ry(r) + r.h / 2})`}
              >
                {r.label}
              </text>
            )}
            {r.w >= 12 && r.h >= 8 && state && (
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
          </g>
        );
      })}
      </g>
      {/* Fixed color legend with the skin cap marked. */}
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
        {(() => {
          const capX = MARGIN + ((SKIN_CAP - T_MIN) / (T_MAX - T_MIN)) * 60;
          return (
            <g>
              <line x1={capX} y1={H + 0.6} x2={capX} y2={H + 4} stroke="#fff" strokeWidth={0.35} />
              <text x={capX} y={H + 6.6} textAnchor="middle" fill="#8fa3bd" fontSize={1.6}>
                skin cap
              </text>
            </g>
          );
        })()}
        <text x={MARGIN} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          {T_MIN} °C
        </text>
        <text x={MARGIN + 62} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          {T_MAX} °C
        </text>
        <text x={W - MARGIN} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          service view · click a zone for its story
        </text>
      </g>
    </svg>
  );
}
