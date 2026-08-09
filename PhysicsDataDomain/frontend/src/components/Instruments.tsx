import type { Explain, SimState } from "../types";

// The instruments column: the emergent readouts, with explain-mode
// cards showing the arithmetic with live values substituted.

function fmtTb(tb: number): string {
  return tb >= 1000 ? `${(tb / 1000).toFixed(2)} PB` : `${tb.toFixed(1)} TB`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "dedupe-ratio":
      return `${s.dedupeRatio.toFixed(1)}× = ${fmtTb(s.logicalTb)} ÷ ${fmtTb(s.physicalTb)}`;
    case "novelty":
      return `${s.todaysNovelPhysicalTb.toFixed(2)} TB novel of ${s.todaysLogicalTb.toFixed(0)} TB logical today`;
    case "compression":
      return `entropy ${s.streamEntropyPct.toFixed(0)}% on today's changes`;
    case "index-pressure":
      return `${s.ingestGbps.toFixed(1)} GB/s at index ${s.indexGb.toFixed(1)} GB (${s.indexPressurePct.toFixed(0)}% over RAM)`;
    case "backup-window":
      return `${s.backupWindowHours.toFixed(2)} h = ${s.todaysLogicalTb.toFixed(0)} TB ÷ ${s.logicalIngestGbps.toFixed(0)} GB/s effective`;
    default:
      return "";
  }
}

export function Instruments({
  state,
  explains,
  explainOn,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
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
      {s?.entropyAlarm && (
        <div className="mini rule-error">
          ■ ENTROPY ALARM — today's changed data reads{" "}
          {s.streamEntropyPct.toFixed(0)}% random
        </div>
      )}
      {s?.hostEncrypted && (
        <div className="mini rule-warning">
          △ Source is encrypting before backup — every generation is novel
        </div>
      )}
      {s && s.capacityUsedPct >= 100 && (
        <div className="mini rule-error">■ STORE FULL — backups would fail</div>
      )}
      <div className="stat">
        <span>dedupe ratio (emergent)</span>
        <span className="fan-overhead">{s ? `${s.dedupeRatio.toFixed(1)}×` : "—"}</span>
      </div>
      <Info id="dedupe-ratio" />
      <div className="stat"><span>logical protected</span><span>{s ? fmtTb(s.logicalTb) : "—"}</span></div>
      <div className="stat"><span>physical stored</span><span>{s ? fmtTb(s.physicalTb) : "—"}</span></div>
      <div className="stat">
        <span>capacity used</span>
        <span>{s ? `${s.capacityUsedPct.toFixed(1)}%` : "—"}</span>
      </div>
      <div className="stat">
        <span>generations retained</span>
        <span>{s ? s.generationsRetained : "—"}</span>
      </div>
      <div className="stat">
        <span>today: novel / logical</span>
        <span>{s ? `${s.todaysNovelPhysicalTb.toFixed(2)} / ${s.todaysLogicalTb.toFixed(0)} TB` : "—"}</span>
      </div>
      <Info id="novelty" />
      <div className="stat">
        <span>stream entropy (changes)</span>
        <span>{s ? `${s.streamEntropyPct.toFixed(0)}%` : "—"}</span>
      </div>
      <Info id="compression" />
      <div className="stat">
        <span>fingerprint index</span>
        <span>{s ? `${s.indexGb.toFixed(1)} GB · ${s.uniqueChunksM.toFixed(0)} M chunks` : "—"}</span>
      </div>
      <div className="stat">
        <span>ingest (physical path)</span>
        <span>{s ? `${s.ingestGbps.toFixed(2)} GB/s` : "—"}</span>
      </div>
      <Info id="index-pressure" />
      <div className="stat">
        <span>backup window</span>
        <span>{s ? `${s.backupWindowHours.toFixed(2)} h` : "—"}</span>
      </div>
      <Info id="backup-window" />
      <div className="stat">
        <span>cleaning reclaimed today</span>
        <span>{s ? `${s.gcReclaimedTb.toFixed(2)} TB` : "—"}</span>
      </div>
      <div className="mini" style={{ marginTop: 6 }}>
        The ratio dial has no input wired to it — it is a quotient of the
        capacity ledger, and everything that moves it moves the data first.
      </div>
    </div>
  );
}
