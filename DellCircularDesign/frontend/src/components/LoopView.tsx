import type { LifecycleMap, LifecycleRegion, RegionKind } from "../types";

// Data-driven lifecycle renderer: draws whatever regions the backend sends,
// so a different loop is data (anatomy.py), not code — same principle as the
// other twins' ChassisView/RackView/FabricView. The `active` set lights
// regions up during playback.
//
// What makes this view unlike every other in the repo: the edges. Each
// region carries `flowsTo`, the directed flow of material, and the drawing
// derives arrows from that data. Three families of edge, told apart by the
// kinds at their ends rather than by hard-coded ids:
//
// - forward edges — the ordinary path around the loop, gently bowed.
// - return edges — refurbish → deployment (a device goes back to work) and
//   reclaim → materials (matter goes back to the start). Drawn at two
//   different radii on purpose: reuse and recycling are not the same thing,
//   and reuse is the tighter, better circle.
// - the loss edge — anything flowing into a `loss` region. Dashed, muted
//   red, and deliberately present: a lifecycle map that shows only the
//   virtuous paths is marketing. The leak is drawn, and measured.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  materials: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  manufacture: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  packaging: { fill: "#2a2118", stroke: "#66513a", text: "#b08d5f" },
  deployment: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  service: { fill: "#0f2e33", stroke: "#2e7d8a", text: "#5fc4d4" },
  recovery: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  refurbish: { fill: "#132b26", stroke: "#2e6655", text: "#5fc4a8" },
  reclaim: { fill: "#232b12", stroke: "#556b2b", text: "#a8c94f" },
  loss: { fill: "#2e1414", stroke: "#7a3030", text: "#c96a5f" },
};

// Brighter fills for regions currently doing work in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  materials: "#24452e",
  manufacture: "#4a3d18",
  packaging: "#453423",
  deployment: "#1d3a66",
  service: "#155965",
  recovery: "#3a3355",
  refurbish: "#1d473d",
  reclaim: "#3a4a18",
  loss: "#4d1f1f",
};

type EdgeFamily = "forward" | "return-reuse" | "return-reclaim" | "loss";

function edgeFamily(from: LifecycleRegion, to: LifecycleRegion): EdgeFamily {
  if (to.kind === "loss") return "loss";
  if (from.kind === "refurbish" && to.kind === "deployment") return "return-reuse";
  if (to.kind === "materials" && from.kind !== "materials") return "return-reclaim";
  return "forward";
}

const EDGE_STROKE: Record<EdgeFamily, string> = {
  forward: "#5a6b82",
  "return-reuse": "#5fc4a8",
  "return-reclaim": "#a8c94f",
  loss: "#c96a5f",
};

const EDGE_MARKER: Record<EdgeFamily, string> = {
  forward: "url(#arrow-fwd)",
  "return-reuse": "url(#arrow-reuse)",
  "return-reclaim": "url(#arrow-reclaim)",
  loss: "url(#arrow-loss)",
};

// How far the control point bows off the straight line, as a fraction of the
// edge length. The two returns get distinct radii — that difference is the
// drawing's argument that reuse is the tighter circle.
const EDGE_BOW: Record<EdgeFamily, number> = {
  forward: 0.1,
  "return-reuse": 0.22,
  "return-reclaim": 0.38,
  loss: 0.12,
};

// Clip a segment from a rect's center toward an outside point to the rect's
// border, so arrows start and end at the box edge rather than under it.
function borderPoint(
  r: LifecycleRegion,
  cx: number,
  cy: number,
  tx: number,
  ty: number,
): { x: number; y: number } {
  const dx = tx - cx;
  const dy = ty - cy;
  if (dx === 0 && dy === 0) return { x: cx, y: cy };
  const sx = dx !== 0 ? r.w / 2 / Math.abs(dx) : Infinity;
  const sy = dy !== 0 ? r.h / 2 / Math.abs(dy) : Infinity;
  const t = Math.min(sx, sy);
  return { x: cx + dx * t, y: cy + dy * t };
}

