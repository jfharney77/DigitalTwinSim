"""FastAPI app for the composition layer.

``compose/`` is pure: it loads each engine in-process under a private package
name, couples two traces, and asserts an identity across the seam. This file is
the only impure edge, as ``live_store.py`` is for the GPU twin. It calls
``compose.run`` directly — the twins' own servers do not need to be running and
are never called over a socket.

Backend :8048, frontend :5221.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import Field

from twinkit.api import Level, make_app
from twinkit.models import CamelModel

from compose import Chain, Link, run
from compose.catalog import CHAIN_INFOS, COUPLINGS, ChainInfo, CouplingInfo
from compose.constants import CONSTANTS
from compose.leveling import leveled_all
from compose.models import CoupledTrace
from compose.presets import CHAINS

_MAX_ITER = int(CONSTANTS["fixed_point_max_iter"].value)

app = make_app(
    title="Composition — one engine's trace becomes another's scenario",
    frontend_port=5221,
)


class LinkRequest(CamelModel):
    coupling: str
    source: str
    target: str
    params: dict[str, Any] = Field(default_factory=dict)


class ChainRequest(CamelModel):
    """A chain as JSON. The presets are served in this shape by
    ``GET /api/chains`` (``defaultChain``), so the page can edit one and post
    it back."""

    id: str
    scenarios: dict[str, dict] = Field(default_factory=dict)
    links: list[LinkRequest] = Field(default_factory=list)
    closed: bool = False
    # Derived, not a second copy: the bound has to move with the constant, or a
    # posted chain cannot ask for the passes a warm facility-water day needs.
    max_iter: int = Field(_MAX_ITER, ge=1, le=2 * _MAX_ITER)
    damping: float = Field(0.5, gt=0.0, le=1.0)
    tol: float = Field(0.005, gt=0.0, le=0.5)
    title: str = ""
    params: dict[str, Any] = Field(default_factory=dict)

    def to_chain(self) -> Chain:
        return Chain(
            id=self.id,
            scenarios=self.scenarios,
            links=tuple(
                Link(coupling=l.coupling, source=l.source, target=l.target, params=dict(l.params))
                for l in self.links
            ),
            closed=self.closed,
            max_iter=self.max_iter,
            damping=self.damping,
            tol=self.tol,
            title=self.title or self.id,
            params=dict(self.params),
        )


def _run_or_refuse(chain: Chain) -> CoupledTrace:
    """Run a chain, turning an adapter's scope refusal into a 422.

    Some couplings refuse rather than clamp — a server too big for a rack slot
    (C5), more rack heat than a CDU can carry (C1). Those are ``ValueError``
    subclasses raised while adapting, and they carry the sentence the reader
    needs; without this they would leave as a 500 with no message.
    """
    try:
        return run(chain)
    except ValueError as refusal:
        raise HTTPException(status_code=422, detail=str(refusal)) from refusal


# The trace routes come first: running a chain is what this app is.
@app.post("/api/run/custom", response_model=CoupledTrace)
def post_run(chain: ChainRequest) -> CoupledTrace:
    """An edited chain. Its own path rather than a POST on ``/api/run`` so a
    static build can serve the presets from snapshots and leave this one out
    (docs/STATIC_HOSTING.md): running an arbitrary chain needs eleven engines
    in the interpreter, which is more than the browser bundle carries."""
    return _run_or_refuse(chain.to_chain())


@app.get("/api/run", response_model=CoupledTrace)
def get_run(chain: str = "heat-to-cdu") -> CoupledTrace:
    """A preset chain with its default scenarios. Also the liveness GET: the
    CustomerSetup chips and the smoke harness expect one."""
    if chain not in CHAINS:
        raise HTTPException(status_code=404, detail=f"unknown chain {chain!r}")
    return _run_or_refuse(CHAINS[chain])


@app.get("/api/couplings", response_model=list[CouplingInfo])
def get_couplings(level: int = Level) -> list[CouplingInfo]:
    """The eight seams as data: fields, units, time bases, the identity each
    one asserts, and the pytest that asserts it."""
    return leveled_all(COUPLINGS, level)


@app.get("/api/chains", response_model=list[ChainInfo])
def get_chains(level: int = Level) -> list[ChainInfo]:
    """The preset chains, each carrying the JSON body ``POST /api/run``
    takes."""
    return leveled_all(CHAIN_INFOS, level)


@app.get("/api/constants")
def get_constants() -> dict[str, object]:
    """The seam constants — the numbers neither engine on either side owns —
    with unit, source and whether they are an estimate."""
    return {"constants": {k: v.model_dump(by_alias=True) for k, v in CONSTANTS.items()}}
