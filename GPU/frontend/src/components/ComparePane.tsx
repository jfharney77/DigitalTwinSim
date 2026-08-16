import type { GpuProfile, LiveState } from "../types";
import { GanttStrip } from "./GanttStrip";
import { dieGrid, fmt, LiveDieView } from "./LiveViz";

// spec_11: two pinned kernel runs side by side. Deltas stay neutral —
// faster/slower in ms and %, never "better/worse": occupancy up is not
// always speed up, which is the block-size lesson's entire point.

function spread(s: LiveState): number {
  const counts = s.smActivity.map((a) => a.blocksRun);
  return Math.max(...counts) - Math.min(...counts);
}

export function ComparePane({
  a,
  b,
  profile,
  onClose,
  onSwap,
}: {
  a: LiveState;
  b: LiveState;
  profile: GpuProfile;
  onClose: () => void;
  onSwap: () => void;
}) {
  const rows: [string, string, string, string][] = [];
  const push = (
    label: string,
    va: number | null,
    vb: number | null,
    unit: string,
    digits = 2,
  ) => {
    let delta = "—";
    if (va != null && vb != null && va > 0) {
      const pct = ((vb - va) / va) * 100;
      delta = `${vb - va >= 0 ? "+" : ""}${(vb - va).toFixed(digits)}${unit} (${pct >= 0 ? "+" : ""}${pct.toFixed(0)}%)`;
    }
    rows.push([label, fmt(va, unit, digits), fmt(vb, unit, digits), delta]);
  };
  push("elapsed", a.elapsedMs, b.elapsedMs, " ms");
  push("occupancy", a.occupancyPct, b.occupancyPct, "%", 1);
  push("blocks/SM spread", spread(a), spread(b), "", 0);

  // spec_28: recorded-vs-remapped puts two different dies side by side, so
  // each pane's Gantt sizes to its own device.
  const smCountA = dieGrid(a, profile).count;
  const smCountB = dieGrid(b, profile).count;
  const paneLabel = (s: LiveState) =>
    s.placement === "modeled"
      ? ` · modeled placement (recorded on ${s.recordedOn ?? "another device"})`
      : "";

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <h3 style={{ margin: 0 }}>
          Compare: {a.kernel} vs {b.kernel}
        </h3>
        <button onClick={onSwap} title="swap A and B">
          A ↔ B
        </button>
        <button onClick={onClose}>Close compare</button>
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
        <div style={{ flex: 1 }}>
          <div className="mini">
            A · {a.kernel} · grid {a.grid?.join("×")} · block{" "}
            {a.block?.join("×")}
            {paneLabel(a)}
          </div>
          <LiveDieView profile={profile} state={a} compact />
        </div>
        <div style={{ flex: 1 }}>
          <div className="mini">
            B · {b.kernel} · grid {b.grid?.join("×")} · block{" "}
            {b.block?.join("×")}
            {paneLabel(b)}
          </div>
          <LiveDieView profile={profile} state={b} compact />
        </div>
      </div>
      <table className="mini" style={{ marginTop: 10, borderSpacing: "12px 2px" }}>
        <thead>
          <tr>
            <th></th>
            <th>A</th>
            <th>B</th>
            <th>B − A</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, va, vb, d]) => (
            <tr key={label}>
              <td>{label}</td>
              <td>{va}</td>
              <td>{vb}</td>
              <td>{d}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <GanttStrip state={a} smCount={smCountA} />
      <GanttStrip state={b} smCount={smCountB} />
    </div>
  );
}
