# Learn the twins

A course over the twins in this repository. Each twin teaches one idea; this
puts them in a teaching order, asks a question before each one, links the
step of the running twin that settles the answer, and checks every link,
cite and quoted number against the code.

The design brief, with the evidence behind every answer, is
[`docs/COURSE_DESIGN.md`](../docs/COURSE_DESIGN.md).

## Open it

```
./Learn/scripts/serve.sh                 # http://localhost:5172/Learn/
scripts/dev.sh DellPowerFlex             # then start the twins a module uses
```

`serve.sh` serves the repository root on 5172 (reserved in `ports.json` as
`reserved.learnPages`), so the pages' relative links to `../CustomerSetup/`
resolve. Opening `Learn/index.html` straight from disk also works; the
liveness chips behave most consistently over http.

## The modules

| Module | Twins | The one idea |
|---|---|---|
| The roofline | GPU | Compute-bound or memory-bound is a ratio, not a property of the chip |
| A server wakes up | R760, iDRAC | A plugged-in server is never off; memory training is the slow stage |
| Heat in one box | R760Thermal | Fans are part of the load they cool; fan power goes as speed cubed |
| Eight GPUs, then seventy-two | XE9680, XE9712, PhysicsCompute | The NVLink domain fuses atomically; where its wall sits is the decision |
| Liquid: heat in equals heat out | IR7000, PhysicsCDU | A loop makes three numbers equal; coordination decides what gives |
| Storage arithmetic and the mirrored ack | PhysicsME5, PowerStore | Every write costs more than one write |
| Deleting the controller | PowerFlex, PowerScale, Exascale, PhysicsStorage | Scale-out removes one thing and the design follows |
| The fabric: lossless two ways | SN6000, Quantum-X800, PhysicsFabric | Ethernet proves losslessness; InfiniBand makes loss inexpressible |
| Survive, verify, contain | PowerProtect, CyberDetect, FortZero, PhysicsResilience | Three separate questions: survive, clean, reachable |
| Running the estate | CloudIQ, VxRail, PrivateCloud, NativeEdge, PhysicsFleet | Operations is where architecture sends its bills |
| Inference at the edge | ProMaxPlus, PhysicsClient | Decode is memory-bound, so never move the weights again |
| Capstone: stand up an AI factory | PhysicsAIFactory, PhysicsCompute, CustomerSetup | GPUs idle because data did not arrive |

Seven electives (rack power, the shared chassis, the rugged edge, dedupe,
modernizing without migrating, the laptop power path, the data pipeline) use
the same template. Tracks are ordered subsets for different readers: the
whole course, AI infrastructure, storage and backup, power and cooling,
security, platform operations, a short predict-only version, and the
electives.

## How it is built

```
Learn/
  index.html            course home: tracks, modules, progress
  modules/<id>.html     one page per module (generated shells)
  course.js             the course as data: window.COURSE = <JSON>
  learn.js              renderer + progress store (plain ES5, no build)
  learn.css             accents over ../CustomerSetup/shared/setup.css
  scripts/serve.sh      python3 -m http.server 5172 over the repo root
  scripts/gen_pages.py  writes modules/<id>.html from course.js
  tests/test_links.py   pins everything below
```

- **Pages load `course.js`, `learn.js`, then `../CustomerSetup/shared/setup.js`.**
  `learn.js` renders synchronously, so when `setup.js` runs on
  `DOMContentLoaded` the entry links exist and get their liveness chips, start
  hints and step-count readout (`data-twin-port` / `data-twin-start` /
  `data-twin-trace`, the same markup the CustomerSetup pages use). The shared
  files are used unchanged.
- **Predict first.** A module's entry links stay locked until the reader
  commits to an answer; then the answer can be revealed, with the pytest case
  that settles it.
- **Progress** lives in `localStorage["learn-progress-v1"]`, every access in a
  `try/catch`. A module is done when its answer is revealed and every check is
  marked (the predict-only track needs only the reveal). Nothing is graded.
- **Reading level** uses the twins' shared `twin-reading-level` key through
  `setup.js`: levels 1 and 2 read the novice register, 3 to 5 the standard one.
  The idea, the question, the reveal and the bridge are authored in both. The
  short track reads novice unless the reader has already picked a level.
- **Dell clean design**: no eyebrow text, no visible step or module numbering,
  no divider rules, no highlighted text, no serifs.

## Adding or changing a module

1. Edit `course.js` (it must stay valid JSON after `window.COURSE = `).
   A link is one of: `tour` (`#tour/<id>`), `phase` (`#phase=<name>`), `step`
   (`#step=N` with an `expectPhase`), `scenario` (`#scenario=<id>` with the
   scenario's exact `title`), `root`, `lesson` (GPU `#live/tour`, with the
   lesson id to step to), or `setup` (a CustomerSetup page).
2. Cite the test that settles each answer as `path::test_name`, and add a
   `pins` entry (`twin`, `step` or `"agg": "max"`, `field`, `value`) for every
   trace number the text quotes.
3. Run `python3 Learn/scripts/gen_pages.py`, then `pytest Learn`.

## What the tests pin

`Learn/tests/test_links.py` (stdlib only; `python3 Learn/tests/test_links.py`
or `pytest Learn`, and part of the root `pytest`):

- ports against `ports.json`, and 5172 reserved and unused by any twin;
- `#phase=` names against the twin's `engine.py`, `#step=N` against the
  phase the trace actually has at N;
- `#tour/<id>` against the `TourStep` ids in the twin's `tour.py`, and a
  failure if a module links a twin that has a tour without using it;
- `#scenario=<id>` and its title against `GuidedScenario` in `presets.py`;
- every cite resolves to an existing test function;
- every quoted number, read from the twin's default trace through the twin's
  own `.venv` (skipped where a venv is absent, as in CI);
- trace endpoints against `main.py`, CustomerSetup links against disk, module
  pages against the generator, tracks and prerequisites for consistency, the
  predict/check contract, both registers, and no visible numbering.
