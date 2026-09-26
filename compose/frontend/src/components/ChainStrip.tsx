import { hostedHref } from "@twinsim/twin-ui";
import type { ChainInfo, CoupledTrace, JoinedTick, SeamResult } from "../types";

// The chain as a row of engine cards joined by seam connectors. Each
// connector carries the identity it asserts and a live `lhs = rhs` readout at
// the playback cursor; a seam that does not hold turns red and says by how
// much. A broken seam is reported, never thrown — sometimes it is the lesson.

function fmt(v: number | null | undefined, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (a >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
  return v.toFixed(a >= 10 ? 1 : digits);
}

function Connector({
  seam,
  at,
}: {
  seam: SeamResult;
  at: JoinedTick | undefined;
}) {
  const live =
    seam.lhsKey && seam.rhsKey && at
      ? { lhs: at.values[seam.lhsKey], rhs: at.values[seam.rhsKey] }
      : null;
  return (
    <div className={`seam-connector${seam.holds ? "" : " broken"}`}>
      <div className="seam-head">
        <span className="seam-id">{seam.coupling.toUpperCase()}</span>
        <span className="seam-verdict">{seam.holds ? "holds" : "broken"}</span>
      </div>
      <div className="seam-identity">{seam.identity}</div>
      <div className="seam-readout">
        {live ? (
          <span>
            {fmt(live.lhs)} = {fmt(live.rhs)} {seam.unit} <em>at the cursor</em>
          </span>
        ) : (
          <span>
            {fmt(seam.lhs)} vs {fmt(seam.rhs)} {seam.unit} <em>over the run</em>
          </span>
        )}
        <span className="seam-error">
          worst {fmt(seam.absError, 3)} / tolerance {fmt(seam.tolerance, 3)} {seam.unit}
          {seam.worstTick !== null && <> at tick {seam.worstTick}</>}
        </span>
      </div>
      {seam.note && <div className="mini seam-note">{seam.note}</div>}
    </div>
  );
}

export function ChainStrip({
  trace,
  info,
  cursor,
}: {
  trace: CoupledTrace;
  info: ChainInfo | null;
  cursor: number;
}) {
  const at = trace.timeline[Math.min(cursor, trace.timeline.length - 1)];
  const ports = new Map(
    (info?.engines ?? []).map((e) => [e.component, { port: e.frontendPort, label: e.label }]),
  );

  return (
    <div className="an-panel chain-strip">
      <h2>{trace.title || trace.chainId}</h2>
      <div className="engine-row">
        {trace.stages.map((stage) => {
          const meta = ports.get(stage.component);
          const href = meta ? hostedHref(stage.component, meta.port, "") : null;
          return (
            <div className="engine-card" key={stage.id}>
              <div className="engine-name">{stage.component}</div>
              <div className="mini engine-label">{stage.label}</div>
              <div className="mini engine-facts">
                {stage.trace.length} ticks · {stage.timeUnit}
                {stage.injectedEvents.length > 0 && (
                  <> · {stage.injectedEvents.length} injected</>
                )}
              </div>
              {href && (
                <a
                  className="mini engine-link"
                  href={href}
                  data-twin-port={meta?.port}
                  data-twin-start={stage.component}
                >
                  open the twin
                </a>
              )}
            </div>
          );
        })}
      </div>
      <div className="seam-row">
        {trace.seams.map((seam, i) => (
          <Connector key={`${seam.coupling}-${i}`} seam={seam} at={at} />
        ))}
      </div>
      {info && <p className="chain-blurb">{info.blurb}</p>}
      {info && <p className="mini chain-watch">Watch for: {info.watch}</p>}
    </div>
  );
}
