"""FastAPI app for the client-device physics simulator: serves the
device maps, constants, presets, guided scenarios, explain entries, and
the simulator itself. The engine is pure; this file is the only impure
edge. ``POST /api/simulate`` takes a Scenario and returns the
deterministic trace; ``GET /api/simulate`` runs the default scenario."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app

from .anatomy import MAPS, map_for
from .brandmap import BRAND_MAP
from .constants import CONSTANTS, PSU_CURVE_SOURCE, PSU_EFFICIENCY_CURVE
from .engine import simulate
from .labs import LABS, LABS_BY_ID, grade_scenario
from .media import MEDIA
from .leveling import leveled, leveled_all
from .models import (
    BrandMap,
    ConfigPreset,
    DeviceMap,
    Explain,
    GuidedScenario,
    PageIntro,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import AAA, AW_LAPTOP, PAGE_INTRO, CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, WORKLOAD_PRESETS
from .validation import validate
from twinkit.labs import Lab, LabResult

app = make_app(
    title="Client-Device Physics Simulator",
    frontend_port=5204,
)


@app.get("/api/anatomy", response_model=DeviceMap)
def get_anatomy(
    product: str = Query("alienware"),
    form_factor: str = Query("laptop", alias="formFactor"),
    level: int = Level,
    view: str | None = Query(None),
) -> DeviceMap:
    # `view` names a map id directly (aw-laptop / aw-desktop / promax). It
    # exists for the static build: snapshots are keyed by the Python parameter
    # name, which an aliased parameter such as formFactor cannot supply.
    if view is not None:
        if view not in MAPS:
            raise HTTPException(404, f"unknown map {view}")
        return leveled(MAPS[view], level)
    return leveled(map_for(product, form_factor), level)


@app.get("/api/anatomy/{map_id}", response_model=DeviceMap)
def get_anatomy_by_id(map_id: str, level: int = Level) -> DeviceMap:
    if map_id not in MAPS:
        raise HTTPException(404, f"unknown map {map_id}")
    return leveled(MAPS[map_id], level)


@app.get("/api/brandmap", response_model=BrandMap)
def get_brandmap(level: int = Level) -> BrandMap:
    """The 2025 client-brand map (physics_specs/10 §8) — the naming
    scheme this app's two products live inside."""
    return leveled(BRAND_MAP, level)


@app.get("/api/media")
def get_media(level: int = Level) -> dict[str, object]:
    """V1/V9 product media — photos/facsimiles with mandatory credits.
    Captions (the V10 x-ray text) are leveled like all teaching prose."""
    return {k: leveled(v, level).model_dump(by_alias=True) for k, v in MEDIA.items()}


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    return {
        "constants": {
            k: v.model_dump(by_alias=True) for k, v in CONSTANTS.items()
        },
        "psuEfficiencyCurve": PSU_EFFICIENCY_CURVE,
        "psuCurveSource": PSU_CURVE_SOURCE,
    }


@app.get("/api/presets/configs", response_model=list[ConfigPreset])
def get_config_presets() -> list[ConfigPreset]:
    return CONFIG_PRESETS


@app.get("/api/presets/workloads", response_model=list[WorkloadPreset])
def get_workload_presets() -> list[WorkloadPreset]:
    return WORKLOAD_PRESETS


@app.get("/api/scenarios", response_model=list[GuidedScenario])
def get_scenarios(level: int = Level) -> list[GuidedScenario]:
    return leveled_all(GUIDED_SCENARIOS, level)


@app.get("/api/intro", response_model=PageIntro)
def get_intro(level: int = Level) -> PageIntro:
    """The simulator page's opening paragraph and instrument glossary,
    leveled like the rest of the teaching prose."""
    return leveled(PAGE_INTRO, level)


@app.get("/api/explain", response_model=list[Explain])
def get_explain(level: int = Level) -> list[Explain]:
    return leveled_all(EXPLAINS, level)


def _run(scenario: Scenario) -> SimResponse:
    trace, log, summary = simulate(scenario)
    return SimResponse(
        validations=validate(scenario),
        trace=trace,
        log=log,
        summary=summary,
    )


@app.post("/api/simulate", response_model=SimResponse)
def post_simulate(scenario: Scenario) -> SimResponse:
    return _run(scenario)


@app.get("/api/simulate", response_model=SimResponse)
def get_simulate() -> SimResponse:
    """Default scenario (Alienware laptop, AAA load) — zero-click first
    paint and the CustomerSetup-style GET liveness probe."""
    return _run(Scenario(config=AW_LAPTOP, workload=AAA))


# --- Graded labs (docs/LAB_PATTERN.md) -------------------------------------
# The API serves the labs and grades scenarios; the reference solutions and
# the gaming attempts in labs.py never leave the server.

@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(404, f"unknown lab {lab_id}")
    return leveled(grade_scenario(lab_id, scenario), level)
