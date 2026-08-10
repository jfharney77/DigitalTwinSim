// V8 (physics_specs/VISUAL_IMPROVEMENTS.md): two runs, one screen.
// The headline series of the current build (solid) and its foil
// (dashed purple) share one chart, and the delta ribbon states the
// gaps that the apps' own tests assert.

export interface DeltaRow {
  label: string;
  a: number;
  b: number;
  unit: string;
}

function path(points: number[], all: number[], w: number, h: number): string {
  if (points.length < 2) return "";
  const min = Math.min(...all);
  const max = Math.max(...all, min + 1e-9);
  const n = points.length - 1;
  return points
    .map((y, i) => {
      const px = (i / n) * w;
      const py = h - ((y - min) / (max - min)) * (h - 4) - 2;
      return `${i === 0 ? "M" : "L"}${px.toFixed(1)},${py.toFixed(1)}`;
    })
    .join(" ");
}

function fmt(v: number): string {
  if (Math.abs(v) >= 1000) return v.toFixed(0);
  if (Math.abs(v) >= 10) return v.toFixed(1);
  return v.toFixed(2);
}

export function ComparePanel({
  aName,
  bName,
  headline,
  unit,
  a,
  b,
  deltas,
}: {
  aName: string;
  bName: string;
  headline: string;
  unit: string;
  a: number[];
  b: number[];
  deltas: DeltaRow[];
}) {
  const W = 260;
  const H = 60;
  const all = [...a, ...b];

  return (
    <div className="an-panel compare-panel">
      <h2>A/B — {headline}{unit ? ` (${unit})` : ""}</h2>
      <div className="mini strip-title">
        <span style={{ color: "#0672cb" }}>— {aName}</span>
        <span style={{ color: "#8b6cc9" }}>┅ {bName}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none"
        style={{ width: "100%", height: 60, display: "block" }}>
        <rect x={0} y={0} width={W} height={H} fill="#0d1420" stroke="#1f2935" strokeWidth={0.5} />
        <path d={path(b, all, W, H)} fill="none" stroke="#8b6cc9"
          strokeWidth={1.3} strokeDasharray="4 3" />
        <path d={path(a, all, W, H)} fill="none" stroke="#0672cb" strokeWidth={1.4} />
      </svg>
      <div className="compare-deltas">
        {deltas.map((d) => {
          const diff = d.a - d.b;
          const rel = d.b !== 0 ? (100 * diff) / Math.abs(d.b) : 0;
          return (
            <div key={d.label} className="stat">
              <span>{d.label}</span>
              <span>
                {fmt(d.a)} vs {fmt(d.b)} {d.unit}
                {Math.abs(rel) >= 1 && (
                  <em className="compare-rel">
                    {" "}({rel > 0 ? "+" : ""}{rel.toFixed(0)}%)
                  </em>
                )}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
