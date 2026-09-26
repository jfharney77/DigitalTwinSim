#!/usr/bin/env python3
"""Snapshot a component's API so its frontend can be hosted with no backend.

    scripts/build_static.py DellPowerStore            # -> DellPowerStore/frontend/dist-static/
    scripts/build_static.py PhysicsME5 --out /tmp/x   # somewhere else
    scripts/build_static.py PhysicsME5 --verify       # also diff against FastAPI's TestClient

Writes, under the output directory (a vite build's outDir — generated, never
committed):

    api-static/index.json                   what exists: params per route, prebaked POST keys
    api-static/<path>/<query>.json          every GET, at every reading level and scenario
    api-static/_post/<path>/<key>.json      POST answers for bodies known ahead of time
    py/bundle.zip                           app/ + twinkit/ sources, only if the app has a POST
                                            route: the in-browser engine (Pyodide) unpacks it

The recipe and the naming contract are docs/STATIC_HOSTING.md; the browser
half is packages/twin-ui/src/staticApi.ts. Both sides call
twinkit.static_dispatch, so a snapshot is what the backend would have said.

Optional <Component>/frontend/static.json:
    {"params": {"product": ["alienware", "promax"]},   values for query params the builder cannot guess
     "skip": ["/api/live"],                            path prefixes to leave out
     "postBodies": {"/api/simulate": [{...}]}}         extra request bodies to prebake
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import re
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LEVELS = ["1", "2", "3", "4", "5"]


def reexec_in_venv(component: str) -> None:
    py = REPO / component / "backend" / ".venv" / "bin" / "python"
    if py.exists() and Path(sys.prefix).resolve() != py.parent.parent.resolve() \
            and not os.environ.get("BUILD_STATIC_NO_REEXEC"):
        os.environ["BUILD_STATIC_NO_REEXEC"] = "1"
        os.execv(str(py), [str(py), *sys.argv])


def safe(value: str) -> str:
    """Must match staticApi.ts `safe()`."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def query_name(query: dict[str, str]) -> str:
    """Must match staticApi.ts `queryName()`: sorted `k-v` pairs joined by `__`, or `_`."""
    if not query:
        return "_"
    return "__".join(f"{safe(k)}-{safe(v)}" for k, v in sorted(query.items()))


