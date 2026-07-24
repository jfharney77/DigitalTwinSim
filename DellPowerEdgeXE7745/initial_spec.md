# DellPowerEdgeXE7745 — air-cooled AI server digital twin (spec)

Status: **spec only.** Chosen in loop iteration 3 as one of the top three
untwinned Dell products; Cyber Detect was built first. Build this one by
following the pattern in `DellPowerEdgeXE9712/` and `DellPowerEdgeR760/`.

## Subject

**Dell PowerEdge XE7745** — a 4U air-cooled AI server: dual AMD EPYC 9005
processors (up to 192 cores each), up to 24 DDR5 DIMMs to 3 TB at
6400 MT/s, PCIe Gen5, up to 8 front E3.S NVMe drives, 8 × 3200 W Titanium
power supplies in 4+4 redundancy, iDRAC10 with Silicon Root of Trust. The
accelerator bay takes **either 8 double-wide GPUs at 600 W each, or 16
single-wide GPUs at 75 W each**.

## The one idea

**The same watts, spent two ways.**

This repo's XE9712 twin is about the machine you build when nothing is
allowed to constrain you: 72 GPUs fused into one NVLink domain, liquid
cooling mandatory, a rack that arrives as a single integrated unit. It is
magnificent and most organizations cannot deploy it, because their
datacenter has no facility water, or a 15 kW rack limit, or a lease that
forbids modifying the room.

The XE7745 is the machine for that constraint, and the interesting thing is
that it does not present the constraint as a compromise — it presents it as
a *fork*. The same chassis, the same power envelope, and two completely
different machines depending on which accelerators go in:

- **8 double-wide GPUs at 600 W** — roughly 4.8 kW of accelerator, few and
  large. Big memory per GPU, high interconnect demand, suited to training
  and to inference on models too large for one small card.
- **16 single-wide GPUs at 75 W** — roughly 1.2 kW of accelerator, many and
  small. Far more independent execution contexts, suited to serving many
  concurrent small models, video transcode, or virtual desktop
  acceleration.

Those are not "high end" and "low end". They are answers to different
questions, and choosing between them is the most consequential decision in
configuring the box — more consequential than the CPU, the memory, or the
storage. A twin that makes that fork legible is doing something none of the
existing twins do, because every other twin in this repo has exactly one
shape.

## Metaphor mapping

- **"Anatomy"** → a top-down 4U chassis floorplan: front NVMe bay, the
  accelerator bay in the middle drawn as a **configurable** region set, dual
  EPYC sockets with their DIMM banks, the PCIe fabric, air-cooling path
  (front-to-back), and the power shelf. Airflow direction should be drawn
  and labelled, in deliberate contrast to the IR7000 twin's liquid loop.
- **"Power-on trace"** → the machine booting *and then loading a workload*,
  where the workload differs by configuration. The trace should be
  parameterized by the accelerator choice, which no other twin in this repo
  does.

## Proposed model shapes

`ChassisAnatomy` / `ChassisRegion` / **`ServerState`**, plus — and this is
the novel part — a `Config` request model.

```
RegionKind = cpu | memory | accelerator | storage | fabric
           | cooling | power | management
```

`ServerState` carries:

- `accelerators_online: int` — 8 or 16, depending on configuration
- `accelerator_watts: int` — ~4,800 or ~1,200
- `total_watts: int`
- `concurrent_contexts: int` — how many independent jobs can run; the
  number the dense-small configuration wins on
- `inlet_temp_c: int` / `exhaust_temp_c: int` — air cooling made visible
- plus the standard `step / phase / label / description / active_regions /
  elapsed_seconds / cycle_cost`

**`POST /api/simulate`** taking a `Config` (like the Alienware twin's
`Scenario`) rather than a fixed `GET`. This is the twin's structural
novelty and the reason it is worth building rather than being a variation
on the R760.

## Proposed phases

