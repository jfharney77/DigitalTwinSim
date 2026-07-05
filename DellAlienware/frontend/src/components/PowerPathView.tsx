import type { PowerState } from "../types";

// The centerpiece dark diagram: a stylized schematic of the m18's AC power
// path — wall → adapter brick → DC-in jack → EC/charger → battery below,
// CPU/GPU/fans on the board. Painted from the current PowerState: flows light
// up with wattage labels, components in `activeRegions` pulse, the battery
// bar tracks batteryPct, fans spin with fanPct. Not the anatomy floorplan —
// this is the electrical mental model, drawn left (wall) to right (silicon).

function fmtW(w: number): string {
  return `${Math.round(w * 10) / 10} W`;
}

// One power flow: a dim base path always visible, plus an animated dashed
// overlay in the flow color while power is actually moving.
function Flow({
  d,
  on,
  color,
  reverse,
}: {
  d: string;
  on: boolean;
  color: string;
  reverse?: boolean;
}) {
  return (
    <g>
      <path d={d} className="pp-flow-base" />
      {on && (
        <path
          d={d}
          className={reverse ? "pp-flow-on pp-flow-rev" : "pp-flow-on"}
          style={{ stroke: color }}
        />
      )}
    </g>
  );
}

// A named block on the schematic. Lights up while its region id is in the
// current state's activeRegions.
function Block({
  id,
  active,
  x,
  y,
  w,
  h,
  label,
  sub,
}: {
  id: string;
  active: Set<string>;
  x: number;
  y: number;
  w: number;
  h: number;
  label: string;
  sub?: string;
}) {
  const on = active.has(id);
  return (
    <g className={on ? "pp-block pp-active" : "pp-block"}>
      <rect x={x} y={y} width={w} height={h} rx={0.8} />
      <text x={x + w / 2} y={y + h / 2 + (sub ? -0.4 : 0.7)} textAnchor="middle">
        {label}
      </text>
      {sub && (
        <text className="pp-sub" x={x + w / 2} y={y + h / 2 + 2.2} textAnchor="middle">
          {sub}
        </text>
      )}
    </g>
  );
}

function Fan({
  id,
  active,
  cx,
  cy,
  fanPct,
}: {
  id: string;
  active: Set<string>;
  cx: number;
  cy: number;
  fanPct: number;
}) {
  const on = active.has(id) || fanPct > 0;
  // Faster spin and stronger presence as fanPct rises.
  const dur = fanPct > 0 ? Math.max(0.5, 3 - 2.4 * (fanPct / 100)) : 0;
  const opacity = 0.35 + 0.65 * (fanPct / 100);
  return (
    <g className={on ? "pp-fan pp-fan-on" : "pp-fan"} opacity={opacity}>
      <circle cx={cx} cy={cy} r={3.6} className="pp-fan-ring" />
      <g
        className="pp-fan-blades"
        style={
          dur > 0
            ? { animationDuration: `${dur}s`, transformOrigin: `${cx}px ${cy}px` }
            : undefined
        }
      >
        {[0, 120, 240].map((a) => (
          <path
            key={a}
            d={`M ${cx} ${cy} l 2.6 -1 a 3 3 0 0 1 -2.6 2.4 z`}
            transform={`rotate(${a} ${cx} ${cy})`}
          />
        ))}
      </g>
      <text x={cx} y={cy + 6.4} textAnchor="middle" className="pp-fan-label">
        {Math.round(fanPct)}%
      </text>
    </g>
  );
}

