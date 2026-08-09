import type { FactoryMap, FactoryRegion, SimState } from "../types";

// The factory block diagram: six coupled blocks painted by activity
// (0–100 from the engine's regionStatus), the compute block carrying a
// rack grid sized by the scenario, and connectors that show the
// couplings — compute↔fabric↔data on the work row, power/cooling feeding
// up from the facility row. The mesh is the lesson; keep it visible.

const MARGIN = 2.5;

// Activity ramp: idle slate → Dell blue → amber → red as a block runs
// hot against its own budget.
const STOPS: [number, string][] = [
  [0.0, "#233043"],
  [0.4, "#2596be"],
  [0.75, "#7fbf5a"],
  [0.9, "#e8c33d"],
  [1.0, "#c8281e"],
];

function lerpColor(a: string, b: string, f: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * f));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

function statusColor(v: number): string {
  const f = Math.max(0, Math.min(1, v / 100));
  for (let i = 1; i < STOPS.length; i++) {
    if (f <= STOPS[i][0]) {
      const [f0, c0] = STOPS[i - 1];
      const [f1, c1] = STOPS[i];
      return lerpColor(c0, c1, (f - f0) / (f1 - f0));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

function blockStat(id: string, s: SimState): string {
  switch (id) {
    case "ops":
      return s.phase;
    case "compute":
      return `${s.gpusOnline.toLocaleString()} GPUs · ${s.gpuUtilPct.toFixed(0)}%`;
    case "fabric":
      return `η ${s.fabricEffPct.toFixed(0)}%`;
    case "data":
      return `${s.storageSupplyGbps.toFixed(0)} GB/s`;
    case "power":
      return `${s.facilityMw.toFixed(2)} / ${s.mwBudget.toFixed(2)} MW`;
    case "cooling":
      return `PUE ${s.pue.toFixed(2)}`;
    case "resilience":
      return `${s.failuresCum} failures`;
    default:
      return "";
  }
}

export function FactoryView({
  anatomy,
  state,
  racks,
  selected,
  onSelect,
}: {
  anatomy: FactoryMap;
  state: SimState | null;
  racks: number;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: FactoryRegion) => r.x + MARGIN;
  const ry = (r: FactoryRegion) => r.y + MARGIN;
  const by = Object.fromEntries(anatomy.regions.map((r) => [r.id, r]));
  const compute = by["compute"];
  const fabric = by["fabric"];
  const data = by["data"];

  // Rack grid inside the compute block, sized by the scenario.
  const rackCells: { x: number; y: number }[] = [];
  if (compute) {
    const cols = Math.ceil(Math.sqrt(racks * (compute.w / compute.h)));
    const rows = Math.ceil(racks / cols);
    const cw = (compute.w - 3) / cols;
    const ch = (compute.h - 8) / rows;
    for (let i = 0; i < racks; i++) {
      rackCells.push({
        x: rx(compute) + 1.5 + (i % cols) * cw + cw * 0.1,
        y: ry(compute) + 6 + Math.floor(i / cols) * ch + ch * 0.1,
      });
    }
  }
  const rackW = compute
    ? (compute.w - 3) / Math.ceil(Math.sqrt(racks * (compute.w / compute.h)))
    : 4;
  const rackH = compute
    ? (compute.h - 8) / Math.ceil(racks / Math.ceil(Math.sqrt(racks * (compute.w / compute.h))))
    : 4;

  const installedFrac = state
    ? state.gpusInstalled / Math.max(1, racks * 72)
    : 0;

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 6}`}
      aria-label={`${anatomy.name} block diagram`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {/* Couplings: the work row passes tokens' ingredients left↔right;
          the facility row feeds budgets upward. */}
      {compute && fabric && data && (
        <g stroke="#3a4a60" strokeWidth={0.7} strokeDasharray="1.6 1.2">
          <line
            x1={rx(compute) + compute.w} y1={ry(compute) + compute.h / 2}
            x2={rx(fabric)} y2={ry(fabric) + fabric.h / 2}
          />
          <line
            x1={rx(fabric) + fabric.w} y1={ry(fabric) + fabric.h / 2}
            x2={rx(data)} y2={ry(data) + data.h / 2}
          />
        </g>
      )}
      {(["power", "cooling"] as const).map((id) => {
        const r = by[id];
        if (!r || !compute) return null;
        const x = rx(r) + r.w / 2;
        return (
          <line
            key={id}
            x1={x} y1={ry(r)} x2={x} y2={ry(compute) + compute.h}
            stroke="#3a4a60" strokeWidth={0.7} strokeDasharray="0.8 1.2"
          />
        );
      })}

      {anatomy.regions.map((r) => {
        const status = state?.regionStatus[r.id] ?? 0;
        const isSel = r.id === selected;
        const fill = statusColor(status);
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
              stroke={isSel ? "var(--accent)" : "#0d1420"}
              strokeWidth={isSel ? 0.6 : 0.3}
            />
            <text
              x={rx(r) + 1.4}
              y={ry(r) + 3.0}
              fill="#e8eef7"
              fontSize={1.9}
              fontWeight={600}
              letterSpacing={0.1}
            >
              {r.label}
            </text>
            {state && (
              <text
                x={rx(r) + r.w - 1.4}
                y={ry(r) + r.h - 1.6}
                textAnchor="end"
                fill="#dce6f2"
                fontSize={1.8}
                fontWeight={700}
              >
                {blockStat(r.id, state)}
              </text>
            )}
          </g>
        );
      })}

      {/* Rack grid inside compute: installed racks light up as the
          install phase progresses; online utilization tints them. */}
      {compute &&
        rackCells.map((c, i) => {
          const installed = i < Math.round(installedFrac * racks);
          const util = state ? state.gpuUtilPct / 100 : 0;
          return (
            <rect
              key={i}
              x={c.x} y={c.y}
              width={Math.max(rackW * 0.8, 0.8)}
              height={Math.max(rackH * 0.8, 0.8)}
              rx={0.3}
              fill={installed ? statusColor(30 + 70 * util) : "#141c2a"}
              stroke="#0d1420"
              strokeWidth={0.2}
            />
          );
        })}

      <text x={MARGIN} y={H + 4} fill="#5a6b82" fontSize={1.7}>
        blocks painted by activity · compute shows {racks} rack{racks === 1 ? "" : "s"} · click a block for its story
      </text>
    </svg>
  );
}
