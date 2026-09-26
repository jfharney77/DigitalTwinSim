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

from .leveling import L
from .models import PowerOnState, ScenarioInfo, SourceLink

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


def _nominal_base() -> list[PowerOnState]:
    """The rack's journey from dark to one fused 72-GPU domain, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="Rack integrated, facility connected",
            description=L(
                novice=(
                    "The rack arrives from the factory already built — 18 compute "
                    "trays, 9 switch trays, power units, and a rack's worth of "
                    "cabling run and tested before it shipped. It is wheeled into "
                    "place and connected to the building's power and water. Nothing "
                    "is switched on. This is not a computer you slide into a rack; "
                    "the rack is the computer, because at this density there are "
                    "thousands of cables and getting one wrong on site is not a "
                    "risk anyone wants to take."
                ),
                plain=(
                    "The XE9712 arrives as one integrated rack — 18 compute trays, "
                    "9 NVLink switch trays, power shelves, and pre-run copper "
                    "cabling — rolled into place and connected to facility power "
                    "and water. Nothing is on. Unlike a server you slide into a "
                    "rack, this is the rack: Dell builds, cables, and tests it as "
                    "a unit before shipping, because at these densities on-site "
                    "cabling is a risk rather than a task."
                ),
                standard=(
                    "The XE9712 arrives from the factory as one integrated rack — "
                    "18 compute trays, 9 NVLink switch trays, power shelves, and "
                    "a rack full of pre-run copper cabling — rolled into place and "
                    "connected to facility power and facility water. Nothing is "
                    "on. Unlike a server you slide into a rack, this is the "
                    "rack: Dell builds, cables, and tests it as a unit before it "
                    "ships, because at these densities cabling by hand on site "
                    "would take days."
                ),
                technical=(
                    "Factory-integrated rack: 18 compute trays, 9 NVLink switch "
                    "trays, power shelves, pre-run copper. Sited and connected to "
                    "facility power and water; nothing energized. The unit of "
                    "delivery is the rack, not the server — on-site cabling at this "
                    "link count is a defect source, not a task."
                ),
                expert=(
                    "Factory-integrated: 18 compute trays, 9 NVSwitch trays, power "
                    "shelves, pre-run copper. Sited, connected, dark. Unit of "
                    "delivery is the rack."
                ),
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
            description=L(
                novice=(
                    "The power units convert the building's alternating current "
                    "into direct current and energize the busbar — a solid copper "
                    "spine running down the back of the rack. The trays have no "
                    "individual power supplies of their own; each one clips onto "
                    "that spine. That is how a single rack can distribute more than "
                    "a hundred kilowatts, which is more than most small office "
                    "buildings use. On this standby power the rack's management "
                    "systems wake up, but none of the processors do."
                ),
                plain=(
                    "The power shelves — rack-mounted rectifier banks — convert "
                    "facility AC to direct current and energize the busbar, a solid "
                    "copper spine down the back of the rack. Trays have no "
                    "individual power supplies; each clips onto the busbar, which "
                    "is how one rack distributes more than a hundred kilowatts. On "
                    "standby power the rack management switch and every tray's "
                    "management controller come up; no compute silicon does."
                ),
                standard=(
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
                technical=(
                    "Rectifier shelves convert facility AC and energize the DC "
                    "busbar. No per-tray PSUs — trays clip to the busbar, which is "
                    "what makes >100 kW per rack distributable. Rack management and "
                    "per-tray BMCs come up on standby; no compute silicon "
                    "energized."
                ),
                expert=(
                    "Rectifier shelves energize the DC busbar; no per-tray PSUs. "
                    ">100 kW distributable. Rack mgmt and tray BMCs on standby "
                    "only."
                ),
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
            description=L(
                novice=(
                    "Before any high-power chip is allowed to switch on, the water "
                    "loop has to be proven. The in-rack cooling unit starts its "
                    "pumps, pressurizes the pipes feeding every tray, and watches "
                    "for leaks and for flow on each branch; fittings on each tray "
                    "let it seal off any branch that fails. About ninety percent of "
                    "this rack's heat leaves through water rather than air. This "
                    "ordering — liquid first, silicon second — is the reverse of "
                    "every air-cooled machine, and the cooling twin elsewhere in "
                    "this repo is entirely about the step being waited on here."
                ),
                plain=(
                    "Before any high-power silicon is allowed on, the liquid loop "
                    "must be proven. The in-rack coolant distribution unit starts "
                    "its pumps, pressurizes the supply and return manifolds, and "
                    "watches for leaks and flow on every branch; quick-disconnect "
                    "fittings let it seal any branch that fails. Roughly ninety "
                    "percent of this rack's heat leaves through water, not air. "
                    "Liquid before silicon inverts every air-cooled machine here, "
                    "and the IR7000 twin is this step from the other side."
                ),
                standard=(
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
                technical=(
                    "Coolant loop proven before any high-power silicon is permitted "
                    "on: CDU pumps start, supply and return manifolds pressurize, "
                    "per-branch leak and flow verified, quick disconnects available "
                    "to isolate a failed branch. ~90% of rack heat is liquid-borne. "
                    "The coolant-before-trayboot ordering is asserted in the engine "
                    "and inverts every air-cooled twin here."
                ),
                expert=(
                    "CDU primes, manifolds pressurize, per-branch leak/flow "
                    "verified before silicon is permitted. ~90% liquid-borne. "
                    "Coolant-before-trayboot asserted."
                ),
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
            description=L(
                novice=(
                    "With water flowing, the 18 compute trays draw power from the "
                    "busbar and start up. Each tray holds two superchips — a "
                    "superchip being one processor fused to two graphics chips on a "
                    "single board with a very fast direct connection between them — "
                    "so each tray brings up two processors and prepares four "
                    "graphics chips. The trays are identical and all start at the "
                    "same moment, like a row of identical computers switched on "
                    "together. At this moment they are still eighteen separate "
                    "computers."
                ),
                plain=(
                    "With coolant flowing, the 18 compute trays clip power from the "
                    "busbar and boot. Each tray holds two GB200 superchips — one "
                    "NVIDIA Grace CPU (72 Arm cores) fused to two Blackwell GPUs on "
                    "one board over a chip-to-chip NVLink — so each brings up two "
                    "Grace CPUs (144 cores a tray) and readies four GPUs. The trays "
                    "are identical and boot in parallel, every one at the same "
                    "moment: for now they are still eighteen separate computers."
                ),
                standard=(
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
                technical=(
                    "Trays draw from the busbar and boot. Two GB200 superchips per "
                    "tray — Grace CPU (72 Arm cores) fused to two Blackwell GPUs "
                    "over NVLink-C2C — so two CPUs up and four GPUs readied per "
                    "tray. Identical trays, parallel boot, lockstep asserted. Still "
                    "eighteen discrete systems at this point."
                ),
                expert=(
                    "Trays boot off the busbar: 2× GB200 superchip each (one "
                    "72-core Grace + 2× Blackwell over C2C per superchip). Lockstep "
                    "asserted. Eighteen discrete systems still."
                ),
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
            description=L(
                novice=(
                    "Now the main event. On every tray at once, the 72 graphics "
                    "chips switch on. Each one loads its built-in start-up "
                    "software, then tests and tunes its own memory, which is "
                    "stacked in layers right beside the chip. The metal plates that "
                    "carry cooling water across each chip begin to warm, and the "
                    "cooling unit takes that heat away. This is the biggest jump in "
                    "power in the whole start-up. In this model each chip is put "
                    "through a self-test under load as it wakes, and a working chip "
                    "can draw around a kilowatt, so seventy-two of them outweigh "
                    "everything else in the rack put together. A chip with nothing "
                    "to do draws far less. The chips are awake, but each can so far "
                    "talk only to the others on its own tray."
                ),
                plain=(
                    "The main event begins. On every tray at once, the Blackwell "
                    "GPUs come out of reset: VBIOS (the GPU's start-up firmware), "
                    "HBM3e memory training on every stack, cold-plate temperatures "
                    "stepping up as the CDU takes the heat. This is the largest "
                    "power step in the trace. This twin wakes each GPU straight "
                    "into a self-test under load, and a loaded GPU draws on the "
                    "order of a kilowatt, so seventy-two of them dominate "
                    "everything else in the rack combined. An idle GPU draws far "
                    "less. They are awake and still unconnected."
                ),
                standard=(
                    "Now the main event begins. On every tray at once, the "
                    "Blackwell GPUs come out of reset: VBIOS, HBM3e memory training "
                    "on every stack (HBM is high-bandwidth memory, DRAM stacked "
                    "beside the GPU), cold-plate temperatures stepping up as the "
                    "CDU takes the heat. This is the largest power step in the "
                    "trace, and the reason is a modelling choice: this twin wakes "
                    "each GPU straight into a self-test under load, and a loaded "
                    "GPU draws on the order of a kilowatt, so seventy-two of them "
                    "dominate everything else in the rack combined. A GPU idling "
                    "out of reset draws far less; the coolant-fault trace shows 68 "
                    "idle GPUs in a rack near 31 kW. The GPUs are alive but still "
                    "seventy-two individuals — each one can so far talk only to its "
                    "own tray."
                ),
                technical=(
                    "GPUs out of reset on every tray at once: VBIOS, per-stack "
                    "HBM3e training, cold-plate temperatures rising as the CDU "
                    "absorbs load. The largest single power step in the trace, by "
                    "modelling choice: the twin runs each GPU's self-test under "
                    "load as it wakes, ~1 kW per GPU. Idle GPUs out of reset draw "
                    "far less (the fault trace idles 68 of them in a ~31 kW rack), "
                    "so a real rack's step to full power lands at burn-in. Awake, "
                    "unfused."
                ),
                expert=(
                    "GPUs out of reset: VBIOS, HBM3e training, cold plates loading. "
                    "Largest power step because the twin loads each GPU in "
                    "self-test (~1 kW × 72); idle-out-of-reset draw is far lower, "
                    "cf. 68 idle GPUs at ~31 kW in the fault trace. Awake, unfused."
                ),
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
            label="NVLink switch trays boot — links train over 5,000 copper cables",
            description=L(
                novice=(
                    "The longest stage. The nine switch trays in the middle of the "
                    "rack start up. Their job is to connect every graphics chip to "
                    "every other one, and the web of connections they form is "
                    "called a fabric. Each connection is an NVLink, NVIDIA's fast "
                    "chip-to-chip link. There are 1,296 of them, carried by more "
                    "than five thousand copper cables at the back of the rack. "
                    "Every link now has to be trained: the two ends agree on a "
                    "speed, tune their signals to the cable between them, and check "
                    "for errors. The links train side by side, not one after "
                    "another, and the stage is still the longest because nothing "
                    "can go on until the last link passes. The cables are copper, "
                    "not optical fibre, which only works because the switch trays "
                    "sit in the middle of the rack so no cable runs far. Copper "
                    "needs no conversion to light, and that saves a great deal of "
                    "power."
                ),
                plain=(
                    "The single longest stage. The 9 NVLink switch trays in the "
                    "middle of the rack boot their NVSwitch chips, and then the "
                    "fabric trains: 1,296 NVLink links, 18 per GPU, carried by more "
                    "than 5,000 copper cables in the cartridge at the back. Each "
                    "link is negotiated, tuned, and error-checked at 200 Gb/s per "
                    "lane. They train in parallel, and the stage is long because "
                    "nothing proceeds until the last one passes. NVLink is the "
                    "scale-up fabric, the network that joins GPUs to each other — "
                    "copper rather than optics, which is only possible because the "
                    "switch trays sit mid-rack so no run is long."
                ),
                standard=(
                    "The single longest stage. The 9 NVLink switch trays in the "
                    "middle of the rack boot their NVSwitch ASICs, and then the "
                    "fabric trains: 1,296 NVLink links (18 per GPU), carried by "
                    "more than 5,000 copper cables in the cartridge at the back of "
                    "the rack, each negotiated, tuned, and error-checked at 200 "
                    "Gb/s per lane. The links train in parallel; the stage is long "
                    "because nothing proceeds until the last one passes. NVLink is "
                    "the scale-up fabric — the interconnect between GPUs, as a "
                    "backplane is between controllers — and an order of magnitude "
                    "faster than the scale-out network: 1.8 TB/s in and out of "
                    "every single GPU (NVIDIA's figure). Until the last link "
                    "trains, there is no domain — just GPUs and switches shouting "
                    "link-training patterns at each other."
                ),
                technical=(
                    "Max-dwell stage. NVSwitch trays boot, then 1,296 NVLink5 links "
                    "(72 GPUs × 18) train in parallel over >5,000 copper cables in "
                    "the rear cartridge — negotiation, equalization, error checking "
                    "at 200 Gb/s per lane; the dwell is the wait for the last link, "
                    "not a serial walk. Copper rather than optics is viable only "
                    "because the switch trays are physically central, bounding "
                    "every run length; the power saving over pluggable optics is "
                    "substantial."
                ),
                expert=(
                    "Max dwell: NVSwitch trays up; 1,296 NVLink5 links (72 × 18) "
                    "train in parallel over >5,000 copper cables at 200 Gb/s/lane. "
                    "Mid-rack switch placement bounds run length, making copper "
                    "viable over optics."
                ),
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
            label="One NVLink domain — every one of 72 GPUs reaches every other",
            description=L(
                novice=(
                    "The signature moment, and the reason this rack exists. The "
                    "software that runs the switch trays joins every trained link "
                    "into one network in which each graphics chip reaches every "
                    "other chip directly. The links are NVLink, NVIDIA's fast "
                    "chip-to-chip link, and the group of chips they join is called "
                    "an NVLink domain. All 72 chips can now read and write each "
                    "other's memory at very high speed. Programs still see 72 "
                    "chips, but the chips share work and memory so closely that "
                    "NVIDIA describes the rack as one giant graphics chip. Watch "
                    "the counter: it goes straight from zero to 72, and there is no "
                    "halfway state where some are joined and some are not."
                ),
                plain=(
                    "The signature moment, and the reason this rack exists: the "
                    "fabric manager, the software that runs the switch trays, "
                    "stitches every trained link into a single NVLink domain in "
                    "which every GPU reaches every other directly. All 72 GPUs can "
                    "now read and write each other's memory at 1.8 TB/s each — "
                    "about 130 TB/s of fabric bandwidth — across 13.4 TB of HBM3e, "
                    "the fast memory stacked beside each GPU (NVIDIA's figures). "
                    "Software still sees 72 GPUs, but joined this closely NVIDIA "
                    "describes them as one enormous GPU. The counter goes 0 to 72 "
                    "with nothing in between: the fuse is atomic."
                ),
                standard=(
                    "The signature moment, and the reason this rack exists: the "
                    "fabric manager stitches every trained link into a single "
                    "all-to-all NVLink domain. All 72 GPUs can now read and write "
                    "each other's memory at 1.8 TB/s each — about 130 TB/s of total "
                    "fabric bandwidth — across 13.4 TB of HBM3e (high-bandwidth "
                    "memory, the DRAM stacked beside each GPU). Those three figures "
                    "are NVIDIA's. This is what NVL72 means. Software still sees 72 "
                    "GPUs on 18 hosts, but every GPU is one hop from every other, "
                    "so a trillion-parameter model that cannot fit on any single "
                    "GPU spreads across the domain. That is why NVIDIA markets the "
                    "rack as a single GPU."
                ),
                technical=(
                    "Fabric manager stitches trained links into a single all-to-all "
                    "NVLink domain: 1.8 TB/s per GPU, ~130 TB/s aggregate, 13.4 TB "
                    "of HBM3e in total (NVIDIA's figures). Software sees 72 CUDA "
                    "devices across 18 hosts, not one device and not one address "
                    "space; NVIDIA markets the domain as a single GPU. The fuse is "
                    "atomic — gpusInDomain ∈ {0, 72}, asserted; no partial domain "
                    "exists at any step."
                ),
                expert=(
                    "One 72-GPU all-to-all NVLink domain: 72 CUDA devices, 18 "
                    "hosts, 1.8 TB/s/GPU, ~130 TB/s aggregate, 13.4 TB HBM3e total "
                    "(NVIDIA's figures). NCCL still runs 72 ranks; NVIDIA markets "
                    "it as a single GPU. Atomic fuse — gpusInDomain ∈ {0, 72}."
                ),
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
            description=L(
                novice=(
                    "Last comes a full check-up. Health checks and a long test "
                    "workload, called a burn-in, exercise the whole rack — every "
                    "chip, every link, every layer of memory — while the cooling "
                    "holds steady. Then the rack is added to the job scheduler, the "
                    "software that hands out work to the machines in a data centre, "
                    "and it starts accepting work. At full load it draws around 120 "
                    "kilowatts, more than three hundred times what the laptop twin "
                    "in this repo can draw from its charger. A separate outside "
                    "network joins this rack to others."
                ),
                plain=(
                    "Health checks and a burn-in workload sweep the domain: every "
                    "GPU, every NVLink path, every HBM stack exercised while the "
                    "CDU holds the loop at temperature. Then the rack joins the "
                    "cluster scheduler and accepts jobs. At full load it draws on "
                    "the order of 120 kW — more than three hundred times the laptop "
                    "twin's 360 W adapter — with the scale-out network joining this rack "
                    "to its neighbours."
                ),
                standard=(
                    "Health checks and a burn-in workload sweep the domain: every "
                    "GPU, every NVLink path, every HBM stack exercised while the "
                    "CDU holds the loop at temperature. Then the rack joins the "
                    "cluster scheduler and accepts jobs. At full load it draws on "
                    "the order of 120 kW — more than three hundred times the laptop "
                    "twin's largest power adapter — with the scale-out network "
                    "(InfiniBand or Spectrum-X Ethernet) joining this rack to its "
                    "neighbors, because a real AI factory is many NVL72 racks "
                    "trained together. One rack, one NVLink domain, ready for work."
                ),
                technical=(
                    "Burn-in sweeps every GPU, NVLink path, and HBM stack under "
                    "thermal load, then the rack joins the cluster scheduler. ~120 "
                    "kW at full load. Scale-out (InfiniBand or Spectrum-X) joins "
                    "this rack to the rest — the point at which the SN6000 twin "
                    "picks up."
                ),
                expert=(
                    "Burn-in across GPUs, links, and HBM under load; rack joins the "
                    "scheduler. ~120 kW. Scale-out fabric takes over past the rack "
                    "wall."
                ),
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


# --- Cooling-interlock telemetry -------------------------------------------
#
# The nominal steps above predate these fields; rather than touch each one,
# the values are stamped on by phase. (branches verified, GPUs powered,
# hottest GPU in °C.) Temperatures are illustrative: a shape, not a reading.
_NOMINAL_COOLING: dict[str, tuple[int, int, int]] = {
    "off": (0, 0, 22),
    "power": (0, 0, 22),
    "coolant": (18, 0, 22),
    "trayboot": (18, 0, 24),
    "gpuinit": (18, 72, 48),
    "fabric": (18, 72, 52),
    "fused": (18, 72, 56),
    "ready": (18, 72, 70),
}


def _with_cooling(state: PowerOnState) -> PowerOnState:
    branches, powered, temp = _NOMINAL_COOLING[state.phase]
    return state.model_copy(
        update={
            "branches_verified": branches,
            "gpus_powered": powered,
            "gpu_temp_c": temp,
        }
    )


def _nominal() -> list[PowerOnState]:
    return [_with_cooling(s) for s in _nominal_base()]


# --- The coolant-fault scenario --------------------------------------------

#: The tray whose coolant branch fails. The map draws 4 of 18 trays; this is
#: the third of the four drawn.
FAULT_TRAY = "t3"
FAULT_TRAY_REGIONS = [f"gpu-{FAULT_TRAY}", f"cpu-{FAULT_TRAY}", f"nic-{FAULT_TRAY}"]
#: The cold plates sit on the GPUs and the Grace CPUs; the NIC joins the
#: failed set once the whole tray is held off the busbar.
FAULT_COLD_PLATES = [f"gpu-{FAULT_TRAY}", f"cpu-{FAULT_TRAY}"]

FAULT_PHASE_ORDER = [
    "off", "power", "coolant",
    "flowfault", "isolate", "repair", "reverify",
    "trayboot", "gpuinit", "fabric", "fused", "ready",
    "leak", "traydown", "held",
]

# Seconds the first fault adds between the coolant step and tray boot, and
# the (illustrative) moment a day into production when the second one lands.
_REPAIR_DELAY_S = 5530
_LEAK_AT_S = 90_000


def _surviving(prefix: str) -> list[str]:
    return [f"{prefix}-{t}" for t in TRAYS if t != FAULT_TRAY]


def _coolant_fault() -> list[PowerOnState]:
    """Liquid before silicon, tested twice.

    Beat one: a tray branch fails verification before any GPU has power, so
    no GPU gets power and the domain counter never reads anything but 0 until
    the repaired rack fuses all 72. Beat two: a cold plate leaks under full
    load, and the tray loses power before the silicon gets any hotter.

    Modelled on NVIDIA's GB200 NVL72 leak handling (tray BMC detects and runs
    a shutdown timer; the building management system closes rack valves) and
    Dell's iDRAC default-action power-off leak events — see ``SCENARIOS`` for
    the links. Holding all 72 GPUs while one tray is out is this twin's site
    policy, not a hardware interlock: real racks can run a 68-GPU partition,
    and the prose says so. Every number is illustrative.
    """
    nominal = _nominal()
    by_phase = {s.phase: s for s in nominal}

    head = [
        by_phase["off"],
        by_phase["power"],
        # Same priming step, but verification has not passed yet.
        by_phase["coolant"].model_copy(update={"branches_verified": 0}),
    ]

    fault = [
        PowerOnState(
            step=0,
            phase="flowfault",
            label="Tray branch fails verification — low flow, leak sensor wet",
            description=L(
                novice=(
                    "The cooling unit checks the water branch feeding each of "
                    "the 18 trays. Seventeen pass. One does not: the flow "
                    "through that tray is below the minimum, and a moisture "
                    "sensor inside the tray reports that it is wet. The wet "
                    "sensor is a real part, one per tray; checking the water "
                    "flow tray by tray is this model's way of drawing the "
                    "rule. Most likely "
                    "a fitting did not seat properly when the tray was pushed "
                    "in. The rule itself is simple: a graphics chip gets power "
                    "only "
                    "after water has been proven to reach it, so this tray "
                    "stays off. The other 17 trays could be started without "
                    "it, and some sites do that. The operators in this story "
                    "bought one 72-chip machine and choose to wait for all of "
                    "it, so all 72 stay off. The operator sees a leak alarm "
                    "naming the tray, in the rack's management software. "
                    "Nothing has been damaged, because nothing that needs the "
                    "water has been switched on."
                ),
                standard=(
                    "The CDU (coolant distribution unit) checks flow on the "
                    "branch feeding each of the 18 compute trays. Seventeen "
                    "pass. One reads low, and that tray's BMC (baseboard "
                    "management controller) reports its leak sensor wet — "
                    "typically a quick-disconnect fitting that did not seat "
                    "when the tray was inserted. The tray's GPUs get no power "
                    "without verified flow. The hardware would let the other "
                    "17 trays boot and form a smaller NVLink partition, and "
                    "NVIDIA's software no longer needs every node present to "
                    "start. The operator in this twin runs the rack as one "
                    "72-GPU machine and holds the whole bring-up instead, so "
                    "the domain counter stays at 0 rather than heading for "
                    "68. That hold is a site policy, not a hardware limit. "
                    "The administrator sees a critical leak event against the "
                    "named tray over Redfish, the management API the BMC "
                    "speaks, in NVIDIA Mission Control. Those per-tray leak "
                    "sensors are documented, on cold plates and manifolds, and "
                    "read over Redfish; per-branch flow verification is this "
                    "twin's way of drawing the interlock rather than a "
                    "published feature of the rack. Nothing is damaged; "
                    "nothing with a cold plate has power yet."
                ),
                expert=(
                    "Per-branch verify: 17 of 18 pass; one branch low-flow with "
                    "tray BMC leak sensor asserted (likely an unseated QD). "
                    "Per-tray leak sensing is documented; per-branch flow "
                    "verification is this twin's device. "
                    "Site policy holds the whole bring-up rather than forming "
                    "a 68-GPU partition; gpusInDomain stays 0. Critical "
                    "Redfish leak event against the tray."
                ),
            ),
            active_regions=COOLING + ["mgmt"],
            failed_regions=FAULT_COLD_PLATES,
            power_watts=2500,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=0,
            gpu_temp_c=22,
            elapsed_seconds=90,
            cycle_cost=2,
        ),
        PowerOnState(
            step=0,
            phase="isolate",
            label="Tray held off the busbar, then pulled to seal its branch",
            description=L(
                novice=(
                    "The rack contains the problem in two steps. The first is "
                    "automatic: the tray is blocked from taking power from "
                    "the copper spine at the back of the rack, so water and "
                    "electricity cannot meet. The second needs a person. The "
                    "tray's water connections seal themselves when they are "
                    "pulled apart, so a technician slides the tray out a few "
                    "centimetres and no more water enters it. The other 17 "
                    "trays keep circulating. The alarm already says which "
                    "tray to pull. If the leak were large, the building's own "
                    "controls would shut off water and power to the whole "
                    "rack; this story stays with a small one."
                ),
                standard=(
                    "Two isolations, and only one is automatic. Electrical: "
                    "the tray is held off the busbar, so a wet board is never "
                    "energized. Liquid: this twin models no automatic "
                    "per-tray shut-off. The tray's "
                    "dry-break quick disconnects (fittings that seal "
                    "themselves when parted) close when a technician "
                    "unseats the tray, which is what Dell's leak event tells "
                    "the operator to do: remove power and disconnect the "
                    "hoses from the rack manifold. The other 17 branches keep "
                    "circulating. Automatic liquid isolation exists one level "
                    "up. For a rack-level leak NVIDIA's guidance has the "
                    "building management system open the rack's breakers and "
                    "shut its supply and return valves. This twin stops at "
                    "one tray and a small leak. The IR7000 twin draws the "
                    "same loop from the plumbing side, and the PhysicsCDU "
                    "simulator shows what the CDU does with the flow that "
                    "remains."
                ),
                expert=(
                    "Electrical isolation automatic (tray inhibited from the "
                    "busbar); liquid isolation manual (tray unseated, "
                    "dry-break QDs close). 17 branches stay in circulation. "
                    "Rack-level escalation (BMS trips breakers, closes "
                    "supply/return) not modelled."
                ),
            ),
            active_regions=["manifold", "mgmt"],
            failed_regions=FAULT_TRAY_REGIONS,
            power_watts=2400,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=0,
            gpu_temp_c=22,
            elapsed_seconds=100,
        ),
        PowerOnState(
            step=0,
            phase="repair",
            label="Technician reseats the tray — the rack waits",
            description=L(
                novice=(
                    "A technician pulls the tray, dries it, inspects the "
                    "fittings, replaces the one that failed, and pushes the "
                    "tray back in. This takes about an hour and a half here; a "
                    "real visit could take a day if a spare tray has to be "
                    "fetched. The other 17 trays are healthy and could run. "
                    "They wait anyway, because these operators run the rack "
                    "as one 72-chip machine and their jobs are sized for "
                    "exactly that."
                ),
                standard=(
                    "A technician pulls the tray, dries it, inspects the cold "
                    "plate loop, replaces the quick disconnect that failed, "
                    "and reseats the tray. The trace gives this about ninety "
                    "minutes; the figure is illustrative, and a swap from "
                    "spares or a parts wait would be longer. Seventeen healthy "
                    "trays sit idle for all of it. That is the cost of "
                    "scheduling the rack as one 72-GPU accelerator: under "
                    "that policy it comes up whole or stays down. A site that "
                    "keeps spare trays out of its partitions would be running "
                    "by now."
                ),
                expert=(
                    "Tray pulled, dried, QD replaced, reseated. ~90 min "
                    "illustrative. 17 healthy trays idle throughout: the "
                    "domain is scheduled as 72 or not at all."
                ),
            ),
            active_regions=["mgmt"],
            failed_regions=FAULT_TRAY_REGIONS,
            power_watts=2400,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=0,
            gpu_temp_c=22,
            elapsed_seconds=5500,
            cycle_cost=4,
        ),
        PowerOnState(
            step=0,
            phase="reverify",
            label="Loop re-primes — 18 of 18 branches verify",
            description=L(
                novice=(
                    "With the tray pushed back in its branch is open again, the air is bled out "
                    "of it, and the cooling unit repeats the same check it ran "
                    "the first time, on every tray and not only the repaired "
                    "one. This time all 18 pass and the moisture sensor is "
                    "dry. Only now does the rack release the hold on power, "
                    "and start-up continues from exactly where it stopped."
                ),
                standard=(
                    "The reseated tray's fittings open, its loop is bled of air, "
                    "and the CDU reruns verification on all 18 branches, not "
                    "only the repaired one. Flow is in range everywhere and "
                    "the tray's leak sensor reads dry, so the operator clears "
                    "the leak event and the interlock releases. Bring-up "
                    "resumes at the step it never reached. From here the "
                    "trace is the nominal one, about ninety minutes late."
                ),
                expert=(
                    "Tray reseated and degassed; full 18-branch re-verify "
                    "passes, leak event cleared, interlock released. Nominal "
                    "sequence resumes at trayboot."
                ),
            ),
            active_regions=COOLING + SHELVES + ["mgmt"],
            power_watts=2500,
            gpus_in_domain=0,
            branches_verified=18,
            gpus_powered=0,
            gpu_temp_c=22,
            elapsed_seconds=5590,
            cycle_cost=2,
        ),
    ]

    # The nominal bring-up, unchanged except for when it happens.
    resumed = [
        by_phase[p].model_copy(
            update={"elapsed_seconds": by_phase[p].elapsed_seconds + _REPAIR_DELAY_S}
        )
        for p in ("trayboot", "gpuinit", "fabric", "fused", "ready")
    ]

    leak = [
        PowerOnState(
            step=0,
            phase="leak",
            label="Cold-plate leak under load — the tray loses power first",
            description=L(
                novice=(
                    "A day into real work, at full power, the same kind of "
                    "moisture sensor trips inside one tray. The tray's own "
                    "management chip acts without asking anyone: it starts a "
                    "countdown and cuts the tray's power. It is counting, not "
                    "measuring temperature. The real countdown takes longer "
                    "than this one step, which is a simplification the model "
                    "makes to keep the order of events visible. Read the "
                    "numbers in that order. Rack power falls "
                    "at this step, and chip temperature does not rise at all. "
                    "The rack does not wait to see whether the chips overheat; "
                    "it removes the heat source before the cooling is lost. "
                    "The job running across all 72 chips ends, because one "
                    "machine made of 72 parts cannot lose four of them. The "
                    "counter reads 0, and 68 chips are still powered."
                ),
                standard=(
                    "A day into production at about 120 kW, a cold-plate leak "
                    "sensor trips in one tray. The response runs on a timer, "
                    "not on a thermometer: NVIDIA's fault table has the tray "
                    "BMC start a shutdown timer on a leak, and does not give "
                    "its length. The one duration NVIDIA does publish nearby "
                    "is a ten-minute going-down timeout on a large leak, in "
                    "the cluster manager's node state machine. This trace "
                    "compresses all of that into a single step, which is the "
                    "twin's simplification and the reason the numbers below "
                    "move as cleanly as they do. Dell's iDRAC event reference "
                    "for liquid-"
                    "cooled PowerEdge servers files leaks under a default "
                    "action of power-off. The tray's four GPUs and two Grace CPUs drop "
                    "off the busbar, rack power falls by one tray's share, "
                    "and the hottest GPU is no hotter than it was a step ago: "
                    "power drops before temperature rises. The NVLink domain "
                    "this twin models is a single 72-GPU partition, so losing "
                    "four members ends it. The counter reads 0 with 68 GPUs "
                    "still powered, and the running job fails: its next "
                    "access to the lost tray's memory returns an error, and "
                    "it restarts from its last checkpoint. The 68 survivors "
                    "are healthy and still linked. A real site can re-form a "
                    "smaller partition from them, or swap in a spare tray it "
                    "held back; that would be a new domain and is not "
                    "modelled here."
                ),
                expert=(
                    "Cold-plate leak sensor asserts at ~120 kW. Tray BMC "
                    "shutdown timer / default-action power-off removes the tray "
                    "from the busbar on a timer, not a thermal alarm; timer "
                    "length unpublished, compressed to one step here: rack power "
                    "falls one tray's share, max GPU temperature flat. Single "
                    "72-GPU partition ends: gpusInDomain 72 → 0 with 68 "
                    "powered. Re-partitioning survivors not modelled."
                ),
            ),
            active_regions=_surviving("gpu") + COOLING + ["mgmt"],
            failed_regions=FAULT_TRAY_REGIONS,
            power_watts=113400,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=68,
            gpu_temp_c=70,
            elapsed_seconds=_LEAK_AT_S,
            cycle_cost=3,
        ),
        PowerOnState(
            step=0,
            phase="traydown",
            label="Tray off and isolated — survivors idle, loop still flowing",
            description=L(
                novice=(
                    "The leaking tray is dead and marked for service. As at "
                    "start-up, its water connections seal only when a "
                    "technician pulls it, so that is the first job on the "
                    "ticket. The "
                    "other 68 chips have no job to run and drop to idle, and "
                    "the rack's power falls to about a quarter of what it "
                    "was. The pumps keep running for the 17 healthy trays, so "
                    "their chips cool down. The operator sees the leak alarm, "
                    "the tray marked as powered off, and the job marked as "
                    "failed and waiting to restart from its last save point."
                ),
                standard=(
                    "The tray is electrically isolated, and the management "
                    "software has opened a service ticket to unseat it so its "
                    "quick disconnects close, as in the bring-up fault. With "
                    "the job gone the 68 surviving GPUs fall to idle and the rack "
                    "settles near 31 kW. The CDU keeps the other 17 branches "
                    "flowing, so temperatures fall. In Mission Control the "
                    "administrator sees the leak event with its severity, the "
                    "tray marked down, the rack's electrical and liquid "
                    "isolation status (both still normal, because the leak "
                    "stayed small), and a failed job "
                    "waiting on its checkpoint. The PhysicsCDU simulator "
                    "covers the loop's side of this: what supply temperature "
                    "and pump speed do when load drops by three quarters in "
                    "seconds."
                ),
                expert=(
                    "Tray electrically isolated; service ticket to unseat it "
                    "and close its QDs. 68 survivors idle, rack ~31 kW, 17 branches in "
                    "flow, temperatures falling. Job awaits checkpoint "
                    "restart."
                ),
            ),
            active_regions=COOLING + ["mgmt"],
            failed_regions=FAULT_TRAY_REGIONS,
            power_watts=31000,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=68,
            gpu_temp_c=41,
            elapsed_seconds=_LEAK_AT_S + 30,
        ),
        PowerOnState(
            step=0,
            phase="held",
            label="Rack held out of the scheduler pending service",
            description=L(
                novice=(
                    "These operators take the rack out of the queue for new "
                    "work until the tray is repaired; another site might keep "
                    "running smaller jobs on the 68. The way back is the one already shown: "
                    "repair the tray, re-check all 18 water branches, and "
                    "rebuild the 72-chip machine in one step. What was lost is "
                    "the work done since the job's last save point, plus the "
                    "hours the rack spends waiting. No chip overheated, and "
                    "no water reached a powered circuit board. The sixty "
                    "seconds the rack spends checking water at every start-up "
                    "pay for that."
                ),
                standard=(
                    "Under this site's one-domain policy the scheduler drains "
                    "the rack and it waits for service. "
                    "Recovery is the path this trace has already walked: "
                    "repair, re-verify all 18 branches, fuse 0 to 72. The "
                    "loss is the work since the last checkpoint plus the "
                    "rack-hours out of service. The hardware is intact. No "
                    "GPU drew power on an unverified branch at any step, the "
                    "domain counter never read anything but 0 or 72, and "
                    "power fell before any temperature rose. All three are "
                    "asserted in tests/test_scenarios.py."
                ),
                expert=(
                    "Rack drained from the scheduler pending service (site "
                    "policy; a 68-GPU partition is possible); recovery "
                    "is repair → 18-branch re-verify → atomic fuse. Loss: work "
                    "since last checkpoint plus rack-hours. Interlock, {0, 72} "
                    "and power-before-temperature invariants held on every "
                    "step."
                ),
            ),
            active_regions=COOLING + SHELVES + ["mgmt"],
            failed_regions=FAULT_TRAY_REGIONS,
            power_watts=30000,
            gpus_in_domain=0,
            branches_verified=17,
            gpus_powered=68,
            gpu_temp_c=36,
            elapsed_seconds=_LEAK_AT_S + 300,
        ),
    ]

    sequence = head + fault + resumed + leak
    return [s.model_copy(update={"step": i}) for i, s in enumerate(sequence)]


SCENARIOS: list[ScenarioInfo] = [
    ScenarioInfo(
        id="nominal",
        name=L(novice="Normal switch-on", standard="Nominal power-on"),
        summary=L(
            novice=(
                "A dark rack becomes one machine: all 72 graphics chips "
                "joined into a single working whole, with the cooling water "
                "passing its checks first time."
            ),
            standard=(
                "Dark rack to one fused 72-GPU NVLink domain, with every "
                "coolant branch verifying first time."
            ),
            expert=(
                "Dark rack to a fused 72-GPU NVLink domain; all 18 coolant "
                "branches verify on the first pass."
            ),
        ),
        hero=L(
            novice="Graphics chips joined into one machine: 0, then 72",
            standard="GPUs in NVLink domain: 0, then 72",
        ),
        key_phases=["coolant", "fused"],
    ),
    ScenarioInfo(
        id="coolant-fault",
        name="Coolant fault",
        summary=L(
            novice=(
                "The cooling water fails its check on one of the 18 shelves "
                "of computing, before any chip has been switched on. The "
                "operators treat the rack as one 72-chip machine, so they "
                "keep every chip off until that shelf is repaired and all 18 "
                "water branches pass. Later, with the machine working hard, "
                "that shelf springs a leak and is switched off before "
                "anything can overheat. Timings, watts and temperatures are "
                "illustrative."
            ),
            standard=(
                "One tray branch fails flow and leak verification before any "
                "GPU has power. The operators run the rack as one 72-GPU "
                "machine, so they hold every GPU off until the tray is "
                "repaired and all 18 branches re-verify. Later a cold plate "
                "leaks under full load and the tray loses power before "
                "anything gets hotter. Timings, watts and temperatures are "
                "illustrative."
            ),
            expert=(
                "A tray branch fails flow and leak verification pre-power. "
                "The rack is operated as one 72-GPU domain, so bring-up holds "
                "until the tray is repaired and all 18 branches re-verify. A "
                "later cold-plate leak under load drops the tray before any "
                "thermal excursion. Timings, watts and temperatures are "
                "illustrative."
            ),
        ),
        hero=L(
            novice="Graphics chips joined into one machine: 0 or 72, never 68",
            standard="GPUs in NVLink domain: 0 or 72, never 68",
        ),
        key_phases=["flowfault", "reverify", "fused", "leak"],
        sources=[
            SourceLink(
                label=(
                    "NVIDIA Mission Control administration guide — leak "
                    "detection on GB200/GB300 NVL72 (cold-plate and manifold "
                    "sensors read by the tray BMC over Redfish; leak status, "
                    "electrical and liquid isolation shown to the operator)"
                ),
                url="https://docs.nvidia.com/mission-control/docs/systems-administration-guide/2.0.0/leak-detection.html",
            ),
            SourceLink(
                label=(
                    "NVIDIA Mission Control installation guide — building "
                    "management system integration (fault table: tray BMC "
                    "starts a shutdown timer; the BMS opens rack breakers and "
                    "closes supply and return valves for rack-level leaks)"
                ),
                url="https://docs.nvidia.com/mission-control/docs/nmc-software-installation-guide/2.3.1/integration-of-bms-with-bcm.html",
            ),
            SourceLink(
                label=(
                    "Dell iDRAC9 User's Guide — liquid cooling leak detection "
                    "on liquid-cooled PowerEdge servers (leak events, alerts "
                    "and the configurable power-off action)"
                ),
                url="https://www.dell.com/support/manuals/en-us/oth-r640/idrac9_7.xx_ug/cpu-and-gpu-leak-detection?guid=guid-2a4d4960-198d-43fe-a6cc-3a3ff574de6e&lang=en-us",
            ),
            SourceLink(
                label=(
                    "Dell iDRAC Error and Event Messages Reference — LCPF, "
                    "liquid cooling system default-action power-off events "
                    "(small leak is a warning, large leak critical; the "
                    "recommended action is to remove power and disconnect "
                    "the hoses from the rack manifold)"
                ),
                url="https://www.dell.com/support/manuals/en-us/poweredge-r440/eemi_automated_2024/lcpfliquid-cooling-system-default-action-power-off-event-messages?guid=guid-4626ce01-767f-4fd9-95db-891e3dbf2411&lang=en-us",
            ),
            SourceLink(
                label=(
                    "NVIDIA IMEX guide — connections, quorum and clean-up "
                    "(a lost node invalidates the memory other jobs imported "
                    "from it; a full quorum is no longer required to start, "
                    "which is why holding the whole rack is a policy)"
                ),
                url="https://docs.nvidia.com/multi-node-nvlink-systems/imex-guide/connections.html",
            ),
        ],
    ),
]

_TRACES = {"nominal": _nominal, "coolant-fault": _coolant_fault}


def simulate(scenario: str = "nominal") -> list[PowerOnState]:
    """The trace for ``scenario`` as pure data. ``simulate()`` is the nominal
    power-on, as it always was; unknown ids raise ``KeyError``."""
    return _TRACES[scenario]()