export function PowerPathView({ state }: { state: PowerState | null }) {
  const active = new Set(state?.activeRegions ?? []);
  const acOn = (state?.acW ?? 0) > 0;
  const chargeOn = (state?.chargeW ?? 0) > 0;
  const hybridOn = (state?.batteryW ?? 0) > 0;
  const sysOn = (state?.systemW ?? 0) > 0;
  const batteryPct = state?.batteryPct ?? 0;
  const plugged = state !== null && state.phase !== "off";

  // System rail color: amber while the battery is supplementing, blue on AC.
  const sysColor = hybridOn ? "var(--flow-hybrid)" : "var(--flow-ac)";

  return (
    <div className="pp-wrap">
      <svg viewBox="0 0 100 64" aria-label="Alienware m18 power path schematic">
        {/* Wall outlet */}
        <g className="pp-block">
          <rect x={1} y={20.5} width={5} height={9} rx={0.8} />
          <circle cx={3.5} cy={23.5} r={0.6} fill="var(--wire)" stroke="none" />
          <circle cx={3.5} cy={26.5} r={0.6} fill="var(--wire)" stroke="none" />
          <text x={3.5} y={32.6} textAnchor="middle" className="pp-sub">
            AC mains
          </text>
        </g>

        {/* Adapter brick — lit as soon as it is producing DC. */}
        <g className={plugged ? "pp-block pp-active" : "pp-block"}>
          <rect x={9.5} y={20.5} width={14} height={9} rx={1} />
          <text x={16.5} y={24.2} textAnchor="middle">
            adapter
          </text>
          <text x={16.5} y={26.8} textAnchor="middle" className="pp-sub">
            19.5 VDC out
          </text>
          {/* LED ring on the plug — lit means the brick has DC output. */}
          <circle
            cx={22.2}
            cy={22.2}
            r={0.7}
            fill={plugged ? "var(--flow-ac)" : "var(--core-off)"}
            stroke="none"
          />
        </g>

        {/* Laptop outline */}
        <rect x={29} y={1.5} width={69.5} height={61} rx={1.5} className="pp-chassis" />
        <text x={31} y={60.4} className="pp-sub">
          Alienware m18 (schematic, not to scale)
        </text>

        {/* Wall → adapter (always carrying when plugged) */}
        <Flow d="M 6 25 L 9.5 25" on={plugged} color="var(--flow-ac)" />

        {/* Adapter → DC-in, with live AC wattage */}
        <Flow d="M 23.5 25 L 31 25" on={acOn} color="var(--flow-ac)" />
        <text
          x={26.5}
          y={22.6}
          textAnchor="middle"
          className="pp-watts"
          fill={acOn ? "var(--flow-ac)" : "var(--txt-dim)"}
        >
          {fmtW(state?.acW ?? 0)}
        </text>

        {/* DC-in jack */}
        <Block id="dc-in" active={active} x={31} y={22} w={6} h={6} label="DC-in" />

        {/* DC-in → charger */}
        <Flow d="M 37 25 L 41 25" on={acOn} color="var(--flow-ac)" />

        {/* EC above the charger — it owns the handshake and the policy. */}
        <Block
          id="ec"
          active={active}
          x={41}
          y={7}
          w={12}
          h={8}
          label="EC"
          sub="embedded ctrl"
        />
        {/* EC ↔ charger control link (not a power flow) */}
        <path d="M 47 15 L 47 21" className="pp-ctrl" />

        {/* Charger / power-path IC */}
        <Block
          id="charger"
          active={active}
          x={41}
          y={21}
          w={12}
          h={8}
          label="charger"
          sub="power path"
        />

        {/* Charger → system rail (board) */}
        <Flow d="M 53 25 L 58 25 L 58 14 L 60.5 14" on={sysOn} color={sysColor} />
        <text
          x={56}
          y={19.4}
          textAnchor="middle"
          className="pp-watts"
          fill={sysOn ? sysColor : "var(--txt-dim)"}
        >
          {fmtW(state?.systemW ?? 0)}
        </text>

        {/* Charger → battery (charging, down) */}
        <Flow d="M 44.5 29 L 44.5 43" on={chargeOn} color="var(--flow-charge)" />
        {/* Battery → charger (hybrid supplement, up) */}
        <Flow d="M 50 43 L 50 29" on={hybridOn} color="var(--flow-hybrid)" reverse />
        <text
          x={41.5}
          y={37}
          textAnchor="end"
          className="pp-watts"
          fill={chargeOn ? "var(--flow-charge)" : "var(--txt-dim)"}
        >
          {chargeOn ? `+${fmtW(state?.chargeW ?? 0)}` : "0 W"}
        </text>
        <text
          x={53}
          y={37}
          className="pp-watts"
          fill={hybridOn ? "var(--flow-hybrid)" : "var(--txt-dim)"}
        >
          {hybridOn ? `−${fmtW(state?.batteryW ?? 0)}` : "0 W"}
        </text>

        {/* Battery pack with fill bar */}
        <g className={active.has("battery") ? "pp-block pp-active" : "pp-block"}>
          <rect x={35} y={43} width={33} height={13} rx={1} />
          <rect x={36.5} y={49} width={30} height={5} rx={0.6} className="pp-batt-well" />
          <rect
            x={36.5}
            y={49}
            width={Math.max(0, Math.min(30, (batteryPct / 100) * 30))}
            height={5}
            rx={0.6}
            className={
              chargeOn ? "pp-batt-fill pp-batt-charging" : "pp-batt-fill"
            }
            style={{
              fill: hybridOn
                ? "var(--flow-hybrid)"
                : batteryPct < 20
                  ? "var(--core-hot)"
                  : "var(--flow-charge)",
            }}
          />
          <text x={38} y={46.8} className="pp-batt-label">
            battery · {Math.round(batteryPct)}%
          </text>
          <text x={66.5} y={46.8} textAnchor="end" className="pp-sub">
            {state?.chargeStage ?? "idle"}
          </text>
        </g>

        {/* Board with CPU / heat pipes / GPU / memory / fans */}
        <g className={active.has("board") ? "pp-block pp-active" : "pp-block"}>
          <rect x={60.5} y={3.5} width={36.5} height={38} rx={1} className="pp-board" />
        </g>
        <Block id="cpu" active={active} x={63} y={7} w={12} h={11} label="CPU" sub={fmtW(state?.cpuW ?? 0)} />
        <Block id="heatpipes" active={active} x={75} y={10.5} w={7} h={4} label="pipes" />
        <Block id="gpu" active={active} x={82} y={7} w={13} h={11} label="GPU" sub={fmtW(state?.gpuW ?? 0)} />
        <Block id="vram" active={active} x={82} y={19.5} w={13} h={4} label="VRAM" />
        <Block id="dimm" active={active} x={63} y={19.5} w={12} h={4} label="DDR5" />
        <Block id="ssd" active={active} x={70} y={31} w={9} h={5.5} label="SSD" />
        <Fan id="fan-left" active={active} cx={66} cy={31.5} fanPct={state?.fanPct ?? 0} />
        <Fan id="fan-right" active={active} cx={90} cy={31.5} fanPct={state?.fanPct ?? 0} />
      </svg>

      {/* Stage caption: what this step of the trace is doing. */}
      {state && (
        <div className="pp-desc">
          <strong>{state.label}.</strong> {state.description}
        </div>
      )}
    </div>
  );
}
