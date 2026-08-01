import { useState } from "react";
import type { LiveState } from "../types";

// spec_10: per-SM block-residency Gantt for one kernel frame. One lane per
// SM, one bar per recorded block, x normalized to the kernel's own span.
// The straggler (latest-finishing block) gets a marker — the tail is the
// lesson the heat tiles can't teach.

export function GanttStrip({
  state,
  smCount,
}: {
  state: LiveState | null;
  smCount: number;
}) {
  // spec_20 #15: a 1-block kernel shouldn't render 23 empty lanes.
  const [hideIdle, setHideIdle] = useState(true);
  const spans = state?.blockSpans;
  if (!state || !spans || spans.length === 0) return null;

  const activeSmIds = Array.from(new Set(spans.map((s) => s.smId))).sort(
    (a, b) => a - b,
  );
  const laneIds = hideIdle
    ? activeSmIds
    : Array.from({ length: smCount }, (_, i) => i);
  const laneOf = new Map(laneIds.map((id, i) => [id, i]));

  const LANE_H = 12;
  const LABEL_W = 44;
  const M = 8;
  const W = 720;
  const plotW = W - LABEL_W - 2 * M;
  const H = M * 2 + 18 + laneIds.length * LANE_H + 16;

  let straggler = spans[0];
  for (const s of spans) if (s.endNorm > straggler.endNorm) straggler = s;

  return (
    <div style={{ marginTop: 12 }}>
      <div className="mini">
        Block residency — {state.kernel}
        {state.spansSampled ? " (spans sampled — first 2,048 records)" : ""}
        {activeSmIds.length < smCount && (
          <label style={{ marginLeft: 10 }}>
            <input
              type="checkbox"
              checked={hideIdle}
              onChange={(e) => setHideIdle(e.target.checked)}
            />{" "}
            hide idle SMs ({smCount - activeSmIds.length})
          </label>
        )}
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        aria-label="Per-SM block residency timeline"
        style={{ width: "100%", marginTop: 4 }}
      >
        <rect
          x={0}
          y={0}
          width={W}
          height={H}
          rx={10}
          fill="#0d1420"
          stroke="#1f2935"
        />
        {laneIds.map((smId, i) => (
          <g key={smId}>
            <text
              x={M}
              y={M + 14 + i * LANE_H + 9}
              fill="#46566e"
              fontSize={8}
            >
              SM {smId}
            </text>
            <line
              x1={M + LABEL_W}
              x2={W - M}
              y1={M + 14 + i * LANE_H + LANE_H / 2}
              y2={M + 14 + i * LANE_H + LANE_H / 2}
              stroke="#141d2c"
            />
          </g>
        ))}
        {spans.map((s, i) => {
          const isStraggler = s === straggler;
          const lane = laneOf.get(s.smId) ?? 0;
          return (
            <rect
              key={i}
              x={M + LABEL_W + s.startNorm * plotW}
              y={M + 14 + lane * LANE_H + 2}
              width={Math.max(1.5, (s.endNorm - s.startNorm) * plotW)}
              height={LANE_H - 4}
              rx={2}
              fill={isStraggler ? "var(--core-hot)" : "var(--core-on)"}
              opacity={isStraggler ? 1 : 0.75}
            >
              <title>
                block on SM {s.smId} · {(s.startNorm * 100).toFixed(0)}–
                {(s.endNorm * 100).toFixed(0)}% of kernel span
                {isStraggler ? " · straggler (last to finish)" : ""}
              </title>
            </rect>
          );
        })}
        <text x={M + LABEL_W} y={H - 6} fill="#3a4a60" fontSize={9}>
          0% ── kernel span ── 100% · red bar = the straggler block that set
          the kernel's finish time
        </text>
      </svg>
    </div>
  );
}
