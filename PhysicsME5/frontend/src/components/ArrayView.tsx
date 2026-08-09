import type { ArrayMap, ArrayRegion, SimState } from "../types";

// The ME5 enclosure, painted by state: 24 drive slots across the top,
// controllers / cache / PSUs along the bottom. Clicking a healthy drive
// fails it; clicking a failed one replaces it; clicking a controller
// fails or restores it. Everything else pins its detail card.

const MARGIN = 2.5;

const STATE_FILL: Record<string, string> = {
  ok: "#2596be",
  failed: "#c8281e",
  rebuilding: "#e8c33d",
  queued: "#b58a2c",
  spare: "#3a4a5e",
  empty: "#141b26",
  offline: "#20242a",
  "write-through": "#e07b28",
};

const STATE_BADGE: Record<string, string> = {
  failed: "✕",
  rebuilding: "…",
  queued: "…",
};

export function ArrayView({
  anatomy,
  state,
  selected,
  onSelect,
  onDriveClick,
  onControllerClick,
}: {
  anatomy: ArrayMap;
  state: SimState | null;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
  onDriveClick?: (index: number) => void;
  onControllerClick?: (id: string) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: ArrayRegion) => r.x + MARGIN;
  const ry = (r: ArrayRegion) => r.y + MARGIN;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 8}`}
      aria-label={`${anatomy.name} state map`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {anatomy.regions.map((r) => {
        const st = state?.regionStates[r.id] ?? "empty";
        const isSel = r.id === selected;
        const isDrive = r.kind === "drive";
        const fill = STATE_FILL[st] ?? "#2596be";
        const badge = STATE_BADGE[st];
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              if (isDrive && onDriveClick && st !== "empty") {
                onDriveClick(Number(r.id.split("-")[1]));
              } else if (r.kind === "controller" && onControllerClick) {
                onControllerClick(r.id);
              } else {
                onSelect?.(isSel ? null : r.id);
              }
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.6}
              fill={fill}
              stroke={isSel ? "var(--accent)" : st === "failed" ? "#c8281e" : "#0d1420"}
              strokeWidth={isSel ? 0.6 : 0.3}
              opacity={st === "empty" ? 0.6 : 1}
            />
            {isDrive ? (
              <>
                <text
                  x={rx(r) + r.w / 2} y={ry(r) + 3}
                  textAnchor="middle" fill="#0d1420"
                  fontSize={1.6} fontWeight={600}
                >
                  {r.label}
                </text>
                {badge && (
                  <text
                    x={rx(r) + r.w / 2} y={ry(r) + r.h / 2 + 1}
                    textAnchor="middle"
                    fill="#0d1420" fontSize={2.6} fontWeight={700}
                  >
                    {badge}
                  </text>
                )}
                {st === "rebuilding" && state && (
                  <rect
                    x={rx(r) + 0.4}
                    y={ry(r) + r.h - 2}
                    width={(r.w - 0.8) * Math.min(1, state.rebuildPct / 100)}
                    height={1.2}
                    fill="#0d1420"
                  />
                )}
              </>
            ) : (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + 0.7 : 3)}
                textAnchor="middle" fill="#0d1420"
                fontSize={Math.min(1.9, (r.w - 1) / (r.label.length * 0.62))}
                fontWeight={600}
              >
                {r.label}
              </text>
            )}
            {!isDrive && st !== "ok" && st !== "empty" && (
              <text
                x={rx(r) + r.w / 2} y={ry(r) + r.h - 2}
                textAnchor="middle" fill="#0d1420"
                fontSize={1.7} fontWeight={700}
              >
                {st === "failed" ? "✕ failed" : st}
              </text>
            )}
          </g>
        );
      })}
      {/* Legend. */}
      <g fontSize={1.7} fill="#5a6b82">
        {(
          [
            ["ok", "healthy"],
            ["spare", "hot spare"],
            ["rebuilding", "rebuilding"],
            ["failed", "failed"],
            ["write-through", "write-through"],
          ] as const
        ).map(([k, label], i) => (
          <g key={k}>
            <rect
              x={MARGIN + i * 19} y={H + 1.4} width={2.4} height={2.4}
              fill={STATE_FILL[k]}
            />
            <text x={MARGIN + i * 19 + 3.2} y={H + 3.4}>{label}</text>
          </g>
        ))}
        <text x={W - MARGIN} y={H + 3.4} textAnchor="end">
          click a drive to fail / replace it · click a controller to fail it
        </text>
      </g>
    </svg>
  );
}
