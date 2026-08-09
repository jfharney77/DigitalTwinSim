import type { Phase, RackMap, SimState } from "../types";

// The rack elevation: load slots painted by phase assignment (click to
// cycle A → B → C), phase strips and the UPS layer painted by live
// watts. The diagram stays dark — it is the diagram.

export const PHASE_COLOR: Record<Phase, string> = {
  A: "#2596be", // blue
  B: "#e8c33d", // amber
  C: "#4caf7d", // green
};

function loadFill(phase: Phase, watts: number, dark: boolean): string {
  if (dark || watts <= 0) return "#141b26";
  return PHASE_COLOR[phase];
}

export function RackView({
  anatomy,
  state,
  phases,
  labels,
  watts,
  selected,
  onSelect,
  onCycleLoad,
}: {
  anatomy: RackMap;
  state: SimState | null;
  phases: Phase[]; // current phase per load slot (config-level truth)
  labels: string[];
  watts: number[];
  selected: string | null;
  onSelect: (id: string | null) => void;
  onCycleLoad: (index: number) => void;
}) {
  const rw = state?.regionWatts ?? {};
  const tripped = new Set(state?.trippedPhases ?? []);
  const rackDark = state ? !state.rackPowered : false;

  const phaseOf = (id: string): Phase | null =>
    id === "pdu-a" ? "A" : id === "pdu-b" ? "B" : id === "pdu-c" ? "C" : null;

  return (
    <svg
      className="rack-svg"
      viewBox={`0 0 ${anatomy.width} ${anatomy.height}`}
      role="img"
      aria-label="Rack power-layer elevation"
    >
      <rect
        x={0} y={0} width={anatomy.width} height={anatomy.height}
        rx={1.5} fill="#0d1420" stroke="#1f2935" strokeWidth={0.4}
      />
      {anatomy.regions.map((r) => {
        const isLoad = r.kind === "load";
        const idx = isLoad ? Number(r.id.split("-")[1]) - 1 : -1;
        const live = rw[r.id] ?? 0;
        const strip = phaseOf(r.id);
        let fill = "#141b26";
        let stroke = "#2a3644";
        if (isLoad && idx >= 0) {
          fill = loadFill(phases[idx] ?? "A", watts[idx] ?? 0, rackDark);
          if ((watts[idx] ?? 0) > 0 && !rackDark && state) {
            const p = phases[idx];
            if (p && tripped.has(p)) fill = "#3a1512";
          }
        } else if (strip) {
          fill = tripped.has(strip)
            ? "#3a1512"
            : live > 0
              ? PHASE_COLOR[strip]
              : "#141b26";
          stroke = PHASE_COLOR[strip];
        } else if (r.kind === "ups") {
          fill = state?.onBattery ? "#7a4a12" : live > 0 ? "#1d2a3a" : "#141b26";
        } else if (r.kind === "battery") {
          fill = (state?.batteryOutputW ?? 0) > 0 ? "#7a4a12" : "#141b26";
        }
        const isSel = selected === r.id;
        return (
          <g
            key={r.id}
            onClick={() => {
              onSelect(isSel ? null : r.id);
              if (isLoad && idx >= 0) onCycleLoad(idx);
            }}
            style={{ cursor: "pointer" }}
          >
            <rect
              x={r.x} y={r.y} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              fillOpacity={isLoad && (watts[idx] ?? 0) > 0 && !rackDark ? 0.55 : 0.9}
              stroke={isSel ? "#ffffff" : stroke}
              strokeWidth={isSel ? 0.5 : 0.3}
            />
            <text
              x={r.x + 1.4}
              y={r.y + r.h / 2 + 1.1}
              fontSize={2.6}
              fill="#d7dee8"
              fontFamily="ui-monospace, monospace"
            >
              {isLoad && idx >= 0
                ? `${labels[idx] ?? r.label} · ${(watts[idx] ?? 0).toFixed(0)} W · ${phases[idx] ?? "?"}`
                : r.label}
            </text>
            {!isLoad && (
              <text
                x={r.x + r.w - 1.4}
                y={r.y + r.h - 1.6}
                fontSize={2.4}
                textAnchor="end"
                fill="#9fb0c3"
                fontFamily="ui-monospace, monospace"
              >
                {strip && tripped.has(strip) ? "TRIPPED" : `${live.toFixed(0)} W`}
              </text>
            )}
          </g>
        );
      })}
      {/* Feed direction annotations */}
      <text x={2} y={anatomy.height - 0.8} fontSize={2.2} fill="#5d6f83"
        fontFamily="ui-monospace, monospace">
        UPS FEEDS THE PHASES · CLICK A SLOT TO CYCLE ITS PHASE
      </text>
    </svg>
  );
}
