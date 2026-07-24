import type { ClusterAnatomy, ClusterRegion, RegionKind } from "../types";

// Data-driven pool renderer: draws whatever regions the backend sends, so a
// bigger pool is data (anatomy.py), not code — same principle as the other
// twins' ChassisView/RackView/FabricView. The `active` set lights regions up
// during playback.
//
// Two derived link sets carry the architecture, both computed from region
// kinds rather than ids:
//
//   1. Client-to-node paths, drawn always. Every client reaches every node
//      directly, with nothing in between. The absence of a convergence
//      point in this picture *is* the product.
//   2. Node-to-node paths, drawn only while rebuilding. Every surviving
//      node reconstructs a sliver from every other, so the mesh that
//      appears during a rebuild is many-to-many — which is why recovery
//      gets faster as the pool grows.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  client: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  network: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  coordinator: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  node: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  protection: { fill: "#2e1a1a", stroke: "#6b3a3a", text: "#c97f7f" },
  management: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
};

// Brighter fills for regions currently doing work in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  client: "#1d3a66",
  network: "#3a3355",
  coordinator: "#4a3d18",
  node: "#24452e",
  protection: "#4d2a2a",
  management: "#1d4555",
};

export function ClusterView({
  anatomy,
  active,
  selected,
  rebuilding,
  onSelect,
  onHover,
}: {
  anatomy: ClusterAnatomy;
  active?: Set<string>;
  selected?: string | null;
  // True during the rebuild step — draws the many-to-many recovery mesh.
  rebuilding?: boolean;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: ClusterRegion) => r.x + MARGIN;
  const ry = (r: ClusterRegion) => r.y + MARGIN;
  const mid = (r: ClusterRegion) => rx(r) + r.w / 2;

  const clients = anatomy.regions.find((r) => r.kind === "client");
  const nodes = anatomy.regions.filter((r) => r.kind === "node");
  // Only nodes still in play take part in the meshes.
  const live = active ? nodes.filter((n) => active.has(n.id)) : nodes;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} pool map`}
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

      {/* Client-to-node paths: direct, with nothing in between. */}
      {clients && (
        <g stroke="#2b3950" strokeWidth={0.25} fill="none">
          {live.map((n) => (
            <line
              key={`c-${n.id}`}
              x1={mid(clients)}
              y1={ry(clients) + clients.h}
              x2={mid(n)}
              y2={ry(n)}
            />
          ))}
        </g>
      )}

      {/* The recovery mesh: every surviving node to every other. */}
      {rebuilding && (
        <g stroke="var(--accent)" strokeWidth={0.35} fill="none" opacity={0.75}>
          {live.map((a, i) =>
            live.slice(i + 1).map((b) => (
              <line
                key={`r-${a.id}-${b.id}`}
                x1={mid(a)}
                y1={ry(a) + a.h}
                x2={mid(b)}
                y2={ry(b) + b.h}
              />
            )),
          )}
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
      {/* Orientation: what is missing between these two bands. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        CLIENTS ↑ — each holds the map
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        NODES ↓ — no controller between them
      </text>
    </svg>
  );
}
