import type { GpuProfile } from "../types";
import { totalCores } from "../types";

export function Controls({
  profiles,
  profileName,
  onProfile,
  n,
  tileSize,
  speed,
  running,
  done,
  onN,
  onTileSize,
  onSpeed,
  onRun,
  onStep,
  onReset,
  phaseLabel,
}: {
  profiles: GpuProfile[];
  profileName: string;
  onProfile: (name: string) => void;
  n: number;
  tileSize: number;
  speed: number;
  running: boolean;
  done: boolean;
  onN: (n: number) => void;
  onTileSize: (t: number) => void;
  onSpeed: (s: number) => void;
  onRun: () => void;
  onStep: () => void;
  onReset: () => void;
  phaseLabel: string;
}) {
  const selected = profiles.find((p) => p.name === profileName);
  return (
    <>
      <div>
        <h2>GPU</h2>
        <label className="field">
          Die profile
          <select value={profileName} onChange={(e) => onProfile(e.target.value)}>
            {profiles.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        {selected && (
          <div className="mini">
            {selected.sm.rows * selected.sm.cols} SMs ·{" "}
            {selected.coresPerSM.rows * selected.coresPerSM.cols} cores each ={" "}
            {totalCores(selected)} lanes
          </div>
        )}
      </div>

      <div>
        <h2>Workload</h2>
        <label className="field">
          Matrix size N (N×N · N×N)
          <input
            type="range"
            min={2}
            max={8}
            value={n}
            onChange={(e) => onN(Number(e.target.value))}
          />
        </label>
        <div className="mini">
          {n}×{n} · {n}×{n} → {n}×{n}
        </div>
        <label className="field" style={{ marginTop: 10 }}>
          Tile size T (shared-memory block)
          <input
            type="range"
            min={1}
            max={n}
            value={Math.min(tileSize || n, n)}
            onChange={(e) => onTileSize(Number(e.target.value))}
          />
        </label>
        <div className="mini">
          {tileSize >= n || tileSize <= 0
            ? `T=${n} — whole matrix, no tiling`
            : `T=${tileSize} — stream ${tileSize}×${tileSize} blocks through shared mem`}
        </div>
      </div>

      <div>
        <h2>Run</h2>
        <div className="btnrow">
          <button className="primary" onClick={onRun} disabled={running}>
            ▶ Run
          </button>
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
        <div className="phase">{done ? "✓ " : ""}{phaseLabel}</div>
      </div>
    </>
  );
}
