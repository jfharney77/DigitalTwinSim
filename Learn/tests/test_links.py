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
        for f in m.get("failures", []):
            for c in f["cite"]:
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


def test_a_novice_reader_meets_no_unleveled_prose():
    """Simulated level-1 students gave up on the second line of a module
    whenever the lede was plain and the next thing was not. Everything a
    reader meets before and after the twin is authored in both registers:
    the prerequisite, every objective, every check question and answer, and
    every how-to or bridging note under a link. Options may stay a plain
    string when the words are already plain; a leveled one must differ."""
    problems = []

    def two(where, v):
        if not isinstance(v, dict) or not v.get("standard") or not v.get("novice"):
            problems.append(f"{where}: needs a standard and a novice register")
        elif v["standard"] == v["novice"]:
            problems.append(f"{where}: registers are identical")

    for m in modules():
        mid = m["id"]
        if m.get("background"):
            two(f"{mid} background", m["background"])
        for i, o in enumerate(m["objectives"]):
            two(f"{mid} objective {i}", o)
        for i, c in enumerate(m["checks"]):
            two(f"{mid} check {i} q", c["q"])
            two(f"{mid} check {i} a", c["a"])
        for e in m["entries"]:
            if "note" in e:
                two(f"{mid} {e['twin']} note", e["note"])
            for link in e["links"]:
                if "how" in link:
                    two(f"{mid} {e['twin']} how", link["how"])
        stops = [("predict", m["predict"]["options"])] + [(f["scenario"], f["options"]) for f in m.get("failures", [])]
        for name, options in stops:
            for i, o in enumerate(options):
                if isinstance(o, dict):
                    two(f"{mid} {name} option {i}", o)
        if not m["core"] and not m.get("background"):
            problems.append(f"{mid}: an elective defines its terms in a background line")
    if problems:
        _fail(problems)


def test_modules_with_several_twins_bridge_between_them():
    """A bare list of links left every persona asking why they were being
    sent to the next app. From the second twin on, an entry says what it adds
    (`note`) or what to do there (`how` on a link); a physics app, which opens
    as a dense console, always says what to watch."""
    problems = []
    for m in modules():
        for i, e in enumerate(m["entries"]):
            guided = "note" in e or any("how" in link for link in e["links"])
            if e["twin"].startswith("Physics") and not any("how" in link for link in e["links"]):
                problems.append(f"{m['id']}: {e['twin']} links say nothing about what to watch")
            elif i > 0 and e.get("port") and not guided:
                problems.append(f"{m['id']}: nothing bridges into {e['twin']}")
    if problems:
        _fail(problems)


def test_entries_know_their_twin_by_its_page_title():
    """The liveness chip only knows that something answers on a port.
    learn.js compares the answering page's <title> with `pageTitle`, so each
    entry carries its twin's real title, and no two twins share one."""
    problems, seen = [], {}
    for m, e in entries():
        if not e.get("port"):
            continue
        html = (ROOT / e["twin"] / "frontend" / "index.html").read_text()
        title = re.search(r"<title>(.*?)</title>", html, re.S).group(1).strip()
        if e.get("pageTitle") != title:
            problems.append(f"{m['id']}: {e['twin']} pageTitle is {e.get('pageTitle')!r}, index.html says {title!r}")
        if seen.setdefault(title, e["twin"]) != e["twin"]:
            problems.append(f"{e['twin']} and {seen[title]} share the page title {title!r}")
    if problems:
        _fail(problems)


# ---- numbers quoted from guided scenarios ----------------------------------

