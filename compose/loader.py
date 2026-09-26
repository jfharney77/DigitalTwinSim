"""Load several component backends at once, each under a private package name.

Every component's backend package is called ``app``. The root test suite
handles that by letting backends take turns holding the name
(``twinkit.testing.claim_backend``). Composition needs two or more engines
alive in the same call, so turn-taking is not enough: this module imports
``<Component>/backend/app`` as the package ``_twin_<Component>`` instead.

Every engine in scope uses relative imports (``from .constants import ...``),
so its modules resolve inside the private package and never touch the name
``app``. The loader never reads or writes ``sys.modules["app"]``.

This is the only module under ``compose/`` that uses importlib.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import pathlib
import sys
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Callable

REPO = pathlib.Path(__file__).resolve().parent.parent

#: The engines the couplings read. Anything else is refused by name.
COMPONENTS = (
    "PhysicsCompute",
    "PhysicsCDU",
    "PhysicsStorage",
    "PhysicsFabric",
    "PhysicsAIFactory",
    "PhysicsRackPower",
    "PhysicsResilience",
    "PhysicsDataDomain",
    "PhysicsXR",
    "PhysicsFleet",
    "DellPowerEdgeR760Thermal",
)

#: Modules of a backend the couplings need. ``main`` is never loaded: it
#: imports FastAPI and is the component's own impure edge.
_NEEDED = ("models", "constants", "engine", "validation")


class AbsoluteAppImport(ImportError):
    """A backend module says ``import app...`` instead of ``from . import``.

    Loaded under a private name, that import would bind to whichever component
    currently holds ``app`` in ``sys.modules`` — silently another engine's
    models. The loader refuses instead.
    """


@dataclass(frozen=True)
class EngineHandle:
    component: str
    package: str
    models: ModuleType
    constants: ModuleType
    engine: ModuleType
    validation: ModuleType | None

    @property
    def simulate(self) -> Callable[..., Any]:
        return self.engine.simulate

    @property
    def Scenario(self) -> Any:  # noqa: N802 - mirrors the class it returns
        return self.models.Scenario

    @property
    def SimEvent(self) -> Any:  # noqa: N802
        return self.models.SimEvent

    def C(self, name: str) -> float:  # noqa: N802 - the engines' own spelling
        return self.constants.value(name)

    def constant(self, name: str) -> Any:
        return self.constants.CONSTANTS[name]

    def validate(self, scenario: Any) -> list[Any]:
        if self.validation is None:
            return []
        return list(self.validation.validate(scenario))


_CACHE: dict[str, EngineHandle] = {}


def _check_no_absolute_app_import(path: pathlib.Path, component: str) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names = [node.module]
        for name in names:
            if name == "app" or name.startswith("app."):
                raise AbsoluteAppImport(
                    f"{component}: {path.name} imports {name!r} absolutely; under a "
                    "private package name that would bind to another component's "
                    "`app`. Use a relative import."
                )


def backend_app_dir(component: str, repo: pathlib.Path | None = None) -> pathlib.Path:
    return (repo or REPO) / component / "backend" / "app"


def load_engine(component: str, repo: pathlib.Path | None = None) -> EngineHandle:
    """Import ``<component>/backend/app`` as the package ``_twin_<component>``."""
    key = component if repo is None else f"{repo}:{component}"
    if key in _CACHE:
        return _CACHE[key]
    if repo is None and component not in COMPONENTS:
        raise KeyError(f"{component!r} is not an engine the composition layer reads")
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))  # engines import twinkit.models

    app_dir = backend_app_dir(component, repo)
    init = app_dir / "__init__.py"
    if not init.exists():
        raise FileNotFoundError(f"{component}: no backend/app package at {app_dir}")
    for mod in _NEEDED:
        path = app_dir / f"{mod}.py"
        if path.exists():
            _check_no_absolute_app_import(path, component)

    package = "_twin_" + component.replace("-", "_")
    if package not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            package, init, submodule_search_locations=[str(app_dir)]
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[package] = module
        spec.loader.exec_module(module)

    def sub(name: str) -> ModuleType | None:
        if not (app_dir / f"{name}.py").exists():
            return None
        return importlib.import_module(f"{package}.{name}")

    models, constants, engine = sub("models"), sub("constants"), sub("engine")
    assert models is not None and constants is not None and engine is not None
    handle = EngineHandle(
        component=component,
        package=package,
        models=models,
        constants=constants,
        engine=engine,
        validation=sub("validation"),
    )
    _CACHE[key] = handle
    return handle
