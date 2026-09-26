#!/usr/bin/env python3
"""Generate components.json from what is actually on disk.

CLAUDE.md listed the components in prose, and the prose drifted. This reads
the directories, ports.json, and each backend's main.py, and writes the
machine-readable index that scripts/dev.sh, the CI table generator and the
CustomerSetup link tests all read instead.

Editorial fields — the one-line description, the hardware family, and the
status — are held in the table below, because no amount of reading the source
tells you whether a component is the pattern others follow or an experiment
nobody finished. Everything else is scanned.

    python3 scripts/gen_components.py           # rewrite components.json
    python3 scripts/gen_components.py --check    # fail if it would change
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# name -> (family, status, one-line description)
#
# status: reference (the pattern others follow) | built | partial | scaffold |
#         archived. See docs/LIFECYCLE.md.
EDITORIAL: dict[str, tuple[str, str, str]] = {
    # --- the reference implementations ---------------------------------------
    "GPU": ("accelerator", "reference",
            "Matmul on a GPU die: the pure-engine + SimState trace pattern every other component follows."),
    "DellPowerEdgeR760": ("server", "reference",
            "A 2U rack server from AC to operating system — the chassis-twin pattern."),
    "DellPowerEdgeR760Thermal": ("server", "reference",
            "The same R760 while it runs: configuration to power to heat to fan response — the physics-sim pattern."),

    # --- storage --------------------------------------------------------------
    "DellPowerStore": ("storage", "built",
            "An all-NVMe appliance whose two controller nodes bring up in lockstep."),
    "DellPowerStoreElite": ("storage", "built",
            "A next-generation appliance joining a live cluster: modernization with zero downtime."),
    "DellPowerMax": ("storage", "built",
            "Rack-scale scale-out storage: drives hang off an InfiniBand fabric, not a director's bus."),
    "DellPowerScale": ("storage", "built",
            "Scale-out NAS with one namespace: growing is adding a node, never a migration."),
    "DellPowerFlex": ("storage", "built",
            "Software-defined block storage: delete the controller and every node rebuilds."),
    "DellExascale": ("storage", "built",
            "A parallel file system where metadata leaves the data path."),
    "DellPowerProtect": ("resilience", "built",
            "Backup, dedupe, and an air gap the attack cannot cross."),
    "DellCyberDetect": ("resilience", "built",
            "Byte-level ransomware detection: which snapshot is the last clean one?"),

    # --- compute --------------------------------------------------------------
    "DellPowerEdgeXE9680": ("server", "built",
            "Eight HGX GPUs fused by NVSwitch — and the NVLink domain stops at the chassis wall."),
    "DellPowerEdgeXE9712": ("rack", "built",
            "A GB200 NVL72 rack whose fabric fuses 72 GPUs into one domain."),
    "DellProMaxPlus": ("client", "built",
            "A discrete NPU whose weights cross the PCIe link exactly once and never leave."),
    "DellAlienware": ("client", "built",
            "A gaming laptop's AC power path: adapter handshake, budget, charge, hybrid supplement."),

    # --- fabric and network ---------------------------------------------------
    "DellPowerSwitchE3200": ("network", "built",
            "A campus switch booting through ONIE into a disaggregated network OS."),
    "DellPowerSwitchSN6000": ("network", "built",
            "A leaf/spine Ethernet AI fabric proving losslessness under congestion."),
    "DellQuantumX800": ("network", "built",
            "InfiniBand: lossless by construction, because no sender transmits without a credit."),

    # --- facility -------------------------------------------------------------
    "DellIR7000": ("facility", "built",
            "A liquid-cooling loop commissioned and ramped: heat in equals heat out, exactly."),

    # --- platform and software ------------------------------------------------
    "DellIDRAC": ("management", "built",
            "The BMC's own firmware bring-up, with the host powered off throughout."),
    "DellCloudIQ": ("management", "built",
            "AIOps observability: the life of one batch of telemetry becoming an insight."),
    "DellNativeEdge": ("edge", "built",
            "Zero-touch edge onboarding: one human action, and it never increments again."),
    "DellVxRail": ("platform", "built",
            "A hyperconverged cluster's first run, ending in one vSAN datastore."),
    "DellPrivateCloud": ("platform", "built",
            "Disaggregated pools under one control plane, with the hypervisor a swappable layer."),
    "DellFortZero": ("resilience", "built",
            "Zero trust: a decision architecture with a centre and no inside."),
    "DellCircularDesign": ("lifecycle", "partial",
            "A product's material ledger, which closes rather than ends."),

    # --- the physics suite ----------------------------------------------------
    "PhysicsClient": ("client", "built",
            "Client-device physics: PL2 burst, shared thermal budget, skin cap, tokens per joule."),
    "PhysicsCompute": ("server", "built",
            "AI-compute physics across XE7745, XE9680 and a liquid-cooled XE9712."),
    "PhysicsStorage": ("storage", "built",
            "Capacity and performance physics: the queueing knee and the rebuild inversion."),
    "PhysicsFabric": ("network", "built",
            "Flow and congestion physics, including the gray failure that reads green."),
    "PhysicsFleet": ("platform", "built",
            "Fleet operations on a daily tick: admin hours, branch recovery, consumption crossover."),
    "PhysicsResilience": ("resilience", "built",
            "Attack timelines: blast radius, decision time, and the air gap holding."),
    "PhysicsData": ("management", "built",
            "A data pipeline whose constraint relocates, graded against planted ground truth."),
    "PhysicsLifecycle": ("lifecycle", "built",
            "Telecom and sustainability on a daily tick, with a carbon ledger that closes."),
    "PhysicsMX7000": ("server", "built",
            "A modular chassis where nothing belongs to a sled: shared fans, pooled PSUs."),
    "PhysicsXR": ("edge", "built",
            "The R760 thermal engine with the environment unlocked to hostile ranges."),
    "PhysicsME5": ("storage", "built",
            "Classic RAID with nothing in the way: write penalty and the rebuild window."),
    "PhysicsDataDomain": ("resilience", "built",
            "Deduplication as arithmetic: the ratio is emergent, never configured."),
    "PhysicsCDU": ("facility", "built",
            "A coolant distribution unit making three numbers equal, and the controller that decides what gives."),
    "PhysicsRackPower": ("facility", "built",
            "Rack PDUs and UPS: phase balance, breaker curves, and the runtime a faded pack really delivers."),
    "PhysicsDisplay": ("client", "built",
            "Display physics, small on purpose: backlight, local dimming, and embodied carbon."),
    "PhysicsAIFactory": ("rack", "built",
            "The capstone: six coupled subsystems, and GPUs idle because data did not arrive."),

    # --- the composition layer ------------------------------------------------
    "compose": ("composition", "built",
            "Two engines at once: one twin's trace becomes another's scenario, with an identity asserted across the seam."),

    # --- specced, not built ---------------------------------------------------
    "DellAIDataPlatform": ("management", "scaffold", "Spec only: the AI data platform pipeline."),
    "DellAPEX": ("platform", "scaffold", "Spec only: consumption-model infrastructure."),
    "DellAutomationStudio": ("management", "scaffold", "Spec only: infrastructure automation."),
    "DellMDR": ("resilience", "scaffold", "Spec only: managed detection and response."),
    "DellObjectScale": ("storage", "scaffold", "Spec only: object storage at scale."),
    "DellPowerEdgeXE7745": ("server", "scaffold", "Spec only: the PCIe-GPU AI server."),
    "DellTelecomBlocks": ("network", "scaffold", "Spec only: telecom infrastructure blocks."),
}

SKIP = {"CustomerSetup", "physics_specs", "tools", "packages", "scripts", "twinkit", "docs", "archive"}

#: Where archived components live. Nothing is there yet; see docs/LIFECYCLE.md
#: and DEFERRED_ACTIONS.md.
ARCHIVE = ROOT / "archive"


def lifecycle_problems(components: list[dict]) -> list[str]:
    """The two lifecycle rules docs/LIFECYCLE.md makes checkable.

    A ``partial`` component says what it is missing at the top of its README,
    and an ``archived`` one lives under archive/ — so the top level only shows
    live work and the archive is labeled rather than silently rotting.
    """
    problems = []
    for c in components:
        in_archive = c["directory"].startswith("archive/")
        if c["status"] == "archived" and not in_archive:
            problems.append(f"{c['name']} is archived but not under archive/")
        if in_archive and c["status"] != "archived":
            problems.append(f"{c['name']} is under archive/ but marked {c['status']}")
        if c["status"] == "partial":
            readme = ROOT / c["directory"] / "README.md"
            head = readme.read_text().splitlines()[:6] if readme.exists() else []
            if "## What's missing" not in head:
                problems.append(
                    f"{c['name']} is partial but its README does not open with a "
                    "\"## What's missing\" block"
                )
    return problems


def trace_endpoint(directory: pathlib.Path) -> str | None:
    """The route a component serves its trace on.

    Every component names that route for its own domain — /api/poweron,
    /api/boot, /api/thermal, /api/join, /api/namespace — which is part of what
    the component is rather than boilerplate, so it is scanned rather than
    assumed. The trace route is the one whose response model is the
    component's ``*Response``; /api/anatomy and /api/catalog return their own
    shapes and are not it.
    """
    main = directory / "backend" / "app" / "main.py"
    if not main.exists():
        return None
    routes = [
        (path, model)
        for path, model in re.findall(
            r'@app\.(?:get|post)\("(/api/[a-z_]+)"(?:, response_model=(\w+))?',
            main.read_text(),
        )
        # /api/tour returns the shared TourResponse (narrated tour mode), not
        # the component's trace.
        if path not in ("/api/health", "/api/levels", "/api/tour")
    ]
    for path, model in routes:
        if model and model.endswith("Response"):
            return path
    return routes[0][0] if routes else None


def build() -> dict:
    ports = json.loads((ROOT / "ports.json").read_text())["twins"]
    components = []
    unknown = []
    entries = sorted(ROOT.iterdir())
    if ARCHIVE.is_dir():
        entries += sorted(ARCHIVE.iterdir())
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith(".") or entry.name in SKIP:
            continue
        if not (entry / "backend").exists() and not list(entry.glob("*spec*.md")):
            continue
        editorial = EDITORIAL.get(entry.name)
        if editorial is None:
            unknown.append(entry.name)
            continue
        family, status, description = editorial
        port = ports.get(entry.name, {})
        components.append({
            "name": entry.name,
            "directory": str(entry.relative_to(ROOT)),
            "family": family,
            "status": status,
            "description": description,
            "backendPort": port.get("backend"),
            "frontendPort": port.get("frontend"),
            "traceEndpoint": trace_endpoint(entry),
            "spec": next((str(p.relative_to(ROOT)) for p in sorted(entry.glob("*spec*.md"))), None),
        })
    if unknown:
        raise SystemExit(
            "components.json has no entry for: " + ", ".join(unknown) +
            "\nAdd it to EDITORIAL in scripts/gen_components.py."
        )
    problems = lifecycle_problems(components)
    if problems:
        raise SystemExit("lifecycle rules broken:\n  " + "\n  ".join(problems))
    return {
        "_comment": (
            "Generated by scripts/gen_components.py — do not hand-edit. "
            "Ports come from ports.json, trace endpoints from each backend's main.py, "
            "and the family/status/description from the EDITORIAL table in that script. "
            "Statuses are documented in docs/LIFECYCLE.md."
        ),
        "statuses": ["reference", "built", "partial", "scaffold", "archived"],
        "components": components,
    }


def main() -> int:
    target = ROOT / "components.json"
    payload = json.dumps(build(), indent=2) + "\n"
    if "--check" in sys.argv:
        current = target.read_text() if target.exists() else ""
        if current != payload:
            print("components.json is stale — run python3 scripts/gen_components.py")
            return 1
        print("components.json is current")
        return 0
    target.write_text(payload)
    print(f"wrote {target.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
