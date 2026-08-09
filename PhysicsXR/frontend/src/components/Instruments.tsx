import type { Explain, SimState } from "../types";

// The instruments column: live readouts with throttle margin bars, plus
// explain-mode affordances that show the governing equation with live
// values substituted. XR additions over the R760 set: filter fouling,
// feed voltage and input current (the brownout pair), and the vibration
// tax on storage.

function fmtW(w: number): string {
  return w >= 1000 ? `${(w / 1000).toFixed(2)} kW` : `${w.toFixed(0)} W`;
}

// Substitute live values into an equation template for explain mode.
function substituted(id: string, s: SimState): string {
  switch (id) {
    case "cpu-power":
      return `${s.cpuPowerW.toFixed(0)} W = f(util) × clamp ${(1 - s.perfLostPct / 100).toFixed(2)}`;
    case "zone-outlet":
      return `${s.exhaustC.toFixed(1)} °C = ${s.inletEffectiveC.toFixed(1)} °C + ${s.dcPowerW.toFixed(0)} W / (ṁ·cp)`;
    case "fan-power":
      return `${s.fanPowerW.toFixed(1)} W = ${s.aliveFans} × P_max × (${s.fanRpmPct.toFixed(0)}%)³ · fouling ${s.foulingPct.toFixed(0)}%`;
    case "wall-power":
      return `${fmtW(s.acPowerW)} = ${fmtW(s.dcPowerW)} / ${s.psuEfficiency.toFixed(3)}`;
    case "brownout":
      return `${s.inputCurrentA.toFixed(1)} A = ${fmtW(s.acPowerW)} / (${s.inputVPct.toFixed(0)}% of nominal)`;
    case "vibration":
      return `storage throughput lost: ${s.storagePerfLostPct.toFixed(0)}%`;
    default:
      return "";
  }
}

function MarginBar({ value, limit, label }: { value: number; limit: number; label: string }) {
  const pct = Math.max(0, Math.min(100, (value / limit) * 100));
  const hot = value > limit - 8;
  return (
    <div className="margin-bar" title={`${label}: ${value.toFixed(1)} °C of ${limit} °C`}>
      <div
        className="margin-fill"
        style={{
          width: `${pct}%`,
          background: hot ? "#c8281e" : pct > 75 ? "#e8c33d" : "#2596be",
        }}
      />
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

  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {s && !s.poweredOn && (
        <div className="mini rule-error">■ SLED OFF — see the event log</div>
      )}
      {s?.cpuThrottling && (
        <div className="mini rule-error">
          ▼ THROTTLING — {s.perfLostPct.toFixed(0)}% performance lost
        </div>
      )}
      {s && s.inputVPct < 100 && s.poweredOn && (
        <div className="mini rule-warning">
          ⚡ FEED SAGGING — {s.inputVPct.toFixed(0)}% of nominal, drawing{" "}
          {s.inputCurrentA.toFixed(1)} A
        </div>
      )}
      <div className="stat"><span>total DC power</span><span>{s ? fmtW(s.dcPowerW) : "—"}</span></div>
      <div className="stat"><span>wall (AC) power</span><span>{s ? fmtW(s.acPowerW) : "—"}</span></div>
      <Info id="wall-power" />
      <div className="stat">
        <span>feed voltage · input current</span>
        <span>{s ? `${s.inputVPct.toFixed(0)}% · ${s.inputCurrentA.toFixed(1)} A` : "—"}</span>
      </div>
      <Info id="brownout" />
      <div className="stat">
        <span>PSU efficiency · load</span>
        <span>{s ? `${(s.psuEfficiency * 100).toFixed(1)}% · ${s.psuLoadPct.toFixed(0)}%` : "—"}</span>
      </div>
      <div className="stat">
        <span>fan power (overhead)</span>
        <span className="fan-overhead">{s ? `${s.fanPowerW.toFixed(1)} W` : "—"}</span>
      </div>
      <Info id="fan-power" />
      <div className="stat">
        <span>filter fouling</span>
        <span>{s ? `${s.foulingPct.toFixed(0)}% airflow lost` : "—"}</span>
      </div>
      <div className="stat"><span>CPU power</span><span>{s ? fmtW(s.cpuPowerW) : "—"}</span></div>
      <Info id="cpu-power" />
      <div className="stat">
        <span>CPU temp</span>
        <span>{s ? `${s.cpuTempC.toFixed(1)} °C` : "—"}</span>
      </div>
      {s && <MarginBar value={s.cpuTempC} limit={98} label="throttle margin" />}
      <div className="stat">
        <span>accelerator temp</span>
        <span>{s ? `${s.accelTempC.toFixed(1)} °C` : "—"}</span>
      </div>
      {s && <MarginBar value={s.accelTempC} limit={92} label="accelerator throttle margin" />}
      <div className="stat">
        <span>storage perf lost (vibration)</span>
        <span>{s ? `${s.storagePerfLostPct.toFixed(0)}%` : "—"}</span>
      </div>
      <Info id="vibration" />
      <div className="stat"><span>airflow</span><span>{s ? `${s.airflowCfm.toFixed(0)} CFM` : "—"}</span></div>
      <div className="stat">
        <span>fans</span>
        <span>{s ? `${s.fanRpmPct.toFixed(0)}% · ${s.aliveFans}/4 alive` : "—"}</span>
      </div>
      <div className="stat">
        <span>ambient at the intake</span>
        <span>{s ? `${s.inletEffectiveC.toFixed(1)} °C` : "—"}</span>
      </div>
      <div className="stat"><span>exhaust</span><span>{s ? `${s.exhaustC.toFixed(1)} °C` : "—"}</span></div>
      <div className="stat"><span>ΔT front→back</span><span>{s ? `${s.deltaTC.toFixed(1)} °C` : "—"}</span></div>
      <Info id="zone-outlet" />
      <div className="mini" style={{ marginTop: 6 }}>
        A simplified model: the rated envelopes are Dell's documented
        numbers, the fouling and vibration rates are labeled estimates —
        the point is the relationships. Watch the filter quietly spend the
        fans' headroom months before the day it matters.
      </div>
    </div>
  );
}
