import type { Constant, CouplingInfo } from "../types";

// The eight seams as data: what is read, what it becomes, the identity that
// is asserted across the gap, and the pytest that asserts it. A coupling
// without an identity would be a prose cross-reference with extra steps.

export function CouplingList({
  couplings,
  constants,
}: {
  couplings: CouplingInfo[];
  constants: Record<string, Constant>;
}) {
  return (
    <div className="couplings-page">
      <div className="an-panel">
        <h2>The seams</h2>
        <p className="mini">
          The twins already cross-reference each other in prose. Each row below is one of
          those references turned into code with a test on it: one engine's trace becomes
          another engine's scenario, and a quantity is asserted to survive the crossing.
        </p>
        <div className="coupling-grid">
          {couplings.map((c) => (
            <div className="coupling-card" key={c.id}>
              <div className="coupling-head">
                <span className="seam-id">{c.id.toUpperCase()}</span>
                <span>{c.title}</span>
              </div>
              <div className="mini coupling-route">
                {c.source} → {c.target}
                {c.closedWith && <> · closed with {c.closedWith.toUpperCase()}</>}
              </div>
              <p className="coupling-blurb">{c.blurb}</p>
              <dl className="mini coupling-facts">
                <dt>reads</dt>
                <dd>{c.sourceFields.join(", ")}</dd>
                <dt>writes</dt>
                <dd>{c.targetInputs.join(", ")}</dd>
                <dt>units</dt>
                <dd>{c.units}</dd>
                <dt>time base</dt>
                <dd>{c.timeBase}</dd>
                <dt>identity</dt>
                <dd>{c.identity}</dd>
                <dt>tolerance</dt>
                <dd>{c.tolerance}</dd>
                <dt>test</dt>
                <dd>{c.test}</dd>
              </dl>
            </div>
          ))}
        </div>
      </div>
      <div className="an-panel">
        <h2>Constants the seams own</h2>
        <p className="mini">
          The numbers neither engine on either side owns. Same discipline as every engine's
          constants table: a value, a unit, a source, and whether it is an estimate.
        </p>
        <table className="constants-table">
          <tbody>
            {Object.entries(constants).map(([name, k]) => (
              <tr key={name}>
                <th>{name}</th>
                <td>
                  {k.value} {k.unit}
                  {k.estimated && <span className="estimate-tag">estimate</span>}
                  <div className="mini">{k.blurb}</div>
                  <div className="mini constant-source">{k.source}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
