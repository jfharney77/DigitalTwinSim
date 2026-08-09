import type { Explain, SimState } from "../types";

// The instruments column: live readouts with the capacity bar, rebuild
// progress, and the risk gauge, plus explain-mode cards that show the
// governing equation with live values substituted.

function fmtK(k: number): string {
  return k >= 100 ? k.toFixed(0) : k >= 10 ? k.toFixed(1) : k.toFixed(2);
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "write-penalty":
      return `${fmtK(s.backendDiskKiops)}k disk = ${fmtK(s.servedReadKiops)}k × ${s.readCost} + ${fmtK(s.servedWriteKiops)}k × ${s.writePenalty}`;
    case "usable-capacity":
      return `${s.rawTb} TB raw = ${s.usableTb} usable + ${s.overheadTb} protection + ${s.spareTb} spare`;
    case "rebuild-time":
      return s.rebuilding
        ? `${s.rebuildHoursRemaining.toFixed(1)} h remaining at ${s.rebuildPct.toFixed(1)}% done`
        : "no rebuild running";
    case "latency-knee":
      return `${s.latencyMs.toFixed(2)} ms at ${s.diskUtilPct.toFixed(0)}% busy`;
    default:
      return "";
  }
}

function Bar({
  segments,
  total,
}: {
  segments: { label: string; tb: number; color: string }[];
  total: number;
}) {
  return (
    <div>
      <div className="margin-bar" style={{ height: 12 }}>
        {segments.map((seg) => (
          <div
            key={seg.label}
            className="margin-fill"
            style={{
              display: "inline-block",
              width: `${(seg.tb / total) * 100}%`,
              height: "100%",
              background: seg.color,
            }}
            title={`${seg.label}: ${seg.tb} TB`}
          />
        ))}
      </div>
      <div className="mini">
        {segments.map((seg) => (
          <span key={seg.label} style={{ marginRight: 8 }}>
            <span style={{ color: seg.color }}>■</span> {seg.label} {seg.tb} TB
          </span>
        ))}
      </div>
    </div>
  );
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

  const risk = s?.riskIndex ?? 0;

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s && !s.online && (
        <div className="mini rule-error">■ ARRAY OFFLINE — see the event log</div>
      )}
      {s?.degraded && s.online && (
        <div className="mini rule-warning">
          △ DEGRADED — {s.drivesFailed} member(s) out
          {s.rebuilding ? `, rebuild ${s.rebuildPct.toFixed(1)}%` : ", no rebuild running"}
        </div>
      )}
      <div className="stat">
        <span>served IOPS</span>
        <span>{s ? `${fmtK(s.servedKiops)}k (${fmtK(s.offeredKiops)}k asked)` : "—"}</span>
      </div>
      <div className="stat">
        <span>read / write</span>
        <span>{s ? `${fmtK(s.servedReadKiops)}k / ${fmtK(s.servedWriteKiops)}k` : "—"}</span>
      </div>
      <div className="stat">
        <span>backend disk I/O</span>
        <span>{s ? `${fmtK(s.backendDiskKiops)}k (write ×${s.writePenalty})` : "—"}</span>
      </div>
      <Info id="write-penalty" />
      <div className="stat">
        <span>latency</span>
        <span>{s ? `${s.latencyMs.toFixed(2)} ms${s.saturated ? " · saturated" : ""}` : "—"}</span>
      </div>
      <Info id="latency-knee" />
      <div className="stat"><span>throughput</span><span>{s ? `${s.throughputMbps.toFixed(0)} MB/s` : "—"}</span></div>
      <div className="stat"><span>disk busy</span><span>{s ? `${s.diskUtilPct.toFixed(0)}%` : "—"}</span></div>
      <div className="stat">
        <span>controllers · drives · spares</span>
        <span>{s ? `${s.controllersAlive} · ${s.drivesServing} · ${s.sparesLeft}` : "—"}</span>
      </div>
      {s && (
        <>
          <div className="stat"><span>capacity</span><span>{s.usableTb} TB usable</span></div>
          <Bar
            total={s.rawTb}
            segments={[
              { label: "usable", tb: s.usableTb, color: "#2596be" },
              { label: "protection", tb: s.overheadTb, color: "#e8c33d" },
              { label: "spare", tb: s.spareTb, color: "#3a4a5e" },
            ]}
          />
          <Info id="usable-capacity" />
        </>
      )}
      {s?.rebuilding && (
        <div className="stat">
          <span>rebuild</span>
          <span>
            {s.rebuildPct.toFixed(1)}% · {s.rebuildHoursRemaining.toFixed(1)} h left
          </span>
        </div>
      )}
      <Info id="rebuild-time" />
      <div className="stat">
        <span>second-failure risk</span>
        <span style={{ color: risk > 60 ? "#c8281e" : risk > 20 ? "#e8c33d" : undefined }}>
          {s ? `${risk.toFixed(0)} / 100` : "—"}
        </span>
      </div>
      <div className="margin-bar" title="second-failure exposure (illustrative)">
        <div
          className="margin-fill"
          style={{
            width: `${risk}%`,
            background: risk > 60 ? "#c8281e" : risk > 20 ? "#e8c33d" : "#2596be",
          }}
        />
      </div>
      <div className="mini" style={{ marginTop: 6 }}>
        Values wear the ~ of a simplified model: drive constants are
        estimates (see the footnote), and the point is the relationships —
        watch one host write become {s?.writePenalty ?? "N"} disk writes.
      </div>
    </div>
  );
}
