"""Pure rack power-on engine for the PowerEdge XE9712.

``simulate()`` returns the deterministic trace of what happens inside a
GB200 NVL72 rack from dark to accepting training jobs. Same purity rule as
every other twin in this repo: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``PowerOnState`` is plain data the
renderer consumes. ``cycle_cost`` marks the long stages (GPU init, NVLink
fabric training) so the UI dwells on them.

The storytelling beat that makes rack-scale AI different from a single
server: the order of operations is inverted from every air-cooled twin.
Nothing with a cold plate may power on until coolant is flowing — liquid
before silicon — and the finale is not an OS boot prompt but the NVLink
fabric *fusing* 72 separate GPUs into one domain that software addresses as
a single giant accelerator. Timing and wattage are illustrative but
plausible for a ~120 kW NVL72 rack; favor a correct mental model over
measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .models import PowerOnState

# The rack in this twin shows four of the real rack's 18 compute trays and
# two of its 9 NVLink switch trays — enough to see the pattern (anatomy.py
# says so honestly).
TRAYS = ["t1", "t2", "t3", "t4"]
NVSWITCH = ["nvswitch-a", "nvswitch-b"]
COOLING = ["cdu", "manifold"]
SHELVES = ["power-shelf-a", "power-shelf-b"]


def _all(prefix: str) -> list[str]:
    """Region ids for `prefix` on every tray, e.g. gpu-t1 … gpu-t4."""
    return [f"{prefix}-{t}" for t in TRAYS]


def simulate() -> list[PowerOnState]:
    """The rack's journey from dark to one fused 72-GPU domain, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="Rack integrated, facility connected",
            description=(
                "The XE9712 arrives from the factory as one integrated rack — "
                "18 compute trays, 9 NVLink switch trays, power shelves, and "
                "a rack full of pre-run copper cabling — rolled into place and "
                "connected to facility power and facility water. Nothing is "
                "on. Unlike a server you slide into a rack, this *is* the "
                "rack: Dell builds, cables, and tests it as a unit before it "
                "ships, because at these densities cabling by hand on site "
                "would take days."
            ),
            active_regions=[],
            power_watts=0,
            gpus_in_domain=0,
            elapsed_seconds=0,
        ),
        PowerOnState(
            step=1,
            phase="power",
            label="Power shelves energize the busbar",
            description=(
                "The power shelves — rack-mounted rectifier banks — convert "
                "facility AC to direct current and energize the busbar, a "
                "solid copper spine running down the back of the rack. Trays "
                "have no individual power supplies; each one clips onto the "
                "busbar, which is how a single rack can distribute more than "
                "one hundred kilowatts. On standby power the rack management "
                "switch and every tray's BMC (baseboard management "
                "controller, the same role iDRAC plays in a PowerEdge "
                "server) wake up and report in."
            ),
            active_regions=SHELVES + ["mgmt"],
            power_watts=800,
            gpus_in_domain=0,
            elapsed_seconds=10,
        ),
        PowerOnState(
            step=2,
            phase="coolant",
            label="Coolant loop primes — liquid before silicon",
            description=(
                "Before any high-power silicon is allowed on, the liquid "
                "loop must be proven. The in-rack CDU (coolant distribution "
                "unit) starts its pumps, pressurizes the supply and return "
                "manifolds, and watches for leaks and flow on every branch; "
                "quick-disconnect fittings on each tray let it seal any "
                "branch that fails. Roughly ninety percent of this rack's "
                "heat leaves through water, not air — a Blackwell GPU under "
                "load cannot survive on airflow — so the management plane "
                "interlocks GPU power on coolant flow. This ordering "
                "inverts every air-cooled twin in this repo: fans follow "
                "the load, but liquid must lead it."
            ),
            active_regions=COOLING + SHELVES,
            power_watts=2500,
            gpus_in_domain=0,
            elapsed_seconds=60,
            cycle_cost=2,
        ),
        PowerOnState(
            step=3,
            phase="trayboot",
            label="Compute trays power on — Grace CPUs boot in lockstep",
            description=(
                "With coolant flowing, the 18 compute trays clip power from "
                "the busbar and boot. Each tray holds two GB200 superchips — "
                "a superchip is one NVIDIA Grace CPU (72 Arm cores) fused to "
                "two Blackwell GPUs on one board with a chip-to-chip NVLink "
                "connection — so each tray brings up two Grace CPUs and "
                "readies four GPUs. The trays are identical and boot in "
                "parallel, exactly as VxRail nodes do: at this moment they "
                "are 18 independent Arm servers that happen to share a rack. "
                "Their ConnectX NICs and BlueField DPUs (data processing "
                "units — NICs with their own cores that offload networking) "
                "link up to the scale-out network."
            ),
            active_regions=_all("cpu") + _all("nic") + ["mgmt"],
            power_watts=14000,
            gpus_in_domain=0,
            elapsed_seconds=150,
            cycle_cost=2,
        ),
        PowerOnState(
            step=4,
            phase="gpuinit",
            label="72 Blackwell GPUs wake on their cold plates",
            description=(
                "Now the main event begins. Tray by tray — but in lockstep "
                "across the rack — the Blackwell GPUs come out of reset: "
                "VBIOS, HBM3e memory training on every stack, cold-plate "
                "temperatures stepping up as the CDU takes the heat. This is "
                "where the rack's power draw goes vertical: each GPU can "
                "draw on the order of a kilowatt, so seventy-two of them "
                "dominate everything else in the rack combined. The GPUs "
                "are alive but still seventy-two individuals — each one can "
                "so far talk only to its own tray."
            ),
            active_regions=_all("gpu") + COOLING,
            power_watts=90000,
            gpus_in_domain=0,
            elapsed_seconds=300,
            cycle_cost=3,
        ),
        PowerOnState(
            step=5,
            phase="fabric",
            label="NVLink switch trays boot — 5,000 links train",
            description=(
                "The single longest stage. The 9 NVLink switch trays in the "
                "middle of the rack boot their NVSwitch ASICs, and then the "
                "fabric trains: more than 5,000 copper links through the "
                "cable cartridge at the back of the rack come up one by one, "
                "each negotiated, tuned, and error-checked at 200 Gb/s per "
                "lane. NVLink is the scale-up fabric — it is to GPUs what "
                "the InfiniBand fabric is to PowerMax directors, but an "
                "order of magnitude faster than the scale-out network: "
                "1.8 TB/s in and out of every single GPU. Until the last "
                "link trains, there is no domain — just GPUs and switches "
                "shouting link-training patterns at each other."
            ),
            active_regions=NVSWITCH + _all("nic"),
            power_watts=98000,
            gpus_in_domain=0,
            elapsed_seconds=480,
            cycle_cost=5,
        ),
        PowerOnState(
            step=6,
            phase="fused",
            label="One NVLink domain — 72 GPUs become one accelerator",
            description=(
                "The signature moment, and the reason this rack exists: the "
                "fabric manager stitches every trained link into a single "
                "all-to-all NVLink domain. All 72 GPUs can now read and "
                "write each other's memory at 1.8 TB/s each — about 130 TB/s "
                "of total fabric bandwidth — so software sees something "
                "close to one enormous GPU with 13.5 TB of pooled HBM3e "
                "rather than 72 cards. This is what NVL72 means. A "
                "trillion-parameter model that cannot fit on any single GPU "
                "simply spreads across the domain as if it were one."
            ),
            active_regions=_all("gpu") + NVSWITCH,
            power_watts=105000,
            gpus_in_domain=72,
            elapsed_seconds=540,
            cycle_cost=2,
        ),
        PowerOnState(
            step=7,
            phase="ready",
            label="Burn-in passed — the rack accepts jobs",
            description=(
                "Health checks and a burn-in workload sweep the domain: "
                "every GPU, every NVLink path, every HBM stack exercised "
                "while the CDU holds the loop at temperature. Then the rack "
                "joins the cluster scheduler and accepts jobs. At full load "
                "it draws on the order of 120 kW — more than a thousand "
                "times the laptop twin's power budget — with the scale-out "
                "network (InfiniBand or Spectrum-X Ethernet) joining this "
                "rack to its neighbors, because a real AI factory is many "
                "NVL72 racks trained together. One rack, one giant GPU, "
                "ready for work."
            ),
            active_regions=(
                _all("gpu") + _all("cpu") + _all("nic")
                + NVSWITCH + COOLING + SHELVES + ["mgmt"]
            ),
            power_watts=120000,
            gpus_in_domain=72,
            elapsed_seconds=720,
        ),
    ]
