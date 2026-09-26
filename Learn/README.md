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
| The roofline | GPU | Compute-bound or memory-bound is the kernel's ratio against the chip's ridge point |
| A server wakes up | R760, iDRAC | A plugged-in server is never off; memory training is the slow stage |
| Heat in one box | R760Thermal | Fans are part of the load they cool; fan power goes as speed cubed |
| Eight GPUs, then seventy-two | XE9680, XE9712, PhysicsCompute | Where the NVLink domain's wall sits is the decision |
| Liquid: heat in equals heat out | IR7000, PhysicsCDU | A loop makes three numbers equal; coordination decides what gives |
| Storage arithmetic and the mirrored ack | PhysicsME5, PowerStore | Every write costs more than one write |
| Deleting the controller | PowerFlex, PowerScale, Exascale, PhysicsStorage | Scale-out removes one thing and the design follows |
| The fabric: lossless two ways | SN6000, Quantum-X800, PhysicsFabric | Ethernet proves it loses nothing to congestion; InfiniBand cannot express that loss; both pay in backpressure |
| Survive, verify, contain | PowerProtect, CyberDetect, FortZero, PhysicsResilience | Three separate questions: survive, clean, reachable |
| Running the estate | CloudIQ, VxRail, PrivateCloud, NativeEdge, PhysicsFleet | Operations is where architecture sends its bills |
| Inference at the edge | ProMaxPlus, GPU, PhysicsClient | Decode is memory-bound, so never move the weights again |
| Capstone: stand up an AI factory | PhysicsAIFactory, PhysicsCompute, CustomerSetup | GPUs idle because data did not arrive |

Seven electives (rack power, the shared chassis, the rugged edge, dedupe,
modernizing without migrating, the laptop power path, the data pipeline) use
the same template. Tracks are ordered subsets for different readers: the
whole course, AI infrastructure, storage and backup, power and cooling,
security, platform operations, a short predict-only version, what goes wrong,
and the electives.

## When it goes wrong

Ten narrative twins serve a second trace beside the happy path: one failure,
with its own invariant and tests, opened with `#scenario=<id>`. The module
that teaches each twin carries a "When it goes wrong" stop for it, after the
checks: a prediction with options, the deep link into the failure trace
(locked until the reader commits), the answer hidden until revealed, and the
tests that settle it. The "What goes wrong" track strings the ten stops
together and shows only them; a stop is done when its answer is revealed.
Outside that track the stops are optional and do not count toward finishing a
module.

| Module | Twin | Scenario | Opens at |
|---|---|---|---|
| A server wakes up | DellIDRAC | `firmware-update-rollback` | `&step=7` |
| Eight GPUs, then seventy-two | DellPowerEdgeXE9712 | `coolant-fault` | `&phase=leak` |
| Storage arithmetic and the mirrored ack | DellPowerStore | `node-loss-failover` | `&phase=degraded` |
| The fabric: lossless two ways | DellPowerSwitchSN6000 | `gray-link` | `&phase=blind` |
| Survive, verify, contain | DellPowerProtect | `cleaning-gc` | `&step=5` |
| Survive, verify, contain | DellCyberDetect | `dwell-exceeds-retention` | `&phase=verdict` |
| Running the estate | DellCloudIQ | `connected-no-data` | `&phase=stale` |
| Running the estate | DellVxRail | `node-add-mismatch` | `&phase=refused` |
| Running the estate | DellNativeEdge | `attestation-fails` | `&phase=quarantine` |
| The laptop's power path | DellAlienware | `charge-taper-diagnostics` | `&phase=heat` |

## Do it: the graded labs

Sixteen of the apps a module opens carry graded labs ([`docs/LAB_PATTERN.md`](../docs/LAB_PATTERN.md)):
a goal, its constraints, a scenario the reader builds with the app's own
controls, and a pure scoring function that grades the trace. The module that
teaches the idea carries one lab stop, after the failure stops — the lab's
goal, the lever to look at, the deep link (`#lab=<id>`), and the tests that
pin the lab itself. The course never grades: the app does, in its own engine,
and the reader marks the stop passed here to keep their place.

