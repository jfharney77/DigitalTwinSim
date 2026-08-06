"""Capability catalog for the NativeEdge twin — backend data, not frontend
code, exactly like the other twins. Categories map onto the architecture
diagram via ``region_ids`` so the UI can light up where a capability lives.
Copy is written for a technically skilled reader new to edge operations:
vocabulary (zero-touch provisioning, attestation, blueprint, ISV, "day 2",
private 5G) is spelled out on first use. Counts are illustrative, anchored
to the Dell sources carried in anatomy.py."""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

_ENDPOINT_REGIONS = [f"endpoint-e{i}" for i in range(1, 5)]

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="endpoints",
        name="Endpoint hardware",
        blurb=(
            "What actually sits at the site — chosen for the site's "
            "conditions, managed identically regardless."
        ),
        limits="Hundreds of sites per estate; one platform across all of them",
        region_ids=_ENDPOINT_REGIONS,
        options=[
            CatalogOption(
                id="poweredge-xr",
                name="PowerEdge XR-series servers",
                summary=(
                    "Short-depth, ruggedized servers built for closets, "
                    "cabinets, and vehicles rather than machine rooms."
                ),
                details=(
                    "The XR line is PowerEdge re-engineered for places "
                    "that are not datacenters: short chassis for wall "
                    "cabinets and vehicle racks, wider temperature and "
                    "dust tolerances, filtered bezels. An XR4000 in a "
                    "trackside garage or an XR12 in a substation runs "
                    "the same iDRAC-style management the R760 twin "
                    "shows — the difference is that nobody is ever "
                    "there, which is the gap this platform fills."
                ),
            ),
            CatalogOption(
                id="gateways",
                name="Edge gateways",
                summary=(
                    "Small fanless boxes that translate operational "
                    "equipment — sensors, PLCs, cameras — into IT."
                ),
                details=(
                    "Gateways sit at the boundary between operational "
                    "technology (the plant's sensors, controllers, and "
                    "cameras, speaking industrial protocols) and the IT "
                    "estate. They are numerous, cheap, and installed by "
                    "whoever is wiring the site — which makes zero-touch "
                    "onboarding more valuable per box here than "
                    "anywhere else in the catalog."
                ),
            ),
            CatalogOption(
                id="workstations",
                name="Precision workstations & client devices",
                summary=(
                    "The estate is not only servers: engineering "
                    "workstations and desktops enroll the same way."
                ),
                details=(
                    "NativeEdge 2.0 extended the estate to client "
                    "devices — Precision workstations running local "
                    "inference (the Pro Max Plus twin's machine is "
                    "exactly this class), point-of-sale desktops, kiosk "
                    "hardware. One onboarding path and one blueprint "
                    "language across servers and clients is what keeps "
                    "an estate from becoming three estates."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="identity",
        name="Device identity & secure onboarding",
        blurb=(
            "The gate: a device exists to the platform only after it "
            "proves it is the machine Dell built."
        ),
        limits="Identity burned in at manufacture; attestation on first boot",
        region_ids=["identity"],
        options=[
            CatalogOption(
                id="secure-onboarding",
                name="Secure device onboarding",
                summary=(
                    "Cryptographic proof of hardware and firmware "
                    "integrity before anything is installed."
                ),
                details=(
                    "Every NativeEdge endpoint carries a cryptographic "
                    "identity created when Dell manufactured it. On "
                    "first boot the device presents that identity plus "
                    "measurements of its boot chain, and the platform "
                    "verifies both against factory records before the "
                    "device receives anything — no OS, no secrets, no "
                    "claim. Zero-touch provisioning without this step "
                    "would be an unauthenticated machine joining the "
                    "estate politely; the twin's trace dwells on "
                    "attestation for exactly that reason."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="orchestrator",
        name="The Orchestrator",
        blurb="One control plane for the whole estate — the product, singular.",
        limits="One Orchestrator per estate (HA-deployed); sites in the hundreds",
        region_ids=["orchestrator"],
        options=[
            CatalogOption(
                id="orchestrator-ha",
                name="NativeEdge Orchestrator (highly available)",
                summary=(
                    "The claiming, provisioning, reconciling brain — "
                    "deployed redundantly, off-site from every edge."
                ),
                details=(
                    "The Orchestrator claims attested devices, "
                    "provisions OS and runtime, reconciles sites "
                    "against blueprints, and drives every 'day 2' "
                    "operation — updates, certificate rotation, "
                    "decommissioning — from one place. It runs highly "
                    "available in a datacenter or cloud, never at the "
                    "edge sites themselves: the estate must survive "
                    "any single site, including the one the control "
                    "plane would have lived at."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="blueprints",
        name="Blueprints & automation",
        blurb="Sites are described once, declaratively — then converged, forever.",
        limits="One blueprint per site class; edits roll out estate-wide",
        region_ids=["blueprint"],
        options=[
            CatalogOption(
                id="blueprints-declarative",
                name="Declarative site blueprints",
                summary=(
                    "The end state written down — apps, config, policy — "
                    "with the Orchestrator computing the steps."
                ),
                details=(
                    "A blueprint states what a class of site runs: "
                    "applications, configuration, security policy, "
                    "update windows. It is declarative — destination, "
                    "not driving directions — so the Orchestrator can "
                    "converge four hundred sites that are each in a "
                    "slightly different state. Estate-wide change is a "
                    "blueprint edit; per-site scripting is the thing "
                    "this exists to abolish."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="applications",
        name="Application catalog & workloads",
        blurb="The estate's app store: Dell-packaged, ISV, and your own containers.",
        limits="Deployed and updated by blueprint reference only",
        region_ids=["catalog"],
        options=[
            CatalogOption(
                id="catalog-apps",
                name="Catalog applications (Dell + ISV)",
                summary=(
                    "Packaged, validated workloads — from vision "
                    "inspection to point-of-sale — deployable by name."
                ),
                details=(
                    "The catalog carries Dell-packaged applications and "
                    "independent software vendors' (ISV) offerings, "
                    "validated to deploy on NativeEdge endpoints: "
                    "computer-vision inspection, retail point-of-sale, "
                    "manufacturing analytics. A blueprint references "
                    "them by name; the platform handles placement, "
                    "installation, and updates over the same pulled, "
                    "verified path as everything else."
                ),
            ),
            CatalogOption(
                id="customer-workloads",
                name="Customer containers & VMs",
                summary=(
                    "Your own software rides the same rails — the "
                    "platform is a runway, not a walled garden."
                ),
                details=(
                    "Most estates exist to run the customer's own "
                    "software — a team's telemetry pipeline, a bank's "
                    "branch stack, a race team's trackside ingest. "
                    "NativeEdge deploys customer containers and VMs "
                    "through the identical blueprint-and-catalog "
                    "motion, so 'ours' and 'bought' software share one "
                    "lifecycle, one security posture, and one update "
                    "path."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="security",
        name="Zero Trust & policy",
        blurb="A box in a public branch is on hostile ground by default.",
        limits="Enforced per endpoint, declared per blueprint",
        region_ids=["policy"],
        options=[
            CatalogOption(
                id="zero-trust-edge",
                name="Zero Trust enforcement at the edge",
                summary=(
                    "Least privilege, verified workloads, no implicit "
                    "trust in the site's own network."
                ),
                details=(
                    "An edge device sits physically exposed — in a "
                    "branch anyone can walk into, a cabinet anyone "
                    "might open — so the platform assumes hostile "
                    "ground: workloads run least-privilege, only "
                    "verified software executes, traffic is encrypted, "
                    "and the site LAN earns nothing by being local. "
                    "The FortZero twin makes the whole argument; here "
                    "it is applied automatically, per endpoint, as "
                    "part of what the blueprint declares."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="connectivity",
        name="Networking & connectivity",
        blurb="Links are assumed to fail — the platform is built around it.",
        limits="Any WAN the site offers; interruption is the design case",
        region_ids=["network"],
        options=[
            CatalogOption(
                id="intermittent-wan",
                name="Intermittent-WAN operation",
                summary=(
                    "Resumable transfers and local autonomy: a dropped "
                    "link is Tuesday, not an incident."
                ),
                details=(
                    "Edge links — branch broadband, cellular, satellite "
                    "on a ship, whatever a race weekend offers — drop "
                    "constantly. Every platform transfer is therefore "
                    "resumable, every device pulls rather than being "
                    "pushed to, and workloads keep running through an "
                    "outage: the site needs the Orchestrator to "
                    "*change*, not to *be*. Substation estates take "
                    "this to its extreme — disconnection is by design, "
                    "not failure."
                ),
            ),
            CatalogOption(
                id="private-5g",
                name="Private 5G & campus networks",
                summary=(
                    "For plants and venues where wiring is impossible "
                    "and Wi-Fi is not dependable enough."
                ),
                details=(
                    "Factories, ports, and venues increasingly run "
                    "private 5G — their own cellular network — for "
                    "coverage no cable plant can reach: moving "
                    "vehicles, temporary structures, hundred-acre "
                    "yards. To NativeEdge it is just another WAN the "
                    "endpoints cross; to the customer it is often the "
                    "thing that made an edge estate feasible at all."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="observability",
        name="Observability & AIOps",
        blurb="NativeEdge deploys and enforces; the watching half closes the loop.",
        limits="Telemetry from every endpoint, streamed centrally",
        region_ids=["observability"],
        options=[
            CatalogOption(
                id="aiops-integration",
                name="CloudIQ / AIOps integration",
                summary=(
                    "Estate telemetry lands in the same observability "
                    "world the CloudIQ twin models."
                ),
                details=(
                    "Every endpoint streams health and lifecycle "
                    "telemetry to the operations center and onward to "
                    "AIOps tooling — Dell's CloudIQ/AIOps world, which "
                    "this repo twins separately. The division of labor "
                    "is clean and deliberate: NativeEdge is hands "
                    "(deploy, enforce, update), observability is eyes "
                    "(watch, predict, alert), and an unstaffed estate "
                    "needs both or it has neither."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="edge-ai",
        name="Edge AI inference",
        blurb="The workload that made edge estates urgent: models near the data.",
        limits="Models retrained centrally, rolled out by blueprint",
        region_ids=_ENDPOINT_REGIONS + ["catalog"],
        options=[
            CatalogOption(
                id="inference-at-edge",
                name="Inference at the endpoint",
                summary=(
                    "Vision models on the line, analytics in the "
                    "garage — where latency and data gravity live."
                ),
                details=(
                    "The workload pattern that made edge estates "
                    "urgent: a camera model inspecting parts cannot "
                    "wait on a round trip to a cloud, and a race "
                    "weekend's telemetry is too heavy to ship raw. So "
                    "the model runs at the endpoint — on an XR server's "
                    "GPU or a discrete-NPU workstation (the Pro Max "
                    "Plus twin's machine) — and the *management* "
                    "problem becomes the hard one: retrain centrally, "
                    "then land the new model at every site without a "
                    "visit. That path is this platform's catalog-and-"
                    "blueprint motion, verbatim."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="services",
        name="Services & validated designs",
        blurb="How estates actually start: designed once, then repeated.",
        limits="Validated per vertical — retail, manufacturing, energy",
        options=[
            CatalogOption(
                id="validated-designs",
                name="Validated designs & deployment services",
                summary=(
                    "Per-vertical reference builds so the first site is "
                    "engineered and the next 399 are copies."
                ),
                details=(
                    "Dell publishes validated designs for the common "
                    "verticals — retail, manufacturing, energy — pairing "
                    "endpoint hardware, blueprints, and catalog "
                    "workloads that are known to work together. The "
                    "engineering happens once, on the first site; every "
                    "subsequent site is a copy stamped out by the "
                    "zero-touch flow this twin's trace walks through. "
                    "That economics — design once, repeat cheaply — is "
                    "the business case under the whole platform."
                ),
            ),
        ],
    ),
]
