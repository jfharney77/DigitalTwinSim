"""Data models for the GPU Matmul Visualizer.

These mirror the TypeScript interfaces in initial_spec.md (§3). Field names are
snake_case in Python but serialize to camelCase JSON so the React frontend can
consume them directly (macDone, macTotal, coreState, ...).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.alias_generators import to_camel

Phase = Literal["idle", "load", "compute", "writeback", "exchange", "done"]  # spec_27
CoreState = Literal["idle", "loading", "computing", "wrote", "mma"]  # spec_23
DType = Literal["fp32", "fp16", "bf16", "int8", "fp8", "fp4"]  # spec_04 + 23
Regime = Literal["memory", "compute"]
Limiter = Literal["threads", "blocks", "none"]  # spec_24: which budget ran out
Execution = Literal["cuda", "tensor"]  # spec_23: an enum, not a bool

# Bits per element by dtype (spec_23 widened spec_04's DTYPE_BYTES to bits —
# fp4 is half a byte, which integer bytes cannot express). Byte counts are
# computed as ceil(cells * bits / 8), which is exactly cells * bytes for every
# byte-aligned dtype, so all pre-fp4 arithmetic is unchanged.
DTYPE_BITS: dict[str, int] = {
    "fp32": 32,
    "fp16": 16,
    "bf16": 16,
    "int8": 8,
    "fp8": 8,
    "fp4": 4,
}


def dtype_bytes(dtype: str) -> float:
    """Bytes per element as a float (fp4 = 0.5). For byte accounting prefer
    ceil(cells * DTYPE_BITS[dtype] / 8), which stays integral."""
    return DTYPE_BITS[dtype] / 8


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SMGrid(CamelModel):
    rows: int = Field(ge=1)
    cols: int = Field(ge=1)


class Memory(CamelModel):
    stacks: int = Field(ge=1)
    label: str = "HBM"


class Bandwidth(CamelModel):
    """Illustrative (NOT real) rates for the memory/compute model (spec_04)."""

    bytes_per_cycle: int = 8  # HBM throughput
    macs_per_cycle: int = 4  # compute throughput


class Power(CamelModel):
    """Illustrative (NOT measured) power constants for the energy model
    (spec_25). Absolute watts are teaching estimates; only the *ratios*
    across the fleet are honest — each real profile's derived envelope
    tracks the part's public TDP/TGP figure (see profiles.py comments).
    Defaults suit the generic teaching dies, exactly as Bandwidth's do."""

    idle_w: float = Field(default=10.0, gt=0)  # floor the die burns doing nothing
    lane_w: float = Field(default=0.5, ge=0)  # added watts per lane doing math
    byte_w: float = Field(default=2.0, ge=0)  # added watts per byte/cycle of
    # foreground HBM traffic (loads and writebacks)


def state_power_watts(
    power: Power,
    bytes_per_cycle: int,
    *,
    active_cores: int,
    stalled: bool,
    mem_active: bool,
    prefetching: bool,
) -> float:
    """spec_25: watts for one SimState, purely from fields the state already
    carries plus the profile's constants. Deterministic; no clocks.

    - The idle floor always burns.
    - Lanes burn lane_w each only while actually doing math: a stalled LOAD's
      waiting lanes are parked, so a stall reads idle + memory watts while
      macDone stands still — the wasteful regime as a number.
    - Foreground memory traffic (loads, writebacks) burns byte_w per byte the
      memory system moves per modeled cycle. Background prefetch (spec_05)
      deliberately adds nothing: charging full memory watts per overlapped
      compute state would bill by duration, not by bytes, and could make
      double-buffering read as *costing* energy. The acknowledged undercount
      (hidden loads' bytes ride free) errs in the direction of the true
      lesson: reuse and overlap never cost more joules.
    """
    watts = power.idle_w
    if not stalled:
        watts += power.lane_w * active_cores
    if mem_active and not prefetching:
        watts += power.byte_w * bytes_per_cycle
    return watts


class Link(CamelModel):
    """Illustrative die-to-die link (spec_27). Absent => the die cannot scale
    up: gpus=2 requests 422 in main.py (consumer dies scale out over PCIe or
    not at all — the refusal is the lesson). Rates are illustrative like
    Bandwidth's, but the *ratios* are honest: NVLink 5 = 2x NVLink 4. The
    link rate is deliberately far below bandwidth.bytes_per_cycle — HBM is
    on package, the link crosses the board; that gap IS the cost model."""

    label: str
    bytes_per_cycle: int = Field(ge=1)


