# TACC Horizon — Texas Advanced Computing Center, Austin

Open `setup.html` in a browser for the drawing.

The publicly reported facts: Horizon (announced November 2025) is the largest academic
supercomputer in the US — 300 petaflops, 10× TACC's Frontera. Dell builds it from
Integrated Rack Scalable Systems (IRSS): direct-liquid-cooled Dell PowerEdge servers on the
NVIDIA Grace Blackwell platform with Vera CPUs — one million CPU cores and 4,000 NVIDIA
GPUs — interconnected with NVIDIA Quantum-X800 InfiniBand. TACC's Dell lineage runs back
through Stampede3 (PowerEdge XE9640, direct liquid cooling) and Frontera (8,008 PowerEdge
nodes, the previous top academic system).

This is the closest public match to the repo's AI Factory quartet — it exercises three of
the four pillars directly.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| IRSS Grace Blackwell racks | `DellPowerEdgeXE9712/` | 5181 |
| Direct liquid cooling plant | `DellIR7000/` | 5182 |
| Quantum-X800 InfiniBand fabric | `DellQuantumX800/` | 5202 |
| The Ethernet fork, for contrast | `DellPowerSwitchSN6000/` | 5185 |
| Management plane (BMCs) | `DellIDRAC/` | 5177 |
| One GPU's work | `GPU/` | 5173 |

Sources:
- https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~11~dell-technologies-powers-taccs-new-supercomputer-horizon.htm
- https://investors.delltechnologies.com/news-releases/news-release-details/dell-technologies-powers-taccs-new-supercomputer-horizon
- https://tacc.utexas.edu/news/latest-news/2024/05/13/stampede3-supercomputer-enters-full-production-modernizes-to-meet-computational-needs/
