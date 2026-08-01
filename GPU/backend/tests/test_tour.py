"""spec_18 — lesson-tour invariants (same style as the repo's tour spec)."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from app.live_store import load_recording
from app.main import TOURS_DIR, app
from app.tour import build_tour

client = TestClient(app)


def test_tour_module_is_pure() -> None:
    src = (Path(__file__).parent.parent / "app" / "tour.py").read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for n in names:
                assert n.split(".")[0] in {"__future__", "typing", "", "models"}, (
                    f"impure import {n}"
                )


def test_every_step_resolves_and_cursor_is_valid() -> None:
    tour = build_tour()
    assert tour.steps, "empty tour"
    for step in tour.steps:
        path = TOURS_DIR / f"{step.lesson_id}.jsonl"
        assert path.exists(), f"missing golden recording {step.lesson_id}"
        trace = load_recording(path, step.lesson_id)
        assert 0 <= step.cursor < len(trace), f"{step.id}: cursor out of range"
        assert step.script.strip()
        assert step.provenance in ("hardware", "representative")


def test_cursor_frames_are_kernel_frames() -> None:
    # Each step narrates a kernel moment; pinning an idle sample would show
    # a dark die under a script describing activity.
    for step in build_tour().steps:
        trace = load_recording(TOURS_DIR / f"{step.lesson_id}.jsonl", step.lesson_id)
        assert trace[step.cursor].kind == "kernel", step.id


def test_tour_endpoints() -> None:
    r = client.get("/api/tour")
    assert r.status_code == 200
    tour = r.json()
    first = tour["steps"][0]["lessonId"]
    rec = client.get(f"/api/tour/recordings/{first}")
    assert rec.status_code == 200
    assert rec.json()["trace"]
    assert client.get("/api/tour/recordings/nope").status_code == 404
    assert client.get("/api/tour/recordings/..%2fescape").status_code == 404


def test_recordings_replay_in_ci() -> None:
    for p in sorted(TOURS_DIR.glob("*.jsonl")):
        trace = load_recording(p)
        assert trace, f"{p.name} replays empty"
        assert trace[0].kind == "device"  # geometry travels with the recording
