import type { SimState } from "../types";
import { useLevel } from "../level";

const WINDOW_D = 240;

function Path({
  points, yMin, yMax, color, w, h, dashed,
}: {
  points: [number, number][];
  yMin: number;
  yMax: number;
  color: string;
  w: number;
  h: number;
  dashed?: boolean;
}) {
  if (points.length < 2) return null;
  const x0 = points[0][0];
  const xSpan = Math.max(points[points.length - 1][0] - x0, 1);
  const d = points
    .map(([x, y], i) => {
      const px = ((x - x0) / xSpan) * w;
      // 2-unit inset so a series pinned at its min or max (version
      // currency sitting at 100%, drift at 0) stays visible, not hidden
      // under the chart edge.
      const py = h - 2 - ((y - yMin) / (yMax - yMin)) * (h - 4);
      return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${Math.max(1, Math.min(h - 1, py)).toFixed(1)}`;
    })
    .join(" ");
  return (
    <path d={d} fill="none" stroke={color} strokeWidth={1.2}
      strokeDasharray={dashed ? "4 3" : undefined} />
  );
}

function Chart({
  title, unit, series, yMin, yMax, current,
}: {
  title: string;
  unit: string;
  series: { points: [number, number][]; color: string; dashed?: boolean }[];
  yMin: number;
  yMax: number;
  current: string;
}) {
  const W = 260;
  const H = 46;
  return (
    <div className="strip-chart">
      <div className="mini strip-title">
        <span>{title}</span>
        <span style={{ color: series[0].color }}>{current} {unit}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        {series.map((sr, i) => (
          <Path key={i} points={sr.points} yMin={yMin} yMax={yMax} color={sr.color} w={W} h={H} dashed={sr.dashed} />
        ))}
      </svg>
    </div>
  );
}

// The caption reads at the level the rest of the page does. The backend's
// L(...) covers server prose; this is page chrome, so the three registers
// live here, keyed the same way (1-2 novice, 3 standard, 4-5 expert).
function caption(level: number): string {
  if (level <= 2) {
    return (
      "The green line is how up to date the servers are. It drops every " +
      "time an update is released and climbs back as the update is " +
      "installed. How fast it climbs is the difference between patching " +
      "by hand and letting the software do it — that choice is the Ops " +
      "mode control — and the hours it costs are the top chart."
    );
  }
  if (level >= 4) {
    return (
      "Version currency saws on the monthly release wave; the close rate " +
      "is the ops mode, priced in the admin-hours strip."
    );
  }
  return (
    "Version currency falls on each monthly release wave and climbs back " +
    "as patching lands. How fast a wave closes is the ops mode — " +
    "automated or manual — and the hours it costs are the admin-hours " +
    "strip at the top."
  );
}

export function StripCharts({
  trace,
  cursor,
  product,
}: {
  trace: SimState[];
  cursor: number;
  product: string;
}) {
  const level = useLevel();
  const upto = trace.slice(0, cursor + 1);
  const from = Math.max(0, upto.length - WINDOW_D);
  const win = upto.slice(from);
  const hours: [number, number][] = win.map((s) => [s.tD, s.adminHoursPerMonth]);
  const version: [number, number][] = win.map((s) => [s.tD, s.versionCurrentPct]);
  const drift: [number, number][] = win.map((s) => [s.tD, s.driftCount]);
  const running: [number, number][] = win.map((s) => [s.tD, s.vmsRunning]);
  const demand: [number, number][] = win.map((s) => [s.tD, s.vmsDemand]);
  const asvc: [number, number][] = win.map((s) => [s.tD, s.costPerVmHourAsvc]);
  const capex: [number, number][] = win.map((s) => [s.tD, s.costPerVmHourCapex]);
  const cur = win[win.length - 1];
  const hMax = Math.max(50, ...hours.map(([, y]) => y)) * 1.1;
  const dMax = Math.max(10, ...drift.map(([, y]) => y)) * 1.1;
  const vMax = Math.max(50, ...demand.map(([, y]) => y)) * 1.1;
  const cMax = Math.max(0.05, ...asvc.map(([, y]) => y), ...capex.map(([, y]) => y)) * 1.2;

  return (
    <div className="an-panel">
      <h2>Strip charts — sim-days</h2>
      <Chart
        title="admin-hours (30-day rate)" unit="h/mo"
        series={[{ points: hours, color: "#e8c33d" }]}
        yMin={0} yMax={hMax}
        current={cur ? cur.adminHoursPerMonth.toFixed(0) : "—"}
      />
      <Chart
        title="version currency" unit="%"
        series={[{ points: version, color: "#7fbf5a" }]}
        yMin={0} yMax={100}
        current={cur ? cur.versionCurrentPct.toFixed(0) : "—"}
      />
      <Chart
        title="drift" unit="pts"
        series={[{ points: drift, color: "#e07b28" }]}
        yMin={0} yMax={dMax}
        current={cur ? String(cur.driftCount) : "—"}
      />
      {product === "apex" ? (
        <Chart
          title="$/VM-h: as-a-service (solid) vs owned (dashed)" unit="$"
          series={[
            { points: asvc, color: "#2596be" },
            { points: capex, color: "#8fa3bd", dashed: true },
          ]}
          yMin={0} yMax={cMax}
          current={cur ? cur.costPerVmHourAsvc.toFixed(3) : "—"}
        />
      ) : (
        <Chart
          title="VMs: running (solid) vs demand (dashed)" unit=""
          series={[
            { points: running, color: "#2596be" },
            { points: demand, color: "#8fa3bd", dashed: true },
          ]}
          yMin={0} yMax={vMax}
          current={cur ? String(cur.vmsRunning) : "—"}
        />
      )}
      <div className="mini">{caption(level)}</div>
    </div>
  );
}
