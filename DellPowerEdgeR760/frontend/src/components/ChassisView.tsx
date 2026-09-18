import type { ChassisAnatomy, ChassisRegion, RegionKind } from "../types";

// Data-driven chassis floorplan renderer: draws whatever regions the backend
// sends, so new servers are data (anatomy.py), not code — same principle as
// the GPU app's AnatomyView. The `active` set lights regions up during the
// power-on trace playback.

const MARGIN = 2.5; // chassis outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  storage: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  cooling: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  cpu: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  memory: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  power: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  expansion: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  management: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  board: { fill: "#1a2433", stroke: "#2b3a4f", text: "#8a9bb5" },
};

// Brighter fills for regions currently carrying power/activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  storage: "#1d3a66",
  cooling: "#1d4a45",
  cpu: "#4a3d18",
  memory: "#3a3355",
  power: "#4a2a24",
  expansion: "#24452e",
  management: "#1d4555",
  board: "#2b3a54",
};

export function ChassisView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
}: {
  anatomy: ChassisAnatomy;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
  // Tour mode: a camera box in the anatomy's own coordinates (the margin is
  // added here), and a per-region layer look — ghost opacity plus an explode
  // offset. Both optional; without them the floorplan draws as before.
  camera?: { x: number; y: number; w: number; h: number };
  regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  // Region coords are chassis-relative; shift them inside the outline.
  const rx = (r: ChassisRegion) => r.x + MARGIN;
  const ry = (r: ChassisRegion) => r.y + MARGIN;
  // The full view is W x (H + 4): the outline plus the orientation labels.
  // A camera box maps to the same framing scaled down, so the whole-map box
  // reproduces the default viewBox exactly and a tween never jumps.
  const viewBox = camera
    ? `${camera.x} ${camera.y} ${camera.w + 2 * MARGIN} ${
        camera.h + (2 * MARGIN + 4) * (camera.h / anatomy.height)
      }`
    : `0 0 ${W} ${H + 4}`;

  return (
    <svg
      viewBox={viewBox}
      aria-label={`${anatomy.name} chassis floorplan`}
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
        const look = regionLook?.(r.id);
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks (fans, backplane),
        // else tooltip only. 0.62 ≈ glyph advance per unit font.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        // Last resort before tooltip-only: two lines, split at the space
        // nearest the middle ("Power distribution" in the narrow PSU column).
        const mid = r.label.length / 2;
        const cut = r.label
          .split("")
          .reduce(
            (best, ch, i) =>
              ch === " " && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))
                ? i
                : best,
            -1,
          );
        const lines =
          cut > 0 ? [r.label.slice(0, cut), r.label.slice(cut + 1)] : [];
        const wSize = lines.length
          ? Math.min(
              1.9,
              r.h * 0.3,
              (r.w - 1.6) / (Math.max(...lines.map((l) => l.length)) * 0.62),
            )
          : 0;
        const showWrapped = !showLabel && !showVLabel && wSize >= 0.9;
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
            style={
              look
                ? {
                    opacity: look.opacity,
                    transform: `translate(${look.dx}px, ${look.dy}px)`,
                  }
                : undefined
            }
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
            {/* Native tooltip where the page has no hover card of its own. */}
            {!onHover && <title>{r.label}</title>}
            {showWrapped && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2 - wSize * 0.25}
                textAnchor="middle"
                fill={isSel || isActive ? "var(--accent)" : style.text}
                fontSize={wSize}
                letterSpacing={0.12}
              >
                <tspan x={rx(r) + r.w / 2}>{lines[0]}</tspan>
                <tspan x={rx(r) + r.w / 2} dy={wSize * 1.15}>
                  {lines[1]}
                </tspan>
              </text>
            )}
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
      {/* Orientation: drive bay / bezel end vs PSU / cabling end. */}
      <text
        x={MARGIN}
        y={H + 2.6}
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        FRONT — drive bay
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        REAR — power &amp; I/O
      </text>
    </svg>
  );
}
