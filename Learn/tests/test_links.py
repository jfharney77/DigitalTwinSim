"""Integrity tests for the Learn course.

The course is a thin layer of questions over the twins, and every question
leans on something the twins do: a phase name, a tour beat, a guided
scenario, a pytest case, a number on a particular step. Each of those can
change under the course without anyone opening it, so each one is pinned
here against the code, and the drift fails this file instead of turning into
a dead link or a wrong answer in front of a reader.

Run with either:
    python3 Learn/tests/test_links.py
    pytest -q Learn
"""

import ast
import importlib.util
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARN = ROOT / "Learn"
COURSE_JS = LEARN / "course.js"
LEARN_PORT = 5172

PREFIX = "window.COURSE = "


def _fail(msgs):
    raise AssertionError("\n".join(msgs))


@lru_cache(maxsize=None)
def course():
    text = COURSE_JS.read_text()
    start = text.index(PREFIX) + len(PREFIX)
    body = text[start:].rstrip()
    assert body.endswith(";"), "course.js must end with `;`"
    return json.loads(body[:-1])


def modules():
    return course()["modules"]


def entries():
    for m in modules():
        for e in m["entries"]:
            yield m, e


def links(kind=None):
    for m, e in entries():
        for link in e["links"]:
            if kind is None or link["kind"] == kind:
                yield m, e, link


def texts(value):
    """A text field is a plain string or {standard, novice}."""
    if isinstance(value, dict):
        return [value.get("standard", ""), value.get("novice", "")]
    return [value]


