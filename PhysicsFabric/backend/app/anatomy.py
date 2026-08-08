"""Fabric maps — three topology diagrams painted by link load. The
geometry carries each product's argument: the campus tree for the
E3200 (with the PoE strip — the budget that binds first), the
leaf/spine mesh with the worst-link strip for the SN6000, and the same
mesh with a small subnet manager *beside* the fabric for the X800 —
control programs the fabric, data never passes through it (the
DellQuantumX800 twin's pin, honored here)."""

from __future__ import annotations

from .leveling import L
from .models import FabricMap, MapRegion


E3200 = FabricMap(
    id="e3200",
    name="PowerSwitch E3200 · campus access",
    vendor="Dell Technologies",
    form_factor="Access → distribution → core tree",
    generation="E3200-ON series",
    year=2024,
    width=100,
    height=56,
    overview=L(
        novice=(
            "A building's network, drawn as the tree it is: the core "
            "at the top, distribution switches in the middle, and "
            "access switches at the bottom feeding the wall jacks. "
            "Two lessons live here. First, the phones, cameras, and "
            "Wi-Fi points draw their electricity through the network "
            "cable itself — and the switch has a fixed power budget "
            "that usually runs out before its ports do. Second, all "
            "the traffic from a floor funnels into a couple of uplink "
            "wires; lose one and the survivor carries everything. The "
            "giant AI fabrics elsewhere in this app obey exactly the "
            "same two arithmetic facts, with bigger numbers."
        ),
        standard=(
            "The fabric engine at building scale — the spec calls it "
            "the right first networking sim. PoE is the mechanic the "
            "big fabrics lack: per-device draws (AP ~20 W, camera "
            "~13 W, phone ~7 W) sum against the switch budget, and "
            "that budget binds before port count does; a PSU loss "
            "halves it and sheds devices by priority. Uplinks are a "
            "LAG pair per access switch — losing one is a ~2 s STP "
            "outage, then the survivor at doubled utilization walks "
            "up the same 1/(1−ρ) curve the SN6000's 800G links use. "
            "Same physics, human scale."
        ),
        expert=(
            "PoE: Σdevice W vs budget, binds first; PSU loss → ½ "
            "budget, priority shed. LAG loss → 2 s STP + survivor at "
            "2× ρ. The 1G/10G rehearsal for the 800G act."
        ),
    ),
    regions=[
        MapRegion(
            id="core", kind="distribution", label="Core",
            x=30, y=1, w=40, h=8,
            description="The building core — everything north of here is someone else's problem.",
        ),
        MapRegion(
            id="distribution", kind="access", label="Distribution",
            x=20, y=13, w=60, h=8,
            description="Aggregates the access layer; the uplink oversubscription lesson repeats here.",
        ),
        MapRegion(
            id="access", kind="leaf", label="Access switches (E3200)",
            x=8, y=25, w=84, h=10,
            description=(
                "The E3200s at the wiring closet. Their uplink pair is "
                "the funnel; their PoE budget is the wallet."
            ),
        ),
        MapRegion(
            id="poe", kind="power", label="PoE budget",
            x=8, y=39, w=84, h=6,
            description=(
                "The power budget leaving through the front ports. "
                "Colored by consumption against budget — the rule that "
                "trips before any port runs out."
            ),
        ),
        MapRegion(
            id="devices", kind="device", label="APs · cameras · phones",
            x=8, y=48, w=84, h=7,
            description=(
                "The powered estate. When budget runs short, phones "
                "shed first, then cameras, then APs — priority is a "
                "configuration decision made visible."
            ),
        ),
    ],
    sources=[
        {"label": "physics_specs/03-networking.md (this repo)",
         "url": "../physics_specs/03-networking.md"},
        {"label": "DellPowerSwitchE3200 twin — the same switch's boot story",
         "url": "http://localhost:5178/"},
    ],
)


def _leafspine(map_id: str, name: str, gen: str, overview: str,
               extra_regions: list[MapRegion],
               sources: list[dict[str, str]]) -> FabricMap:
    return FabricMap(
        id=map_id,
        name=name,
        vendor="Dell Technologies",
        form_factor="Leaf/spine fabric — topology view",
        generation=gen,
        year=2026,
        width=100,
        height=56,
        overview=overview,
        regions=[
            MapRegion(
                id="spines", kind="spine", label="Spine tier",
                x=20, y=1, w=60, h=9,
                description=(
                    "The spines every leaf connects to. Mean spine-link "
                    "load colors this tier; the worst link gets its own "
                    "strip below, because averages hide the lesson."
                ),
            ),
            MapRegion(
                id="worst-link", kind="telemetry", label="WORST LINK",
                x=20, y=13, w=60, h=5,
                description=(
                    "The single busiest link in the fabric — the one "
                    "that decides tail latency. ECMP hash collisions "
                    "load it far above the mean; adaptive routing "
                    "exists to flatten exactly this strip."
                ),
            ),
            MapRegion(
                id="leaves", kind="leaf", label="Leaf tier",
                x=8, y=22, w=84, h=10,
                description=(
                    "Top-of-rack leaves. Downlink ÷ uplink capacity is "
                    "the oversubscription ratio, and congestion appears "
                    "exactly where it predicts."
                ),
            ),
            MapRegion(
                id="endpoints", kind="endpoint", label="GPU racks",
                x=8, y=36, w=84, h=9,
                description=(
                    "The racks the fabric exists for — PhysicsCompute's "
                    "XE9680s, whose NVLink stops at the chassis wall. "
                    "Everything past that wall is this app."
                ),
            ),
            *extra_regions,
        ],
        sources=[
            {"label": "physics_specs/03-networking.md (this repo)",
             "url": "../physics_specs/03-networking.md"},
            *sources,
        ],
    )


