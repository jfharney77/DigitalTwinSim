import type { Explain, SimState } from "../types";

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "admin-hours":
      return `${s.adminHoursPerMonth.toFixed(0)} h/month · ${s.adminHoursCum.toFixed(0)} h total`;
    case "n-plus-one":
      return `${s.nodesHealthy}/${s.nodesTotal} healthy · headroom ${s.headroomPct.toFixed(0)}%`;
    case "availability":
      return `${s.availabilityPct.toFixed(3)}% (${s.outageMinutesCum.toFixed(0)} outage-min)`;
    case "apex-econ":
      return `$${s.costPerVmHourAsvc.toFixed(3)} asvc vs $${s.costPerVmHourCapex.toFixed(3)} owned /VM-h`;
    default:
      return "";
  }
}

export function Instruments({
  state,
  explains,
  explainOn,
  product,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
  product: string;
}) {
  const s = state;
  const ex = (id: string) => explains.find((e) => e.id === id);

  const Info = ({ id }: { id: string }) => {
    const e = ex(id);
    if (!explainOn || !e || !s) return null;
    return (
      <div className="mini explain-card">
        <div className="explain-eq">{e.equation}</div>
        <div className="explain-live">{substituted(id, s)}</div>
        <div>{e.explanation}</div>
        <div className="explain-chain">{e.inputs.join(" → ")}</div>
      </div>
    );
  };

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s?.exposure && (
        <div className="mini rule-error">
          ⚠ EXPOSURE — served but unprotected; a second failure loses data
        </div>
      )}
      {s?.updating && (
        <div className="mini rule-warning">⟳ UPDATE ROLLING</div>
      )}
      <div className="stat">
        <span>admin-hours / month</span>
        <span className="fan-overhead">{s ? s.adminHoursPerMonth.toFixed(0) : "—"}</span>
      </div>
      <div className="stat"><span>admin-hours total</span><span>{s ? s.adminHoursCum.toFixed(0) : "—"}</span></div>
      <Info id="admin-hours" />
      <div className="stat"><span>sites · nodes</span><span>{s ? `${s.sitesDeployed} · ${s.nodesHealthy}/${s.nodesTotal}` : "—"}</span></div>
      <div className="stat"><span>VMs running / demand</span><span>{s ? `${s.vmsRunning} / ${s.vmsDemand}` : "—"}</span></div>
      <div className="stat"><span>headroom</span><span>{s ? `${s.headroomPct.toFixed(0)}%` : "—"}</span></div>
      <Info id="n-plus-one" />
      <div className="stat"><span>version currency</span><span>{s ? `${s.versionCurrentPct.toFixed(0)}%` : "—"}</span></div>
      <div className="stat"><span>drift</span><span>{s ? s.driftCount : "—"}</span></div>
      <div className="stat"><span>availability</span><span>{s ? `${s.availabilityPct.toFixed(3)}%` : "—"}</span></div>
      <div className="stat"><span>faults · trucks</span><span>{s ? `${s.faultsCum} · ${s.truckRolls}` : "—"}</span></div>
      <Info id="availability" />
      {product === "apex" && (
        <>
          <div className="stat"><span>monthly bill</span><span>{s ? `$${s.monthlyBill.toFixed(0)}` : "—"}</span></div>
          <div className="stat"><span>commitment used</span><span>{s ? `${s.commitmentUtilizationPct.toFixed(0)}%` : "—"}</span></div>
          <div className="stat">
            <span>$/VM-h · asvc vs owned</span>
            <span>{s ? `${s.costPerVmHourAsvc.toFixed(3)} vs ${s.costPerVmHourCapex.toFixed(3)}` : "—"}</span>
          </div>
          <Info id="apex-econ" />
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        Admin-hour figures are estimates; the order-of-magnitude gap
        between manual and automated is the claim, not the decimals.
      </div>
    </div>
  );
}
