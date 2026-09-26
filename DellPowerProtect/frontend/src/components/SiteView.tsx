import type { RegionKind, SiteAnatomy, SiteRegion } from "../types";

// Data-driven site-map renderer: draws whatever regions the backend sends,
// so a bigger or different deployment is data (anatomy.py), not code —
// same principle as the other twins' ChassisView/RackView. The `active`
// set lights regions up during lifecycle playback.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  workload: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  backup: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  appliance: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  gap: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  analytics: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  recovery: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  mgmt: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
};

// Brighter fills for regions currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  workload: "#3a3355",
  backup: "#1d4555",
  appliance: "#1d3a66",
  gap: "#4a2a24",
  analytics: "#4a3d18",
  recovery: "#24452e",
  mgmt: "#2e3370",
};

// The shared error token (packages/twin-ui tokens.css). The label uses a
// lighter tint of it, because the token itself is too dark to read on the
// diagram's dark fill.
const ERROR = "var(--dell-error, #ce1126)";
const ERROR_TEXT = "#ff8a96";
const FAILED_FILL = "#3a1218";

export function SiteView({
  anatomy,
  active,
  failed,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
}: {
  anatomy: SiteAnatomy;
  active?: Set<string>;
  // Regions in an alert condition (failure scenarios): drawn in the error
  // colour with a dashed outline, so they never read as ordinary activity.
  failed?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
  // Tour mode: a camera box in the anatomy's own coordinates (the margin is
  // added here), and a per-region layer look — ghost opacity plus an offset.
  // Without them the map draws exactly as before.
  camera?: { x: number; y: number; w: number; h: number };
  regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: SiteRegion) => r.x + MARGIN;
  const ry = (r: SiteRegion) => r.y + MARGIN;

  // A camera box maps to the same framing scaled down, so the whole-map box
  // reproduces the default viewBox exactly and a tween never jumps.
  const viewBox = camera
    ? `${camera.x} ${camera.y} ${camera.w + 2 * MARGIN} ${
        camera.h + (2 * MARGIN + 4) * (camera.h / anatomy.height)
      }`
    : `0 0 ${W} ${H + 4}`;

  // The orientation labels tell a newcomer which half is which, so a zoomed
  // camera must not clip them. Zoomed in, they ride the bottom corners of the
  // frame, scaled with it, and each shows only while its half is in view.
  const zoom = camera ? camera.h / anatomy.height : 1;
  const zoomed = !!camera && zoom < 0.999;
  const gap = anatomy.regions.find((r) => r.kind === "gap");
  const gapLeft = gap ? gap.x + MARGIN : W / 2;
  const gapRight = gap ? gap.x + gap.w + MARGIN : W / 2;
  const viewLeft = camera ? camera.x : 0;
  const viewRight = camera ? camera.x + camera.w + 2 * MARGIN : W;
  const viewBottom = camera
    ? camera.y + camera.h + (2 * MARGIN + 4) * zoom
    : H + 4;
  const labelY = zoomed ? viewBottom - 1.4 * zoom : H + 2.6;
  const labelSize = 1.7 * zoom;
  const showProduction = !zoomed || viewLeft < gapLeft - 4;
  const showVault = !zoomed || viewRight > gapRight + 4;
  // Only one half in view: the short name fits whatever the frame width.
  const vaultLabel =
    zoomed && showProduction && camera!.w < anatomy.width * 0.75
      ? "VAULT"
      : "CYBER RECOVERY VAULT — BEYOND THE GAP";

  return (
    <svg
      viewBox={viewBox}
      aria-label={`${anatomy.name} site map`}
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
          ? ERROR
          : isSel
          ? "var(--accent)"
          : isActive
            ? "var(--accent)"
            : style.stroke;
        return (
          <g
            key={r.id}
            className={
              (isActive ? "an-region region-active" : "an-region") +
              (isFailed ? " region-failed" : "")
            }
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
              fill={
                isFailed
                  ? FAILED_FILL
                  : isActive
                    ? KIND_ACTIVE_FILL[r.kind]
                    : style.fill
              }
              stroke={stroke}
              strokeWidth={isFailed ? 0.7 : isSel || isActive ? 0.5 : 0.25}
              strokeDasharray={isFailed ? "1.6 0.9" : undefined}
            />
            {isFailed && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.4}
                textAnchor="middle"
                fill={ERROR_TEXT}
                fontSize={1.5}
                letterSpacing={0.2}
              >
                SPACE ALERT
              </text>
            )}
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={
                  isFailed ? ERROR_TEXT : isSel || isActive ? "var(--accent)" : style.text
                }
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
                fill={
                  isFailed ? ERROR_TEXT : isSel || isActive ? "var(--accent)" : style.text
                }
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: production on the left, the vault beyond the gap. */}
      {zoomed && (showProduction || showVault) && (
        <rect
          x={viewLeft}
          y={labelY - 2.2 * zoom}
          width={viewRight - viewLeft}
          height={3.6 * zoom}
          fill="#0d1420"
          opacity={0.85}
        />
      )}
      {showProduction && (
        <text
          x={zoomed ? viewLeft + MARGIN * zoom : MARGIN}
          y={labelY}
          fill="#5a6b82"
          fontSize={labelSize}
          letterSpacing={0.3 * zoom}
        >
          PRODUCTION
        </text>
      )}
      {showVault && (
        <text
          x={zoomed ? viewRight - MARGIN * zoom : W - MARGIN}
          y={labelY}
          textAnchor="end"
          fill="#5a6b82"
          fontSize={labelSize}
          letterSpacing={0.3 * zoom}
        >
          {vaultLabel}
        </text>
      )}
    </svg>
  );
}
