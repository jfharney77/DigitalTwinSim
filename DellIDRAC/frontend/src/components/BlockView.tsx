import type { Block, RegionKind, SubsystemMap } from "../types";

// Data-driven subsystem block-diagram renderer: draws whatever blocks the
// backend sends, so a new controller is data (anatomy.py), not code — same
// principle as the R760 app's ChassisView. The `active` set lights blocks up
// during the bring-up trace playback.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  soc: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  memory: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  network: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  sideband: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  io: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  power: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  security: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  sensor: { fill: "#1a2433", stroke: "#2b3a4f", text: "#8a9bb5" },
};

// Brighter fills for blocks currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  soc: "#4a3d18",
  memory: "#3a3355",
  network: "#1d3a66",
  sideband: "#1d4a45",
  io: "#24452e",
  power: "#4a2a24",
  security: "#1d4555",
  sensor: "#2b3a54",
};

export function BlockView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: SubsystemMap;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  // Block coords are diagram-relative; shift them inside the outline.
  const rx = (r: Block) => r.x + MARGIN;
  const ry = (r: Block) => r.y + MARGIN;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} subsystem block diagram`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5}
        y={0.5}
        width={W - 1}
        height={H - 1}
        rx={1.5}
        fill="#0d1420"
        stroke="#1f2935"
        strokeWidth={0.6}
      />
      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        // Fit the label to the block: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        // 0.62 ≈ glyph advance per unit font.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.0;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.0;
        const fontSize = hSize;
        const stroke = isSel
          ? "var(--accent)"
          : isActive
            ? "var(--accent)"
            : style.stroke;
        return (
          <g
            key={r.id}
            className={isActive ? "an-region region-active" : "an-region"}
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(isSel ? null : r.id);
            }}
            onMouseMove={(e) => onHover?.(r.id, e.clientX, e.clientY)}
            onMouseLeave={() => onHover?.(null, 0, 0)}
          >
            <rect
              x={rx(r)}
              y={ry(r)}
              width={r.w}
              height={r.h}
              rx={0.8}
              fill={isActive ? KIND_ACTIVE_FILL[r.kind] : style.fill}
              stroke={stroke}
              strokeWidth={isSel || isActive ? 0.5 : 0.25}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={isSel || isActive ? "var(--accent)" : style.text}
                fontSize={vSize}
                letterSpacing={0.2}
                transform={`rotate(-90 ${rx(r) + r.w / 2} ${ry(r) + r.h / 2})`}
              >
                {r.label}
              </text>
            )}
            {showLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + fontSize * 0.35 : 2.6)}
                textAnchor="middle"
                fill={isSel || isActive ? "var(--accent)" : style.text}
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: host-facing management buses vs the outside world. */}
      <text
        x={MARGIN}
        y={H + 2.6}
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        HOST SIDE — sideband buses
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        OUTSIDE — network &amp; console
      </text>
    </svg>
  );
}