@lru_cache(maxsize=None)
def gen_pages():
    spec = importlib.util.spec_from_file_location("learn_gen_pages", LEARN / "scripts" / "gen_pages.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---- layout ---------------------------------------------------------------

def test_layout():
    """The files the README promises exist, and every page loads course.js,
    then learn.js, then the shared setup.js. The order is load-bearing:
    setup.js wires the liveness chips on DOMContentLoaded, so the links must
    already be in the DOM, which means learn.js has to render first."""
    problems = []
    for rel in ("index.html", "course.js", "learn.js", "learn.css", "README.md",
                "scripts/serve.sh", "scripts/gen_pages.py"):
        if not (LEARN / rel).exists():
            problems.append(f"Learn/{rel} missing")
    pages = [LEARN / "index.html"] + sorted((LEARN / "modules").glob("*.html"))
    for page in pages:
        html = page.read_text()
        order = [html.find(s) for s in ("course.js", "learn.js", "CustomerSetup/shared/setup.js")]
        if -1 in order or order != sorted(order):
            problems.append(f"{page.relative_to(ROOT)}: must load course.js, learn.js, setup.js in that order")
        if "CustomerSetup/shared/setup.css" not in html or "learn.css" not in html:
            problems.append(f"{page.relative_to(ROOT)}: must link setup.css and learn.css")
        if 'name="viewport"' not in html:
            problems.append(f"{page.relative_to(ROOT)}: no viewport meta (phones)")
        for ref in re.findall(r'(?:href|src)="([^"#:]+)(?:#[^"]*)?"', html):
            if not (page.parent / ref).resolve().exists():
                problems.append(f"{page.relative_to(ROOT)}: broken relative link {ref}")
    if problems:
        _fail(problems)


def test_module_pages_are_generated():
    """One page per module, each the generated shell for its id, and no
    orphan pages for modules that no longer exist."""
    problems = []
    gp = gen_pages()
    want = {m["id"]: gp.page(m) for m in modules()}
    have = {p.stem: p for p in (LEARN / "modules").glob("*.html")}
    for mid, html in want.items():
        name = gp.filename(mid)
        path = LEARN / "modules" / name
        if not path.exists():
            problems.append(f"Learn/modules/{name} missing (run python3 Learn/scripts/gen_pages.py)")
        elif path.read_text() != html:
            problems.append(f"Learn/modules/{name} is stale (run python3 Learn/scripts/gen_pages.py)")
    expected = {Path(gp.filename(mid)).stem for mid in want}
    for stem in sorted(set(have) - expected):
        problems.append(f"Learn/modules/{stem}.html has no module in course.js")
    if problems:
        _fail(problems)


# ---- ports ----------------------------------------------------------------

def test_ports_match_registry():
    """Each entry's port is the twin's frontend port in ports.json, and the
    twin is a real top-level directory."""
    reg = json.loads((ROOT / "ports.json").read_text())["twins"]
    problems = []
    for m, e in entries():
        twin = e["twin"]
        if not (ROOT / twin).is_dir():
            problems.append(f"{m['id']}: {twin} is not a directory")
            continue
        if twin == "CustomerSetup":
            if "port" in e:
                problems.append(f"{m['id']}: CustomerSetup links are relative, give no port")
            continue
        if twin not in reg:
            problems.append(f"{m['id']}: {twin} is not in ports.json")
        elif reg[twin]["frontend"] != e.get("port"):
            problems.append(f"{m['id']}: {twin} at :{e.get('port')}, ports.json says :{reg[twin]['frontend']}")
    if problems:
        _fail(problems)


def test_reserved_port():
    """5172 is reserved for these pages, the serve script uses it, and no
    twin's frontend or backend sits on it."""
    reg = json.loads((ROOT / "ports.json").read_text())
    problems = []
    if reg.get("reserved", {}).get("learnPages") != LEARN_PORT:
        problems.append(f"ports.json reserved.learnPages must be {LEARN_PORT}")
    if str(LEARN_PORT) not in (LEARN / "scripts" / "serve.sh").read_text():
        problems.append(f"Learn/scripts/serve.sh does not use {LEARN_PORT}")
    for name, ports in reg["twins"].items():
        if LEARN_PORT in (ports.get("frontend"), ports.get("backend")):
            problems.append(f"{name} uses {LEARN_PORT}")
    if problems:
        _fail(problems)


# ---- deep links -----------------------------------------------------------

def _engine_text(twin):
    return (ROOT / twin / "backend" / "app" / "engine.py").read_text()


def test_phase_links_name_real_phases():
    """#phase=<name> names a phase string in the twin's engine.py; the twin's
    App.tsx would otherwise fall back to step 0 without a word."""
    problems = []
    for m, e, link in links("phase"):
        if f'"{link["value"]}"' not in _engine_text(e["twin"]):
            problems.append(f"{m['id']}: {e['twin']} #phase={link['value']} is not in its engine.py")
    for m, e, link in links("step"):
        if f'"{link["expectPhase"]}"' not in _engine_text(e["twin"]):
            problems.append(f"{m['id']}: {e['twin']} #step expects phase {link['expectPhase']}, not in engine.py")
    if problems:
        _fail(problems)


@lru_cache(maxsize=None)
def trace_of(twin):
    """The twin's default trace as plain dicts, computed with the twin's own
    interpreter (each backend has its own venv and its own `app` package).
    None when the venv is absent, so a fresh clone skips instead of failing."""
    backend = ROOT / twin / "backend"
    py = backend / ".venv" / "bin" / "python"
    if not py.exists():
        return None
    code = (
        "import json\n"
        "from app.engine import simulate\n"
        "print(json.dumps([s.model_dump(mode='json') for s in simulate()]))\n"
    )
    out = subprocess.run([str(py), "-c", code], cwd=backend, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(f"{twin}: simulate() failed:\n{out.stderr[-800:]}")
    return json.loads(out.stdout)


def test_step_links_land_on_the_expected_phase():
    """#step=N is only as good as N: the step must exist and sit in the phase
    the course says it does."""
    problems, checked = [], 0
    for m, e, link in links("step"):
        trace = trace_of(e["twin"])
        if trace is None:
            continue
        checked += 1
        n = link["value"]
        if not 0 <= n < len(trace):
            problems.append(f"{m['id']}: {e['twin']} #step={n} is past the last step ({len(trace) - 1})")
        elif trace[n]["phase"] != link["expectPhase"]:
            problems.append(
                f"{m['id']}: {e['twin']} #step={n} is phase {trace[n]['phase']}, course expects {link['expectPhase']}"
            )
    if problems:
        _fail(problems)


def tour_step_ids(path):
    """Every TourStep(id=...) in a tour.py, resolving a module-level constant
    such as id=SIGNATURE_STEP_ID."""
    tree = ast.parse(path.read_text())
    consts = {}
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)) and isinstance(getattr(node, "value", None), ast.Constant):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    consts[t.id] = node.value.value
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "TourStep":
            for kw in node.keywords:
                if kw.arg != "id":
                    continue
                if isinstance(kw.value, ast.Constant):
                    ids.add(kw.value.value)
                elif isinstance(kw.value, ast.Name) and kw.value.id in consts:
                    ids.add(consts[kw.value.id])
    return ids


