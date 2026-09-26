# Composition layer — design

Status: built. `compose/` implements this design; where the build deviates, the
"Implementation notes" section of [`compose/README.md`](../compose/README.md) says so.
This file stays the design of record — read it for *why*, read the README for *what shipped*.

The twins cross-reference each other in prose: PhysicsCompute's `data_feed_pct` slider "is"
PhysicsStorage's `gpu_idle_due_to_data` gauge; the XE9712's cold plate "is" the CDU's load.
Today a reader has to carry the number across by hand. This design makes the carry a piece
of code with a test on it: **one engine's trace becomes another engine's scenario**, and an
identity is asserted across the seam.

Field names below were read from each app's `backend/app/models.py` on 2026-09-18. Python
names are snake_case; the wire is camelCase (the shared alias generator).

## 1. Principles

1. **Pure, like the engines.** `compose/` imports no FastAPI, no `time`, no `random`, no
   file or network IO. `compose/tests/test_purity.py` AST-checks every module under
   `compose/` except `compose/server/` with `twinkit.testing.assert_engine_is_pure`.
2. **No server-to-server calls.** A coupling never opens a socket. Engines are called
   in-process, or their JSON traces are passed in as data.
3. **Engines are not edited to be coupled.** An adapter uses the events and fields an engine
   already has. Where an engine lacks the input a seam needs, this document says so, states
   the quantization error the workaround costs, and lists the additive change that would
   remove it (section 9). No coupling is blocked on those changes.
4. **The seam is where the test lives.** Every coupling names an identity and a tolerance.
   A coupling without an identity is a prose cross-reference with extra steps and is not
   admitted.
5. **Deterministic closed loops.** Feedback couplings run a fixed-point iteration with a
   fixed iteration cap, fixed damping, and a fixed convergence threshold. Same chain in,
   same `CoupledTrace` out, byte for byte.
6. **Numbers stay illustrative.** Coupling two illustrative engines yields an illustrative
   result. Every `CoupledTrace` carries `illustrative: true` and the union of the
   `estimated` constants the seam touched.

## 2. Package layout

```
compose/
  __init__.py        run, Chain, Link, CoupledTrace (re-exports)
  loader.py          load_engine("PhysicsCDU") -> EngineHandle; the only importlib user
  resample.py        hold, mean_pool, steady_window, to_events (pure functions)
  seam.py            SeamCheck, SeamResult, assert_seams
  chain.py           Chain, Link, run(), fixed_point()
  couplings/
    c1_compute_heat_to_cdu.py
    c2_cdu_caps_to_compute.py
    c3_storage_to_compute_feed.py
    c4_fabric_gray_to_factory.py
    c5_wall_watts_to_rackpower.py
    c6_resilience_to_datadomain.py
    c7_xr_site_to_fleet.py
    c8_factory_fed.py            the capstone chain (section 7)
  json_adapter.py    same couplings over recorded JSON traces instead of live engines
  server/            the only impure edge: FastAPI app, port 8048
  frontend/          React/Vite "Couplings" page, port 5221
  scripts/           start_backend.sh, start_frontend.sh, start_all.sh, stop_all.sh, bake.py
  tests/
```

No venv of its own for the pure part: `compose/` needs only `pydantic`, which every backend
venv already has, so `pytest compose` runs from any of them or from the root suite.
`compose/server/` needs FastAPI and uses the same `.venv` recipe as every backend.

### 2.1 Importing 42 packages that are all called `app`

The root suite solves this for tests by letting backends take turns holding the name
`app` (`twinkit.testing.claim_backend` / `_activate`: stash the previous owner's `app.*`
modules, delete them from `sys.modules`, put the new backend first on `sys.path`). That is
turn-taking. Composition needs two engines alive **at once**, so it cannot reuse it directly.

`compose/loader.py` loads each backend's `app` package under a private name instead:

```python
def load_engine(component: str) -> EngineHandle:
    """Import <component>/backend/app as the package `_twin_<component>`."""
```

- `importlib.util.spec_from_file_location("_twin_PhysicsCDU", ".../app/__init__.py",
  submodule_search_locations=[".../app"])`, registered in `sys.modules` under the private
  name before execution.
