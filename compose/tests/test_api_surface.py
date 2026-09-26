"""The six routes, pinned by name, and the shapes the page reads.

The server module is loaded from its path under a private name rather than
imported as ``app.main``: the root suite lets 40-odd backends take turns
holding the name ``app``, and the composition layer stays out of that game
(compose/tests/conftest.py says why).
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

SERVER = pathlib.Path(__file__).resolve().parent.parent / "backend" / "app" / "main.py"

EXPECTED_ROUTES = {
    "/api/health",
    "/api/levels",
    "/api/couplings",
    "/api/chains",
    "/api/constants",
    "/api/run",
    "/api/run/custom",
}


@pytest.fixture(scope="module")
def server():
    pytest.importorskip("fastapi")
    name = "_compose_server_main"
    spec = importlib.util.spec_from_file_location(name, SERVER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(name, None)


@pytest.fixture(scope="module")
def client(server):
    starlette_testclient = pytest.importorskip("starlette.testclient")
    return starlette_testclient.TestClient(server.app)


def test_api_surface_snapshot(server):
    """Add a route deliberately: this test names all of them."""
    paths = {r.path for r in server.app.routes if r.path.startswith("/api")}
    assert paths == EXPECTED_ROUTES


def test_the_preset_route_is_a_get_and_the_custom_one_a_post(server):
    """The split is what makes a static build possible: presets are
    addressable by URL and snapshotted, a custom chain needs the engines."""
    by_path = {r.path: set(r.methods) for r in server.app.routes if r.path.startswith("/api/run")}
    assert "GET" in by_path["/api/run"]
    assert by_path["/api/run/custom"] == {"POST"}


def test_health_and_levels_are_the_shared_shapes(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    levels = client.get("/api/levels").json()
    assert levels["default"] == 3
    assert [l["level"] for l in levels["levels"]] == [1, 2, 3, 4, 5]


def test_couplings_carry_reading_levels(client):
    novice = client.get("/api/couplings?level=1").json()
    standard = client.get("/api/couplings?level=3").json()
    assert [c["id"] for c in standard] == [f"c{i}" for i in range(1, 9)]
    assert novice != standard, "level 1 reads the same as level 3 — nothing is authored"
    for c in standard:
        assert c["identity"] and c["test"] and c["sourceFields"]


def test_chains_carry_the_body_the_post_route_takes(client):
    chains = client.get("/api/chains").json()
    ids = {c["id"] for c in chains}
    assert {"heat-to-cdu", "closed-loop", "factory-fed"} <= ids
    body = next(c for c in chains if c["id"] == "heat-to-cdu")["defaultChain"]
    posted = client.post("/api/run/custom", json=body)
    assert posted.status_code == 200
    assert posted.json()["chainId"] == "heat-to-cdu"


def test_get_run_is_the_liveness_get_and_404s_on_an_unknown_chain(client):
    trace = client.get("/api/run?chain=heat-to-cdu").json()
    assert trace["stages"] and trace["seams"] and trace["charts"]
    assert trace["illustrative"] is True
    assert client.get("/api/run?chain=nope").status_code == 404


def test_constants_are_served_with_their_sources(client):
    constants = client.get("/api/constants").json()["constants"]
    assert constants["comm_fraction"]["estimated"] is True
    for name, c in constants.items():
        assert c["unit"] and c["source"], name
