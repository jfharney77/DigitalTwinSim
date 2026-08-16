import { useState } from "react";
import type { CoreState, GpuProfile, SimState } from "../types";

// Geometry constants (px in SVG user units). The viewBox is computed from the
// profile so any die size renders; the SVG scales to its container via CSS.
const MARGIN = 8;
const MEM_W = 40;
const MEM_GAP = 16;
const TOP = 110; // top offset for the SM grid (room for DIE label + L2 bus)
const FOOTER = 30;
const SM_GAP = 10;
const SM_PAD_X = 14;
const SM_HEAD = 50; // SM header: label + shared-mem strip
const SM_PAD_BOTTOM = 14;
const CS = 30; // core square
const CGAP = 6; // gap between cores

// Density rule (spec_07): above this lane count, per-core rects are unreadable
// and heavy — render per-SM aggregate tiles instead; click a tile to inspect
// that SM's lanes per-core in a detail strip below the die.
const DENSE_LIMIT = 512;
const TILE_W = 116;
const TILE_H = 66;
const DETAIL_CS = 10; // core square in the dense-mode detail strip
const DETAIL_CGAP = 3;

const CORE_FILL: Record<CoreState, string> = {
  idle: "var(--core-off)",
  loading: "var(--sm-edge)",
  computing: "var(--core-on)",
  wrote: "var(--core-hot)",
  mma: "var(--core-mma)", // spec_23: the whole SM flashes as one MMA block
};

