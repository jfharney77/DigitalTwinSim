import { useMemo } from "react";
import type { ContentProfile, PanelMap, SimState } from "../types";

// The monitor drawn face-on. The screen area previews the content profile
// and — on the mini-LED class — dims per local-dimming zone: a 20×10 cell
// grid stands in for the 2,000 real zones (10× scale, labeled). Edge-lit
// draws one uniform glow fed from a bottom strip. Standby goes dark.
//
// The zone pattern is a deterministic hash of (row, col, content), so the
// same state always paints the same picture — no randomness, same rule as
// the engine.

const ZONE_COLS = 20;
const ZONE_ROWS = 10;

function cellHash(r: number, c: number, salt: number): number {
  // Deterministic 0–1 pseudo-pattern; stable across renders.
  const x = Math.sin(r * 127.1 + c * 311.7 + salt * 74.7) * 43758.5453;
  return x - Math.floor(x);
}

const CONTENT_SALT: Record<ContentProfile, number> = {
  dark: 1, mixed: 2, bright: 3, hdr: 4,
};

interface Props {
  anatomy: PanelMap;
  state: SimState | null;
  isMiniled: boolean;
  dimming: boolean;
  selected: string | null;
  onSelect: (id: string | null) => void;
}

export function MonitorView({
  anatomy, state, isMiniled, dimming, selected, onSelect,
}: Props) {
  const on = state?.on ?? false;
  const lit = state?.litFraction ?? 0;
  const content = state?.content ?? "mixed";
  const brightness = (state?.brightnessPct ?? 0) / 100;
  const hdr = content === "hdr";

  const zones = useMemo(() => {
    if (!isMiniled) return [];
    const salt = CONTENT_SALT[content];
    const out: { r: number; c: number; v: number }[] = [];
    for (let r = 0; r < ZONE_ROWS; r++) {
      for (let c = 0; c < ZONE_COLS; c++) {
        const h = cellHash(r, c, salt);
        // A cell is "lit" when its hash falls under the lit fraction;
        // dimming off means every cell is driven.
        const driven = dimming ? h < Math.max(lit, 0.04) : true;
        out.push({ r, c, v: driven ? (hdr ? 1 : 0.85) : 0.06 });
      }
    }
    return out;
  }, [isMiniled, content, lit, dimming, hdr]);

  const panel = anatomy.regions.find((r) => r.id === "panel");
  const shelf = anatomy.regions.filter((r) => r.y > 48);
  const backlight = anatomy.regions.find((r) => r.id === "backlight");
  const vb = `0 0 ${anatomy.width} ${anatomy.height}`;

  const glow = on ? 0.15 + 0.75 * brightness * (isMiniled && dimming ? lit : 1) : 0;

  return (
    <svg viewBox={vb} className="monitor-view" role="img"
         aria-label="Monitor front view">
      {/* Bezel */}
      {panel && (
        <g onClick={() => onSelect(selected === "panel" ? null : "panel")}
           style={{ cursor: "pointer" }}>
          <rect x={panel.x - 1.5} y={panel.y - 1.5}
                width={panel.w + 3} height={panel.h + 3} rx={1.2}
                fill="#0b0e13" stroke={selected === "panel" ? "#3f8cff" : "#2a3140"}
                strokeWidth={0.5} />
          {/* Screen field */}
          <rect x={panel.x} y={panel.y} width={panel.w} height={panel.h}
                fill={on ? `rgba(120,170,255,${0.04 + glow * 0.25})` : "#05070a"} />
          {/* Edge-lit: uniform wash + the strip itself */}
          {!isMiniled && on && (
            <>
              <rect x={panel.x} y={panel.y} width={panel.w} height={panel.h}
                    fill={`rgba(190,215,255,${glow * 0.5})`} />
              <rect x={panel.x} y={panel.y + panel.h - 1.2} width={panel.w}
                    height={1.2} fill={`rgba(120,190,255,${0.3 + brightness * 0.7})`} />
            </>
          )}
          {/* Mini-LED zone grid */}
          {isMiniled && on && zones.map(({ r, c, v }) => (
            <rect key={`${r}-${c}`}
                  x={panel.x + (c * panel.w) / ZONE_COLS + 0.15}
                  y={panel.y + (r * panel.h) / ZONE_ROWS + 0.15}
                  width={panel.w / ZONE_COLS - 0.3}
                  height={panel.h / ZONE_ROWS - 0.3}
                  rx={0.2}
                  fill={hdr && v === 1
                    ? `rgba(255,250,230,${0.9 * brightness + 0.1})`
                    : `rgba(150,195,255,${v * (0.25 + 0.65 * brightness)})`} />
          ))}
          {!on && (
            <text x={panel.x + panel.w / 2} y={panel.y + panel.h / 2}
                  textAnchor="middle" fontSize={2.6} fill="#3a4354"
                  fontFamily="ui-monospace, monospace">
              STANDBY · {state ? state.acPowerW.toFixed(1) : "0.3"} W
            </text>
          )}
        </g>
      )}

      {/* Backlight band label */}
      {backlight && (
        <g onClick={() => onSelect(selected === "backlight" ? null : "backlight")}
           style={{ cursor: "pointer" }}>
          <rect x={backlight.x} y={backlight.y} width={backlight.w}
                height={backlight.h} rx={0.8}
                fill={on ? `rgba(120,190,255,${0.05 + glow * 0.3})` : "#0b0e13"}
                stroke={selected === "backlight" ? "#3f8cff" : "#232a38"}
                strokeWidth={0.4} />
          <text x={backlight.x + 2} y={backlight.y + backlight.h / 2 + 1}
                fontSize={2.4} fill="#8fa3c0"
                fontFamily="ui-monospace, monospace">
            {isMiniled
              ? `BACKLIGHT — 2,000 ZONES (drawn 200, 10× scale) · ${state?.zonesLit ?? 0} lit`
              : "BACKLIGHT — EDGE STRIP · all or nothing"}
          </text>
        </g>
      )}

      {/* Electronics shelf */}
      {shelf.map((r) => (
        <g key={r.id}
           onClick={() => onSelect(selected === r.id ? null : r.id)}
           style={{ cursor: "pointer" }}>
          <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={0.8}
                fill={r.id === "hub" && (state?.hubOutW ?? 0) > 0
                  ? "rgba(90,200,140,0.18)"
                  : "#10141c"}
                stroke={selected === r.id ? "#3f8cff" : "#232a38"}
                strokeWidth={0.4} />
          <text x={r.x + r.w / 2} y={r.y + r.h / 2 + 0.9}
                textAnchor="middle" fontSize={2.1} fill="#8fa3c0"
                fontFamily="ui-monospace, monospace">
            {r.label}
          </text>
          {r.id === "hub" && (state?.hubOutW ?? 0) > 0 && (
            <text x={r.x + r.w / 2} y={r.y + r.h - 1.2} textAnchor="middle"
                  fontSize={1.9} fill="#5ac88c"
                  fontFamily="ui-monospace, monospace">
              → {state?.hubOutW.toFixed(0)} W to laptop
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}