export function LoopView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: LifecycleMap;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: LifecycleRegion) => r.x + MARGIN;
  const ry = (r: LifecycleRegion) => r.y + MARGIN;
  const cx = (r: LifecycleRegion) => rx(r) + r.w / 2;
  const cy = (r: LifecycleRegion) => ry(r) + r.h / 2;

  const byId = new Map(anatomy.regions.map((r) => [r.id, r]));
  const mapCx = W / 2;
  const mapCy = H / 2;

  const edges = anatomy.regions.flatMap((from) =>
    from.flowsTo
      .map((toId) => byId.get(toId))
      .filter((to): to is LifecycleRegion => !!to)
      .map((to) => {
        const family = edgeFamily(from, to);
        const x1 = cx(from);
        const y1 = cy(from);
        const x2 = cx(to);
        const y2 = cy(to);
        const a = borderPoint(from, x1, y1, x2, y2);
        const b = borderPoint(to, x2, y2, x1, y1);
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const len = Math.hypot(dx, dy) || 1;
        // Perpendicular unit normal; pick the side pointing away from the
        // map's center so returns arc around the outside of the loop.
        let nx = -dy / len;
        let ny = dx / len;
        const mx = (a.x + b.x) / 2;
        const my = (a.y + b.y) / 2;
        if ((mx - mapCx) * nx + (my - mapCy) * ny < 0) {
          nx = -nx;
          ny = -ny;
        }
        const bow = EDGE_BOW[family] * len;
        const px = mx + nx * bow;
        const py = my + ny * bow;
        const lit = (active?.has(from.id) ?? false) && (active?.has(to.id) ?? false);
        return { from, to, family, a, b, px, py, lit };
      }),
  );

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} lifecycle loop`}
      onClick={() => onSelect?.(null)}
    >
      <defs>
        {(
          [
            ["arrow-fwd", EDGE_STROKE.forward],
            ["arrow-reuse", EDGE_STROKE["return-reuse"]],
            ["arrow-reclaim", EDGE_STROKE["return-reclaim"]],
            ["arrow-loss", EDGE_STROKE.loss],
          ] as const
        ).map(([id, color]) => (
          <marker
            key={id}
            id={id}
            viewBox="0 0 6 6"
            refX={5}
            refY={3}
            markerWidth={5}
            markerHeight={5}
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 6 3 L 0 6 z" fill={color} />
          </marker>
        ))}
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

      {/* The flows, under the boxes so labels stay readable. */}
      <g fill="none">
        {edges.map((e) => (
          <path
            key={`edge-${e.from.id}-${e.to.id}`}
            d={`M ${e.a.x} ${e.a.y} Q ${e.px} ${e.py} ${e.b.x} ${e.b.y}`}
            stroke={e.lit ? "var(--accent)" : EDGE_STROKE[e.family]}
            strokeWidth={e.lit ? 0.5 : 0.32}
            strokeDasharray={e.family === "loss" ? "1.1 0.9" : undefined}
            opacity={e.family === "loss" ? 0.85 : e.lit ? 0.95 : 0.6}
            markerEnd={e.lit ? undefined : EDGE_MARKER[e.family]}
          />
        ))}
      </g>

      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        const isLoss = r.kind === "loss";
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const stroke = isSel
          ? "var(--accent)"
          : isActive
            ? isLoss
              ? "#c96a5f"
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
              rx={0.8}
              fill={isActive ? KIND_ACTIVE_FILL[r.kind] : style.fill}
              stroke={stroke}
              strokeWidth={isSel || isActive ? 0.5 : 0.25}
              strokeDasharray={isLoss ? "0.9 0.7" : undefined}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={isSel || (isActive && !isLoss) ? "var(--accent)" : style.text}
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
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.6)}
                textAnchor="middle"
                fill={isSel || (isActive && !isLoss) ? "var(--accent)" : style.text}
                fontSize={hSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}

      {/* Orientation: what kind of diagram this is. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        A LOOP, NOT A LINE — two returns, at two radii
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#c96a5f"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        THE LEAK IS DRAWN — lost mass is measured, not hidden
      </text>
    </svg>
  );
}
