import type { DetectAnatomy, DetectRegion, RegionKind } from "../types";

// Data-driven detection-map renderer: draws whatever regions the backend
// sends, so a different timeline is data (anatomy.py), not code — same
// principle as the other twins' ChassisView/RackView/ClusterView.
//
// This view carries one idea the others do not have to. Corruption is
// *invisible* until content analysis reveals it, so snapshots are drawn
// identically until `revealed` goes true. Before that moment, a viewer
// looking at the timeline genuinely cannot tell which copies are ruined —
// which is exactly the position an administrator is in, and the reason the
// product exists. Marking them early would quietly undo the whole lesson.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  array: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  snapshot: { fill: "#1a2030", stroke: "#3a4566", text: "#7b8bb5" },
  inspect: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  classifier: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  models: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
  verdict: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  recovery: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
};

// Brighter fills for regions currently doing work in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  array: "#1d3a66",
  snapshot: "#2c3550",
  inspect: "#3a3355",
  classifier: "#2e3370",
  models: "#1d4555",
  verdict: "#4a3d18",
  recovery: "#24452e",
};

// Only ever applied once the analysis has established it.
const CORRUPT_FILL = "#3d1414";
const CORRUPT_STROKE = "#8c3a3a";

export function TimelineView({
  anatomy,
  active,
  selected,
  corruptedCount = 0,
  revealed = false,
  namedClean = -1,
  onSelect,
  onHover,
}: {
  anatomy: DetectAnatomy;
  active?: Set<string>;
  selected?: string | null;
  // How many of the newest snapshots contain corruption.
  corruptedCount?: number;
  // Whether content analysis has run. Until it has, corruption is drawn
  // exactly like health, because that is what it looks like.
  revealed?: boolean;
  // 1-based index of the snapshot the verdict named; -1 before a verdict.
  namedClean?: number;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: DetectRegion) => r.x + MARGIN;
  const ry = (r: DetectRegion) => r.y + MARGIN;

  // The timeline, oldest to newest. Corruption always affects the newest
  // copies, so the boundary is derived rather than hard-coded.
  const snaps = anatomy.regions
    .filter((r) => r.kind === "snapshot")
    .sort((a, b) => a.x - b.x);
  const firstCorruptIdx = snaps.length - corruptedCount;
  const isCorrupt = (i: number) => corruptedCount > 0 && i >= firstCorruptIdx;
  const named = snaps[namedClean - 1] ?? null;
  const axisY = snaps.length > 0 ? ry(snaps[0]) + snaps[0].h + 1.6 : 0;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 4}`}
      aria-label={`${anatomy.name} detection map`}
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

      {/* The time axis under the snapshot row. */}
      {snaps.length > 0 && (
        <g>
          <line
            x1={rx(snaps[0])}
            y1={axisY}
            x2={rx(snaps[snaps.length - 1]) + snaps[snaps.length - 1].w}
            y2={axisY}
            stroke="#2b3950"
            strokeWidth={0.2}
          />
          <text
            x={rx(snaps[0])}
            y={axisY + 2.2}
            fill="#5a6b82"
            fontSize={1.5}
            letterSpacing={0.2}
          >
            OLDEST
          </text>
          <text
            x={rx(snaps[snaps.length - 1]) + snaps[snaps.length - 1].w}
            y={axisY + 2.2}
            textAnchor="end"
            fill="#5a6b82"
            fontSize={1.5}
            letterSpacing={0.2}
          >
            NEWEST
          </text>
        </g>
      )}

      {/* The verdict: a marker on the timeline, which is the whole output. */}
      {named && (
        <g>
          <line
            x1={rx(named) + named.w / 2}
            y1={ry(named) - 1.6}
            x2={rx(named) + named.w / 2}
            y2={ry(named)}
            stroke="var(--accent)"
            strokeWidth={0.5}
          />
          <text
            x={rx(named) + named.w / 2}
            y={ry(named) - 2.4}
            textAnchor="middle"
            fill="var(--accent)"
            fontSize={1.6}
            letterSpacing={0.15}
          >
            last clean
          </text>
        </g>
      )}

      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        const snapIdx = snaps.indexOf(r);
        const corrupt = revealed && snapIdx >= 0 && isCorrupt(snapIdx);
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const fontSize = hSize;
        const fill = corrupt
          ? CORRUPT_FILL
          : isActive
            ? KIND_ACTIVE_FILL[r.kind]
            : style.fill;
        const stroke = corrupt
          ? CORRUPT_STROKE
          : isSel || isActive
            ? "var(--accent)"
            : style.stroke;
        const textFill = corrupt
          ? "#d98b8b"
          : isSel || isActive
            ? "var(--accent)"
            : style.text;
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
              fill={fill}
              stroke={stroke}
              strokeWidth={isSel || isActive || corrupt ? 0.5 : 0.25}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={textFill}
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
                fill={textFill}
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
            {corrupt && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.6}
                textAnchor="middle"
                fill="#d98b8b"
                fontSize={1.5}
              >
                corrupt
              </text>
            )}
          </g>
        );
      })}
      {/* Orientation: what the diagram is actually navigating. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        EVIDENCE ↓ — read the bytes
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        CONCLUSION ↓ — name a copy
      </text>
    </svg>
  );
}
