import type { DType, GpuProfile } from "../types";
import { totalCores } from "../types";
import { InfoDot } from "./InfoDot";

const DTYPES: DType[] = ["fp32", "fp16", "bf16", "int8"];

export function Controls({
  profiles,
  profileName,
  onProfile,
  n,
  tileSize,
  dtype,
  doubleBuffer,
  speed,
  running,
  done,
  onN,
  onTileSize,
  onDtype,
  onDoubleBuffer,
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
  dtype: DType;
  doubleBuffer: boolean;
  speed: number;
  running: boolean;
  done: boolean;
  onN: (n: number) => void;
  onTileSize: (t: number) => void;
  onDtype: (d: DType) => void;
  onDoubleBuffer: (v: boolean) => void;
  onSpeed: (s: number) => void;
  onRun: () => void;
  onStep: () => void;
  onReset: () => void;
  phaseLabel: string;
}) {
  const selected = profiles.find((p) => p.name === profileName);
  return (
    <>
      <div className="an-panel">
        <h2>GPU</h2>
        <label className="field">
          <span className="field-head">
            Die profile
            <InfoDot title="Die profile">
              <p>
                A GPU is one chip of silicon — the <strong>die</strong>. This picks which
                die you're simulating, and the panel on the left draws its floor plan.
              </p>
              <p>
                The hierarchy: thousands of tiny multiply-add units called{" "}
                <strong>lanes</strong> (CUDA cores) are bundled into{" "}
                <strong>SMs</strong> (Streaming Multiprocessors — a worker crew with its
                own scheduler and fast scratchpad), tiled across the die alongside{" "}
                <strong>HBM</strong> memory.
              </p>
              <p>
                <code>Generic-128</code> = 8 SMs × 16 lanes = 128 lanes;{" "}
                <code>Generic-512</code> = 16 SMs × 32 lanes = 512 lanes. Each output cell
                of the result matrix is assigned to a lane, and you watch them light up.
                Dies are pure data, so adding a new one is a config change, not code.
              </p>
            </InfoDot>
          </span>
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

      <div className="an-panel">
        <h2>Workload</h2>
        <label className="field">
          <span className="field-head">
            Matrix size N (N×N · N×N)
            <InfoDot title="Matrix size N">
              <p>
                The dimension of the square matrices being multiplied: an N×N matrix times
                an N×N matrix, producing an N×N result.
              </p>
              <p>
                Bigger N means more work — the total multiply-adds grow as{" "}
                <strong>N³</strong> (each of the N² output cells sums N products). It also
                means more output cells to spread across the lanes, so a larger N keeps
                more of the die busy.
              </p>
              <p>
                Kept small (2–8) on purpose: this is a mental-model tool, not GPU-scale.
                Changing N re-runs the simulation from scratch.
              </p>
            </InfoDot>
          </span>
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
          <span className="field-head">
            Tile size T (shared-memory block)
            <InfoDot title="Tile size T">
              <p>
                A whole matrix rarely fits in an SM's small, fast scratchpad (shared
                memory). So the work is broken into <strong>tiles</strong>: T×T blocks are
                streamed in from HBM, multiplied, and the next block is streamed in.
              </p>
              <p>
                Smaller T = smaller blocks, so more separate load→compute→writeback trips
                but a lighter memory footprint per trip. <code>T=N</code> means one tile =
                the whole matrix (no tiling).
              </p>
              <p>
                Tiling is the single most important trick for making matmul fast on real
                hardware — it maximizes reuse of data already sitting in fast memory.
              </p>
            </InfoDot>
          </span>
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
        <label className="field" style={{ marginTop: 10 }}>
          <span className="field-head">
            Precision (dtype)
            <InfoDot title="Precision (dtype)">
              <p>
                How many bits store each number — same idea as <code>int8</code> vs{" "}
                <code>float</code> vs <code>double</code> in normal code. Fewer bits =
                smaller footprint, less accuracy.
              </p>
              <p>
                <code>fp32</code> = 4 bytes (most accurate), <code>fp16</code> /{" "}
                <code>bf16</code> = 2 bytes (bf16 trades accuracy for wider range),{" "}
                <code>int8</code> = 1 byte (quantized, tiniest).
              </p>
              <p>
                Here it feeds the <strong>bandwidth model</strong>: a smaller dtype means
                fewer bytes to haul from HBM, so loads are cheaper and lanes stall less.
                This is why AI moved to fp16/bf16/int8 — not to save space, but to feed the
                lanes faster. It changes data <em>moved</em>, not the number of multiplies.
              </p>
            </InfoDot>
          </span>
          <select value={dtype} onChange={(e) => onDtype(e.target.value as DType)}>
            {DTYPES.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <div className="mini">
          fewer bytes per element → less data to move from HBM
        </div>
        <div className="field-head" style={{ marginTop: 10 }}>
          <label className="check">
            <input
              type="checkbox"
              checked={doubleBuffer}
              onChange={(e) => onDoubleBuffer(e.target.checked)}
            />
            Double-buffering (overlap load + compute)
          </label>
          <InfoDot title="Double-buffering">
            <p>
              Without it, a lane sits idle during each tile load — compute and memory take
              turns, so the expensive silicon waits on HBM.
            </p>
            <p>
              With it, the SM keeps <strong>two buffers</strong>: while the lanes compute on
              tile <em>k</em>, the hardware is already <strong>prefetching</strong> tile{" "}
              <em>k+1</em> in the background. The next tile is ready the moment compute
              finishes, so the load latency is <strong>hidden</strong> behind useful work.
            </p>
            <p>
              Watch the phase readout: with it on, "prefetching next tile" appears during
              compute and the stall time between tiles shrinks. This is a classic
              latency-hiding technique — trading a little extra memory for far better lane
              utilization.
            </p>
          </InfoDot>
        </div>
        <div className="mini">
          {doubleBuffer
            ? "prefetch next tile while computing — hides load stalls"
            : "off — cores stall on every load"}
        </div>
      </div>

      <div className="an-panel">
        <span className="field-head">
          <h2 className="with-info">Run</h2>
          <InfoDot title="Run controls">
            <p>
              <strong>Run</strong> plays the trace on a clock owned entirely by the UI — the
              simulation itself is pure data with no notion of time.
            </p>
            <p>
              <strong>Step</strong> advances exactly one state so you can inspect a single
              phase transition; <strong>Reset</strong> returns to the start.
            </p>
            <p>
              <strong>Speed</strong> retunes the playback interval live (it does not change
              the simulation, only how fast you watch it). Slower is better for following
              the load → compute → writeback phases per tile.
            </p>
          </InfoDot>
        </span>
        <div className="btnrow">
          <button className="primary" onClick={onRun} disabled={running}>
            Run
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