@lru_cache(maxsize=None)
def guided_trace(twin, scenario, patch_json):
    """A physics app's guided scenario, run through the app's own routes in
    its own interpreter: the scenario body GET /api/scenarios serves, with an
    optional patch merged in (the change the course tells the reader to make),
    POSTed to /api/simulate. None when the venv is absent."""
    backend = ROOT / twin / "backend"
    py = backend / ".venv" / "bin" / "python"
    if not py.exists():
        return None
    code = (
        "import json, sys, warnings\n"
        "warnings.simplefilter('ignore')\n"
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "body = [s for s in c.get('/api/scenarios').json() if s['id'] == sys.argv[1]][0]['scenario']\n"
        "def merge(a, b):\n"
        "    for k, v in b.items():\n"
        "        if isinstance(v, dict) and isinstance(a.get(k), dict): merge(a[k], v)\n"
        "        else: a[k] = v\n"
        "merge(body, json.loads(sys.argv[2]))\n"
        "print(json.dumps(c.post('/api/simulate', json=body).json()['trace']))\n"
    )
    out = subprocess.run([str(py), "-c", code, scenario, patch_json], cwd=backend,
                         capture_output=True, text=True, timeout=180)
    if out.returncode != 0:
        raise AssertionError(f"{twin}: running scenario {scenario} failed:\n{out.stderr[-800:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_scenario_quoted_numbers():
    """The numbers the course quotes from a physics app's guided scenario
    (`scenarioPins`): read at a tick of the scenario's own trace (-1 is the
    last), within `tol` (default 0.5, so a quoted "about 65 W" pins 64.9)."""
    problems = []
    for m in modules():
        linked = {(e["twin"], l["id"]) for e in m["entries"] for l in e["links"] if l["kind"] == "scenario"}
        for pin in m.get("scenarioPins", []):
            where = f"{m['id']}: {pin['twin']} {pin['scenario']}"
            if (pin["twin"], pin["scenario"]) not in linked:
                problems.append(f"{where} is pinned but not linked from the module")
                continue
            trace = guided_trace(pin["twin"], pin["scenario"], json.dumps(pin.get("patch", {}), sort_keys=True))
            if trace is None:
                continue
            step = pin["step"]
            if not -len(trace) <= step < len(trace):
                problems.append(f"{where} has no tick {step}")
                continue
            got, want = trace[step].get(pin["field"]), pin["value"]
            if isinstance(want, bool) or isinstance(want, str):
                ok = got == want
            else:
                ok = isinstance(got, (int, float)) and abs(got - want) <= pin.get("tol", 0.5)
            if not ok:
                problems.append(f"{where} tick {step} {pin['field']} is {got!r}, course quotes {want!r}")
    if problems:
        _fail(problems)


# ---- failure scenarios ----------------------------------------------------

def failures():
    """Every "when it goes wrong" stop: (module, stop)."""
    for m in modules():
        for f in m.get("failures", []):
            yield m, f


@lru_cache(maxsize=None)
def scenario_probe(twin, scenario, request_json):
    """Ask the twin's own backend about a failure scenario, in the twin's own
    interpreter and through its real routes (FastAPI's TestClient, no server,
    no port): the ids GET /api/scenarios lists, the scenario's trace, and the
    status an unknown id gets. None when the venv is absent."""
    backend = ROOT / twin / "backend"
    py = backend / ".venv" / "bin" / "python"
    if not py.exists():
        return None
    code = (
        "import json, sys, warnings\n"
        "warnings.simplefilter('ignore')\n"
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "req = json.loads(sys.argv[2])\n"
        "c = TestClient(app)\n"
        "def call(sid):\n"
        "    url = '/api/' + req['endpoint'] + '?scenario=' + sid\n"
        "    return c.post(url, json=req['body']) if req['method'] == 'POST' else c.get(url)\n"
        "r = call(sys.argv[1])\n"
        "body = r.json()\n"
        "print(json.dumps({\n"
        "    'ids': [s['id'] for s in c.get('/api/scenarios').json()],\n"
        "    'status': r.status_code,\n"
        "    'trace': body.get('trace') if isinstance(body, dict) else None,\n"
        "    'unknown': call('no-such-scenario').status_code,\n"
        "}))\n"
    )
    out = subprocess.run([str(py), "-c", code, scenario, request_json], cwd=backend,
                         capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise AssertionError(f"{twin}: probing scenario {scenario} failed:\n{out.stderr[-800:]}")
    return json.loads(out.stdout.strip().splitlines()[-1])


def _failure_request(f):
    """How the stop's trace is fetched: GET /api/<trace>?scenario=<id>, or the
    explicit request a POST twin (Alienware) needs."""
    req = f.get("request") or {"method": "GET", "endpoint": f["trace"], "body": None}
    return json.dumps(req, sort_keys=True)


def _failure_trace(f):
    probe = scenario_probe(f["twin"], f["scenario"], _failure_request(f))
    return None if probe is None else probe


def test_failure_scenario_ids_exist_in_the_backend():
    """#scenario=<id> on a narrative twin names a scenario its backend really
    serves. Without a venv: the id is a string literal in backend/app, the
    route exists, and App.tsx reads scenario= from the hash. With one: the id
    is in GET /api/scenarios, the trace comes back 200, an unknown id is a
    404 (so a typo cannot silently play the happy path), and the phase or
    step the link pauses on is where the course says it is."""
    problems = []
    for m, f in failures():
        twin, sid = f["twin"], f["scenario"]
        app_dir = ROOT / twin / "backend" / "app"
        if not any(f'"{sid}"' in p.read_text() for p in app_dir.glob("*.py")):
            problems.append(f"{m['id']}: {twin} backend/app never names scenario {sid!r}")
        req = json.loads(_failure_request(f))
        main = (app_dir / "main.py").read_text()
        if f'"/api/{req["endpoint"]}"' not in main or '"/api/scenarios"' not in main:
            problems.append(f"{m['id']}: {twin} main.py lacks /api/{req['endpoint']} or /api/scenarios")
        if "scenario" not in (ROOT / twin / "frontend" / "src" / "App.tsx").read_text():
            problems.append(f"{m['id']}: {twin} App.tsx does not read #scenario=")
        at = f["at"]
        if at["kind"] not in ("phase", "step"):
            problems.append(f"{m['id']}: {twin} failure stop pauses on a phase or a step")
            continue
        probe = _failure_trace(f)
        if probe is None:
            continue
        if sid not in probe["ids"]:
            problems.append(f"{m['id']}: {twin} /api/scenarios lists {probe['ids']}, not {sid!r}")
        if probe["status"] != 200 or not probe["trace"]:
            problems.append(f"{m['id']}: {twin} scenario {sid} returned {probe['status']} with no trace")
            continue
        if probe["unknown"] != 404:
            problems.append(f"{m['id']}: {twin} answers an unknown scenario id with {probe['unknown']}, not 404")
        trace = probe["trace"]
        if at["kind"] == "phase":
            if at["value"] not in {s["phase"] for s in trace}:
                problems.append(f"{m['id']}: {twin} #scenario={sid}&phase={at['value']} is not a phase of that trace")
        else:
            n = at["value"]
            if not 0 <= n < len(trace):
                problems.append(f"{m['id']}: {twin} #scenario={sid}&step={n} is past the last step")
            elif trace[n]["phase"] != at["expectPhase"]:
                problems.append(f"{m['id']}: {twin} {sid} step {n} is {trace[n]['phase']}, course expects {at['expectPhase']}")
    if problems:
        _fail(problems)


def test_failure_quoted_numbers():
    """The numbers a failure stop quotes, read off the failure trace itself."""
    problems = []
    for m, f in failures():
        probe = _failure_trace(f)
        if probe is None or not probe["trace"]:
            continue
        trace = probe["trace"]
        for pin in f.get("pins", []):
            if "agg" in pin:
                got, where = max(s[pin["field"]] for s in trace), f"max {pin['field']}"
            elif pin["step"] >= len(trace):
                problems.append(f"{m['id']}: {f['scenario']} has no step {pin['step']}")
                continue
            else:
                got, where = trace[pin["step"]].get(pin["field"]), f"step {pin['step']} {pin['field']}"
            if got != pin["value"]:
                problems.append(f"{m['id']}: {f['twin']} {f['scenario']} {where} is {got!r}, course quotes {pin['value']!r}")
    if problems:
        _fail(problems)


def test_failure_stops_have_the_contract():
    """A failure stop is a prediction like any other: a question and an
    answer in both registers, at least three options, a valid answer index,
    the tests that settle it, quoted numbers pinned, and a twin the module
    already teaches at its registered port."""
    reg = json.loads((ROOT / "ports.json").read_text())["twins"]
    problems, seen = [], set()
    for m, f in failures():
        where = f"{m['id']}/{f.get('scenario')}"
        for key in ("twin", "port", "name", "scenario", "at", "label", "q", "options", "answer", "a", "cite", "pins"):
            if key not in f:
                problems.append(f"{where}: missing {key}")
        if problems and problems[-1].startswith(where):
            continue
        if f["twin"] not in {e["twin"] for e in m["entries"]}:
            problems.append(f"{where}: {f['twin']} is not a twin this module teaches")
        if reg.get(f["twin"], {}).get("frontend") != f["port"]:
            problems.append(f"{where}: port {f['port']} is not {f['twin']}'s frontend port in ports.json")
        if "trace" not in f and "request" not in f:
            problems.append(f"{where}: needs a trace endpoint or an explicit request")
        for field in ("q", "a"):
            v = f[field]
            if not isinstance(v, dict) or not v.get("standard") or not v.get("novice") or v["standard"] == v["novice"]:
                problems.append(f"{where}: {field} needs two distinct registers")
        if len(f["options"]) < 3 or not 0 <= f["answer"] < len(f["options"]):
            problems.append(f"{where}: needs at least 3 options and a valid answer index")
        if not f["cite"] or not f["pins"]:
            problems.append(f"{where}: needs a cite and at least one pinned number")
        if (f["twin"], f["scenario"]) in seen:
            problems.append(f"{where}: listed twice")
        seen.add((f["twin"], f["scenario"]))
    if problems:
        _fail(problems)


def test_what_goes_wrong_track_strings_every_failure():
    """The failure track visits every failure stop exactly once, and asks
    nothing of a module that has none."""
    problems = []
    tracks = [t for t in course()["tracks"] if t.get("failuresOnly")]
    if [t["id"] for t in tracks] != ["what-goes-wrong"]:
        _fail(["exactly one failuresOnly track, id what-goes-wrong"])
    by_id = {m["id"]: m for m in modules()}
    visited = []
    for s in tracks[0]["steps"]:
        stops = [f for f in by_id[s["module"]].get("failures", []) if "only" not in s or f["twin"] in s["only"]]
        if not stops:
            problems.append(f"what-goes-wrong: {s['module']} shows no failure stop")
        for twin in s.get("only", []):
            if twin not in {f["twin"] for f in stops}:
                problems.append(f"what-goes-wrong: {s['module']} keeps {twin}, which has no failure stop")
        visited += [(f["twin"], f["scenario"]) for f in stops]
    every = [(f["twin"], f["scenario"]) for _, f in failures()]
    if sorted(visited) != sorted(every):
        problems.append(f"what-goes-wrong visits {sorted(visited)}, the course has {sorted(every)}")
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


# ---- graded labs and coupled chains ---------------------------------------
# A lab stop is do-mode: the module's app grades a scenario the reader builds.
# The course only links to it, so what can drift is the id, the title, the
# difficulty and the port — all pinned here against the app's own labs.py.

LAB_ID_RE = re.compile(r'id="([a-z0-9-]+)"')


@lru_cache(maxsize=None)
def app_labs(twin):
    """{lab id: (title, difficulty)} read out of <twin>/backend/app/labs.py.
    Read, not imported: the file is pure data plus a pure grader, and the
    course has no business starting an interpreter per twin for this."""
    path = ROOT / twin / "backend" / "app" / "labs.py"
    if not path.exists():
        return {}
    text = path.read_text()
    found = {}
    for m in re.finditer(r"^[A-Z_0-9]+ = Lab\(\n(.*?)^\)", text, re.S | re.M):
        block = m.group(1)
        lid = LAB_ID_RE.search(block)
        title = re.search(r'title="([^"]+)"', block)
        diff = re.search(r"difficulty=(\d)", block)
        if lid and title and diff:
            found[lid.group(1)] = (title.group(1), int(diff.group(1)))
    return found


def lab_stops():
    for m in modules():
        if "lab" in m:
            yield m, m["lab"]


def test_lab_stops_name_real_labs():
    """Every lab stop names a lab the app actually declares, with the app's
    own title and difficulty, on the twin's registered frontend port, and the
    app's frontend answers the #lab=<id> deep link the course sends."""
    reg = json.loads((ROOT / "ports.json").read_text())["twins"]
    problems = []
    for m, lab in lab_stops():
        twin = lab["twin"]
        known = app_labs(twin)
        if not known:
            problems.append(f"{m['id']}: {twin} declares no labs")
            continue
        if lab["id"] not in known:
            problems.append(f"{m['id']}: {twin} has no lab {lab['id']} (has {', '.join(sorted(known))})")
            continue
        title, difficulty = known[lab["id"]]
        if lab["title"] != title:
            problems.append(f"{m['id']}: lab title is {lab['title']!r}, {twin} says {title!r}")
        if lab["difficulty"] != difficulty:
            problems.append(f"{m['id']}: lab difficulty is {lab['difficulty']}, {twin} says {difficulty}")
        if reg.get(twin, {}).get("frontend") != lab["port"]:
            problems.append(f"{m['id']}: lab port :{lab['port']} is not {twin}'s frontend port")
        app = ROOT / twin / "frontend" / "src" / "App.tsx"
        if "#lab=" not in app.read_text():
            problems.append(f"{m['id']}: {twin}/frontend/src/App.tsx has no #lab= deep link")
        for cite in lab["cite"]:
            path, _, name = cite.partition("::")
            f = ROOT / path
            if not f.exists() or not re.search(rf"^def {re.escape(name)}\(", f.read_text(), re.M):
                problems.append(f"{m['id']}: lab cite {cite} does not resolve")
    if problems:
        _fail(problems)


def test_every_module_whose_app_has_labs_carries_the_lab_stop():
    """A lab that exists and is never linked is a lab nobody finds. If any
    twin in a module declares labs, the module carries a stop for one of them."""
    problems = []
    for m in modules():
        if "lab" in m:
            continue
        for e in m["entries"]:
            if app_labs(e["twin"]):
                problems.append(f"{m['id']}: {e['twin']} has graded labs and the module links none")
    if problems:
        _fail(problems)


def test_lab_prose_is_authored_in_both_registers():
    """Same rule as everything else a reader meets: two registers, and they
    have to differ. `how` may be shared between stops (it describes the same
    mechanism); the goal and the lever are about this lab."""
    problems = []
    for m, lab in lab_stops():
        for field in ("goal", "lever", "how"):
            v = lab.get(field)
            if not isinstance(v, dict) or not v.get("standard") or not v.get("novice"):
                problems.append(f"{m['id']} lab {field}: needs a standard and a novice register")
            elif v["standard"] == v["novice"]:
                problems.append(f"{m['id']} lab {field}: registers are identical")
        if not isinstance(lab.get("label"), str) or not lab["label"]:
            problems.append(f"{m['id']} lab: label must be one plain string")
    if problems:
        _fail(problems)


def test_the_labs_track_is_every_lab_stop_in_course_order():
    tracks = {t["id"]: t for t in course()["tracks"]}
    problems = []
    if "labs" not in tracks:
        _fail(["there is no 'labs' track"])
    track = tracks["labs"]
    if not track.get("labsOnly"):
        problems.append("the labs track must set labsOnly, or it renders as a normal track")
    want = [m["id"] for m, _ in lab_stops()]
    got = [s["module"] for s in track["steps"]]
    if got != want:
        problems.append(f"labs track is {got}, the lab stops in course order are {want}")
    js = (LEARN / "learn.js").read_text()
    for needed in ("labsOnly", "renderLabSection", "#lab="):
        if needed not in js:
            problems.append(f"learn.js does not handle {needed}")
    if problems:
        _fail(problems)


# The capstone's last stop is the coupled chain: compose/ runs two engines at
# once, and the couplings the course names have to be the ones that exist.

def coupling_ids():
    text = (ROOT / "compose" / "catalog.py").read_text()
    return set(re.findall(r'id="(c\d+)"', text))


def chain_ids():
    text = (ROOT / "compose" / "presets.py").read_text()
    return set(re.findall(r'id="([a-z0-9-]+)"', text))


def test_the_capstone_ends_on_the_coupled_chain():
    """M12 is the last core module, and the thing after its lab is the chain
    that computes the factory from the other engines' traces. Every coupling
    id, the chain id, the port and both cites are pinned against compose/."""
    problems = []
    capstone = [m for m in modules() if m["core"]][-1]
    if "couplings" not in capstone:
        _fail([f"{capstone['id']} is the last core module and names no coupled chain"])
    c = capstone["couplings"]
    reg = json.loads((ROOT / "ports.json").read_text())["twins"]
    if reg.get(c["twin"], {}).get("frontend") != c["port"]:
        problems.append(f"{capstone['id']}: coupled chain port :{c['port']} is not {c['twin']}'s frontend port")
    known_couplings, known_chains = coupling_ids(), chain_ids()
    if not known_couplings or not known_chains:
        problems.append("compose/catalog.py or compose/presets.py declares nothing")
    if c["chain"] not in known_chains:
        problems.append(f"{capstone['id']}: chain {c['chain']} is not a preset chain in compose/presets.py")
    for cid in c["ids"]:
        if cid not in known_couplings:
            problems.append(f"{capstone['id']}: coupling {cid} is not in compose/catalog.py")
    for cid in c["seams"]:
        if cid not in c["ids"]:
            problems.append(f"{capstone['id']}: seam {cid} is not one of the chain's couplings")
    for field in ("text", "how"):
        v = c[field]
        if not v.get("standard") or not v.get("novice") or v["standard"] == v["novice"]:
            problems.append(f"{capstone['id']} couplings {field}: needs two distinct registers")
    for cite in c["cite"]:
        path, _, name = cite.partition("::")
        f = ROOT / path
        if not f.exists() or not re.search(rf"^def {re.escape(name)}\(", f.read_text(), re.M):
            problems.append(f"{capstone['id']}: coupling cite {cite} does not resolve")
    app = ROOT / c["twin"] / "frontend" / "src" / "App.tsx"
    text = app.read_text()
    for hashed in ("#chain=", "#seams"):
        if hashed not in text:
            problems.append(f"{c['twin']}/frontend/src/App.tsx has no {hashed} deep link")
    if "renderCouplings" not in (LEARN / "learn.js").read_text():
        problems.append("learn.js does not render the coupled chain")
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
