import type { Explain, Phase, SimState } from "../types";
import { PHASE_COLOR } from "./RackView";

// The three phase-balance bar meters with the 80% continuous-load line
// drawn — the panel an electrician would check before adding one more
// server to the convenient outlet.

function Meter({
  phase,
  watts,
  amps,
  pct,
  tripped,
}: {
  phase: Phase;
  watts: number;
  amps: number;
  pct: number;
  tripped: boolean;
}) {
  const fillPct = Math.min(100, pct);
  const color = tripped
    ? "#c8281e"
    : pct > 100
      ? "#c8281e"
      : pct > 80
        ? "#e8c33d"
        : PHASE_COLOR[phase];
  return (
    <div className="phase-meter">
      <div className="mini strip-title">
        <span style={{ color: PHASE_COLOR[phase] }}>Phase {phase}</span>
        <span>
          {tripped
            ? "TRIPPED"
            : `${watts.toFixed(0)} W · ${amps.toFixed(1)} A · ${pct.toFixed(0)}%`}
        </span>
      </div>
      <div className="phase-bar">
        <div
          className="phase-fill"
          style={{ width: `${fillPct}%`, background: color }}
        />
        <div className="phase-80-line" title="80% continuous-load rule" />
      </div>
    </div>
  );
}

export function PhaseMeters({
  state,
  explains,
  explainOn,
}: {
  state: SimState | null;
  explains: Explain[];
  explainOn: boolean;
}) {
  const s = state;
  const tripped = new Set(s?.trippedPhases ?? []);
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
      <h2>Phase balance</h2>
      <Meter
        phase="A" watts={s?.phaseAW ?? 0} amps={s?.phaseAAmps ?? 0}
        pct={s?.phaseAPct ?? 0} tripped={tripped.has("A")}
      />
      <Meter
        phase="B" watts={s?.phaseBW ?? 0} amps={s?.phaseBAmps ?? 0}
        pct={s?.phaseBPct ?? 0} tripped={tripped.has("B")}
      />
      <Meter
        phase="C" watts={s?.phaseCW ?? 0} amps={s?.phaseCAmps ?? 0}
        pct={s?.phaseCPct ?? 0} tripped={tripped.has("C")}
      />
      <div className="stat">
        <span>imbalance</span>
        <span>{s ? `${s.imbalancePct.toFixed(0)}%` : "—"}</span>
      </div>
      <Info
        id="imbalance"
        live={
          s
            ? `max dev of ${[s.phaseAW, s.phaseBW, s.phaseCW]
                .map((w) => w.toFixed(0))
                .join(" / ")} W from avg → ${s.imbalancePct.toFixed(0)}%`
            : ""
        }
      />
      <Info
        id="phase-current"
        live={
          s
            ? `${s.phaseAAmps.toFixed(1)} A = ${s.phaseAW.toFixed(0)} W ÷ (230 V × 0.98)`
            : ""
        }
      />
      <Info
        id="breaker-trip"
        live={
          s
            ? `worst phase at ${Math.max(s.phaseAPct, s.phaseBPct, s.phaseCPct).toFixed(0)}% of rating`
            : ""
        }
      />
      <div className="mini">
        The notch on every bar is the 80% continuous-load line. Yellow past
        the notch, red past the rating — and past the rating the breaker's
        thermal curve is already counting.
      </div>
    </div>
  );
}
