"""twinkit.static_dispatch answers as FastAPI would, on the real app and on the
stub — the contract static hosting rests on (docs/STATIC_HOSTING.md)."""

from __future__ import annotations

import pytest

from twinkit.models import CamelModel
from twinkit.static_dispatch import body_key, canonical, dispatch, dispatch_json, route_params
from twinkit import fastapi_stub


class Ask(CamelModel):
    load_pct: int = 50


class Answer(CamelModel):
    doubled_pct: int


def build(FastAPI, Query, HTTPException):
    app = FastAPI(title="t")

    @app.get("/api/thing", response_model=Answer)
    def thing(level: int = Query(3, ge=1, le=5), scenario: str = "a") -> Answer:
        if scenario == "missing":
            raise HTTPException(status_code=404, detail="unknown")
        return Answer(doubled_pct=level * 2)

    @app.post("/api/simulate", response_model=Answer)
    def simulate(ask: Ask) -> Answer:
        return Answer(doubled_pct=ask.load_pct * 2)

    return app


def apps():
    out = [build(fastapi_stub.FastAPI, fastapi_stub.Query, fastapi_stub.HTTPException)]
    try:
        import fastapi
        out.append(build(fastapi.FastAPI, fastapi.Query, fastapi.HTTPException))
    except ImportError:  # pragma: no cover
        pass
    return out


@pytest.mark.parametrize("app", apps())
def test_dispatch_matches_the_backend_contract(app):
    assert dispatch(app, "GET", "/api/thing", {}) == (200, {"doubledPct": 6})
    assert dispatch(app, "GET", "/api/thing", {"level": "1"}) == (200, {"doubledPct": 2})
    assert dispatch(app, "GET", "/api/thing", {"level": "9"})[0] == 422
    assert dispatch(app, "GET", "/api/thing", {"level": "x"})[0] == 422
    assert dispatch(app, "GET", "/api/thing", {"scenario": "missing"}) == (404, {"detail": "unknown"})
    assert dispatch(app, "GET", "/api/nope", {})[0] == 404
    assert dispatch(app, "POST", "/api/simulate", {}, {"loadPct": 21}) == (200, {"doubledPct": 42})
    assert dispatch(app, "POST", "/api/simulate", {}, {"loadPct": "many"})[0] == 422
    assert dispatch_json(app, "POST", "/api/simulate", "{}", '{"loadPct":1}') == '{"status":200,"body":{"doubledPct":2}}'
    kinds = {k: v["kind"] for r in app.routes if getattr(r, "path", "") == "/api/thing"
             for k, v in route_params(r).items()}
    assert kinds == {"level": "query", "scenario": "query"}


def test_body_key_is_the_value_the_browser_computes():
    # Pinned against packages/twin-ui/src/staticApi.ts bodyKey() for the same data.
    body = {"config": {"x": 1.0, "y": 0.25, "s": "é—"}, "events": [{"t": 60, "k": True, "n": None}]}
    assert body_key(body) == "c70ea4ab"
    assert canonical({"b": 2.0, "a": [1.5]}) == '{"a":[1.5],"b":2}'
