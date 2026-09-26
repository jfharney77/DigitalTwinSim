import { Gauge } from "./Gauge";
import type { Explain, SimState } from "../types";

function fmtH(h: number): string {
  return h >= 48 ? `${(h / 24).toFixed(1)} d` : `${h.toFixed(1)} h`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "rpo":
      return `newest clean copy ${fmtH(s.lastCleanPointAgeH)} old now${s.rpoRealisedH >= 0 ? ` · ${fmtH(s.rpoRealisedH)} old when the restore was ordered` : ""}`;
    case "rto":
      if (s.restoreFailed) return "no intact copy — nothing to restore";
      return s.recovered || s.failedRestores
        ? `${fmtH(s.rtoHours)} actual${s.failedRestores ? ` after ${s.failedRestores} failed restore(s)` : ""}`
        : `${s.decisionHours.toFixed(0)} h deciding + ${s.transferHours.toFixed(1)} h moving data = ${fmtH(s.decisionHours + s.transferHours)}`;
    case "blast":
      return `${(s.peakBlastGb / 1000).toFixed(1)} TB at peak · contain ${s.timeToContainH > 0 ? fmtH(s.timeToContainH) : "—"}`;
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
      {s && product !== "fortzero" && (
        <div className="gauge-row">
          <Gauge label="newest clean copy age" unit="h" value={s.lastCleanPointAgeH} min={0} max={336}
            bands={[{ to: 24, color: "#7fbf5a" }, { to: 72, color: "#e8c33d" }, { to: 336, color: "#c8281e" }]}
            ticks={[24]} format={(v) => (v >= 48 ? `${(v / 24).toFixed(1)}d` : `${v.toFixed(0)}h`)} />
          <Gauge label={s.restoreFailed ? "RTO · no intact copy" : "RTO"} unit="h"
            value={s.restoreFailed ? 0 : s.rtoHours} min={0} max={150}
            bands={[{ to: 24, color: "#7fbf5a" }, { to: 72, color: "#e8c33d" }, { to: 150, color: "#c8281e" }]}
            ticks={[]} format={(v) => (s.restoreFailed ? "—" : v >= 48 ? `${(v / 24).toFixed(1)}d` : `${v.toFixed(0)}h`)} />
        </div>
      )}
      {s && product === "fortzero" && (
        <div className="gauge-row">
          <Gauge label="reachable assets" unit="" value={s.reachableAssets} min={0} max={100}
            bands={[{ to: 10, color: "#7fbf5a" }, { to: 30, color: "#e8c33d" }, { to: 100, color: "#c8281e" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}`} />
          <Gauge label="stale grants" unit="" value={s.staleGrants} min={0} max={200}
            bands={[{ to: 30, color: "#7fbf5a" }, { to: 80, color: "#e8c33d" }, { to: 200, color: "#c8281e" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}`} />
        </div>
      )}
      {s?.incidentActive && !s.contained && (
        <div className="mini rule-error">■ CORRUPTION SPREADING — uncontained</div>
      )}
      {s?.detected && !s?.recovered && (
        <div className="mini rule-warning">◉ DETECTED — last clean point identified</div>
      )}
      {s?.recovered && (
        <div className="mini rule-ok">✓ RECOVERED</div>
      )}
      {s?.restoreFailed && (
        <div className="mini rule-error">■ RESTORE FAILED — no intact copy exists</div>
      )}
      {product !== "fortzero" ? (
        <>
          <div className="stat"><span>clean · corrupted</span><span>{s ? `${s.cleanTb.toFixed(0)} · ${s.corruptedTb.toFixed(1)} TB` : "—"}</span></div>
          <div className="stat">
            <span>newest clean copy age (live)</span>
            <span className={s && s.lastCleanPointAgeH > 48 ? "fan-overhead" : undefined}>
              {s ? fmtH(s.lastCleanPointAgeH) : "—"}
            </span>
          </div>
          <div className="stat">
            <span>RPO realised (copy age at restore order)</span>
            <span>{s && s.rpoRealisedH >= 0 ? fmtH(s.rpoRealisedH) : "—"}</span>
          </div>
          <Info id="rpo" />
          <div className="stat">
            <span>RTO ({s?.recovered ? "actual" : "estimate"}, from the restore order)</span>
            <span className={s?.restoreFailed ? "fan-overhead" : undefined}>
              {s ? (s.restoreFailed ? "no intact copy" : fmtH(s.rtoHours)) : "—"}
            </span>
          </div>
          <div className="stat"><span>RTO · deciding</span><span>{s ? `${s.decisionHours.toFixed(0)} h` : "—"}</span></div>
          <div className="stat"><span>RTO · moving data</span><span>{s ? `${s.transferHours.toFixed(1)} h` : "—"}</span></div>
          {s?.restoring && (
            <div className="stat">
              <span>restore progress</span>
              <span>
                {s.restoreStage === "deciding"
                  ? "deciding which copy · 0% moved"
                  : `moving data · ${s.restoreProgressPct.toFixed(0)}%`}
              </span>
            </div>
          )}
          <div className="stat"><span>down since onset</span><span>{s && s.outageHours > 0 ? fmtH(s.outageHours) : "—"}</span></div>
          <Info id="rto" />
          <div className="stat"><span>copies intact · repo / vault</span><span>{s ? `${s.repoCopiesIntact} / ${s.vaultCopiesIntact}` : "—"}</span></div>
          <div className="stat"><span>backup storage</span><span>{s ? `${s.backupStorageTb.toFixed(1)} TB` : "—"}</span></div>
          <div className="stat"><span>corruption score</span><span>{s ? s.corruptionScore.toFixed(0) : "—"}</span></div>
          <div className="stat"><span>blast radius (most data corrupt at once)</span><span>{s ? `${(s.peakBlastGb / 1000).toFixed(1)} TB` : "—"}</span></div>
          <Info id="blast" />
          <div className="stat"><span>alert backlog</span><span>{s ? s.alertsBacklog : "—"}</span></div>
          <div className="stat"><span>false alarms · hours</span><span>{s ? `${s.falseAlarmsCum} · ${s.investigationHoursCum.toFixed(0)} h` : "—"}</span></div>
          <Info id="roc" />
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
        say so. Not modelled: restoring only the damaged volumes (every
        restore here moves the whole estate, the slowest case), and the
        cost of rehydrating deduplicated backups (the pipe runs at its
        full rate).
      </div>
    </div>
  );
}
