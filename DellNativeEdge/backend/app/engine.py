"""Pure zero-touch-onboarding engine for the Dell NativeEdge twin.

``simulate()`` returns the deterministic trace of one edge site going from
a sealed crate to a managed estate. Same purity rule as every other twin in
this repo: no FastAPI, no IO, no timers — the frontend owns the playback
clock, and each ``OnboardState`` is plain data the renderer consumes.
``cycle_cost`` marks the long stage (attestation) so the UI dwells on it.

The idea this twin exists to teach: **nobody touches the device.** Every
hardware twin in this repo assumes a person at the moment of truth —
someone presses the R760's power button, racks the XE9712, plugs the
Alienware in. An edge estate breaks that assumption at scale: four hundred
sites, no IT staff at any of them, and the person who unboxes the machine
is a shop manager whose job is not this. So NativeEdge inverts the
direction of trust. The device is not provisioned *by* someone; it wakes,
proves cryptographically that it is the machine Dell built and shipped,
and asks the central Orchestrator what it is supposed to become. The only
human action in the whole sequence is supplying power and a network cable
— ``operator_actions`` reaches 1 there and never moves again, and
``tests/test_engine.py`` asserts exactly that. Timings are illustrative;
favor a correct mental model over measured numbers (project scope
guardrail).
"""

from __future__ import annotations

from .leveling import L
from .models import OnboardState

# The endpoints drawn at this site (an estate is one building block
# repeated; anatomy.py draws four).
ENDPOINTS = ["e1", "e2", "e3", "e4"]


def _endpoints() -> list[str]:
    return [f"endpoint-{e}" for e in ENDPOINTS]


