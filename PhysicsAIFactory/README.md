# PhysicsAIFactory — the Dell AI Factory capstone simulator

Product #9 of `physics_specs/10-additional-products.md`: **"Stand up an AI
factory"** — one integrated dashboard over compute, fabric, data, facility,
resilience, and cost. Backend :8046, frontend :5219.

## The framing, honestly

The spec calls this "a grand scenario mode spanning the whole suite rather
than new physics" — the final exam that only works if the shared-library
architecture was honored. The eight per-spec physics apps
(`PhysicsCompute/`, `PhysicsStorage/`, `PhysicsFabric/`, … from
`physics_specs/BUILD_PLAN.md`) were built after this one and share engines
by copy, not import, so **this app still sits the exam alone**: every subsystem is
a deliberate first-order aggregate of its own (one efficiency number for
the fabric, one bandwidth number for the data platform, one PUE for the
facility), and the `Scenario` shape is the interface those per-product
engines could later feed. What this app genuinely owns is the *couplings*
— the arithmetic by which a storage shortfall becomes idle GPUs, a warm
day becomes fewer tokens, and a checkpoint interval becomes money.

## What it simulates

An hour-by-hour deterministic trace of a training factory's life:
procurement → rack install (~2 h/rack — the Colossus pace) → bring-up →
ramp → steady training, with checkpoints, MTBF-scheduled failures that
genuinely rewind the token counter, and timed events (storage
degradation, warm days, multi-GPU failures). Six headline instruments:

- **tokens/s** = GPUs × per-GPU rate × (data availability × fabric
  efficiency × (1 − checkpoint tax) × ramp)
- **GPU idle due to data %** — the hero number: (1 − min(1,
  storage GB/s ÷ demand GB/s)) × 100
- **facility MW** — the power identity (subsystems sum to IT; facility =
  IT × PUE ≤ budget, enforced by shedding GPU clocks)
- **PUE**, **$/Mtok** (energy + straight-line capex amortization ÷
  tokens), and **time-to-first-token**

Identities pinned in `backend/tests/test_engine.py`: power balance every
tick; starvation emerging from the supply/demand ratio (not scripted);
the checkpoint interval's interior optimum (Young/Daly) emerging from
literal rollbacks; the facility budget as a hard ceiling under a warm-day
PUE excursion.

## Run

```
./PhysicsAIFactory/scripts/start_all.sh    # backend :8046 background, frontend :5219 foreground
./PhysicsAIFactory/scripts/stop_all.sh
```

Backend tests: `cd PhysicsAIFactory/backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd PhysicsAIFactory/frontend && npm run build`
Vite proxies `/api` → `http://localhost:8046`. `POST /api/simulate` takes
a Scenario; `GET /api/simulate` runs the default (8-rack factory,
frontier-LLM job).

## Guided scenarios

1. **Stand up an AI factory** — the full arc; the capex meter runs 112
   hours before the first token exists.
2. **The starved cluster** — a vision job (6 GB/s per GPU) whose data
   platform degrades to 25% of nominal; idle-due-to-data jumps to 65%
   (the platform had headroom), tokens/s falls 65%, and facility power
   falls only ~23%, because a data-stalled GPU busy-waits at an estimated
   65% of the power of the work it was denied (`stall_power_fraction`,
   the PhysicsCompute value). $/Mtok climbs for the rest of the run. The
   GPU twin's memory-bound roofline, building-sized.
3. **Checkpoint Goldilocks** — 5 vs 60 vs 480 minutes; the middle wins,
   and the validation panel computes the Young/Daly optimum for any build.
4. **Warm day at 90% of budget** — ΔPUE +0.2 turns weather into a compute
   problem; the engine sheds clocks so facility sits exactly on the
   ceiling.

## What we don't model

Parallelism strategy, network topology below one efficiency number,
storage behavior below one bandwidth number, batch-size dynamics, failure
clustering beyond deterministic MTBF arithmetic, electricity markets, or
real prices. Constants live in `backend/app/constants.py` with units and
a `source` field; several are arithmetic on public reporting (xAI
Colossus install pace — 1,500 racks in 122 days; Meta's Llama 3 405B
failure cadence — 419 interruptions in a 54-day snapshot on 16,384 GPUs —
and model-card throughput, ~140 tokens/s per H100, rounded to an
illustrative 200) and every estimate says so. Sub-hour losses round to the 1-hour
tick, which flatters checkpoint intervals at or below an hour.

## Companion twins

The narrative twins this dashboard aggregates (linked from the app
footer): `DellPowerEdgeXE9712` (:5181), `DellPowerSwitchSN6000` (:5185),
`DellQuantumX800` (:5202), `DellIR7000` (:5182), `DellExascale` (:5184),
and `GPU` (:5173).

## Graded labs

Three labs (`#labs`, `#lab=<id>`), built to `docs/LAB_PATTERN.md`: the engine's
acceptance scenarios turned into problems with a twist. `backend/app/labs.py`
is pure (AST-checked); `GET /api/labs` and `POST /api/labs/{id}/grade` are its
HTTP edge, and a static build grades in the browser through the same module.
Delivered work is `effectiveGpus` — tokens kept (net of rollbacks) ÷ one GPU's
full-rate output over the whole 720 h run, dark hours zero — an illustrative
proxy, not a benchmark. Every constraint (the storage failure, the warm spell,
the budget, the run length, the stock job and prices) is measured from the
trace, never a locked control.

| Lab | Difficulty | The lesson |
|---|---|---|
| `feed-the-worst-day` — Feed the cluster on its worst day | 1 | Supply is what the platform delivers today, not what was bought: size storage for the day it runs at 50% (2 × demand), and no further. |
| `spend-the-megawatt` — Spend the megawatt | 2 | Under a fixed power ceiling capped GPUs still draw idle watts, so work is an inverted U in rack count while $/Mtok only climbs: 9 racks beat 16. |
| `checkpoint-the-giant` — Checkpoint the giant | 3 | The interval alone cannot pass: storage sets t_ckpt, so it is the second checkpoint lever, and its 10 W per GB/s runs into the same megawatt wall as the GPUs. |
