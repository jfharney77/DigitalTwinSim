"""The UI renders every prose field as plain text, so markdown emphasis
(`*word*`, `**word**`) would reach the reader as literal asterisks. The Dell
clean-design skin also rules out highlighted text, so the fix is plain prose,
not a markdown renderer. Checked on every content endpoint at every level."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
EMPHASIS = re.compile(r"\*[^\s*][^*]*\*")


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for v in node.values():
            yield from _strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("path", ["/api/anatomy", "/api/inference", "/api/catalog", "/api/usecases", "/api/tour"])
def test_served_prose_carries_no_markdown_emphasis(path: str, level: int) -> None:
    r = client.get(path, params={"level": level})
    assert r.status_code == 200
    bad = [s for s in _strings(r.json()) if EMPHASIS.search(s)]
    assert not bad, f"{path}?level={level} serves literal markdown: {bad[0][:120]}"
