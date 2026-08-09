import { Gauge } from "./Gauge";
import type { Explain, SimState } from "../types";

function fmtG(g: number): string {
  return g >= 1000 ? `${(g / 1000).toFixed(1)} Tb/s` : `${g.toFixed(0)} Gb/s`;
}

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "oversub":
      return `${s.oversubRatio.toFixed(2)} : 1`;
    case "queue-delay":
      return `${s.latencyUs.toFixed(1)} µs at worst link ${s.worstLinkPct.toFixed(0)}%`;
    case "ecmp":
      return `worst ${s.worstLinkPct.toFixed(0)}% vs mean ${s.meanLinkPct.toFixed(0)}%`;
    case "lossless":
      return `drops ${s.droppedPps.toFixed(0)} pps · pauses ${s.pauseEventsS.toFixed(0)}/s · stalls ${s.stallUsPerS.toFixed(0)} µs/s`;
    case "optics-power":
      return `${s.opticsPowerW.toFixed(0)} W optics vs ${s.asicPowerW.toFixed(0)} W ASIC`;
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
      {s && (
        <div className="gauge-row">
          <Gauge label="worst link" unit="%" value={s.worstLinkPct} min={0} max={150}
            bands={[{ to: 70, color: "#7fbf5a" }, { to: 90, color: "#e8c33d" }, { to: 150, color: "#c8281e" }]}
            ticks={[90, 100]} format={(v) => `${v.toFixed(0)}%`} />
          <Gauge label="delivered" unit="%" min={0} max={100}
            value={s.demandedGbps > 0 ? (100 * s.deliveredGbps) / s.demandedGbps : 100}
            bands={[{ to: 90, color: "#c8281e" }, { to: 99, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}%`} />
        </div>
      )}
      {s && (
        <div className={`mini ${s.statusAllGreen ? "rule-ok" : "rule-error"}`}>
          {s.statusAllGreen ? "● ALL GREEN (says the fabric)" : "■ FAULT VISIBLE"}
          {s.goodputPenaltyPct > 0 && s.statusAllGreen && (
            <span> — and yet goodput is down {s.goodputPenaltyPct.toFixed(0)}%…</span>
          )}
        </div>
      )}
      <div className="stat"><span>delivered / demand</span><span>{s ? `${fmtG(s.deliveredGbps)} / ${fmtG(s.demandedGbps)}` : "—"}</span></div>
      <div className="stat">
        <span>worst link</span>
        <span className={s && s.worstLinkPct > 90 ? "fan-overhead" : undefined}>
          {s ? `${s.worstLinkPct.toFixed(0)}%` : "—"}
        </span>
      </div>
      <div className="stat"><span>mean link</span><span>{s ? `${s.meanLinkPct.toFixed(0)}%` : "—"}</span></div>
      <Info id="ecmp" />
      <div className="stat"><span>oversubscription</span><span>{s ? `${s.oversubRatio.toFixed(2)}:1` : "—"}</span></div>
      <Info id="oversub" />
      <div className="stat"><span>latency</span><span>{s ? `${s.latencyUs.toFixed(1)} µs` : "—"}</span></div>
      <div className="stat"><span>FCT (64 MB)</span><span>{s ? `${s.fctMs.toFixed(1)} ms` : "—"}</span></div>
      <Info id="queue-delay" />
      <div className="stat"><span>drops</span><span>{s ? `${s.droppedPps.toFixed(0)} pps` : "—"}</span></div>
      <div className="stat"><span>pauses · stalls</span><span>{s ? `${s.pauseEventsS.toFixed(0)}/s · ${s.stallUsPerS.toFixed(0)} µs/s` : "—"}</span></div>
      <Info id="lossless" />
      {product === "x800" && (
        <div className="stat"><span>all-reduce rate</span><span>{s ? fmtG(s.allreduceGbps) : "—"}</span></div>
      )}
      {product !== "e3200" && (
        <>
          <div className="stat"><span>fabric power</span><span>{s ? `${(s.fabricPowerW / 1000).toFixed(1)} kW` : "—"}</span></div>
          <div className="stat"><span>optics share</span><span>{s ? `${s.opticsPowerW.toFixed(0)} W` : "—"}</span></div>
          <Info id="optics-power" />
        </>
      )}
      {product === "e3200" && (
        <>
          <div className="stat">
            <span>PoE demand / budget</span>
            <span className={s && s.poeDemandW > s.poeBudgetW ? "fan-overhead" : undefined}>
              {s ? `${s.poeDemandW.toFixed(0)} / ${s.poeBudgetW.toFixed(0)} W` : "—"}
            </span>
          </div>
          <div className="stat"><span>devices powered</span><span>{s ? `${s.devicesPowered} / ${s.devicesTotal}` : "—"}</span></div>
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        Flow-level fluid model — no packets, deliberately. Constants carry
        sources; estimates say so.
      </div>
    </div>
  );
}
