# DellProMaxPlus — on-device inference digital twin (fifteenth component)

A digital twin of the **Dell Pro Max 16 Plus** with the **Qualcomm AI 100 PC
Inference Card** — the first mobile workstation to ship an enterprise-grade
*discrete* Neural Processing Unit. Two AI-100 NPUs, 32 AI cores, roughly
450 TOPS of 8-bit compute, and 64 GB of dedicated on-card AI memory. Dell
demonstrated a 109-billion-parameter Llama 4 model generating text on this
machine with no internet connection and no server behind it.

The counterpart to this repo's datacenter twins. Where the XE9712, IR7000,
Exascale, and SN6000 twins answer "how do you build a machine large enough
to train a frontier model", this one answers the question that comes after:
what happens when the model is small enough to live on the laptop.

## The one idea

**The weights never move.**

Every other accelerator twin in this repo is a story about transfer. The
XE9712 fuses 72 GPUs precisely so gradients can cross between them at
1.8 TB/s. The SN6000 exists to carry traffic between racks without dropping
it. The Exascale rack answers a read from four data servers at once. All of
them are fighting the same fight: the data is somewhere else, and getting it
here is the problem.

A discrete NPU with its own memory declines the fight. The model is compiled
offline into a container built for this specific silicon, streamed across
PCIe exactly once, and from then on it is simply *there* — 61 GB resident in
64 GB that belongs to the card and to nothing else. Generation reads it in
place. The bus goes quiet. The host CPU has nothing to do. And because
nothing is being fetched from anywhere, the network can be disconnected
without changing a single number, which is the last step of the trace and
the entire commercial argument: the data never leaves the machine because it
never had to.

`linkGbps` is nonzero during exactly one phase, and `test_engine.py` asserts
it.

## What it shows

- **Inference in motion** (`/`) — the life of a model on this machine:
  ahead-of-time compile, 61 GB crossing PCIe once, residency, prefill
  (compute-bound), decode (memory-bound), sustained generation at flat
  wattage, and finally the network disconnected with nothing changing.
- **Inside the machine** (`/#anatomy`) — the inference path drawn around one
  boundary: host CPU, system memory and the model library on the left; the
  PCIe strip in the middle; two AI-100 NPUs and 64 GB of AI memory on the
  right. The dashed weights path is derived from region kinds, so a
  different card is data, not code.
- **Components & options** (`/#components`) — platform, discrete NPU card,
  host processor, system memory, model library, other accelerators on board,
  toolchain, models that fit, thermal and power, deployment and security.
- **Use cases** (`/#usecases`) — regulated case review on material that
  cannot leave the building, an agent development loop with no metered API,
  and a field engineer where there is no connectivity at all.

## Run

```
./DellProMaxPlus/scripts/start_all.sh   # backend :8013, frontend :5186
./DellProMaxPlus/scripts/stop_all.sh
```

`start_all.sh` creates the backend venv, installs dependencies, starts
uvicorn in the background (logs to `logs/backend.log`), and runs Vite in the
foreground — Ctrl-C stops both. Then open <http://localhost:5186>.

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

Vite proxies `/api` → `http://localhost:8013`. If that port is taken by
another twin, run the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8113 npm run dev`.

Trace endpoint is `GET /api/inference`, returning `InferenceResponse`;
`/api/anatomy`, `/api/catalog`, and `/api/usecases` follow the same shape as
the other twins.

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order `off→compile→load→resident→prefill→decode→sustained→offline`
  never regresses.
- **The weights cross the link exactly once** — `linkGbps > 0` during the
  load phase and during no other phase. The defining property.
- **Never evicted** — `weightsResidentGb` is monotonic, reaches the full
  model, and stays exactly there. No paging is what makes the thousandth
  token arrive as predictably as the first.
- **The host is idle during generation** — no host-side region (CPU, system
  DRAM, SSD) is active once tokens are flowing. The counterpart to the
  Exascale twin's "metadata leaves the data path".
- **Sustained power never throttles** — from the first generating step,
  wattage holds within 10% of peak. The discrete-NPU claim versus a laptop
  GPU that spikes and then sags.
- **Disconnecting the network changes nothing** — the final step is a
  non-event, by construction.
- **Loading the model is the longest stage** (unique max `cycleCost`), and
  its cost is paid per model rather than per prompt.
- Geometry carries the lesson: every host-side region lies strictly left of
  the PCIe strip and every card-side region strictly right of it
  (`test_anatomy.py::test_the_boundary_is_drawn_and_the_sides_are_separate`).
  The AI memory spans both NPUs and is the largest block on the card,
  because capacity — not TOPS — is what decides which models run.

## Honesty notes

- Wattages, rates, and timings are illustrative but plausible; favor a
  correct mental model over measured numbers (project scope guardrail).
- The 64 GB / ~120B-parameter pairing implies weights quantized to roughly
  four bits. Dell's FP16 claim is about the *arithmetic*, not the storage —
  the twin says so explicitly rather than blurring the two, because only the
  storage decision is what makes the model fit.
- The only shipped visual is `frontend/public/promax-npu.svg`, a
  self-contained schematic drawn for this project with an honest credit
  line — not a Dell or Qualcomm product image.

## Sources

- [Dell — Reimagining AI: discrete NPU power with Dell Pro Max](https://www.dell.com/en-us/blog/reimagining-ai-discrete-npu-power-with-dell-pro-max/)
- [Dell Pro Max Plus 16 with Qualcomm AI 100 — product brief (PDF)](https://www.delltechnologies.com/asset/en-us/products/workstations/briefs-summaries/dell-pro-max-plus-workstation-with-qualcomm-npu-brief.pdf)
- [Dell Pro Max 16 Plus — product page](https://www.dell.com/en-us/shop/dell-laptops/dell-pro-max-16-plus-laptop/spd/dell-pro-max-mb16250-laptop)
- [Qualcomm Cloud AI SDK — architecture](https://quic.github.io/cloud-ai-sdk-pages/latest/Getting-Started/Architecture/)
- [Serving LLMs on Cloud AI 100 vs NVIDIA GPUs (arXiv 2507.00418)](https://arxiv.org/abs/2507.00418)
