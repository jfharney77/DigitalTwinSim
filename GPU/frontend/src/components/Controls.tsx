import type { DType, Execution, GpuProfile, WorkloadKind } from "../types";
import { totalCores } from "../types";
import { InfoDot } from "./InfoDot";

const DTYPES: DType[] = ["fp32", "fp16", "bf16", "int8", "fp8", "fp4"];

export function Controls({
  profiles,
  profileName,
  onProfile,
  kind,
  steps,
  onKind,
  onSteps,
  n,
  m,
  kDim,
  kvLen,
  prefill,
  onKvLen,
  onPrefill,
  tileSize,
  dtype,
  execution,
  onExecution,
  gpus,
  onGpus,
  doubleBuffer,
  blockSize,
  speed,
  running,
  done,
  onN,
  onM,
  onKDim,
  onTileSize,
  onDtype,
  onDoubleBuffer,
  onBlockSize,
  onSpeed,
  onRun,
  onStep,
  onReset,
  phaseLabel,
}: {
  profiles: GpuProfile[];
  profileName: string;
  onProfile: (name: string) => void;
  kind: WorkloadKind;
  steps: number;
  onKind: (k: WorkloadKind) => void;
  onSteps: (s: number) => void;
  n: number;
  m: number; // 0 = "= N" (square; spec_22 sentinel)
  kDim: number; // 0 = "= N"
  kvLen: number; // spec_26: starting KV-cache length (llm_decode only)
  prefill: boolean; // spec_26: prompt-block regime instead of decode
  onKvLen: (v: number) => void;
  onPrefill: (v: boolean) => void;
  tileSize: number;
  dtype: DType;
  execution: Execution; // spec_23: "cuda" scalar path or "tensor" MMA path
  onExecution: (e: Execution) => void;
  gpus: number; // spec_27: 1, or 2 across the die-to-die link (matmul only)
  onGpus: (g: number) => void;
  doubleBuffer: boolean;
  blockSize: number; // spec_24: 0 = derived (one tile = one block)
  speed: number;
  running: boolean;
  done: boolean;
  onN: (n: number) => void;
  onM: (m: number) => void;
  onKDim: (k: number) => void;
  onTileSize: (t: number) => void;
  onDtype: (d: DType) => void;
  onDoubleBuffer: (v: boolean) => void;
  onBlockSize: (b: number) => void;
  onSpeed: (s: number) => void;
  onRun: () => void;
  onStep: () => void;
  onReset: () => void;
  phaseLabel: string;
}) {
  const selected = profiles.find((p) => p.name === profileName);
  // spec_23: the multipliers key set is the die's supported-dtype declaration.
  const tensorSpec = selected?.tensor ?? null;
  const tensorDtypes = tensorSpec ? Object.keys(tensorSpec.multipliers) : [];
  const dtypeDisabled = (d: DType): string | null => {
    if (execution !== "tensor") return null; // scalar path moves bytes only
    if (!tensorSpec) return `${selected?.name ?? "this die"} has no tensor units`;
    if (!tensorDtypes.includes(d)) {
      return d === "fp4"
        ? "fp4 is a property of the die — only B300-Blackwell-Ultra declares it"
        : `${selected?.name} has no tensor path for ${d} (supported: ${tensorDtypes.join(", ")})`;
    }
    return null;
  };
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
        {/* spec_30: cross-navigation — only when the atlas maps this profile
            to a floorplan. Unmapped profiles show nothing: no disabled
            button apologizing for the generic dies. */}
        {selected?.dieId && (
          <div className="mini">
            <a href={`#anatomy/${selected.dieId}`}>See this die's anatomy →</a>
          </div>
        )}
      </div>

      <div className="an-panel">
        <h2>Workload</h2>
        <label className="field">
          <span className="field-head">
            Kind
            <InfoDot title="Workload kind">
              <p>
                <strong>Matrix multiply</strong> is the single N×N·N×N matmul from
                spec_01–05.
              </p>
              <p>
                <strong>Neural-net training step</strong> (spec_06) runs one SGD step
                of a tiny 2-layer MLP: the forward pass is two matmuls, backprop is
                three more, and the weight update is a cheap elementwise op. Same
                silicon, same tiling and bandwidth model — only the operands change.
              </p>
              <p>
                Two things to watch: training costs about <strong>3×</strong> an
                inference pass, and every backprop op is just a{" "}
                <strong>transposed matmul</strong>. There is no separate "backprop
                circuit".
              </p>
              <p>
                <strong>LLM token decode</strong> (spec_26) runs one token step
                of a toy transformer block. The interesting part is the{" "}
                <strong>KV cache</strong>: every new token re-reads it in full,
                so as context grows the bytes grow and the arithmetic barely
                does — the roofline dot slides left into the memory-bound
                regime.
              </p>
            </InfoDot>
          </span>
          <select
            value={kind}
            onChange={(e) => onKind(e.target.value as WorkloadKind)}
          >
            <option value="matmul">Matrix multiply</option>
            <option value="mlp_step">Neural-net training step</option>
            <option value="llm_decode">LLM token decode</option>
          </select>
        </label>
        {kind === "mlp_step" && (
          <>
            <label className="field" style={{ marginTop: 10 }}>
              <span className="field-head">
                Training steps
                <InfoDot title="Training steps">
                  <p>
                    How many SGD steps to run back-to-back. Each step repeats the
                    same 8-op pipeline with the <strong>updated weights</strong>, so
                    the loss counter falls step over step — the network is learning
                    with arithmetic you can watch.
                  </p>
                </InfoDot>
              </span>
              <input
                type="range"
                min={1}
                max={10}
                value={steps}
                onChange={(e) => onSteps(Number(e.target.value))}
              />
            </label>
            <div className="mini">
              {steps === 1 ? "one SGD step" : `${steps} SGD steps · loss falls as weights update`}
            </div>
          </>
        )}
        {kind === "llm_decode" && (
          <>
            <label className="field" style={{ marginTop: 10 }}>
              <span className="field-head">
                {prefill ? "Prompt blocks" : "Tokens to generate"}
                <InfoDot title="Tokens">
                  <p>
                    How many decode steps to run back-to-back. The KV cache
                    grows by one row per token, so <strong>later tokens
                    genuinely cost more</strong> than earlier ones — watch the
                    op strip pick up extra cache-block matmuls.
                  </p>
                </InfoDot>
              </span>
              <input
                type="range"
                min={1}
                max={10}
                value={steps}
                onChange={(e) => onSteps(Number(e.target.value))}
              />
            </label>
            <label className="field" style={{ marginTop: 10 }}>
              <span className="field-head">
                KV cache length
                <InfoDot title="KV cache length">
                  <p>
                    The pile of past <strong>keys and values</strong> every new
                    token must re-read in full. More context = more bytes per
                    token, while the useful arithmetic barely grows.
                  </p>
                  <p>
                    That is the whole demo: as the slider grows, arithmetic
                    intensity falls and the regime badge flips from{" "}
                    <strong>compute-bound</strong> to{" "}
                    <strong>memory-bound</strong>. Nothing about the silicon
                    changed — the workload's <em>shape</em> did. This is why
                    decode speed is quoted in GB/s, not TFLOPs.
                  </p>
                </InfoDot>
              </span>
              <input
                type="range"
                min={8}
                max={64}
                value={kvLen}
                onChange={(e) => onKvLen(Number(e.target.value))}
              />
            </label>
            <div className="mini">
              {kvLen} cached tokens · {Math.ceil(kvLen / n)}×{" "}
              {n}-row cache block{Math.ceil(kvLen / n) > 1 ? "s" : ""} re-read
              per token
            </div>
            <div className="field-head" style={{ marginTop: 10 }}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={prefill}
                  onChange={(e) => onPrefill(e.target.checked)}
                />
                Prefill (whole prompt block at once)
              </label>
              <InfoDot title="Prefill vs decode">
                <p>
                  <strong>Prefill</strong> runs the same op list for a whole
                  N-token prompt block at once, so the attention matmuls are
                  ordinary square matmuls with <strong>full operand
                  reuse</strong> — compute-bound at any cache length.
                </p>
                <p>
                  <strong>Decode</strong> produces one token per stream and
                  re-reads the whole cache to do it. Batch of tokens vs one
                  token: two regimes from one switch. The Dell Pro Max Plus
                  twin teaches the same split from the device side.
                </p>
              </InfoDot>
            </div>
          </>
        )}
        <label className="field" style={{ marginTop: 10 }}>
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
          {(m || n)}×{(kDim || n)} · {(kDim || n)}×{n} → {(m || n)}×{n}
        </div>
        {kind === "matmul" && (
          <>
            <div className="field-head" style={{ marginTop: 10 }}>
              <label className="check">
                <input
                  type="checkbox"
                  checked={m !== 0 || kDim !== 0}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onM(n);
                      onKDim(n);
                    } else {
                      onM(0);
                      onKDim(0);
                    }
                  }}
                />
                Rectangular (M×K×N)
              </label>
              <InfoDot title="Rectangular matmul (M, K, N)">
                <p>
                  Real matmuls are rarely square. <strong>M</strong> (rows of A
                  and C) and <strong>N</strong> (columns of B and C) size the
                  output — how many independent cells there are to spread across
                  the lanes. <strong>K</strong> is the shared dimension: how
                  deep each cell's dot-product accumulation runs. K never
                  appears in C's shape at all.
                </p>
                <p>
                  Shrinking K makes each cell cheaper; shrinking M or N makes
                  fewer cells. Watch the roofline: a tall-skinny shape (long K,
                  small output) has lower arithmetic intensity than a short-fat
                  one at the same total MACs.
                </p>
                <p>Off = square: M and K snap back to "= N".</p>
              </InfoDot>
            </div>
            {(m !== 0 || kDim !== 0) && (
              <>
                <label className="field" style={{ marginTop: 10 }}>
                  <span className="field-head">Rows M (A and C)</span>
                  <input
                    type="range"
                    min={2}
                    max={8}
                    value={m || n}
                    onChange={(e) => onM(Number(e.target.value))}
                  />
                </label>
                <label className="field" style={{ marginTop: 10 }}>
                  <span className="field-head">Depth K (shared dim)</span>
                  <input
                    type="range"
                    min={2}
                    max={8}
                    value={kDim || n}
                    onChange={(e) => onKDim(Number(e.target.value))}
                  />
                </label>
                <div className="mini">
                  A is {(m || n)}×{(kDim || n)}, B is {(kDim || n)}×{n} — each C
                  cell sums {(kDim || n)} products
                </div>
              </>
            )}
          </>
        )}
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
            Block size (threads per block)
            <InfoDot title="Block size (threads per block)">
              <p>
                On real hardware you launch a grid of <strong>thread blocks</strong>, and
                each block claims warp slots on one SM until it finishes. Block size is
                a <strong>launch decision</strong>, made before the first instruction runs.
              </p>
              <p>
                It sets <strong>occupancy</strong> (see the Counters read-out): an SM can
                hold only so many resident threads <em>and</em> so many resident blocks —
                whichever budget runs out first wins. Tiny blocks waste the thread budget
                on the block ceiling; huge blocks leave slots stranded.
              </p>
              <p>
                <strong>Derived</strong> keeps today's implicit rule — one output tile is
                one block. An explicit size feeds the occupancy read-out only; the
                animation's cell-to-lane mapping is deliberately untouched.
              </p>
            </InfoDot>
          </span>
          <select
            value={blockSize}
            onChange={(e) => onBlockSize(Number(e.target.value))}
          >
            <option value={0}>Derived (one tile = one block)</option>
            {[32, 64, 128, 256, 512, 1024].map((b) => (
              <option key={b} value={b}>
                {b} threads
              </option>
            ))}
          </select>
        </label>
        <div className="mini">
          {blockSize === 0
            ? "auto — the tile's cells form the block"
            : `each block claims ${Math.ceil(
                blockSize / (selected?.warpSize ?? 32),
              )} warp slot${blockSize > (selected?.warpSize ?? 32) ? "s" : ""} on one SM`}
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
            {DTYPES.map((d) => {
              const why = dtypeDisabled(d);
              return (
                <option key={d} value={d} disabled={why != null} title={why ?? undefined}>
                  {d}
                  {why != null ? " — no tensor path" : ""}
                </option>
              );
            })}
          </select>
        </label>
        <div className="mini">
          fewer bytes per element → less data to move from HBM
        </div>
        <label className="field" style={{ marginTop: 10 }}>
          <span className="field-head">
            Execution
            <InfoDot title="Execution: CUDA cores vs tensor cores">
              <p>
                <strong>CUDA cores</strong> run the matmul the scalar way: one
                k-rank per step, one MAC per lane — every trace this app has
                shown since spec_01.
              </p>
              <p>
                <strong>Tensor cores</strong> are matrix-multiply-accumulate
                (MMA) units: one instruction consumes a whole 16-rank chunk of
                the dot product, at multipliers that grow as the dtype shrinks.
                Watch the die — the owning SM flashes as <em>one block</em>,
                because the SM's tensor units issue the MMA, not 128 scalar
                lanes.
              </p>
              <p>
                The roofline lesson: tensor cores multiply MACs/cycle,{" "}
                <strong>not</strong> bytes/cycle, so the ridge point moves
                right and the memory wall gets <em>worse</em>. Which dtypes are
                offered is a property of the die — fp4 exists only on the
                B300.
              </p>
              <p>
                Honesty ceiling: multipliers are teaching constants whose{" "}
                <em>ratios</em> track published dense-throughput tables; no
                sparsity, no clock effects, no per-unit scheduling, and low-
                precision numerics are not modeled — dtype affects bytes and
                rate only.
              </p>
            </InfoDot>
          </span>
          <select
            value={execution}
            onChange={(e) => onExecution(e.target.value as Execution)}
          >
            <option value="cuda">CUDA cores (scalar)</option>
            <option
              value="tensor"
              disabled={!tensorSpec}
              title={
                tensorSpec
                  ? undefined
                  : `${selected?.name ?? "this die"} has no tensor units — the generic teaching dies stay scalar`
              }
            >
              Tensor cores (MMA)
              {tensorSpec ? "" : " — not on this die"}
            </option>
          </select>
        </label>
        <div className="mini">
          {execution === "tensor" && tensorSpec
            ? `×${tensorSpec.multipliers[dtype] ?? "?"} MACs/cycle at ${dtype} · ${tensorSpec.mmaK} ranks per MMA step`
            : "scalar path — one k-rank per step, one MAC per lane"}
        </div>
        {kind === "matmul" && (
          <>
            <label className="field" style={{ marginTop: 10 }}>
              <span className="field-head">
                GPUs (NVLink scale-up)
                <InfoDot title="Scale up to 2 GPUs">
                  <p>
                    Real training matmuls stopped fitting one die years ago.
                    The fix is the least glamorous move in parallel computing:
                    <strong> split the output</strong> — die 0 takes C's top
                    rows, die 1 the rest — run the same kernel on each, then{" "}
                    <strong>pay to exchange results over the link</strong>.
                  </p>
                  <p>
                    Compute halves, but communication is <em>added, not
                    hidden</em>: watch the trailing exchange phase. Small N
                    barely speeds up (the exchange dominates); large N
                    approaches — never reaches — <strong>2×</strong>.
                  </p>
                  <p>
                    The link is a <strong>feature of the die</strong>, not the
                    workload: H100 has NVLink 4, B300 has NVLink 5 at twice
                    the rate, and consumer dies have none — they scale out
                    over PCIe or not at all. The refusal is itself the lesson.
                  </p>
                </InfoDot>
              </span>
              <select
                value={gpus}
                onChange={(e) => onGpus(Number(e.target.value))}
              >
                <option value={1}>1 GPU</option>
                <option
                  value={2}
                  disabled={!selected?.link}
                  title={
                    selected?.link
                      ? undefined
                      : `${selected?.name ?? "this die"} has no die-to-die link — consumer dies scale out over PCIe or not at all`
                  }
                >
                  2 GPUs
                  {selected?.link
                    ? ` over ${selected.link.label}`
                    : " — no link on this die"}
                </option>
              </select>
            </label>
            <div className="mini">
              {gpus === 2 && selected?.link
                ? `split C's rows across two dies, all-gather over ${selected.link.label} (${selected.link.bytesPerCycle} B/cycle — far below HBM on purpose)`
                : selected?.link
                  ? `this die can scale up over ${selected.link.label}`
                  : "no link — asking this die to scale up is refused"}
            </div>
          </>
        )}
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
