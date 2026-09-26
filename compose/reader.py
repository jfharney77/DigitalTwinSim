"""One way to read a field, whether the state is a live model or recorded JSON.

Couplings are written against ``get(state, "liquid_watts")``. A live engine
hands back pydantic models (snake_case attributes); a recorded ``SimResponse``
body is dicts with camelCase keys. ``get`` reads either, so the same coupling
runs over both (``compose/json_adapter.py``).
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

from pydantic.alias_generators import to_camel


def get(state: Any, field: str, default: Any = None) -> Any:
    if isinstance(state, dict):
        if field in state:
            return state[field]
        return state.get(to_camel(field), default)
    return getattr(state, field, default)


def series(trace: Iterable[Any], field: str) -> list[float]:
    return [float(get(s, field, 0.0) or 0.0) for s in trace]


def dump(model: Any) -> Any:
    """A model, a list of models, or already-plain data, as camelCase JSON data."""
    if hasattr(model, "model_dump"):
        return model.model_dump(by_alias=True)
    if isinstance(model, (list, tuple)):
        return [dump(m) for m in model]
    return model


def slim_trace(trace: Sequence[Any]) -> list[dict]:
    """The trace as dicts, without the per-region maps (the Couplings page
    draws strip charts, not floorplans, and the maps are most of the bytes)."""
    out = []
    for state in trace:
        row = dump(state)
        out.append({k: v for k, v in row.items() if not isinstance(v, dict)})
    return out
