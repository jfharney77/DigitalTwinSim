"""FastAPI app: serves the enclosure map, constants, presets, guided
scenarios, explain entries, and the simulator itself. The engine is pure;
this file is the only impure edge. ``POST /api/simulate`` takes a Scenario
and returns the deterministic trace; ``GET /api/simulate`` runs the
default scenario so a liveness probe has something to read."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .constants import CONSTANTS, RISK_FACTOR, RISK_FACTOR_SOURCE
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    ArrayMap,
    ConfigPreset,
    Explain,
    GuidedScenario,
    Scenario,
    SimResponse,
    WorkloadPreset,
)
from .presets import CONFIG_PRESETS, EXPLAINS, GUIDED_SCENARIOS, WORKLOAD_PRESETS
from .validation import validate

app = make_app(
    title="PowerVault ME5 RAID Physics Simulator",
    frontend_port=5214,
)


@app.get("/api/anatomy", response_model=ArrayMap)
def get_anatomy(level: int = Level) -> ArrayMap:
    return leveled(ANATOMY, level)


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    """The whole constants table, sources and all — so the UI can badge
    estimate-derived readouts and there is no second copy of any value."""
    return {
        "constants": {
            k: v.model_dump(by_alias=True) for k, v in CONSTANTS.items()
        },
        "riskFactors": RISK_FACTOR,
        "riskFactorSource": RISK_FACTOR_SOURCE,
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
    """The default scenario (RAID 6 build, OLTP workload) — for liveness
    probes and a zero-click first paint."""
    from .presets import OLTP

    return _run(Scenario(workload=OLTP))


# --- Graded labs (docs/LAB_PATTERN.md) --------------------------------------
# app/labs.py is pure; this is its HTTP edge, and the only place lab prose is
# resolved to a reading level. Reference solutions are never served.
from fastapi import HTTPException  # noqa: E402
from twinkit.labs import Lab, LabResult  # noqa: E402

from .labs import LABS, LABS_BY_ID, grade_scenario  # noqa: E402


@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    """The graded labs: goal, criteria, hints and start scenario."""
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    """Run the learner's scenario through the engine and grade the trace."""
    if lab_id not in LABS_BY_ID:
        raise HTTPException(status_code=404, detail=f"unknown lab {lab_id!r}")
    return leveled(grade_scenario(lab_id, scenario), level)
