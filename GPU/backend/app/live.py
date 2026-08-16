"""Live CUDA co-browsing (spec_08, extended by specs 10/12/14/15/16/17) —
the PURE layer.

This module is the live mode's counterpart to ``engine.py``: models for the
probe wire format plus a pure fold that turns a stamped event stream into
``LiveState`` frames. Nothing here touches the clock, the filesystem, or the
network — the impure edge (session JSONL files, SSE broadcast, timestamping,
the measurement store) lives in ``live_store.py``, and ``tests/test_live.py``
AST-checks this file to keep it that way. A recorded session replays through
``replay()`` exactly like a simulator trace: pure data in, pure data out.

Event sources feeding the same fold:
- ``device_info`` (spec_12) — what GPU this session runs on; sizes the per-SM
  picture. Without one, the spec_07 default (24 SMs) applies.
- ``kernel_launch`` — from ``twinprobe.cuh`` (Tier A) or the CUPTI injector
  (Tier C, spec_17; ``source: "cupti"``, timing-only): per-block records of
  the SM id the hardware chose plus clock64 timing. May be ``sampled``
  (spec_16) — a declared 1-in-``sampleStride`` subset, scaled to estimates.
- ``kernel_progress`` (spec_14) — incremental per-SM counts streamed while a
  long kernel runs; the closing ``kernel_launch`` is always authoritative.
- ``gpu_sample`` — whole-GPU telemetry from ``twin-sampler`` (Tier B).
- ``measurement`` (spec_15) — a calibration number (e.g. measured stream
  GB/s). Not a frame: the store persists it, the fold never sees it.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .models import CamelModel
from .profiles import RTX_4060_LAPTOP

# The default die when no device_info has arrived (spec_07's machine). If the
# profile's SM count ever drifts from the hardware's 24, test_profiles.py
# fails first.
DEFAULT_SM_COUNT: int = RTX_4060_LAPTOP.sm.rows * RTX_4060_LAPTOP.sm.cols
SM_COUNT = DEFAULT_SM_COUNT  # legacy alias used by tests/tools

# Hard ceiling on any smid the wire will carry; the *real* bound is the
# session device's SM count, enforced in the fold where the device is known.
MAX_SMID = 1024

# Gantt spans per kernel frame (spec_10): enough to draw, bounded on the wire.
MAX_SPANS = 2048

Dim3 = tuple[
    Annotated[int, Field(ge=1)],
    Annotated[int, Field(ge=1)],
    Annotated[int, Field(ge=1)],
]


class DeviceInfo(CamelModel):
    """The GPU a session runs on (spec_12); from cudaGetDeviceProperties."""

    name: str
    sm_count: int = Field(ge=1, le=MAX_SMID)
    max_threads_per_sm: int | None = Field(default=None, ge=1)
    warp_size: int | None = Field(default=None, ge=1)
    vram_mb: float | None = Field(default=None, ge=0)


class DeviceInfoEvent(CamelModel):
    type: Literal["device_info"] = "device_info"
    name: str
    sm_count: int = Field(ge=1, le=MAX_SMID)
    max_threads_per_sm: int | None = Field(default=None, ge=1)
    warp_size: int | None = Field(default=None, ge=1)
    vram_mb: float | None = Field(default=None, ge=0)
    # spec_28: the remap marker. Set only by remap.py on the read path; names
    # the die the stream was actually recorded on. The fold turns it into
    # placement="modeled" frames, and ingest REJECTS any event carrying it —
    # modeled data must never enter a session recording.
    modeled_from: str | None = None

    def device(self) -> DeviceInfo:
        return DeviceInfo(
            name=self.name,
            sm_count=self.sm_count,
            max_threads_per_sm=self.max_threads_per_sm,
            warp_size=self.warp_size,
            vram_mb=self.vram_mb,
        )


class BlockRecord(CamelModel):
    """One thread block's footprint: which SM ran it, and when (clock64)."""

    smid: int = Field(ge=0, lt=MAX_SMID)
    start: int = 0
    end: int = 0


