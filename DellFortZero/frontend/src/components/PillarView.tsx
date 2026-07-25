import type { Pillar, RegionKind, ZeroTrustMap } from "../types";

// Data-driven zero-trust map renderer: draws whatever pillars the backend
// sends, so a different architecture is data (anatomy.py), not code — same
// principle as the other twins' ChassisView/RackView/ClusterView.
//
// The derived geometry here is a set of spokes from every pillar to the
// policy engine, computed from region kinds. That is deliberately the
// *only* connective drawing: no ring, no enclosing box, no boundary of any
// kind. Every other map in this repo carries its lesson in a boundary; this
// one carries it in the absence of one, and adding a perimeter shape for
// visual tidiness would quietly reverse the whole argument.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  identity: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  device: { fill: "#16233a", stroke: "#3a5288", text: "#5f88d8" },
  network: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  workload: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  data: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  visibility: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  automation: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  policy: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
};

// Brighter fills for pillars currently feeding a decision.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  identity: "#1d3a66",
  device: "#23386b",
  network: "#3a3355",
  workload: "#2e3370",
  data: "#24452e",
  visibility: "#1d4555",
  automation: "#1d4a45",
  policy: "#4a3d18",
};

export function PillarView({
  anatomy,
  active,
  selected,
  breached = false,
  onSelect,
  onHover,
}: {
  anatomy: ZeroTrustMap;
  active?: Set<string>;
  selected?: string | null;
  // True while an attacker holds a position inside the network. Nothing
  // about the drawing opens up — which is the point being made.
  breached?: boolean;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: Pillar) => r.x + MARGIN;
  const ry = (r: Pillar) => r.y + MARGIN;
  const cx = (r: Pillar) => rx(r) + r.w / 2;
  const cy = (r: Pillar) => ry(r) + r.h / 2;

  const policy = anatomy.regions.find((r) => r.kind === "policy") ?? null;
  const pillars = anatomy.regions.filter((r) => r.kind !== "policy");

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} architecture map`}
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

      {/* Spokes to the decision point. Every pillar feeds every ruling, so
          a lit pillar draws a lit spoke — the decision is visibly made
          from all of them at once at the decide step. */}
      {policy && (
        <g fill="none">
          {pillars.map((p) => {
            const lit = (active?.has(p.id) ?? false) && (active?.has(policy.id) ?? false);
            return (
              <line
                key={`spoke-${p.id}`}
                x1={cx(p)}
                y1={cy(p)}
                x2={cx(policy)}
                y2={cy(policy)}
                stroke={lit ? "var(--accent)" : "#2b3950"}
                strokeWidth={lit ? 0.4 : 0.18}
                strokeDasharray={lit ? undefined : "1.2 1.2"}
              />
            );
          })}
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

      {/* The intruder, drawn where a perimeter would have called them safe.
          Nothing about the map opens up around them. */}
      {breached && (
        <text
          x={W / 2}
          y={H - 2}
          textAnchor="middle"
          fill="#d98b8b"
          fontSize={1.8}
          letterSpacing={0.2}
        >
          intruder inside the network — reaching nothing
        </text>
      )}

      {/* Orientation: what this diagram has, and what it deliberately lacks. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        SEVEN CO-EQUAL PILLARS
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        A CENTRE, BUT NO INSIDE
      </text>
    </svg>
  );
}