def test_tour_ids_exist():
    """#tour/<id> names a TourStep in the twin's tour.py, and the twin's
    App.tsx parses the #tour/ route."""
    problems = []
    for m, e, link in links("tour"):
        tour = ROOT / e["twin"] / "backend" / "app" / "tour.py"
        app = ROOT / e["twin"] / "frontend" / "src" / "App.tsx"
        if not tour.exists():
            problems.append(f"{m['id']}: {e['twin']} has no tour.py")
            continue
        if link["id"] not in tour_step_ids(tour):
            problems.append(f"{m['id']}: {e['twin']} #tour/{link['id']} is not a TourStep id in tour.py")
        if "#tour" not in app.read_text():
            problems.append(f"{m['id']}: {e['twin']} App.tsx does not handle #tour/<id>")
    if problems:
        _fail(problems)


def test_twins_with_tours_link_one():
    """A narrative twin that has grown a tour should be entered through it:
    if a module links a twin by #phase/#step only and the twin now has a
    tour, the course is behind."""
    problems = []
    for m, e in entries():
        kinds = {link["kind"] for link in e["links"]}
        has_tour = (ROOT / e["twin"] / "backend" / "app" / "tour.py").exists()
        if has_tour and kinds & {"phase", "step"} and "tour" not in kinds:
            problems.append(f"{m['id']}: {e['twin']} has a tour.py; add a tour link")
    if problems:
        _fail(problems)


def test_gpu_lesson_ids_exist():
    """The GPU lesson-tour link opens #live/tour at the first lesson; the
    lesson it tells the reader to step to must still exist."""
    problems = []
    for m, e, link in links("lesson"):
        ids = tour_step_ids(ROOT / e["twin"] / "backend" / "app" / "tour.py")
        if link["lesson"] not in ids:
            problems.append(f"{m['id']}: lesson {link['lesson']} is not in {e['twin']}'s tour.py")
        if link["hash"] != "#live/tour":
            problems.append(f"{m['id']}: lesson links open #live/tour")
    if problems:
        _fail(problems)


@lru_cache(maxsize=None)
def guided_scenarios(app):
    """{id: title} for every GuidedScenario(...) in the app's presets.py."""
    tree = ast.parse((ROOT / app / "backend" / "app" / "presets.py").read_text())
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "GuidedScenario":
            kw = {k.arg: k.value for k in node.keywords}
            if isinstance(kw.get("id"), ast.Constant):
                title = kw.get("title")
                found[kw["id"].value] = title.value if isinstance(title, ast.Constant) else None
    return found


def test_scenario_ids_and_titles():
    """#scenario=<id> names a GuidedScenario in presets.py, its title matches
    (the page tells the reader what to look for by title), and the app's
    App.tsx reads #scenario= from the hash."""
    problems = []
    for m, e, link in links("scenario"):
        found = guided_scenarios(e["twin"])
        if link["id"] not in found:
            problems.append(f"{m['id']}: {e['twin']} has no guided scenario {link['id']}")
        elif found[link["id"]] != link["title"]:
            problems.append(
                f"{m['id']}: {e['twin']} scenario {link['id']} is titled {found[link['id']]!r}, course says {link['title']!r}"
            )
        app = (ROOT / e["twin"] / "frontend" / "src" / "App.tsx").read_text()
        if "#scenario=" not in app and "scenario=" not in app:
            problems.append(f"{m['id']}: {e['twin']} App.tsx does not read #scenario=")
    if problems:
        _fail(problems)