class KernelLaunchEvent(CamelModel):
    type: Literal["kernel_launch"] = "kernel_launch"
    kernel: str
    grid: Dim3
    block: Dim3
    blocks: list[BlockRecord] = Field(default_factory=list)
    # An hour-plus "kernel" is a corrupt event, not a measurement (spec_19 #6).
    elapsed_ms: float | None = Field(default=None, ge=0, le=3_600_000)
    occupancy_pct: float | None = Field(default=None, ge=0, le=100)
    # spec_16: a declared 1-in-sampleStride subset (first blocks + stride).
    sampled: bool = False
    sample_stride: int = Field(default=1, ge=1)
    # spec_17: cupti events carry timing but no placement records.
    source: Literal["probe", "cupti"] = "probe"
    occupancy_source: Literal["theoretical", "measured"] = "theoretical"

    def grid_blocks(self) -> int:
        return self.grid[0] * self.grid[1] * self.grid[2]

    def records_dropped(self) -> int:
        """Blocks the grid ran but the probe failed to report. Zero for
        declared sampling (a contract, not an accident) and for cupti events
        (timing-only by design) — the UI distinguishes those by their own
        flags instead of a false "partial" alarm."""
        if self.sampled or self.source == "cupti":
            return 0
        return self.grid_blocks() - len(self.blocks)

    @model_validator(mode="after")
    def _no_excess_records(self) -> "KernelLaunchEvent":
        if len(self.blocks) > self.grid_blocks():
            raise ValueError(
                f"{len(self.blocks)} block records for a "
                f"{self.grid_blocks()}-block grid"
            )
        return self


class ProgressCount(CamelModel):
    """Per-SM tally streamed mid-kernel (spec_14)."""

    smid: int = Field(ge=0, lt=MAX_SMID)
    started: int = Field(ge=0)
    ended: int = Field(ge=0)

    @model_validator(mode="after")
    def _ended_le_started(self) -> "ProgressCount":
        if self.ended > self.started:
            raise ValueError("ended blocks exceed started blocks")
        return self


class KernelProgressEvent(CamelModel):
    type: Literal["kernel_progress"] = "kernel_progress"
    kernel: str
    counts: list[ProgressCount] = Field(default_factory=list)


class GpuSampleEvent(CamelModel):
    type: Literal["gpu_sample"] = "gpu_sample"
    util_pct: float | None = Field(default=None, ge=0, le=100)
    vram_mb: float | None = Field(default=None, ge=0)
    power_w: float | None = Field(default=None, ge=0)
    temp_c: float | None = None


# spec_15's calibration metrics. spec_25 adds peak_power_w: the max sampled
# watts over a kernel window, fed from gpu_sample.powerW — either POSTed by
# tooling directly or derived by the store when a sampled session stops.
MeasurementMetric = Literal["stream_gbps", "peak_power_w"]


class MeasurementEvent(CamelModel):
    """A calibration measurement (spec_15). Persisted by the store, never a
    frame — replay() skips it."""

    type: Literal["measurement"] = "measurement"
    metric: MeasurementMetric
    value: float = Field(gt=0, allow_inf_nan=False)
    kernel: str | None = None


ProbeEvent = Annotated[
    Union[
        DeviceInfoEvent,
        KernelLaunchEvent,
        KernelProgressEvent,
        GpuSampleEvent,
        MeasurementEvent,
    ],
    Field(discriminator="type"),
]


class StampedEvent(CamelModel):
    """A probe event plus its ingest time (ms since session start).

    The stamp is applied at the transport edge (``live_store.py``) — the one
    place live mode reads a clock — so everything downstream stays pure.
    """

    t_ms: float = Field(ge=0)
    event: ProbeEvent


