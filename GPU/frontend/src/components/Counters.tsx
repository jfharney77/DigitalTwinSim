import type { SimState, Summary } from "../types";

export function Counters({
  state,
  tiling,
  summary,
  losses,
}: {
  state: SimState | null;
  tiling?: { hbmLoads: number; tilesDone: number; tilesTotal: number } | null;
  summary?: Summary | null;
  // Losses computed so far (spec_06); null for plain matmul workloads.
  losses?: number[] | null;
}) {
  const macs = state?.macDone ?? 0;
  const total = state?.macTotal ?? 0;
  const active = state?.activeCores ?? 0;
  const util = state ? Math.round(state.utilization * 100) : 0;

  return (
    <div className="an-panel">
      <h2>Counters</h2>
      <div className="stat">
        <span>MACs done</span>
        <span>{macs}</span>
      </div>
      <div className="stat">
        <span>of total</span>
        <span>{total}</span>
      </div>
      <div className="stat">
        <span>active cores</span>
        <span>{active}</span>
      </div>
      <div className="stat">
        <span>utilization</span>
        <span>{util}%</span>
      </div>
      {losses != null && (
        <>
          <div className="stat">
            <span>loss</span>
            <span>{losses.length ? losses[losses.length - 1].toFixed(3) : "—"}</span>
          </div>
          {losses.length > 1 && (
            <div className="mini">
              per step: {losses.map((l) => l.toFixed(2)).join(" · ")}
            </div>
          )}
        </>
      )}
      {tiling && (
        <>
          <div className="stat">
            <span>HBM tile-loads</span>
            <span>{tiling.hbmLoads}</span>
          </div>
          <div className="stat">
            <span>tiles done</span>
            <span>
              {tiling.tilesDone} / {tiling.tilesTotal}
            </span>
          </div>
        </>
      )}

      {summary && (
        <>
          <h2 style={{ marginTop: 16 }}>Roofline (illustrative)</h2>
          <div className="stat">
            <span>regime</span>
            <span>{summary.regime === "memory" ? "memory-bound" : "compute-bound"}</span>
          </div>
          <div className="stat">
            <span>intensity (MAC/byte)</span>
            <span>{summary.arithmeticIntensity.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span>ridge point</span>
            <span>{summary.ridgePoint.toFixed(2)}</span>
          </div>
          <div className="stat">
            <span>load cycles</span>
            <span>{summary.loadCyclesTotal}</span>
          </div>
          <div className="stat">
            <span>compute cycles</span>
            <span>{summary.computeCyclesTotal}</span>
          </div>
          <div className="stat">
            <span>bytes moved</span>
            <span>{summary.bytesMoved}</span>
          </div>
          <div className="stat">
            <span>serial cycles</span>
            <span>{summary.serialCycles}</span>
          </div>
          <div className="stat">
            <span>double-buffered</span>
            <span>
              {summary.pipelinedCycles}
              {summary.pipelinedCycles < summary.serialCycles
                ? ` (${(summary.serialCycles / summary.pipelinedCycles).toFixed(2)}×)`
                : ""}
            </span>
          </div>
        </>
      )}
    </div>
  );
}
