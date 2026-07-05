import { InfoDot } from "./InfoDot";
import type {
  AdapterOption,
  LaptopProfile,
  ThermalMode,
  WorkloadKind,
} from "../types";

const THERMAL_MODES: { id: ThermalMode; name: string }[] = [
  { id: "quiet", name: "Quiet" },
  { id: "balanced", name: "Balanced" },
  { id: "performance", name: "Performance" },
  { id: "fullSpeed", name: "Full Speed" },
];

const WORKLOADS: { id: WorkloadKind; name: string }[] = [
  { id: "idle", name: "Idle (desktop)" },
  { id: "gaming", name: "Gaming" },
  { id: "fullLoad", name: "Full load (CPU+GPU burn)" },
];

export function PowerControls({
  profiles,
  profileId,
  onProfile,
  adapters,
  adapterId,
  onAdapter,
  startBatteryPct,
  onStartBatteryPct,
  thermalMode,
  onThermalMode,
  workload,
  onWorkload,
  speed,
  onSpeed,
  running,
  done,
  phaseLabel,
  onRun,
  onPause,
  onStep,
  onReset,
}: {
  profiles: LaptopProfile[];
  profileId: string;
  onProfile: (id: string) => void;
  adapters: AdapterOption[];
  adapterId: string;
  onAdapter: (id: string) => void;
  startBatteryPct: number;
  onStartBatteryPct: (pct: number) => void;
  thermalMode: ThermalMode;
  onThermalMode: (m: ThermalMode) => void;
  workload: WorkloadKind;
  onWorkload: (w: WorkloadKind) => void;
  speed: number;
  onSpeed: (s: number) => void;
  running: boolean;
  done: boolean;
  phaseLabel: string;
  onRun: () => void;
  onPause: () => void;
  onStep: () => void;
  onReset: () => void;
}) {
  const adapter = adapters.find((a) => a.id === adapterId) ?? null;
  return (
    <>
      <div className="an-panel">
        <div className="field-head">
          <h2 className="with-info">Scenario</h2>
          <InfoDot title="Scenario">
            <p>
              Every control here changes the input to the simulation. The
              backend recomputes the whole plug-in trace — detect, handshake,
              power budget, charging, boot, load — and playback starts over
              from the beginning.
            </p>
          </InfoDot>
        </div>

        <label className="field">
          <span className="field-head">
            Laptop
            <InfoDot title="Laptop profile">
              <p>
                The machine being simulated. The profile sets the CPU power
                limit, the GPU's TGP (total graphics power — the sustained
                wattage the GPU package may draw), the battery capacity in
                watt-hours, and which adapters Dell ships for it.
              </p>
            </InfoDot>
          </span>
          <select value={profileId} onChange={(e) => onProfile(e.target.value)}>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-head">
            AC adapter
            <InfoDot title="AC adapter and the PSID handshake">
              <p>
                Dell barrel plugs carry three conductors: outer barrel ground,
                inner barrel +19.5 V, and a center pin used for a 1-Wire data
                link. A small ID chip in the brick (the PSID, power supply ID)
                answers over that pin with the adapter's family, wattage,
                voltage and current, plus a checksum.
              </p>
              <p>
                The EC (embedded controller — the always-on microcontroller
                that manages power, charging and fans) reads the PSID before
                trusting the supply. If the pin is bent or the chip is missing
                (many third-party bricks), BIOS reports the adapter as
                Unknown: charging is disabled or slowed and CPU/GPU power is
                capped, because the platform cannot verify how much current it
                may draw. The unrecognized option here models exactly that.
              </p>
            </InfoDot>
          </span>
          <select value={adapterId} onChange={(e) => onAdapter(e.target.value)}>
            {adapters.map((a) => (
              <option key={a.id} value={a.id}>
                {a.name} — {a.watts} W, {a.connector === "usbc" ? "USB-C" : "barrel"}
                {a.recognized ? "" : " (not recognized)"}
              </option>
            ))}
          </select>
          {adapter && (
            <span className="mini">
              {adapter.voltage} V · {adapter.amps} A ·{" "}
              {adapter.recognized
                ? "PSID handshake succeeds"
                : "PSID handshake fails — BIOS will show Unknown"}
            </span>
          )}
        </label>

        <label className="field">
          <span className="field-head">
            Start battery: {startBatteryPct}%
            <InfoDot title="Starting battery level">
              <p>
                Charge level when the plug goes in. It decides the charge
                stage (a deeply drained pack starts with a gentle precharge,
                then constant current, then a constant-voltage taper) and
                whether hybrid power is available: below about 20% the
                battery is not allowed to supplement the adapter, so the
                system throttles instead.
              </p>
              <p>
                Above ~94% the charger deliberately does nothing — Dell holds
                a 94–100% band where charging will not restart, to avoid
                micro-cycling the cells.
              </p>
            </InfoDot>
          </span>
          <input
            type="range"
            min={0}
            max={100}
            value={startBatteryPct}
            onChange={(e) => onStartBatteryPct(Number(e.target.value))}
          />
        </label>

        <label className="field">
          <span className="field-head">
            Thermal mode
            <InfoDot title="Thermal modes (AWCC)">
              <p>
                AWCC (Alienware Command Center, Dell's control software) offers
                operating modes that trade noise for sustained clocks: Quiet,
                Balanced, Performance, and Full Speed (fans pinned at 100%).
                A more aggressive fan curve keeps the CPU and GPU inside
                their temperature limits longer, so they hold higher power.
              </p>
              <p>
                Touching 99–100 °C under load is documented as normal for
                these machines — the thermal control circuit trims a few
                hundred MHz and carries on.
              </p>
            </InfoDot>
          </span>
          <select
            value={thermalMode}
            onChange={(e) => onThermalMode(e.target.value as ThermalMode)}
          >
            {THERMAL_MODES.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field-head">
            Workload
            <InfoDot title="Workload">
              <p>
                What the machine does after boot. Idle sits near the platform
                floor (~25 W). Gaming pushes the GPU toward its TGP with a
                moderate CPU load. Full load runs CPU and GPU flat out — on an
                m18 that can exceed what even a 280 W adapter delivers, which
                is when hybrid power pulls the difference from the battery
                instead of throttling.
              </p>
            </InfoDot>
          </span>
          <select
            value={workload}
            onChange={(e) => onWorkload(e.target.value as WorkloadKind)}
          >
            {WORKLOADS.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="an-panel">
        <div className="field-head">
          <h2 className="with-info">Playback</h2>
          <InfoDot title="Playback">
            <p>
              The trace is fixed data computed by the backend; Run only plays
              it back. Step walks one event at a time. Stages that take longer
              in the real world (charging, boot) dwell on screen longer.
            </p>
          </InfoDot>
        </div>
        <div className="btnrow">
          {running ? (
            <button className="primary" onClick={onPause}>
              Pause
            </button>
          ) : (
            <button className="primary" onClick={onRun}>
              Run
            </button>
          )}
          <button onClick={onStep}>Step</button>
          <button onClick={onReset}>Reset</button>
        </div>
        <label className="field" style={{ marginTop: 10 }}>
          Speed
          <input
            type="range"
            min={1}
            max={20}
            value={speed}
            onChange={(e) => onSpeed(Number(e.target.value))}
          />
        </label>
        <div className="phase">
          {done ? "✓ " : ""}
          {phaseLabel}
        </div>
      </div>
    </>
  );
}
