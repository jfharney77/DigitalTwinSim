import type { ClusterAnatomy, ClusterRegion, RegionKind } from "../types";

// Data-driven cluster floorplan renderer: draws whatever regions the backend
// sends, so a bigger or different cluster is data (anatomy.py), not code —
// same principle as the GPU app's AnatomyView and the chassis twins'
// ChassisView. The `active` set lights regions up during first-run playback.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  compute: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  memory: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  storage: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  boot: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  network: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  management: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  power: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  fabric: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
};

// Brighter fills for regions currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  compute: "#4a3d18",
  memory: "#3a3355",
  storage: "#1d3a66",
  boot: "#1d4a45",
  network: "#24452e",
  management: "#1d4555",
  power: "#4a2a24",
  fabric: "#2e3370",
};

// A refused region: the error token for the outline, a dark red wash for the
// fill so the label stays legible on the dark diagram.
const FAILED_FILL = "#3a1216";
const FAILED_TEXT = "#ff8a94";

export function ClusterView({
  anatomy,
  active,
  failed,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
}: {
  anatomy: ClusterAnatomy;
  active?: Set<string>;
  // Regions a failure scenario marks as refused: drawn in the error colour
  // with a dashed outline, so they never read as merely idle.
  failed?: Set<string>;
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
  const rx = (r: ClusterRegion) => r.x + MARGIN;
  const ry = (r: ClusterRegion) => r.y + MARGIN;
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
      aria-label={`${anatomy.name} cluster floorplan`}
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
        const isFailed = failed?.has(r.id) ?? false;
        const look = regionLook?.(r.id);
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const fontSize = hSize;
        const stroke = isFailed
          ? "var(--dell-error)"
          : isSel
          ? "var(--accent)"
          : isActive
            ? "var(--accent)"
            : style.stroke;
        return (
          <g
            key={r.id}
            className={
              isFailed
                ? "an-region region-failed"
                : isActive
                  ? "an-region region-active"
                  : "an-region"
            }
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(isSel ? null : r.id);
            }}
            onMouseMove={(e) => onHover?.(r.id, e.clientX, e.clientY)}
            onMouseLeave={() => onHover?.(null, 0, 0)}
            style={
              look
                ? {
                    opacity: look.opacity,
                    transform: `translate(${look.dx}px, ${look.dy}px)`,
                  }
                : undefined
            }
          >
            <rect
              x={rx(r)}
              y={ry(r)}
              width={r.w}
              height={r.h}
              rx={0.8}
              fill={
                isFailed
                  ? FAILED_FILL
                  : isActive
                    ? KIND_ACTIVE_FILL[r.kind]
                    : style.fill
              }
              stroke={stroke}
              strokeWidth={isFailed || isSel || isActive ? 0.5 : 0.25}
              strokeDasharray={isFailed ? "1.2 0.7" : undefined}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={isFailed ? FAILED_TEXT : isSel || isActive ? "var(--accent)" : style.text}
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
                fill={isFailed ? FAILED_TEXT : isSel || isActive ? "var(--accent)" : style.text}
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: drive-bay front vs NIC/power rear, as on the chassis twins. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        FRONT — NVMe drive bays
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        REAR — NIC &amp; power
      </text>
    </svg>
  );
}
