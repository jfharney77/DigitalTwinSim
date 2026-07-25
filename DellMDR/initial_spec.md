# DellMDR — managed detection and response digital twin (spec)

Status: **spec only.** Chosen in loop iteration 5 as one of the top three
untwinned Dell products; Dell Private Cloud was built first. Build this one
by following the pattern in `DellCyberDetect/` and `DellFortZero/`.

## Subject

**Dell Managed Detection and Response** — a fully managed 24×7 security
operations service monitoring, detecting, investigating and responding to
threats across endpoints, network, infrastructure and cloud, with detections
specific to Dell infrastructure and devices. Dell combines its own security
analysts with partner extended-detection platforms, including a partnership
with CrowdStrike incorporating Falcon Next-Gen SIEM.

## The one idea

**The alert is not the product. The person who read it is.**

This repo already has two security twins and they are both about machinery.
`DellCyberDetect` reads bytes to find corruption. `DellFortZero` removes the
perimeter so position grants nothing. Both are engineering answers, and both
share a limitation neither twin states: they produce *findings*, and a
finding nobody acts on is not a control.

That gap is where most real incidents live. The Target breach, and a long
line since, were detected — the alert fired, and it sat in a queue nobody
had capacity to work through. Modern security tooling generates far more
signal than any organization can staff against, and the bottleneck stopped
being detection a long time ago. It is triage.

So this twin's subject is not a product but a *capability*: 24×7 human
coverage, which is much harder to buy than software because it is three
shifts, holiday cover, retention, and expertise that takes years to build.
The honest framing is that MDR is an answer to a staffing problem wearing
the clothes of a technology problem, and the twin should say that plainly.

The trace should therefore make the funnel visible: an enormous number of
raw signals, narrowing through correlation, then through automated triage,
and finally to the small number a human actually reads — with the invariant
that **nothing reaches a human unenriched** and **nothing that reaches a
human is left unresolved**.

## Metaphor mapping

- **"Anatomy"** → a funnel drawn left to right, and the geometry *is* the
  lesson: telemetry sources (many, small), collection, correlation, the
  detection platform, automated triage, the analyst desk (one, and drawn
  small), then response and reporting. Geometry test:
  `test_the_funnel_narrows` — each stage's total drawn area must be
  strictly smaller than the previous stage's. The picture has to show the
  reduction, because the reduction is the service.
- **"Power-on trace"** → one night shift: a quiet baseline, a burst of
  signals, correlation, triage, one genuine incident escalated to a human,
  investigated, contained, and reported.

## Proposed model shapes

`SocMap` / `SocRegion` / **`TriageState`**.

```
RegionKind = source | collection | correlation | platform
           | automation | analyst | response | reporting
```

`TriageState` carries:

- `raw_signals: int` — hundreds of thousands
- `correlated_alerts: int` — thousands
- `triaged_alerts: int` — dozens
- `escalated_to_human: int` — single digits
- `unenriched_escalations: int` — **exists to be zero**. This twin's
  `droppedPackets`.
- `open_at_shift_end: int` — **also exists to be zero**: a queue that grows
  overnight is the failure this service exists to prevent
- `minutes_to_response: int`
- plus the standard `step / phase / label / description / active_regions /
  elapsed_minutes / cycle_cost`

## Proposed phases

`quiet → burst → collect → correlate → triage → escalate → investigate → contain → report`

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_the_funnel_only_narrows`** — at every step,
   `raw_signals >= correlated_alerts >= triaged_alerts >=
   escalated_to_human`. THE invariant, and the arithmetic of the whole
   service.
2. **`test_nothing_reaches_a_human_unenriched`** —
   `unenriched_escalations == 0` on every step. An analyst handed a raw
   alert has been handed the problem, not the answer; enrichment is what
   the service is actually selling.
3. **`test_the_queue_is_empty_at_shift_end`** — `open_at_shift_end == 0` at
   the final step. The characteristic failure of under-staffed security is
   a queue that grows faster than it drains, and the whole value of 24×7
   coverage is that it does not.
4. **`test_the_reduction_is_real`** — `escalated_to_human` must be smaller
   than `raw_signals` by at least three orders of magnitude at the burst.
   A funnel that barely narrows is a licence, not a service.
5. **`test_a_human_is_in_the_loop_for_every_escalation`** — whenever
   `escalated_to_human > 0`, the analyst region is active. Automation
   narrows; it does not decide.
6. **`test_response_time_is_bounded`** — `minutes_to_response` at the
   contain step is under an agreed threshold, and the trace should carry
   that threshold as a named constant so it is arguable.
7. **`test_investigation_is_the_longest_stage`** — unique max `cycle_cost`.
   The expensive part is a person understanding what happened, which is
   exactly the part that cannot be bought as software.
8. Standard: phase order, active regions exist, engine purity
   (AST-checked).

## Geometry invariant

`test_the_analyst_desk_is_the_smallest_region` — the human capacity is the
scarcest thing in the picture and must be drawn that way, in deliberate
contrast to the source band. It is the same trick the PowerFlex twin uses
for its metadata manager, used to make the opposite point: there, small
means "not on the data path"; here, small means "this is the constraint".

## Catalog (~9 categories, backend data)

Coverage scope (endpoints, network, infrastructure, cloud, Dell-specific
detections), the detection platform and partner XDR/SIEM, telemetry
collection, correlation and enrichment, automated triage and playbooks,
analyst tiers and the escalation model, response authority (what the
provider may do without asking), reporting and posture recommendations,
service levels and what they actually guarantee.

## Use cases (3)

1. A mid-sized organization that cannot staff three shifts — the base case,
   and the honest one: this is bought because 24×7 is a hiring problem, not
   because the tooling is better.
2. An organization that already has tooling and is drowning in its output.
3. A regulated business needing demonstrable coverage and an audit trail of
   who looked at what and when.

## A note on tone

The twin must be honest about what is given up. Outsourcing triage means an
external party decides what is worth your attention, and they do not know
your business as well as you do — so the tuning period is painful and the
first months produce both false escalations and missed context. The
catalog's "response authority" category is where this gets real: letting a
provider isolate a host at 3 a.m. without asking is either the point of the
service or an outage waiting to happen, depending entirely on how well the
boundaries were drawn.

## Cross-references to keep intact

- **DellCyberDetect** — produces findings; this twin is what happens to a
  finding. The two should name each other, because the pairing is the
  point: detection without response capacity is a queue.
- **DellFortZero** — its automation pillar makes the same argument, that
  continuous verification producing alerts for humans to triage in the
  morning is a perimeter model with better logging. This twin is the "in
  the morning" problem taken seriously.
- **DellPowerProtect** — recovery is where an unhandled incident ends up.
- **DellCloudIQ** — the same signal-to-insight funnel applied to
  infrastructure health rather than threats.

## Ports

Backend **:8027**, frontend **:5200** (after DellAPEX's 8026/5199).
Trace endpoint `GET /api/triage` returning `TriageResponse`.

## Sources

- <https://www.dell.com/en-us/lp/managed-detection-response>
- <https://www.dell.com/en-us/lp/dt/managed-detection-response>
- <https://www.storagereview.com/news/dell-technologies-enhances-managed-detection-and-response-service>
- <https://www.dell.com/en-us/blog/dell-technologies-strengthens-data-protection-security-speeds-threat-response/>
