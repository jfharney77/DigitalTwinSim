import { Gauge } from "./Gauge";
import type { Explain, SimState } from "../types";

function substituted(id: string, s: SimState): string {
  switch (id) {
    case "matrix":
      return `${s.integrationHoursCum.toFixed(0)} h · ${s.mismatchEventsCum} mismatches`;
    case "five-nines":
      return `${s.availabilityPct.toFixed(3)}% · coverage ${s.coveragePct.toFixed(0)}%`;
    case "carbon-ledger":
      return `${s.totalCarbonKg.toFixed(0)} kg ÷ ${s.usefulYears.toFixed(1)} y = ${s.carbonPerUsefulYear.toFixed(0)} kg/y`;
    case "embodied-vs-use":
      return `${s.embodiedKgCum.toFixed(0)} embodied vs ${s.useKgCum.toFixed(0)} use kg`;
    default:
      return "";
  }
}

export function Instruments({
  state,
  explains,
  explainOn,
  telecom,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
  telecom: boolean;
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
      {s && telecom && (
        <div className="gauge-row">
          <Gauge label="coverage" unit="%" value={s.coveragePct} min={0} max={100}
            bands={[{ to: 90, color: "#c8281e" }, { to: 99, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}%`} />
          <Gauge label="availability" unit="%" value={s.availabilityPct} min={98} max={100}
            bands={[{ to: 99.9, color: "#c8281e" }, { to: 99.99, color: "#e8c33d" }, { to: 100, color: "#7fbf5a" }]}
            ticks={[99.999]} format={(v) => `${v.toFixed(2)}%`} />
        </div>
      )}
      {s && !telecom && (
        <div className="gauge-row">
          <Gauge label="kg CO2e / useful-year" unit="" value={s.carbonPerUsefulYear} min={0} max={200}
            bands={[{ to: 60, color: "#7fbf5a" }, { to: 100, color: "#e8c33d" }, { to: 200, color: "#c8281e" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}`} />
          <Gauge label="devices consumed" unit="" value={s.devicesConsumed} min={0} max={5}
            bands={[{ to: 1.5, color: "#7fbf5a" }, { to: 2.5, color: "#e8c33d" }, { to: 5, color: "#c8281e" }]}
            ticks={[]} format={(v) => `${v.toFixed(0)}`} />
        </div>
      )}
      {telecom ? (
        <>
          {s && s.sitesUp < s.sitesTotal && (
            <div className="mini rule-error">
              ■ {s.sitesTotal - s.sitesUp} SITES DARK
            </div>
          )}
          {s?.updating && <div className="mini rule-warning">⟳ UPDATE ROLLING</div>}
          <div className="stat"><span>sites up</span><span>{s ? `${s.sitesUp} / ${s.sitesTotal}` : "—"}</span></div>
          <div className="stat"><span>coverage</span><span>{s ? `${s.coveragePct.toFixed(1)}%` : "—"}</span></div>
          <div className="stat"><span>subscribers served</span><span>{s ? `${s.subscribersServedK.toFixed(0)}k` : "—"}</span></div>
          <div className="stat">
            <span>integration hours</span>
            <span className="fan-overhead">{s ? s.integrationHoursCum.toFixed(0) : "—"}</span>
          </div>
          <div className="stat"><span>version mismatches</span><span>{s ? s.mismatchEventsCum : "—"}</span></div>
          <Info id="matrix" />
          <div className="stat"><span>availability</span><span>{s ? `${s.availabilityPct.toFixed(3)}%` : "—"}</span></div>
          <div className="stat"><span>ambient</span><span>{s ? `${s.ambientC.toFixed(0)} °C` : "—"}</span></div>
          <Info id="five-nines" />
        </>
      ) : (
        <>
          {s && !s.deviceAlive && (
            <div className="mini rule-error">■ DEVICE RECYCLED — useful years frozen</div>
          )}
          {s?.onSecondLife && (
            <div className="mini rule-ok">↻ SECOND LIFE — carbon amortizing</div>
          )}
          <div className="stat">
            <span>carbon per useful-year</span>
            <span className="fan-overhead">{s ? `${s.carbonPerUsefulYear.toFixed(0)} kg/y` : "—"}</span>
          </div>
          <Info id="carbon-ledger" />
          <div className="stat"><span>total carbon</span><span>{s ? `${s.totalCarbonKg.toFixed(0)} kgCO2e` : "—"}</span></div>
          <div className="stat"><span>embodied · use</span><span>{s ? `${s.embodiedKgCum.toFixed(0)} · ${s.useKgCum.toFixed(0)} kg` : "—"}</span></div>
          <Info id="embodied-vs-use" />
          <div className="stat"><span>devices consumed</span><span>{s ? s.devicesConsumed : "—"}</span></div>
          <div className="stat"><span>e-waste</span><span>{s ? `${s.ewasteKg.toFixed(1)} kg` : "—"}</span></div>
          <div className="stat"><span>TCO</span><span>{s ? `$${s.tcoUsd.toFixed(0)}` : "—"}</span></div>
          <div className="stat"><span>disassembly score</span><span>{s ? `${s.disassemblyMinutes.toFixed(0)} min` : "—"}</span></div>
        </>
      )}
      <div className="mini" style={{ marginTop: 6 }}>
        {telecom
          ? "Envelope figures and hours are estimates; XR limits to verify against Dell spec sheets."
          : "All carbon figures are labeled estimates — Dell's per-product PCF reports are the real calibration source."}
      </div>
    </div>
  );
}
