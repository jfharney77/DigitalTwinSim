"""A stand-in for ``fastapi`` when a component backend runs with no server.

Static hosting (docs/STATIC_HOSTING.md) runs a scenario-driven component's
real ``app/main.py`` inside the browser under Pyodide. Pyodide ships pydantic
but not FastAPI, and installing it from PyPI on every first visit costs
seconds and a second origin. A component's ``main.py`` only uses FastAPI to
*declare* routes; :mod:`twinkit.static_dispatch` calls the endpoint functions
directly. So all the stub has to do is remember the declarations.

    from twinkit.fastapi_stub import install
    install()            # before anything imports fastapi
    import app.main      # make_app(), @app.get, @app.post all work

Only the declaration surface is covered: ``FastAPI``, ``Query``/``Path``/
``Body``, ``HTTPException``, ``add_middleware`` and the CORS import. A
component that needs more (streaming, uploads, ``Request``) cannot be served
this way — the GPU twin's live tab is the known case.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Callable


class HTTPException(Exception):
    def __init__(self, status_code: int, detail: Any = None, **_: Any) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class Param:
    """What ``Query(3, ge=1, le=5)`` leaves behind: the default and bounds."""

    def __init__(self, default: Any = ..., **kwargs: Any) -> None:
        self.default = default
        self.ge = kwargs.get("ge")
        self.le = kwargs.get("le")
        self.gt = kwargs.get("gt")
        self.lt = kwargs.get("lt")


def Query(default: Any = ..., **kwargs: Any) -> Any:  # noqa: N802 - FastAPI's name
    return Param(default, **kwargs)


Path = Body = Query


class Route:
    def __init__(self, path: str, methods: set[str], endpoint: Callable[..., Any],
                 response_model: Any = None) -> None:
        self.path = path
        self.methods = methods
        self.endpoint = endpoint
        self.response_model = response_model


class FastAPI:
    def __init__(self, **kwargs: Any) -> None:
        self.title = kwargs.get("title", "")
        self.version = kwargs.get("version", "")
        self.routes: list[Route] = []

    def _declare(self, method: str) -> Callable[..., Any]:
        def declare(path: str, response_model: Any = None, **_: Any) -> Callable[..., Any]:
            def register(fn: Callable[..., Any]) -> Callable[..., Any]:
                self.routes.append(Route(path, {method}, fn, response_model))
                return fn
            return register
        return declare

    def __getattr__(self, name: str) -> Any:
        if name in ("get", "post", "put", "delete", "patch"):
            return self._declare(name.upper())
        raise AttributeError(name)

    def add_middleware(self, *_: Any, **__: Any) -> None:
        return None


class CORSMiddleware:  # accepted by add_middleware and ignored
    pass


def install() -> None:
    """Register the stub as ``fastapi`` — a no-op if the real one is importable
    already, so native runs keep using FastAPI itself."""
    if "fastapi" in sys.modules:
        return
    fastapi = types.ModuleType("fastapi")
    fastapi.FastAPI = FastAPI  # type: ignore[attr-defined]
    fastapi.Query = Query  # type: ignore[attr-defined]
    fastapi.Path = Path  # type: ignore[attr-defined]
    fastapi.Body = Body  # type: ignore[attr-defined]
    fastapi.HTTPException = HTTPException  # type: ignore[attr-defined]
    middleware = types.ModuleType("fastapi.middleware")
    cors = types.ModuleType("fastapi.middleware.cors")
    cors.CORSMiddleware = CORSMiddleware  # type: ignore[attr-defined]
    middleware.cors = cors  # type: ignore[attr-defined]
    fastapi.middleware = middleware  # type: ignore[attr-defined]
    sys.modules["fastapi"] = fastapi
    sys.modules["fastapi.middleware"] = middleware
    sys.modules["fastapi.middleware.cors"] = cors
