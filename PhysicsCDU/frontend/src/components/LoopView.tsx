import type { LoopMap, LoopRegion, SimState } from "../types";

// The cooling loop drawn as a circuit: facility plant → heat exchanger
// → manifolds → tray banks, regions colored by temperature on a fixed
// 10–80 °C scale (color-blind-safe blue→yellow→red ramp). Dashed flow
// lines animate with pump speed. Clicking a pump toggles a failure;
// clicking anything else pins its detail card.

const MARGIN = 2.5;
const T_MIN = 10;
const T_MAX = 80;

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

export function LoopView({
  anatomy,
  state,
  deadPumps,
  installedPumps,
  selected,
  onSelect,
  onTogglePump,
}: {
  anatomy: LoopMap;
  state: SimState | null;
  deadPumps: Set<number>;
  installedPumps: number;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  onTogglePump?: (index: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: LoopRegion) => r.x + MARGIN;
  const ry = (r: LoopRegion) => r.y + MARGIN;
  const speed = state?.pumpSpeedPct ?? 0;
  const flowClass = speed > 66 ? "flow-fast" : speed > 33 ? "flow-mid" : "flow-slow";
  const supplyColor = tempColor(state?.secSupplyC ?? T_MIN);
  const returnColor = tempColor(state?.secReturnC ?? T_MIN);
  const facColor = tempColor(state?.facSupplyC ?? T_MIN);

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 10}`}
      aria-label={`${anatomy.name} loop map`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {/* Flow lines: facility loop (left), secondary loop (right). */}
      {state && state.secFlowLpm > 0 && (
        <g className={flowClass} strokeWidth={0.5} strokeDasharray="2.5 2" opacity={0.85} fill="none">
          {/* Facility: plant → hx (supply, top) and back (return, bottom). */}
          <path d={`M ${8 + MARGIN} 23 H ${33 + MARGIN}`} stroke={facColor} />
          <path d={`M ${33 + MARGIN} 36 H ${8 + MARGIN}`} stroke={tempColor(state.facReturnC)} />
          {/* Secondary: hx → supply manifold → (trays) → return manifold → pumps → hx. */}
          <path d={`M ${40 + MARGIN} 21 H ${70 + MARGIN}`} stroke={supplyColor} />
          <path d={`M ${97 + MARGIN} 56 H ${62 + MARGIN} V 50 H ${40 + MARGIN}`} stroke={returnColor} />
        </g>
      )}
      {anatomy.regions.map((r) => {
        const temp = state?.regionTemps[r.id] ?? T_MIN;
        const isSel = r.id === selected;
        const isPump = r.kind === "pump";
        const pumpIdx = isPump ? Number(r.id.split("-")[1]) : -1;
        const dead = isPump && (deadPumps.has(pumpIdx) || pumpIdx >= installedPumps);
        const absentPump = isPump && pumpIdx >= installedPumps;
        const isTray = r.kind === "tray";
        const trayIdx = isTray ? Number(r.id.split("-")[1]) : -1;
        const trayStatus = isTray && state ? state.bankStatus[trayIdx] : null;
        const trayAbsent = trayStatus === "absent";
        const trayTripped = trayStatus === "tripped";
        const muted = dead || trayAbsent;
        const fill = muted ? "#20242a" : tempColor(temp);
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
              if (isPump && !absentPump && onTogglePump) onTogglePump(pumpIdx);
              else onSelect?.(isSel ? null : r.id);
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              stroke={
                isSel ? "var(--accent)"
                : dead && !absentPump ? "#c8281e"
                : trayTripped ? "#c8281e"
                : "#0d1420"
              }
              strokeWidth={isSel ? 0.6 : trayTripped ? 0.5 : 0.3}
              strokeDasharray={trayAbsent || absentPump ? "1 1" : undefined}
              opacity={muted ? 0.9 : 1}
            />
            {(showLabel || (dead && !absentPump)) && !showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.4)}
                textAnchor="middle"
                fill={dead && !absentPump ? "#e07b6a" : muted ? "#5a6b82" : "#0d1420"}
                fontSize={Math.max(hSize, 1.0)}
                fontWeight={600}
                letterSpacing={0.1}
              >
                {dead && !absentPump ? "✕ dead" : trayTripped ? `✕ ${r.label}` : r.label}
              </text>
            )}
            {showVLabel && !dead && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={muted ? "#5a6b82" : "#0d1420"}
                fontSize={vSize}
                fontWeight={600}
                transform={`rotate(-90 ${rx(r) + r.w / 2} ${ry(r) + r.h / 2})`}
              >
                {r.label}
              </text>
            )}
            {/* Temperature readout on the larger blocks. */}
            {r.w >= 10 && r.h >= 7 && state && !muted && (
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
      {/* Fixed color legend, 10–80 °C. */}
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
          10 °C
        </text>
        <text x={MARGIN + 60} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          80 °C
        </text>
        <text x={W - MARGIN} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          FACILITY (left) ↔ RACK (right) · click a pump to fail it
        </text>
      </g>
    </svg>
  );
}