def simulate() -> list[OnboardState]:
    """One site's journey from sealed crate to managed estate, as pure data."""
    return [
        OnboardState(
            step=0,
            phase="crated",
            label="The crate arrives — nothing is configured",
            description=L(
                novice=(
                    "Boxes arrive at a site with no IT department: a shop, a "
                    "factory floor, a race-weekend garage. Inside each box is "
                    "an edge computer that has never been switched on since it "
                    "left Dell's factory, and nobody on site knows how to set "
                    "up a server — nor should they have to. Notice what is "
                    "missing from this whole story from the start: there is no "
                    "technician in it. The count of human actions taken so far "
                    "is zero, and the point of everything that follows is that "
                    "it will only ever reach one."
                ),
                plain=(
                    "Sealed crates arrive at a site with no IT staff — a "
                    "branch, a line, a substation, a garage. Inside are edge "
                    "devices exactly as Dell's factory built them: nothing "
                    "configured, no OS staged for this site, no credentials "
                    "on board that matter yet. The operator-actions counter "
                    "reads zero, and the trace exists to show it stopping at "
                    "one."
                ),
                standard=(
                    "Sealed crates arrive at the site — a retail branch, a "
                    "factory line, a substation, a trackside garage — and "
                    "the site has no IT staff, which is the premise the "
                    "whole platform is built on. Inside each crate is an "
                    "edge device exactly as Dell's factory built it: "
                    "firmware signed, identity burned in at manufacture, "
                    "nothing configured for this site. Every hardware twin "
                    "in this repo assumes a person at the moment of truth — "
                    "someone presses the power button, someone racks the "
                    "machine. Watch the operator-actions counter through "
                    "this trace: it reads zero now, it will reach one at "
                    "the next step, and the platform's entire argument is "
                    "that it never moves again."
                ),
                technical=(
                    "Crates on site, no IT staff present — the design "
                    "premise. Devices are factory-state: signed firmware, "
                    "manufacture-time identity, no site configuration. "
                    "operator_actions = 0; the trace asserts it peaks at 1."
                ),
                expert=(
                    "Factory-state devices, no staff on site. "
                    "operator_actions = 0, ceiling 1 (asserted)."
                ),
            ),
            active_regions=[],
            endpoints_online=0,
            operator_actions=0,
            trust_established=False,
            progress_percent=0,
            elapsed_seconds=0,
        ),
        OnboardState(
            step=1,
            phase="power",
            label="Power and a network cable — the only human action",
            description=L(
                novice=(
                    "Someone on site — a shop manager, a plant supervisor, a "
                    "mechanic — follows a one-line instruction: plug in the "
                    "power lead and the network cable. That is the entire "
                    "job, and it is the only thing any human at any site will "
                    "do in this whole story. The counter ticks from zero to "
                    "one. Everything after this happens between the machine "
                    "and a distant control system, in both cases without "
                    "anyone standing there — because at four hundred sites, "
                    "'someone technical stands there' is not a plan."
                ),
                plain=(
                    "A shop manager follows a one-line instruction — plug in "
                    "the power lead and the black network cable — and the "
                    "operator-actions counter ticks 0 → 1, where it stays. "
                    "The device boots its factory firmware and reaches out "
                    "for the Orchestrator; nothing is pushed to it, and "
                    "nobody logs in. At estate scale this step is the whole "
                    "human resourcing plan, which is why it must fit in one "
                    "sentence."
                ),
                standard=(
                    "Someone on site follows a one-line instruction: plug "
                    "in the power lead and the black network cable. The "
                    "operator-actions counter ticks from zero to one — and "
                    "that is the last time it moves, because this is the "
                    "last thing any human does. The device boots the "
                    "firmware Dell's factory signed, finds the network, and "
                    "reaches *out* toward the Orchestrator: nothing is "
                    "pushed at it, no laptop is connected to it, nobody "
                    "logs in locally. The direction of that first "
                    "connection is the platform's whole inversion — the "
                    "device asks to be claimed, rather than waiting to be "
                    "configured. Multiply this moment by four hundred "
                    "sites and the one-line instruction is the entire "
                    "human resourcing plan."
                ),
                technical=(
                    "Power + network applied by untrained staff — "
                    "operator_actions 0 → 1, final value (asserted). "
                    "Device boots signed factory firmware and initiates "
                    "outbound contact; no local login, no push, no console. "
                    "Pull, not push, from the first packet."
                ),
                expert=(
                    "Power + cable: operator_actions → 1, never again. "
                    "Outbound-only first contact; no local access."
                ),
            ),
            active_regions=_endpoints() + ["network"],
            endpoints_online=0,
            operator_actions=1,
            trust_established=False,
            progress_percent=5,
            elapsed_seconds=120,
        ),
        OnboardState(
            step=2,
            phase="attest",
            label="The device proves it is the machine Dell built",
            description=L(
                novice=(
                    "The longest stage, on purpose. Before anything is "
                    "installed, the machine has to prove what it is: "
                    "measurements of its hardware and firmware, taken as it "
                    "started up, are checked against a record of what Dell "
                    "actually built and shipped — a certificate created in "
                    "the factory. Until that proof lands, this box is just an "
                    "unknown computer that plugged itself into the company "
                    "network, and it gets nothing: no software, no secrets, "
                    "no trust. This screen dwells here because the security "
                    "step is the point, not paperwork to skip past."
                ),
                plain=(
                    "The longest stage, deliberately. The device presents "
                    "its factory-issued identity and measurements of its "
                    "boot chain — hardware, firmware, configuration — to "
                    "the secure-onboarding service, which checks them "
                    "against what Dell manufactured. Until attestation "
                    "passes, the box is an unauthenticated stranger on the "
                    "network and receives nothing. Zero-touch without this "
                    "step is just an open door; the dwell time is the twin "
                    "refusing to treat security as boilerplate."
                ),
                standard=(
                    "The longest stage, and deliberately so. The device "
                    "presents its factory-issued cryptographic identity "
                    "and measurements of its own boot chain — hardware, "
                    "firmware, configuration — to the secure-onboarding "
                    "service, which verifies them against what Dell "
                    "manufactured (the same hardware root-of-trust story "
                    "the iDRAC twin tells from inside one server). Until "
                    "the proof completes, this machine is exactly what it "
                    "looks like: an unknown computer that connected "
                    "itself to the network, and it receives nothing — no "
                    "OS, no secrets, no claim. Zero-touch provisioning "
                    "without attestation would just be an unauthenticated "
                    "machine joining your estate politely, and the trace "
                    "dwells here because proving integrity is genuinely "
                    "the slow part — and the part everything downstream "
                    "stands on."
                ),
                technical=(
                    "Max-dwell stage. Device presents manufacture-time "
                    "identity + measured boot evidence; the onboarding "
                    "service verifies against factory records (hardware "
                    "root of trust — cf. the iDRAC twin). No claim, no "
                    "payload, no secrets until verification completes. "
                    "trust_established stays false through this step; "
                    "ZTP without attestation is an open door."
                ),
                expert=(
                    "Max dwell: measured boot + factory identity verified. "
                    "Nothing lands pre-verification. trust still false "
                    "here."
                ),
            ),
            active_regions=_endpoints() + ["identity", "network"],
            endpoints_online=0,
            operator_actions=1,
            trust_established=False,
            progress_percent=20,
            elapsed_seconds=300,
            cycle_cost=5,
        ),
        OnboardState(
            step=3,
            phase="onboard",
            label="The Orchestrator claims the site into the estate",
            description=L(
                novice=(
                    "Proof accepted. The central control system — the "
                    "Orchestrator, running far from this site — recognizes "
                    "the machines as ones it was expecting and claims them "
                    "into the estate. The online counter jumps from zero to "
                    "four, all at once: the site is claimed as a set, not "
                    "one box at a time. Note who did this — no one. The "
                    "machines asked, proved themselves, and were accepted, "
                    "while the human count stayed at one."
                ),
                plain=(
                    "Attestation passed, trust is established, and the "
                    "Orchestrator claims the site: the devices appear in "
                    "the estate inventory, bound to this site's "
                    "definition, and endpoints-online snaps 0 → 4 together "
                    "— a site is claimed as a set. The Orchestrator "
                    "itself is never in that count: it is the thing doing "
                    "the claiming, not a thing being claimed. Operator "
                    "actions: still one."
                ),
                standard=(
                    "The proof lands, trust is established — true from "
                    "here to the end of the trace, never revoked — and "
                    "the NativeEdge Orchestrator claims the devices into "
                    "the estate: they appear in inventory, bound to this "
                    "site, keyed to the blueprint that describes what "
                    "the site should run. The endpoints-online counter "
                    "snaps from zero to four in one step, because a "
                    "site is claimed as a set — the estate's unit is "
                    "the site, not the box. Two things to notice: the "
                    "Orchestrator is not in the counter, because it is "
                    "the claimer and never the claimed; and the "
                    "operator-actions counter still reads one, because "
                    "the claiming happened between machines."
                ),
                technical=(
                    "trust_established → true (monotone from here — "
                    "asserted). Orchestrator claims the site as a unit: "
                    "endpoints_online 0 → 4 in one step, devices bound "
                    "to site + blueprint. The Orchestrator is excluded "
                    "from the endpoint count (asserted). "
                    "operator_actions unchanged at 1."
                ),
                expert=(
                    "Trust true (monotone). Site claimed as a set: "
                    "online 0 → 4. Orchestrator ∉ count. Humans: still 1."
                ),
            ),
            active_regions=_endpoints() + ["identity", "orchestrator", "network"],
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=40,
            elapsed_seconds=360,
            cycle_cost=2,
        ),
        OnboardState(
            step=4,
            phase="provision",
            label="OS and platform software land — pulled, not pushed",
            description=L(
                novice=(
                    "Now the machines become useful. Operating systems and "
                    "the platform's own software download to all four "
                    "devices at once, over the ordinary network the cable "
                    "plugged into — no USB sticks, no laptop visits, no "
                    "screens attached. The direction matters: each device "
                    "fetches what the control system says it should have, "
                    "checks the signatures, and installs it. If a site "
                    "loses its connection halfway, the device just resumes "
                    "when the link returns — patience is built in, because "
                    "edge networks fail all the time."
                ),
                plain=(
                    "Operating systems and the NativeEdge platform "
                    "software land on all four endpoints in lockstep — "
                    "pulled by each device from the Orchestrator, "
                    "signature-checked, installed. No media, no site "
                    "visit, no console. Interruptions are assumed rather "
                    "than exceptional: a device that loses WAN mid-download "
                    "resumes when the link returns, which is what "
                    "separates edge provisioning from datacenter "
                    "provisioning."
                ),
                standard=(
                    "Operating systems and the platform's own runtime "
                    "land on all four endpoints in lockstep — an estate "
                    "is provisioned as a set, the same visual beat as "
                    "VxRail's nodes booting together. Every byte is "
                    "pulled: the device asks the Orchestrator what it "
                    "should run, fetches it over the WAN, verifies the "
                    "signatures against the trust established at "
                    "attestation, and installs. Nothing is pushed at an "
                    "address someone typed, no USB stick exists in this "
                    "story, and the links are assumed to be bad — a "
                    "device that loses its connection mid-download "
                    "resumes when the link returns, because at a "
                    "substation or a race weekend, 'the WAN dropped' is "
                    "Tuesday, not an incident."
                ),
                technical=(
                    "OS + platform runtime pulled by all endpoints in "
                    "lockstep (asserted): fetch from Orchestrator, verify "
                    "against attestation-rooted trust, install. "
                    "Interruption-tolerant by design — resume on WAN "
                    "return. No push, no media, no console."
                ),
                expert=(
                    "Lockstep pull-provision: fetch, verify, install; "
                    "resumable. No push path exists."
                ),
            ),
            active_regions=_endpoints() + ["orchestrator", "network"],
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=60,
            elapsed_seconds=600,
            cycle_cost=3,
        ),
        OnboardState(
            step=5,
            phase="blueprint",
            label="The site's blueprint is applied — intent, not steps",
            description=L(
                novice=(
                    "What should this site actually run? Somewhere central, "
                    "an engineer wrote that down once — as a description of "
                    "the end state, not a list of steps: which applications, "
                    "which settings, which rules. That description, called a "
                    "blueprint, is now applied to this site, and the same "
                    "blueprint is applied at every site like it. Writing "
                    "down the destination once beats giving four hundred "
                    "sets of directions — and when the blueprint changes "
                    "next year, every site follows it automatically."
                ),
                plain=(
                    "The site's blueprint applies: a declarative "
                    "description — written once, centrally — of what this "
                    "class of site runs: applications, configuration, "
                    "policies, update windows. Declarative is the "
                    "load-bearing word: the blueprint states the end "
                    "state, the Orchestrator computes the steps, and the "
                    "same blueprint serves every site of this class. "
                    "Change it once and the estate follows."
                ),
                standard=(
                    "The Orchestrator applies this site's blueprint — a "
                    "declarative description, written once by an "
                    "engineer who will never visit, of what a site of "
                    "this class runs: which applications, which "
                    "configuration, which policies, which update "
                    "windows. Declarative is the load-bearing word. The "
                    "blueprint states the destination, not the driving "
                    "directions; the Orchestrator computes whatever "
                    "steps this particular site needs to get there, "
                    "which is the only approach that survives four "
                    "hundred sites in four hundred slightly different "
                    "states. When the blueprint changes next quarter, "
                    "the estate converges on the new destination the "
                    "same way — no site visits, no per-site scripts."
                ),
                technical=(
                    "Blueprint application: declarative site-class "
                    "definition (apps, config, policy, update windows) "
                    "authored once, centrally. Orchestrator reconciles "
                    "per-site state toward the declared end state — "
                    "convergence, not scripted steps. Estate-wide "
                    "changes are blueprint edits."
                ),
                expert=(
                    "Declarative blueprint per site class; Orchestrator "
                    "reconciles. Edits converge the estate."
                ),
            ),
            active_regions=_endpoints() + ["orchestrator", "blueprint"],
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=75,
            elapsed_seconds=660,
        ),
        OnboardState(
            step=6,
            phase="workload",
            label="Workloads start — the site begins doing its job",
            description=L(
                novice=(
                    "The applications arrive and start: the point-of-sale "
                    "system, the camera model checking parts on a line, the "
                    "telemetry collector in a garage — whatever this site "
                    "exists to do. They come from a catalog of packaged "
                    "software, the way apps come from a phone's store, and "
                    "they were chosen by the blueprint, not by anyone "
                    "standing at the machine. From the site's point of "
                    "view, computers arrived in boxes and became a working "
                    "system, and nobody set anything up."
                ),
                plain=(
                    "Workloads deploy from the application catalog — "
                    "Dell-packaged, ISV, and the customer's own — as the "
                    "blueprint dictates: inference at a line, "
                    "point-of-sale at a branch, telemetry ingestion at a "
                    "garage. Deployment is the same pulled, verified "
                    "motion as everything before it. The site is now "
                    "doing the job it was shipped for; local hands "
                    "involved so far: one plug-in."
                ),
                standard=(
                    "The workloads land and start — pulled from the "
                    "application catalog (Dell-packaged applications, "
                    "independent software vendors' offerings, and the "
                    "customer's own containers) exactly as the blueprint "
                    "dictates: a computer-vision inspection model at a "
                    "factory line, point-of-sale at a branch, telemetry "
                    "ingestion at a trackside garage. Deployment is the "
                    "same motion as everything before it — the device "
                    "pulls, verifies against established trust, runs — "
                    "and the same motion will deliver every future "
                    "update, which is how a model gets retrained "
                    "centrally and lands at four hundred sites without "
                    "four hundred visits. The site is now doing the job "
                    "it was shipped to do."
                ),
                technical=(
                    "Catalog workloads (Dell / ISV / customer "
                    "containers) deploy per blueprint: pull, verify, "
                    "run. Update path is identical to install path — "
                    "central model retrain → estate-wide rollout, no "
                    "site visits. Site operational."
                ),
                expert=(
                    "Blueprint-driven catalog deploy: pull/verify/run. "
                    "Updates ride the same path. Site live."
                ),
            ),
            active_regions=_endpoints() + ["orchestrator", "blueprint", "catalog"],
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=90,
            elapsed_seconds=720,
            cycle_cost=2,
        ),
        OnboardState(
            step=7,
            phase="managed",
            label="Managed — policy enforced, telemetry flowing, no one there",
            description=L(
                novice=(
                    "Steady state. The site runs itself: security rules "
                    "are enforced automatically, health data streams back "
                    "to the center, and software updates will arrive the "
                    "same way everything else did — pulled, verified, "
                    "unattended. Read the counters one last time. Four "
                    "machines online. Trust proven and kept. And exactly "
                    "one human action, ever: somebody plugged in two "
                    "cables. That is the entire story, and at four "
                    "hundred sites it is the only story that scales."
                ),
                plain=(
                    "Steady state: Zero Trust policy enforced at the "
                    "edge, telemetry streaming to observability (the "
                    "CloudIQ twin's world), lifecycle — patches, app "
                    "updates, eventually decommissioning — automated "
                    "over the same pulled, verified path. Final "
                    "counters: four online, trust held, operator "
                    "actions one. The person who plugged it in has "
                    "long since gone back to their actual job."
                ),
                standard=(
                    "Steady state, which at the edge means: running "
                    "unattended, forever. Zero Trust policy is enforced "
                    "on every endpoint — least privilege, verified "
                    "workloads, the FortZero twin's argument applied at "
                    "the edge; telemetry streams to the observability "
                    "layer (where the CloudIQ twin picks the story up: "
                    "NativeEdge deploys and enforces, AIOps watches and "
                    "predicts); and the whole lifecycle — patches, "
                    "application updates, certificate rotation, "
                    "eventual decommissioning — rides the same pulled, "
                    "verified path that built the site. Read the "
                    "counters one last time: four endpoints online, "
                    "trust established and never revoked, operator "
                    "actions exactly one. The shop manager plugged in "
                    "two cables and went back to work — and that is "
                    "the only version of this story that survives "
                    "multiplication by four hundred."
                ),
                technical=(
                    "Steady state: Zero Trust enforcement at the "
                    "endpoint, telemetry to AIOps (CloudIQ handoff), "
                    "full lifecycle over the pull path (patch, update, "
                    "rotate, decommission). Finals: online 4, trust "
                    "held, operator_actions 1 — the invariant the "
                    "twin exists for, at its terminal value."
                ),
                expert=(
                    "Unattended steady state: ZT enforced, telemetry "
                    "out, lifecycle on the pull path. online 4, trust "
                    "true, operator_actions 1. QED."
                ),
            ),
            active_regions=(
                _endpoints()
                + ["network", "identity", "orchestrator", "blueprint",
                   "catalog", "policy", "observability"]
            ),
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=100,
            elapsed_seconds=780,
        ),
    ]