The **Labs** track visits only those stops, in course order. A stop is done
when it is marked passed; outside that track a lab is optional and does not
count toward finishing a module.

| Module | App | Lab | Title |
|---|---|---|---|
| Heat in one box | DellPowerEdgeR760Thermal | `psu-sweet-spot` | Find the PSU sweet spot |
| Eight GPUs, then seventy-two | PhysicsCompute | `worst-seat` | Keep the worst seat cool |
| Liquid: heat in equals heat out | PhysicsCDU | `full-rack-lean-pumps` | Full rack, leanest pumps |
| Storage arithmetic and the mirrored ack | PhysicsME5 | `pay-the-write-tax` | Pay the write tax |
| Deleting the controller | PhysicsStorage | `size-for-the-survivor` | Size for the survivor's worst hour |
| The fabric: lossless two ways | PhysicsFabric | `elephants-on-a-budget` | Tame the elephants on a power budget |
| Survive, verify, contain | PhysicsResilience | `back-within-a-day` | Back within a day, losing as little as you can |
| Running the estate | PhysicsFleet | `headroom-for-the-last-day` | Headroom for the last day |
| Inference at the edge | PhysicsClient | `charge-while-you-play` | Charge while you play |
| Capstone: stand up an AI factory | PhysicsAIFactory | `feed-the-worst-day` | Feed the cluster on its worst day |
| Rack power: the runtime the battery really has | PhysicsRackPower | `three-feeds-eight-servers` | Three feeds, eight unequal servers |
| Shared chassis: the noisy neighbor | PhysicsMX7000 | `spread-the-heat` | Spread the heat |
| Rugged edge: the filter nobody changed | PhysicsXR | `dust-and-heat` | Six months of dust, one hot afternoon |
| Dedupe as arithmetic: the entropy alarm | PhysicsDataDomain | `branch-box-memory` | How long can the branch box remember? |
| The laptop's power path | DellAlienware | `fit-the-brick` | Fit the game inside the brick |
| The data pipeline: the bottleneck moves | PhysicsData | `quiet-and-quick` | A detector that is quiet and quick |

## The chain, coupled

The capstone module ends where the course has been heading: `compose/`, which
runs two engines at once and asserts an identity across the hand-off. Its last
section links the `factory-fed` chain — the AI factory computed from the other
engines' traces rather than from its own aggregates — and the seam table, and
names the couplings that chain leans on (`c1`…`c4`, `c8`). Those ids and the
chain id are pinned against `compose/catalog.py` and `compose/presets.py`.

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
  Everything a reader meets is authored in both: the idea, the prerequisite,
  the objectives, the question, the reveal, the checks, the how-to and
  bridging lines under the links, and the bridge. Options are leveled where
  the standard wording uses a term the novice text has not introduced. The
  pytest ids under an answer show in the standard register only. The short
  track reads novice unless the reader has already picked a level.
- **Dell clean design**: no eyebrow text, no visible step or module numbering,
  no divider rules, no highlighted text, no serifs.

## Adding or changing a module

1. Write for what the reader will see. Quote the twin's on-screen step
   numbers (they count from one; `#step=N` counts from zero) and its on-screen
   phase labels, never engine ids or field names. Quote the number the screen
   shows, not the bound a test asserts. A question has to be answerable from
   what the page and the linked steps have shown by then, and the lede, the
   objectives and the locked link labels must not give the prediction away
   (`lockedLabel` is the neutral label shown until the reader commits).