class SmActivity(CamelModel):
    sm_id: int
    blocks_run: int  # blocks this SM ran in the CURRENT kernel (resets per kernel)
    busy: bool  # blocks were resident in the last window
    estimated: bool = False  # spec_16: scaled from a declared sample, not counted


class BlockSpan(CamelModel):
    """One block's residency, normalized to the kernel's own span (spec_10)."""

    sm_id: int
    start_norm: float = Field(ge=0, le=1)
    end_norm: float = Field(ge=0, le=1)


class LiveState(CamelModel):
    """One frame of the live view; the renderer consumes nothing else."""

    session_id: str
    t_ms: float
    kind: Literal["kernel", "sample", "device", "progress"]
    device: DeviceInfo | None = None
    kernel: str | None = None
    grid: Dim3 | None = None
    block: Dim3 | None = None
    sm_activity: list[SmActivity]
    # Blocks the current kernel ran that the probe did NOT report (truncated
    # records). Nonzero means the per-SM picture is an undercount — the UI
    # must mark the frame partial rather than present it as complete.
    records_dropped: int = 0
    # spec_14: True while a kernel is mid-flight (progress frames); the
    # closing kernel_launch frame clears it.
    running: bool = False
    # spec_10: normalized block residency for the Gantt strip (kernel frames).
    block_spans: list[BlockSpan] | None = None
    spans_sampled: bool = False
    # spec_17: where the kernel data came from; "cupti" means timing-only.
    source: Literal["probe", "cupti"] = "probe"
    occupancy_source: Literal["theoretical", "measured"] = "theoretical"
    # spec_28: provenance is structural. "modeled" means the SM placement was
    # invented by a remap onto another die; recorded_on then names the die
    # the data was actually measured on. Measured frames never carry it.
    placement: Literal["measured", "modeled"] = "measured"
    recorded_on: str | None = None
    occupancy_pct: float | None = None
    elapsed_ms: float | None = None
    util_pct: float | None = None
    vram_mb: float | None = None
    power_w: float | None = None
    temp_c: float | None = None


def _idle_activity(count: int) -> list[SmActivity]:
    return [SmActivity(sm_id=i, blocks_run=0, busy=False) for i in range(count)]


def _sm_limit(prev: LiveState | None) -> int:
    if prev is not None and prev.device is not None:
        return prev.device.sm_count
    return DEFAULT_SM_COUNT


def _spans(ev: KernelLaunchEvent) -> tuple[list[BlockSpan] | None, bool]:
    """Normalize block clock64 stamps to [0,1] over the kernel's span."""
    valid = [r for r in ev.blocks if r.end >= r.start and r.end > 0]
    if not valid:
        return None, False
    sampled = len(valid) > MAX_SPANS
    take = valid[:MAX_SPANS]
    lo = min(r.start for r in take)
    hi = max(r.end for r in take)
    width = hi - lo
    if width <= 0:
        return [BlockSpan(sm_id=r.smid, start_norm=0.0, end_norm=1.0) for r in take], sampled
    return (
        [
            BlockSpan(
                sm_id=r.smid,
                start_norm=(r.start - lo) / width,
                end_norm=(r.end - lo) / width,
            )
            for r in take
        ],
        sampled,
    )


def _carry_telemetry(state: LiveState, prev: LiveState | None) -> LiveState:
    if prev is None:
        return state
    state.util_pct = prev.util_pct
    state.vram_mb = prev.vram_mb
    state.power_w = prev.power_w
    state.temp_c = prev.temp_c
    return state


