# DellPrivateCloud — disaggregated-infrastructure digital twin (nineteenth component)

A digital twin of **Dell Private Cloud** — compute, storage, and networking
pooled and scaled separately under one control plane, with the hypervisor as
a swappable layer: VMware, Red Hat, Nutanix (added February 2026), or
Microsoft.

The direct counterargument to this repo's **VxRail** twin, and meant to be
read alongside it.

## The one idea

**You can change your mind.**

Hyperconverged infrastructure fused compute and storage into one node and
bought real, substantial simplicity with that coupling. The price was paid
in two currencies:

- **Fixed ratios.** Capacity is added by adding nodes, and a node brings
  processors and memory whether or not anyone wanted them. Estates routinely
  end up owning a third more of one resource than they will ever use —
  racked, licensed, powered, and depreciating.
- **Lock-in.** The software stack that performs the magic is the stack you
  are married to for the life of the estate.

Disaggregation un-buys the coupling and keeps most of the simplicity,
because a single control plane now provides what the fused node used to.
Dell cites research that **52% of IT leaders are weighing multiple
hypervisors** specifically to reduce lock-in, which is a fairly direct
summary of what the last few years taught the market.

Worth being honest about why this is possible now and not in 2012. The idea
was never clever. Hyperconvergence won for a decade because crossing a
network to reach storage cost more than keeping the drives local. The
architecture did not get smarter — the interconnect got fast enough that the
compromise stopped being necessary.

## What it shows

- **The estate** (`/`) — a private cloud built from separate pools, running
  120 workloads, then growing *one* resource, then acquiring a second
  hypervisor beside the first. Storage doubles without a single server being
  added; a second hypervisor arrives without a workload noticing or an
  operator gaining a second console.
- **Inside the stack** (`/#anatomy`) — control plane over workloads over
  four identical hypervisor slots over three separate resource pools.
- **Components & options** (`/#components`) — architecture (the decision
  that determines whether the later ones stay decisions), hypervisor,
  control plane, the three pools, workloads and migration, operations and
  consumption.
- **Use cases** (`/#usecases`) — an estate that wants the option to leave
  without leaving yet, a business whose data grows and whose compute does
  not, and a platform team running VMs and containers forever.

## The two steps worth stepping through

**`growstorage`** — capacity doubles from 200 TB to 400 TB and the compute
count stays at 48. On a hyperconverged cluster the same need is met by
adding nodes.

**`switch`** — a second hypervisor appears while workloads, downtime, and
control-plane count all hold still. It is also the trace's longest stage,
and honestly so: the claim is not that switching is quick, it is that
switching is possible without an outage.

## Run

```
./DellPrivateCloud/scripts/start_all.sh   # backend :8025, frontend :5198
./DellPrivateCloud/scripts/stop_all.sh
```

`start_all.sh` creates the backend venv, installs dependencies, starts
uvicorn in the background (logs to `logs/backend.log`), and runs Vite in the
foreground — Ctrl-C stops both. Then open <http://localhost:5198>.

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

Vite proxies `/api` → `http://localhost:8025`. If that port is taken, run
the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8125 npm run dev`.

Trace endpoint is `GET /api/cloud`, returning `CloudResponse`;
`/api/anatomy`, `/api/catalog`, and `/api/usecases` follow the same shape as
the other twins.

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order
  `off→pools→control→install→deploy→run→growstorage→switch→mixed` never
  regresses.
- **Compute and storage scale independently** — at the expansion, storage
  grows and compute does not move. The defining property, and the direct
  contrast with the VxRail twin.
- **Nothing scales that was not asked for** — the stricter form: across the
  whole trace, each resource changes only in the phases that exist to change
  it. Coupling would show up as a quantity moving in a step that had nothing
  to do with it.
- **One control plane regardless of hypervisor count** — two hypervisors,
  one console. Otherwise "we support both" means "we will sell you both
  problems".
- **The workloads never notice** — zero downtime on every step, and the
  workload count is constant through both the expansion and the migration.
- **The hypervisor is a choice, not a foundation** — no hypervisor is
  present on every step, and acquiring a second one moves nothing beneath
  it.
- **The control plane precedes any hypervisor** — disaggregation without a
  unified control plane is just three-tier again.
- **Cross-hypervisor migration is the longest stage** (unique max
  `cycleCost`).
- Geometry: `test_the_hypervisors_are_interchangeable_slots` requires four
  identical slots on one row; `test_the_pools_are_three_separate_columns`
  requires compute, storage, and network to be disjoint peers (on a
  hyperconverged diagram they would be one box);
  `test_the_stack_is_layered_top_to_bottom` pins control plane over
  workloads over hypervisors over pools.

## A note on the rendering

`StackView.tsx` draws unused hypervisor slots **dimmed rather than hidden**.
The empty slots are the product — an option not taken is still an option —
so hiding them would quietly reverse the lesson. It also draws three
separate connectors from the three pools up to the hypervisor row, because
they are three separate purchases. Keep both behaviors if you touch the
component.

## Honesty notes

- Counts and timings are illustrative but plausible; favor a correct mental
  model over measured numbers (project scope guardrail).
- The twin does not argue against VMware, and says so in the catalog:
  staying is a perfectly good decision, and the argument is against having
  no alternative.
- Cross-hypervisor migration is presented as slow and real — format
  conversion, testing, and care about what does not translate. Anyone
  selling it as effortless is selling something.
- The catalog also notes that licensing arithmetic drives more hypervisor
  decisions than technical merit does.
- The only shipped visual is `frontend/public/privatecloud-stack.svg`, a
  self-contained schematic drawn for this project with an honest credit line
  — not a Dell product image.

## Sources

- [Dell — why Dell Private Cloud outperforms HCI](https://www.dell.com/en-us/blog/rethinking-infrastructure-why-dell-private-cloud-outperforms-hci/)
- [Dell Private Cloud and HCI solutions](https://www.dell.com/en-us/shop/private-cloud-and-hci-solutions/sc/private-cloud-solutions)
- [Dell unveils disaggregated infrastructure strategy (Computer Weekly)](https://www.computerweekly.com/news/366624041/Dell-unveils-disaggregated-infrastructure-strategy)
- [Dell Private Cloud expands choice with Nutanix support](https://www.hpcwire.com/bigdatawire/this-just-in/dell-private-cloud-expands-choice-with-nutanix-support/)
