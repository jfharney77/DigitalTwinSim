import type { PlatformMap, PlatformRegion, RegionKind } from "../types";

// Data-driven architecture-diagram renderer: draws whatever regions the
// backend sends, so the platform layout is data (anatomy.py), not code — same
// principle as the hardware twins' ChassisView. The flow runs left (telemetry
// in) to right (insights out). The `active` set lights regions up during
// pipeline playback.

const MARGIN = 2.5; // diagram outline padding, in the map's own units

const KIND_STYLE: Record<RegionKind, { fill: string; stroke: string; text: string }> = {
  source: { fill: "#12233a", stroke: "#3d5a9e", text: "#4f7cff" },
  gateway: { fill: "#0f2a30", stroke: "#2f7f8a", text: "#4fd6df" },
  ingest: { fill: "#16203a", stroke: "#3a4a8a", text: "#6f8fff" },
  analytics: { fill: "#2b2412", stroke: "#6b5a2b", text: "#c9a94f" },
  security: { fill: "#2b1a1a", stroke: "#6b3a3a", text: "#c97a6a" },
  insight: { fill: "#16281a", stroke: "#3a6647", text: "#6ab585" },
  assistant: { fill: "#1f1a33", stroke: "#5a4fc9", text: "#9f8fff" },
  action: { fill: "#22290f", stroke: "#5a662b", text: "#a4c94f" },
};

// Brighter fills for regions currently doing work in the pipeline.
const KIND_ACTIVE_FILL: Record<RegionKind, string> = {
  source: "#1d3a66",
  gateway: "#17454e",
  ingest: "#22305a",
  analytics: "#4a3d18",
  security: "#4a2a24",
  insight: "#24452e",
  assistant: "#322a5a",
  action: "#3a451a",
};

// A failing region: the stroke and cross use the skin's error token; the fill
// and label are its dark-panel tints, since the token itself is too dark to
// read as text on the diagram.
const FAILED_FILL = "#3a1216";
const FAILED_TEXT = "#ff9aa5";

export function PlatformView({
  anatomy,
  active,
  failed,
  selected,
  onSelect,
  onHover,
  camera,
  regionLook,
}: {
  anatomy: PlatformMap;
  active?: Set<string>;
  // Regions blocked or starved at this step (failure scenarios): drawn in the
  // error colour with a dashed outline, whether or not they are also active.
  // The break itself is marked on the gateway-to-cloud link, below.
  failed?: Set<string>;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  // Client (viewport) coords, for the tooltip; null on leave.
  onHover?: (id: string | null, cx: number, cy: number) => void;
  // Tour mode: a camera box in the map's own coordinates (the margin is
  // added here), and a per-region look for the layer peel. Without them the
  // diagram draws exactly as before.
  camera?: { x: number; y: number; w: number; h: number };
  regionLook?: (id: string) => { opacity: number; dx: number; dy: number };
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  // Region coords are diagram-relative; shift them inside the outline.
  const rx = (r: PlatformRegion) => r.x + MARGIN;
  const ry = (r: PlatformRegion) => r.y + MARGIN;
  // A camera box maps to the same framing scaled down, so the whole-map box
  // reproduces the default viewBox exactly and a tween never jumps.
  const viewBox = camera
    ? `${camera.x} ${camera.y} ${camera.w + 2 * MARGIN} ${
        camera.h + (2 * MARGIN + 4) * (camera.h / anatomy.height)
      }`
    : `0 0 ${W} ${H + 4}`;

  // The break marker, derived from region kinds so the layout stays data:
  // drawn on the link between the gateway and cloud ingest while any block is
  // blocked or starved.
  const gw = anatomy.regions.find((r) => r.kind === "gateway");
  const ing = anatomy.regions.find((r) => r.kind === "ingest");
  const breakAt =
    failed && failed.size > 0 && gw && ing
      ? {
          x1: rx(gw) + gw.w,
          x2: rx(ing),
          cx: (rx(gw) + gw.w + rx(ing)) / 2,
          y: ry(gw) + gw.h / 2,
          top: Math.min(ry(gw), ry(ing)),
        }
      : null;

  return (
    <svg
      viewBox={viewBox}
      aria-label={`${anatomy.name} architecture diagram`}
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
      {anatomy.regions.map((r) => {
        const style = KIND_STYLE[r.kind];
        const isSel = r.id === selected;
        const isActive = active?.has(r.id) ?? false;
        const isFailed = failed?.has(r.id) ?? false;
        const look = regionLook?.(r.id);
        // Fit the label to the region: shrink to fit horizontally, fall back
        // to a rotated label for tall-narrow blocks, else tooltip only.
        // 0.62 ≈ glyph advance per unit font.
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.45, (r.w - 1.6) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.6) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.4 && hSize >= 1.05;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.05;
        const fontSize = hSize;
        const stroke = isFailed
          ? "var(--dell-error)"
          : isSel
          ? "var(--accent)"
          : isActive
            ? "var(--accent)"
            : style.stroke;
        return (
          <g
            key={r.id}
            className={
              "an-region" +
              (isActive ? " region-active" : "") +
              (isFailed ? " region-failed" : "")
            }
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
              fill={
                isFailed
                  ? FAILED_FILL
                  : isActive
                    ? KIND_ACTIVE_FILL[r.kind]
                    : style.fill
              }
              stroke={stroke}
              strokeWidth={isFailed ? 0.6 : isSel || isActive ? 0.5 : 0.25}
              strokeDasharray={isFailed ? "1.4 0.8" : undefined}
            />
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill={
                  isFailed
                    ? FAILED_TEXT
                    : isSel || isActive
                      ? "var(--accent)"
                      : style.text
                }
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
                fill={
                  isFailed
                    ? FAILED_TEXT
                    : isSel || isActive
                      ? "var(--accent)"
                      : style.text
                }
                fontSize={fontSize}
                letterSpacing={0.12}
              >
                {r.label}
              </text>
            )}
          </g>
        );
      })}
      {breakAt && (
        // Where the upload actually stops: the customer's own proxy, which is
        // not a block on this map. It sits on the gateway-to-cloud link, so the
        // picture does not blame the two blocks the prose clears. The cross
        // keeps the state from resting on colour alone.
        <g className="link-break" pointerEvents="none">
          <line
            x1={breakAt.x1}
            y1={breakAt.y}
            x2={breakAt.x2}
            y2={breakAt.y}
            stroke="var(--dell-error)"
            strokeWidth={0.45}
            strokeDasharray="0.8 0.6"
          />
          <path
            d={`M ${breakAt.cx - 1.1} ${breakAt.y - 1.1} l 2.2 2.2 m 0 -2.2 l -2.2 2.2`}
            stroke="var(--dell-error)"
            strokeWidth={0.55}
            fill="none"
          />
          <text
            x={breakAt.cx}
            y={breakAt.top - 1.2}
            textAnchor="middle"
            fill={FAILED_TEXT}
            fontSize={1.4}
            letterSpacing={0.1}
          >
            upload refused at the company proxy
          </text>
        </g>
      )}
      {/* Orientation: telemetry flows in from the left, insights out to the right. */}
      <text
        x={MARGIN}
        y={H + 2.6}
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        TELEMETRY IN — monitored Dell systems
      </text>
      <text
        x={W - MARGIN}
        y={H + 2.6}
        textAnchor="end"
        fill="#5a6b82"
        fontSize={1.7}
        letterSpacing={0.3}
      >
        INSIGHTS &amp; ACTIONS OUT
      </text>
    </svg>
  );
}