def fold(prev: LiveState | None, session_id: str, stamped: StampedEvent) -> LiveState:
    """Fold one stamped event into the next frame.

    Kernel events replace the per-SM picture (``blocks_run`` is per kernel —
    the number that makes run-to-run scheduler variation visible); progress
    events accumulate monotonically until the closing launch replaces them;
    sample events refresh telemetry and clear ``busy``; device events size
    the die. Telemetry and last-kernel fields carry forward so the counters
    never flicker to null.

    Raises ``ValueError`` on data that contradicts the session's device — a
    smid outside the die, or a device change under recorded kernels.
    """
    ev = stamped.event
    limit = _sm_limit(prev)
    # spec_28: provenance carries forward — once a stream is modeled (the
    # remap marker on its device_info), every downstream frame says so.
    placement = prev.placement if prev else "measured"
    recorded_on = prev.recorded_on if prev else None

    if isinstance(ev, MeasurementEvent):  # pragma: no cover — replay skips these
        raise ValueError("measurement events are not frames")

    if isinstance(ev, DeviceInfoEvent):
        if ev.modeled_from is not None:
            placement, recorded_on = "modeled", ev.modeled_from
        new_count = ev.sm_count
        if prev is not None and prev.kernel is not None and new_count != limit:
            raise ValueError(
                f"device changed mid-session: {limit} -> {new_count} SMs "
                "after kernels were recorded"
            )
        return LiveState(
            session_id=session_id,
            t_ms=stamped.t_ms,
            kind="device",
            device=ev.device(),
            kernel=prev.kernel if prev else None,
            grid=prev.grid if prev else None,
            block=prev.block if prev else None,
            sm_activity=(
                prev.sm_activity
                if prev is not None and len(prev.sm_activity) == new_count
                else _idle_activity(new_count)
            ),
            records_dropped=prev.records_dropped if prev else 0,
            source=prev.source if prev else "probe",
            occupancy_source=prev.occupancy_source if prev else "theoretical",
            placement=placement,
            recorded_on=recorded_on,
            occupancy_pct=prev.occupancy_pct if prev else None,
            elapsed_ms=prev.elapsed_ms if prev else None,
            util_pct=prev.util_pct if prev else None,
            vram_mb=prev.vram_mb if prev else None,
            power_w=prev.power_w if prev else None,
            temp_c=prev.temp_c if prev else None,
        )

    if isinstance(ev, KernelLaunchEvent):
        per_sm = [0] * limit
        for rec in ev.blocks:
            if rec.smid >= limit:
                raise ValueError(
                    f"smid {rec.smid} out of range for a {limit}-SM device"
                )
            per_sm[rec.smid] += 1
        estimated = ev.sampled and ev.sample_stride > 1
        if estimated:
            per_sm = [n * ev.sample_stride for n in per_sm]
        spans, spans_sampled = _spans(ev)
        state = LiveState(
            session_id=session_id,
            t_ms=stamped.t_ms,
            kind="kernel",
            device=prev.device if prev else None,
            kernel=ev.kernel,
            grid=ev.grid,
            block=ev.block,
            sm_activity=[
                SmActivity(sm_id=i, blocks_run=n, busy=n > 0, estimated=estimated)
                for i, n in enumerate(per_sm)
            ],
            records_dropped=ev.records_dropped(),
            running=False,
            block_spans=spans,
            spans_sampled=spans_sampled,
            source=ev.source,
            occupancy_source=ev.occupancy_source,
            placement=placement,
            recorded_on=recorded_on,
            occupancy_pct=ev.occupancy_pct,
            elapsed_ms=ev.elapsed_ms,
        )
        return _carry_telemetry(state, prev)

    if isinstance(ev, KernelProgressEvent):
        # Accumulate monotonically on top of any prior progress for the SAME
        # kernel; a different kernel name starts a fresh picture.
        continuing = (
            prev is not None and prev.running and prev.kernel == ev.kernel
        )
        per_sm = (
            [a.blocks_run for a in prev.sm_activity] if continuing else [0] * limit
        )
        busy = [False] * limit
        for c in ev.counts:
            if c.smid >= limit:
                raise ValueError(
                    f"smid {c.smid} out of range for a {limit}-SM device"
                )
            per_sm[c.smid] = max(per_sm[c.smid], c.started)
            busy[c.smid] = c.started > c.ended
        state = LiveState(
            session_id=session_id,
            t_ms=stamped.t_ms,
            kind="progress",
            device=prev.device if prev else None,
            kernel=ev.kernel,
            grid=prev.grid if continuing else None,
            block=prev.block if continuing else None,
            sm_activity=[
                SmActivity(sm_id=i, blocks_run=n, busy=busy[i])
                for i, n in enumerate(per_sm)
            ],
            records_dropped=0,
            running=True,
            placement=placement,
            recorded_on=recorded_on,
        )
        return _carry_telemetry(state, prev)

    # GpuSampleEvent
    return LiveState(
        session_id=session_id,
        t_ms=stamped.t_ms,
        kind="sample",
        device=prev.device if prev else None,
        kernel=prev.kernel if prev else None,
        grid=prev.grid if prev else None,
        block=prev.block if prev else None,
        sm_activity=[
            SmActivity(
                sm_id=a.sm_id,
                blocks_run=a.blocks_run,
                busy=False,
                estimated=a.estimated,
            )
            for a in (prev.sm_activity if prev else _idle_activity(limit))
        ],
        records_dropped=prev.records_dropped if prev else 0,
        running=prev.running if prev else False,
        source=prev.source if prev else "probe",
        occupancy_source=prev.occupancy_source if prev else "theoretical",
        placement=placement,
        recorded_on=recorded_on,
        occupancy_pct=prev.occupancy_pct if prev else None,
        elapsed_ms=prev.elapsed_ms if prev else None,
        util_pct=ev.util_pct,
        vram_mb=ev.vram_mb,
        power_w=ev.power_w,
        temp_c=ev.temp_c,
    )


