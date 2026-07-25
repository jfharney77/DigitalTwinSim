import type { CloudAnatomy, CloudRegion, RegionKind } from "../types";

// Data-driven stack renderer: draws whatever regions the backend sends, so
// a different stack is data (anatomy.py), not code — same principle as the
// other twins' ChassisView/RackView/ClusterView.
//
// Two pieces of derived drawing carry the argument, both computed from
// region kinds:
//
//   1. Unused hypervisor slots are drawn dimmed rather than hidden. The
//      empty slots are the product — an option not taken is still an
//      option — so removing them would quietly reverse the lesson.
//   2. Each pool draws its own separate line up to the hypervisor row.
//      On a hyperconverged diagram compute and storage would share one
//      connector because they are one purchase; here they visibly do not.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  controlplane: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  workload: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  hypervisor: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  compute: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  storage: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  network: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  fabric: { fill: "#1a2030", stroke: "#3a4566", text: "#7b8bb5" },
};

// Brighter fills for regions doing work at this step.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  controlplane: "#4a3d18",
  workload: "#1d3a66",
  hypervisor: "#2e3370",
  compute: "#24452e",
  storage: "#1d4555",
  network: "#3a3355",
  fabric: "#2c3550",
};

const POOL_KINDS: RegionKind[] = ["compute", "storage", "network"];

export function StackView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: CloudAnatomy;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: CloudRegion) => r.x + MARGIN;
  const ry = (r: CloudRegion) => r.y + MARGIN;
  const mid = (r: CloudRegion) => rx(r) + r.w / 2;

  const hypervisors = anatomy.regions.filter((r) => r.kind === "hypervisor");
  const pools = POOL_KINDS.map((k) =>
    anatomy.regions.find((r) => r.kind === k),
  ).filter(Boolean) as CloudRegion[];
  const hvRowTop = hypervisors.length ? Math.min(...hypervisors.map(ry)) : 0;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} stack map`}
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

      {/* Each pool rises to the hypervisor row on its own line. Three
          separate connectors, because they are three separate purchases. */}
      <g stroke="#2b3950" strokeWidth={0.25} fill="none" strokeDasharray="1.2 1.2">
        {pools.map((p) => (
          <line
            key={`lift-${p.id}`}
            x1={mid(p)}
            y1={ry(p)}
            x2={mid(p)}
            y2={hvRowTop + (hypervisors[0]?.h ?? 0)}
          />
        ))}
      </g>

      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        // An unused hypervisor slot is dimmed, never hidden: the empty
        // slots are the product.
        const dimmed = r.kind === "hypervisor" && !isActive && !!active?.size;
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const fontSize = hSize;
        const stroke = isSel || isActive ? "var(--accent)" : style.stroke;
        return (
          <g
            key={r.id}
            className={isActive ? "an-region region-active" : "an-region"}
            opacity={dimmed ? 0.42 : 1}
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
              strokeDasharray={dimmed ? "1 1" : undefined}
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
            {dimmed && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.6}
                textAnchor="middle"
                fill="#5a6b82"
                fontSize={1.4}
              >
                available
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: what is decoupled from what. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        ONE CONTROL PLANE ↑
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        THREE POOLS, BOUGHT SEPARATELY ↓
      </text>
    </svg>
  );
}
