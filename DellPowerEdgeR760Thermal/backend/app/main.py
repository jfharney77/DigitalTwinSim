"""FastAPI app: serves the chassis map, constants, presets, guided
scenarios, explain entries, and the simulator itself. The engine is pure;
this file is the only impure edge. ``POST /api/simulate`` takes a Scenario
and returns the deterministic trace (the Alienware twin's pattern);
``GET /api/simulate`` runs the default scenario so the CustomerSetup
liveness enrichment — which expects a GET — has something to read."""

from __future__ import annotations

from twinkit.api import Level, make_app

from .anatomy import ANATOMY
from .constants import CONSTANTS, PSU_CURVE_SOURCE, PSU_EFFICIENCY_CURVE
from .engine import simulate
from .leveling import leveled, leveled_all
from .models import (
    ChassisMap,
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
    title="R760 Power & Thermal Simulator",
    frontend_port=5203,
)


@app.get("/api/anatomy", response_model=ChassisMap)
def get_anatomy(level: int = Level) -> ChassisMap:
    return leveled(ANATOMY, level)


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    """The whole constants table, sources and all — so the UI can badge
    estimate-derived readouts and there is no second copy of any value."""
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
    """The default scenario (Balanced build, database workload) — for the
    CustomerSetup chip enrichment and for a zero-click first paint."""
    from .presets import BALANCED, DATABASE

    return _run(Scenario(config=BALANCED, workload=DATABASE))
