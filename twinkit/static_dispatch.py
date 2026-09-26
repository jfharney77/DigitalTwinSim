"""Call a component's API routes as plain functions — no server, no threads.

Two callers, one code path (docs/STATIC_HOSTING.md):

* ``scripts/build_static.py`` snapshots every GET endpoint to JSON files;
* the in-browser Pyodide worker answers ``POST /api/simulate`` by running the
  same ``engine.py`` the backend runs.

FastAPI's own request path runs sync endpoints in a thread pool, and Pyodide
has no threads, so the ASGI app cannot be driven in the browser. Every
component endpoint is a plain function of query parameters and at most one
pydantic body, so this module does what FastAPI would: find the route, coerce
the query, validate the body, call the function, dump the result by alias.
It works on a real ``FastAPI`` app and on :mod:`twinkit.fastapi_stub`'s.

Pure stdlib + pydantic. No IO.
"""

from __future__ import annotations

import enum
import inspect
import json
import re
import typing
from typing import Any

from pydantic import BaseModel, ValidationError

__all__ = ["api_routes", "route_params", "dispatch", "dispatch_json", "canonical", "body_key"]


def api_routes(app: Any) -> list[Any]:
    """The component's own routes: anything under ``/api`` with an endpoint."""
    return [
        r for r in app.routes
        if getattr(r, "path", "").startswith("/api") and getattr(r, "endpoint", None)
    ]


def _hints(fn: Any) -> dict[str, Any]:
    try:
        return typing.get_type_hints(fn)
    except Exception:  # unresolvable forward ref: fall back to raw annotations
        return dict(getattr(fn, "__annotations__", {}))


def _is_model(tp: Any) -> bool:
    return inspect.isclass(tp) and issubclass(tp, BaseModel)


def route_params(route: Any) -> dict[str, dict[str, Any]]:
    """``{name: {"kind": "query"|"path"|"body", "type": tp, "default": d, "required": bool}}``."""
    hints = _hints(route.endpoint)
    in_path = set(re.findall(r"{(\w+)", route.path))
    out: dict[str, dict[str, Any]] = {}
    for name, p in inspect.signature(route.endpoint).parameters.items():
        tp = hints.get(name, str)
        default = p.default
        if hasattr(default, "default") and not isinstance(default, (str, int, float, bool)):
            default = default.default  # Query(3, ...) -> 3
        required = default is inspect.Parameter.empty or default is ...
        try:  # pydantic's "undefined" sentinel, when the real FastAPI is in use
            from pydantic_core import PydanticUndefined
            required = required or default is PydanticUndefined
        except Exception:
            pass
        kind = "body" if _is_model(tp) else "path" if name in in_path else "query"
        out[name] = {"kind": kind, "type": tp, "default": default, "required": required,
                     "bounds": p.default}
    return out


def _coerce(raw: str, tp: Any) -> Any:
    origin = typing.get_origin(tp)
    if origin is typing.Union or str(origin) == "types.UnionType":
        args = [a for a in typing.get_args(tp) if a is not type(None)]
        tp = args[0] if args else str
    if tp is bool:
        if raw.lower() in ("1", "true", "yes", "on"):
            return True
        if raw.lower() in ("0", "false", "no", "off"):
            return False
        raise ValueError(f"not a boolean: {raw!r}")
    if tp is int:
        return int(raw)
    if tp is float:
        return float(raw)
    if inspect.isclass(tp) and issubclass(tp, enum.Enum):
        return tp(raw)
    return raw


def _check_bounds(name: str, value: Any, spec: Any) -> None:
    for attr, ok in (("ge", lambda v, b: v >= b), ("le", lambda v, b: v <= b),
                     ("gt", lambda v, b: v > b), ("lt", lambda v, b: v < b)):
        bound = getattr(spec, attr, None)
        if bound is None:
            for m in getattr(spec, "metadata", ()) or ():  # real FastAPI keeps them here
                bound = getattr(m, attr, None)
                if bound is not None:
                    break
        if bound is not None and not ok(value, bound):
            raise ValueError(f"{name} must be {attr} {bound}")


def encode(value: Any) -> Any:
    """What FastAPI's response path produces: models by alias, JSON-safe leaves."""
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [encode(v) for v in value]
    if isinstance(value, enum.Enum):
        return value.value
    return value


def _match(app: Any, method: str, path: str) -> tuple[Any, dict[str, str]] | None:
    for r in api_routes(app):
        if method.upper() not in (r.methods or set()):
            continue
        pattern = "^" + re.sub(r"{(\w+)(:[^}]*)?}", r"(?P<\1>[^/]+)", r.path) + "$"
        m = re.match(pattern, path)
        if m:
            return r, m.groupdict()
    return None


def dispatch(app: Any, method: str, path: str, query: dict[str, str] | None = None,
             body: Any = None) -> tuple[int, Any]:
    """``(status, json-able payload)`` for one request, as the backend would answer."""
    found = _match(app, method, path)
    if found is None:
        return 404, {"detail": "Not Found"}
    route, path_values = found
    query = dict(query or {})
    kwargs: dict[str, Any] = {}
    for name, spec in route_params(route).items():
        if spec["kind"] == "body":
            try:
                kwargs[name] = spec["type"].model_validate(body if body is not None else {})
            except ValidationError as exc:
                return 422, {"detail": json.loads(exc.json(include_url=False))}
            continue
        raw = path_values.get(name) if spec["kind"] == "path" else query.get(name)
        if raw is None:
            if spec["required"]:
                return 422, {"detail": f"missing parameter {name!r}"}
            kwargs[name] = spec["default"]
            continue
        try:
            value = _coerce(raw, spec["type"])
            _check_bounds(name, value, spec["bounds"])
        except ValueError as exc:
            return 422, {"detail": str(exc)}
        kwargs[name] = value
    try:
        result = route.endpoint(**kwargs)
        if inspect.iscoroutine(result):  # async endpoints: native callers only
            import asyncio
            result = asyncio.run(result)
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status is None:
            raise
        return int(status), {"detail": getattr(exc, "detail", str(exc))}
    return 200, encode(result)


def dispatch_json(app: Any, method: str, path: str, query_json: str = "{}",
                  body_json: str | None = None) -> str:
    """String in, string out — the shape the browser worker calls."""
    body = json.loads(body_json) if body_json else None
    status, payload = dispatch(app, method, path, json.loads(query_json or "{}"), body)
    return json.dumps({"status": status, "body": payload}, separators=(",", ":"))


# --- prebaked POST responses -------------------------------------------------
# The builder can answer known request bodies ahead of time (the default
# scenario, every guided scenario) so first paint never waits for Pyodide. The
# browser finds them by hashing the body it is about to send; both sides must
# canonicalize identically. packages/twin-ui/src/staticApi.ts mirrors this.

def canonical(value: Any) -> str:
    """Key-sorted, whitespace-free JSON with integral floats written as ints —
    what ``JSON.stringify`` of the same data produces after key-sorting."""
    def norm(v: Any) -> Any:
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, float) and v.is_integer() and abs(v) < 1e15:
            return int(v)
        if isinstance(v, dict):
            return {k: norm(v[k]) for k in sorted(v)}
        if isinstance(v, (list, tuple)):
            return [norm(x) for x in v]
        return v
    return json.dumps(norm(value), separators=(",", ":"), ensure_ascii=False)


def body_key(value: Any) -> str:
    """FNV-1a 32-bit over the canonical form's UTF-16 code units, as 8 hex digits."""
    h = 0x811C9DC5
    data = canonical(value).encode("utf-16-le")
    for i in range(0, len(data), 2):
        h ^= data[i] | (data[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"
