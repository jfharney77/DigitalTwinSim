"""Management scenarios for iDRAC9.

Same shape as the R760 use cases, but a "build" here is mostly a set of
*enabled capabilities* — a license tier plus the interfaces, network mode and
features it unlocks — rather than parts bolted into a chassis. Every config
line's category_id/option_id must resolve against catalog.py (enforced in
tests/test_catalog.py), and each capability's home blocks light up on the
subsystem diagram.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

LIGHTS_OUT_DEPLOY = UseCase(
    id="lights-out-deploy",
    title="Lights-out OS deployment",
    summary=(
        "Install an operating system on a brand-new, headless server in a "
        "datacenter you will never physically visit — from your desk."
    ),
    narrative=[
        (
            "The scenario: a server has just been racked and cabled in a "
            "colo hundreds of miles away. It has no operating system, no "
            "keyboard, no monitor, and no one standing next to it. In the old "
            "world this meant a technician with a crash cart and a USB stick. "
            "With iDRAC it is a task you do from your chair: the management "
            "controller booted the moment the cords went in, so the server is "
            "already reachable on the network before it has ever run a line "
            "of host code."
        ),
        (
            "The flow is entirely out-of-band. You open the HTML5 web console "
            "on iDRAC's dedicated management port, launch Virtual Console to "
            "see the real screen, and use Virtual Media to mount an "
            "installer ISO from your workstation as if it were a USB drive on "
            "the front of the server. You power the host on remotely, watch it "
            "POST, and drive the installer — or hand the whole job to the "
            "Lifecycle Controller, which can deploy a supported OS from its "
            "own driver repository with no external media at all."
        ),
        (
            "None of this needs an agent in the operating system, because "
            "there is no operating system yet — that is the point. The "
            "management plane is separate from the production plane, so it can "
            "build the production plane from nothing. The one prerequisite is "
            "the license: Virtual Console and Virtual Media are Enterprise "
            "features, which is why lights-out shops standardize on Enterprise "
            "or above across the fleet."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="license", option_id="lic-enterprise", qty=1,
            rationale=(
                "Virtual Console and Virtual Media are Enterprise features — "
                "the whole scenario depends on them."
            ),
        ),
        UseCaseItem(
            category_id="network", option_id="net-dedicated", qty=1,
            rationale=(
                "A dedicated management port so the server is reachable "
                "before any host NIC is even configured."
            ),
        ),
        UseCaseItem(
            category_id="presence", option_id="pres-vconsole", qty=1,
            rationale="See the real console — POST, boot menu, installer — remotely.",
        ),
        UseCaseItem(
            category_id="presence", option_id="pres-vmedia", qty=1,
            rationale="Mount the installer ISO to the headless server across the network.",
        ),
        UseCaseItem(
            category_id="lifecycle", option_id="lc-controller", qty=1,
            rationale=(
                "Alternative to media entirely: deploy the OS from the "
                "on-board driver repository."
            ),
        ),
        UseCaseItem(
            category_id="interface", option_id="if-webgui", qty=1,
            rationale="The point-and-click surface a human drives the install from.",
        ),
    ],
    outcomes=[
        Stat(label="Technician trips", value="Zero"),
        Stat(label="Reachable", value="Before the host has an OS"),
        Stat(label="License", value="Enterprise (console + media)"),
        Stat(label="Media", value="Remote ISO or on-board LC repo"),
    ],
)

FLEET_AUTOMATION = UseCase(
    id="fleet-automation",
    title="Zero-touch fleet provisioning",
    summary=(
        "Bring a rack of identical servers to a known-good configuration "
        "automatically, with no one configuring them one by one."
    ),
    narrative=[
        (
            "The scenario: fifty servers arrive for a new cluster. Configuring "
            "each one by hand — BIOS settings, RAID layout, iDRAC network, "
            "boot order — is slow and, worse, inconsistent; the one server "
            "somebody fat-fingered is the one that pages you at 3 a.m. months "
            "later. The goal is to make configuration a versioned artifact, "
            "applied identically and automatically."
        ),
        (
            "iDRAC and the Lifecycle Controller make the fleet self-"
            "configuring. A Server Configuration Profile captures a golden "
            "machine's entire setup — BIOS, iDRAC, RAID, NIC — as one file. "
            "With Zero-Touch Provisioning, each new server on first power-on "
            "reaches a provisioning service, pulls that profile, and applies "
            "it before anyone logs in. Everything is driven over the Redfish "
            "API, so the whole process lives in the same infrastructure-as-"
            "code pipeline as the rest of the estate, and System Lockdown Mode "
            "then freezes the result against drift."
        ),
        (
            "This is where a dedicated management network and a consistent "
            "license tier stop being nice-to-haves. Automatic server "
            "configuration is an Enterprise feature; the dedicated NIC keeps "
            "provisioning traffic off production; and lockdown ensures the "
            "carefully-applied profile is the profile that is still there next "
            "quarter. The payoff is fifty servers that are genuinely identical."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="license", option_id="lic-enterprise", qty=1,
            rationale="Automatic server configuration (incl. ZTP) is an Enterprise feature.",
        ),
        UseCaseItem(
            category_id="interface", option_id="if-redfish", qty=1,
            rationale="Drives the whole flow from the same IaC pipeline as everything else.",
        ),
        UseCaseItem(
            category_id="lifecycle", option_id="lc-scp", qty=1,
            rationale="Captures the golden config as one importable file.",
        ),
        UseCaseItem(
            category_id="lifecycle", option_id="lc-ztp", qty=1,
            rationale="Each server pulls and applies the profile on first power-on, untouched.",
        ),
        UseCaseItem(
            category_id="network", option_id="net-dedicated", qty=1,
            rationale="Keeps provisioning traffic on an isolated management network.",
        ),
        UseCaseItem(
            category_id="security", option_id="sec-lockdown", qty=1,
            rationale="Freezes the applied configuration against later drift.",
        ),
    ],
    outcomes=[
        Stat(label="Per-server touch", value="None after racking"),
        Stat(label="Config", value="One versioned profile, applied to all"),
        Stat(label="Consistency", value="Locked against drift"),
        Stat(label="Driven by", value="Redfish + Lifecycle Controller"),
    ],
)

PREDICTIVE_TELEMETRY = UseCase(
    id="predictive-telemetry",
    title="Predictive telemetry at scale",
    summary=(
        "Stream fine-grained health and performance data off every server so "
        "failures are caught weeks before they cause an outage."
    ),
    narrative=[
        (
            "The scenario: a large fleet where the expensive failures are the "
            "ones nobody saw coming — a fan slowly losing RPM, an inlet "
            "temperature creeping up, a PSU drawing more than its neighbors. "
            "Polling each server occasionally over SNMP catches these late, if "
            "at all. What is needed is a continuous, high-resolution feed of "
            "what every machine is actually doing."
        ),
        (
            "iDRAC Datacenter turns the always-running monitoring engine into "
            "a telemetry source: it streams detailed metric reports — "
            "temperatures, power, fan speeds, performance counters — out to an "
            "external collector over Redfish at configurable rates. Feed that "
            "into an analytics stack and drift becomes visible as a trend line "
            "long before it becomes an alert, so parts get replaced on a "
            "maintenance window instead of at 3 a.m. The advanced power and "
            "thermal controls in the same tier then let you act on what you "
            "see — capping draw during a rack-level crunch, for instance."
        ),
        (
            "Because the management controller is out-of-band, this telemetry "
            "keeps flowing even when the host is unhealthy or wedged — you can "
            "watch a server misbehave and reach it to intervene when an "
            "in-band agent would already be gone. The cost of entry is the "
            "Datacenter license (telemetry streaming is exclusive to it) and "
            "hardening the management plane itself, since it now carries the "
            "keys to the whole fleet's health data."
        ),
    ],
    config=[
        UseCaseItem(
            category_id="license", option_id="lic-datacenter", qty=1,
            rationale="Telemetry streaming and advanced thermal/power are Datacenter-only.",
        ),
        UseCaseItem(
            category_id="lifecycle", option_id="lc-telemetry", qty=1,
            rationale="The high-rate metric feed itself — the point of the build.",
        ),
        UseCaseItem(
            category_id="interface", option_id="if-redfish", qty=1,
            rationale="The transport telemetry reports are pushed over, into the collector.",
        ),
        UseCaseItem(
            category_id="network", option_id="net-dedicated", qty=1,
            rationale="Keeps the metric stream off production and flowing when the host is down.",
        ),
        UseCaseItem(
            category_id="security", option_id="sec-mfa", qty=1,
            rationale="The management plane now holds fleet-wide health data — guard its logins.",
        ),
    ],
    outcomes=[
        Stat(label="Failure warning", value="Weeks, not minutes"),
        Stat(label="Data rate", value="Streamed, configurable"),
        Stat(label="Works when", value="Host is unhealthy or off"),
        Stat(label="License", value="Datacenter (telemetry-exclusive)"),
    ],
)

USE_CASES: list[UseCase] = [
    LIGHTS_OUT_DEPLOY,
    FLEET_AUTOMATION,
    PREDICTIVE_TELEMETRY,
]
