# CustomerSetup — real customer deployments, drawn with this repo's twins

Each folder below documents one publicly reported customer deployment of Dell hardware,
and draws that setup as a diagram built out of the digital twins in this repository.
Open `index.html` for the gallery, or any folder's `setup.html` directly; each folder's
`README.md` carries the sources and the honest limits of what was reported.

The drawings are stylized mental models assembled from press releases, vendor
announcements, and trade-press coverage — not floor plans. Counts, wattages, and
topologies are illustrative unless a source states them; each page's note box and
per-block basis tags (sourced / inferred / representative) say exactly which is which.

| Folder | Customer | Setup | Twins referenced |
|---|---|---|---|
| `xAI-Colossus/` | xAI (Memphis, TN) | Colossus AI supercluster — 100k+ GPUs in 122 days, Dell PowerEdge GPU servers, Spectrum-X Ethernet, liquid cooling | XE9712, SN6000, IR7000, Exascale, GPU |
| `TACC-Horizon/` | Texas Advanced Computing Center (Austin, TX) | Horizon — largest academic supercomputer in the US, Dell IRSS liquid-cooled racks, 4,000 NVIDIA GPUs, Quantum-X800 InfiniBand | XE9712, IR7000, SN6000, iDRAC, GPU |
| `McLarenRacing/` | McLaren Racing (Woking, UK) | F1 factory HPC + trackside edge — PowerEdge, PowerStore, PowerScale, Dell AI Factory, ~1.5 TB per race weekend | R760, PowerStore, PowerScale, GPU, CloudIQ |
| `RHB-Bank/` | RHB Banking Group (Malaysia) | Air-gapped cyber-recovery vault — PowerProtect Cyber Recovery + CyberSense over the production estate | PowerProtect, CyberDetect, PowerStore, PowerMax |
| `Rackspace/` | Rackspace Technology | Managed private clouds — VMware Cloud Foundation on VxRail, PowerStore beside the HCI | VxRail, PowerStore, R760, PrivateCloud |
| `F1Soft/` | F1Soft (Kathmandu, Nepal) | National payments platform on PowerFlex software-defined storage | PowerFlex, R760, SN6000, CloudIQ |
| `DoD-FortZero/` | US Department of Defense | Project Fort Zero Target Level zero-trust validation — seven pillars, one policy engine, no perimeter drawn | FortZero, iDRAC, PrivateCloud, R760 |

## Viewing

`./CustomerSetup/scripts/serve.sh` serves the pages at `http://localhost:5170/`
(port reserved in the repo-root `ports.json`). Opening `setup.html` via `file://` also
works, but the liveness pings and shared localStorage behave uniformly only over http.

## How the pages work

- `shared/setup.css` + `shared/setup.js` are the template every page uses — light Dell
  clean-design chrome, dark inline-SVG diagram, no external assets. New setups start from
  these rather than copying styles.
- **Liveness chips.** Every twin link carries `data-twin-port` / `data-twin-start`;
  `setup.js` pings each port and renders a running / not-running chip, with the start
  command shown when a twin is down. Links only work while the twin's dev server runs.
  Links also carry `data-twin-trace` (the twin's trace endpoint, e.g. `poweron` →
  `GET /api/poweron`): when the twin is up and the pages are served over http, the chip
  enriches to what the twin would play — "running · 10 steps · idle → contained".
- **Archived sources.** Each folder's `sources.json` records every cited URL with title,
  publisher, access date, and the specific claims it supports — the citation survives
  link rot, and `test_sources_are_archived` fails if a page cites a URL without an entry.
- **Walkthrough.** Each diagram has a stepped narration (`window.WALKTHROUGH` + `data-wt`
  groups in the SVG): Back / Next / Show all, dimming everything outside the current
  step's focus.
- **Deep links into the twins.** The "What the twins would show you" sections link
  `http://localhost:<port>/#phase=<name>` — the twins' frontends open with the playback
  cursor at the first step of that phase (`#step=N` also works). The feature lives in each
  twin's `App.tsx`.
- **Reading registers.** Pages author two registers (novice and standard) and honor the
  twins' shared 1–5 reading-level choice (`localStorage` key `twin-reading-level`):
  levels 1–2 read novice, 3–5 standard. The control follows the reader between twins and
  these pages.
- **Scale badges.** Where a drawing shows fewer units than reality ("4 of ~1,500"),
  the ratio is on the SVG itself, so a screenshot can't mislead; representative blocks are
  drawn with dashed borders.
- **Block ↔ row cross-linking.** Table rows carry `data-wt-ref="group[,group]"`:
  hovering a row spotlights its blocks in the diagram (unless a walkthrough step is
  active), and clicking a block scrolls to and flashes its rows.

## Port registry

The repo-root `ports.json` records every twin's frontend/backend/proxy ports (scanned
from `vite.config.ts` and `scripts/start_backend.sh`) plus known historical collisions
and reserved ports. `test_ports_registry` fails if the registry drifts from disk, if any
vite proxy points at the wrong backend, or if a **new** collision appears — assign new
twins' ports by checking this file first.

## Tests

`python3 CustomerSetup/tests/test_links.py` (also runs under pytest) pins every
cross-reference: twin dirs exist, `data-twin-port` matches each twin's `vite.config.ts`,
relative links resolve, every `#phase=` name appears in that twin's `engine.py`, every
walkthrough focus names a real `data-wt` group, and every page keeps the honesty features
(sources, note box, basis tags, both registers). Keep it green when adding a setup.
