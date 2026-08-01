import type { ClusterAnatomy, ClusterRegion, RegionKind } from "../types";

// Data-driven cluster renderer: draws whatever regions the backend sends, so
// a bigger cluster is data (anatomy.py), not code — same principle as the
// other twins' ChassisView/RackView/FabricView. The `active` set lights
// regions up during playback.
//
// One region gets special treatment, keyed on kind rather than id: the
// `namespace` region. It is the only shape in the map that spans every node,
// and it is the twin's whole argument — one file system, no volumes — so it
// is drawn as a single continuous band with its own fill and, when active, a
// soft glow. Everything else belongs to a node or sits in a band; the
// namespace refuses to be partitioned and the drawing has to say so.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  node: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  media: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  protocol: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  interconnect: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  namespace: { fill: "#0f2e33", stroke: "#2e7d8a", text: "#5fc4d4" },
  management: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
};

// Brighter fills for regions currently doing work in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  node: "#24452e",
  media: "#3a3355",
  protocol: "#1d3a66",
  interconnect: "#4a3d18",
  namespace: "#155965",
  management: "#1d4555",
};

export function ClusterView({
  anatomy,
  active,
  selected,
  rebalancing,
  onSelect,
  onHover,
}: {
  anatomy: ClusterAnatomy;
  active?: Set<string>;
  selected?: string | null;
  // True while the cluster redistributes data onto a new node — draws the
  // node-to-node redistribution links across the interconnect.
  rebalancing?: boolean;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: ClusterRegion) => r.x + MARGIN;
  const ry = (r: ClusterRegion) => r.y + MARGIN;
  const mid = (r: ClusterRegion) => rx(r) + r.w / 2;

  const nodes = anatomy.regions.filter((r) => r.kind === "node");
  // Only nodes lit by the trace take part in the rebalance links: before the
  // expansion four light, after it six — the view just paints what the trace
  // says.
  const live = active ? nodes.filter((n) => active.has(n.id)) : nodes;
  const namespaceActive = anatomy.regions.some(
    (r) => r.kind === "namespace" && (active?.has(r.id) ?? false),
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} cluster map`}
      onClick={() => onSelect?.(null)}
    >
      <defs>
        {/* Soft glow for the one shape that spans every node. */}
        <filter id="ns-glow" x="-20%" y="-60%" width="140%" height="220%">
          <feGaussianBlur stdDeviation="0.9" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
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

      {/* Rebalance links: node to node across the back-end interconnect. */}
      {rebalancing && (
        <g stroke="var(--accent)" strokeWidth={0.35} fill="none" opacity={0.75}>
          {live.map((a, i) =>
            live.slice(i + 1).map((b) => (
              <line
                key={`rb-${a.id}-${b.id}`}
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
        const isNamespace = r.kind === "namespace";
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
            ? isNamespace
              ? "#5fc4d4"
              : "var(--accent)"
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
              rx={isNamespace ? 1.4 : 0.8}
              fill={isActive ? KIND_ACTIVE_FILL[r.kind] : style.fill}
              stroke={stroke}
              strokeWidth={isSel || isActive ? 0.5 : isNamespace ? 0.4 : 0.25}
              opacity={isNamespace ? 0.92 : 1}
              filter={isNamespace && isActive ? "url(#ns-glow)" : undefined}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={isSel || isActive ? (isNamespace ? "#8fe3f0" : "var(--accent)") : style.text}
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
                fill={isSel || isActive ? (isNamespace ? "#8fe3f0" : "var(--accent)") : style.text}
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: what refuses to be partitioned. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        PROTOCOLS ↑ — every node answers every protocol
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill={namespaceActive ? "#5fc4d4" : "#5a6b82"}
        fontSize={1.7}
        letterSpacing={0.3}
      >
        ONE NAMESPACE — no volume boundaries below it
      </text>
    </svg>
  );
}
