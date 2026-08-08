import type { Explain, SimState } from "../types";

function fmtH(h: number): string {
  return h >= 48 ? `${(h / 24).toFixed(1)} d` : `${h.toFixed(1)} h`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "rpo":
      return `last clean point ${fmtH(s.lastCleanPointAgeH)} old`;
    case "rto":
      return `${fmtH(s.rtoHours)}${s.failedRestores ? ` after ${s.failedRestores} failed restore(s)` : ""}`;
    case "blast":
      return `${s.blastRadiusGb.toFixed(0)} GB · contain ${s.timeToContainH > 0 ? fmtH(s.timeToContainH) : "—"}`;
    case "roc":
      return `detect ${s.detected ? fmtH(s.detectionLatencyH) : "—"} · ${s.falseAlarmsCum} false alarms (${s.investigationHoursCum.toFixed(0)} h)`;
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
      {s?.incidentActive && !s.contained && (
        <div className="mini rule-error">■ CORRUPTION SPREADING — uncontained</div>
      )}
      {s?.detected && !s?.recovered && (
        <div className="mini rule-warning">◉ DETECTED — last clean point identified</div>
      )}
      {s?.recovered && (
        <div className="mini rule-ok">✓ RECOVERED</div>
      )}
      {product !== "fortzero" ? (
        <>
          <div className="stat"><span>clean · corrupted</span><span>{s ? `${s.cleanTb.toFixed(0)} · ${s.corruptedTb.toFixed(1)} TB` : "—"}</span></div>
          <div className="stat">
            <span>RPO (clean-point age)</span>
            <span className={s && s.lastCleanPointAgeH > 48 ? "fan-overhead" : undefined}>
              {s ? fmtH(s.lastCleanPointAgeH) : "—"}
            </span>
          </div>
          <Info id="rpo" />
          <div className="stat"><span>RTO (estimate/actual)</span><span>{s ? fmtH(s.rtoHours) : "—"}</span></div>
          <Info id="rto" />
          <div className="stat"><span>copies intact · repo / vault</span><span>{s ? `${s.repoCopiesIntact} / ${s.vaultCopiesIntact}` : "—"}</span></div>
          <div className="stat"><span>backup storage</span><span>{s ? `${s.backupStorageTb.toFixed(1)} TB` : "—"}</span></div>
          <div className="stat"><span>corruption score</span><span>{s ? s.corruptionScore.toFixed(0) : "—"}</span></div>
          <div className="stat"><span>blast radius</span><span>{s ? `${s.blastRadiusGb.toFixed(0)} GB` : "—"}</span></div>
          <Info id="blast" />
          <div className="stat"><span>alert backlog</span><span>{s ? s.alertsBacklog : "—"}</span></div>
          <div className="stat"><span>false alarms · hours</span><span>{s ? `${s.falseAlarmsCum} · ${s.investigationHoursCum.toFixed(0)} h` : "—"}</span></div>
          <Info id="roc" />
          {s?.restoring && (
            <div className="stat"><span>restore progress</span><span>{s.restoreProgressPct.toFixed(0)}%</span></div>
          )}
        </>
      ) : (
        <>
          <div className="stat">
            <span>reachable assets</span>
            <span className={s && s.reachableAssets > 10 ? "fan-overhead" : undefined}>
              {s ? s.reachableAssets : "—"}
            </span>
          </div>
          <div className="stat"><span>policy checks / session</span><span>{s ? s.policyChecksPerSession : "—"}</span></div>
          <div className="stat"><span>stale grants</span><span>{s ? s.staleGrants : "—"}</span></div>
          <Info id="blast" />
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        The incident is an abstract corruption rate and a timestamp —
        defensive architecture only. Constants carry sources; estimates
        say so.
      </div>
    </div>
  );
}
