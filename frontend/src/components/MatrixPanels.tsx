import type { SimState } from "../types";

// Renders the A, B, C matrices (spec_02). C is derived client-side from the
// current accumulation step k:  Cpartial[i][j] = sum over kk in [0,k) A[i][kk]*B[kk][j].
// The backend stays the source of truth for A/B; C is just a view of the trace.

function partialC(a: number[][], b: number[][], k: number): number[][] {
  const n = a.length;
  const c: number[][] = [];
  for (let i = 0; i < n; i++) {
    const row: number[] = [];
    for (let j = 0; j < n; j++) {
      let sum = 0;
      for (let kk = 0; kk < k; kk++) sum += a[i][kk] * b[kk][j];
      row.push(sum);
    }
    c.push(row);
  }
  return c;
}

function formula(a: number[][], b: number[][], i: number, j: number, k: number): string {
  const n = a.length;
  const terms = [];
  for (let kk = 0; kk < n; kk++) {
    const done = kk < k;
    terms.push(`${done ? "" : "("}${a[i][kk]}·${b[kk][j]}${done ? "" : ")"}`);
  }
  return `C[${i}][${j}] = ${terms.join(" + ")}`;
}

function Grid({
  title,
  values,
  cellClass,
  cellTitle,
}: {
  title: string;
  values: number[][];
  cellClass?: (i: number, j: number) => string;
  cellTitle?: (i: number, j: number) => string;
}) {
  const n = values.length;
  return (
    <div className="matrix">
      <div className="matrix-label">{title}</div>
      <div
        className="matrix-grid"
        style={{ gridTemplateColumns: `repeat(${n}, 1fr)` }}
      >
        {values.flatMap((row, i) =>
          row.map((v, j) => (
            <div
              key={`${i}-${j}`}
              className={`cell ${cellClass?.(i, j) ?? ""}`}
              title={cellTitle?.(i, j)}
            >
              {v}
            </div>
          )),
        )}
      </div>
    </div>
  );
}

export function MatrixPanels({
  a,
  b,
  state,
}: {
  a: number[][];
  b: number[][];
  state: SimState | null;
}) {
  if (!a.length || !b.length) return null;

  const phase = state?.phase ?? "idle";
  const k = state?.k ?? 0;
  // Operand index consumed during compute-step k is (k-1); see engine phases.
  const activeIndex = phase === "compute" ? k - 1 : -1;
  // C cells are finalized together once all N accumulation steps are done.
  const cDone = phase === "writeback" || phase === "done";
  // Show C only once computation has begun.
  const showC = phase === "compute" || cDone;
  const c = showC ? partialC(a, b, k) : a.map((row) => row.map(() => 0));

  return (
    <div className="panels">
      <Grid
        title="A"
        values={a}
        cellClass={(_, j) => (j === activeIndex ? "op-active" : "")}
      />
      <span className="panels-op">×</span>
      <Grid
        title="B"
        values={b}
        cellClass={(i) => (i === activeIndex ? "op-active" : "")}
      />
      <span className="panels-op">=</span>
      <Grid
        title="C"
        values={c}
        cellClass={() => (cDone ? "c-done" : showC ? "c-partial" : "c-blank")}
        cellTitle={(i, j) => formula(a, b, i, j, k)}
      />
    </div>
  );
}