class TensorSpec(CamelModel):
    """Illustrative MMA capability (spec_23). Absent => no tensor path.

    The multipliers KEY SET is the supported-dtype declaration: a dtype absent
    from the dict is unsupported on this die (main.py 422s the pair before the
    engine ever sees it). units_per_sm is drawn, not simulated per-unit."""

    # to_camel would yield "unitsPerSm"; the spec/TS want "unitsPerSM"
    # (same gotcha as cores_per_sm).
    units_per_sm: int = Field(ge=1, alias="unitsPerSM")
    mma_m: int = 16  # tile shape one MMA step consumes (mmaM/mmaN/mmaK)
    mma_n: int = 16
    mma_k: int = 16
    # dtype -> throughput multiplier over bandwidth.macs_per_cycle.
    multipliers: dict[DType, float]


class GpuProfile(CamelModel):
    """Describes the die. Everything structural derives from this (spec §3)."""

    name: str
    sm: SMGrid
    # to_camel would yield "coresPerSm"; spec (and the TS types) want "coresPerSM".
    cores_per_sm: SMGrid = Field(alias="coresPerSM")
    memory: Memory
    has_l2_bus: bool = True
    bandwidth: Bandwidth = Field(default_factory=Bandwidth)  # spec_04
    # Per-SM residency limits (spec_24). Ada defaults so every existing profile
    # (and every persisted request) stays valid untouched. Plain to_camel gives
    # maxThreadsPerSm / maxBlocksPerSm / warpSize — the same casing DeviceInfo
    # in live.py already serializes, so no PerSM-style alias here.
    max_threads_per_sm: int = Field(default=1536, ge=1)
    max_blocks_per_sm: int = Field(default=24, ge=1)
    warp_size: int = Field(default=32, ge=1)
    # Tensor-core capability (spec_23). None = scalar-only die: tensor-mode
    # requests 422 in main.py, and the engine's fallback is the scalar path.
    tensor: TensorSpec | None = None
    # Cross-navigation (spec_30): the anatomy.py DieAnatomy id this profile
    # draws, or None when the museum has no matching floorplan. Plain to_camel
    # gives "dieId" — no alias gotcha. Nulls are honest and allowed in both
    # directions; the reverse map is derived in profiles.py, never authored.
    die_id: str | None = None
    # Power constants (spec_25). Default keeps every older profile and
    # persisted request valid untouched, exactly as Bandwidth did in spec_04.
    power: Power = Field(default_factory=Power)
    # Die-to-die link (spec_27). None = no scale-up path on this die.
    link: Link | None = None

    def envelope_watts(self) -> float:
        """spec_25 derived ceiling: every lane computing while foreground
        memory streams at full rate. No state may exceed it."""
        return (
            self.power.idle_w
            + self.power.lane_w * self.total_cores()
            + self.power.byte_w * self.bandwidth.bytes_per_cycle
        )

    def total_cores(self) -> int:
        return (
            self.sm.rows
            * self.sm.cols
            * self.cores_per_sm.rows
            * self.cores_per_sm.cols
        )


