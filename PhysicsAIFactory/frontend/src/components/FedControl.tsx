import { START_COMMAND } from "../fed";
import type { FedRun } from "../fed";

// Aggregate or fed: the same engine, two ways of getting its inputs. The
// control says which, and when the two disagree it names the cause rather
// than averaging the difference away.

export function FedControl({
  mode,
  fed,
  error,
  loading,
  onMode,
}: {
  mode: "aggregate" | "fed";
  fed: FedRun | null;
  error: string | null;
  loading: boolean;
  onMode: (mode: "aggregate" | "fed") => void;
}) {
  return (
    <div className="an-panel fed-panel">
      <h2>Where the numbers come from</h2>
      <div className="btnrow">
        <button
          className={mode === "aggregate" ? "active" : ""}
          onClick={() => onMode("aggregate")}
        >
          Aggregate
        </button>
        <button className={mode === "fed" ? "active" : ""} onClick={() => onMode("fed")}>
          Fed by engines
        </button>
      </div>
      <p className="mini">
        Aggregate is this app's own model: one efficiency number per block. Fed runs the
        detailed twins — storage, fabric, the rack and its cooling loop — and carries their
        outputs in across tested seams. The engine is the same in both.
      </p>
      {loading && <p className="mini">Running the other engines…</p>}
      {error && (
        <p className="mini an-error">
          The composition layer is not answering ({error}). Start it with{" "}
          <code>{START_COMMAND}</code>, then try again.
        </p>
      )}
      {mode === "fed" && fed && (
        <>
          <p className="mini">
            The instruments above read the fed run. The floorplan keeps to the aggregate one —
            the seams carry instrument values, not the map.
          </p>
          <div className="mini">
            {fed.seams.length} seam{fed.seams.length === 1 ? "" : "s"} asserted on the way here
            {fed.seams.every((s) => s.holds) ? ", all holding" : ", one broken — see the chain"}.
          </div>
          {fed.divergences.map((d) => (
            <div key={d.instrument} className="mini fed-divergence">
              <b>{d.instrument}</b>: {d.aggregate.toFixed(2)} aggregate vs {d.fed.toFixed(2)} fed —{" "}
              {d.cause ?? "unexplained"}
              {d.explanation && <div>{d.explanation}</div>}
            </div>
          ))}
          <p className="mini">
            Estimates the chain leaned on: {fed.estimatedConstants.join(", ") || "none"}.
          </p>
        </>
      )}
    </div>
  );
}