2. Edit `course.js` (it must stay valid JSON after `window.COURSE = `).
   A link is one of: `tour` (`#tour/<id>`), `phase` (`#phase=<name>`), `step`
   (`#step=N` with an `expectPhase`), `scenario` (`#scenario=<id>` with the
   scenario's exact `title`), `root`, `lesson` (GPU `#live/tour`, with the
   lesson id to step to), or `setup` (a CustomerSetup page).
3. Cite the test that settles each answer as `path::test_name`, and add a
   `pins` entry (`twin`, `step` or `"agg": "max"`, `field`, `value`) for every
   trace number the text quotes.
   A number quoted from a physics app's guided scenario gets a
   `scenarioPins` entry instead (`twin`, `scenario`, `step` as a tick index
   with -1 for the last, `field` in the wire's camelCase, `value`, an optional
   `tol`, and an optional `patch` merged into the scenario body when the text
   tells the reader to change a control). Under a link, `how` says what to do
   and what to watch; on an entry, `note` says why the reader is being sent
   there and how its numbers relate to the previous twin's. Each entry carries
   the twin's `pageTitle`, which the page compares with whatever answers on
   the port.
4. A failure stop goes in the module's `failures` list: `twin`, `port`,
   `name`, `scenario`, `at` (a `phase`, or a `step` with `expectPhase`),
   `trace` (the GET endpoint; a POST twin gives a `request` with `method`,
   `endpoint` and `body` instead), `label`, `q` and `a` in both registers,
   `options`, `answer`, `cite`, and `pins` read from the failure trace. Add
   the twin to the `what-goes-wrong` track's step for that module.
5. Run `python3 Learn/scripts/gen_pages.py`, then `pytest Learn`.

## What the tests pin

`Learn/tests/test_links.py` (stdlib only; `python3 Learn/tests/test_links.py`
or `pytest Learn`, and part of the root `pytest`):

- ports against `ports.json`, and 5172 reserved and unused by any twin;
- `#phase=` names against the twin's `engine.py`, `#step=N` against the
  phase the trace actually has at N;
- `#tour/<id>` against the `TourStep` ids in the twin's `tour.py`, and a
  failure if a module links a twin that has a tour without using it;
- `#scenario=<id>` and its title against `GuidedScenario` in `presets.py`;
- every number quoted from a guided scenario (`scenarioPins`), by posting the
  scenario the app itself serves, patched as the text instructs, to the app's
  own `/api/simulate`;
- both registers on every prerequisite, objective, check, how-to and note,
  and a bridge into every twin after a module's first;
- each entry's `pageTitle` against the twin's `index.html`, unique per twin;
- a narrative twin's failure `#scenario=<id>` against its backend: the id is
  named in `backend/app`, and, through the twin's own `.venv` and its real
  routes, it is listed by `GET /api/scenarios`, its trace returns 200, an
  unknown id returns 404, and the `&phase=` or `&step=` it pauses on is where
  the course says;
- every number a failure stop quotes, read from the failure trace;
- the failure-stop contract, and that the "What goes wrong" track visits every
  stop exactly once;
- every cite resolves to an existing test function;
- every quoted number, read from the twin's default trace through the twin's
  own `.venv` (skipped where a venv is absent, as in CI);
- every lab stop against the app's own `backend/app/labs.py`: the lab id
  exists, the title and difficulty are the app's, the port is the twin's
  registered frontend port, its `App.tsx` answers `#lab=<id>`, the cites
  resolve, the goal and lever are in both registers, and a module whose app
  has labs and links none fails;
- the Labs track: exactly the lab stops, in course order, `labsOnly` set, and
  `learn.js` still handling all three;
- the capstone's coupled chain: every coupling id against `compose/catalog.py`,
  the chain id against `compose/presets.py`, the port, both registers, both
  cites, and `#chain=` / `#seams` in compose's `App.tsx`;
- trace endpoints against `main.py`, CustomerSetup links against disk, module
  pages against the generator, tracks and prerequisites for consistency, the
  predict/check contract, both registers, and no visible numbering.
