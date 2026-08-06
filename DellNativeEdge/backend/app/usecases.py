"""Use-case build sheets for the NativeEdge twin — backend data. Every
``category_id``/``option_id`` must resolve against catalog.py (enforced in
tests/test_catalog.py). Quantities and outcomes are illustrative, anchored
to the Dell sources carried in anatomy.py."""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="retail-branches",
        title="Four hundred branches, provisioned by shop managers",
        summary=(
            "The canonical estate: every branch gets a box and a one-line "
            "instruction — plug in the black cable — and the platform does "
            "the rest."
        ),
        narrative=[
            (
                "A retailer with four hundred branches has four hundred "
                "sites and zero site technicians, and the arithmetic of "
                "visiting them is the whole problem: a two-hour visit per "
                "site is a hundred working weeks of travel for every "
                "rollout, repeated at every refresh. So the deployment "
                "plan is a shipping manifest and one sentence for the "
                "shop manager: plug in the power lead and the black "
                "network cable. Everything this twin's trace shows — "
                "attestation, claiming, provisioning, blueprint, "
                "workload — then happens four hundred times without a "
                "single additional human action."
            ),
            (
                "The estate stays uniform because it was never touched "
                "individually: every branch converges on the same "
                "blueprint, runs the same point-of-sale and back-office "
                "stack from the catalog, and takes updates in the same "
                "maintenance window. When a branch's hardware fails, the "
                "replacement ships from depot, the shop manager repeats "
                "the sentence, and the blueprint rebuilds the site — "
                "repair is re-onboarding, not troubleshooting."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="endpoints", option_id="gateways", qty=400,
                rationale="One box per branch; installed by whoever is there.",
            ),
            UseCaseItem(
                category_id="identity", option_id="secure-onboarding", qty=400,
                rationale=(
                    "Four hundred unattended network joins are four "
                    "hundred reasons to attest first."
                ),
            ),
            UseCaseItem(
                category_id="orchestrator", option_id="orchestrator-ha", qty=1,
                rationale="One control plane; the estate is the unit of operation.",
            ),
            UseCaseItem(
                category_id="blueprints", option_id="blueprints-declarative", qty=1,
                rationale="One branch blueprint; four hundred convergences.",
            ),
            UseCaseItem(
                category_id="applications", option_id="catalog-apps", qty=1,
                rationale="Point-of-sale and back-office from the validated catalog.",
            ),
            UseCaseItem(
                category_id="connectivity", option_id="intermittent-wan", qty=400,
                rationale="Branch broadband drops daily; the platform assumes it.",
            ),
        ],
        outcomes=[
            Stat(label="Sites", value="400, no technician at any of them"),
            Stat(label="Human actions", value="One per site — power and a cable"),
            Stat(label="Hardware repair", value="Ship a box; re-onboarding rebuilds it"),
        ],
    ),
    UseCase(
        id="vision-inspection",
        title="A vision model on the line, updated without a visit",
        summary=(
            "Computer-vision quality inspection at the edge, retrained "
            "centrally, landed at every plant by blueprint — the day-2 "
            "story."
        ),
        narrative=[
            (
                "A manufacturer runs camera-based quality inspection on "
                "its lines: a model watches every part, flags defects in "
                "milliseconds, and cannot tolerate a cloud round trip — "
                "the line moves faster than the network. So inference "
                "runs at the edge, on XR-class servers beside the line, "
                "and the platform's job begins after deployment: models "
                "drift, defects evolve, and the data-science team "
                "retrains monthly. Without an estate platform, every "
                "retrain is a plant-by-plant visit; with one, the new "
                "model is a catalog version bump referenced by the "
                "blueprint, and the estate converges in a maintenance "
                "window."
            ),
            (
                "The trace's security beat matters doubly here: a device "
                "on a factory network sits next to operational equipment "
                "that must never meet an unauthenticated machine, so "
                "attestation-before-anything is plant policy, not "
                "IT preference. And the telemetry flowing back — "
                "inference rates, defect counts, device health — is what "
                "the observability side turns into the next retraining "
                "decision, closing the loop between the line and the "
                "data-science team."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="endpoints", option_id="poweredge-xr", qty=24,
                rationale="Rugged short-depth servers beside the lines, GPU-equipped.",
            ),
            UseCaseItem(
                category_id="edge-ai", option_id="inference-at-edge", qty=24,
                rationale="Millisecond verdicts; the line outruns any cloud.",
            ),
            UseCaseItem(
                category_id="applications", option_id="customer-workloads", qty=1,
                rationale="The inspection model is the customer's own container.",
            ),
            UseCaseItem(
                category_id="blueprints", option_id="blueprints-declarative", qty=1,
                rationale="A retrain is a version bump; the estate converges.",
            ),
            UseCaseItem(
                category_id="security", option_id="zero-trust-edge", qty=24,
                rationale="Factory networks border OT gear; nothing implicit.",
            ),
            UseCaseItem(
                category_id="observability", option_id="aiops-integration", qty=1,
                rationale="Defect and drift telemetry drives the next retrain.",
            ),
        ],
        outcomes=[
            Stat(label="Plants", value="6 · 24 line servers"),
            Stat(label="Model updates", value="Monthly, zero site visits"),
            Stat(label="Verdict latency", value="Milliseconds, on the line"),
        ],
    ),
    UseCase(
        id="substation-cloud",
        title="A distributed private cloud across substations",
        summary=(
            "A utility's estate where disconnection is by design: sites "
            "that run autonomously and reconcile when the link returns."
        ),
        narrative=[
            (
                "A utility operates edge compute at dozens of "
                "substations — protection analytics, grid telemetry, "
                "camera security — and its network philosophy inverts "
                "the datacenter's: substations are *designed* to operate "
                "disconnected, because the grid must not depend on a WAN "
                "link. The platform's assumed-intermittent connectivity "
                "stops being resilience engineering and becomes the "
                "operating mode: sites run autonomously on their "
                "blueprint-declared state, and when the link returns "
                "they reconcile — pulling updates, pushing telemetry, "
                "rotating certificates — before going quiet again."
            ),
            (
                "This is the estate pattern Dell now markets as "
                "Distributed Private Cloud: many small sites behaving as "
                "one cloud, with NativeEdge as the substrate. The "
                "security posture is the strictest in this twin — "
                "critical infrastructure, physically exposed cabinets, "
                "regulatory audit — and it leans entirely on the "
                "attestation gate and per-endpoint Zero Trust the trace "
                "dwells on: every device proved its identity before it "
                "existed, and no site's LAN is trusted because it is "
                "remote, fenced, or familiar."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="endpoints", option_id="poweredge-xr", qty=60,
                rationale="Substation cabinets: rugged, filtered, unattended.",
            ),
            UseCaseItem(
                category_id="connectivity", option_id="intermittent-wan", qty=60,
                rationale="Disconnection is the design, not the failure mode.",
            ),
            UseCaseItem(
                category_id="orchestrator", option_id="orchestrator-ha", qty=1,
                rationale="One estate brain, far from every substation.",
            ),
            UseCaseItem(
                category_id="security", option_id="zero-trust-edge", qty=60,
                rationale="Critical infrastructure in physically exposed cabinets.",
            ),
            UseCaseItem(
                category_id="identity", option_id="secure-onboarding", qty=60,
                rationale="Audit requires proof of what joined, and when.",
            ),
            UseCaseItem(
                category_id="services", option_id="validated-designs", qty=1,
                rationale="Engineered once against the energy reference design.",
            ),
        ],
        outcomes=[
            Stat(label="Substations", value="60, autonomous by design"),
            Stat(label="Reconciliation", value="Opportunistic — when the link is up"),
            Stat(label="Trust", value="Attested at joining; never assumed after"),
        ],
    ),
]