export function DieView({
  profile,
  state,
  label = "DIE",
  dimmed = false,
}: {
  profile: GpuProfile;
  state: SimState | null;
  // spec_27: two-die mode names each schematic ("GPU 0 · DIE") and dims the
  // die whose states are not currently playing (and both during exchange).
  label?: string;
  dimmed?: boolean;
}) {
  const { sm, coresPerSM } = profile;
  const coresPerSMCount = coresPerSM.rows * coresPerSM.cols;
  const totalCores = sm.rows * sm.cols * coresPerSMCount;
  const dense = totalCores > DENSE_LIMIT;

  // Dense mode: which SM the detail strip inspects.
  const [inspected, setInspected] = useState(0);

  const smW = dense
    ? TILE_W
    : SM_PAD_X * 2 + coresPerSM.cols * CS + (coresPerSM.cols - 1) * CGAP;
  const smH = dense
    ? TILE_H
    : SM_HEAD + coresPerSM.rows * CS + (coresPerSM.rows - 1) * CGAP + SM_PAD_BOTTOM;
  const gridW = sm.cols * smW + (sm.cols - 1) * SM_GAP;
  const gridH = sm.rows * smH + (sm.rows - 1) * SM_GAP;

  const gx = MARGIN + MEM_W + MEM_GAP;
  const gy = TOP;
  const detailH = dense
    ? 44 + coresPerSM.rows * (DETAIL_CS + DETAIL_CGAP) + 10
    : 0;
  const W = gx + gridW + MEM_GAP + MEM_W + MARGIN;
  const H = gy + gridH + detailH + FOOTER;

  const memActive = state?.memActive ?? false;
  const memFill = memActive ? "var(--mem-active)" : "var(--mem)";

  const stalled = state?.stalled ?? false;
  const fillFor = (flatIndex: number): string => {
    const cs = state?.coreState[flatIndex] ?? "idle";
    // While stalled (waiting on HBM), "loading" cores show the stall color.
    if (stalled && cs === "loading") return "var(--stall)";
    return CORE_FILL[cs];
  };

  // Dense mode: aggregate one SM's lanes into {active count, dominant state}.
  const smSummary = (smIndex: number) => {
    const base = smIndex * coresPerSMCount;
    const counts: Record<CoreState, number> = {
      idle: 0,
      loading: 0,
      computing: 0,
      wrote: 0,
      mma: 0,
    };
    for (let i = 0; i < coresPerSMCount; i++) {
      counts[state?.coreState[base + i] ?? "idle"]++;
    }
    const active = coresPerSMCount - counts.idle;
    const dominant: CoreState =
      counts.mma > 0 // spec_23: an MMA SM is all-or-nothing by construction
        ? "mma"
        : counts.wrote >= counts.computing && counts.wrote >= counts.loading && counts.wrote > 0
          ? "wrote"
          : counts.computing >= counts.loading && counts.computing > 0
            ? "computing"
            : counts.loading > 0
              ? "loading"
              : "idle";
    return { active, dominant };
  };

  // spec_23: whole-SM MMA flash — an SM is either fully "mma" or not at all,
  // so one lane's state answers for the block; the badge shows ranks/step.
  const mmaRanks = state?.ranksPerStep ?? null;
  const smHasMma = (idx: number) => {
    const base = idx * coresPerSMCount;
    for (let i = 0; i < coresPerSMCount; i++) {
      if (state?.coreState[base + i] === "mma") return true;
    }
    return false;
  };

  const sms = [];
  let smIndex = 0;
  for (let r = 0; r < sm.rows; r++) {
    for (let c = 0; c < sm.cols; c++) {
      const x = gx + c * (smW + SM_GAP);
      const y = gy + r * (smH + SM_GAP);
      if (dense) {
        const { active, dominant } = smSummary(smIndex);
        const frac = active / coresPerSMCount;
        const barW = smW - 20;
        const idx = smIndex;
        sms.push(
          <g
            key={smIndex}
            onClick={() => setInspected(idx)}
            style={{ cursor: "pointer" }}
          >
            <rect
              x={x}
              y={y}
              width={smW}
              height={smH}
              rx={8}
              fill="var(--sm-idle)"
              stroke={inspected === idx ? "var(--core-on)" : "var(--sm-edge)"}
              strokeWidth={inspected === idx ? 2.5 : 1.5}
            />
            <text x={x + 10} y={y + 18} fill="#8a9bb5" fontSize={10} letterSpacing="1">
              SM {smIndex}
            </text>
            {/* aggregate activity bar: fill fraction of lanes, dominant color */}
            <rect
              x={x + 10}
              y={y + 28}
              width={barW}
              height={14}
              rx={3}
              fill="#16203040"
              stroke="#243042"
            />
            {frac > 0 && (
              <rect
                x={x + 10}
                y={y + 28}
                width={Math.max(2, barW * frac)}
                height={14}
                rx={3}
                fill={
                  stalled && dominant === "loading"
                    ? "var(--stall)"
                    : CORE_FILL[dominant]
                }
              />
            )}
            <text x={x + 10} y={y + 56} fill="#46566e" fontSize={9}>
              {active}/{coresPerSMCount} lanes
            </text>
            {smHasMma(idx) && (
              <text
                x={x + smW - 8}
                y={y + 56}
                fill="var(--core-mma)"
                fontSize={9}
                textAnchor="end"
              >
                MMA{mmaRanks != null ? ` ×${mmaRanks}` : ""}
              </text>
            )}
          </g>,
        );
      } else {
        const baseCore = smIndex * coresPerSMCount;
        const coreRects = [];
        const cx0 = x + SM_PAD_X;
        const cy0 = y + SM_HEAD;
        for (let i = 0; i < coresPerSM.rows; i++) {
          for (let j = 0; j < coresPerSM.cols; j++) {
            const flat = baseCore + i * coresPerSM.cols + j;
            coreRects.push(
              <rect
                key={flat}
                x={cx0 + j * (CS + CGAP)}
                y={cy0 + i * (CS + CGAP)}
                width={CS}
                height={CS}
                rx={4}
                fill={fillFor(flat)}
                stroke="#11161f"
              />,
            );
          }
        }
        sms.push(
          <g key={smIndex}>
            <rect
              x={x}
              y={y}
              width={smW}
              height={smH}
              rx={8}
              fill="var(--sm-idle)"
              stroke="var(--sm-edge)"
              strokeWidth={1.5}
            />
            <text x={x + 10} y={y + 18} fill="#8a9bb5" fontSize={10} letterSpacing="1">
              SM {smIndex}
            </text>
            <rect
              x={x + 8}
              y={y + 26}
              width={smW - 16}
              height={14}
              rx={3}
              fill="#16203040"
              stroke="#243042"
            />
            <text x={x + 12} y={y + 37} fill="#46566e" fontSize={8}>
              shared mem
            </text>
            {/* warp scheduler tick */}
            <rect x={x + smW - 30} y={y + 6} width={22} height={8} rx={2} fill="#243042" />
            {smHasMma(smIndex) && (
              <text
                x={x + smW - 8}
                y={y + 22}
                fill="var(--core-mma)"
                fontSize={9}
                textAnchor="end"
              >
                MMA{mmaRanks != null ? ` ×${mmaRanks}` : ""}
              </text>
            )}
            {coreRects}
          </g>,
        );
      }
      smIndex++;
    }
  }

  // Dense mode: detail strip — the inspected SM's lanes, per-core.
  let detail = null;
  if (dense) {
    const base = inspected * coresPerSMCount;
    const dy = gy + gridH + 20;
    const detailW =
      coresPerSM.cols * (DETAIL_CS + DETAIL_CGAP) - DETAIL_CGAP;
    const cores = [];
    for (let i = 0; i < coresPerSM.rows; i++) {
      for (let j = 0; j < coresPerSM.cols; j++) {
        const flat = base + i * coresPerSM.cols + j;
        cores.push(
          <rect
            key={flat}
            x={gx + j * (DETAIL_CS + DETAIL_CGAP)}
            y={dy + 24 + i * (DETAIL_CS + DETAIL_CGAP)}
            width={DETAIL_CS}
            height={DETAIL_CS}
            rx={2}
            fill={fillFor(flat)}
            stroke="#11161f"
          />,
        );
      }
    }
    detail = (
      <g>
        <text x={gx} y={dy + 12} fill="#8a9bb5" fontSize={10} letterSpacing="1">
          SM {inspected} · {coresPerSMCount} lanes (click any SM tile to inspect)
        </text>
        <rect
          x={gx - 8}
          y={dy + 16}
          width={detailW + 16}
          height={coresPerSM.rows * (DETAIL_CS + DETAIL_CGAP) + 14}
          rx={6}
          fill="var(--sm-idle)"
          stroke="var(--sm-edge)"
        />
        {cores}
      </g>
    );
  }

  // Memory stacks/controllers on left + right edges.
  const memY = gy;
  const memH = gridH;
  const mem = [MARGIN, W - MARGIN - MEM_W].map((mx, idx) => (
    <g key={`mem-${idx}`}>
      <rect
        x={mx}
        y={memY}
        width={MEM_W}
        height={memH}
        rx={6}
        fill={memFill}
        stroke="#2b3a4f"
      />
      <text x={mx + 6} y={memY - 6} fill="#4f7cff" fontSize={11} letterSpacing="2">
        {profile.memory.label}
      </text>
    </g>
  ));

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      aria-label={`GPU die schematic${label !== "DIE" ? ` (${label})` : ""}`}
      style={dimmed ? { opacity: 0.45, transition: "opacity 0.2s" } : undefined}
    >
      <rect
        x={MARGIN}
        y={MARGIN}
        width={W - 2 * MARGIN}
        height={H - 2 * MARGIN}
        rx={14}
        fill="#0d1420"
        stroke="#1f2935"
        strokeWidth={2}
      />
      <text x={gx} y={34} fill="#3a4a60" letterSpacing="4" fontSize={11}>
        {label}
      </text>
      {profile.hasL2Bus && (
        <>
          <rect
            x={gx}
            y={64}
            width={gridW}
            height={26}
            rx={5}
            fill="#141d2c"
            stroke="#243042"
          />
          <text x={gx + 10} y={82} fill="#5a6b82" fontSize={11}>
            L2 CACHE · INTERCONNECT
          </text>
        </>
      )}
      {mem}
      {sms}
      {detail}
      <text x={gx} y={H - 12} fill="#3a4a60" fontSize={10}>
        {sm.rows * sm.cols} SM · {coresPerSMCount} cores each = {totalCores} lanes
        {dense ? " · aggregate view (per-SM tiles)" : ""}
      </text>
    </svg>
  );
}
