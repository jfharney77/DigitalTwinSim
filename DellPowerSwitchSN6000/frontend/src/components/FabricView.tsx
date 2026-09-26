import type { FabricAnatomy, FabricRegion, LinkStatus, RegionKind } from "../types";

// Data-driven topology renderer: draws whatever regions the backend sends,
// so a bigger or different fabric is data (anatomy.py), not code — same
// principle as the other twins' ChassisView/RackView/SiteView. The `active`
// set lights regions up during fabric playback.

const MARGIN = 2.5; // outline padding, in the anatomy's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  spine: { fill: "#1c1f3f", stroke: "#5a4fc9", text: "#8f7fff" },
  leaf: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  endpoint: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  optics: { fill: "#241f33", stroke: "#4a4066", text: "#8a7ab5" },
  telemetry: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  cooling: { fill: "#122b2b", stroke: "#2e5c54", text: "#4fa08a" },
  management: { fill: "#12282e", stroke: "#2e5666", text: "#4fa0c9" },
};

// Brighter fills for regions currently carrying activity in the trace.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  spine: "#2e3370",
  leaf: "#1d3a66",
  endpoint: "#4a3d18",
  optics: "#3a3355",
  telemetry: "#24452e",
  cooling: "#1d4a45",
  management: "#1d4555",
};

export function FabricView({
  anatomy,
  active,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
  sick,
  hot,
}: {
  // The saturated leaf-spine link ("<leaf id>:<spine id>") and its load, drawn
  // in amber so the busiest-link number has a place on the map.
  hot?: { hotLink: string | null; peakLinkPercent: number } | null;
  // Failure scenarios: the link under suspicion. It is drawn exactly like
  // the other links until telemetry has located it — before that the
  // operator cannot tell it apart either, and marking it early would undo
  // the lesson (the Cyber Detect twin's `revealed` rule).
  sick?: {
    sickLink: string | null;
    sickLinkStatus: LinkStatus | null;
    sickLinkLocated: boolean;
    trafficSteered: boolean;
    symbolErrorsPerSec: number;
  } | null;
  anatomy: FabricAnatomy;
  active?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the photo tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
  // Tour mode: a camera box in the anatomy's own coordinates (the margin is
  // added here) and a per-region look (layer peel). Both optional; without
  // them the view draws exactly as before.
  camera?: { x: number; y: number; w: number; h: number };
  regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
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
  const mid = (r: FabricRegion) => rx(r) + r.w / 2;

  const faulty =
    !!sick &&
    sick.sickLinkLocated &&
    (sick.symbolErrorsPerSec > 0 || sick.sickLinkStatus !== "up");
  const sickId = faulty ? sick!.sickLink : null;
  const sickLeaf = leaves.find((l) => sickId?.startsWith(`${l.id}:`));
  const sickSpine = spines.find((s) => sickId?.endsWith(`:${s.id}`));
  // Carrying job traffic: solid. Routed around, shut down or retraining: dashed.
  const sickCarrying =
    faulty && sick!.sickLinkStatus === "up" && !sick!.trafficSteered;
  const sickLabel = !faulty
    ? ""
    : sick!.sickLinkStatus === "up"
      ? sick!.trafficSteered
        ? "UP · NO TRAFFIC"
        : "UP · ERRING"
      : sick!.sickLinkStatus === "admin-down"
        ? "SHUT DOWN"
        : "RETRAINING";

  const hotId = hot?.hotLink ?? null;
  const hotLeaf = leaves.find((l) => hotId?.startsWith(`${l.id}:`));
  const hotSpine = spines.find((s) => hotId?.endsWith(`:${s.id}`));

  // A camera box maps to the same framing scaled down, so the whole-map box
  // reproduces the default viewBox exactly and a tween never jumps.
  const viewBox = camera
    ? `${camera.x} ${camera.y} ${camera.w + 2 * MARGIN} ${
        camera.h + (2 * MARGIN + 4) * (camera.h / anatomy.height)
      }`
    : `0 0 ${W} ${H + 4}`;

  return (
    <svg
      viewBox={viewBox}
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

      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        const look = regionLook?.(r.id);
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
            style={
              look
                ? {
                    opacity: look.opacity,
                    transform: `translate(${look.dx}px, ${look.dy}px)`,
                  }
                : undefined
            }
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
      {/* The saturated link, drawn over the blocks in amber with its load. */}
      {hotLeaf && hotSpine && (
        <g className="hot-link" pointerEvents="none">
          <line
            x1={mid(hotLeaf)}
            y1={ry(hotLeaf)}
            x2={mid(hotSpine)}
            y2={ry(hotSpine) + hotSpine.h}
            stroke="#e8a33d"
            strokeWidth={0.7}
          />
          <text
            x={(mid(hotLeaf) + mid(hotSpine)) / 2 + 1.2}
            y={(ry(hotLeaf) + ry(hotSpine) + hotSpine.h) / 2 - 1}
            fill="#e8a33d"
            fontSize={1.5}
            letterSpacing={0.2}
            stroke="var(--bg, #0d1320)"
            strokeWidth={0.5}
            paintOrder="stroke"
          >
            {hot!.peakLinkPercent}% · BUSIEST
          </text>
        </g>
      )}
      {/* The located sick link, drawn over the blocks (the optics band sits across
          the uplinks), in the diagram's error colour. */}
      {sickLeaf && sickSpine && (
        <g className="sick-link" pointerEvents="none" data-status={sick!.sickLinkStatus ?? ""}>
          <line
            x1={mid(sickLeaf)}
            y1={ry(sickLeaf)}
            x2={mid(sickSpine)}
            y2={ry(sickSpine) + sickSpine.h}
            stroke="var(--core-hot)"
            strokeWidth={0.6}
            strokeDasharray={sickCarrying ? undefined : "1.2 1"}
          />
          <circle cx={mid(sickLeaf)} cy={ry(sickLeaf)} r={0.8} fill="var(--core-hot)" />
          <circle
            cx={mid(sickSpine)}
            cy={ry(sickSpine) + sickSpine.h}
            r={0.8}
            fill="var(--core-hot)"
          />
          <text
            x={(mid(sickLeaf) + mid(sickSpine)) / 2 + 1.2}
            y={(ry(sickLeaf) + ry(sickSpine) + sickSpine.h) / 2 + 2.4}
            fill="var(--core-hot)"
            fontSize={1.5}
            letterSpacing={0.2}
            stroke="var(--bg, #0d1320)"
            strokeWidth={0.5}
            paintOrder="stroke"
          >
            {sickLabel}
          </text>
        </g>
      )}

      {/* Orientation: the two-hop path, top to bottom. */}
      <text x={MARGIN} y={H + 2.6} fill="#5a6b82" fontSize={1.7} letterSpacing={0.3}>
        SPINE ↑ — every leaf reaches every spine
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
