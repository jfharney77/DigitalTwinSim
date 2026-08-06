import type { PlatformMap, PlatformRegion, RegionKind } from "../types";

// Data-driven architecture-diagram renderer: draws whatever regions the
// backend sends, so a bigger estate or a different platform is data
// (anatomy.py), not code — same principle as the CloudIQ twin's
// PlatformView and the hardware twins' ChassisView. The `active` set
// lights regions up during onboarding playback.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  endpoint: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  network: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  identity: { fill: "#0f2a30", stroke: "#2e5c66", text: "#4fa0c9" },
  orchestrator: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  blueprint: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  catalog: { fill: "#22290f", stroke: "#55662e", text: "#a0b54f" },
  policy: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  observability: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
};

// Brighter fills for regions currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  endpoint: "#4a3d18",
  network: "#1d3a66",
  identity: "#1d4555",
  orchestrator: "#2e3370",
  blueprint: "#3a3355",
  catalog: "#3a451d",
  policy: "#4a2a24",
  observability: "#24452e",
};

export function PlatformView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: PlatformMap;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: PlatformRegion) => r.x + MARGIN;
  const ry = (r: PlatformRegion) => r.y + MARGIN;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} architecture diagram`}
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
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
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
      {/* Orientation: the estate on the left, control on the right. */}
      <text
        x={MARGIN}
        y={H + 2.6}
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        THE ESTATE — sites with no IT staff
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        CONTROL &amp; INSIGHT — one Orchestrator
      </text>
    </svg>
  );
}
