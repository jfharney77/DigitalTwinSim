# DellAPEX — consumption-model digital twin (spec)

Status: **spec only.** Chosen in loop iteration 5 as one of the top three
untwinned Dell products; Dell Private Cloud was built first. Build this one
by following the pattern in `DellPrivateCloud/` and `DellCloudIQ/`.

## Subject

**Dell APEX Infrastructure** — on-premises hardware, software and services
on a pay-per-use consumption model. Dell installs infrastructure with
**buffer capacity** beyond the committed amount, meters usage, and bills on
commitment plus buffer consumed. Capacity scales elastically within the
buffer at one consistent rate with no overage fees, and for products metered
on storage or memory, **billing is capped at 85% of total installed
capacity**.

## The one idea

**The hardware is already there, and you are not paying for it.**

Every other twin in this repo is about a physical or logical property —
where the bytes go, what the fabric refuses to do, which copy is clean.
This one is the only twin whose subject is *money*, and it earns its place
because the commercial model has a genuine architectural consequence that a
price list does not convey.

Cloud made elasticity the expected default, and on-premises infrastructure
could not offer it for an obvious physical reason: capacity you might need
in March has to be racked in January, and racked capacity is bought
capacity. The traditional answer was over-provisioning — buy for the peak,
run at the average, and write off the difference as the cost of being able
to grow.

APEX changes what is billed rather than what is installed. The buffer is
physically present, powered, and instantly usable; you simply do not pay for
it until you use it. The gap between *installed* and *billed* is the whole
product, and the trace should make that gap visible on every step.

The 85% cap is the detail that makes the model honest rather than
theoretical: without it, "elastic" and "unbounded bill" are the same
sentence. With it there is a ceiling, and the ceiling is below the hardware
you can actually reach — which is a strange and interesting thing to build
into a contract.

## Metaphor mapping

- **"Anatomy"** → a capacity diagram rather than a floorplan: one wide
  horizontal bar representing installed capacity, divided into *committed*,
  *buffer*, and *headroom above the billing cap*, with the metering,
  billing, and operations blocks beneath it. Geometry test:
  `test_the_bar_accounts_for_all_installed_capacity` — the committed,
  buffer, and above-cap regions must tile the installed bar exactly, with
  no gap and no overlap. The picture must add up, because the argument is
  arithmetic.
- **"Power-on trace"** → a year of consumption: quiet start, growth into
  the buffer, a spike, the cap being reached, and a scale-down.

## Proposed model shapes

`CapacityMap` / `CapacityRegion` / **`ConsumptionState`**.

```
RegionKind = committed | buffer | headroom | metering
           | billing | workload | operations
```

`ConsumptionState` carries:

- `installed_tb: int` — constant; the hardware never moves
- `committed_tb: int` — the contracted floor
- `used_tb: int` — actual consumption
- `billed_tb: int` — what appears on the invoice
- `overage_fees: int` — **exists to be zero**. This twin's
  `droppedPackets`.
- `provisioning_delay_days: int` — **also exists to be zero**: the buffer
  is already racked
- plus the standard `step / phase / label / description / active_regions /
  elapsed_months / cycle_cost`

## Proposed phases

`installed → quiet → steady → growth → spike → capped → scaledown → renewal`

- `installed` — hardware racked, including buffer nobody is paying for
- `quiet` — usage below commitment; billed at the commitment (the floor is
  real, and the trace should not hide it)
- `growth` — usage rises into the buffer; billing follows, at the same rate
- `spike` — a burst that would have required a purchase order in a
  traditional model, served instantly
- `capped` — usage passes 85% of installed; billing stops rising even
  though usage continues
- `scaledown` — usage falls and so does the bill, which is the half of
  "elastic" that on-premises models historically could not offer
- `renewal` — the commitment is re-set against what actually happened

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_the_hardware_never_moves`** — `installed_tb` is constant on
   every step. Nothing is delivered, racked, or removed during the entire
   year. THE structural claim.
2. **`test_billing_is_capped_below_installed_capacity`** — `billed_tb`
   never exceeds 85% of `installed_tb`, even at the spike where `used_tb`
   goes higher. The ceiling is real and sits below reachable hardware.
3. **`test_billing_never_falls_below_the_commitment`** — `billed_tb >=
   committed_tb` always. The floor is real too, and a twin that showed only
   the upside would be an advertisement.
4. **`test_no_overage_fees_ever`** — `overage_fees == 0` on every step,
   including the spike.
5. **`test_capacity_is_available_without_delay`** —
   `provisioning_delay_days == 0` on every step; contrast explicitly with
   the purchase-order path a traditional model requires.
6. **`test_billing_tracks_usage_between_the_floor_and_the_cap`** — in the
   band between commitment and cap, `billed_tb == max(committed, used)`
   exactly. No hidden multipliers.
7. **`test_the_bill_falls_when_usage_falls`** — at the scale-down,
   `billed_tb` strictly decreases. This is the half of elasticity that
   on-premises could not previously do, and the one worth testing.
8. **`test_the_spike_actually_exceeds_the_commitment`** — the claim is only
   interesting if the buffer is genuinely used; the spike must push
   `used_tb` well past `committed_tb`.
9. Standard: phase order, elapsed increasing, active regions exist, engine
   purity (AST-checked).

## Catalog (~9 categories, backend data)

Consumption models (subscription, pay-per-use, Data Center Utility),
committed capacity sizing, buffer sizing, metering and what is measured,
billing mechanics and the cap, covered products (storage, compute, private
cloud), operations and who runs it, exit and renewal terms, financial
treatment (capital versus operating expenditure).

## Use cases (3)

1. A seasonal business — retail, tax, ticketing — whose peak is four times
   its average and whose traditional option was buying for the peak.
2. A company that cannot forecast growth and has been over-provisioning
   defensively for a decade.
3. A finance-driven move from capital to operating expenditure, where the
   architecture is incidental and the accounting is the point.

## A note on tone

Like the circular-design spec, this twin is at risk of reading as a sales
sheet. The guards are structural: the commitment floor must be modelled
honestly (you pay it whether or not you use it), the trace must include a
quiet period where the customer is paying for capacity they are not
consuming, and the catalog must cover exit terms. A consumption model is a
genuine trade, not a free lunch, and the twin should be usable by someone
deciding *against* it.

## Cross-references to keep intact

- **DellPrivateCloud** — its operations catalog names consumption models
  explicitly: if storage can be added without compute, it can be billed
  without compute. The architecture and the commercial model reinforce each
  other, and neither is much use with the other absent.
- **DellCloudIQ** — metering and consumption telemetry are the same
  telemetry-to-insight path.
- **DellCircularDesign** (spec, iteration 4) — both twins are about what
  happens to hardware over time rather than what it does; the asset-recovery
  and renewal stories join up.

## Ports

Backend **:8026**, frontend **:5199** (after DellPrivateCloud's 8025/5198).
Trace endpoint `GET /api/consumption` returning `ConsumptionResponse`.

## Sources

- <https://www.dell.com/en-us/shop/apex/subscriptions/sl/apex-infrastructure>
- <https://www.dell.com/en-us/shop/dell-apex-subscription-as-a-service-solutions/sc/apex>
- <https://dell.com/en-us/dt/payment-solutions/flexible-consumption/data-center-utility.htm>
- <https://www.dell.com/en-us/blog/transform-your-it-subscription-meets-pay-per-use/>
