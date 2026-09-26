"""The composition layer's own constants.

Same discipline as every engine's ``constants.py``: a value, a unit, a source
and an ``estimated`` flag, served to the UI so there is no second copy. These
are the numbers a *seam* needs that neither engine on either side owns.
"""

from __future__ import annotations

from twinkit.models import CamelModel


class Constant(CamelModel):
    value: float
    unit: str
    source: str
    estimated: bool
    blurb: str


CONSTANTS: dict[str, Constant] = {
    "comm_fraction": Constant(
        value=0.25, unit="fraction of a training step",
        source="Estimate. Published large-model training profiles put collective "
               "communication between roughly 15% and 40% of step time depending on "
               "parallelism layout; 0.25 is a round middle.",
        estimated=True,
        blurb="Share of one training step spent in collectives. Only this share "
              "stretches when the fabric's flow-completion time stretches (C4).",
    ),
    "util_deadband_pct": Constant(
        value=1.0, unit="utilization points",
        source="Design choice: PhysicsCDU's util_pct is an integer.",
        estimated=False,
        blurb="C1 emits a set-util event only when utilization moves by a whole point.",
    ),
    "supply_deadband_c": Constant(
        value=0.25, unit="°C",
        source="Design choice, sized to PhysicsCDU's 0.01 °C output rounding and the "
               "240-event cap.",
        estimated=False,
        blurb="C2 emits a set-coolant-supply event only when supply moves this far.",
    ),
    "cap_deadband_pct": Constant(
        value=1.0, unit="cap points",
        source="Design choice: PhysicsCompute's gpu_pct is an integer.",
        estimated=False,
        blurb="C2 emits a set-workload event only when the carried cap moves a point.",
    ),
    "load_deadband_w": Constant(
        value=10.0, unit="W",
        source="Design choice, below the metering resolution a rack PDU reports.",
        estimated=False,
        blurb="C5 emits a set-load event only when a server's wall watts move this far.",
    ),
    "max_injected_events": Constant(
        value=240, unit="events per run",
        source="Design choice: keeps an adapted scenario readable in the UI diff.",
        estimated=False,
        blurb="Upper bound on the events any adapter writes into a target scenario. "
              "When a series would need more, the deadband is widened and the seam "
              "tolerance widens with it.",
    ),
    "fixed_point_damping": Constant(
        value=0.5, unit="fraction",
        source="Design choice (docs/COMPOSITION_DESIGN.md section 4, C2).",
        estimated=False,
        blurb="Each closed-loop iteration moves the carried cap half way to the new value.",
    ),
    "fixed_point_max_iter": Constant(
        value=48, unit="iterations",
        source="Design choice (docs/COMPOSITION_DESIGN.md section 4, C2), raised from the "
               "design's 12 to cover the whole range PhysicsCDU accepts: the map still "
               "contracts on 45 °C facility water, only far more slowly, and the worst valid "
               "day measured took 37 passes. compose/tests/test_edges.py pins that.",
        estimated=False,
        blurb="The closed loop stops here whether or not it has settled, and says which. "
              "The preset days settle in one to five passes; the cap is sized for the "
              "hottest facility water the CDU model accepts.",
    ),
    "fixed_point_tol": Constant(
        value=0.005, unit="relative",
        source="Design choice (docs/COMPOSITION_DESIGN.md section 4, C2).",
        estimated=False,
        blurb="The loop has settled when run-integrated liquid energy moves less than this.",
    ),
    "heatwave_days_per_year": Constant(
        value=12, unit="days per site-year",
        source="Estimate. A round figure for days on which a hot-climate rooftop "
               "enclosure sees its design-day inlet; varies widely by climate.",
        estimated=True,
        blurb="How often the hostile day PhysicsXR simulates actually happens (C7).",
    ),
    "filter_visit_h": Constant(
        value=1.0, unit="admin-hours per visit",
        source="Estimate: a scheduled filter swap folded into an existing site visit.",
        estimated=True,
        blurb="What preventing the shutdown costs, for C7's comparison with the truck rolls.",
    ),
    "gpus_per_xe9712_rack": Constant(
        value=72, unit="GPUs",
        source="NVIDIA GB200 NVL72 (72 GPUs per rack), as in PhysicsCompute's 18 trays × 4.",
        estimated=False,
        blurb="Scales one detailed rack to the factory's rack count (C8).",
    ),
    "facility_overhead_pue": Constant(
        value=0.12, unit="PUE points",
        source="Estimate: lighting, UPS and distribution losses, and the facility-side "
               "chilled-water plant, as a flat share of IT power.",
        estimated=True,
        blurb="The part of PUE the CDU model does not see; added to the pump share in C8.",
    ),
}


def value(name: str) -> float:
    return CONSTANTS[name].value


def estimated_names(*names: str) -> list[str]:
    """``compose.<name>`` for each named constant that is an estimate."""
    return [f"compose.{n}" for n in names if CONSTANTS[n].estimated]
