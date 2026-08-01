"""Integrity tests for the CustomerSetup pages.

Static documents drift: twins get renamed, ports get reassigned, spec files
move. These tests pin every cross-reference a setup page makes to something
that actually exists in the repo, so the drift surfaces here instead of as a
dead link in a browser.

Run with either:
    python3 CustomerSetup/tests/test_links.py
    pytest -q CustomerSetup/tests/test_links.py
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SETUP_DIR = ROOT / "CustomerSetup"

SETUP_PAGES = sorted(SETUP_DIR.glob("*/setup.html"))
READMES = sorted(SETUP_DIR.glob("*/README.md"))
INDEX = SETUP_DIR / "index.html"


def _fail(msgs):
    raise AssertionError("\n".join(msgs))


def test_layout():
    """Every customer folder has both files; shared assets and index exist."""
    problems = []
    if not SETUP_PAGES:
        problems.append("no setup.html pages found")
    if not INDEX.exists():
        problems.append("CustomerSetup/index.html missing")
    for asset in ("shared/setup.css", "shared/setup.js"):
        if not (SETUP_DIR / asset).exists():
            problems.append(f"CustomerSetup/{asset} missing")
    for page in SETUP_PAGES:
        if not (page.parent / "README.md").exists():
            problems.append(f"{page.parent.name}/README.md missing")
    for readme in READMES:
        if not (readme.parent / "setup.html").exists():
            problems.append(f"{readme.parent.name}/setup.html missing")
    if problems:
        _fail(problems)


def test_twin_dirs_and_ports():
    """Every data-twin-start dir exists, and its data-twin-port matches the
    port in that twin's vite.config.ts."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        for port, start in re.findall(
            r'data-twin-port="(\d+)"\s+data-twin-start="([^"]+)"', html
        ):
            twin = ROOT / start
            if not twin.is_dir():
                problems.append(f"{page.parent.name}: twin dir {start} does not exist")
                continue
            vite = twin / "frontend" / "vite.config.ts"
            if not vite.exists():
                problems.append(f"{page.parent.name}: {start} has no vite.config.ts")
                continue
            m = re.search(r"port:\s*(\d+)", vite.read_text())
            if not m:
                problems.append(f"{page.parent.name}: no port in {start}'s vite.config.ts")
            elif m.group(1) != port:
                problems.append(
                    f"{page.parent.name}: links {start} at :{port} "
                    f"but vite.config.ts says :{m.group(1)}"
                )
    if problems:
        _fail(problems)


def _scan_twin_ports():
    """Read every twin's actual ports from disk (vite config + backend script)."""
    twins = {}
    for d in sorted(ROOT.iterdir()):
        if not d.is_dir() or d.name.startswith(".") or d.name == "CustomerSetup":
            continue
        entry = {}
        vite = d / "frontend" / "vite.config.ts"
        back = d / "scripts" / "start_backend.sh"
        if vite.exists():
            t = vite.read_text()
            m = re.search(r"port:\s*(\d+)", t)
            if m:
                entry["frontend"] = int(m.group(1))
            m = re.search(r"target:[^,]*?localhost:(\d+)", t)
            if m:
                entry["proxyDefault"] = int(m.group(1))
        if back.exists():
            m = re.search(r"--port\s+(\d+)", back.read_text())
            if m:
                entry["backend"] = int(m.group(1))
        if entry:
            twins[d.name] = entry
    return twins


