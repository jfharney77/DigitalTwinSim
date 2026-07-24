# DellAutomationStudio — infrastructure-as-code digital twin (spec)

Status: **spec only.** Chosen in loop iteration 3 as one of the top three
untwinned Dell products; Cyber Detect was built first. Build this one by
following the pattern in `DellCloudIQ/` and `DellCyberDetect/`.

## Subject

**Dell Automation Studio** (available June 2026) and the wider **Dell
Automation Platform** — a CI/CD-native infrastructure orchestration toolkit
for DevOps and platform-engineering teams. A **blueprint** is a
declarative, infrastructure-as-code YAML file describing application
topology and the executables for automated actions. It leverages existing
Terraform and Ansible investment, and ships a **Blueprint AI Assistant**, a
generative-AI tool for authoring workflows. It integrates with Dell Private
Cloud and Dell Distributed Private Cloud.

## The one idea

**The gap between the drawing and the rack.**

Every other twin in this repo is a machine, and its anatomy is a picture of
something that physically exists. This one's subject is the *description* —
the YAML file that says what the estate should be. Which sets up the only
question that matters about infrastructure as code, and the one most
demonstrations carefully avoid: what happens when the description and the
reality disagree?

Because they always do. Someone resizes a volume by hand at 2 a.m. during
an incident. A firmware update lands out of band. A blueprint is applied
partially and the failure is never cleaned up. The industry word for this is
drift, and the honest observation is that drift is not an error state — it
is the *normal* state of any estate that humans can touch. A declarative
system's real value is not that it builds things; anyone can build things.
It is that it can continuously answer "does reality still match the
drawing?" and converge them when it does not.

So the trace here is not a deployment. It is: author a blueprint, apply it,
watch reality diverge from it, detect the divergence, and reconcile — with
the invariant that **the blueprint is never edited to match reality.** That
direction is the whole discipline. The moment you update the description to
excuse the drift, you have a document, not a control.

## Metaphor mapping

Following CloudIQ and Cyber Detect (software, not boxes):

- **"Anatomy"** → a two-plane diagram, and the geometry is the lesson.
  The **upper plane** is the declared state: the blueprint, the AI
  assistant that helped author it, version control, the plan. The **lower
  plane** is the actual estate: compute, storage, networking, runtimes.
  Between them, a single reconciliation band. A `test_anatomy.py` should
  pin that every declaration-plane region sits strictly *above* the
  reconciliation band and every estate region strictly below — the same
  trick the Pro Max Plus twin uses for its PCIe boundary, but here the
  boundary separates *intent* from *fact*.
- **"Power-on trace"** → the life of a blueprint, from authoring to
  steady-state convergence.

## Proposed model shapes

`PlatformAnatomy` / `PlatformRegion` / **`ReconcileState`**.

```
RegionKind = blueprint | assistant | versioning | plan | reconcile
           | compute | storage | network | runtime | observability
```

`ReconcileState` carries:

- `declared_resources: int` — what the blueprint says should exist
- `actual_resources: int` — what is really there
- `drifted_resources: int` — the difference that matters
- `blueprint_version: int` — **must never change during reconciliation**;
  this twin's `droppedPackets`
- `converged: bool`
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

## Proposed phases

`empty → author → plan → apply → converged → drift → detect → reconcile → steady`

- `author` — a blueprint is written, with the AI assistant scaffolding it
  from validated outcomes
- `plan` — the dry run: what *would* change. The step every team skips
  once and never skips again.
- `apply` — the estate is built to match
- `converged` — description and reality agree, briefly
- `drift` — someone changes something by hand during an incident; entirely
  reasonably, and now the estate is wrong
- `detect` — continuous comparison notices
- `reconcile` — the estate is moved back to the description, *not the
  reverse*
- `steady` — continuous convergence as the normal operating mode

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_the_blueprint_is_never_edited_to_match_reality`** — THE
   invariant. `blueprint_version` is constant across the entire
   drift/detect/reconcile sequence. Reality moves toward the description;
   the description does not move toward reality. If it did, drift would be
   self-certifying and the control would be theatre.
2. **`test_drift_is_detected_before_it_is_reconciled`** — no reconcile step
   precedes a detect step, and `drifted_resources > 0` at detection. You
   cannot fix what you have not noticed.
3. **`test_convergence_is_a_state_not_an_event`** — `converged` is true at
   the `converged` phase, false throughout drift and detection, and true
   again at `steady`. It is allowed to be lost; that is the point.
4. **`test_drift_returns_to_zero_only_by_reconciliation`** —
   `drifted_resources` becomes nonzero at drift and reaches zero only at or
   after reconcile, never by itself.
5. **`test_nothing_is_applied_without_a_plan`** — the first `apply` step
   follows the first `plan` step, and the plan region is active during it.
6. **`test_the_estate_never_exceeds_the_declaration`** — after
   reconciliation, `actual_resources == declared_resources`. Converged
   means equal, not merely "no errors".
7. **`test_reconciliation_is_the_longest_stage`** — unique max
   `cycle_cost`. Converging a live estate safely is slow, and pretending
   otherwise is how outages happen.
8. Standard: phase order, active regions exist, engine purity
   (AST-checked).

## Catalog (~10 categories, backend data)

Blueprint authoring (YAML, the AI assistant, validated outcomes), existing
IaC integration (Terraform, Ansible), version control and CI/CD
integration, the plan/dry-run stage, drift detection and reconciliation
policy, target infrastructure (compute, storage, network, runtimes),
Dell Private Cloud and Distributed Private Cloud integration, governance
and approval, observability, services and validated designs.

## Use cases (3)

1. A platform team giving developers self-service infrastructure without
   giving them the console.
2. An estate where drift is the normal state — reconciling hundreds of
   hand-modified systems back to a declaration.
3. A regulated environment where the blueprint *is* the audit evidence:
   what was declared, who approved it, and proof reality matched.

## Cross-references to keep intact

- **DellNativeEdge** (spec, iteration 1) — its blueprint-driven,
  zero-touch onboarding is the same declarative instinct at the edge. Both
  specs should point at each other; NativeEdge onboards devices,
  Automation Studio describes full-stack outcomes.
- **DellCloudIQ** — observability tells you what *is*; this tells you what
  *should be*. Drift is the difference, and the two are complementary.
- **DellPowerFlex** — an estate that can be reshaped while running is
  exactly what makes continuous reconciliation practical.
- **DellIDRAC** — server-level configuration profiles are the same idea one
  machine at a time.

## Ports

Backend **:8021**, frontend **:5194** (after DellPowerEdgeXE7745's
8020/5193). Trace endpoint `GET /api/reconcile` returning
`ReconcileResponse`.

## Sources

- <https://www.dell.com/en-us/lp/dt/automation-platform>
- <https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/automation-studio>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm>
- <https://www.dell.com/en-us/blog/dell-ushers-in-the-agentic-era-of-it-operations/>
