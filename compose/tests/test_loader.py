from __future__ import annotations

import sys

import pytest

from compose.loader import AbsoluteAppImport, COMPONENTS, load_engine


def test_two_engines_alive_at_once_have_distinct_classes():
    app_before = sys.modules.get("app")
    cdu = load_engine("PhysicsCDU")
    compute = load_engine("PhysicsCompute")
    assert cdu.Scenario is not compute.Scenario
    assert cdu.Scenario.__module__ == "_twin_PhysicsCDU.models"
    assert compute.Scenario.__module__ == "_twin_PhysicsCompute.models"
    # Both still work after the other loaded.
    assert cdu.simulate(cdu.Scenario())[0] and compute.simulate(compute.Scenario())[0]
    assert sys.modules.get("app") is app_before, "loading must never touch the name `app`"


def test_every_engine_in_scope_loads_and_has_the_shared_signature():
    for component in COMPONENTS:
        handle = load_engine(component)
        trace, log, summary = handle.simulate(handle.Scenario())
        assert trace and summary is not None, component
        assert handle.constants.CONSTANTS, component


def test_handles_are_cached():
    assert load_engine("PhysicsFleet") is load_engine("PhysicsFleet")


def test_unknown_components_are_refused_by_name():
    with pytest.raises(KeyError):
        load_engine("DellPowerStore")


def test_an_absolute_app_import_fails_with_a_named_error(tmp_path):
    app = tmp_path / "Rogue" / "backend" / "app"
    app.mkdir(parents=True)
    (app / "__init__.py").write_text("")
    (app / "models.py").write_text("class Scenario: ...\nclass SimEvent: ...\n")
    (app / "constants.py").write_text("CONSTANTS = {}\ndef value(n): return 0\n")
    (app / "engine.py").write_text("from app.models import Scenario\ndef simulate(s): return [], [], None\n")
    with pytest.raises(AbsoluteAppImport, match="Rogue"):
        load_engine("Rogue", repo=tmp_path)
