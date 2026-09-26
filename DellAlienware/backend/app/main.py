"""FastAPI app: serves the laptop catalog, interior anatomies, use cases,
and the AC power-path simulation. All content is static data + a pure
engine — no state. Runs on port 8003 (frontend Vite dev server on 5176
proxies /api here)."""

from __future__ import annotations

from fastapi import HTTPException, Query

from twinkit.api import Level, make_app
from twinkit.labs import Lab, LabResult
from twinkit.tour import TourResponse

from .anatomy import ANATOMIES
from .catalog import DEFAULT_PROFILE, PROFILES
from .diagnostics import (
    BASELINE_ID,
    DIAGNOSTIC_SCENARIO,
    SCENARIO_ID,
    TRACE_SCENARIOS,
    analyze_charge_diagnostics,
    simulate_charge_diagnostics,
    walk_adapters,
)
from .engine import analyze, simulate
from .labs import EXPLAINS, LABS, LABS_BY_ID, Explain, grade_scenario
from .leveling import leveled, leveled_all
from .models import (
    Anatomy,
    DiagnosticResponse,
    LaptopProfile,
    Scenario,
    SimulateRequest,
    SimulateResponse,
    TraceScenario,
    UseCase,
)
from .tour import TOUR_RESPONSE
from .usecases import USE_CASES

app = make_app(
    title="Alienware m18 Inside",
    frontend_port=5176,
)


@app.get("/api/catalog", response_model=list[LaptopProfile])
def get_catalog(level: int = Level) -> list[LaptopProfile]:
    return leveled_all(list(PROFILES.values()), level)


@app.get("/api/catalog/default", response_model=LaptopProfile)
def get_default_profile(level: int = Level) -> LaptopProfile:
    return leveled(DEFAULT_PROFILE, level)


@app.get("/api/anatomy", response_model=list[Anatomy])
def get_anatomies(level: int = Level) -> list[Anatomy]:
    return leveled_all(list(ANATOMIES.values()), level)


@app.get("/api/anatomy/{anatomy_id}", response_model=Anatomy)
def get_anatomy(anatomy_id: str, level: int = Level) -> Anatomy:
    anatomy = ANATOMIES.get(anatomy_id)
    if anatomy is None:
        raise HTTPException(status_code=404, detail=f"unknown anatomy {anatomy_id!r}")
    return leveled(anatomy, level)


@app.get("/api/usecases", response_model=list[UseCase])
def get_usecases(level: int = Level) -> list[UseCase]:
    return leveled_all(USE_CASES, level)


@app.get("/api/tour", response_model=TourResponse)
def get_tour(level: int = Level) -> TourResponse:
    """The narrated guided tour (m18 R2 interior, one fixed scenario)."""
    return leveled(TOUR_RESPONSE, level)


# Which trace to play. Omitted (or "plug-in") is the plug-in power path,
# unchanged; "charge-taper-diagnostics" is the failure walk in diagnostics.py.
TraceScenarioId = Query(
    None,
    alias="scenario",
    description="Trace scenario id; see GET /api/scenarios. Omit for the plug-in trace.",
)


@app.post("/api/simulate", response_model=SimulateResponse | DiagnosticResponse)
def post_simulate(
    req: SimulateRequest,
    level: int = Level,
    # Named for its wire name: twinkit.static_dispatch (the static-hosted build's
    # in-browser path) binds query parameters by Python name, not by alias.
    scenario: str | None = TraceScenarioId,
) -> SimulateResponse | DiagnosticResponse:
    trace_scenario = scenario
    scenario = req.scenario
    if trace_scenario is not None and trace_scenario not in TRACE_SCENARIOS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"unknown scenario {trace_scenario!r}; "
                f"known: {sorted(TRACE_SCENARIOS)}"
            ),
        )
    profile = PROFILES.get(scenario.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=422, detail=f"unknown profileId {scenario.profile_id!r}"
        )
    adapter = next(
        (a for a in profile.adapters if a.id == scenario.adapter_id), None
    )
    if adapter is None:
        raise HTTPException(
            status_code=422,
            detail=(
                f"unknown adapterId {scenario.adapter_id!r} "
                f"for profile {profile.id!r}"
            ),
        )
    if trace_scenario == SCENARIO_ID:
        good, _ = walk_adapters(profile, adapter)
        walk = simulate_charge_diagnostics(profile, adapter, scenario)
        return leveled(
            DiagnosticResponse(
                profile=profile,
                scenario=scenario,
                adapter=good,
                summary=analyze_charge_diagnostics(profile, adapter, walk),
                trace=walk,
                trace_scenario=DIAGNOSTIC_SCENARIO,
            ),
            level,
        )
    trace = simulate(profile, adapter, scenario)
    return leveled(
        SimulateResponse(
            profile=profile,
            scenario=scenario,
            adapter=adapter,
            summary=analyze(profile, adapter, scenario, trace),
            trace=trace,
        ),
        level,
    )


@app.get("/api/scenarios", response_model=list[TraceScenario])
def get_scenarios(level: int = Level) -> list[TraceScenario]:
    """The traces POST /api/simulate can play: the plug-in path and the
    charging-diagnostics failure walk (?scenario=<id>)."""
    return leveled_all(list(TRACE_SCENARIOS.values()), level)


# --- Graded labs (docs/LAB_PATTERN.md) ---------------------------------------
# Labs and their Explain entries are data; grading is app/labs.py's pure
# function. The reference solutions never leave the server.


@app.get("/api/explain", response_model=list[Explain])
def get_explain(level: int = Level) -> list[Explain]:
    """The power path's equations — what each graded lab line cites."""
    return leveled_all(EXPLAINS, level)


@app.get("/api/labs", response_model=list[Lab])
def get_labs(level: int = Level) -> list[Lab]:
    return leveled_all(LABS, level)


@app.post("/api/labs/{lab_id}/grade", response_model=LabResult)
def post_lab_grade(lab_id: str, scenario: Scenario, level: int = Level) -> LabResult:
    if lab_id not in LABS_BY_ID:
        raise HTTPException(
            status_code=404,
            detail=f"unknown lab {lab_id!r}; known: {sorted(LABS_BY_ID)}",
        )
    try:
        result = grade_scenario(lab_id, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return leveled(result, level)
