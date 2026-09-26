import type {
  ConfigPreset,
  ServerConfig,
  Validation,
} from "../types";
import { CPU_TDP_TIERS, DIMM_COUNTS, PSU_CAPACITIES } from "../types";

// The build panel (spec §7 left column): configuration controls with the
// validation results inline — the mini thermal-restriction document.
//
// The labels carry the reading level too. This panel is the first thing a
// guided scenario asks anyone to touch, and at level 1 a row reading "CPU
// TDP tier · 16× E3.S NVMe · 1+1 redundant" is a wall of undefined terms.
// The controls do the same thing at every level; only the words change.

const MAX_DRIVES: Record<string, number> = {
  "12x3.5": 12,
  "24x2.5": 24,
  "16xE3.S": 16,
};

// label at levels 3+, label at levels 1–2.
type Labels = { std: string; novice: string };

function pick(level: number, l: Labels): string {
  return level <= 2 ? l.novice : l.std;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="field cfg-row">
      <span className="cfg-label">{label}</span>
      {children}
    </label>
  );
}

export function BuildPanel({
  level,
  config,
  presets,
  validations,
  onChange,
  onPreset,
}: {
  level: number;
  config: ServerConfig;
  presets: ConfigPreset[];
  validations: Validation[];
  onChange: (c: ServerConfig) => void;
  onPreset: (p: ConfigPreset) => void;
}) {
  const set = (patch: Partial<ServerConfig>) => {
    const next = { ...config, ...patch };
    // Keep drive count legal for the chassis.
    next.drives = Math.min(next.drives, MAX_DRIVES[next.chassis]);
    onChange(next);
  };
  const problems = validations.filter((v) => v.level !== "ok");

  return (
    <div className="an-panel">
      <h2>Build</h2>
      {level <= 2 && (
        <div className="mini">
          Each row is a choice about the machine you are building: how much
          heat it can make, how much air it can move, and how much
          electricity it can be fed. Start from one of the ready-made
          builds below, then change one row at a time and watch what moves.
        </div>
      )}
      <div className="btnrow cfg-presets">
        {presets.map((p) => (
          <button key={p.id} title={p.blurb} onClick={() => onPreset(p)}>
            {p.name}
          </button>
        ))}
      </div>

      <Row label={pick(level, { std: "CPU sockets", novice: "How many processors" })}>
        <select value={config.sockets} onChange={(e) => set({ sockets: +e.target.value })}>
          <option value={1}>1</option>
          <option value={2}>2</option>
        </select>
      </Row>
      <Row label={pick(level, { std: "CPU TDP tier", novice: "Processor power class" })}>
        <select value={config.cpuTdpW} onChange={(e) => set({ cpuTdpW: +e.target.value })}>
          {CPU_TDP_TIERS.map((t) => (
            <option key={t} value={t}>{t} W</option>
          ))}
        </select>
      </Row>
      <Row label={pick(level, { std: "Heatsink", novice: "Processor cooler" })}>
        <select value={config.heatsink} onChange={(e) => set({ heatsink: e.target.value as ServerConfig["heatsink"] })}>
          <option value="standard">Standard</option>
          <option value="high-performance">{level <= 2 ? "High-performance (bigger, moves more heat)" : "High-performance"}</option>
        </select>
      </Row>
      <Row label={pick(level, { std: "Fan kit", novice: "Fan type" })}>
        <select value={config.fanKit} onChange={(e) => set({ fanKit: e.target.value as ServerConfig["fanKit"] })}>
          <option value="standard">Standard</option>
          <option value="gold">{level <= 2 ? "High-performance (Gold — stronger fans)" : "High-performance (Gold)"}</option>
        </select>
      </Row>
      <Row label={pick(level, { std: "DIMMs", novice: "Memory sticks" })}>
        <select value={config.dimms} onChange={(e) => set({ dimms: +e.target.value })}>
          {DIMM_COUNTS.map((d) => (
            <option key={d} value={d}>{level <= 2 ? `${d} sticks` : `${d}× DDR5`}</option>
          ))}
        </select>
      </Row>
      <Row label={pick(level, { std: "Front bay", novice: "Disks at the front" })}>
        <select value={config.chassis} onChange={(e) => set({ chassis: e.target.value as ServerConfig["chassis"] })}>
          <option value="12x3.5">{level <= 2 ? "12 large spinning disks" : "12× 3.5″ HDD"}</option>
          <option value="24x2.5">{level <= 2 ? "24 small flash disks" : "24× 2.5″ SSD"}</option>
          <option value="16xE3.S">{level <= 2 ? "16 fast flash disks (E3.S NVMe)" : "16× E3.S NVMe"}</option>
        </select>
      </Row>
      <Row label={`${pick(level, { std: "Drives", novice: "Disks fitted" })} (${config.drives})`}>
        <input
          type="range" min={0} max={MAX_DRIVES[config.chassis]}
          value={config.drives}
          onChange={(e) => set({ drives: +e.target.value })}
        />
      </Row>
      <Row label={pick(level, { std: "Double-wide GPUs", novice: "Large graphics cards" })}>
        <select value={config.gpusDoubleWide} onChange={(e) => set({ gpusDoubleWide: +e.target.value })}>
          {[0, 1, 2].map((n) => <option key={n} value={n}>{n}× 300 W</option>)}
        </select>
      </Row>
      <Row label={pick(level, { std: "Single-wide accels", novice: "Small add-in accelerator cards" })}>
        <select value={config.accelsSingleWide} onChange={(e) => set({ accelsSingleWide: +e.target.value })}>
          {[0, 1, 2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}× 75 W</option>)}
        </select>
      </Row>
      <Row label={`${pick(level, { std: "I/O cards", novice: "Network and other cards" })} (${config.ioCardW} W)`}>
        <input
          type="range" min={0} max={100} step={5}
          value={config.ioCardW}
          onChange={(e) => set({ ioCardW: +e.target.value })}
        />
      </Row>
      <Row label={pick(level, { std: "PSUs", novice: "Power supplies" })}>
        <select
          value={`${config.psuCount}/${config.redundancy}`}
          onChange={(e) => {
            const [count, red] = e.target.value.split("/");
            set({ psuCount: +count, redundancy: red as ServerConfig["redundancy"] });
          }}
        >
          <option value="1/1+0">{level <= 2 ? "One power supply — no spare" : "1 (no redundancy)"}</option>
          <option value="2/1+1">{level <= 2 ? "Two power supplies, either one can run the server alone" : "2 (1+1 redundant)"}</option>
          <option value="2/1+0">{level <= 2 ? "Two power supplies sharing the load, with no spare capacity" : "2 (combined, 2+0)"}</option>
        </select>
      </Row>
      <Row label={pick(level, { std: "PSU capacity", novice: "How much each power supply can deliver" })}>
        <select value={config.psuCapacityW} onChange={(e) => set({ psuCapacityW: +e.target.value })}>
          {PSU_CAPACITIES.map((c) => <option key={c} value={c}>{c} W</option>)}
        </select>
      </Row>

      <h2 style={{ marginTop: 12 }}>Configuration rules</h2>
      {problems.length === 0 && (
        <div className="mini rule-ok">✓ This build passes every rule.</div>
      )}
      {problems.map((v) => (
        <div key={v.ruleId} className={`mini rule-${v.level}`} title={v.source}>
          {v.level === "error" ? "✕ " : "△ "}
          {v.message}
        </div>
      ))}
    </div>
  );
}
