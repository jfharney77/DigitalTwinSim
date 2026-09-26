"""Preset chains: one per coupling, the closed loop, and the capstone."""

from __future__ import annotations

from .chain import Chain, Link

XE9712_RAMP = {
    "config": {"product": "xe9712"},
    "workload": {"gpuPct": 10, "cpuPct": 10},
    "durationS": 900,
    "events": [{"atS": 60, "action": "set-workload",
                "workload": {"gpuPct": 100, "cpuPct": 40, "dataFeedPct": 100}}],
}
XE9712_FULL = {
    "config": {"product": "xe9712"},
    "workload": {"gpuPct": 100, "cpuPct": 40},
    "durationS": 900,
}
WARM_WATER = {"events": [{"atS": 200, "action": "set-facility-supply", "value": 29}]}

EXASCALE = {
    "config": {"product": "exascale", "units": 32, "drivesPerUnit": 12, "driveTb": 15.36,
               "driveClass": "nvme", "protection": "ec8+2",
               "lightningUnits": 16, "fileUnits": 6, "objectUnits": 6, "blockUnits": 4},
    "workload": {"iopsDemandK": 3000, "blockKb": 1024, "readPct": 95, "sequentialPct": 90,
                 "workingSetFitPct": 15, "ingestTbDay": 5, "reductionRatio": 1.5},
    "durationH": 72,
    "events": [{"atH": 40, "action": "set-workload",
                "workload": {"iopsDemandK": 5000, "blockKb": 1024, "readPct": 95,
                             "sequentialPct": 90, "workingSetFitPct": 15,
                             "ingestTbDay": 5, "reductionRatio": 1.5}}],
}

GRAY_FABRIC = {
    "config": {"product": "sn6000", "losslessRoce": True},
    "workload": {"demandGbps": 4000, "pattern": "alltoall", "collectivePct": 60},
    "durationS": 600,
    "events": [{"atS": 200, "action": "gray-failure"}, {"atS": 400, "action": "clear-gray"}],
}
HEALTHY_FABRIC = {**GRAY_FABRIC, "events": []}
GRAY_TO_THE_END = {**GRAY_FABRIC, "events": [{"atS": 360, "action": "gray-failure"}]}

R760_BUSY = {
    "config": {"cpuTdpW": 250, "gpusDoubleWide": 0},
    "workload": {"cpuPct": 20, "memPct": 20, "storagePct": 10, "gpuPct": 0},
    "durationS": 600,
    "events": [{"atS": 120, "action": "set-workload",
                "workload": {"cpuPct": 100, "memPct": 80, "storagePct": 60, "gpuPct": 0}}],
}
R760_FAN_DOWN = {**R760_BUSY, "workload": {"cpuPct": 100, "memPct": 80, "storagePct": 60, "gpuPct": 0},
                 "events": [{"atS": 200, "action": "kill-fan", "index": 2}]}

ATTACK = {
    "config": {"product": "powerprotect", "estateTb": 200, "changeGbDay": 500, "vault": True,
               "detection": False, "restoreGbps": 1.0},
    "durationH": 1440,
    "events": [{"atH": 240, "action": "slow-incident", "value": 100},
               {"atH": 960, "action": "contain"},
               {"atH": 984, "action": "attempt-restore"}],
}

XR_FOULED = {
    "config": {"platform": "xr8000", "cpuTdpW": 205, "thermalConfig": "standard", "dimms": 8,
               "driveType": "ssd", "drives": 2, "accelsSingleWide": 2, "ioCardW": 100,
               "psuCount": 1, "psuCapacityW": 800, "redundancy": "1+0"},
    "workload": {"cpuPct": 100, "memPct": 80, "storagePct": 50, "accelPct": 100},
    "environment": {"inletC": 30, "dust": "heavy", "filterMonths": 6},
    "durationS": 1800,
    "events": [{"atS": 300, "action": "set-inlet", "value": 45}],
}
XR_CLEANED = {**XR_FOULED, "events": [{"atS": 60, "action": "clean-filter"},
                                      {"atS": 300, "action": "set-inlet", "value": 45}]}
XR_BROWNOUT = {
    "config": XR_FOULED["config"],
    "workload": XR_FOULED["workload"],
    "environment": {"inletC": 30, "dust": "moderate", "filterMonths": 0},
    "durationS": 600,
    "events": [{"atS": 300, "action": "voltage-sag", "value": 65, "seconds": 20}],
}
XR_CLOSET = {
    "config": XR_FOULED["config"],
    "workload": {"cpuPct": 40, "memPct": 30, "storagePct": 20, "accelPct": 0},
    "environment": {"inletC": 24, "dust": "clean", "filterMonths": 0},
    "durationS": 600,
}
FLEET = {"config": {"product": "nativeedge", "nodesPerSite": 2, "opsMode": "automated",
                    "siteClass": "store", "twoNodeHa": True},
         "durationD": 180}
