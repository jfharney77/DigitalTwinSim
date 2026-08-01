# spec_07 — RTX 4060 Laptop GPU profile (the user's real die)

**Goal:** add the NVIDIA GeForce RTX 4060 Laptop GPU (AD107, Ada Lovelace) as a
first-class die in both places dies live: a `GpuProfile` for the simulator and a
`DieAnatomy` entry for the anatomy page. This is the die the live CUDA mode
(spec_08) will light up, so its geometry must match what the driver reports.

Verified on this machine (WSL2, driver 596.36): `nvidia-smi` reports
"NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB".

## 1. The real numbers (anchor sources: NVIDIA Ada whitepaper, TechPowerUp AD107)

| Property | Value |
|---|---|
| Die | AD107, Ada Lovelace, TSMC 4N |
| SMs | **24** |
| FP32 CUDA cores | 3,072 (128 per SM) |
| Tensor cores | 96 (4th gen, 4/SM) |
| RT cores | 24 (3rd gen, 1/SM) |
| L2 cache | 32 MB |
| Memory | 8 GB GDDR6, 128-bit, ~256 GB/s |
| Boost clock | ~2.37 GHz (TGP-dependent) |
| TGP | 35–115 W (laptop OEM configurable) |
| Warp size | 32; max 1,536 resident threads/SM; max 24 resident blocks/SM |

The occupancy limits in the last row matter to spec_09's experiments — put them
in the profile so the UI can compute occupancy honestly.

## 2. `GpuProfile` entry (`profiles.py` — data, not code)

```python
RTX_4060_LAPTOP = GpuProfile(
    name="RTX-4060-Laptop",
    sm=SMGrid(rows=4, cols=6),            # 24 SMs — matches the physical count
    cores_per_sm=SMGrid(rows=8, cols=16), # 128 lanes/SM -> 3072 total
    memory=Memory(stacks=2, label="GDDR6 128-bit"),
    has_l2_bus=True,
)
```

**Render-density guardrail** (initial_spec §1 says tens to low hundreds of
elements): 3,072 per-core rects is too many to read and too heavy to animate.
`DieView` gains a density rule driven by the profile, not hardcoded: when
`totalCores > 512`, render **per-SM tiles** (24 tiles, each showing an
aggregate fill level = fraction of its lanes active) instead of per-core rects.
The existing Generic-128/512 profiles are unaffected. A `coreDetail` toggle can
still zoom one SM to per-core view (reuses the existing per-core renderer scoped
to a single SM).

Existing invariants hold unchanged: `totalCores = 4*6*8*16 = 3072`;
`activeCores <= totalCores`; `utilization = activeCores/totalCores`. The matmul
mapping (`tile_aware_core`) needs no change — tiles round-robin across 24 SMs.

## 3. `DieAnatomy` entry (`anatomy.py` — the annotated floorplan)

Add `ad107` to the anatomy page alongside the existing dies:

- Regions: 24 SM blocks grouped into **3 GPCs** (8 SMs each, per the Ada
  whitepaper's AD107 layout), the 32 MB L2 slab across the middle, 2 × 64-bit
  GDDR6 memory controller strips on the edges, PCIe 4.0 x8 interface, the
  Optical Flow Accelerator, NVENC/NVDEC block, and the display engine.
- Stats: the table in §1.
- Sources: NVIDIA Ada Lovelace whitepaper (GPU architecture PDF), TechPowerUp
  GPU database AD107 page. Layout is a stylized mental model traced from the
  whitepaper's block diagram, per the existing anatomy honesty rule; photos
  only if a credited, license-safe die shot exists (Fritzchens Fritz publishes
  CC-licensed die shots on Flickr — check AD107 availability; credit line
  required if used).
- Geometry invariants in `test_anatomy.py` as usual, plus: exactly 24 SM
  regions, exactly 3 GPC groups, exactly 2 memory-controller strips.

## 4. Why this die (copy for the anatomy page)

One honest paragraph: this is a *laptop* die — the interesting story vs. the
datacenter dies already on the anatomy page is the 128-bit bus (256 GB/s vs
HBM's terabytes) and the configurable 35–115 W TGP. The roofline ridge point
sits far left of a datacenter part: the same matmul that is compute-bound on
the H100 anatomy entry is memory-bound here at much smaller sizes. `analyze()`
already computes regimes from profile bandwidth — give the profile a real
`Bandwidth` entry (256 GB/s, ~15 FP32 TFLOP/s peak at ~2.4 GHz) so the roofline
read-out is truthful for the machine the user is sitting at.

## 5. Tests

- `test_engine.py` parametrization gains the new profile (all spec_01–05
  invariants must hold on a 24-SM die — they are profile-generic already).
- `test_anatomy.py`: geometry + the three counts in §3.
- Frontend: `npm run build` type-checks the density-rule prop.

## 6. Out of scope

No live data in this spec — spec_07 is pure data + one render-density rule.
The live CUDA feed that colors this die is spec_08; the CUDA lessons that
exercise it are spec_09.
