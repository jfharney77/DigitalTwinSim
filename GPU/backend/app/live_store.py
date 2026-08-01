"""Live CUDA co-browsing (spec_08) — the IMPURE edge.

Everything the pure layer (``live.py``) is forbidden to do happens here, and
only here: reading the clock to stamp events, appending session JSONL files,
and fanning frames out to SSE subscribers. Keep this module thin — if logic
wants to grow here, it probably belongs in the pure fold.

Sessions are append-only JSONL under ``backend/sessions/`` (one stamped event
per line, camelCase). A finished session replays through ``live.replay()``
like any other pure trace.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid
from pathlib import Path

from .live import (
    LiveState,
    MeasurementEvent,
    ProbeEvent,
    StampedEvent,
    fold,
    replay,
)
from .models import CamelModel

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"
# spec_15: calibration measurements outlive sessions — latest value per metric.
MEASUREMENTS_FILE = "measurements.json"
# spec_20 #6: a recording is a lesson artifact, not an unbounded log.
MAX_SESSION_EVENTS = 100_000
# spec_20 #7: keep this many past values per metric so drift is visible.
MEASUREMENT_HISTORY = 20


class SessionInfo(CamelModel):
    id: str
    name: str
    event_count: int
    active: bool = False


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-]+", "-", name).strip("-").lower()
    return s or "session"


class Subscriber:
    """One SSE consumer: its frame queue plus a count of frames dropped when
    the queue was full. The stream reports drops so a lagging tab knows its
    view skipped ahead — silence would let a stale die pass as live."""

    __slots__ = ("queue", "dropped")

    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
        self.dropped = 0

    def take_dropped(self) -> int:
        n, self.dropped = self.dropped, 0
        return n


class LiveHub:
    """One active session at a time; any number of SSE subscribers."""

    def __init__(self) -> None:
        self._session_id: str | None = None
        self._session_name: str | None = None
        self._t0: float | None = None  # monotonic origin of the session
        self._latest: LiveState | None = None
        self._event_count = 0
        self._subscribers: set[Subscriber] = set()

    # -- sessions -------------------------------------------------------------

    @staticmethod
    def _ensure_dir() -> None:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        # Recordings are user data — never version-controlled (spec_21 #16).
        gi = SESSIONS_DIR / ".gitignore"
        if not gi.exists():
            gi.write_text("*\n!.gitignore\n")

    def start_session(self, name: str | None = None) -> SessionInfo:
        self.stop_session()
        label = name or "session"
        stamp = time.strftime("%Y%m%d-%H%M%S")
        # The uuid suffix makes ids collision-proof: two same-name sessions in
        # the same second must never share a file (a shared file interleaves
        # two time origins and the recording becomes unreplayable).
        self._session_id = f"{stamp}-{uuid.uuid4().hex[:6]}-{_slug(label)}"
        self._session_name = label
        self._t0 = time.monotonic()
        self._latest = None
        self._event_count = 0
        self._ensure_dir()
        self._path(self._session_id).touch()
        return self.active_session()  # type: ignore[return-value]

    def stop_session(self) -> None:
        self._session_id = None
        self._session_name = None
        self._t0 = None
        self._latest = None
        self._event_count = 0

    def active_session(self) -> SessionInfo | None:
        if self._session_id is None:
            return None
        return SessionInfo(
            id=self._session_id,
            name=self._session_name or self._session_id,
            event_count=self._event_count,
            active=True,
        )

    def _ensure_session(self) -> None:
        # The probe should light the die without ceremony: first event with no
        # session open starts an ad-hoc one.
        if self._session_id is None:
            self.start_session("adhoc")

    def _path(self, session_id: str) -> Path:
        # session ids come from us or from list_sessions(); the guard keeps
        # path traversal out of hand-crafted requests.
        if "/" in session_id or ".." in session_id:
            raise ValueError(f"bad session id {session_id!r}")
        return SESSIONS_DIR / f"{session_id}.jsonl"

    def delete_session(self, session_id: str) -> None:
        """Delete a recording (spec_19 #2). The active session is refused —
        deleting the file under a live recorder corrupts, never helps."""
        if session_id == self._session_id:
            raise PermissionError("session is actively recording")
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        path.unlink()

    def import_session(self, name: str, jsonl: str) -> SessionInfo:
        """spec_20 #3: save an uploaded recording — but only after the whole
        thing replays cleanly. A recording that can't replay isn't saved."""
        events = [
            StampedEvent.model_validate_json(line)
            for line in jsonl.splitlines()
            if line.strip()
        ]
        if not events:
            raise ValueError("empty recording")
        if len(events) > MAX_SESSION_EVENTS:
            raise ValueError("recording exceeds the event cap")
        replay("import", events)  # raises on anything unreplayable
        stamp = time.strftime("%Y%m%d-%H%M%S")
        sid = f"{stamp}-{uuid.uuid4().hex[:6]}-{_slug(name)}"
        self._ensure_dir()
        self._path(sid).write_text(
            "\n".join(e.model_dump_json(by_alias=True) for e in events) + "\n"
        )
        return SessionInfo(
            id=sid, name=_slug(name), event_count=len(events), active=False
        )

    def rename_session(self, session_id: str, new_name: str) -> SessionInfo:
        """spec_20 #5: rename = new slug, same stamp+uuid prefix."""
        if session_id == self._session_id:
            raise PermissionError("session is actively recording")
        old = self._path(session_id)
        if not old.exists():
            raise FileNotFoundError(session_id)
        prefix = "-".join(session_id.split("-", 3)[:3])  # stamp + hex6
        new_id = f"{prefix}-{_slug(new_name)}"
        new = self._path(new_id)
        if new.exists() and new != old:
            raise ValueError(f"a recording named {new_id!r} already exists")
        old.rename(new)
        with new.open() as f:
            count = sum(1 for line in f if line.strip())
        return SessionInfo(
            id=new_id, name=_slug(new_name), event_count=count, active=False
        )

    def raw_recording(self, session_id: str) -> str:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        return path.read_text()

    def latest(self) -> LiveState | None:
        return self._latest

    def list_sessions(self, limit: int = 50) -> list[SessionInfo]:
        self._ensure_dir()
        infos = []
        # Newest first (ids sort chronologically); bounded (spec_19 #4).
        for p in sorted(SESSIONS_DIR.glob("*.jsonl"), reverse=True)[:limit]:
            with p.open() as f:
                count = sum(1 for line in f if line.strip())
            infos.append(
                SessionInfo(
                    id=p.stem,
                    # id layout: YYYYmmdd-HHMMSS-<hex6>-<name-slug>
                    name=p.stem.split("-", 3)[-1],
                    event_count=count,
                    active=p.stem == self._session_id,
                )
            )
        return infos

    def load_trace(self, session_id: str) -> list[LiveState]:
        path = self._path(session_id)
        if not path.exists():
            raise FileNotFoundError(session_id)
        return load_recording(path, session_id)

    # -- measurements (spec_15) ----------------------------------------------

    def record_measurement(self, ev: MeasurementEvent) -> None:
        self._ensure_dir()
        path = SESSIONS_DIR / MEASUREMENTS_FILE
        data = json.loads(path.read_text()) if path.exists() else {}
        prior = data.get(ev.metric, {})
        history = (prior.get("history") or [])[-(MEASUREMENT_HISTORY - 1):]
        if "value" in prior:
            history.append(prior["value"])
        data[ev.metric] = {
            "value": ev.value,
            "kernel": ev.kernel,
            "measuredAt": time.strftime("%Y-%m-%d"),
            "history": history,
        }
        path.write_text(json.dumps(data, indent=2) + "\n")

    def measurements(self) -> dict:
        path = SESSIONS_DIR / MEASUREMENTS_FILE
        return json.loads(path.read_text()) if path.exists() else {}

    # -- ingest + fan-out -----------------------------------------------------

    def ingest(self, event: ProbeEvent) -> LiveState:
        self._ensure_session()
        assert self._session_id is not None and self._t0 is not None

        # Measurements are calibrations, not frames (spec_15): persist to the
        # measurement store and return the current picture unchanged.
        if isinstance(event, MeasurementEvent):
            self.record_measurement(event)
            if self._latest is not None:
                return self._latest
            from .live import _idle_activity, _sm_limit  # local, stays pure

            return LiveState(
                session_id=self._session_id,
                t_ms=0.0,
                kind="sample",
                sm_activity=_idle_activity(_sm_limit(None)),
            )

        if self._event_count >= MAX_SESSION_EVENTS:
            raise OverflowError(
                f"recording full ({MAX_SESSION_EVENTS} events) — start a new session"
            )
        t_ms = (time.monotonic() - self._t0) * 1000.0
        stamped = StampedEvent(t_ms=t_ms, event=event)
        # Fold BEFORE persisting: an event the fold rejects (smid beyond the
        # device, mid-session device change) must never enter the recording.
        folded = fold(self._latest, self._session_id, stamped)
        with self._path(self._session_id).open("a") as f:
            f.write(stamped.model_dump_json(by_alias=True) + "\n")
        self._event_count += 1
        self._latest = folded
        payload = self._latest.model_dump_json(by_alias=True)
        for sub in list(self._subscribers):
            try:
                sub.queue.put_nowait(payload)
            except asyncio.QueueFull:
                # A stalled browser tab must never block ingest — but the
                # drop is counted and reported on the stream, never silent.
                sub.dropped += 1
        return self._latest

    def subscribe(self) -> Subscriber:
        sub = Subscriber()
        if self._latest is not None:
            sub.queue.put_nowait(self._latest.model_dump_json(by_alias=True))
        self._subscribers.add(sub)
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        self._subscribers.discard(sub)


HUB = LiveHub()


def load_recording(path: Path, session_id: str | None = None) -> list[LiveState]:
    """Replay any JSONL recording (a session file, or a golden lesson
    recording under backend/tours/ — spec_18)."""
    events = [
        StampedEvent.model_validate_json(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    return replay(session_id or path.stem, events)
