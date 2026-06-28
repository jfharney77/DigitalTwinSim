"""Data models for the GPU Matmul Visualizer.

These mirror the TypeScript interfaces in initial_spec.md (§3). Field names are
snake_case in Python but serialize to camelCase JSON so the React frontend can
consume them directly (macDone, macTotal, coreState, ...).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Phase = Literal["idle", "load", "compute", "writeback", "done"]
CoreState = Literal["idle", "loading", "computing", "wrote"]
DType = Literal["fp32"]  # future: fp16, bf16, int8


class CamelModel(BaseModel):
    """Base model: snake_case in Python, camelCase over the wire."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SMGrid(CamelModel):
    rows: int = Field(ge=1)
    cols: int = Field(ge=1)


class Memory(CamelModel):
    stacks: int = Field(ge=1)
    label: str = "HBM"


class GpuProfile(CamelModel):
    """Describes the die. Everything structural derives from this (spec §3)."""

    name: str
    sm: SMGrid
    # to_camel would yield "coresPerSm"; spec (and the TS types) want "coresPerSM".
    cores_per_sm: SMGrid = Field(alias="coresPerSM")
    memory: Memory
    has_l2_bus: bool = True

    def total_cores(self) -> int:
        return (
            self.sm.rows
            * self.sm.cols
            * self.cores_per_sm.rows
            * self.cores_per_sm.cols
        )


class Workload(CamelModel):
    kind: Literal["matmul"] = "matmul"
    n: int = Field(ge=2, le=64, alias="N")
    dtype: DType = "fp32"


class SimState(CamelModel):
    """Pure data emitted per step; the renderer consumes this (spec §3)."""

    cycle: int
    phase: Phase
    k: int
    mac_done: int
    mac_total: int
    mem_active: bool
    core_state: list[CoreState]
    active_cores: int
    utilization: float


class SimulateRequest(CamelModel):
    profile: GpuProfile
    workload: Workload


class SimulateResponse(CamelModel):
    profile: GpuProfile
    workload: Workload
    total_cores: int
    mac_total: int
    trace: list[SimState]
