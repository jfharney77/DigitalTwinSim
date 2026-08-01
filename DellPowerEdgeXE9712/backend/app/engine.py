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
            description=L(
                novice=(
                    "The rack arrives from the factory already built — 18 compute "
                    "trays, 9 switch trays, power units, and a rack's worth of "
                    "cabling run and tested before it shipped. It is wheeled into "
                    "place and connected to the building's power and water. Nothing "
                    "is switched on. This is not a computer you slide into a rack; "
                    "the rack *is* the computer, because at this density there are "
                    "thousands of cables and getting one wrong on site is not a "
                    "risk anyone wants to take."
                ),
                plain=(
                    "The XE9712 arrives as one integrated rack — 18 compute trays, "
                    "9 NVLink switch trays, power shelves, and pre-run copper "
                    "cabling — rolled into place and connected to facility power "
                    "and water. Nothing is on. Unlike a server you slide into a "
                    "rack, this *is* the rack: Dell builds, cables, and tests it as "
                    "a unit before shipping, because at these densities on-site "
                    "cabling is a risk rather than a task."
                ),
                standard=(
                    "The XE9712 arrives from the factory as one integrated rack — "
                    "18 compute trays, 9 NVLink switch trays, power shelves, and "
                    "a rack full of pre-run copper cabling — rolled into place and "
                    "connected to facility power and facility water. Nothing is "
                    "on. Unlike a server you slide into a rack, this *is* the "
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
                    "graphics chips. The trays are identical and start in parallel, "
                    "exactly as the cluster twin's nodes do: at this moment they "
                    "are still eighteen separate computers."
                ),
                plain=(
                    "With coolant flowing, the 18 compute trays clip power from the "
                    "busbar and boot. Each tray holds two GB200 superchips — one "
                    "NVIDIA Grace CPU (72 Arm cores) fused to two Blackwell GPUs on "
                    "one board over a chip-to-chip NVLink — so each brings up two "
                    "Grace CPUs and readies four GPUs. The trays are identical and "
                    "boot in parallel, exactly as VxRail nodes do: at this moment "
                    "they are still eighteen separate computers."
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
                    "Trays boot off the busbar: 2× GB200 superchip each (Grace + 2× "
                    "Blackwell over C2C). Lockstep asserted. Eighteen discrete "
                    "systems still."
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
                    "Now the main event. Tray by tray, but in step across the rack, "
                    "the graphics chips come out of reset: firmware, memory tuning "
                    "on every stack, and cold-plate temperatures climbing as the "
                    "cooling unit takes the heat away. This is where the rack's "
                    "power consumption goes vertical — each of these chips can draw "
                    "around a kilowatt, so seventy-two of them dominate everything "
                    "else in the rack put together. They are awake, and they are "
                    "still strangers to one another."
                ),
                plain=(
                    "The main event begins. Tray by tray, but in lockstep across "
                    "the rack, the Blackwell GPUs come out of reset: VBIOS, HBM3e "
                    "memory training on every stack, cold-plate temperatures "
                    "stepping up as the CDU takes the heat. This is where the "
                    "rack's power draw goes vertical — each GPU can draw on the "
                    "order of a kilowatt, so seventy-two of them dominate "
                    "everything else in the rack combined. They are awake and still "
                    "unconnected."
                ),
                standard=(
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
                technical=(
                    "GPUs out of reset in lockstep: VBIOS, per-stack HBM3e "
                    "training, cold-plate temperatures rising as the CDU absorbs "
                    "load. The largest single power step in the trace — ~1 kW per "
                    "GPU, so 72 of them dominate the rack's total. Awake, unfused."
                ),
                expert=(
                    "GPUs out of reset: VBIOS, HBM3e training, cold plates loading. "
                    "Largest power step (~1 kW × 72). Awake, unfused."
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
            label="NVLink switch trays boot — 5,000 links train",
            description=L(
                novice=(
                    "The longest stage. The nine switch trays in the middle of the "
                    "rack start up, and then the connections between chips are "
                    "trained: more than five thousand copper links, coming up one "
                    "at a time, each negotiated, tuned, and error-checked. This is "
                    "the fabric that joins graphics chips to each other — and it is "
                    "copper rather than optical fibre, which is only possible "
                    "because the switch trays sit physically in the middle of the "
                    "rack so no cable has to run very far. That single layout "
                    "decision saves an enormous amount of power."
                ),
                plain=(
                    "The single longest stage. The 9 NVLink switch trays in the "
                    "middle of the rack boot their NVSwitch chips, and then the "
                    "fabric trains: more than 5,000 copper links through the cable "
                    "cartridge at the back come up one by one, each negotiated, "
                    "tuned, and error-checked at 200 Gb/s per lane. NVLink is the "
                    "scale-up fabric — copper rather than optics, which is only "
                    "possible because the switch trays sit mid-rack so no run is "
                    "long."
                ),
                standard=(
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
                technical=(
                    "Max-dwell stage. NVSwitch trays boot, then >5,000 copper links "
                    "through the rear cartridge train individually — negotiation, "
                    "equalization, error checking at 200 Gb/s per lane. Copper "
                    "rather than optics is viable only because the switch trays are "
                    "physically central, bounding every run length; the power "
                    "saving over pluggable optics is substantial."
                ),
                expert=(
                    "Max dwell: NVSwitch trays up, >5,000 copper links trained at "
                    "200 Gb/s/lane. Mid-rack switch placement bounds run length, "
                    "making copper viable over optics."
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
            label="One NVLink domain — 72 GPUs become one accelerator",
            description=L(
                novice=(
                    "The signature moment, and the reason this rack exists: every "
                    "trained link is stitched into one all-to-all network, and the "
                    "72 graphics chips can now read and write each other's memory "
                    "directly at enormous speed. Software stops seeing 72 cards and "
                    "starts seeing something close to one gigantic processor with "
                    "all their memory pooled together. Note that the counter goes "
                    "straight from zero to 72 — there is no halfway state where "
                    "some are joined and some are not."
                ),
                plain=(
                    "The signature moment, and the reason this rack exists: the "
                    "fabric manager stitches every trained link into a single "
                    "all-to-all NVLink domain. All 72 GPUs can now read and write "
                    "each other's memory at 1.8 TB/s each — about 130 TB/s of "
                    "fabric bandwidth — so software sees something close to one "
                    "enormous GPU with 13.5 TB of pooled HBM3e rather than 72 "
                    "cards. The counter goes 0 to 72 with nothing in between: the "
                    "fuse is atomic."
                ),
                standard=(
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
                technical=(
                    "Fabric manager stitches trained links into a single all-to-all "
                    "NVLink domain: 1.8 TB/s per GPU, ~130 TB/s aggregate, 13.5 TB "
                    "pooled HBM3e presented as approximately one device. The fuse "
                    "is atomic — gpusInDomain ∈ {0, 72}, asserted; no partial "
                    "domain exists at any step."
                ),
                expert=(
                    "All-to-all NVLink domain: 1.8 TB/s/GPU, ~130 TB/s aggregate, "
                    "13.5 TB pooled HBM3e as one logical device. Atomic fuse — "
                    "gpusInDomain ∈ {0, 72}."
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
                    "Health checks and a burn-in workload sweep the whole rack — "
                    "every chip, every link, every memory stack exercised while the "
                    "cooling holds steady. Then the rack joins the job scheduler "
                    "and starts accepting work. At full load it draws around 120 "
                    "kilowatts, more than a thousand times what the laptop twin in "
                    "this repo uses, with the outside network joining this rack to "
                    "others."
                ),
                plain=(
                    "Health checks and a burn-in workload sweep the domain: every "
                    "GPU, every NVLink path, every HBM stack exercised while the "
                    "CDU holds the loop at temperature. Then the rack joins the "
                    "cluster scheduler and accepts jobs. At full load it draws on "
                    "the order of 120 kW — more than a thousand times the laptop "
                    "twin's budget — with the scale-out network joining this rack "
                    "to its neighbours."
                ),
                standard=(
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
