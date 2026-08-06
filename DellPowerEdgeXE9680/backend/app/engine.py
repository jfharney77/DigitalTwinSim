"""Pure server power-on engine for the PowerEdge XE9680.

``simulate()`` returns the deterministic trace of what happens inside an
8-GPU HGX server from dark to accepting training jobs. Same purity rule as
every other twin in this repo: no FastAPI, no IO, no timers — the frontend
owns the playback clock, and each ``PowerOnState`` is plain data the
renderer consumes. ``cycle_cost`` marks the long stage (GPU init and HBM
training) so the UI dwells on it.

The storytelling beat that separates this twin from its rack-scale sibling
(the XE9712): here the NVLink fuse is small and quick — eight GPUs over an
NVSwitch complex soldered to one baseboard, not 5,000 cables — and the
counter stops at eight because the domain stops at the chassis wall. What
happens *next* is the point: eight NICs train, one per GPU, and everything
past eight travels over ordinary Ethernet or InfiniBand. Buy the box again
and again and the fabric does the rest — which is how xAI's Colossus put
100,000 GPUs to work in 122 days. Timing and wattage are illustrative but
plausible for a ~11 kW air-cooled 6U server; favor a correct mental model
over measured numbers (project scope guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import PowerOnState

# The eight SXM sockets on the HGX baseboard, and the eight scale-out NICs
# that pair with them one-to-one (anatomy.py draws both sets).
GPUS = ["g1", "g2", "g3", "g4", "g5", "g6", "g7", "g8"]
FANS = ["fan-bank-a", "fan-bank-b"]


def _gpus() -> list[str]:
    return [f"gpu-{g}" for g in GPUS]


def _nics() -> list[str]:
    return [f"nic-{g}" for g in GPUS]


def simulate() -> list[PowerOnState]:
    """The server's journey from dark to eight GPUs on the fabric, as pure data."""
    return [
        PowerOnState(
            step=0,
            phase="off",
            label="Racked and cabled, dark",
            description=L(
                novice=(
                    "The server sits in an ordinary rack, switched off. It is a "
                    "big machine — six rack units tall, about eighty kilograms — "
                    "but it is still a machine one team can install with a lift: "
                    "slide it in, connect power, plug in the network cables. That "
                    "ordinariness is the point. Unlike the rack-sized system "
                    "elsewhere in this repo that ships as one factory-built "
                    "cabinet, this box goes wherever a standard rack already is, "
                    "and a data center can take delivery of thousands of "
                    "identical ones and install them in parallel."
                ),
                plain=(
                    "The XE9680 sits racked and cabled, dark: a 6U, ~80 kg box "
                    "in a standard rack, installed with a server lift like any "
                    "other PowerEdge. Power is connected, the eight network "
                    "cables are seated, nothing is on. The contrast with the "
                    "XE9712 rack twin is the point — no factory-integrated "
                    "cabinet, no facility water hookup, just a (large) server "
                    "any data center can rack in numbers, in parallel."
                ),
                standard=(
                    "The XE9680 sits racked and cabled, dark. It is a big "
                    "server — 6U tall, on the order of 80 kg — but it is still "
                    "a server: it slides into a standard rack, takes ordinary "
                    "facility power, and needs no factory-integrated cabinet "
                    "and no building water. That ordinariness is the strategy. "
                    "The XE9712 twin's rack ships as one pre-built machine "
                    "because 5,000 NVLink cables cannot be run on site; this "
                    "box keeps its fast fabric entirely inside the chassis, so "
                    "installing a thousand of them is a thousand ordinary rack "
                    "jobs that can happen simultaneously — which is how "
                    "Colossus stood up 100,000 GPUs in 122 days."
                ),
                technical=(
                    "6U, ~80 kg, standard rack, ordinary facility power, no "
                    "liquid hookup in the air-cooled configuration. The scale-up "
                    "fabric is confined to the chassis, so deployment "
                    "parallelizes: N boxes are N independent rack-and-cable "
                    "jobs. Dark; PSUs connected; eight scale-out cables seated."
                ),
                expert=(
                    "6U HGX box, standard rack, no facility integration. "
                    "Scale-up fabric is chassis-internal; deployment is "
                    "embarrassingly parallel. Dark."
                ),
            ),
            active_regions=[],
            power_watts=0,
            gpus_in_domain=0,
            nics_up=0,
            elapsed_seconds=0,
        ),
        PowerOnState(
            step=1,
            phase="power",
            label="PSUs energize — iDRAC wakes on standby",
            description=L(
                novice=(
                    "Power arrives. The six power supplies at the rear come "
                    "alive and make a small standby voltage available, and on "
                    "that trickle the server's built-in management computer — "
                    "the iDRAC — boots. The iDRAC is a small always-on computer "
                    "inside the server whose whole job is looking after the big "
                    "one: it checks what hardware is present, watches "
                    "temperatures, and decides when the main processors may "
                    "start. Six supplies where an ordinary server has two is "
                    "the first hint of what this box is: together they can "
                    "deliver about eleven kilowatts, roughly what four homes "
                    "draw at once."
                ),
                plain=(
                    "The six rear PSUs energize and put out standby power, and "
                    "on it the iDRAC — the server's baseboard management "
                    "controller, a small always-on computer that supervises the "
                    "big one — boots, inventories the hardware, and starts "
                    "watching temperatures. Six supplies instead of a normal "
                    "server's two is the tell: together they can feed on the "
                    "order of eleven kilowatts, most of it destined for the "
                    "GPU tray."
                ),
                standard=(
                    "The six power supplies at the rear energize and present "
                    "standby power, and on it the iDRAC (integrated Dell "
                    "Remote Access Controller — the BMC, a small always-on "
                    "computer that supervises the server; this repo has a "
                    "whole twin about it) boots, inventories the hardware, "
                    "and begins watching thermals. Nothing else is on yet. "
                    "Six PSUs where an ordinary PowerEdge carries two is the "
                    "first tell of what this chassis is: together they can "
                    "feed on the order of 11 kW, and nearly all of it is "
                    "spoken for by the GPU tray."
                ),
                technical=(
                    "PSU bank (six supplies, N+N-capable) energizes; iDRAC "
                    "boots on standby, inventories, starts thermal watch. No "
                    "compute silicon on. The PSU count is sized for ~11 kW "
                    "sustained, dominated by the HGX tray."
                ),
                expert=(
                    "PSUs up, iDRAC on standby, inventory + thermal watch. "
                    "~11 kW envelope, HGX-dominated."
                ),
            ),
            active_regions=["psu-bank", "idrac"],
            power_watts=350,
            gpus_in_domain=0,
            nics_up=0,
            elapsed_seconds=10,
        ),
        PowerOnState(
            step=2,
            phase="post",
            label="The x86 host boots — a GPU server is still a server",
            description=L(
                novice=(
                    "The two main processors — ordinary Intel Xeon chips — "
                    "start up and run their power-on self-test: checking "
                    "themselves, tuning the thirty-two memory sticks (the "
                    "slowest part of any modern server's boot), and counting "
                    "the devices attached to them. From the host's point of "
                    "view the eight graphics chips are, for now, just eight "
                    "devices on its internal connectors, no different in kind "
                    "from a network card. Everything the GPUs will ever be fed "
                    "passes through this host first, but the host is the "
                    "servant here, not the star."
                ),
                plain=(
                    "The two Xeons boot and run POST: BIOS, training the 32 "
                    "DDR5 DIMMs (the slow part of any server boot — the R760 "
                    "twin dwells on the same step), and enumerating PCIe "
                    "devices. To the host, the eight GPUs are so far just "
                    "eight PCIe endpoints, no different in kind from the NICs "
                    "and NVMe drives beside them. The host stages data and "
                    "launches work, but in this machine it is the servant, "
                    "not the star."
                ),
                standard=(
                    "The two Intel Xeon processors boot and run POST "
                    "(power-on self-test): BIOS, DDR5 memory training across "
                    "32 DIMMs — the same stage the R760 twin dwells on, "
                    "because tuning memory timing is the slow part of any "
                    "server boot — and PCIe enumeration, the roll call of "
                    "attached devices. To the host, the eight GPUs are at "
                    "this moment just eight PCIe endpoints, addressed no "
                    "differently than the NICs and NVMe drives beside them. "
                    "That is worth pausing on: everything the GPUs will be "
                    "fed passes through this ordinary x86 computer, but in "
                    "this machine the host exists to serve the accelerators, "
                    "not the other way around."
                ),
                technical=(
                    "Dual Xeons POST: BIOS, DDR5 training across 32 DIMMs, "
                    "PCIe Gen5 enumeration. GPUs appear as PCIe endpoints "
                    "only — the NVLink complex is invisible to the host bus. "
                    "Host role is staging and launch, not compute."
                ),
                expert=(
                    "Dual-socket POST: DDR5 train, PCIe Gen5 enumerate. GPUs "
                    "are endpoints; NVLink invisible to the host. Host = "
                    "feeder."
                ),
            ),
            active_regions=["host-cpus", "nvme-bay", "idrac"],
            power_watts=1200,
            gpus_in_domain=0,
            nics_up=0,
            elapsed_seconds=90,
            cycle_cost=2,
        ),
        PowerOnState(
            step=3,
            phase="gpuinit",
            label="Eight SXM GPUs wake — fans ramp to a roar",
            description=L(
                novice=(
                    "The longest stage, and the loudest. The eight graphics "
                    "chips on the big board in the front half of the chassis "
                    "come out of reset one firmware step at a time, and each "
                    "one tunes its stacked high-speed memory — thousands of "
                    "tiny adjustments per chip. Power consumption goes "
                    "vertical, from about one kilowatt to nine, and the fan "
                    "wall spins up to hold the chips at temperature with "
                    "nothing but moving air. That roar is this machine's "
                    "signature: its bigger rack-scale sibling needs building "
                    "water to survive, but this box cools itself the way "
                    "servers always have."
                ),
                plain=(
                    "The longest stage, and the loudest. The eight SXM GPUs "
                    "on the HGX baseboard come out of reset — firmware, then "
                    "HBM training on every stack of high-bandwidth memory, "
                    "thousands of per-lane adjustments per GPU. Draw goes "
                    "vertical, ~1 kW to ~9 kW in one step, and the fan banks "
                    "ramp toward full speed to hold the tray at temperature "
                    "on air alone — the XE9712 needs facility water for this "
                    "moment; this box needs airflow and a hot aisle that can "
                    "take it."
                ),
                standard=(
                    "The longest stage, and the loudest. The eight SXM GPUs "
                    "(SXM is the socketed, high-power module form factor — "
                    "no card edge, no cable, bolted straight to the HGX "
                    "baseboard) come out of reset: firmware loads, then HBM "
                    "training — each GPU tunes the interface to its stacks "
                    "of high-bandwidth memory, thousands of per-lane "
                    "adjustments, the accelerator equivalent of the host's "
                    "DIMM training and the reason this stage holds the "
                    "trace's longest dwell. Power draw goes vertical, from "
                    "about one kilowatt to nine, and the fan wall behind the "
                    "front bay ramps toward full speed: this chassis holds "
                    "eight ~700 W devices at temperature with moving air "
                    "alone, which its rack-scale sibling cannot do at 72 "
                    "GPUs without building water. The GPUs are awake — and "
                    "still eight individuals."
                ),
                technical=(
                    "Max-dwell stage. Eight SXM devices out of reset: VBIOS, "
                    "per-stack HBM training (the accelerator analogue of DIMM "
                    "training). Largest power step in the trace, ~1.2 kW → "
                    "~9 kW. Fan banks ramp to hold ~700 W/device on air — "
                    "the air-vs-liquid line the XE9680L moves. Awake, "
                    "unfused."
                ),
                expert=(
                    "Max dwell: 8× SXM out of reset, HBM trains, largest "
                    "power step (→ ~9 kW). Air holds ~700 W/device. Awake, "
                    "unfused."
                ),
            ),
            active_regions=_gpus() + FANS,
            power_watts=9000,
            gpus_in_domain=0,
            nics_up=0,
            elapsed_seconds=270,
            cycle_cost=5,
        ),
        PowerOnState(
            step=4,
            phase="fuse",
            label="NVSwitch fuses eight GPUs into one domain",
            description=L(
                novice=(
                    "The switch chips on the same board now connect the eight "
                    "graphics chips into one group: any of them can read and "
                    "write any other's memory directly, at speeds an ordinary "
                    "network cannot approach. Software stops seeing eight "
                    "separate cards and starts seeing something close to one "
                    "very large processor. Notice two things. The counter "
                    "jumps from zero to eight all at once — the group either "
                    "exists or it does not. And it will never read nine: the "
                    "connection is wiring on a board, and it ends where the "
                    "board ends, at the chassis wall."
                ),
                plain=(
                    "The NVSwitch chips on the baseboard stitch the eight "
                    "GPUs into one NVLink domain — every GPU can read and "
                    "write every other's HBM at 900 GB/s, an order of "
                    "magnitude past PCIe, so software addresses something "
                    "close to one large accelerator. The counter snaps 0 → 8 "
                    "atomically, and 8 is where it stops, forever: the fuse "
                    "is copper traces on one board, and the domain ends at "
                    "the chassis wall. The XE9712 moves that wall out to a "
                    "whole rack; this box keeps it here and pays the fabric "
                    "for everything beyond."
                ),
                standard=(
                    "The quiet counterpart to the XE9712's grand finale. The "
                    "NVSwitch chips on the HGX baseboard — the same switch "
                    "silicon the rack twin fills nine trays with — stitch "
                    "the eight GPUs into a single NVLink domain: every GPU "
                    "can now read and write every other's HBM directly at "
                    "900 GB/s, roughly an order of magnitude beyond PCIe, "
                    "and software addresses something close to one large "
                    "accelerator with a terabyte-plus of pooled memory. Two "
                    "things carry this twin's whole argument. The counter "
                    "snaps from zero to eight atomically — a partial domain "
                    "never exists. And eight is where it stops, forever: "
                    "the fuse is copper traces on one baseboard, took "
                    "seconds rather than the rack twin's minutes of cable "
                    "training, and ends at the chassis wall. NVLink stops "
                    "here. Scale does not."
                ),
                technical=(
                    "NVSwitch complex fuses 8× SXM into one NVLink domain: "
                    "900 GB/s per GPU peer-to-peer HBM access, pooled "
                    "memory ~1.1–1.5 TB depending on baseboard. Atomic — "
                    "gpusInDomain ∈ {0, 8}, asserted; and 8 is a hard "
                    "ceiling, also asserted. Board-level traces, not cable "
                    "training: the fuse is fast because it is small."
                ),
                expert=(
                    "NVSwitch fuse: 8-GPU domain, 900 GB/s/GPU P2P HBM. "
                    "gpusInDomain ∈ {0, 8}; 8 is the ceiling. Board traces, "
                    "not cables — fast because small."
                ),
            ),
            active_regions=_gpus() + ["nvswitch", *FANS],
            power_watts=9500,
            gpus_in_domain=8,
            nics_up=0,
            elapsed_seconds=330,
            cycle_cost=2,
        ),
        PowerOnState(
            step=5,
            phase="fabric",
            label="Eight NICs train — one per GPU, onto the fabric",
            description=L(
                novice=(
                    "Now the box reaches outward. Eight network cards — one "
                    "for each graphics chip, which is a striking design "
                    "choice — negotiate their links to the network switch at "
                    "the top of the rack, each at 400 gigabits per second. "
                    "The pairing is the whole philosophy of this machine: "
                    "inside the box, chips talk over the board; past the "
                    "box, every chip has its own private on-ramp to the "
                    "data-center network, so eight here can work with eight "
                    "thousand elsewhere without queueing behind each other. "
                    "In xAI's Colossus, that is about 3.6 terabits of "
                    "network per server."
                ),
                plain=(
                    "The box reaches outward: eight ConnectX NICs — one per "
                    "GPU, the pairing that defines this class of machine — "
                    "train their 400 GbE links to the leaf switch, and the "
                    "nicsUp counter climbs to eight. Each GPU gets a "
                    "private on-ramp to the data-center fabric (RDMA "
                    "traffic bypasses the host CPU entirely), so all-to-all "
                    "training traffic never queues behind a shared port. "
                    "This is the step the SN6000 fabric twin receives: "
                    "~3.6 Tb/s of network per server, Colossus's reported "
                    "figure."
                ),
                standard=(
                    "Now the box reaches outward. Eight ConnectX NICs — "
                    "one dedicated to each GPU, the design choice that "
                    "defines this class of machine — train their 400 GbE "
                    "links against the leaf switch at the top of the rack, "
                    "and the nicsUp counter climbs to eight. One NIC per "
                    "GPU means every accelerator has its own private "
                    "on-ramp to the data-center fabric: remote GPUs read "
                    "and write its memory over RDMA (remote direct memory "
                    "access — the NIC moves the data without involving the "
                    "host CPU) without queueing behind seven siblings on a "
                    "shared port. This is the hand-off the SN6000 twin "
                    "catches: NVLink carried the conversation inside the "
                    "chassis, and from here outward it rides Ethernet — "
                    "about 3.6 Tb/s of it per server, which is the number "
                    "xAI's Colossus reported."
                ),
                technical=(
                    "8× ConnectX 400 GbE NICs link-train to the leaf — one "
                    "per GPU, so per-accelerator RDMA never shares a port. "
                    "nicsUp 0 → 8; ~3.6 Tb/s per server onto the scale-out "
                    "fabric (Spectrum-X at Colossus). GPU-to-GPU past the "
                    "chassis wall is GPUDirect RDMA from here on."
                ),
                expert=(
                    "8× 400 GbE train, 1:1 NIC:GPU, ~3.6 Tb/s/server. "
                    "Past the wall it's GPUDirect RDMA on the scale-out "
                    "fabric."
                ),
            ),
            active_regions=_nics() + ["nvswitch", *FANS],
            power_watts=10200,
            gpus_in_domain=8,
            nics_up=8,
            elapsed_seconds=390,
            cycle_cost=2,
        ),
        PowerOnState(
            step=6,
            phase="ready",
            label="Burn-in passed — the server joins the cluster",
            description=L(
                novice=(
                    "Health checks sweep the whole machine — every graphics "
                    "chip, every connection between them, every network "
                    "link, every memory stack exercised while the fans hold "
                    "the temperature steady. Then the server reports to the "
                    "cluster's job scheduler and starts accepting work. On "
                    "its own it is a formidable computer; the deeper point "
                    "is that it is one identical unit among thousands, and "
                    "the counter still reads eight. Joining the cluster "
                    "multiplied the machine's reach, not its domain — "
                    "growing past eight was the network's job, and the "
                    "network did it."
                ),
                plain=(
                    "Burn-in sweeps the box — every GPU, every NVLink path, "
                    "every NIC, every HBM stack under thermal load — and "
                    "then the server registers with the cluster scheduler "
                    "and accepts jobs at ~11 kW. gpusInDomain still reads "
                    "8: joining a 100,000-GPU cluster did not grow the "
                    "NVLink domain by one. Scale came from the fabric, "
                    "box by identical box — the Colossus recipe."
                ),
                standard=(
                    "Health checks and a burn-in workload sweep the box: "
                    "every GPU, every NVLink path, every NIC, every HBM "
                    "stack exercised while the fans hold temperature. Then "
                    "the server registers with the cluster scheduler and "
                    "accepts work, drawing on the order of 11 kW at full "
                    "load. Look at the counters one last time: nicsUp "
                    "reads eight, and gpusInDomain still reads eight — "
                    "joining a hundred-thousand-GPU cluster did not grow "
                    "the NVLink domain by a single GPU. That is the whole "
                    "architecture in one line: the domain is the box, the "
                    "cluster is the fabric, and you scale by buying the "
                    "box again — which is exactly what Colossus did, "
                    "roughly 12,500 times over."
                ),
                technical=(
                    "Burn-in across GPUs, NVLink paths, NICs, and HBM under "
                    "thermal load; server joins the scheduler at ~11 kW. "
                    "Final counters: nicsUp = 8, gpusInDomain = 8 — cluster "
                    "membership does not extend the NVLink domain. Scale is "
                    "fleet × fabric, not a bigger domain."
                ),
                expert=(
                    "Burn-in, join scheduler, ~11 kW. gpusInDomain = 8, "
                    "still. Scale = identical boxes × fabric."
                ),
            ),
            active_regions=(
                _gpus() + _nics()
                + ["nvswitch", "host-cpus", "nvme-bay", "idrac", "psu-bank", *FANS]
            ),
            power_watts=11000,
            gpus_in_domain=8,
            nics_up=8,
            elapsed_seconds=540,
        ),
    ]
