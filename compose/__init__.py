"""The composition layer: one engine's trace becomes another engine's scenario,
and an identity is asserted across the seam.

    from compose import run, presets
    trace = run(presets.chain("closed-loop"))

See docs/COMPOSITION_DESIGN.md and compose/README.md.
"""

from .chain import Chain, Link, run
from .models import CoupledTrace, SeamResult
from .seam import assert_seams

__all__ = ["Chain", "Link", "run", "CoupledTrace", "SeamResult", "assert_seams"]
