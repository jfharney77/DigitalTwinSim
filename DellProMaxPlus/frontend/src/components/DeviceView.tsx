import type { DeviceAnatomy, DeviceRegion, RegionKind } from "../types";

// Data-driven inference-path renderer: draws whatever regions the backend
// sends, so a different card or a different machine is data (anatomy.py),
// not code — same principle as the other twins' ChassisView/RackView/
// FabricView. The `active` set lights regions up during playback.
//
// The one piece of derived geometry is the weights path: storage → link →
// AI memory, found by region kind rather than by id, and drawn heavier
// while the link is actually carrying traffic. That path is the subject of
// the whole twin, so it has to be visible — and it has to be visibly quiet
// for every step after load.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  host: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  memory: { fill: "#16233a", stroke: "#3a5288", text: "#5f88d8" },
  storage: { fill: "#1a2030", stroke: "#3a4566", text: "#7b8bb5" },
  link: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  npu: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  aimemory: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  thermal: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  power: { fill: "#2e1a1a", stroke: "#6b3a3a", text: "#c97f7f" },
  runtime: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
};

// Brighter fills for regions currently doing work in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  host: "#1d3a66",
  memory: "#23386b",
  storage: "#2c3550",
  link: "#4a3d18",
  npu: "#2e3370",
  aimemory: "#24452e",
  thermal: "#1d4a45",
  power: "#4d2a2a",
  runtime: "#3a3355",
};

export function DeviceView({
  anatomy,
  active,
  selected,
  linkBusy,
  onSelect,
  onHover,
}: {
  anatomy: DeviceAnatomy;
  active?: Set<string>;
  selected?: string | null;
  // True while weights are actually crossing the boundary — the one phase
  // where the path is a bandwidth story rather than a quiet line.
  linkBusy?: boolean;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: DeviceRegion) => r.x + MARGIN;
  const ry = (r: DeviceRegion) => r.y + MARGIN;

  // The weights path, derived from region kinds so it survives a redraw of
  // the map: model file → boundary → the memory it will live in.
  const byKind = (k: RegionKind) => anatomy.regions.find((r) => r.kind === k);
  const src = byKind("storage");
  const strip = byKind("link");
  const dest = byKind("aimemory");
  const midY = (r: DeviceRegion) => ry(r) + r.h / 2;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} inference path`}
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

      {/* The weights path, drawn under the blocks. Heavy while loading,
          faint afterwards — the visual form of "it only crosses once". */}
      {src && strip && dest && (
        <g
          stroke={linkBusy ? "var(--accent)" : "#2b3950"}
          strokeWidth={linkBusy ? 0.7 : 0.25}
          strokeDasharray={linkBusy ? undefined : "1.4 1.2"}
          fill="none"
        >
          <path
            d={`M ${rx(src) + src.w} ${midY(src)}
                L ${rx(strip)} ${midY(src)}
                M ${rx(strip) + strip.w} ${midY(dest)}
                L ${rx(dest)} ${midY(dest)}`}
          />
          <line
            x1={rx(strip) + strip.w / 2}
            y1={midY(src)}
            x2={rx(strip) + strip.w / 2}
            y2={midY(dest)}
          />
        </g>
      )}

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
      {/* Orientation: the boundary the weights cross exactly once. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        HOST ← the model at rest
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        CARD → the model resident
      </text>
    </svg>
  );
}