def test_ports_registry():
    """ports.json at the repo root is the port registry: it must match what is
    actually on disk, every vite proxy default must point at its own backend,
    and no port may be shared beyond the registry's knownCollisions."""
    problems = []
    reg_path = ROOT / "ports.json"
    if not reg_path.exists():
        _fail(["ports.json missing at repo root"])
    reg = json.loads(reg_path.read_text())
    actual = _scan_twin_ports()

    for name, ports in actual.items():
        if name not in reg["twins"]:
            problems.append(f"ports.json: missing twin {name}")
        elif reg["twins"][name] != ports:
            problems.append(
                f"ports.json: {name} says {reg['twins'][name]}, disk says {ports}"
            )
    for name in reg["twins"]:
        if name not in actual:
            problems.append(f"ports.json: lists {name}, which has no ports on disk")

    for name, ports in actual.items():
        if "proxyDefault" in ports and ports.get("proxyDefault") != ports.get("backend"):
            problems.append(
                f"{name}: vite proxies /api to :{ports['proxyDefault']} "
                f"but its backend runs on :{ports.get('backend')}"
            )

    known = {k: sorted(v) for k, v in reg.get("knownCollisions", {}).items()}
    coll = defaultdict(list)
    for name, ports in actual.items():
        for kind in ("frontend", "backend"):
            if kind in ports:
                coll[f"{kind}:{ports[kind]}"].append(name)
    for key, names in sorted(coll.items()):
        if len(names) > 1 and known.get(key) != sorted(names):
            problems.append(f"NEW port collision {key}: {sorted(names)}")
    if problems:
        _fail(problems)


def test_localhost_links_have_metadata():
    """Every distinct localhost port a page links carries chip metadata
    somewhere on that page (so the liveness chip and start-hint can render)."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        linked = set(re.findall(r'href="http://localhost:(\d+)/', html))
        tagged = set(re.findall(r'data-twin-port="(\d+)"', html))
        for port in sorted(linked - tagged):
            problems.append(
                f"{page.parent.name}: links localhost:{port} but no link to that "
                f"port carries data-twin-port/data-twin-start"
            )
    if problems:
        _fail(problems)


def test_relative_links_resolve():
    """Relative hrefs (spec files, index, shared assets) must resolve."""
    problems = []
    for page in list(SETUP_PAGES) + [INDEX]:
        html = page.read_text()
        refs = re.findall(r'(?:href|src)="([^"#]+)(?:#[^"]*)?"', html)
        for ref in refs:
            if ref.startswith(("http://", "https://", "mailto:")):
                continue
            target = (page.parent / ref).resolve()
            if not target.exists():
                problems.append(f"{page.parent.name}/{page.name}: broken relative link {ref}")
    if problems:
        _fail(problems)


def test_phase_links_name_real_phases():
    """Every #phase=<name> link names a phase that appears in that twin's
    backend engine.py — the deep link would otherwise silently no-op."""
    problems = []
    port_to_twin = {}
    for page in SETUP_PAGES:
        html = page.read_text()
        for port, start in re.findall(
            r'data-twin-port="(\d+)"\s+data-twin-start="([^"]+)"', html
        ):
            port_to_twin[port] = start
        for port, phase in re.findall(
            r'href="http://localhost:(\d+)/#phase=([a-z0-9_-]+)"', html
        ):
            twin = port_to_twin.get(port)
            if twin is None:
                problems.append(
                    f"{page.parent.name}: #phase link on :{port} but no twin metadata for that port"
                )
                continue
            engine = ROOT / twin / "backend" / "app" / "engine.py"
            if not engine.exists():
                problems.append(f"{page.parent.name}: {twin} has no backend/app/engine.py")
                continue
            if f'"{phase}"' not in engine.read_text():
                problems.append(
                    f"{page.parent.name}: links {twin} #phase={phase}, "
                    f"not found in its engine.py"
                )
    if problems:
        _fail(problems)


def test_pages_carry_the_contract():
    """Each setup page keeps the honesty features: sources, a note box,
    basis tags, a walkthrough, and both reading registers."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        name = page.parent.name
        if "https://" not in html:
            problems.append(f"{name}: no source URLs")
        if 'class="note"' not in html:
            problems.append(f"{name}: no note box separating fact from illustration")
        if 'class="basis' not in html:
            problems.append(f"{name}: no basis (sourced/inferred/representative) tags")
        if "window.WALKTHROUGH" not in html or 'id="walkthrough"' not in html:
            problems.append(f"{name}: no walkthrough")
        if "lvl-novice" not in html or "lvl-standard" not in html:
            problems.append(f"{name}: missing a reading register")
    if problems:
        _fail(problems)


