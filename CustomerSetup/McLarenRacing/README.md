# McLaren Racing — Woking, UK + trackside

Open `setup.html` in a browser for the drawing.

The publicly reported facts: McLaren Racing has been a Dell Technologies partner since 2018,
extending the deal in February 2026 through the seasons that produced back-to-back F1
Constructors' Championships (2024, 2025). Named hardware: Dell PowerEdge servers and HPC
systems for CFD, simulation, and AI; PowerStore and PowerScale storage for modelling
workloads; a Dell AI Factory processing up to 1.5 TB of data per race weekend across
factory, road, and trackside.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| Factory HPC + garage edge servers | `DellPowerEdgeR760/` | 5174 |
| The accelerators' work (CFD/AI matmuls) | `GPU/` | 5173 |
| PowerStore block storage | `DellPowerStore/` | 5175 |
| Fleet observability (representative) | `DellCloudIQ/` | 5180 |
| PowerScale file storage | `DellPowerScale/initial_spec.md` (specced, unbuilt) | — |

Sources:
- https://www.mclaren.com/racing/latest-news/2026/mclaren-racing-extends-relationship-with-dell-technologies/
- https://investors.delltechnologies.com/news-releases/news-release-details/mclaren-racing-extends-relationship-dell-technologies-accelerate
- https://www.dell.com/en-us/blog/mclaren-racing-turns-race-data-into-an-edge-with-dell-technologies-storage/
- https://channellife.com.au/story/mclaren-extends-dell-tech-deal-to-power-f1-data-push
