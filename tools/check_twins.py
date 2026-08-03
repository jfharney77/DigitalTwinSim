#!/usr/bin/env python3
"""Cross-twin contract linter.

Every twin in this repo follows one pattern: a pure-engine FastAPI backend, a
React/Vite frontend in the Dell clean-design skin, four lifecycle scripts, the
shared reading-level mechanism, and a registered port pair. Individual twins
test their own invariants; nothing tests the pattern itself — a new twin can
silently ship without a stop script or with an unregistered port. This linter
locks the pattern in.

Run: python3 tools/check_twins.py   (exit 0 = every twin conforms)
"""

import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BACKEND_MODULES = ("models.py", "engine.py", "main.py", "leveling.py")
SCRIPTS = ("start_backend.sh", "start_frontend.sh", "start_all.sh", "stop_all.sh")
# Modules a pure engine must never import (the twins' own AST tests go
# further; this is the pattern-level echo so a twin without that test
# still gets caught).
IMPURE = {"fastapi", "uvicorn", "time", "asyncio", "threading", "socket", "requests"}


def check_twin(name, ports, problems):
    twin = ROOT / name
    backend = twin / "backend"
    frontend = twin / "frontend"

    for mod in BACKEND_MODULES:
        if not (backend / "app" / mod).exists():
            problems.append(f"{name}: missing backend/app/{mod}")
    tests = list((backend / "tests").glob("test_*.py"))
    if not tests:
        problems.append(f"{name}: no backend tests")

    engine = backend / "app" / "engine.py"
    if engine.exists():
        try:
            tree = ast.parse(engine.read_text())
        except SyntaxError as e:
            problems.append(f"{name}: engine.py does not parse ({e})")
        else:
            for node in ast.walk(tree):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods = [node.module.split(".")[0]]
                for m in mods:
                    if m in IMPURE:
                        problems.append(f"{name}: engine.py imports {m} — engines are pure")

    for script in SCRIPTS:
        path = twin / "scripts" / script
        if not path.exists():
            problems.append(f"{name}: missing scripts/{script}")
        elif not path.stat().st_mode & 0o111:
            problems.append(f"{name}: scripts/{script} is not executable")

    vite = frontend / "vite.config.ts"
    if not vite.exists():
        problems.append(f"{name}: missing frontend/vite.config.ts")
    else:
        t = vite.read_text()
        m = re.search(r"port:\s*(\d+)", t)
        if not m or int(m.group(1)) != ports.get("frontend"):
            problems.append(
                f"{name}: vite port {m.group(1) if m else '?'} != "
                f"registry {ports.get('frontend')}"
            )
    if not (frontend / "src" / "level.ts").exists():
        problems.append(f"{name}: missing frontend/src/level.ts (reading-level store)")
    if not (frontend / "src" / "components" / "LevelControl.tsx").exists():
        problems.append(f"{name}: missing LevelControl.tsx")

    back_script = twin / "scripts" / "start_backend.sh"
    if back_script.exists():
        m = re.search(r"--port\s+(\d+)", back_script.read_text())
        if not m or int(m.group(1)) != ports.get("backend"):
            problems.append(
                f"{name}: backend port {m.group(1) if m else '?'} != "
                f"registry {ports.get('backend')}"
            )


def check_hub(registry, problems):
    hub = ROOT / "index.html"
    if not hub.exists():
        problems.append("repo-root index.html (landing hub) missing")
        return
    t = hub.read_text()
    for name in registry:
        if f'"{name}"' not in t:
            problems.append(f"index.html: hub does not list {name}")


def main():
    problems = []
    reg_path = ROOT / "ports.json"
    if not reg_path.exists():
        print("FAIL: ports.json missing")
        return 1
    registry = json.loads(reg_path.read_text())["twins"]

    # Every twin directory with a backend must be in the registry, and
    # vice versa — the registry and the filesystem describe the same repo.
    on_disk = {
        d.name for d in ROOT.iterdir()
        if d.is_dir() and (d / "backend" / "app").is_dir() and d.name != "CustomerSetup"
    }
    for name in sorted(on_disk - set(registry)):
        problems.append(f"{name}: built twin not in ports.json")
    for name in sorted(set(registry) - on_disk):
        problems.append(f"{name}: in ports.json but no backend on disk")

    for name in sorted(registry):
        if name in on_disk:
            check_twin(name, registry[name], problems)
    check_hub(registry, problems)

    if problems:
        print(f"FAIL — {len(problems)} problem(s):")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"ok — {len(on_disk)} twins conform to the pattern")
    return 0


if __name__ == "__main__":
    sys.exit(main())
