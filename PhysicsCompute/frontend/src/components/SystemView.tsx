import type { SimState, SystemMap, SystemRegion } from "../types";

// The system map painted by temperature. Fixed 15–105 °C scale, same
// color-blind-safe ramp as the rest of the physics suite; the coolant
// throttle line (65 °C) is marked on the legend for the rack view.

const MARGIN = 2.5;
const T_MIN = 15;
const T_MAX = 105;

const STOPS: [number, string][] = [
  [0.0, "#2c4fd8"],
  [0.25, "#2596be"],
  [0.5, "#7fbf5a"],
  [0.7, "#e8c33d"],
  [0.85, "#e07b28"],
  [1.0, "#c8281e"],
];

function lerpColor(a: string, b: string, f: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  const c = pa.map((v, i) => Math.round(v + (pb[i] - v) * f));
  return `#${c.map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

export function tempColor(t: number): string {
  const f = Math.max(0, Math.min(1, (t - T_MIN) / (T_MAX - T_MIN)));
  for (let i = 1; i < STOPS.length; i++) {
    if (f <= STOPS[i][0]) {
      const [f0, c0] = STOPS[i - 1];
      const [f1, c1] = STOPS[i];
      return lerpColor(c0, c1, (f - f0) / (f1 - f0));
    }
  }
  return STOPS[STOPS.length - 1][1];
}

export function SystemView({
  anatomy,
  state,
  selected,
  onSelect,
}: {
  anatomy: SystemMap;
  state: SimState | null;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
}) {
  const W = anatomy.width + 2 * MARGIN;
  const H = anatomy.height + 2 * MARGIN;
  const rx = (r: SystemRegion) => r.x + MARGIN;
  const ry = (r: SystemRegion) => r.y + MARGIN;
  const isRack = anatomy.id === "xe9712";

  return (
    <svg
      viewBox={`0 0 ${W} ${H + 10}`}
      aria-label={`${anatomy.name} thermal map`}
      onClick={() => onSelect?.(null)}
    >
      <rect
        x={0.5} y={0.5} width={W - 1} height={H - 1} rx={1.5}
        fill="#0d1420" stroke="#1f2935" strokeWidth={0.6}
      />
      {state && isRack && state.flowLpm > 0 && (
        <g strokeWidth={0.8} opacity={0.85} fill="none">
          {/* supply riser: cool, upward; return riser: warm, downward */}
          <line
            className="flowline"
            x1={86.5} y1={H - 4} x2={86.5} y2={6}
            stroke={tempColor(state.coolantSupplyC)}
            style={{ animationDuration: `${Math.max(0.5, 30 / Math.max(state.flowLpm / 10, 1))}s` }}
          />
          <line
            className="flowline"
            x1={96.5} y1={6} x2={96.5} y2={H - 4}
            stroke={tempColor(state.coolantReturnC)}
            style={{ animationDuration: `${Math.max(0.5, 30 / Math.max(state.flowLpm / 10, 1))}s` }}
          />
        </g>
      )}
      {state && !isRack && state.fanRpmPct > 0 && (
        <g stroke="#2596be" strokeWidth={0.5} opacity={0.7}>
          {[12, 27, 42].map((y) => (
            <line
              key={y}
              className="flowline"
              x1={4} y1={y} x2={W - 4} y2={y}
              style={{ animationDuration: `${Math.max(0.6, 6 - state.fanRpmPct / 20)}s` }}
            />
          ))}
        </g>
      )}
      {anatomy.regions.map((r) => {
        const temp = state?.regionTemps[r.id] ?? T_MIN;
        const isSel = r.id === selected;
        const fill = tempColor(temp);
        const len = r.label.length || 1;
        const hSize = Math.min(1.9, r.h * 0.42, (r.w - 1.4) / (len * 0.62));
        const vSize = Math.min(1.9, r.w * 0.42, (r.h - 1.4) / (len * 0.62));
        const showLabel = !!r.label && r.h > 3.2 && hSize >= 1.0;
        const showVLabel = !showLabel && !!r.label && r.w >= 3 && vSize >= 1.0;
        return (
          <g
            key={r.id}
            className="an-region"
            onClick={(e) => {
              e.stopPropagation();
              onSelect?.(isSel ? null : r.id);
            }}
          >
            <rect
              x={rx(r)} y={ry(r)} width={r.w} height={r.h} rx={0.8}
              fill={fill}
              stroke={isSel ? "var(--accent)" : "#0d1420"}
              strokeWidth={isSel ? 0.6 : 0.3}
            />
            {showLabel && !showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + (r.h < 6 ? r.h / 2 + hSize * 0.35 : 2.4)}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={Math.max(hSize, 1.0)}
                fontWeight={600}
                letterSpacing={0.1}
              >
                {r.label}
              </text>
            )}
            {showVLabel && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h / 2}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={vSize}
                fontWeight={600}
                transform={`rotate(-90 ${rx(r) + r.w / 2} ${ry(r) + r.h / 2})`}
              >
                {r.label}
              </text>
            )}
            {r.w >= 12 && r.h >= 7 && state && (
              <text
                x={rx(r) + r.w / 2}
                y={ry(r) + r.h - 1.6}
                textAnchor="middle"
                fill="#0d1420"
                fontSize={1.7}
                fontWeight={700}
              >
                {temp.toFixed(0)}°
              </text>
            )}
          </g>
        );
      })}
      {isRack && (
        <g pointerEvents="none">
          {/* V5 bezel facsimile: tray faceplates with handles and state
              LEDs, PSU faces on the shelf, NVSwitch port row, CDU
              grille — recognizably the machine, honestly an
              illustration (labeled in the legend). */}
          {anatomy.regions.map((r) => {
            const temp = state?.regionTemps[r.id] ?? T_MIN;
            const led = temp < 55 ? "#7fbf5a" : temp < 70 ? "#e8c33d" : "#c8281e";
            const x0 = rx(r);
            const y0 = ry(r);
            if (r.kind === "tray") {
              const n = 4;
              return (
                <g key={r.id}>
                  {Array.from({ length: n }, (_, i) => {
                    const tx = x0 + 1 + (i * (r.w - 2)) / n;
                    const tw = (r.w - 2) / n - 1;
                    return (
                      <g key={i}>
                        <rect x={tx} y={y0 + 1} width={tw} height={r.h - 2}
                          rx={0.6} fill="none" stroke="#0d1420" strokeWidth={0.35} />
                        <rect x={tx + 1} y={y0 + r.h / 2 - 0.5} width={2.2}
                          height={1} rx={0.3} fill="#0d1420" opacity={0.55} />
                        <circle cx={tx + tw - 1.4} cy={y0 + 2.2} r={0.7} fill={led} />
                      </g>
                    );
                  })}
                </g>
              );
            }
            if (r.kind === "power") {
              const n = 6;
              return (
                <g key={r.id}>
                  {Array.from({ length: n }, (_, i) => {
                    const px = x0 + 1 + (i * (r.w - 2)) / n;
                    const pw = (r.w - 2) / n - 0.8;
                    return (
                      <g key={i}>
                        <rect x={px} y={y0 + 1.2} width={pw} height={r.h - 2.4}
                          rx={0.4} fill="none" stroke="#0d1420" strokeWidth={0.3} />
                        <circle cx={px + pw / 2} cy={y0 + r.h - 2} r={0.55}
                          fill={state?.poweredOn === false ? "#5a6b82" : "#7fbf5a"} />
                      </g>
                    );
                  })}
                </g>
              );
            }
            if (r.kind === "nvswitch") {
              return (
                <g key={r.id} opacity={0.6}>
                  {Array.from({ length: 18 }, (_, i) => (
                    <rect key={i} x={x0 + 2 + i * 4} y={y0 + r.h - 2.6}
                      width={2.6} height={1.4} rx={0.2} fill="#0d1420" />
                  ))}
                </g>
              );
            }
            if (r.kind === "cdu") {
              return (
                <g key={r.id} stroke="#0d1420" strokeWidth={0.3} opacity={0.5}>
                  {Array.from({ length: 3 }, (_, i) => (
                    <line key={i} x1={x0 + 2} y1={y0 + 2 + i * 2}
                      x2={x0 + r.w - 2} y2={y0 + 2 + i * 2} />
                  ))}
                </g>
              );
            }
            return null;
          })}
        </g>
      )}
      <g>
        {Array.from({ length: 30 }, (_, i) => (
          <rect
            key={i}
            x={MARGIN + i * 2}
            y={H + 1.2}
            width={2}
            height={2.2}
            fill={tempColor(T_MIN + ((i + 0.5) / 30) * (T_MAX - T_MIN))}
          />
        ))}
        {isRack && (() => {
          const capX = MARGIN + ((65 - T_MIN) / (T_MAX - T_MIN)) * 60;
          return (
            <g>
              <line x1={capX} y1={H + 0.6} x2={capX} y2={H + 4} stroke="#fff" strokeWidth={0.35} />
              <text x={capX} y={H + 6.6} textAnchor="middle" fill="#8fa3bd" fontSize={1.6}>
                coolant throttle
              </text>
            </g>
          );
        })()}
        <text x={MARGIN} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          {T_MIN} °C
        </text>
        <text x={MARGIN + 62} y={H + 6.6} fill="#5a6b82" fontSize={1.7}>
          {T_MAX} °C
        </text>
        <text x={W - MARGIN} y={H + 6.6} textAnchor="end" fill="#5a6b82" fontSize={1.7}>
          {isRack ? "front elevation (bezels are illustration) · click a zone" : "top-down, FRONT left · click a zone"}
        </text>
      </g>
    </svg>
  );
}
