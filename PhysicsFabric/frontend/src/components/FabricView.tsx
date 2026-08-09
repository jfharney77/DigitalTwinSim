import type { MapRegion, FabricMap, SimState } from "../types";

// The product architecture diagram, painted by LOAD (0–100%+) rather
// than temperature: blue idle → green working → yellow busy → red
// saturated; loads past 100% (over-demand) clip into deep red.

const MARGIN = 2.5;

const STOPS: [number, string][] = [
  [0.0, "#2c4fd8"],
  [0.35, "#2596be"],
  [0.6, "#7fbf5a"],
  [0.8, "#e8c33d"],
  [0.92, "#e07b28"],
  [1.0, "#c8281e"],
];

function lerpColor(a: string, b: string, f: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * f));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function loadColor(pct: number): string {
  const f = Math.max(0, Math.min(1, pct / 100));
  for (let i = 1; i < STOPS.length; i++) {
    if (f <= STOPS[i][0]) {
      const [f0, c0] = STOPS[i - 1];
      const [f1, c1] = STOPS[i];
      return lerpColor(c0, c1, (f - f0) / (f1 - f0));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

export function FabricView({
  anatomy,
  state,
  selected,
  onSelect,
}: {
  anatomy: FabricMap;
  state: SimState | null;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: MapRegion) => r.x + MARGIN;
  const ry = (r: MapRegion) => r.y + MARGIN;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 10}`}
      aria-label={`${anatomy.name} load map`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {state && state.deliveredGbps > 0 && (
        <line
          className="flowline"
          x1={50} y1={H - 6} x2={50} y2={5}
          stroke="#7fbf5a"
          strokeWidth={0.9}
          opacity={0.8}
          style={{ animationDuration: `${Math.max(0.4, 5 / Math.max(state.deliveredGbps / 4000, 0.4))}s` }}
        />
      )}
      {state && Object.keys(state.linkLoad).length > 0 && (() => {
        // V4: the drawn topology. Fabric keys "l{i}-s{j}" run between
        // the leaf band (top edge y=22) and the spine band (bottom edge
        // y=10); campus keys "a{i}-u{j}" run access (y=25) → distribution
        // (y=21). Colors follow the load ramp; the worst link is thick
        // and dashed white; slack (dead) links hang gray.
        const entries = Object.entries(state.linkLoad);
        const fabric = entries[0][0].startsWith("l");
        const worst = Math.max(...entries.map(([, v]) => v));
        const M = 2.5;
        if (fabric) {
          const leaves = new Set(entries.map(([k]) => k.split("-")[0])).size;
          const spines = new Set(entries.map(([k]) => k.split("-")[1])).size;
          const leafX = (i: number) => M + 8 + ((i + 0.5) * 84) / leaves;
          const spineX = (j: number) => M + 20 + ((j + 0.5) * 60) / spines;
          return (
            <g>
              {entries.map(([k, v]) => {
                const [li, sj] = k.split("-").map((t) => parseInt(t.slice(1)));
                const isWorst = v === worst && v > 0;
                const dead = v === 0;
                return (
                  <g key={k}>
                    <line
                      x1={spineX(sj)} y1={M + 10} x2={leafX(li)} y2={M + 22}
                      stroke={dead ? "#2a3a52" : loadColor(v)}
                      strokeWidth={isWorst ? 1.4 : 0.55}
                      opacity={dead ? 0.5 : 0.9}
                    >
                      <title>{`${k}: ${v.toFixed(0)}%`}</title>
                    </line>
                    {isWorst && v > 90 && (
                      <line
                        x1={spineX(sj)} y1={M + 10} x2={leafX(li)} y2={M + 22}
                        stroke="#ffffff" strokeWidth={0.4}
                        strokeDasharray="1.5 1.5"
                      />
                    )}
                  </g>
                );
              })}
            </g>
          );
        }
        const accesses = new Set(entries.map(([k]) => k.split("-")[0])).size;
        const accX = (i: number) => M + 8 + ((i + 0.5) * 84) / accesses;
        return (
          <g>
            {entries.map(([k, v]) => {
              const [ai, uj] = k.split("-").map((t) => parseInt(t.slice(1)));
              const dead = v === 0;
              return (
                <line
                  key={k}
                  x1={accX(ai) + (uj === 0 ? -1.5 : 1.5)} y1={M + 25}
                  x2={M + 20 + 30 + (accX(ai) - M - 50) * 0.5} y2={M + 21}
                  stroke={dead ? "#2a3a52" : loadColor(v)}
                  strokeWidth={v === worst && v > 0 ? 1.2 : 0.55}
                  opacity={dead ? 0.5 : 0.9}
                >
                  <title>{`${k}: ${v.toFixed(0)}%`}</title>
                </line>
              );
            })}
          </g>
        );
      })()}
      {anatomy.regions.map((r) => {
        const load = state?.regionLoad[r.id] ?? 0;
        const isSel = r.id === selected;
        const over = load > 100;
        const fill = loadColor(load);
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.42, (r.w - 1.4) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.0 && hSize >= 0.95;
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(isSel ? null : r.id);
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              stroke={isSel ? "var(--accent)" : over ? "#ffffff" : "#0d1420"}
              strokeWidth={isSel ? 0.6 : over ? 0.5 : 0.3}
              strokeDasharray={over ? "1.2 0.8" : undefined}
            />
            {showLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.4)}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={Math.max(hSize, 0.95)}
                fontWeight={600}
                letterSpacing={0.1}
              >
                {over ? `${r.label} — SATURATED` : r.label}
              </text>
            )}
            {r.w >= 20 && r.h >= 7 && state && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.6}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={1.7}
                fontWeight={700}
              >
                {load.toFixed(0)}%
              </text>
            )}
          </g>
        );
      })}
      <g>
        {Array.from({ length: 30 }, (_, i) => (
          <rect
            key={i}
            x={MARGIN + i * 2}
            y={H + 1.2}
            width={2}
            height={2.2}
            fill={loadColor(((i + 0.5) / 30) * 100)}
          />
        ))}
        <text x={MARGIN} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          idle
        </text>
        <text x={MARGIN + 62} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          saturated
        </text>
        <text x={W - MARGIN} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          colored by load / fill · click a block
        </text>
      </g>
    </svg>
  );
}
