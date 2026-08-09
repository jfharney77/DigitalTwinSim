import type { Explain, SimState, Summary } from "../types";

// The readout panel: wall power, the component split, heat vs delivery,
// and the lifetime-carbon bar. Explain mode substitutes live values into
// each equation, the R760Thermal pattern.

function Row({ label, value, unit, accent }: {
  label: string; value: string; unit: string; accent?: boolean;
}) {
  return (
    <div className="instr-row">
      <span className="instr-label">{label}</span>
      <span className={`instr-value${accent ? " instr-accent" : ""}`}>
        {value}<span className="instr-unit"> {unit}</span>
      </span>
    </div>
  );
}

export function Instruments({ state, summary, explains, explainOn }: {
  state: SimState | null;
  summary: Summary | null;
  explains: Explain[];
  explainOn: boolean;
}) {
  const c = summary?.carbon ?? null;
  return (
    <div className="an-panel">
      <h2>Instruments</h2>
      {state && (
        <>
          <Row label="Wall power" value={state.acPowerW.toFixed(1)} unit="W" accent />
          <Row label="Backlight" value={state.backlightW.toFixed(1)} unit="W" />
          <Row label="Electronics" value={state.electronicsW.toFixed(1)} unit="W" />
          <Row label="Hub → laptop" value={state.hubOutW.toFixed(0)} unit="W" />
          <Row label="Hub loss" value={state.hubLossW.toFixed(1)} unit="W" />
          <Row label="Heat into the room" value={state.heatW.toFixed(1)} unit="W" />
          <Row label="Lit fraction"
               value={(state.litFraction * 100).toFixed(0)} unit="%" />
          <Row label="This run" value={state.cumulativeWh.toFixed(2)} unit="Wh" />
          <div className="mini">
            Acoustics: 0 dBA by construction — nothing in this product
            moves. That sentence is the entire fan model.
          </div>
        </>
      )}

      {c && (
        <>
          <h2 style={{ marginTop: "1rem" }}>Lifetime carbon</h2>
          <div className="carbon-bar" title="embodied vs use-phase">
            <div className="carbon-embodied" style={{ width: `${c.embodiedPct}%` }}>
              {c.embodiedPct.toFixed(0)}%
            </div>
            <div className="carbon-use" style={{ width: `${c.usePct}%` }}>
              {c.usePct.toFixed(0)}%
            </div>
          </div>
          <div className="mini carbon-legend">
            <span><i className="swatch swatch-embodied" /> embodied {c.embodiedKg.toFixed(0)} kg</span>
            <span><i className="swatch swatch-use" /> use {c.useKg.toFixed(0)} kg</span>
            <span>lifetime {c.lifetimeKg.toFixed(0)} kgCO2e</span>
          </div>
          <Row label="Average on-power" value={c.avgOnPowerW.toFixed(1)} unit="W" />
          <Row label="Annual energy" value={c.annualKwh.toFixed(0)} unit="kWh" />
          <div className="mini">
            Embodied figures from Dell PCF datasheets (27″ and 32″ class
            proxies); use-phase computed from this scenario's duty cycle at
            the grid intensity you set — badge: intensity is an estimate.
          </div>
        </>
      )}

      {explainOn && state && (
        <div className="explain-list">
          {explains.map((e) => (
            <div key={e.id} className="explain-card">
              <strong>{e.title}</strong>
              <div className="explain-eq">{e.equation}</div>
              <div className="explain-live">
                {e.id === "backlight-power" &&
                  `= ${state.backlightW.toFixed(1)} W at ${state.brightnessPct}% brightness, lit ${(state.litFraction * 100).toFixed(0)}%`}
                {e.id === "wall-power" &&
                  `= ${state.acPowerW.toFixed(1)} W from ${state.dcPowerW.toFixed(1)} W DC`}
                {e.id === "heat" &&
                  `= ${state.dcPowerW.toFixed(1)} − ${state.hubOutW.toFixed(0)} = ${state.heatW.toFixed(1)} W`}
                {e.id === "use-carbon" && c &&
                  `= ${c.annualKwh.toFixed(0)} kWh/yr → ${c.useKg.toFixed(0)} kg over the service life`}
              </div>
              <div className="explain-chain">{e.inputs.join(" → ")}</div>
              <p className="mini">{e.explanation}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
