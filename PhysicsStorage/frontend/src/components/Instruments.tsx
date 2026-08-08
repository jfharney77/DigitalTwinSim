import type { Explain, SimState } from "../types";

function fmtTb(tb: number): string {
  return tb >= 1000 ? `${(tb / 1000).toFixed(2)} PB` : `${tb.toFixed(1)} TB`;
}

function fmtRpo(s: number): string {
  if (s < 90) return `${s.toFixed(0)} s`;
  if (s < 5400) return `${(s / 60).toFixed(1)} min`;
  return `${(s / 3600).toFixed(1)} h`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "queueing":
      return `${s.latencyMs.toFixed(2)} ms = service × 1/(1−${(s.utilizationPct / 100).toFixed(2)})`;
    case "capacity":
      return `${fmtTb(s.usableTb)} usable = ${fmtTb(s.rawTb)} × (1−ovh); ×${s.reductionRatio} → ${fmtTb(s.effectiveTb)}`;
    case "rebuild":
      return s.rebuilding
        ? `${s.rebuildPct.toFixed(0)}% rebuilt · ${s.rebuildHoursLeft.toFixed(1)} h left`
        : "no rebuild running";
    case "srdf":
      return s.rpoSeconds > 0
        ? `RPO ${fmtRpo(s.rpoSeconds)}`
        : s.srdfLatencyMs > 0
          ? `+${s.srdfLatencyMs.toFixed(2)} ms of geography per write`
          : "replication off";
    case "gpu-idle":
      return `${s.gpuIdleDueToDataPct.toFixed(1)}% of GPU time lost to data`;
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
      {s && !s.online && (
        <div className="mini rule-error">■ OFFLINE — data loss; see the log</div>
      )}
      {s?.saturated && (
        <div className="mini rule-error">▼ SATURATED — demand beyond the ceiling</div>
      )}
      {s?.exposure && (
        <div className="mini rule-error">
          ⚠ EXPOSURE WINDOW — one more failure loses data
        </div>
      )}
      <div className="stat"><span>latency (mean · p99)</span><span>{s ? `${s.latencyMs.toFixed(2)} · ${s.p99Ms.toFixed(2)} ms` : "—"}</span></div>
      <Info id="queueing" />
      <div className="stat"><span>IOPS delivered / demand</span><span>{s ? `${s.iopsDeliveredK.toFixed(0)}k / ${s.iopsDemandK.toFixed(0)}k` : "—"}</span></div>
      <div className="stat"><span>utilization ρ</span><span>{s ? `${s.utilizationPct.toFixed(0)}%` : "—"}</span></div>
      <div className="stat"><span>throughput</span><span>{s ? `${s.throughputGbs.toFixed(1)} GB/s` : "—"}</span></div>
      <div className="stat"><span>cache hit</span><span>{s ? `${s.cacheHitPct.toFixed(0)}%` : "—"}</span></div>
      <div className="stat">
        <span>capacity used</span>
        <span className={s && s.usedPct >= 80 ? "fan-overhead" : undefined}>
          {s ? `${fmtTb(s.usedTb)} · ${s.usedPct.toFixed(1)}%` : "—"}
        </span>
      </div>
      <Info id="capacity" />
      <div className="stat"><span>snapshots</span><span>{s ? fmtTb(s.snapshotTb) : "—"}</span></div>
      <div className="stat"><span>units online</span><span>{s ? s.unitsOnline : "—"}</span></div>
      <div className="stat">
        <span>rebuild</span>
        <span>{s?.rebuilding ? `${s.rebuildPct.toFixed(0)}% · ${s.rebuildHoursLeft.toFixed(1)} h left` : "—"}</span>
      </div>
      <Info id="rebuild" />
      {product === "powermax" && (
        <>
          <div className="stat"><span>SRDF write tax</span><span>{s ? `${s.srdfLatencyMs.toFixed(2)} ms` : "—"}</span></div>
          <div className="stat"><span>RPO</span><span>{s ? fmtRpo(s.rpoSeconds) : "—"}</span></div>
          <Info id="srdf" />
        </>
      )}
      {product === "exascale" && (
        <>
          <div className="stat">
            <span>GPU idle due to data</span>
            <span className={s && s.gpuIdleDueToDataPct > 2 ? "fan-overhead" : undefined}>
              {s ? `${s.gpuIdleDueToDataPct.toFixed(1)}%` : "—"}
            </span>
          </div>
          <Info id="gpu-idle" />
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        Legible, not benchmark-accurate: the knee's shape is the lesson,
        not the absolute IOPS. Constants carry sources; estimates say so.
      </div>
    </div>
  );
}