def test_setup_links_resolve():
    """The capstone's CustomerSetup links point at real setup pages."""
    problems = []
    for m, e, link in links("setup"):
        if not (ROOT / "CustomerSetup" / link["path"]).exists():
            problems.append(f"{m['id']}: CustomerSetup/{link['path']} does not exist")
    if problems:
        _fail(problems)


def test_link_kinds_are_known():
    known = {"tour", "phase", "step", "scenario", "root", "lesson", "setup"}
    problems = [f"{m['id']}: unknown link kind {link['kind']}" for m, e, link in links() if link["kind"] not in known]
    if problems:
        _fail(problems)


def test_trace_endpoints_exist():
    """data-twin-trace values name a GET route in the twin's main.py, so the
    liveness chip can read the step count and phase span."""
    problems = []
    for m, e in entries():
        if "trace" not in e:
            continue
        main = ROOT / e["twin"] / "backend" / "app" / "main.py"
        if f'"/api/{e["trace"]}"' not in main.read_text():
            problems.append(f"{m['id']}: {e['twin']} has no /api/{e['trace']} in main.py")
    if problems:
        _fail(problems)


# ---- answers --------------------------------------------------------------

def _all_cites():
    for m in modules():
        for c in m["predict"]["cite"]:
            yield m, c
        for check in m["checks"]:
            for c in check["cite"]:
                yield m, c


def test_cites_resolve():
    """Every `path::test_name` cite names a test that exists. An answer is
    only as good as the test that settles it."""
    problems = []
    for m, cite in _all_cites():
        path, _, name = cite.partition("::")
        f = ROOT / path
        if not f.exists():
            problems.append(f"{m['id']}: cite file {path} missing")
        elif not name or not re.search(rf"^def {re.escape(name)}\(", f.read_text(), re.M):
            problems.append(f"{m['id']}: {path} has no test {name}")
    if problems:
        _fail(problems)


def test_quoted_numbers():
    """The numbers the answers quote are read off the twins' traces here,
    through each twin's own interpreter. A changed engine fails this test in
    the same run that changes the component's own test."""
    problems = []
    for m in modules():
        for pin in m.get("pins", []):
            trace = trace_of(pin["twin"])
            if trace is None:
                continue
            if "agg" in pin:
                got = max(s[pin["field"]] for s in trace)
                where = f"max {pin['field']}"
            else:
                if pin["step"] >= len(trace):
                    problems.append(f"{m['id']}: {pin['twin']} has no step {pin['step']}")
                    continue
                got = trace[pin["step"]][pin["field"]]
                where = f"step {pin['step']} {pin['field']}"
            if got != pin["value"]:
                problems.append(f"{m['id']}: {pin['twin']} {where} is {got}, course quotes {pin['value']}")
    if problems:
        _fail(problems)


# ---- structure ------------------------------------------------------------

