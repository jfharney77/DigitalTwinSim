import type { SimState, Summary } from "../types";

export function Counters({
  state,
  tiling,
  summary,
}: {
  state: SimState | null;
  tiling?: { hbmLoads: number; tilesDone: number; tilesTotal: number } | null;
  summary?: Summary | null;
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