SITE_MIX = [
    {"id": "rooftop-fouled", "label": "Rooftop, filter six months overdue", "sites": 60, "scenario": XR_FOULED},
    {"id": "brownout-cell-site", "label": "Cell site on a weak feed", "sites": 20, "scenario": XR_BROWNOUT},
    {"id": "clean-closet", "label": "Conditioned closet", "sites": 120, "scenario": XR_CLOSET},
]

FACTORY = {"durationH": 720}

CHAINS: dict[str, Chain] = {}


def _add(chain: Chain) -> None:
    CHAINS[chain.id] = chain


_add(Chain(
    id="heat-to-cdu", title="XE9712 heat loads the CDU",
    scenarios={"PhysicsCompute": XE9712_RAMP, "PhysicsCDU": {}},
    links=(Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": 2}),),
))
_add(Chain(
    id="closed-loop", title="Warm water day, closed loop",
    scenarios={"PhysicsCompute": XE9712_RAMP, "PhysicsCDU": WARM_WATER},
    links=(Link("c1", "PhysicsCompute", "PhysicsCDU", {"racks": 2}),
           Link("c2", "PhysicsCDU", "PhysicsCompute")),
    closed=True,
))
_add(Chain(
    id="storage-feed", title="Exascale feeds the GPUs",
    scenarios={"PhysicsStorage": EXASCALE, "PhysicsCompute": XE9712_FULL},
    links=(Link("c3", "PhysicsStorage", "PhysicsCompute", {"window_s": 600}),),
))
_add(Chain(
    id="gray-fabric", title="A gray link costs tokens",
    scenarios={"PhysicsFabric": GRAY_FABRIC, "PhysicsAIFactory": FACTORY},
    links=(Link("c4", "PhysicsFabric", "PhysicsAIFactory"),),
))
_add(Chain(
    id="wall-watts", title="Servers load the rack's phases",
    scenarios={"PhysicsRackPower": {"config": {"breakerAmps": 16}}},
    links=(Link("c5", "DellPowerEdgeR760Thermal", "PhysicsRackPower", {"servers": [
        {"label": "R760 A", "component": "DellPowerEdgeR760Thermal", "scenario": R760_BUSY},
        {"label": "R760 B", "component": "DellPowerEdgeR760Thermal", "scenario": R760_FAN_DOWN},
        {"label": "R760 C", "component": "DellPowerEdgeR760Thermal", "scenario": R760_BUSY},
    ]}),),
))
_add(Chain(
    id="attack-to-appliance", title="An attack, read from the backup appliance",
    scenarios={"PhysicsResilience": ATTACK, "PhysicsDataDomain": {"appliance": "dd9910"}},
    links=(Link("c6", "PhysicsResilience", "PhysicsDataDomain"),
           Link("c6", "PhysicsDataDomain", "PhysicsResilience")),
))
_add(Chain(
    id="hostile-sites", title="Hostile edge sites cost admin hours",
    scenarios={"PhysicsFleet": FLEET},
    links=(Link("c7", "PhysicsXR", "PhysicsFleet", {"site_mix": SITE_MIX}),),
))
_FED_LINKS = (
    Link("c3", "PhysicsStorage", "PhysicsCompute"),
    Link("c1", "PhysicsCompute", "PhysicsCDU"),
    Link("c2", "PhysicsCDU", "PhysicsCompute"),
    Link("c4", "PhysicsFabric", "PhysicsAIFactory"),
)
_add(Chain(
    id="factory-fed", title="The AI factory, fed by engines",
    scenarios={"PhysicsAIFactory": FACTORY, "PhysicsStorage": {**EXASCALE, "events": []},
               "PhysicsFabric": HEALTHY_FABRIC, "PhysicsCompute": XE9712_FULL, "PhysicsCDU": {}},
    links=_FED_LINKS + (Link("c8", "PhysicsCompute", "PhysicsAIFactory",
                             {"racks_per_cdu": 2, "storage_racks": 1}),),
    closed=True,
))
_add(Chain(
    id="factory-fed-bad-day", title="The AI factory on a bad day",
    scenarios={"PhysicsAIFactory": FACTORY, "PhysicsStorage": {**EXASCALE, "events": []},
               "PhysicsFabric": GRAY_TO_THE_END, "PhysicsCompute": XE9712_FULL, "PhysicsCDU": {}},
    links=_FED_LINKS + (Link("c8", "PhysicsCompute", "PhysicsAIFactory", {
        "racks_per_cdu": 2, "storage_racks": 1,
        "warm_water": {"facilitySupplyC": 29, "atS": 120, "fromH": 480, "toH": 721}}),),
    closed=True,
))


def chain(chain_id: str) -> Chain:
    return CHAINS[chain_id]
