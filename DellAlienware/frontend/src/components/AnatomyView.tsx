import type { Anatomy, Region, RegionKind } from "../types";

// Data-driven interior floorplan renderer: draws whatever regions the backend
// sends, so new machines are data (anatomy.py), not code — same principle as
// the GPU app's AnatomyView and the R760 ChassisView. The `active` set lights
// regions up during trace playback.

const MARGIN = 2.5; // chassis outline padding, in the anatomy's own units
const MIN_LABEL = 1.05; // smallest legible label, in map units at full view

// Split a label into two lines at the separator or space nearest its middle.
function splitLabel(label: string): [string, string] | null {
  const mid = label.length / 2;
  let best = -1;
  for (let i = 0; i < label.length; i++) {
    if (label[i] === " " && (best < 0 || Math.abs(i - mid) < Math.abs(best - mid))) best = i;
  }
  if (best < 0) return null;
  const a = label.slice(0, best).replace(/\s*·\s*$/, "").trim();
  const b = label.slice(best + 1).replace(/^\s*·\s*/, "").trim();
  return a && b ? [a, b] : null;
}

export const KIND_STYLE: Record<
  RegionKind,
  { fill: string; stroke: string; text: string }
> = {
  board: { fill: "#1a2433", stroke: "#2b3a4f", text: "#8a9bb5" },
  power: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  battery: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  cooling: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  memory: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  storage: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  io: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  display: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  wireless: { fill: "#26202b", stroke: "#5c4a66", text: "#a583b5" },
};

// Brighter fills for regions currently carrying power/activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  board: "#2b3a54",
  power: "#4a2a24",
  battery: "#24452e",
  cooling: "#1d4a45",
  memory: "#3a3355",
  storage: "#1d3a66",
  io: "#4a3d18",
  display: "#1d4555",
  wireless: "#40334a",
};

export function AnatomyView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
}: {
  anatomy: Anatomy;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
  // Guided tour: a camera box in the anatomy's own coordinates, and a
  // per-region ghost/offset. Without them the view draws exactly as before.
  camera?: { x: number; y: number; w: number; h: number };
  regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  // Region coords are chassis-relative; shift them inside the outline.
  const rx = (r: Region) => r.x + MARGIN;
  const ry = (r: Region) => r.y + MARGIN;

  // The whole-map camera (0, 0, width, height) reproduces the default
  // viewBox exactly, so the tour's first frame does not jump.
  const viewBox = camera
    ? `${camera.x} ${camera.y} ${camera.w + 2 * MARGIN} ${
        camera.h + (2 * MARGIN + 4) * (camera.h / anatomy.height)
      }`
    : `0 0 ${W} ${H + 4}`;

  // Zoomed in by the tour camera, a label may be smaller in map units and
  // still read at the same size on screen; small blocks (the DC-in jack, the
  // EC, the charger) get their names back, wrapping onto two lines if needed.
  const zoom = camera ? Math.max(1, anatomy.width / camera.w) : 1;
  const minLabel = MIN_LABEL / zoom;

  return (
    <svg
      viewBox={viewBox}
      aria-label={`${anatomy.name} interior floorplan`}
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
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= minLabel;
        const wrapped = camera && !showLabel ? splitLabel(r.label) : null;
        const wSize = wrapped
          ? Math.min(
              1.9,
              (r.h - 1.2) / 2.4,
              (r.w - 1.6) / (Math.max(wrapped[0].length, wrapped[1].length) * 0.62),
            )
          : 0;
        const showWrap = !!wrapped && wSize >= minLabel;
        const showVLabel =
          !showLabel && !showWrap && !!r.label && r.w >= 3 && vSize >= minLabel;
        const stroke = isSel || isActive ? "var(--accent)" : style.stroke;
        const look = regionLook?.(r.id);
        return (
          <g
            key={r.id}
            className={isActive ? "an-region region-active" : "an-region"}
            style={
              look
                ? { opacity: look.opacity, transform: `translate(${look.dx}px, ${look.dy}px)` }
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
            {showWrap && wrapped && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2 - wSize * 0.25}
                textAnchor="middle"
                fill={isSel || isActive ? "var(--accent)" : style.text}
                fontSize={wSize}
                letterSpacing={0.1}
              >
                <tspan x={rx(r) + r.w / 2}>{wrapped[0]}</tspan>
                <tspan x={rx(r) + r.w / 2} dy={wSize * 1.2}>
                  {wrapped[1]}
                </tspan>
              </text>
            )}
            {showLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.6)}
                textAnchor="middle"
                fill={isSel || isActive ? "var(--accent)" : style.text}
                fontSize={hSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: bottom cover off, viewed from below; rear at y=0. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        ↑ REAR — hinge, exhaust, DC-in
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        ↓ FRONT — palm rest
      </text>
    </svg>
  );
}
