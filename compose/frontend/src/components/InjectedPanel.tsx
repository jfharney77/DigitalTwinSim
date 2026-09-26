import { useState } from "react";
import type { CoupledTrace, Stage } from "../types";

// What the adapter wrote into the target's scenario, the target's own
// validation rules (they still run), and the notes the chain carries about
// what the seam could not express.

const SHOWN = 6;

function eventLine(ev: Record<string, unknown>): string {
  const at =
    ev.atS !== undefined ? `t+${ev.atS}s`
    : ev.atH !== undefined ? `h ${ev.atH}`
    : ev.atD !== undefined ? `day ${ev.atD}`
    : "";
  const value = ev.value !== undefined && ev.value !== null ? ` ${ev.value}` : "";
  const index = ev.index !== undefined && ev.index !== null ? ` #${ev.index}` : "";
  return `${at}  ${String(ev.action ?? "")}${index}${value}`.trim();
}

function StageBlock({ stage }: { stage: Stage }) {
  const [all, setAll] = useState(false);
  const events = all ? stage.injectedEvents : stage.injectedEvents.slice(0, SHOWN);
  const config = Object.entries(stage.injectedConfig);
  if (events.length === 0 && config.length === 0 && stage.validations.length === 0) return null;
  return (
    <div className="injected-stage">
      <div className="mini injected-head">{stage.id}</div>
      {config.length > 0 && (
        <ul className="mini injected-list">
          {config.map(([k, v]) => (
            <li key={k}>
              <span className="injected-kind">config</span> {k} = {JSON.stringify(v)}
            </li>
          ))}
        </ul>
      )}
      {events.length > 0 && (
        <ul className="mini injected-list">
          {events.map((ev, i) => (
            <li key={i}>
              <span className="injected-kind">event</span> {eventLine(ev)}
            </li>
          ))}
        </ul>
      )}
      {stage.injectedEvents.length > SHOWN && (
        <button className="mini" onClick={() => setAll((v) => !v)}>
          {all ? "show fewer" : `show all ${stage.injectedEvents.length}`}
        </button>
      )}
      {stage.validations.map((v, i) => (
        <div key={i} className={`mini validation ${v.level ?? ""}`}>
          {(v.level ?? "note").toUpperCase()}: {v.message ?? v.rule}
        </div>
      ))}
    </div>
  );
}

export function InjectedPanel({ trace }: { trace: CoupledTrace }) {
  return (
    <div className="controls injected-panel">
      <h2>What the adapter injected</h2>
      {trace.stages.every(
        (s) =>
          s.injectedEvents.length === 0 &&
          Object.keys(s.injectedConfig).length === 0 &&
          s.validations.length === 0,
      ) && <p className="mini">Nothing: this chain carries its numbers as configuration only.</p>}
      {trace.stages.map((s) => (
        <StageBlock key={s.id} stage={s} />
      ))}
      {trace.divergences.length > 0 && (
        <>
          <h2>Where the two modes disagree</h2>
          {trace.divergences.map((d) => (
            <div key={d.instrument} className="mini divergence">
              <b>{d.instrument}</b>: {d.aggregate.toFixed(2)} aggregate vs {d.fed.toFixed(2)} fed
              {d.cause ? ` — ${d.cause}` : " — unexplained"}
              {d.explanation && <div className="divergence-why">{d.explanation}</div>}
            </div>
          ))}
        </>
      )}
      {trace.notes.length > 0 && (
        <>
          <h2>What the seam could not carry</h2>
          {trace.notes.map((n, i) => (
            <p key={i} className="mini">
              {n}
            </p>
          ))}
        </>
      )}
      <h2>Honesty</h2>
      <p className="mini">
        Coupling two illustrative engines gives an illustrative result. These constants are
        estimates and the chain says so: {trace.estimatedConstants.join(", ") || "none"}.
      </p>
    </div>
  );
}
