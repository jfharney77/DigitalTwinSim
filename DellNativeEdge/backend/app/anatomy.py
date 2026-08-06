"""Platform-architecture data: the Dell NativeEdge platform, annotated.

Like the CloudIQ twin, the subject is software, so the "anatomy" is an
architecture diagram — regions in a normalized coordinate space the
frontend renders as SVG, flow running left to right: the edge estate (many
identical endpoints, deliberately drawn as a uniform band) → the WAN → the
secure-onboarding gate → the NativeEdge Orchestrator (central and singular
— the biggest block in the drawing, because one control plane is the whole
product) → blueprints and the application catalog → policy and
observability. Geometry is stylized — favor a correct mental model over
architectural completeness (project scope guardrail).

The geometry carries the lesson the way Exascale's does: an estate is one
building block repeated (``test_anatomy.py`` pins the endpoint band as
uniform, N ≥ 4), and everything that makes the estate manageable sits on
the far side of a WAN from it — nothing on the left edge ever has a
person standing next to it.
"""

from __future__ import annotations

from .leveling import L
from .models import PlatformMap, PlatformRegion, Photo, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
PLATFORM_ILLO = Photo(
    url="/nativeedge-platform.svg",
    caption=(
        "The NativeEdge platform, schematically: a uniform band of edge "
        "endpoints behind a WAN, the secure-onboarding gate, the singular "
        "Orchestrator, and the blueprint/catalog/policy/observability "
        "plane that manages the estate without anyone on site."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_ENDPOINT_DESC = (
    "One edge endpoint — a PowerEdge XR-class server, gateway, or "
    "workstation at a site with no IT staff: a branch, a line, a "
    "substation, a trackside garage. Drawn identical to its neighbours on "
    "purpose: an estate is one building block repeated, and everything "
    "that makes four hundred of these manageable — identity burned in at "
    "manufacture, outbound-only onboarding, pulled software — is designed "
    "so that no person ever stands next to this box after the day it was "
    "plugged in."
)


def _endpoint(idx: int, y: float) -> PlatformRegion:
    return PlatformRegion(
        id=f"endpoint-e{idx}", kind="endpoint", label=f"Edge site {idx}",
        x=0, y=y, w=14, h=12, description=_ENDPOINT_DESC,
    )


ANATOMY = PlatformMap(
    id="nativeedge",
    name="Dell NativeEdge",
    vendor="Dell Technologies",
    form_factor="Edge operations software platform",
    generation="NativeEdge 2.x (Dell Distributed Private Cloud basis)",
    year=2024,
    width=100,
    height=58,
    overview=L(
        novice=(
            "This is a control system for computers that live far from any "
            "IT department — in shops, factories, substations, race-weekend "
            "garages. The band of identical boxes on the left is the estate: "
            "the same edge computer repeated at hundreds of sites, none of "
            "which has a technician. Everything else in the picture exists "
            "so that nobody ever has to visit those sites. When a new box is "
            "plugged in, it proves to the identity gate that it really is "
            "the machine Dell built, and then the big block in the middle — "
            "the Orchestrator — takes over: it decides what the site should "
            "run from a written-down plan, installs everything over the "
            "network, applies the security rules, and watches the result. "
            "The only human act in the whole diagram is connecting two "
            "cables at the far left."
        ),
        plain=(
            "Dell NativeEdge is an edge-operations platform: it manages "
            "estates of servers, gateways, and workstations deployed "
            "outside any datacenter. The diagram reads left to right — a "
            "uniform band of endpoints (an estate is one building block "
            "repeated), the WAN, the secure-onboarding gate where a device "
            "cryptographically proves it is the machine Dell built, the "
            "singular Orchestrator that claims devices and reconciles them "
            "against declarative blueprints, then the application catalog, "
            "Zero Trust policy, and observability. The design premise: no "
            "site has IT staff, so the only human action anywhere is power "
            "and a network cable."
        ),
        standard=(
            "Dell NativeEdge is Dell's edge operations software platform "
            "(2023; 2.0 in 2024; now also the basis of Dell Distributed "
            "Private Cloud): it manages estates of servers, gateways, "
            "workstations, and desktops deployed outside the datacenter — "
            "factory floors, retail branches, substations, ships, "
            "trackside garages. The diagram reads left to right. The "
            "endpoint band is drawn uniform on purpose: an estate is one "
            "building block repeated, at sites that have no IT staff, "
            "which is the premise everything else answers. Behind the WAN "
            "sits the secure-onboarding gate — a device wakes, proves "
            "cryptographically that it is the machine Dell built, and "
            "only then exists to the platform — and the NativeEdge "
            "Orchestrator, drawn central and singular because one "
            "control plane claiming, provisioning, and reconciling the "
            "whole estate is the product. To its right, the declarative "
            "blueprints that state what each site-class runs, the "
            "application catalog that supplies it, and the Zero Trust "
            "policy and observability planes that keep it honest. The "
            "trace on the first tab walks one site through all of it "
            "with exactly one human action."
        ),
        technical=(
            "Edge operations platform: uniform endpoint band (N=4 drawn; "
            "estates are hundreds) → WAN → secure device onboarding "
            "(manufacture-time identity + measured boot) → singular "
            "Orchestrator (claim, provision, blueprint reconciliation) → "
            "catalog / Zero Trust policy / observability. Phase order "
            "crated → power → attest → onboard → provision → blueprint → "
            "workload → managed. Asserted: operator_actions peaks at 1 "
            "(power phase) and never increments; nothing runs and no "
            "endpoint counts as online before trust_established; trust "
            "is monotone; the Orchestrator is never in the endpoint "
            "count; endpoints light in lockstep; attestation holds max "
            "dwell. Geometry pinned: endpoint band uniform, Orchestrator "
            "singular/largest/central, estate strictly left of control."
        ),
        expert=(
            "ZTP estate platform. operator_actions ≤ 1 (asserted); no "
            "run before attest; trust monotone; Orchestrator ∉ endpoint "
            "count; lockstep estate; attest = max dwell. Geometry: "
            "uniform endpoint band, singular central Orchestrator, "
            "estate left / control right."
        ),
    ),
    regions=[
        _endpoint(1, 1),
        _endpoint(2, 15),
        _endpoint(3, 29),
        _endpoint(4, 43),
        PlatformRegion(
            id="network", kind="network", label="WAN",
            x=16, y=1, w=8, h=54,
            description=(
                "The wide-area network between the sites and the "
                "Orchestrator — broadband at a branch, private 5G at a "
                "plant, satellite on a ship, whatever a race weekend "
                "offers. It is drawn as a band the whole estate must "
                "cross because its properties shape the platform: links "
                "are intermittent by design, so every transfer is "
                "resumable, every device pulls rather than being pushed "
                "to, and nothing assumes the connection stays up."
            ),
        ),
        PlatformRegion(
            id="identity", kind="identity", label="Secure onboarding",
            x=26, y=20, w=12, h=16,
            description=(
                "The gate every device passes exactly once: secure "
                "device onboarding. A NativeEdge endpoint carries a "
                "cryptographic identity burned in at manufacture, and on "
                "first boot it proves — via that identity and "
                "measurements of its own boot chain — that it is the "
                "unmodified machine Dell built and shipped. Until the "
                "proof lands, the platform gives it nothing. This is the "
                "iDRAC twin's hardware root of trust, made the entry "
                "ticket to an entire estate."
            ),
        ),
        PlatformRegion(
            id="orchestrator", kind="orchestrator", label="NativeEdge Orchestrator",
            x=42, y=12, w=20, h=34,
            description=(
                "The platform's center of gravity, drawn as the biggest "
                "block in the diagram because one control plane is the "
                "product: the Orchestrator claims attested devices into "
                "the estate, provisions their OS and runtime, reconciles "
                "every site against its blueprint, rolls out updates, and "
                "retires hardware at end of life — for hundreds of sites, "
                "from one place, over links assumed to be unreliable. It "
                "is the answer to the question the endpoint band poses: "
                "how do you operate four hundred sites that have no "
                "operators?"
            ),
        ),
        PlatformRegion(
            id="blueprint", kind="blueprint", label="Blueprints",
            x=66, y=1, w=16, h=15,
            description=(
                "Declarative site definitions: what a site of each class "
                "runs — applications, configuration, policy, update "
                "windows — written once by an engineer who will never "
                "visit. A blueprint states the end state, not the steps; "
                "the Orchestrator computes whatever this particular site "
                "needs to converge, which is the only approach that "
                "survives four hundred sites in four hundred slightly "
                "different states."
            ),
        ),
        PlatformRegion(
            id="catalog", kind="catalog", label="App catalog",
            x=66, y=20, w=16, h=15,
            description=(
                "The application catalog: Dell-packaged software, "
                "independent software vendors' offerings, and the "
                "customer's own containers, all deployable by blueprint "
                "reference. It is the estate's app store — a "
                "computer-vision inspection model, a point-of-sale "
                "stack, a telemetry pipeline — and the same catalog "
                "path that installs a workload also updates it, which "
                "is how a centrally retrained model reaches every site "
                "without a single visit."
            ),
        ),
        PlatformRegion(
            id="policy", kind="policy", label="Zero Trust policy",
            x=86, y=1, w=13, h=15,
            description=(
                "The security plane: Zero Trust policy enforced at every "
                "endpoint — least-privilege workloads, verified software "
                "only, encrypted traffic, no implicit trust in the "
                "site's own network (a box in a public-facing branch is "
                "on hostile ground by default). The FortZero twin makes "
                "the full argument; here it is applied per-endpoint, "
                "automatically, as part of what the blueprint declares."
            ),
        ),
        PlatformRegion(
            id="observability", kind="observability", label="Observability",
            x=86, y=20, w=13, h=15,
            description=(
                "The watching half: health, telemetry, and lifecycle "
                "state for every endpoint in the estate, streamed to the "
                "operations center and onward to AIOps tooling — the "
                "CloudIQ twin's world. The division of labor is clean: "
                "NativeEdge deploys and enforces, observability watches "
                "and predicts, and together they close the loop that "
                "keeps an unstaffed estate honest."
            ),
        ),
    ],
    stats=[
        Stat(label="Subject", value="Edge operations software platform (2023; 2.0 in 2024)"),
        Stat(label="Manages", value="PowerEdge XR, gateways, workstations, desktops"),
        Stat(label="Human actions per site", value="1 — power and a network cable"),
        Stat(label="Onboarding", value="Secure device onboarding — attest before anything"),
        Stat(label="Control plane", value="One Orchestrator per estate, sites in the hundreds"),
        Stat(label="Configuration", value="Declarative blueprints — intent, not steps"),
        Stat(label="Connectivity", value="Assumed intermittent — every transfer resumable"),
        Stat(label="Security", value="Zero Trust enforced per endpoint"),
    ],
    photo=PLATFORM_ILLO,
    sources=[
        SourceLink(
            label="Dell NativeEdge — edge platform page",
            url="https://www.dell.com/en-us/dt/solutions/edge-computing/edge-platform.htm",
        ),
        SourceLink(
            label="Announcing Dell NativeEdge 2.0 (Dell blog)",
            url="https://www.dell.com/en-us/blog/announcing-dell-nativeedge-2-0-reimagining-edge-operations/",
        ),
        SourceLink(
            label="NativeEdge Orchestrator (Dell InfoHub white paper)",
            url="https://infohub.delltechnologies.com/en-us/l/introduction-to-the-dell-nativeedge-software-platform-white-paper-4/nativeedge-orchestrator-11/",
        ),
        SourceLink(
            label="Dell NativeEdge launch press release (May 2023)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2023~05~dell-nativeedge-software-transforms-edge-operations.htm",
        ),
    ],
)
