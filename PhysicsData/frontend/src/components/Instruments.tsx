import { Gauge } from "./Gauge";
import type { Explain, SimState } from "../types";

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "min-stages":
      return `${s.throughputTbh.toFixed(1)} TB/h — constraint: ${s.bottleneck}`;
    case "littles-law":
      return `lag = backlog ÷ ${s.throughputTbh.toFixed(1)} = ${s.freshnessLagH.toFixed(0)} h`;
    case "kv-sessions":
      return `${s.sessionsActive}/${s.sessionsCapacity} sessions · +${s.tokenLatencyTaxPct.toFixed(0)}%/token`;
    case "scored-detection":
      return `P ${s.precisionPct.toFixed(0)}% · R ${s.recallPct.toFixed(0)}% · MTTD ${s.mttdH.toFixed(0)} h`;
    case "forecast-lag":
      return `${s.daysToFullForecast.toFixed(1)} days to full (± ${s.forecastErrorDays.toFixed(1)}d wrong)`;
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
      {s && product === "aidataplatform" && (
        <div className="gauge-row">
          <Gauge label="GPU idle (data)" unit="%" value={s.gpuIdleDueToDataPct} min={0} max={100}
            bands={[{ to: 2, color: "#7fbf5a" }, { to: 10, color: "#e8c33d" }, { to: 100, color: "#c8281e" }]}
            ticks={[5]} format={(v) => `${v.toFixed(1)}%`} />
          <Gauge label="freshness lag" unit="h" value={s.freshnessLagH} min={0} max={72}
            bands={[{ to: 6, color: "#7fbf5a" }, { to: 24, color: "#e8c33d" }, { to: 72, color: "#c8281e" }]}
            ticks={[24]} format={(v) => `${v.toFixed(0)}h`} />
        </div>
      )}
      {s && product === "cloudiq" && (
        <div className="gauge-row">
          <Gauge label="precision" unit="%" value={s.precisionPct} min={0} max={100}
            bands={[{ to: 50, color: "#c8281e" }, { to: 80, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}%`} />
          <Gauge label="recall" unit="%" value={s.recallPct} min={0} max={100}
            bands={[{ to: 50, color: "#c8281e" }, { to: 80, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}%`} />
        </div>
      )}
      {product === "aidataplatform" ? (
        <>
          <div className="stat"><span>throughput</span><span>{s ? `${s.throughputTbh.toFixed(1)} TB/h` : "—"}</span></div>
          <div className="stat">
            <span>bottleneck</span>
            <span className="fan-overhead">{s ? s.bottleneck : "—"}</span>
          </div>
          <Info id="min-stages" />
          <div className="stat">
            <span>freshness lag</span>
            <span className={s && s.freshnessLagH > 24 ? "fan-overhead" : undefined}>
              {s ? `${s.freshnessLagH.toFixed(0)} h` : "—"}
            </span>
          </div>
          <Info id="littles-law" />
          <div className="stat">
            <span>GPU idle due to data</span>
            <span className={s && s.gpuIdleDueToDataPct > 5 ? "fan-overhead" : undefined}>
              {s ? `${s.gpuIdleDueToDataPct.toFixed(1)}%` : "—"}
            </span>
          </div>
          <div className="stat"><span>sessions (long-context)</span><span>{s ? `${s.sessionsActive} / ${s.sessionsCapacity}` : "—"}</span></div>
          <div className="stat"><span>token latency tax</span><span>{s ? `+${s.tokenLatencyTaxPct.toFixed(0)}%` : "—"}</span></div>
          <Info id="kv-sessions" />
          <div className="stat"><span>analytics scan</span><span>{s ? `${s.analyticsScanRateTbh.toFixed(1)} TB/h` : "—"}</span></div>
        </>
      ) : (
        <>
          {s && (
            <div className={`mini ${s.deviceStatusAllGreen ? "rule-ok" : "rule-error"}`}>
              {s.deviceStatusAllGreen ? "● DEVICE STATUS: ALL GREEN" : "■ DEVICE FAULT"}
              {s.issuesActive > s.issuesDetected && (
                <span> — with {s.issuesActive - s.issuesDetected} planted issue(s) unfound…</span>
              )}
            </div>
          )}
          <div className="stat"><span>health (worst · mean)</span><span>{s ? `${s.healthScoreWorst.toFixed(0)} · ${s.healthScoreMean.toFixed(0)}` : "—"}</span></div>
          <div className="stat"><span>issues found / planted</span><span>{s ? `${s.issuesDetected} / ${s.issuesActive}` : "—"}</span></div>
          <div className="stat"><span>precision · recall</span><span>{s ? `${s.precisionPct.toFixed(0)}% · ${s.recallPct.toFixed(0)}%` : "—"}</span></div>
          <div className="stat"><span>MTTD</span><span>{s ? `${s.mttdH.toFixed(0)} h` : "—"}</span></div>
          <Info id="scored-detection" />
          <div className="stat"><span>false positives</span><span>{s ? s.falsePositivesCum : "—"}</span></div>
          <div className="stat">
            <span>array fill</span>
            <span className={s && s.arrayFillPct > 80 ? "fan-overhead" : undefined}>
              {s ? `${s.arrayFillPct.toFixed(1)}%` : "—"}
            </span>
          </div>
          <div className="stat"><span>days to full (forecast)</span><span>{s ? s.daysToFullForecast.toFixed(1) : "—"}</span></div>
          <div className="stat"><span>forecast error</span><span>{s ? `${s.forecastErrorDays.toFixed(1)} d` : "—"}</span></div>
          <Info id="forecast-lag" />
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        Rates and speedup claims are labeled estimates; the shapes — the
        moving constraint, the graded knob, the lagging fit — are the
        curriculum.
      </div>
    </div>
  );
}