def test_walkthrough_focus_names_exist():
    """Every walkthrough step's focus names must match a data-wt group in the
    page's SVG — a typo would silently dim the whole diagram."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        groups = set(re.findall(r'data-wt="([a-z-]+)"', html))
        wt = re.search(r"window\.WALKTHROUGH\s*=\s*\[(.*?)\];", html, re.S)
        if not wt:
            continue
        for focus_list in re.findall(r"focus:\s*\[(.*?)\]", wt.group(1), re.S):
            for name in re.findall(r'"([a-z-]+)"', focus_list):
                if name not in groups:
                    problems.append(
                        f"{page.parent.name}: walkthrough focuses '{name}' "
                        f"but the SVG has no data-wt=\"{name}\" group"
                    )
    if problems:
        _fail(problems)


def test_row_refs_name_real_groups():
    """Every table row's data-wt-ref must name real data-wt SVG groups, and
    every setup page must have at least one cross-linked row."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        groups = set(re.findall(r'data-wt="([a-z-]+)"', html))
        refs = re.findall(r'data-wt-ref="([a-z,-]+)"', html)
        if not refs:
            problems.append(f"{page.parent.name}: no data-wt-ref cross-linked rows")
        for ref in refs:
            for name in ref.split(","):
                if name not in groups:
                    problems.append(
                        f"{page.parent.name}: row references '{name}' "
                        f"but the SVG has no data-wt=\"{name}\" group"
                    )
    if problems:
        _fail(problems)


def test_trace_endpoints_exist():
    """Every data-twin-trace endpoint must be a route in that twin's
    backend main.py — the chip enrichment would otherwise 404 quietly."""
    problems = []
    for page in SETUP_PAGES:
        html = page.read_text()
        for start, trace in re.findall(
            r'data-twin-start="([^"]+)" data-twin-trace="([^"]+)"', html
        ):
            main = ROOT / start / "backend" / "app" / "main.py"
            if not main.exists():
                problems.append(f"{page.parent.name}: {start} has no backend/app/main.py")
                continue
            if f"/api/{trace}" not in main.read_text():
                problems.append(
                    f"{page.parent.name}: {start} tagged with trace endpoint "
                    f"/api/{trace}, not found in its main.py"
                )
    if problems:
        _fail(problems)


def test_sources_are_archived():
    """Every source URL a page or README cites has an entry in the folder's
    sources.json (title, publisher, dateAccessed, supported claims) — so the
    citation survives link rot, and so every URL earns its place by naming
    what it supports."""
    problems = []
    for page in SETUP_PAGES:
        folder = page.parent
        sj = folder / "sources.json"
        if not sj.exists():
            problems.append(f"{folder.name}: no sources.json")
            continue
        entries = json.loads(sj.read_text())
        archived = {e["url"] for e in entries}
        for e in entries:
            for field in ("url", "title", "publisher", "dateAccessed", "supports"):
                if not e.get(field):
                    problems.append(f"{folder.name}: sources.json entry missing {field}")
        cited = set()
        m = re.search(r"<h2>Sources</h2>\s*<ul>(.*?)</ul>", page.read_text(), re.S)
        if m:
            cited |= set(re.findall(r'href="(https?://[^"]+)"', m.group(1)))
        readme = folder / "README.md"
        if readme.exists():
            in_sources = False
            for line in readme.read_text().splitlines():
                if line.strip().startswith("Sources"):
                    in_sources = True
                elif in_sources and line.strip().startswith("- http"):
                    cited.add(line.strip()[2:])
        for url in sorted(cited - archived):
            problems.append(f"{folder.name}: cites {url} but sources.json has no entry")
    if problems:
        _fail(problems)


def test_readmes_cite_sources():
    problems = []
    for readme in READMES:
        if "https://" not in readme.read_text():
            problems.append(f"{readme.parent.name}/README.md: no source URLs")
    if problems:
        _fail(problems)


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_")]

if __name__ == "__main__":
    failed = 0
    for test in TESTS:
        try:
            test()
            print(f"ok   {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {test.__name__}\n{e}")
    sys.exit(1 if failed else 0)