class Workload(CamelModel):
    kind: Literal["matmul", "mlp_step", "llm_decode"] = "matmul"
    n: int = Field(ge=2, le=64, alias="N")
    dtype: DType = "fp32"
    seed: int = 0  # deterministic operand pattern (spec_02)
    tile_size: int = 0  # T; 0 means whole matrix / no tiling (spec_03)
    double_buffer: bool = False  # overlap next-tile load with compute (spec_05)
    steps: int = Field(default=1, ge=1, le=10)  # SGD steps for mlp_step (spec_06)
    # Rectangular matmul (spec_22): A is M×K, B is K×N, C is M×N. 0 = "= n"
    # (the sentinel), so square stays the default and every old request is
    # untouched. Explicit alias="M"/"K": to_camel would emit lowercase m/k.
    # Python field is k_dim (not k) to avoid grep-shadowing SimState.k.
    m: int = Field(default=0, alias="M")
    k_dim: int = Field(default=0, alias="K")
    # Threads per thread-block (spec_24). 0 = "derived": one output tile is one
    # block (today's implicit rule, T² cells clamped to 1024) — the default
    # reproduces existing traces exactly. A nonzero value feeds the occupancy
    # read-out only; the cell→lane mapping and trace shape are untouched.
    block_size: int = Field(default=0, ge=0, le=1024)
    # LLM decode (spec_26): starting KV-cache length (to_camel gives kvLen
    # cleanly) and the prefill contrast switch. Ignored by other kinds — both
    # carry harmless defaults, so old requests are untouched.
    kv_len: int = Field(default=8, ge=8, le=64)
    prefill: bool = False
    # Execution path (spec_23). "cuda" (the default) is the scalar path every
    # spec_01–22 trace used — byte-for-byte unchanged. "tensor" steps whole
    # mma_k-rank MMA chunks per state; mlp_step and llm_decode inherit it for
    # free because they chain engine.simulate().
    execution: Execution = "cuda"
    # NVLink scale-up (spec_27): run the matmul data-parallel across two dies
    # of the same profile, with an explicit trailing exchange phase. Default 1
    # keeps every existing trace byte-identical (the spec_05/spec_23 pattern).
    gpus: int = Field(default=1, ge=1, le=2)

    @field_validator("m", "k_dim")
    @classmethod
    def _dim_zero_or_in_range(cls, v: int) -> int:
        if v != 0 and not (2 <= v <= 64):
            raise ValueError("must be 0 (= n) or between 2 and 64")
        return v

    @model_validator(mode="after")
    def _mlp_stays_square(self) -> "Workload":
        # spec_22: mlp_step's five chained matmuls share one square shape.
        # Reject rectangular params loudly (422) rather than ignoring them.
        # spec_26: llm_decode chains square matmuls the same way, and caps N
        # at 8 (§5 — at N=8, kv_len=64 a token is already 22 matmuls).
        if self.kind in ("mlp_step", "llm_decode") and (self.m or self.k_dim):
            raise ValueError(
                f"{self.kind} is square-only: M and K must be 0 (or omitted)"
            )
        if self.kind == "llm_decode" and self.n > 8:
            raise ValueError("llm_decode caps N at 8 (spec_26 §5)")
        # spec_27: the spec models one matmul across two dies; the chained
        # workloads (mlp_step, llm_decode) would need an exchange per op —
        # a different lesson (pipeline/tensor parallelism, deferred in §4).
        # Refuse loudly rather than sharding only some of the chain.
        if self.kind in ("mlp_step", "llm_decode") and self.gpus > 1:
            raise ValueError(
                f"{self.kind} is single-GPU only: spec_27 scale-up applies to "
                "the plain matmul (sharding a chained workload is pipeline "
                "parallelism, deliberately out of scope)"
            )
        return self


class Occupancy(CamelModel):
    """Resident-warp budget for one launch config (spec_24). Fixed at launch —
    one block_size per run — so it rides on Summary, never SimState."""

    block_size: int  # effective threads per block (derived when workload says 0)
    warps_per_block: int  # warp-granular, like hardware
    blocks_resident: int  # min(block ceiling, thread ceiling)
    occupancy_pct: float  # claimed warp slots / slots the SM could hold
    limiter: Limiter  # which ceiling ran out first ("none" at exactly 100%)


class SimState(CamelModel):
    """Pure data emitted per step; the renderer consumes this (spec §3)."""

    cycle: int
    phase: Phase
    k: int
    mac_done: int
    mac_total: int
    mem_active: bool
    core_state: list[CoreState]
    active_cores: int
    utilization: float
    # Tiling context (spec_03); null outside a tile (idle/done) and k_tile is
    # null during writeback. Tile indices are in tile units (multiply by tile_size).
    tile_row: int | None = None
    tile_col: int | None = None
    k_tile: int | None = None
    # Bandwidth model (spec_04): cores waiting on HBM, and modeled cycles this
    # event costs (loads cost more than compute -> the UI dwells on them).
    stalled: bool = False
    cycle_cost: int = 1
    # Double-buffering (spec_05): the next tile is loading in the background while
    # these cores compute (overlap -> mem_active is also true here).
    prefetching: bool = False
    # MLP op context (spec_06); null for plain matmul workloads. op_index is
    # global across steps (step_index * ops_per_step + position).
    op_index: int | None = None
    op_count: int | None = None
    op_name: str | None = None
    step_index: int | None = None
    # Tensor-core mode (spec_23): this compute step is one MMA instruction —
    # the owning SM's lanes light as a block, not per-lane — and it consumed
    # ranks_per_step k-ranks at once (the final chunk may be partial).
    mma: bool = False
    ranks_per_step: int | None = None
    # Power model (spec_25): illustrative watts this state burns, derived by
    # state_power_watts() from the fields above at trace-build time. Energy
    # over the trace is Σ power_watts × cycle_cost (the Summary ledger).
    power_watts: float = 0.0
    # NVLink scale-up (spec_27): which die this state's core_state[] describes.
    # None for single-GPU traces and for the shared idle/exchange/done states —
    # one logical trace, interleaved per-die states (the wire stays lean).
    gpu: int | None = None


