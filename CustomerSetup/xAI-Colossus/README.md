# xAI Colossus — Memphis, Tennessee

Open `setup.html` in a browser for the drawing.

The publicly reported facts: Dell Technologies and Supermicro supplied the GPU servers for
xAI's Colossus supercluster. 100,000 GPUs were brought online in 122 days and doubled to
200,000 within about three more months. Servers are 8-GPU HGX systems, 64 GPUs per
liquid-cooled rack, roughly 1,500 racks at the first build. Every GPU gets a dedicated
400 GbE NIC on an NVIDIA Spectrum-X Ethernet fabric (~3.6 Tb/s of network per server).
The march toward one million GPUs runs on Dell-built NVIDIA Blackwell (B200/GB200) systems.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| 8-GPU HGX servers (first build) | `DellPowerEdgeXE9680/` | 5201 |
| GB200 rack-scale compute (expansion) | `DellPowerEdgeXE9712/` | 5181 |
| One GPU die under a matmul | `GPU/` | 5173 |
| Spectrum-X Ethernet fabric | `DellPowerSwitchSN6000/` | 5185 |
| Liquid cooling loop | `DellIR7000/` | 5182 |
| Training data tier (representative, not reported) | `DellExascale/` | 5184 |

Sources:
- https://www.datacenterdynamics.com/en/news/dell-and-super-micro-computer-to-provide-server-racks-for-xai-supercomputer/
- https://introl.com/blog/xai-memphis-colossus-100000-gpu-supercomputer-infrastructure
- https://www.datacenterfrontier.com/machine-learning/article/55244139/the-colossus-ai-supercomputer-elon-musks-drive-toward-data-center-ai-technology-domination
- https://introl.com/blog/xai-colossus-2-gigawatt-expansion-555k-gpus-january-2026
