import type { DieAnatomy, DieRegion, RegionKind } from "../types";

// Data-driven floorplan renderer: draws whatever regions the backend sends,
// so new dies are data (anatomy.py), not code — same principle as DieView.

const MARGIN = 2.5; // die outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  compute: { fill: "var(--sm-idle)", stroke: "var(--sm-edge)", text: "#8a9bb5" },
  l2: { fill: "#141d2c", stroke: "#31456b", text: "#5a6b82" },
  mem: { fill: "var(--mem)", stroke: "#3d5a9e", text: "#4f7cff" },
  nvlink: { fill: "#15282a", stroke: "#2e5c54", text: "#4fa08a" },
  io: { fill: "#1d1a2b", stroke: "#453a66", text: "#8a7ab5" },
  media: { fill: "#281f2a", stroke: "#663a5c", text: "#b57aa4" },
  cache: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  fabric: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
};

// Faint grid of unit tiles inside a compute cluster suggesting its SMs/CUs.
function ComputeTexture({ x, y, w, h }: { x: number; y: number; w: number; h: number }) {
  const pad = 1.4;
  const top = 3.6; // room for the label
  const iw = w - 2 * pad;
  const ih = h - top - pad;
  if (iw < 4 || ih < 4) return null;
  const cols = Math.max(2, Math.round(iw / 4.4));
  const rows = Math.max(2, Math.round(ih / 4.4));
  const gap = 0.7;
  const tw = (iw - gap * (cols - 1)) / cols;
  const th = (ih - gap * (rows - 1)) / rows;
  const tiles = [];
  for (let i = 0; i < rows; i++) {
    for (let j = 0; j < cols; j++) {
      tiles.push(
        <rect
          key={`${i}-${j}`}
          x={x + pad + j * (tw + gap)}
          y={y + top + i * (th + gap)}
          width={tw}
          height={th}
          rx={0.4}
          fill="#141c29"
          stroke="#22304466"
          strokeWidth={0.15}
        />,
      );
    }
  }
  return <>{tiles}</>;
}

export function AnatomyView({
  anatomy,
  selected,
  onSelect,
  onHover,
}: {
  anatomy: DieAnatomy;
  selected: string | null;
  onSelect: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  // Region coords are die-relative; shift them inside the outline.
  const rx = (r: DieRegion) => r.x + MARGIN;
  const ry = (r: DieRegion) => r.y + MARGIN;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      aria-label={`${anatomy.name} die floorplan`}
      onClick={() => onSelect(null)}
    >
      <rect
        x={0.5}
        y={0.5}
        width={W - 1}
        height={H - 1}
        rx={2.5}
        fill="#0d1420"
        stroke="#1f2935"
        strokeWidth={0.6}
      />
      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks (memory PHY columns),
        // else tooltip only. 0.62 ≈ monospace glyph advance per unit font.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const fontSize = hSize;
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              onSelect(isSel ? null : r.id);
            }}
            onMouseMove={(e) => onHover(r.id, e.clientX, e.clientY)}
            onMouseLeave={() => onHover(null, 0, 0)}
          >
            <rect
              x={rx(r)}
              y={ry(r)}
              width={r.w}
              height={r.h}
              rx={0.8}
              fill={style.fill}
              stroke={isSel ? "var(--accent)" : style.stroke}
              strokeWidth={isSel ? 0.5 : 0.25}
            />
            {r.kind === "compute" && (
              <ComputeTexture x={rx(r)} y={ry(r)} w={r.w} h={r.h} />
            )}
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={isSel ? "var(--accent)" : style.text}
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
                fill={isSel ? "var(--accent)" : style.text}
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
