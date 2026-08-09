import type { Explain, SimState, Summary } from "../types";

// The UPS panel — home of the hero instrument: predicted runtime (what
// the front panel believes) beside actual runtime (what the faded
// battery can deliver), with the gap badged whenever they disagree.

function fmtMin(m: number): string {
  if (m >= 9999) return "∞";
  return `${m.toFixed(1)} min`;
}

export function UpsPanel({
  state,
  summary,
  explains,
  explainOn,
  onUtilityFail,
  onUtilityRestore,
  onSelfTest,
}: {
  state: SimState | null;
  summary: Summary | null;
  explains: Explain[];
  explainOn: boolean;
  onUtilityFail: () => void;
  onUtilityRestore: () => void;
  onSelfTest: () => void;
}) {
  const s = state;
  const gapPct =
    s && s.predictedRuntimeMin > 0 && s.predictedRuntimeMin < 9999
      ? (1 - s.actualRuntimeMin / s.predictedRuntimeMin) * 100
      : 0;
  const ex = (id: string) => explains.find((e) => e.id === id);

  const Info = ({ id, live }: { id: string; live: string }) => {
    const e = ex(id);
    if (!explainOn || !e || !s) return null;
    return (
      <div className="mini explain-card">
        <div className="explain-eq">{e.equation}</div>
        <div className="explain-live">{live}</div>
        <div>{e.explanation}</div>
        <div className="explain-chain">{e.inputs.join(" → ")}</div>
      </div>
    );
  };

  return (
    <div className="an-panel">
      <h2>UPS &amp; battery</h2>
      {s && !s.utilityOn && (
        <div className="mini rule-error">
          ■ ON BATTERY — utility is down
        </div>
      )}
      {s && !s.rackPowered && (
        <div className="mini rule-error">■ RACK DARK — battery exhausted</div>
      )}
      <div className="stat">
        <span>charge</span>
        <span>{s ? `${s.chargePct.toFixed(0)}% · ${s.batteryWhRemaining.toFixed(0)} Wh` : "—"}</span>
      </div>
      <div className="runtime-pair">
        <div className="runtime-box">
          <div className="mini">predicted (front panel)</div>
          <div className="runtime-num">
            {s ? fmtMin(s.predictedRuntimeMin) : "—"}
          </div>
          <div className="mini">
            {s?.selfTested ? "corrected by self-test" : "from nameplate Wh"}
          </div>
        </div>
        <div className="runtime-box">
          <div className="mini">actual (faded battery)</div>
          <div className="runtime-num">
            {s ? fmtMin(s.actualRuntimeMin) : "—"}
          </div>
          <div className="mini">
            {summary
              ? `pack at ${(summary.batteryCapacityFraction * 100).toFixed(0)}% of nameplate`
              : ""}
          </div>
        </div>
      </div>
      {gapPct > 2 && (
        <div className="mini rule-warning">
          ▲ The panel overpromises by {gapPct.toFixed(0)}% — it has never
          measured this battery.
        </div>
      )}
      <Info
        id="runtime"
        live={
          s
            ? `${fmtMin(s.actualRuntimeMin)} = ${s.batteryWhRemaining.toFixed(0)} Wh × 0.93 ÷ ${s.pduInputW.toFixed(0)} W`
            : ""
        }
      />
      <Info
        id="fade"
        live={
          summary
            ? `capacity fraction = ${(summary.batteryCapacityFraction * 100).toFixed(0)}%`
            : ""
        }
      />
      <div className="stat">
        <span>wall (AC) input</span>
        <span>{s ? `${s.acInputW.toFixed(0)} W` : "—"}</span>
      </div>
      <Info
        id="wall-power"
        live={
          s && s.utilityOn
            ? `${s.acInputW.toFixed(0)} W = ${s.pduInputW.toFixed(0)} ÷ 0.98 + ${s.chargeDrawW.toFixed(0)} W charger`
            : s
              ? `battery ${s.batteryOutputW.toFixed(0)} W × 0.93 = ${s.pduInputW.toFixed(0)} W load`
              : ""
        }
      />
      <div className="stat">
        <span>battery output</span>
        <span>{s ? `${s.batteryOutputW.toFixed(0)} W` : "—"}</span>
      </div>
      <div className="stat">
        <span>inverter loss</span>
        <span>{s ? `${s.inverterLossW.toFixed(0)} W` : "—"}</span>
      </div>
      <div className="btnrow">
        <button onClick={onUtilityFail}>Utility fails now</button>
        <button onClick={onUtilityRestore}>Restore utility</button>
        <button onClick={onSelfTest}>Self-test now</button>
      </div>
    </div>
  );
}
