"""compose/ is pure like the engines it couples: no FastAPI, no clock, no
randomness, no file or network IO. The server under compose/backend/ is the
only impure edge and is not checked here."""

from __future__ import annotations

import importlib
import pathlib

from twinkit.testing import assert_engine_is_pure

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _modules() -> list[str]:
    names = []
    for path in sorted(ROOT.glob("*.py")) + sorted((ROOT / "couplings").glob("*.py")):
        rel = path.relative_to(ROOT.parent).with_suffix("")
        names.append(".".join(rel.parts))
    return names


def test_every_compose_module_is_pure():
    names = _modules()
    assert "compose.loader" in names and "compose.couplings.c8_factory_fed" in names
    for name in names:
        module = importlib.import_module(name)
        assert_engine_is_pure(module, also_ban=("socket", "urllib", "requests", "httpx", "subprocess", "datetime"))


def test_only_the_loader_uses_importlib():
    users = [
        p.name for p in list(ROOT.glob("*.py")) + list((ROOT / "couplings").glob("*.py"))
        if "importlib" in p.read_text(encoding="utf-8") and p.name != "loader.py"
    ]
    assert users == [], users
