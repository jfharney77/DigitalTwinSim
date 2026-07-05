import type { MlpInfo } from "../types";

// The training-step op strip (spec_06 §3): one tile per op of the current
// step, title only — active gets the blue border, finished ops get a check
// glyph and the tint fill. No ordinals; position is the order.
export function OpPipeline({
  mlp,
  currentOp,
  done,
}: {
  mlp: MlpInfo;
  currentOp: number | null;
  done: boolean;
}) {
  const per = mlp.opsPerStep;
  const stepIdx =
    currentOp !== null
      ? Math.floor(currentOp / per)
      : done
        ? Math.floor((mlp.ops.length - 1) / per)
        : 0;
  const ops = mlp.ops.slice(stepIdx * per, (stepIdx + 1) * per);

  return (
    <div className="op-strip">
      {ops.map((op, j) => {
        const g = stepIdx * per + j;
        const finished = done || (currentOp !== null && g < currentOp);
        const active = !done && currentOp === g;
        return (
          <div
            key={g}
            className={`op-tile${active ? " active" : ""}${finished ? " done" : ""}`}
          >
            {finished ? "✓ " : ""}
            {op.name}
          </div>
        );
      })}
    </div>
  );
}
