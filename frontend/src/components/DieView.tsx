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

const CORE_FILL: Record<CoreState, string> = {
  idle: "var(--core-off)",
  loading: "var(--sm-edge)",
  computing: "var(--core-on)",
  wrote: "var(--core-hot)",
};

export function DieView({
  profile,
  state,
}: {
  profile: GpuProfile;
  state: SimState | null;
}) {
  const { sm, coresPerSM } = profile;
  const coresPerSMCount = coresPerSM.rows * coresPerSM.cols;

  const smW = SM_PAD_X * 2 + coresPerSM.cols * CS + (coresPerSM.cols - 1) * CGAP;
  const smH =
    SM_HEAD + coresPerSM.rows * CS + (coresPerSM.rows - 1) * CGAP + SM_PAD_BOTTOM;
  const gridW = sm.cols * smW + (sm.cols - 1) * SM_GAP;
  const gridH = sm.rows * smH + (sm.rows - 1) * SM_GAP;

  const gx = MARGIN + MEM_W + MEM_GAP;
  const gy = TOP;
  const W = gx + gridW + MEM_GAP + MEM_W + MARGIN;
  const H = gy + gridH + FOOTER;

  const memActive = state?.memActive ?? false;
  const memFill = memActive ? "var(--mem-active)" : "var(--mem)";

  const fillFor = (flatIndex: number): string => {
    const cs = state?.coreState[flatIndex] ?? "idle";
    return CORE_FILL[cs];
  };

  const sms = [];
  let smIndex = 0;
  for (let r = 0; r < sm.rows; r++) {
    for (let c = 0; c < sm.cols; c++) {
      const x = gx + c * (smW + SM_GAP);
      const y = gy + r * (smH + SM_GAP);
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
          {coreRects}
        </g>,
      );
      smIndex++;
    }
  }

  // HBM stacks on left + right edges.
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

  const totalCores =
    sm.rows * sm.cols * coresPerSM.rows * coresPerSM.cols;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} aria-label="GPU die schematic">
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
        DIE
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
      <text x={gx} y={H - 12} fill="#3a4a60" fontSize={10}>
        {sm.rows * sm.cols} SM · {coresPerSMCount} cores each = {totalCores} lanes
      </text>
    </svg>
  );
}