`off → power → post → thermal → gpuinit → workload → steady → throttlecheck`

- `thermal` — fans spin to the profile the accelerator configuration
  demands; this precedes GPU init, echoing the XE9712's "liquid before
  silicon" with air
- `throttlecheck` — the honest final beat: at 8 × 600 W the exhaust
  temperature is genuinely near the limit, and the trace should say so
  rather than pretending air cooling is free

## Signature invariants to enforce (backend/tests/test_engine.py)

1. **`test_both_configurations_fit_the_same_envelope`** — THE invariant.
   Simulate both configurations; `total_watts` must stay under the chassis
   limit in both, and the accelerator bay's region set must be the same
   physical space. Same box, same power, two machines.
2. **`test_the_fork_is_a_real_trade`** — the dense-small configuration must
   have strictly more `concurrent_contexts` *and* strictly less
   `accelerator_watts` than the few-large one. If one configuration
   dominated the other on every axis it would not be a choice.
3. **`test_air_cooling_is_honest`** — `exhaust_temp_c > inlet_temp_c` on
   every step under load, and in the 8 × 600 W configuration the exhaust
   must approach the stated limit at steady state. This twin must not
   present air cooling as free; the IR7000 twin exists because it is not.
4. **`test_fans_lead_the_accelerators`** — the first `thermal` step
   precedes the first `gpuinit` step, in both configurations. The air-cooled
   counterpart to the XE9712's "liquid before silicon".
5. **`test_accelerator_count_matches_the_configuration`** — 8 or 16, never
   anything else, and `acceleratorsOnline` never exceeds what the
   configuration declares.
6. **`test_gpu_init_is_the_largest_power_jump`** (as in the XE9712 twin).
7. **`test_power_supply_redundancy_holds`** — the 4+4 arrangement means
   the machine survives losing half the supplies; a step should demonstrate
   it.
8. Standard: phase order, monotonic counters, active regions exist, engine
   purity (AST-checked).

## Catalog (~11 categories, backend data)

Chassis and form factor, accelerator configuration (**the fork** — first
category, as the discrete-NPU card is first in the Pro Max Plus twin),
processors (EPYC 9005), memory, storage (E3.S NVMe), PCIe fabric and
topology, cooling and airflow, power and redundancy, management (iDRAC10,
Silicon Root of Trust — cross-reference the iDRAC twin), networking, AI
software stack and validated designs.

## Use cases (3)

1. An enterprise adding AI to a datacenter that cannot take liquid cooling
   — the whole reason this SKU exists.
2. An inference service running many concurrent small models on the
   16 × 75 W configuration.
3. Fine-tuning and mixed AI workloads on 8 × 600 W, as the on-ramp for an
   organization not yet ready for a GB200 rack.

## Cross-references to keep intact

- **DellPowerEdgeXE9712** — the unconstrained answer. This twin is the
  constrained one, and the pair should be readable together: liquid before
  silicon versus fans before silicon.
- **DellIR7000** — the reason liquid exists; this twin's throttle check is
  the argument for it.
- **DellPowerEdgeR760** — the general-purpose 2U server this is a sibling
  of; the boot sequence shares its shape.
- **DellIDRAC** — iDRAC10 and Silicon Root of Trust.
- **DellProMaxPlus** — the other twin about accelerator choice, at laptop
  scale.

## Ports

Backend **:8020**, frontend **:5193** (after DellCyberDetect's 8019/5192).
Trace endpoint `POST /api/simulate` returning `ServerResponse` — note the
POST, matching the Alienware twin rather than the fixed-GET twins.

## Sources

- <https://www.delltechnologies.com/asset/no-no/products/servers/technical-support/poweredge-xe7745-spec-sheet.pdf>
- <https://www.dell.com/en-us/shop/ipovw/poweredge-xe7745>
- <https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-ai-factory-with-nvidia-delivers-proven-path-to-enterprise-ai-roi.htm>