class KernelStat(CamelModel):
    kernel: str
    runs: int
    best_ms: float | None = None
    worst_ms: float | None = None


class SessionSummary(CamelModel):
    """Whole-session answers (spec_20 #1): the fold's counterpart for
    "what happened in this recording"."""

    session_id: str
    frames: int
    kernel_launches: int
    device_name: str | None = None
    duration_ms: float
    kernel_stats: list[KernelStat]


def summarize(session_id: str, trace: list[LiveState]) -> SessionSummary:
    stats: dict[str, KernelStat] = {}
    device = None
    for s in trace:
        if s.device is not None:
            device = s.device.name
        if s.kind != "kernel" or s.kernel is None:
            continue
        st = stats.setdefault(s.kernel, KernelStat(kernel=s.kernel, runs=0))
        st.runs += 1
        if s.elapsed_ms is not None:
            st.best_ms = (
                s.elapsed_ms if st.best_ms is None else min(st.best_ms, s.elapsed_ms)
            )
            st.worst_ms = (
                s.elapsed_ms if st.worst_ms is None else max(st.worst_ms, s.elapsed_ms)
            )
    return SessionSummary(
        session_id=session_id,
        frames=len(trace),
        kernel_launches=sum(st.runs for st in stats.values()),
        device_name=device,
        duration_ms=trace[-1].t_ms if trace else 0.0,
        kernel_stats=sorted(stats.values(), key=lambda st: st.kernel),
    )


def replay(session_id: str, events: list[StampedEvent]) -> list[LiveState]:
    """Rebuild a session's full frame sequence. Pure and deterministic —
    the same recording always yields the same trace (the test pins this).
    Measurement events are calibrations, not frames — skipped.

    Raises ``ValueError`` on a non-monotonic stamp: time running backwards in
    a recording is corruption, not data.
    """
    states: list[LiveState] = []
    prev: LiveState | None = None
    last_t = -1.0
    for st in events:
        if st.t_ms < last_t:
            raise ValueError(
                f"non-monotonic stamp: {st.t_ms} after {last_t} in {session_id}"
            )
        last_t = st.t_ms
        if isinstance(st.event, MeasurementEvent):
            continue
        prev = fold(prev, session_id, st)
        states.append(prev)
    return states
