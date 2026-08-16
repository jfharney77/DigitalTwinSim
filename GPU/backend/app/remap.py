"""spec_28 — fleet replay: remap a recorded event stream onto another die.

Pure, like ``live.py`` (the AST purity check in ``tests/test_remap.py``
covers this file too): no fastapi/time/file imports, ever. ``remap_events``
rewrites the stream and the *existing* ``replay()`` folds it — no second
render path, no forked ``LiveState`` logic.

The honesty rule dominates everything here: a remapped frame is **modeled,
never measured**. The marker is ``DeviceInfoEvent.modeled_from`` — the fold
turns it into ``placement="modeled"`` / ``recordedOn=<original device>`` on
every downstream frame, ingest rejects any event carrying it, and the
identity remap (target == recorded device) short-circuits to the untouched
stream, because labeling measured data modeled is the honesty rule inverted.

What stays true under remap: block count, grid and block dims, per-block
durations and launch order, kernel name, elapsed ms, recordsDropped,
sampling flags, telemetry (gpu_sample frames pass through untouched).
What is invented: which SM each block lands on — and everything downstream
of placement (per-SM counts, queue depth, Gantt rows, the idle-tile count).
Measured occupancy (spec_15) is stripped: it was measured on a die the
remapped picture no longer shows.
"""

from __future__ import annotations

from .live import (
    BlockRecord,
    DeviceInfoEvent,
    KernelLaunchEvent,
    KernelProgressEvent,
    ProgressCount,
    StampedEvent,
)
from .models import GpuProfile
from .profiles import RTX_4060_LAPTOP


def recorded_device_name(events: list[StampedEvent]) -> str:
    """The die a recording actually ran on: its first device_info's name,
    or the spec_07 default when the recording never declared one."""
    for st in events:
        if isinstance(st.event, DeviceInfoEvent):
            return st.event.name
    return RTX_4060_LAPTOP.name


def _remap_launch(ev: KernelLaunchEvent, sm_count: int) -> KernelLaunchEvent:
    # Deterministic round-robin in launch order: sort by start, ties broken
    # by the original (smid, start[, end]) — a total order, so the function
    # is a function. Every start/end stamp is preserved; only smid changes.
    ordered = sorted(ev.blocks, key=lambda r: (r.start, r.smid, r.end))
    blocks = [
        BlockRecord(smid=i % sm_count, start=r.start, end=r.end)
        for i, r in enumerate(ordered)
    ]
    update: dict[str, object] = {"blocks": blocks}
    if ev.occupancy_source == "measured":
        # Measured occupancy belongs to the recorded die, never a modeled one.
        update["occupancy_source"] = "theoretical"
        update["occupancy_pct"] = None
    return ev.model_copy(update=update)


def _remap_progress(ev: KernelProgressEvent, sm_count: int) -> KernelProgressEvent:
    # Re-bucket per-SM tallies by the same round-robin rule: enumerate the
    # started blocks in (source smid) order and deal them across the target.
    started: dict[int, int] = {}
    ended: dict[int, int] = {}
    i = 0
    for c in sorted(ev.counts, key=lambda c: c.smid):
        for j in range(c.started):
            t = i % sm_count
            started[t] = started.get(t, 0) + 1
            if j < c.ended:
                ended[t] = ended.get(t, 0) + 1
            i += 1
    counts = [
        ProgressCount(smid=s, started=started[s], ended=ended.get(s, 0))
        for s in sorted(started)
    ]
    return ev.model_copy(update={"counts": counts})


def remap_events(
    events: list[StampedEvent], target: GpuProfile
) -> list[StampedEvent]:
    """Rewrite a recorded stream as-if scheduled on ``target``.

    Identity (target == recorded device) returns the stream untouched —
    measured data is never relabeled modeled. Otherwise every device_info is
    replaced by one built from the target profile (marker set; fields we
    never measured stay ``None``), and if the stream opens with anything
    else, a marked device_info is inserted at the front so the fold sizes
    the die before the first remapped smid arrives (the one case where the
    frame count grows, by exactly one device frame).
    """
    recorded_on = recorded_device_name(events)
    if target.name == recorded_on:
        return events
    sm_count = target.sm.rows * target.sm.cols

    def marked_device(t_ms: float) -> StampedEvent:
        return StampedEvent(
            t_ms=t_ms,
            event=DeviceInfoEvent(
                name=target.name, sm_count=sm_count, modeled_from=recorded_on
            ),
        )

    out: list[StampedEvent] = []
    if events and not isinstance(events[0].event, DeviceInfoEvent):
        out.append(marked_device(events[0].t_ms))
    for st in events:
        ev = st.event
        if isinstance(ev, DeviceInfoEvent):
            out.append(marked_device(st.t_ms))
        elif isinstance(ev, KernelLaunchEvent):
            out.append(
                StampedEvent(t_ms=st.t_ms, event=_remap_launch(ev, sm_count))
            )
        elif isinstance(ev, KernelProgressEvent):
            out.append(
                StampedEvent(t_ms=st.t_ms, event=_remap_progress(ev, sm_count))
            )
        else:
            # gpu_sample / measurement: telemetry was measured on the recorded
            # die — it passes through untouched and the frame label says so.
            out.append(st)
    return out