class SimulateRequest(CamelModel):
    profile: GpuProfile
    workload: Workload


class Summary(CamelModel):
    """Analytical roofline read-out for the whole workload (spec_04)."""

    bytes_moved: int
    load_cycles_total: int
    compute_cycles_total: int
    arithmetic_intensity: float  # MACs per byte moved
    ridge_point: float  # intensity where memory- and compute-bound balance
    regime: Regime
    # Scheduling cost estimates (spec_05): serial vs double-buffered.
    serial_cycles: int
    pipelined_cycles: int
    # spec_24: the launch's resident-warp budget — the other percentage,
    # deliberately next to the roofline so both read-outs ride one response.
    occupancy: Occupancy
    # Energy ledger (spec_25), stamped by engine.attach_energy() over the
    # built trace (analyze() alone is trace-free and leaves the zeros).
    # Units are frankly modeled: a "cycle" is spec_04's illustrative cycle,
    # so these are illustrative joules — the comparisons are the product.
    energy_joules: float = 0.0
    avg_power_watts: float = 0.0  # energy ÷ Σ cycle_cost
    joules_per_mac: float = 0.0  # energy ÷ macTotal — this sim's tokens/J
    # NVLink scale-up read-outs (spec_27). exchange_cycles is the all-gather's
    # modeled cost; scaleup_speedup = serial 1-GPU cycles ÷ (max(die0, die1) +
    # exchange) — always < 2, approaching 2 as N³ compute swamps N² exchange.
    # Both keep their neutral defaults when gpus=1.
    exchange_cycles: int = 0
    scaleup_speedup: float = 1.0


class MlpOp(CamelModel):
    """One op in the training-step pipeline (spec_06). Matmul ops carry their
    operand snapshots (display-rounded); pointwise ops carry none."""

    name: str
    kind: Literal["matmul", "pointwise"]
    a: list[list[float]] | None = None
    b: list[list[float]] | None = None
    a_label: str | None = None
    b_label: str | None = None
    c_label: str | None = None


class MlpInfo(CamelModel):
    """Training-step metadata riding in the simulate response (spec_06)."""

    ops: list[MlpOp]  # steps × ops_per_step, aligned with SimState.op_index
    ops_per_step: int
    loss: list[float]  # one per step
    eta: float


class LlmInfo(CamelModel):
    """LLM decode metadata riding in the simulate response (spec_26). Ops
    reuse the MlpOp wire shape so OpPipeline renders them unchanged."""

    ops: list[MlpOp]  # variable per token (6+2B matmuls + 5 pointwise)
    ops_per_token: list[int]  # op-strip boundaries; Σ == len(ops)
    kv_len: list[int]  # cache length S_t per token — grows by one row
    intensity: list[float]  # the number to watch, as loss was for spec_06
    softmax_row: list[float]  # final token's stream-0 attention weights
    prefill: bool


class SimulateResponse(CamelModel):
    profile: GpuProfile
    workload: Workload
    total_cores: int
    mac_total: int
    # Resolved dims (spec_22): the sentinel rule (0 = "= n") applied server-
    # side so the frontend never re-derives it. Square workloads echo n thrice.
    m: int
    k: int
    n: int
    tile_size: int  # effective T after clamping (spec_03)
    summary: Summary  # spec_04
    a: list[list[float]]  # operand A (spec_02; floats for mlp_step)
    b: list[list[float]]  # operand B (spec_02)
    trace: list[SimState]
    mlp: MlpInfo | None = None  # spec_06
    llm: LlmInfo | None = None  # spec_26
