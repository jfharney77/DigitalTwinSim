"""The same couplings over recorded JSON traces instead of live engines.

A ``SimResponse`` body saved from a running twin (camelCase dicts) can be fed
through the same ``adapt`` and ``check`` functions the live executors use: the
couplings read fields through ``reader.get``, which accepts either shape. No
engine is imported here; the target scenario comes back as JSON to POST to the
target twin (or to run later), and a recorded target response can be checked
against the recorded source.
"""

from __future__ import annotations

from typing import Any

from .couplings import c1_compute_heat_to_cdu as c1
from .couplings import c3_storage_to_compute_feed as c3
from .couplings import c5_wall_watts_to_rackpower as c5
from .couplings import c7_xr_site_to_fleet as c7
from .models import SeamResult


def _trace(response: dict | list) -> list[dict]:
    return response["trace"] if isinstance(response, dict) else response


def adapt(coupling: str, source: Any, base_scenario: dict | None = None,
          params: dict | None = None) -> dict:
    """Target scenario JSON for ``coupling`` from recorded source response(s)."""
    params = params or {}
    if coupling == "c1":
        return c1.adapt(_trace(source), base_scenario, cdu=params.get("cdu"),
                        racks=int(params.get("racks", 1)))[0]
    if coupling == "c3":
        return c3.adapt(_trace(source), base_scenario, params)[0]
    if coupling == "c5":
        sources = [(label, _trace(resp)) for label, resp in source]
        return c5.adapt(sources, base_scenario, params)[0]
    if coupling == "c7":
        outcomes = []
        for site in source:
            o = c7.site_outcome(site["response"]["summary"], int(site["durationS"]),
                                float(params.get("throttle_fault_fraction", c7.THROTTLE_FAULT_FRACTION)))
            o.update({"id": site["id"], "sites": int(site["sites"])})
            outcomes.append(o)
        return c7.adapt(outcomes, base_scenario, params)[0]
    raise KeyError(f"{coupling}: no JSON path (C2, C4, C6 and C8 run engines between their passes)")


def check(coupling: str, source: Any, target: dict | list,
          params: dict | None = None) -> list[SeamResult]:
    """The seam identity for ``coupling`` over two recorded responses."""
    params = params or {}
    if coupling == "c1":
        return c1.check(_trace(source), _trace(target), cdu=params.get("cdu"),
                        racks=int(params.get("racks", 1)))
    if coupling == "c5":
        sources = [(label, _trace(resp)) for label, resp in source]
        return c5.check(sources, _trace(target), int(params.get("slots_used", len(sources))))
    raise KeyError(f"{coupling}: no JSON seam check")