- Every engine module uses relative imports (`from .constants import value as C`,
  `from .models import ...` — verified in PhysicsCDU, PhysicsCompute, PhysicsAIFactory), so
  they resolve inside `_twin_PhysicsCDU` and never touch the name `app`. The loader never
  writes `sys.modules["app"]`, so it cannot disturb the root suite's turn-taking.
- `EngineHandle` exposes `simulate`, `Scenario`, `SimEvent`, `constants`, and the models
  module. Handles are cached per component.
- `compose/tests/test_loader.py` pins: two handles loaded together have distinct `Scenario`
  classes; `"app"` in `sys.modules` is unchanged by loading; a backend whose engine uses an
  absolute `import app...` fails with a named error rather than silently binding to another
  component.

All eight engines in scope have the signature
`simulate(scenario) -> tuple[list[SimState], list[LogEntry], Summary]`.

### 2.2 The JSON path

`compose/json_adapter.py` runs the same coupling functions over traces that are already
JSON (`SimResponse` bodies, camelCase). Each coupling is written against a tiny read
protocol — `get(state, "liquid_watts")` — with two implementations, attribute access for
live models and camelCase key lookup for dicts. This is what static hosting uses (section
8) and what lets a recorded trace from a running twin be fed in without importing it.

## 3. API

```python
@dataclass(frozen=True)
class Link:
    coupling: str                 # "c1", "c2", ...
    source: str                   # component dir, e.g. "PhysicsCompute"
    target: str
    params: dict[str, float | int | str] = field(default_factory=dict)

@dataclass(frozen=True)
class Chain:
    id: str
    scenarios: dict[str, dict]    # component -> base Scenario (camelCase JSON), the user's input
    links: tuple[Link, ...]
    closed: bool = False          # True -> fixed_point() over the links that form the cycle
    max_iter: int = 12
    damping: float = 0.5
    tol: float = 0.005            # relative, on the loop variable the closing link names

def run(chain: Chain) -> CoupledTrace: ...
```

```python
class CoupledTrace(CamelModel):
    chain_id: str
    stages: list[Stage]           # one per engine run, in execution order
    seams: list[SeamResult]       # one per link (per iteration for closed chains: the last)
    iterations: int               # 1 for open chains
    converged: bool
    residual_history: list[float] # closed chains: loop-variable residual per iteration
    timeline: list[JoinedTick]    # common time base, see 3.1
    illustrative: bool = True
    estimated_constants: list[str]

class Stage(CamelModel):
    component: str
    scenario: dict                # the scenario actually run, including injected events
    injected_events: list[dict]   # only the events the adapter added, for the UI diff
    trace: list[dict]
    summary: dict
    validations: list[dict]       # the target's own validation rules still run

class SeamResult(CamelModel):
    coupling: str
    identity: str                 # human-readable equation
    lhs: float; rhs: float; unit: str
    abs_error: float; tolerance: float
    holds: bool
    worst_tick: int | None
    note: str                     # e.g. "integer util quantization, <= 0.92 kW"
```