def test_modules_and_tracks_consistent():
    problems = []
    ids = [m["id"] for m in modules()]
    if len(ids) != len(set(ids)):
        problems.append("module ids are not unique")
    known = set(ids)
    by_id = {m["id"]: m for m in modules()}
    for m in modules():
        for p in m["prereqs"]:
            if p not in known:
                problems.append(f"{m['id']}: prereq {p} is not a module")
        nxt = m["bridge"].get("next")
        if nxt is not None and nxt not in known:
            problems.append(f"{m['id']}: bridge.next {nxt} is not a module")

    # no cycles in prerequisites
    state = {}

    def visit(mid, stack):
        if state.get(mid) == "done":
            return
        if mid in stack:
            problems.append("prerequisite cycle: " + " > ".join(stack + [mid]))
            return
        for p in by_id.get(mid, {}).get("prereqs", []):
            visit(p, stack + [mid])
        state[mid] = "done"

    for mid in ids:
        visit(mid, [])

    track_ids = [t["id"] for t in course()["tracks"]]
    if len(track_ids) != len(set(track_ids)) or "full" not in track_ids:
        problems.append("track ids must be unique and include 'full'")
    for t in course()["tracks"]:
        for s in t["steps"]:
            if s["module"] not in known:
                problems.append(f"track {t['id']}: {s['module']} is not a module")
                continue
            twins = {e["twin"] for e in by_id[s["module"]]["entries"]}
            for only in s.get("only", []):
                if only not in twins:
                    problems.append(f"track {t['id']}: {s['module']} has no entry for {only}")
    core = [m["id"] for m in modules() if m["core"]]
    full = [s["module"] for s in course()["tracks"][track_ids.index("full")]["steps"]] if "full" in track_ids else []
    if full != core:
        problems.append("the full track must be every core module, in course order")
    in_a_track = {s["module"] for t in course()["tracks"] for s in t["steps"]}
    for mid in sorted(known - in_a_track):
        problems.append(f"{mid} is in no track, so no page links to it")
    if problems:
        _fail(problems)


def test_every_module_has_the_contract():
    """Predict with at least three options and a valid answer, evidence and
    a cite; two to four checks, each with a cite; both reading registers on
    the idea, the question, the reveal and the bridge; every link labeled."""
    problems = []
    for m in modules():
        mid = m["id"]
        p = m["predict"]
        if len(p["options"]) < 3:
            problems.append(f"{mid}: predict needs at least 3 options")
        if not 0 <= p["answer"] < len(p["options"]):
            problems.append(f"{mid}: predict answer index out of range")
        if not p["cite"]:
            problems.append(f"{mid}: predict has no cite")
        if not 2 <= len(m["checks"]) <= 4:
            problems.append(f"{mid}: needs 2 to 4 checks")
        for i, c in enumerate(m["checks"]):
            if not c.get("q") or not c.get("a") or not c.get("cite"):
                problems.append(f"{mid}: check {i} needs q, a and cite")
        for field, value in (("idea", m["idea"]), ("predict.q", p["q"]), ("predict.reveal", p["reveal"]),
                             ("bridge.text", m["bridge"]["text"])):
            if not isinstance(value, dict) or not value.get("standard") or not value.get("novice"):
                problems.append(f"{mid}: {field} needs both a standard and a novice register")
            elif value["standard"] == value["novice"]:
                problems.append(f"{mid}: {field} registers are identical")
        if not m["entries"]:
            problems.append(f"{mid}: no entry links")
        for e in m["entries"]:
            if not e.get("name"):
                problems.append(f"{mid}: {e['twin']} entry has no name")
            for link in e["links"]:
                if not link.get("label"):
                    problems.append(f"{mid}: a {link['kind']} link on {e['twin']} has no label")
        if m["core"] and len(m["objectives"]) < 2:
            problems.append(f"{mid}: core modules list at least 2 objectives")
    if problems:
        _fail(problems)


def test_clean_design_copy():
    """Dell clean design: no visible step numbering ("Step 3", "Module 7")
    in the authored text, and no "3 of 12" counter built by the renderer.
    (Quantities such as "4 of 7 snapshots" are content, not numbering.)"""
    problems = []
    pattern = re.compile(r"\b(Step \d|Module \d|Lesson \d)")
    blob = json.dumps(course(), ensure_ascii=False)
    for hit in pattern.findall(blob):
        problems.append(f"course.js: visible numbering {hit!r}")
    js = (LEARN / "learn.js").read_text()
    if re.search(r'" of "\s*\+|\+\s*" of "', js):
        problems.append("learn.js builds an 'N of M' counter")
    if problems:
        _fail(problems)


def test_root_index_links_learn():
    if 'href="Learn/index.html"' not in (ROOT / "index.html").read_text():
        _fail(["index.html does not link Learn/index.html"])


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
