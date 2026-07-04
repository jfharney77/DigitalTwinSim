import type { SimState } from "../types";

// Renders A, B, C (spec_02) with tiling overlays (spec_03). With tiling, C fills
// in tile-by-tile, so each cell tracks its own accumulation depth: we replay the
// trace up to the cursor and record, per cell, the highest k reached so far.

function tileSpan(index: number, tileSize: number, n: number): [number, number] {
  const start = index * tileSize;
  return [start, Math.min(start + tileSize, n)];
}

// Per-cell accumulation depth (0..N) at the current cursor.
function cellDepths(
  trace: SimState[],
  cursor: number,
  n: number,
  tileSize: number,
): number[][] {
  const depth: number[][] = Array.from({ length: n }, () => Array(n).fill(0));
  for (let idx = 0; idx <= cursor && idx < trace.length; idx++) {
    const s = trace[idx];
    if (s.tileRow === null || s.tileCol === null) continue;
    const [r0, r1] = tileSpan(s.tileRow, tileSize, n);
    const [c0, c1] = tileSpan(s.tileCol, tileSize, n);
    if (s.phase === "compute") {
      for (let i = r0; i < r1; i++)
        for (let j = c0; j < c1; j++) depth[i][j] = s.k;
    } else if (s.phase === "writeback") {
      for (let i = r0; i < r1; i++)
        for (let j = c0; j < c1; j++) depth[i][j] = n;
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
    return `${done ? "" : "("}${a[i][kk]}·${b[kk][j]}${done ? "" : ")"}`;
  });
  return `C[${i}][${j}] = ${terms.join(" + ")}`;
}

function Grid({
  title,
  values,
  tileSize,
  n,
  cellClass,
  cellTitle,
}: {
  title: string;
  values: number[][];
  tileSize: number;
  n: number;
  cellClass?: (i: number, j: number) => string;
  cellTitle?: (i: number, j: number) => string;
}) {
  return (
    <div className="matrix">
      <div className="matrix-label">{title}</div>
      <div className="matrix-grid" style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}>
        {values.flatMap((row, i) =>
          row.map((v, j) => {
            const edge =
              tileSize < n
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
                {v}
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
}: {
  a: number[][];
  b: number[][];
  trace: SimState[];
  cursor: number;
  tileSize: number;
}) {
  if (!a.length || !b.length) return null;
  const n = a.length;
  const t = tileSize || n;
  const state = trace[cursor] ?? null;
  const phase = state?.phase ?? "idle";

  const depth = cellDepths(trace, cursor, n, t);

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
        title="A"
        values={a}
        tileSize={t}
        n={n}
        cellClass={(i, j) => (inActiveA(i, j) ? opClass : "")}
      />
      <span className="panels-op">×</span>
      <Grid
        title="B"
        values={b}
        tileSize={t}
        n={n}
        cellClass={(i, j) => (inActiveB(i, j) ? opClass : "")}
      />
      <span className="panels-op">=</span>
      <Grid
        title="C"
        values={a.map((_, i) => b[0].map((_, j) => cValue(i, j)))}
        tileSize={t}
        n={n}
        cellClass={(i, j) => {
          const d = depth[i][j];
          const base = d >= n ? "c-done" : d > 0 ? "c-partial" : "c-blank";
          return inActiveC(i, j) ? `${base} c-active` : base;
        }}
        cellTitle={(i, j) => formula(a, b, i, j, depth[i][j])}
      />
    </div>
  );
}
