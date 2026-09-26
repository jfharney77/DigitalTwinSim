"""Run one engine in-process from a camelCase scenario dict."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .loader import EngineHandle, load_engine
from .models import Stage
from .reader import dump, slim_trace

TIME_UNIT = {
    "PhysicsCompute": "s", "PhysicsCDU": "s", "PhysicsFabric": "s",
    "PhysicsRackPower": "s", "PhysicsXR": "s", "DellPowerEdgeR760Thermal": "s",
    "PhysicsStorage": "h", "PhysicsAIFactory": "h", "PhysicsResilience": "h",
    "PhysicsDataDomain": "d", "PhysicsFleet": "d",
}


@dataclass
class EngineRun:
    handle: EngineHandle
    scenario: Any                 # the validated Scenario model
    trace: list[Any]
    log: list[Any]
    summary: Any
    validations: list[Any] = field(default_factory=list)

    @property
    def component(self) -> str:
        return self.handle.component


def run_engine(component: str, scenario: dict | None) -> EngineRun:
    handle = load_engine(component)
    model = handle.Scenario.model_validate(scenario or {})
    trace, log, summary = handle.simulate(model)
    return EngineRun(handle, model, list(trace), list(log), summary, handle.validate(model))


def stage_of(
    run: EngineRun,
    stage_id: str,
    label: str,
    injected_events: list[dict] | None = None,
    injected_config: dict | None = None,
) -> Stage:
    return Stage(
        id=stage_id,
        component=run.component,
        label=label,
        time_unit=TIME_UNIT[run.component],
        scenario=dump(run.scenario),
        injected_events=injected_events or [],
        injected_config=injected_config or {},
        trace=slim_trace(run.trace),
        summary=dump(run.summary),
        validations=[v for v in dump(run.validations) if v.get("level") != "ok"],
        log=dump(run.log)[:200],
    )