def find_bodies(value, model, found):
    """Any nested object that validates as the POST body model and sits under a
    key named like one ('scenario', 'config'...) is a body the UI will send."""
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, dict) and k.lower() in ("scenario", "body", "request"):
                try:
                    model.model_validate(v)
                    found.append(v)
                except Exception:
                    pass
            find_bodies(v, model, found)
    elif isinstance(value, list):
        for v in value:
            find_bodies(v, model, found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("component")
    ap.add_argument("--out", default=None)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    component = args.component.strip("/")
    reexec_in_venv(component)

    backend = REPO / component / "backend"
    frontend = REPO / component / "frontend"
    out = Path(args.out) if args.out else frontend / "dist-static"
    sys.path[:0] = [str(backend), str(REPO)]
    os.chdir(backend)

    from twinkit.static_dispatch import api_routes, body_key, dispatch, route_params
    from app.main import app  # noqa: E402

    cfg_path = frontend / "static.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    skip = tuple(cfg.get("skip", []))
    enumerated: dict[str, list[str]] = {"level": LEVELS, **cfg.get("params", {})}

    # `scenario` ids come from the component's own listing.
    if "scenario" not in enumerated:
        status, listing = dispatch(app, "GET", "/api/scenarios", {})
        if status == 200 and isinstance(listing, list):
            enumerated["scenario"] = [s["id"] for s in listing if isinstance(s, dict) and "id" in s]

    public = frontend / "public"
    public_files = {"/" + str(p.relative_to(public)) for p in public.rglob("*") if p.is_file()} \
        if public.exists() else set()

    def relocate(value):
        """'/photo.webp' -> 'photo.webp': the site is served from a sub-path
        (vite --base=./), so root-absolute public assets must become relative."""
        if isinstance(value, str):
            return value[1:] if value in public_files else value
        if isinstance(value, dict):
            return {k: relocate(v) for k, v in value.items()}
        if isinstance(value, list):
            return [relocate(v) for v in value]
        return value

    api_dir = out / "api-static"
    index: dict[str, object] = {"component": component, "get": {}, "post": {}, "engine": False}
    written = 0
    warnings: list[str] = []
    snapshots: list[object] = []
    client = None
    if args.verify:
        from fastapi.testclient import TestClient
        client = TestClient(app)

    def write(path: Path, payload) -> None:
        nonlocal written
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False))
        written += 1

    for route in api_routes(app):
        if route.path.startswith(skip) if skip else False:
            continue
        if "GET" not in route.methods:
            continue
        params = route_params(route)
        if any(p["kind"] == "path" for p in params.values()):
            warnings.append(f"{route.path}: path parameters — not snapshotted (list URLs in static.json if needed)")
            continue
        axes = []
        ok = True
        for name, spec in params.items():
            values = enumerated.get(name)
            if values is None:
                if spec["required"]:
                    warnings.append(f"{route.path}: required param {name!r} has no values (static.json params)")
                    ok = False
                else:
                    warnings.append(f"{route.path}: param {name!r} snapshotted at its default only")
                axes.append([(name, None)])
            else:
                head = [] if spec["required"] else [(name, None)]
                axes.append(head + [(name, v) for v in values])
        if not ok:
            continue
        index["get"][route.path] = sorted(params)
        for combo in itertools.product(*axes):
            query = {k: v for k, v in combo if v is not None}
            status, payload = dispatch(app, "GET", route.path, query)
            if status != 200:
                continue  # e.g. a scenario id this route does not serve
            if client is not None:
                theirs = client.get(route.path, params=query).json()
                assert theirs == payload, f"dispatch != FastAPI for GET {route.path} {query}"
            snapshots.append(payload)
            rel = route.path[len("/api/"):] or "_root"
            write(api_dir / rel / f"{query_name(query)}.json", relocate(payload))

    # POST routes: bundle the engine for the browser and prebake known bodies.
    for route in api_routes(app):
        if "POST" not in route.methods or (skip and route.path.startswith(skip)):
            continue
        body_models = [p["type"] for p in route_params(route).values() if p["kind"] == "body"]
        if not body_models:
            continue
        index["engine"] = True
        model = body_models[0]
        bodies: list[dict] = list(cfg.get("postBodies", {}).get(route.path, []))
        find_bodies(snapshots, model, bodies)
        keys: list[str] = []
        for body in bodies:
            key = body_key(body)
            if key in keys:
                continue
            status, payload = dispatch(app, "POST", route.path, {}, body)
            if status != 200:
                continue
            if client is not None:
                assert client.post(route.path, json=body).json() == payload, \
                    f"dispatch != FastAPI for POST {route.path}"
            rel = route.path[len("/api/"):]
            write(api_dir / "_post" / rel / f"{key}.json", relocate(payload))
            keys.append(key)
        index["post"][route.path] = keys

    if index["engine"]:
        bundle = out / "py" / "bundle.zip"
        bundle.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
            for root, pkg in ((backend / "app", "app"), (REPO / "twinkit", "twinkit")):
                for p in sorted(root.rglob("*.py")):
                    relp = p.relative_to(root)
                    if "tests" in relp.parts or "__pycache__" in relp.parts:
                        continue
                    z.write(p, f"{pkg}/{relp}")
            # Non-Python data an app reads at import (JSON tables and the like).
            for p in sorted((backend / "app").rglob("*")):
                if p.is_file() and p.suffix in (".json", ".txt", ".csv", ".md"):
                    z.write(p, f"app/{p.relative_to(backend / 'app')}")

    write(api_dir / "index.json", index)
    for w in warnings:
        print(f"  note: {w}")
    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file() and
               ("api-static" in p.parts or "py" in p.parts))
    print(f"[{component}] {written} files, {size // 1024} KiB -> {out.relative_to(REPO) if out.is_relative_to(REPO) else out}"
          f"{'  (engine bundled for Pyodide)' if index['engine'] else ''}"
          f"{'  verified against FastAPI' if client is not None else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
