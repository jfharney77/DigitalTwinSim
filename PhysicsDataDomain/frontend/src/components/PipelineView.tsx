import type { PipelineMap, SimState } from "../types";

// The dedupe data path, drawn from backend region data and painted by the
// engine's regionLoad (0..1). Left → right is the direction of data; the
// arrows between stages thicken with today's novelty — on a quiet estate
// almost nothing flows past DD Boost, which is the product's whole pitch.

function loadColor(load: number): string {
  // 0 = dark idle panel, 1 = hot amber.
  if (load <= 0) return "#141c2a";
  const stops: [number, string][] = [
    [0.15, "#1a2c44"],
    [0.35, "#1f4d6e"],
    [0.6, "#2596be"],
    [0.85, "#c98f2c"],
    [1.01, "#c8501e"],
  ];
  for (const [max, c] of stops) if (load <= max) return c;
  return "#c8501e";
}

export function PipelineView({
  anatomy,
  state,
  selected,
  onSelect,
}: {
  anatomy: PipelineMap;
  state: SimState | null;
  selected: string | null;
  onSelect: (id: string | null) => void;
}) {
  const W = anatomy.width;
  const H = anatomy.height;
  const load = (id: string) => state?.regionLoad[id] ?? 0;
  const novelty = state ? load("boost") : 0;

  const byId = new Map(anatomy.regions.map((r) => [r.id, r]));
  const chain = ["streams", "boost", "chunker"];
  const arrows: { x1: number; y1: number; x2: number; y2: number; w: number }[] = [];
  for (let i = 0; i < chain.length - 1; i++) {
    const a = byId.get(chain[i])!;
    const b = byId.get(chain[i + 1])!;
    arrows.push({
      x1: a.x + a.w, y1: a.y + a.h / 2,
      x2: b.x, y2: b.y + b.h / 2,
      w: 0.6 + 2.4 * (state ? 1 : 0),
    });
  }
  const chunker = byId.get("chunker")!;
  const index = byId.get("index")!;
  const store = byId.get("store")!;
  const cleaner = byId.get("cleaner")!;

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="pipeline-svg"
      style={{ width: "100%", background: "#0b1119", borderRadius: 6 }}
      onClick={() => onSelect(null)}
    >
      <defs>
        <marker id="arr" viewBox="0 0 6 6" refX={5} refY={3} markerWidth={5}
          markerHeight={5} orient="auto">
          <path d="M0,0 L6,3 L0,6 z" fill="#3c4b5d" />
        </marker>
      </defs>

      {/* Direction labels, CloudIQ style. */}
      <text x={1} y={H - 1.2} fontSize={2.2} fill="#5b6c80"
        fontFamily="ui-monospace, monospace">
        STREAMS IN
      </text>
      <text x={W - 1} y={H - 1.2} fontSize={2.2} fill="#5b6c80" textAnchor="end"
        fontFamily="ui-monospace, monospace">
        CONTAINERS &amp; CLEANING
      </text>

      {/* Stage-to-stage arrows. */}
      {arrows.map((a, i) => (
        <line key={i} x1={a.x1} y1={a.y1} x2={a.x2} y2={a.y2}
          stroke="#3c4b5d" strokeWidth={0.5} markerEnd="url(#arr)" />
      ))}
      {/* Chunker fans out to index (lookup) and store (novel bytes). */}
      <line x1={chunker.x + chunker.w} y1={chunker.y + chunker.h / 2}
        x2={index.x} y2={index.y + index.h / 2}
        stroke="#3c4b5d" strokeWidth={0.5} strokeDasharray="1.2 0.8"
        markerEnd="url(#arr)" />
      <line x1={chunker.x + chunker.w} y1={chunker.y + chunker.h / 2}
        x2={store.x} y2={store.y + store.h / 2}
        stroke="#c98f2c" strokeOpacity={0.25 + 0.75 * novelty}
        strokeWidth={0.4 + 2.2 * novelty} markerEnd="url(#arr)" />
      <line x1={store.x + store.w} y1={store.y + store.h / 2}
        x2={cleaner.x} y2={cleaner.y + cleaner.h / 2}
        stroke="#3c4b5d" strokeWidth={0.5} markerEnd="url(#arr)" />

      {anatomy.regions.map((r) => {
        const l = load(r.id);
        const isSel = selected === r.id;
        return (
          <g key={r.id}
            onClick={(e) => {
              e.stopPropagation();
              onSelect(isSel ? null : r.id);
            }}
            style={{ cursor: "pointer" }}>
            <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={0.8}
              fill={loadColor(l)}
              stroke={isSel ? "#e8ecf1" : "#31405269"}
              strokeWidth={isSel ? 0.5 : 0.3}
              className="an-region" />
            <text x={r.x + r.w / 2} y={r.y + 3.2} fontSize={2.1}
              textAnchor="middle" fill="#dce4ee"
              fontFamily="ui-monospace, monospace">
              {r.label}
            </text>
            <text x={r.x + r.w / 2} y={r.y + r.h - 1.6} fontSize={1.9}
              textAnchor="middle" fill="#8fa1b6"
              fontFamily="ui-monospace, monospace">
              {Math.round(l * 100)}%
            </text>
          </g>
        );
      })}
    </svg>
  );
}
