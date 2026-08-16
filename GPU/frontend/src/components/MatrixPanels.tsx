import type { SimState } from "../types";

// Renders A (M×K), B (K×N), C (M×N) (spec_02, rectangular per spec_22) with
// tiling overlays (spec_03). With tiling, C fills in tile-by-tile, so each cell
// tracks its own accumulation depth: we replay the trace up to the cursor and
// record, per cell, the highest k reached so far — capped at K, the shared dim.

function tileSpan(index: number, tileSize: number, axis: number): [number, number] {
  const start = index * tileSize;
  return [start, Math.min(start + tileSize, axis)];
}

// Per-cell accumulation depth (0..K) at the current cursor, over the M×N output.
function cellDepths(
  trace: SimState[],
  cursor: number,
  mRows: number,
  nCols: number,
  kDepth: number,
  tileSize: number,
): number[][] {
  const depth: number[][] = Array.from({ length: mRows }, () =>
    Array(nCols).fill(0),
  );
  for (let idx = 0; idx <= cursor && idx < trace.length; idx++) {
    const s = trace[idx];
    if (s.tileRow === null || s.tileCol === null) continue;
    const [r0, r1] = tileSpan(s.tileRow, tileSize, mRows);
    const [c0, c1] = tileSpan(s.tileCol, tileSize, nCols);
    if (s.phase === "compute") {
      for (let i = r0; i < r1; i++)
        for (let j = c0; j < c1; j++) depth[i][j] = Math.min(s.k, kDepth);
    } else if (s.phase === "writeback") {
      for (let i = r0; i < r1; i++)
        for (let j = c0; j < c1; j++) depth[i][j] = kDepth;
    }
  }
  return depth;
}

function partialValue(a: number[][], b: number[][], i: number, j: number, k: number): number {
  let sum = 0;
  for (let kk = 0; kk < k; kk++) sum += a[i][kk] * b[kk][j];
  return sum;
}

function formula(a: number[][], b: number[][], i: number, j: number, k: number): string {
  const terms = a[i].map((_, kk) => {
    const done = kk < k;
    return `${done ? "" : "("}${fmt(a[i][kk])}·${fmt(b[kk][j])}${done ? "" : ")"}`;
  });
  return `[${i}][${j}] = ${terms.join(" + ")}`;
}

function fmt(v: number): string | number {
  return Number.isInteger(v) ? v : v.toFixed(2);
}

function Grid({
  title,
  values,
  tileSize,
  tiled,
  cellClass,
  cellTitle,
}: {
  title: string;
  values: number[][];
  tileSize: number;
  tiled: boolean;
  cellClass?: (i: number, j: number) => string;
  cellTitle?: (i: number, j: number) => string;
}) {
  const cols = values[0]?.length ?? 0;
  // Rectangular shapes can get wide (spec_22): shrink cells past 8 columns
  // so the three panels stay bounded side by side.
  const compact = cols > 8 || values.length > 8 ? " compact" : "";
  return (
    <div className="matrix">
      <div className="matrix-label">
        {title} · {values.length}×{cols}
      </div>
      <div
        className={`matrix-grid${compact}`}
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
      >
        {values.flatMap((row, i) =>
          row.map((v, j) => {
            const edge = tiled
              ? `${i % tileSize === 0 && i > 0 ? " tile-top" : ""}${
                  j % tileSize === 0 && j > 0 ? " tile-left" : ""
                }`
              : "";
            return (
              <div
                key={`${i}-${j}`}
                className={`cell ${cellClass?.(i, j) ?? ""}${edge}`}
                title={cellTitle?.(i, j)}
              >
                {fmt(v)}
              </div>
            );
          }),
        )}
      </div>
    </div>
  );
}

export function MatrixPanels({
  a,
  b,
  trace,
  cursor,
  tileSize,
  aLabel = "A",
  bLabel = "B",
  cLabel = "C",
}: {
  a: number[][]; // M×K
  b: number[][]; // K×N
  trace: SimState[];
  cursor: number;
  tileSize: number;
  aLabel?: string;
  bLabel?: string;
  cLabel?: string;
}) {
  if (!a.length || !b.length) return null;
  const mRows = a.length; // rows of A and C
  const kDepth = a[0]?.length ?? 0; // shared dim: cols of A, rows of B
  const nCols = b[0]?.length ?? 0; // cols of B and C
  const maxDim = Math.max(mRows, kDepth, nCols);
  const t = tileSize > 0 && tileSize < maxDim ? tileSize : maxDim;
  const tiled = t < maxDim;
  const state = trace[cursor] ?? null;
  const phase = state?.phase ?? "idle";

  const depth = cellDepths(trace, cursor, mRows, nCols, kDepth, t);

  // Active tiles from the current state: which blocks are "in shared memory".
  const inActiveC = (i: number, j: number) =>
    state?.tileRow != null &&
    state?.tileCol != null &&
    i >= state.tileRow * t &&
    i < state.tileRow * t + t &&
    j >= state.tileCol * t &&
    j < state.tileCol * t + t;
  const inActiveA = (i: number, j: number) =>
    state?.tileRow != null &&
    state?.kTile != null &&
    i >= state.tileRow * t &&
    i < state.tileRow * t + t &&
    j >= state.kTile * t &&
    j < state.kTile * t + t;
  const inActiveB = (i: number, j: number) =>
    state?.kTile != null &&
    state?.tileCol != null &&
    i >= state.kTile * t &&
    i < state.kTile * t + t &&
    j >= state.tileCol * t &&
    j < state.tileCol * t + t;

  // Loading -> streaming into fast memory (blue); computing -> resident & reused (amber).
  const opClass = phase === "load" ? "op-loading" : "op-active";

  const cValue = (i: number, j: number) => partialValue(a, b, i, j, depth[i][j]);

  return (
    <div className="panels">
      <Grid
        title={aLabel}
        values={a}
        tileSize={t}
        tiled={tiled}
        cellClass={(i, j) => (inActiveA(i, j) ? opClass : "")}
      />
      <span className="panels-op">×</span>
      <Grid
        title={bLabel}
        values={b}
        tileSize={t}
        tiled={tiled}
        cellClass={(i, j) => (inActiveB(i, j) ? opClass : "")}
      />
      <span className="panels-op">=</span>
      <Grid
        title={cLabel}
        values={a.map((_, i) => b[0].map((_, j) => cValue(i, j)))}
        tileSize={t}
        tiled={tiled}
        cellClass={(i, j) => {
          const d = depth[i][j];
          const base = d >= kDepth ? "c-done" : d > 0 ? "c-partial" : "c-blank";
          return inActiveC(i, j) ? `${base} c-active` : base;
        }}
        cellTitle={(i, j) => formula(a, b, i, j, depth[i][j])}
      />
    </div>
  );
}
