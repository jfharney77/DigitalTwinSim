import type { GpuProfile, LiveState } from "../types";
import { InfoDot } from "./InfoDot";

// Shared live-view pieces (specs 10/11/12/16/17): the per-SM die, the
// counters strip, and helpers. Used by LivePage, ComparePane, and LessonTour.

export function fmt(
  v: number | null | undefined,
  unit: string,
  digits = 0,
): string {
  return v == null ? "—" : `${v.toFixed(digits)}${unit}`;
}

// Identity for a frame that survives buffer trimming (spec_11 — pinning by
// array index broke once the buffer hit its cap).
export function frameKey(s: LiveState): string {
  return `${s.tMs.toFixed(3)}|${s.kernel ?? ""}|${s.kind}`;
}

// spec_12: the die's geometry comes from the session's device when known;
// the spec_07 profile is only the default before any device_info arrives.
export function dieGrid(
  state: LiveState | null,
  profile: GpuProfile,
): { rows: number; cols: number; count: number; label: string } {
  const count = state?.device?.smCount ?? profile.sm.rows * profile.sm.cols;
  const label = state?.device?.name ?? profile.name;
  if (count === profile.sm.rows * profile.sm.cols) {
    return { rows: profile.sm.rows, cols: profile.sm.cols, count, label };
  }
  const cols = Math.ceil(Math.sqrt(count * 1.5));
  return { rows: Math.ceil(count / cols), cols, count, label };
}

export function LiveDieView({
  profile,
  state,
  compact,
}: {
  profile: GpuProfile;
  state: LiveState | null;
  compact?: boolean;
}) {
  const { rows, cols, count, label } = dieGrid(state, profile);
  const TILE_W = compact ? 88 : 116;
  const TILE_H = compact ? 50 : 62;
  const GAP = compact ? 7 : 10;
  const M = 8;
  const TOP = 46;
  const gridW = cols * TILE_W + (cols - 1) * GAP;
  const gridH = rows * TILE_H + (rows - 1) * GAP;
  const W = gridW + 2 * M + 16;
  const H = TOP + gridH + 34;

  const acts = state?.smActivity ?? [];
  const maxBlocks = Math.max(1, ...acts.map((a) => a.blocksRun));
  const timingOnly = state?.source === "cupti";

  const tiles = [];
  for (let i = 0; i < count; i++) {
    const r = Math.floor(i / cols);
    const c = i % cols;
    const a = acts[i];
    const x = M + 8 + c * (TILE_W + GAP);
    const y = TOP + r * (TILE_H + GAP);
    const heat = a ? a.blocksRun / maxBlocks : 0;
    tiles.push(
      <g key={i}>
        <rect
          x={x}
          y={y}
          width={TILE_W}
          height={TILE_H}
          rx={8}
          fill="var(--sm-idle)"
          stroke={a?.busy ? "var(--core-hot)" : "var(--sm-edge)"}
          strokeWidth={a?.busy ? 2.5 : 1.5}
        />
        {a && a.blocksRun > 0 && (
          <rect
            x={x + 3}
            y={y + 3}
            width={TILE_W - 6}
            height={TILE_H - 6}
            rx={6}
            fill="var(--core-on)"
            opacity={0.15 + 0.85 * heat}
          />
        )}
        <text
          x={x + 7}
          y={y + 15}
          fill="#8a9bb5"
          fontSize={compact ? 8 : 10}
          letterSpacing="1"
        >
          SM {i}
        </text>
        <text
          x={x + 7}
          y={y + TILE_H - 8}
          fill="#c8d6ee"
          fontSize={compact ? 10 : 12}
        >
          {a ? `${a.estimated ? "~" : ""}${a.blocksRun}` : 0} blk
        </text>
      </g>,
    );
  }

  return (
    <svg viewBox={`0 0 ${W} ${H}`} aria-label="Live GPU die activity">
      <rect
        x={M}
        y={M}
        width={W - 2 * M}
        height={H - 2 * M}
        rx={14}
        fill="#0d1420"
        stroke="#1f2935"
        strokeWidth={2}
      />
      <text
        x={M + 8}
        y={30}
        fill={state?.placement === "modeled" ? "#c77700" : "#3a4a60"}
        letterSpacing="4"
        fontSize={11}
      >
        {label.toUpperCase()} ·{" "}
        {state?.placement === "modeled"
          ? // spec_28: the honesty rule — every remapped view says so, in the
            // same load-bearing style as spec_18's provenance captions.
            `MODELED PLACEMENT (RECORDED ON ${(state.recordedOn ?? "another device").toUpperCase()})`
          : timingOnly
            ? "CUPTI CAPTURE (TIMING ONLY — NO PLACEMENT DATA)"
            : state?.running
              ? "KERNEL RUNNING — STREAMED COUNTS"
              : "REAL BLOCK PLACEMENT (%smid)"}
      </text>
      {tiles}
      <text x={M + 8} y={H - 12} fill="#3a4a60" fontSize={10}>
        {count} SM · fill = share of this kernel's blocks · ring = blocks
        resident{acts.some((a) => a.estimated) ? " · ~ = estimated from a declared sample" : ""}
      </text>
    </svg>
  );
}

export function LiveCounters({ state }: { state: LiveState | null }) {
  const occLabel =
    state?.occupancySource === "measured" ? "Occupancy (measured)" : "Occupancy";
  // spec_19 #16: low occupancy gets the page's one splash of warning color —
  // it's the number the curriculum teaches most.
  const lowOcc = state?.occupancyPct != null && state.occupancyPct < 50;
  // spec_20 #11: the one number that says how full the die is right now.
  const busy = state ? state.smActivity.filter((a) => a.busy).length : 0;
  const smTotal = state?.smActivity.length ?? 0;
  const items: [string, string, string, boolean][] = [
    [occLabel, fmt(state?.occupancyPct, "%", 1), "probe", lowOcc],
    ["SMs busy", state ? `${busy}/${smTotal}` : "—", "probe", false],
    [
      "Kernel time",
      state?.running ? "running…" : fmt(state?.elapsedMs, " ms", 2),
      "probe",
      false,
    ],
    ["GPU util", fmt(state?.utilPct, "%"), "sampler", false],
    ["VRAM", fmt(state?.vramMb, " MB"), "sampler", false],
    ["Power", fmt(state?.powerW, " W", 1), "sampler", false],
    ["Temp", fmt(state?.tempC, " °C"), "sampler", false],
  ];
  return (
    <div className="counters">
      {items.map(([label, value, source, warn]) => (
        <div className="counter" key={label} title={`source: ${source}`}>
          <div className="mini">
            {label}
            {label.startsWith("Occupancy") && (
              <InfoDot title="occupancy">
                Occupancy is the share of an SM's thread slots kept busy. Two
                budgets cap it — total resident threads (1,536 on Ada) AND
                total resident blocks (24) — and whichever runs out first
                wins. Tiny blocks hit the block ceiling with thread slots to
                spare; huge blocks can strand slots too. That's why the
                fastest block size is rarely at either extreme.
              </InfoDot>
            )}
          </div>
          <div className="value" style={warn ? { color: "#c77700" } : undefined}>
            {value}
          </div>
        </div>
      ))}
    </div>
  );
}
