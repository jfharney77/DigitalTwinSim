# DellFortZero — zero-trust digital twin (eighteenth component)

A digital twin of **Dell Project Fort Zero** — Dell's turnkey zero-trust
private cloud, which in April 2025 completed the US Department of Defense's
assessment for **Target Level** validation as a sovereign, on-premises
deployment, tested against sophisticated attack.

## The one idea

**There is no inside.**

Every other twin in this repo carries its lesson in a boundary. The Pro Max
Plus draws a PCIe strip and pins that weights cross it exactly once. The
PowerProtect twin draws an air gap and pins that the attack cannot cross it.
The PowerFlex twin draws a client band and a node band with nothing between
them. Boundaries are how architecture diagrams normally carry meaning — and
how security was historically designed: verify at the perimeter, then treat
what is behind it as trusted.

That model fails identically every time. An attacker who gets in once
inherits everything the inside was permitted to do, and moves sideways at
leisure, which is why breach reports so consistently describe weeks of
undetected lateral movement after a single phished credential.

Zero trust does not harden the perimeter. It deletes the concept. Every
request is ruled on individually against one resource, using identity,
device posture, network context, workload and data sensitivity together, and
the ruling expires. A request from the corporate network, on a managed
laptop, by an authenticated employee is granted nothing by any of those
facts — they are evidence a policy engine weighs.

So this twin's map is drawn with **no enclosing shape at all**, and
`test_anatomy.py` enforces that nothing in it is large enough to become one.

`implicitTrustGrants` is zero on every step — most pointedly at the breach,
which is the exact step where a perimeter model would have handed over the
estate.

## What it shows

- **One request** (`/`) — a single access request under continuous
  verification: identity and posture, network context gathered as *evidence*,
  a policy ruling drawing on all seven pillars, a least-privilege grant with
  an expiry, continuous monitoring, the lease running out — and then an
  attacker compromising a host inside the network and reaching nothing.
- **Inside the architecture** (`/#anatomy`) — the seven DoD pillars, all
  drawn the same size, around a central policy engine. No perimeter.
- **Components & options** (`/#components`) — policy decision and
  enforcement, identity, device, network, application and workload, data,
  visibility and analytics, automation and orchestration. The categories are
  the DoD's pillars, not a product line.
- **Use cases** (`/#usecases`) — a sovereign environment that must assume it
  is already breached, a manufacturer whose suppliers need access but not
  trust, and an enterprise whose perimeter stopped existing years ago.

## The two steps worth stepping through

**`context`** — network location is gathered, confidence rises to 72%, and
`resourcesReachable` is still zero. In a perimeter model that step *is* the
authorization.

**`breach`** — an attacker holds a genuine position inside the network, with
the network and visibility pillars registering them. Resources reachable:
zero. Not because the attack was blocked, but because being inside was never
worth anything.

## Run

```
./DellFortZero/scripts/start_all.sh   # backend :8022, frontend :5195
./DellFortZero/scripts/stop_all.sh
```

`start_all.sh` creates the backend venv, installs dependencies, starts
uvicorn in the background (logs to `logs/backend.log`), and runs Vite in the
foreground — Ctrl-C stops both. Then open <http://localhost:5195>.

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

Vite proxies `/api` → `http://localhost:8022`. If that port is taken, run
the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8122 npm run dev`.

Trace endpoint is `GET /api/access`, returning `AccessResponse`;
`/api/anatomy`, `/api/catalog`, and `/api/usecases` follow the same shape as
the other twins.

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order
  `idle→request→verify→context→decide→grant→monitor→expire→breach→contained`
  never regresses.
- **Nothing is ever trusted implicitly** — `implicitTrustGrants == 0` on
  every step. The defining property.
- **Network location never authorizes** — the context step considers the
  network pillar and reaches zero resources; nothing is reachable before a
  decision.
- **The breach reaches nothing** — and `test_the_breach_is_actually_inside`
  checks the attacker genuinely holds the position a perimeter would have
  honoured, so the claim is tested rather than asserted.
- **Verification is continuous, not once** — the count climbs through the
  session and most steeply while access is live.
- **Trust is a lease, not a property** — a grant carries an expiry, and
  outside a grant there is no lease at all; at expiry confidence and
  reachability both return to zero.
- **Least privilege is literal** — at most one resource reachable, ever.
- **All seven pillars feed the decision** — the DoD model is an
  architecture, not a menu, and a gap in any pillar is a route around all of
  them.
- **The policy engine is consulted on every active step** — it is a decision
  point, not a gateway that steps aside once opened.
- **Continuous monitoring is the longest stage** (unique max `cycleCost`) —
  the honest location of zero trust's cost is not the login, it is the never
  stopping.
- Geometry: `test_nothing_is_drawn_as_a_perimeter` caps every region at 40%
  of the map's width and height; `test_the_pillars_are_co_equal` requires all
  seven identical in size (a diagram making one larger would be arguing with
  the reference architecture); `test_the_policy_engine_is_the_centre` puts
  the decision point closer to the map centre than anything else.

## Honesty notes

- Trust scores, verification counts, and timings are illustrative but
  plausible; favor a correct mental model over measured numbers (project
  scope guardrail).
- The DoD Target Level validation (April 2025) is Dell's stated achievement
  and is labelled as such. The pillar model is the DoD's reference
  architecture, not a Dell invention — that is why it is used here.
- The catalog is deliberately honest about the two ways adoptions fail:
  policy-engine latency (people route around it, and the exceptions become
  permanent) and alert volume (a system generating more alerts than anyone
  reviews has converted a security control into a compliance artefact).
- The only shipped visual is `frontend/public/fortzero-pillars.svg`, a
  self-contained schematic drawn for this project with an honest credit line
  — not a Dell product image.

## Sources

- [Dell achieves US DoD validation for zero-trust solution (April 2025)](https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~04~dell-technologies-achieves-us-department-of-defense-validation-for-zero-trust-solution.htm)
- [Dell — Zero Trust](https://www.dell.com/en-us/lp/dt/security-zero-trust)
- [Dell Technologies Project Fort Zero to transform security](https://investors.delltechnologies.com/news-releases/news-release-details/dell-technologies-project-fort-zero-transform-security)