SN6000 = _leafspine(
    "sn6000",
    "PowerSwitch SN6000 · AI Ethernet fabric",
    "NVIDIA Spectrum-6 / Spectrum-X",
    L(
        novice=(
            "The Ethernet fabric that joins GPU racks into one "
            "training cluster. Traffic spreads across parallel paths "
            "by a hashing trick that is usually fair and occasionally "
            "terrible — a few unlucky big flows can pile onto one "
            "link while its neighbors idle. The adaptive-routing "
            "switch watches and rebalances; toggling it is the "
            "clearest before/after in this app. The other surprise is "
            "power: at hundreds of ports, the little optical plugs on "
            "each port together draw as much as the switch's own "
            "brain — which is why the newest switches move the optics "
            "inside the package."
        ),
        standard=(
            "Spectrum-X Ethernet as flow physics: static ECMP models "
            "hash collisions as a worst-link excess over fair share "
            "(up to +85% with elephant flows); adaptive routing "
            "leaves ~15% of that skew. Lossless RoCE swaps drops for "
            "PFC pauses that spread congestion upstream — visible in "
            "the pause counter and the latency multiplier. The optics "
            "ledger is the other lesson: ~18 W per pluggable port "
            "rivals the ASIC at 128 ports; the CPO toggle drops it to "
            "~6 W. Compare against the X800 personality on identical "
            "traffic — the suite's best A/B."
        ),
        expert=(
            "ECMP skew +25/+50/+85% by pattern; AR ×0.15 residual. "
            "RoCE: drops→pauses, HoL spread ×1.5. Optics: 18 W/port "
            "pluggable vs 6 CPO — Σoptics ≈ ASIC at scale. A/B "
            "against IB is the point."
        ),
    ),
    [
        MapRegion(
            id="optics", kind="optics", label="Optics ledger",
            x=8, y=49, w=40, h=6,
            description=(
                "Per-port optics power as a share of fabric power. "
                "Pluggables at 128 ports rival the ASIC; CPO cuts the "
                "line by two-thirds."
            ),
        ),
        MapRegion(
            id="telemetry", kind="manager", label="Telemetry",
            x=52, y=49, w=40, h=6,
            description=(
                "The watching layer. Its color is the gray-failure "
                "goodput penalty — the damage every status light "
                "misses. PhysicsData's anomaly feed is the other half "
                "of this story."
            ),
        ),
    ],
    [{"label": "DellPowerSwitchSN6000 twin", "url": "http://localhost:5185/"}],
)


X800 = _leafspine(
    "x800",
    "Quantum-X800 · Dell-integrated InfiniBand",
    "NVIDIA Quantum-X800 XDR",
    L(
        novice=(
            "The other way to build the same fabric. InfiniBand "
            "refuses, by construction, to ever lose a packet: a "
            "sender may not transmit until the receiver has "
            "explicitly granted it room. Congestion still exists — "
            "it shows up as senders waiting rather than data "
            "vanishing. And the fabric can do arithmetic: when "
            "thousands of GPUs add their results together, the "
            "switches themselves combine the numbers en route, so "
            "the answer crosses the wires once instead of many "
            "times. Run identical traffic on this and the Ethernet "
            "personality; the difference is the whole choice."
        ),
        standard=(
            "Lossless by construction: credit-based flow control "
            "makes the drop counter structurally zero — congestion "
            "manifests as sender stall time (µs/s), the honest cost "
            "metric. SHARP moves the collective into the fabric: "
            "with it on, all-reduce bytes crossing links fall by "
            "half while the effective all-reduce rate rises ~1.8× — "
            "the counters cross, the DellQuantumX800 twin's "
            "signature move. The subnet manager sits beside the "
            "fabric, small: essential to its life, absent from every "
            "packet's."
        ),
        expert=(
            "Credit FC: drops unexpressible; stalls are the cost. "
            "SHARP: link bytes ×0.5, allreduce ×1.8 — counters "
            "cross. SM beside, never in, the data path."
        ),
    ),
    [
        MapRegion(
            id="manager", kind="manager", label="Subnet mgr",
            x=8, y=49, w=26, h=6,
            description=(
                "The subnet manager — programs every route, then "
                "leaves the data path. Drawn small and beside the "
                "fabric on purpose (the DellQuantumX800 twin pins "
                "this in a test; we honor it)."
            ),
        ),
        MapRegion(
            id="sharp", kind="optics", label="SHARP in-network compute",
            x=40, y=49, w=52, h=6,
            description=(
                "The reduction trees inside the switches. Colored by "
                "the collective share when SHARP is on — math the "
                "wires no longer have to carry."
            ),
        ),
    ],
    [{"label": "DellQuantumX800 twin", "url": "http://localhost:5202/"}],
)


MAPS: dict[str, FabricMap] = {
    "e3200": E3200,
    "sn6000": SN6000,
    "x800": X800,
}