`run()` never raises on a broken seam; it reports `holds=False`. `assert_seams(trace)`
raises, and is what the pytest cases call. The UI shows a broken seam in the log, not as a
crash — a seam breaking is sometimes the lesson (C2 without convergence, C8's disagreement).

### 3.1 Time bases and resampling

Engines tick at 1 s, 1 h, or 1 d. Rules, all in `resample.py`, all pure:

| Function | Use | Rule |
|---|---|---|
| `steady_window(trace, field, frac=0.2)` | fast -> slow (s -> h, s -> d) | mean of the last 20% of ticks; a 900 s run stands for "this operating point", and the slow engine holds it until the next operating point |
| `mean_pool(trace, field, n)` | fast -> slow when the fast run is long enough to cover the slow tick | block mean, conserves the integral |
| `hold(trace, field, n)` | slow -> fast | zero-order hold, one slow tick = n fast ticks |
| `to_events(series, action, deadband)` | any -> event list | emit an event only when the value moves by more than `deadband` since the last emitted event; caps event count at 240 per run |

Energy-like quantities use `mean_pool` (integral conserved, asserted in
`test_resample.py`: `sum(pooled)*n == sum(raw)` to 1e-9). State-like quantities use `hold`.
`timeline` is built on the slowest base in the chain with `hold`/`mean_pool` applied
per field according to a `kind: "flow" | "state"` tag each coupling declares.

## 4. The couplings

Eight couplings. C1+C2 form a closed loop; C3 and C4 feed C8; C5–C7 are open seams.

### C1 — XE9712 liquid heat becomes the CDU's load

| | |
|---|---|
| Source | `PhysicsCompute`, `config.product="xe9712"`. `SimState.liquid_watts` (W), `t` (s). Also read: `coolant_supply_c`, `flow_lpm` for the UI only |
| Target | `PhysicsCDU`. `CduConfig.tray_groups`, and `set-util` events (`value` = %) |
| Units | W -> kW (÷1000) |
| Time base | 1 s -> 1 s; durations must match (both capped 7200 s), `to_events` deadband 1 util point |

The CDU has no "heat in kW" input. Its load is
`groups_online × group_kw × (idle + (1−idle)·util) × cap` with `group_kw=40`,
`group_idle_fraction=0.08` (`bank_heat_kw`). The adapter inverts that:

```
groups  = ceil(peak(liquid_kw) / group_kw), clamped 1..6        -> CduConfig.tray_groups
util(t) = ((liquid_kw(t) / (groups·group_kw)) − idle) / (1 − idle), clamped 0..1
event   = {at_s: t, action: "set-util", value: round(100·util)}
```

`util_pct` is an integer, so the seam has a quantization error of at most
`0.5% × (1−idle) × groups × 40 kW` = 0.92 kW at five groups. Heat below the idle floor
(`groups × 3.2 kW`) cannot be expressed; those ticks are flagged in `SeamResult.note`.
Section 9 lists the additive `set-heat-kw` event that removes both limits.

**Identity (heat out == heat in):** with the CDU uncapped (`cap_pct == 100`, no trips),
for every tick after the first `set-util`:
`|PhysicsCompute.liquid_watts/1000 − PhysicsCDU.it_load_kw| <= 0.5·(1−idle)·groups·group_kw/100 + 0.05`
and over the run `|∫liquid − ∫it_load| / ∫liquid <= 0.5%`. The CDU's own two-loop identity
(`it_load == sec ṁ·cp·ΔT == fac ṁ·cp·ΔT`) then carries the same watts to facility water,
so the chain XE9712 -> secondary loop -> facility is closed end to end.

**Pytest:** `compose/tests/test_c1.py::test_heat_out_equals_heat_in_across_the_seam`
(per-tick bound + integral bound, on idle->full ramp and on a `set-data-feed` starvation
run); `::test_air_share_never_crosses_the_seam` (`air_watts` is excluded — the CDU only
sees liquid; `liquid + air == dc` is asserted upstream so nothing is lost, it just goes to
the room); `::test_sub_floor_heat_is_flagged_not_hidden`.

### C2 — CDU caps and supply temperature come back as compute throttling (closed loop)

| | |
|---|---|
| Source | `PhysicsCDU`. `SimState.sec_supply_c` (°C), `cap_pct` (%), `bank_status`, `sec_flow_lpm` |
| Target | `PhysicsCompute` xe9712. Events `set-coolant-supply` (value °C), `set-workload` (`gpu_pct` scaled by `cap_pct/100`), `degrade-pump` (value = 1 − sec_flow/flow_setpoint), `restrict-tray` for tripped banks (bank i -> trays 3i..3i+2) |
| Units | °C -> °C; % -> %; L/min ratio -> fraction |
| Time base | 1 s -> 1 s, `to_events` deadband 0.25 °C / 1 cap point |

`coolant_supply_c` is bounded 17–45 in `SystemConfig`; adapter clamps and notes it.
The IRC cap is a power cap; PhysicsCompute has no power-cap event, so the cap is applied as
demanded `gpu_pct × cap`. This is the honest approximation: tokens fall with the cap, which
is the point.

**Fixed point.** C1 then C2 then C1 … The loop variable is the run-integrated liquid energy
`E = ∫liquid_watts dt`. Iteration k runs Compute with the events from CDU run k−1 (iteration
0: none), damping applied to the injected series: `x_k = 0.5·x_new + 0.5·x_{k−1}`.
Stop when `|E_k − E_{k−1}|/E_k < 0.005` or at `max_iter=12`. No randomness, fixed order, so
deterministic. Latched trips make the map discontinuous; when the trip set differs between
two consecutive iterations the solver pins the trip set from the later iteration and
continues, and records `note="trip set pinned at iter k"`.

**Identity:** at the fixed point the C1 identity holds **and**
`Compute.coolant_supply_c(t) == clamp(CDU.sec_supply_c(t))` within the 0.25 °C deadband
**and** Compute's delivered `tokens_per_s` integral is ≤ the open-loop C1 run's (a closed
loop can only cost compute, never add it).

**Pytest:** `test_c2.py::test_closed_loop_converges_and_is_deterministic` (two runs,
identical JSON; `iterations <= 12`; residual history monotone non-increasing after
iteration 2); `::test_warm_water_day_costs_tokens_in_the_coupled_run` (CDU
`set-facility-supply` +6 °C -> coupled tokens integral strictly below the uncoupled one);
`::test_uncoordinated_policy_trips_restrict_the_right_trays`.

### C3 — Exascale delivered throughput becomes the GPUs' data feed

| | |
|---|---|
| Source | `PhysicsStorage`, `product="exascale"`. `iops_delivered_k`, `iops_demand_k`, `throughput_gbs` (GB/s), `gpu_idle_due_to_data_pct`, `t_h` |
| Target | `PhysicsCompute`. `Workload.data_feed_pct` and `set-data-feed` events (value %) |
| Units | ratio -> % |
| Time base | 1 h -> 1 s via `hold`; one compute run per *distinct* storage operating point (deduplicated), each of `params.window_s` (default 600 s). A week with a drive failure yields 3–5 compute runs, not 168 |

`feed_pct = round(100 × min(1, read_delivered / read_demand))`, which is exactly the
quantity Storage already turns into `gpu_idle_due_to_data_pct`.

**Identity:** for each operating point,
`|(100 − Storage.gpu_idle_due_to_data_pct) − Compute.effective_gpu_util_pct / gpu_pct × 100| <= 1.0`
(the two engines' definitions of "idle because data was late" agree to one point — integer
`data_feed_pct` accounts for 0.5), and Compute's `gpu_hours_wasted` increases by
`idle_frac × gpus × window_h` within 2%.

**Pytest:** `test_c3.py::test_the_two_idle_gauges_are_the_same_number`;
`::test_a_node_failure_in_storage_shows_up_as_wasted_gpu_hours`;
`::test_starved_gpus_still_burn_power` (Compute's `stall_power_fraction`: dc falls by less
than tokens fall — the seam must not hide that).

### C4 — A gray failure in the fabric becomes lost tokens in the factory

| | |
|---|---|
| Source | `PhysicsFabric` (sn6000 or quantumx800). `delivered_gbps`, `demanded_gbps`, `goodput_penalty_pct`, `fct_ms`, `status_all_green`, `allreduce_gbps` |
| Target | `PhysicsAIFactory`. Step-time stretch applied to `TrainingJob.tokens_per_gpu_s`, per operating point; hourly via `hold` |
| Units | ms ratio -> dimensionless |
| Time base | 1 s -> 1 h via `steady_window` per fabric regime (healthy / gray / rerouted) |

Step-time model, stated as an estimate in `compose/constants.py` with units and source
like every other constant: a training step is a compute part and a collective part,
`comm_fraction = 0.25` (estimate). Collective time scales with `fct_ms`:

```
stretch      = (1 − comm_fraction) + comm_fraction × fct_gray / fct_healthy
tokens_scale = 1 / stretch
```

AIFactory has no mid-run event for fabric efficiency, so v1 runs the factory once per
fabric regime with `tokens_per_gpu_s × tokens_scale` and splices the traces at the regime
boundary (`splice()` restamps `tokens_total_b` and `cost_usd_m` cumulatively; asserted
monotone except at the factory's own failure rewinds). Section 9 lists the additive
`degrade-fabric` event that makes this one run.

**Identity:** `Factory.tokens_per_s(gray) / Factory.tokens_per_s(healthy) == tokens_scale`
within 0.5% at steady state, **and** the adversarial half carries across the seam:
`Fabric.status_all_green is True` on every gray tick while factory tokens/s is strictly
lower. Green and slower, both asserted, as PhysicsFabric does for itself.

**Pytest:** `test_c4.py::test_gray_failure_is_green_in_the_fabric_and_red_in_the_tokens`;
`::test_infiniband_credit_stalls_cost_less_than_ethernet_drops` (same demand, both
products); `::test_splice_preserves_cumulative_counters`.

### C5 — Server wall watts load the rack's phases

| | |
|---|---|
| Source | `DellPowerEdgeR760Thermal` and/or `PhysicsCompute` (xe7745 / xe9680 only). `SimState.ac_power_w` (W), `t` (s). Up to eight source runs |
| Target | `PhysicsRackPower`. `RackConfig.loads[i].power_w` (initial) and `set-load` events (`index`, `value` W); `phase` from `params.phases`, default round-robin A/B/C |
| Units | W -> W |
| Time base | 1 s -> 1 s, `to_events` deadband 10 W |

`RackLoad.power_w` is capped at 2000 W. An R760 fits. An XE9680 (~11 kW) does not: the
adapter splits it across its PSUs — one slot per PSU feed, `ac_power_w / alive_psus` — and
refuses (validation error, not a clamp) if a single PSU share exceeds 2000 W. XE9712 is
out of scope for this coupling; it is busbar-fed, which PhysicsRackPower does not model.

**Identity (watts in == watts out):** on every tick with no tripped phase,
`|Σ_sources ac_power_w(t) − RackPower.pdu_input_w(t)| <= 10 W × n_loads` (the deadband), and
the integral matches within 0.2%. RackPower's own identity (outlets = phases = PDU input)
then takes it to the wall.

**Pytest:** `test_c5.py::test_wall_watts_are_conserved_across_the_seam`;
`::test_a_fan_failure_upstream_moves_the_phase_meter` (kill-fan in R760Thermal -> fan
power up -> phase amps up, the fan-feedback loop visible at the breaker);
`::test_an_oversized_server_is_refused_not_clamped`.

### C6 — An attack timeline becomes a ransomware event in the backup appliance, and comes back as restore time

| | |
|---|---|
| Source | `PhysicsResilience` (powerprotect). `incident_active`, `corrupted_tb`, `clean_tb`, `blast_radius_gb`, `contained`, `t_h`; config `estate_tb`, `change_gb_day`, `restore_gbps` |
| Target | `PhysicsDataDomain`. `Dataset.full_tb = estate_tb`, `daily_change_pct = 100·change_gb_day/(1000·estate_tb)`; events `ransomware-start` (`value` = % of dataset newly encrypted per day), `ransomware-stop` |
| Return | DataDomain `Summary.alarm_day`, `ingest_gbps`, `dedupe_ratio` -> Resilience rerun with `detection` timing and `restore_gbps` informed by the appliance |
| Units | GB/h -> %/day: `value = 100 × (spread_gb_h × 24 / 1000) / estate_tb`; h -> day: `at_day = floor(t_h / 24)` |
| Time base | 1 h -> 1 d via `mean_pool` (24), events floor to the day |

Two-pass, open (not iterated): pass 1 Resilience gives the attack; DataDomain reads it from
the ingest side; pass 2 Resilience reruns with detection latency set from the entropy alarm
(`(alarm_day − start_day) × 24 h`, used only if earlier than Resilience's own detection).

**Identity:** encrypted volume agrees across the seam —
`|DataDomain.encrypted_fraction_pct(day) / 100 × full_tb − Resilience.corrupted_tb(24·day)| <= one day of spread`
until containment; and pass-2 `rto_hours == decide_h + restore_tb × 8000 / (restore_gbps × 3600)`
using the same TB on both sides (Resilience's RTO law, unchanged — the seam must not alter
it, only feed it). Scope boundary of PhysicsResilience is inherited: the adapter passes
rates and sizes, nothing about technique, and `test_c6.py` re-runs that app's scope test
over the `compose/couplings/c6_*` source.

**Pytest:** `test_c6.py::test_both_engines_agree_how_much_is_encrypted`;
`::test_the_entropy_alarm_beats_the_capacity_curve_in_the_coupled_run`
(`alarm_day < capacity notice`, the DataDomain lesson surviving coupling);
`::test_earlier_detection_shrinks_blast_radius_in_pass_two`.

### C7 — A hostile edge site becomes admin hours and truck rolls

| | |
|---|---|
| Source | `PhysicsXR`. `Summary.shutdown`, `throttle_seconds`, `SimState.fouling_pct`, `perf_lost_pct`; scenario `environment` |
| Target | `PhysicsFleet` (`product="nativeedge"`). `node-fault` events, `FleetConfig.site_class`, `sites`, `wan_reliable` |
| Units | s of a representative day -> faults per site-year -> events in days |
| Time base | 1 s -> 1 d via `steady_window`; one XR run = "a day at this site class" |

`params.site_mix` gives counts per XR scenario, e.g. `{phoenix_rooftop: 120, fargo: 80,
clean_closet: 200}`. Each XR run yields a site-day outcome: `shutdown` -> one fault per
occurrence interval (`params.heatwave_days_per_year`, default 12, estimate);
`throttle_seconds > 0` with no shutdown -> no fault, logged as degraded. Faults are
scheduled deterministically: `n = round(sites × days/365 × rate)`, spread evenly across
the run (`at_d = floor((i+0.5) × duration_d / n)`), MTBF-division style as AIFactory does.

**Identity:** `Fleet.faults_cum(end) − baseline.faults_cum(end) == n_injected` exactly, and
`Δ admin_hours_cum == n_injected × per_fault_hours(ops_mode, site_class)` within 1%, where
`per_fault_hours` is read from Fleet's constants (including `truck_roll_h`). The ledger
closes: every hour the hostile environment costs is attributable to an injected fault.

**Pytest:** `test_c7.py::test_injected_faults_are_all_accounted_for`;
`::test_a_filter_change_upstream_is_cheaper_than_the_truck_rolls_downstream`
(XR `clean-filter` event removes the shutdown -> Fleet admin hours fall by more than the
filter visit costs); `::test_fault_schedule_is_deterministic`.

### C8 — The capstone fed by real engines

The chain `PhysicsStorage -(C3)-> PhysicsCompute <-(C1,C2)-> PhysicsCDU`, plus
`PhysicsFabric -(C4)->`, all into `PhysicsAIFactory`. Specified in section 7 because it is
also a product feature.

## 5. Server and frontend

`compose/server/main.py` — FastAPI, **backend :8048, frontend :5221** (next free pair in
`ports.json` after PowerStoreElite's 8047/5220; 8015–8027 gaps are reservations for the
specced-but-unbuilt twins and are left alone). Add
`"Compose": {"frontend": 5221, "proxyDefault": 8048, "backend": 8048}` to `ports.json` and
a `components.json` row (family `composition`, status `built` when it is).

| Route | Returns |
|---|---|
| `GET /api/couplings` | the eight couplings as data: source/target, field map, units, identity text, tolerance, reading-leveled blurb |
| `GET /api/chains` | preset chains (one per coupling + the capstone + the closed loop) |
| `POST /api/run` | `Chain` -> `CoupledTrace` |
| `GET /api/run?chain=<id>` | preset chain, default params (CustomerSetup-style liveness GET) |
| `GET /api/constants` | `compose/constants.py` (`comm_fraction`, deadbands, `heatwave_days_per_year`) with unit/source/estimated |
| `GET /api/levels` | shared `leveling.py`, byte-for-byte |

The server calls `compose.run` in-process. It does not call the twins' servers, and the
twins do not need to be running.

**Couplings page** (`#couplings`, Dell clean-design chrome, dark diagrams, no eyebrow text,
no step numbers, no divider rules):

- Left: the chain as a row of engine cards joined by seam connectors. Each connector shows
  the identity and a live `lhs = rhs` readout at the cursor; a broken seam turns the
  connector red and says by how much.
- Centre: stacked strip charts on the common time base, source field directly above the
  target field it became, so the hand-off is visible as two curves that match.
- Right: the injected events diff ("what the adapter wrote into the target scenario"), the
  target's own validations, and for closed chains a residual-per-iteration chart with an
  iteration scrubber — stepping through iterations shows the loop settling.
- One playback clock, in `App.tsx`, driving all stages through `timeline`. Reading-level
  control in the header; leveled prose on coupling blurbs and identities (1/3/5 authored).
- Each engine card deep-links to the twin's own frontend (`data-twin-port` liveness chip,
  reusing the CustomerSetup pattern).

Tests: `compose/tests/test_api_surface.py` pins the six routes by name;
`test_engine_purity` as above; `frontend/smoke.json` for `scripts/smoke.sh`.

## 6. Determinism and cost

- Every adapter is a pure function `(source trace, target base scenario, params) ->
  target scenario`. `test_determinism.py` runs every preset chain twice and compares
  `model_dump_json()` byte for byte.
- Budget: a 7200 s engine run is ~7200 ticks; the closed loop is at most 12 × 2 runs.
  Preset chains use 900 s windows so `POST /api/run` stays under ~2 s. `to_events` caps
  injected events at 240.
- Float formatting: seam comparisons use unrounded engine outputs where available; where an
  engine rounds on the way out (`round(x, 1)` is common) the tolerance includes the
  rounding quantum and says so in `note`.

## 7. PhysicsAIFactory: "fed by real engines" mode

The capstone's README already says the `Scenario` shape "is the interface the per-product
engines could later feed". This is that.

**Shape.** The factory engine is not changed. `compose/couplings/c8_factory_fed.py`
builds the factory's inputs from upstream runs and calls the same `simulate`:

| Factory input | Aggregate mode (today) | Fed mode |
|---|---|---|
| `job.tokens_per_gpu_s` | constant 200 (Llama-3 arithmetic) | unchanged base × C4 `tokens_scale` per fabric regime |
| `data.storage_gbps` | one number | PhysicsStorage exascale `throughput_gbs` at steady state, scaled by `params.storage_racks`; failures arrive as `degrade-storage` events (value = % remaining = delivered/nominal) on the hour they happen in the storage trace |
| `compute.gpu_peak_w` | tier constant | PhysicsCompute xe9712 `steady gpu_power_w / gpus` at 100% — the wall-side number from the detailed model |
| PUE | per-cooling constant + `warm-day` events | derived: `(it + CDU pump_power_kw × racks + facility share) / it`; a CDU warm-water run becomes a `warm-day` event with `value = ΔPUE` |
| GPU throttling | none | C2 fixed point: `cap_pct < 100` hours become reduced `tokens_per_gpu_s` via splice |

**UI.** PhysicsAIFactory's `BuildPanel` gains a two-position control, "Aggregate" and
"Fed by engines". Fed mode fetches `GET :8048/api/run?chain=factory-fed` (through the vite
proxy key `/compose-api`; when the compose server is down the control is disabled with the
start command shown, same idiom as the CustomerSetup chips). Both traces render on the same
six headline instruments with the aggregate trace ghosted, so the difference is the
picture. This is an additive frontend edit in a component another workflow owns — small,
and deferred until that workflow is idle.

**The agreement test** — `compose/tests/test_c8.py`:

- `test_fed_and_aggregate_agree_when_nothing_is_wrong`: healthy storage, healthy fabric,
  design-day facility water. Steady-state `tokens_per_s` within **5%**, `facility_mw`
  within **8%**, `gpu_idle_data_pct` within **2 points**, `pue` within **0.05**. The
  tolerances are wide on purpose: the aggregate model is one efficiency number per block,
  and the test's job is to catch the two models drifting apart, not to pretend they are
  the same model.
- `test_where_they_disagree_the_reason_is_named`: for each instrument outside tolerance the
  fed chain must emit a `Divergence(instrument, aggregate, fed, cause)` whose `cause` is
  one of a closed enum — `stall_power` (starved GPUs still burn ~`stall_power_fraction` of
  demand in PhysicsCompute; the aggregate idles them to `gpu_idle_fraction`, so fed
  `facility_mw` is *higher* under starvation — this one is expected and pinned as a
  strict inequality), `hourly_rounding` (sub-hour events), `cap_vs_shed` (the CDU caps on
  temperature, the factory sheds on MW budget — different walls), `checkpoint_burst`
  (Storage's Exascale checkpoint period vs the factory's `checkpoint_interval_min`).
  An unexplained divergence fails the test. That is the "or explains why not".
- `test_starvation_is_the_same_story_in_both_modes`: halve storage; both modes' idle %
  rise to the shortfall within 2 points; tokens fall proportionally in both.

## 8. Static hosting

No backend on a static host, so the chain runs ahead of time.

- `compose/scripts/bake.py` (the impure edge, like `live_store.py`): runs every preset chain
  at reading levels 1/3/5 and writes `compose/frontend/public/baked/<chain>.json` and
  `couplings.<level>.json`, `constants.json`, `index.json` (with the git SHA and the
  engines' constants hash).
- `frontend/src/api.ts`: `VITE_STATIC=1` at build time swaps `fetch("/api/run?chain=x")`
  for `fetch("baked/x.json")`. Same types, same components. Relative URLs only, so it
  works under any sub-path.
- In static mode the scenario controls are limited to the baked presets plus baked
  parameter sweeps (each preset declares up to two swept params × five values = at most 25
  files per chain, ~150–400 KB each gzipped). Free-form `POST /api/run` is disabled with
  a line saying why.
- PhysicsAIFactory's fed mode under static hosting reads `baked/factory-fed.json` from a
  configurable base URL (`VITE_COMPOSE_BASE`), falling back to disabled.
- `compose/tests/test_bake.py::test_baked_files_match_a_fresh_run` regenerates in memory
  and compares to what is on disk, so a stale bake fails CI after any engine change
  (baked files are committed; they are small and they are the static site's data).
- A later option, not in scope: Pyodide running `compose` + engines in the browser. The
  engines are pure Python plus pydantic, so it is feasible; the bake is simpler and enough.

## 9. Additive engine changes that would tighten seams (optional, none blocking)

| Engine | Addition | Removes |
|---|---|---|
| PhysicsCDU | event `set-heat-kw` (value kW, overrides the bank formula) | C1's 0.92 kW quantization and idle floor |
| PhysicsCompute | event `set-power-cap` (value %) | C2's cap-as-demand approximation |
| PhysicsAIFactory | events `degrade-fabric` (value = tokens scale), `set-gpu-peak-w` | C4/C8 trace splicing |
| PhysicsRackPower | `RackLoad.power_w` upper bound 2000 -> 12000 | C5's per-PSU split |

Each is one `Literal` member, one `elif` in the event loop, one test. They belong to the
owning component's workflow, not to `compose/`.

## 10. Build order

1. `loader.py`, `resample.py`, `seam.py` + their tests (no couplings yet).
2. C1, C5 (open, conservation identities, simplest).
3. C3, C6, C7 (open, cross time base).
4. C2 (`fixed_point`), then C4 (`splice`).
5. C8 + the agreement test.
6. Server, Couplings page, bake, `ports.json` / `components.json` rows,
   `scripts/gen_root_pytest.py` awareness of `compose/` (it has no `app` package, so it
   needs no generated conftest — only `norecursedirs` must not exclude it).
7. PhysicsAIFactory fed-mode control.

## 11. Not in scope

Server-to-server calls; live coupling of two running frontends; coupling the narrative
Dell* twins (their traces are storyboards, not physics — C5's R760Thermal is the one
Dell*-named physics engine); sub-tick co-simulation (engines exchange whole traces, not
ticks — the closed loop is a fixed point over runs, which is why it is deterministic and
also why it cannot show transients faster than the CDU's 60 s loop lag honestly; the page
says so).
