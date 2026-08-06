import type { FabricAnatomy, FabricRegion, RegionKind } from "../types";

// Data-driven topology renderer: draws whatever regions the backend sends,
// so a bigger or different fabric is data (anatomy.py), not code — same
// principle as the other twins' ChassisView/RackView/SiteView. The `active`
// set lights regions up during fabric playback. A dashed spur joins the
// subnet manager to the spine tier: control reaches the fabric, data never
// passes through the manager, and the line style says so.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  spine: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  leaf: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  endpoint: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  manager: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  optics: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  cooling: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
};

// Brighter fills for regions currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  spine: "#2e3370",
  leaf: "#1d3a66",
  endpoint: "#4a3d18",
  manager: "#1d4555",
  optics: "#3a3355",
  cooling: "#1d4a45",
};

export function FabricView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: FabricAnatomy;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: FabricRegion) => r.x + MARGIN;
  const ry = (r: FabricRegion) => r.y + MARGIN;

  // Draw the leaf/spine mesh: every leaf uplinks to every spine. The links
  // are derived from the region data, so a bigger fabric needs no code
  // change — the mesh is the topology's whole point, so it must be visible.
  const spines = anatomy.regions.filter((r) => r.kind === "spine");
  const leaves = anatomy.regions.filter((r) => r.kind === "leaf");
  const endpoints = anatomy.regions.filter((r) => r.kind === "endpoint");
  const manager = anatomy.regions.find((r) => r.kind === "manager");
  const mid = (r: FabricRegion) => rx(r) + r.w / 2;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} topology`}
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

      {/* Leaf-to-spine mesh, drawn under the blocks. */}
      <g stroke="#2b3950" strokeWidth={0.25} fill="none">
        {leaves.map((l) =>
          spines.map((s) => (
            <line
              key={`${l.id}-${s.id}`}
              x1={mid(l)}
              y1={ry(l)}
              x2={mid(s)}
              y2={ry(s) + s.h}
            />
          )),
        )}
        {/* Each leaf down to the rack it serves. */}
        {leaves.map((l, i) => {
          const e = endpoints[i];
          return e ? (
            <line
              key={`${l.id}-${e.id}`}
              x1={mid(l)}
              y1={ry(l) + l.h}
              x2={mid(e)}
              y2={ry(e)}
            />
          ) : null;
        })}
      </g>

      {/* The manager's control spur: dashed, to the spine tier — control
          reaches the fabric; data never passes through the manager. */}
      {manager && spines[0] && (
        <line
          x1={rx(manager) + manager.w}
          y1={ry(manager) + manager.h / 2}
          x2={rx(spines[0])}
          y2={ry(spines[0]) + spines[0].h / 2}
          stroke="#2e5666"
          strokeWidth={0.3}
          strokeDasharray="1 0.8"
          fill="none"
        />
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
      {/* Orientation: the two-hop path, top to bottom; the brain beside it. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        SM beside the tree — routes in, data never through
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        GPU RACKS ↓ — any pair, two hops
      </text>
    </svg>
  );
}
