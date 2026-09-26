"""Failure scenarios for the NativeEdge twin: a second pure trace.

Same purity rule as ``engine.py`` (no FastAPI, no IO, no timers, no
randomness; AST-checked in ``tests/test_scenarios.py``). The happy path in
``engine.simulate()`` is untouched; a scenario is a different trace built
from the same state model, extended only additively (``ScenarioState``).

``attestation-fails`` — the trust chain failure. Four devices arrive, four
are plugged in, and one of them cannot prove it is the machine Dell built
for this tenant. The three lessons the trace exists to pin:

* **Nothing is deployed to an unattested device.** ``deployed_to`` never
  contains a quarantined endpoint, and the quarantined endpoint is never lit
  on a provisioning, blueprint or workload step.
* **One bad device never blocks the estate.** The three healthy endpoints
  reach every phase at the same second they do on the happy path.
* **Trust is per device.** ``endpoint_trust`` carries a verdict for each
  endpoint; the failed hardware is never trusted, and only a replacement
  unit that passes its own attestation fills the slot.

What is sourced and what is not: the voucher mismatch and its event text, the
endpoint's serial being listed in the estate *before* it is powered on (the
voucher is uploaded first), the Device Attestation Key in the TPM, the minimal
factory OS, FDO's two-way check, and whole-unit replacement with a new voucher
are Dell's documentation and the FIDO spec (see ``SOURCES``). Dell's KB
documents the voucher event with an Orchestrator-side cause; a single device
failing on its own, the tampered-measurement variant, reading Dell's
whole-unit-replacement procedure (written for a unit that arrives
non-functioning) as the answer to a device that cannot attest, the word
quarantine, the timings, the three-day replacement and the single-step
recovery are illustrative.
"""

from __future__ import annotations

from .engine import ENDPOINTS, simulate
from .leveling import L
from .models import ScenarioInfo, ScenarioState, SourceLink

ATTESTATION_FAILS = "attestation-fails"

# The unit that fails. Which one is arbitrary; that it is one of four
# identical boxes nobody could tell apart on the loading dock is the point.
BAD = "endpoint-e3"

_ALL = [f"endpoint-{e}" for e in ENDPOINTS]
_HEALTHY = [e for e in _ALL if e != BAD]

# Illustrative: a return-and-replace turnaround of three days.
_REPLACEMENT_ARRIVES_S = 3 * 24 * 3600

SOURCES = [
    SourceLink(
        label=(
            "Dell KB 000216857: onboarding fails, 'Public Key of the voucher "
            "is not matching NativeEdge Orchestrator' (event 0x00301006)"
        ),
        url="https://www.dell.com/support/kbdoc/en-us/000216857/",
    ),
    SourceLink(
        label=(
            "Dell NativeEdge Security Configuration Guide: secure supply "
            "chain flow, ownership voucher, minimal factory OS"
        ),
        url=(
            "https://www.dell.com/support/manuals/en-us/native-edge-or-solutions/"
            "nativeedge-security-v1-0-cg/secure-supply-chain-flow-of-nativeedge-"
            "endpoints?guid=guid-cad66296-f660-4299-b8ec-255678700efa&lang=en-us"
        ),
    ),
    SourceLink(
        label=(
            "Dell NativeEdge Service Manual: Device Attestation Key in the "
            "TPM (original device onboarding)"
        ),
        url=(
            "https://www.dell.com/support/manuals/en-us/native-edge-or-solutions/"
            "nativeedge-sm/original-device-onboarding?guid=guid-2ef03dbb-c7e6-"
            "4bf4-ba12-389f69538c51&lang=en-us"
        ),
    ),
    SourceLink(
        label=(
            "Dell NativeEdge Service Manual: whole unit replacement — "
            "written for a unit that arrives non-functioning or fails under "
            "warranty; this trace reads a device that cannot attest as that "
            "case"
        ),
        url=(
            "https://www.dell.com/support/manuals/en-us/native-edge-or-solutions/"
            "nativeedge-sm/whole-unit-replacement?guid=guid-4a253334-c0fb-4a12-"
            "8e79-61aaea50a4da&lang=en-us"
        ),
    ),
    SourceLink(
        label=(
            "Dell NativeEdge Service Manual: replacement and voucher (Dell's "
            "voucher system retires the old Service Tag and associates the "
            "new unit's voucher with the customer account)"
        ),
        url=(
            "https://www.dell.com/support/manuals/en-us/native-edge-or-solutions/"
            "nativeedge-sm/dell-edge-gateway-replacement-and-voucher?guid=guid-"
            "b56ae9a9-6a01-4769-b33f-c2c0742b603a&lang=en-us"
        ),
    ),
    SourceLink(
        label=(
            "FIDO Device Onboard spec v1.1 (TO2): the device verifies the "
            "ownership voucher's signature chain and the owner's proof of "
            "the owner key — the check runs both ways"
        ),
        url=(
            "https://fidoalliance.org/specs/FDO/FIDO-Device-Onboard-PS-v1.1-"
            "20220419/FIDO-Device-Onboard-PS-v1.1-20220419.html"
        ),
    ),
    SourceLink(
        label=(
            "Dell NativeEdge Orchestrator User's Guide: secure device onboard "
            "with FDO — before onboarding, 'the voucher is uploaded, and the "
            "estate lists the endpoint serial number'"
        ),
        url=(
            "https://www.dell.com/support/manuals/en-us/native-edge-or-solutions/"
            "nativeedge-orchestrator-ug/secure-device-onboard-with-fdo?guid=guid-"
            "b41dfbd8-b3b3-46e4-9ccc-5ff29d366545&lang=en-us"
        ),
    ),
    SourceLink(
        label="Dell KB 000227781: MTLS onboarding certificate-chain failures",
        url="https://www.dell.com/support/kbdoc/en-sg/000227781/",
    ),
]

SCENARIOS = [
    ScenarioInfo(
        id="zero-touch",
        title="Zero-touch onboarding",
        summary=(
            "Four devices arrive at one site, all four prove what they are, "
            "and the site is managed after one on-site action."
        ),
        hero_label="operator actions",
        illustrative="Timings are illustrative.",
        intro=L(
            novice=(
                "Every hardware twin in this collection has a person at the "
                "key moment: someone presses a power button or plugs in an "
                "adapter. An edge estate cannot work that way. It is four "
                "hundred sites with no IT staff at any of them. This trace "
                "follows one of those sites as four new devices arrive. Each "
                "device wakes, proves it is the machine Dell built, and asks "
                "the central control system, the Orchestrator, what it should "
                "become. The only thing anyone at the site does is plug the "
                "devices into power and the network. The work people used to "
                "do on site moved to head office and is done once for every "
                "site: loading Dell's digital receipts for the devices and "
                "writing the plan for what a site runs. Play the trace and "
                "watch the operator actions counter reach one and stop."
            ),
            standard=(
                "Every hardware twin in this repo assumes a person at the "
                "moment of truth: someone presses the power button, racks the "
                "machine, plugs in the adapter. An edge estate breaks that "
                "assumption: four hundred sites, no IT staff at any of them. "
                "So NativeEdge inverts the direction of trust. This trace "
                "follows one site receiving four devices. Each device wakes, "
                "proves cryptographically that it is the machine Dell built, "
                "and asks the Orchestrator what it should become: OS, "
                "blueprint, workloads and policy are all pulled, never "
                "pushed. The only on-site human action is the plug-in visit, "
                "power and a network cable for the four devices. The effort "
                "moved to the centre, where it is done once for the estate: "
                "an administrator loads the devices' ownership vouchers into "
                "the Orchestrator and authors the blueprint. Play the trace "
                "and watch the operator-actions counter reach one, and stop."
            ),
            expert=(
                "One site, four devices, no site IT. Device-initiated "
                "onboarding under FDO (FIDO Device Onboard): attest, get "
                "claimed, then pull OS, blueprint, workloads and policy. "
                "On-site human acts: one, the plug-in. Voucher loading and "
                "blueprint authoring are central, done once, uncounted."
            ),
        ),
    ),
    ScenarioInfo(
        id=ATTESTATION_FAILS,
        title="One device fails attestation",
        summary=(
            "One of the four cannot prove it is the machine Dell built for "
            "this tenant. It is quarantined and receives nothing; the other "
            "three onboard on schedule; the failed unit is returned and "
            "replaced."
        ),
        hero_label="quarantined",
        intro=L(
            novice=(
                "This is the same delivery to the same site, with one "
                "difference: one of the four devices cannot prove it is the "
                "machine Dell built for this customer. The trace starts "
                "exactly like the other one, because nobody can tell which "
                "box is bad until the check answers. Watch three things. The "
                "failed device, drawn in red, is sent nothing. The other "
                "three are set up at the same times as before. And the "
                "people count is kept in two rows: operator actions still "
                "stops at one, the plug-in visit, and swapping the bad "
                "device later is a second on-site action, counted under its "
                "own name as a recovery action. By the end a person at the "
                "site has acted twice."
            ),
            standard=(
                "The same site and the same four devices, except that one of "
                "them cannot prove it is the machine Dell built for this "
                "tenant. The first three steps are the happy path's, word "
                "for word, because nobody can tell which box is bad before "
                "attestation answers. Three things to watch: the failed "
                "device is quarantined and receives nothing; the other three "
                "onboard on the happy path's clock; and on-site human acts "
                "are kept in two rows. Operator actions still stops at one, "
                "the plug-in visit. Swapping the failed unit is a second "
                "on-site act and is counted under its own name, recovery "
                "actions, so the site ends on one plus one. Central work "
                "(vouchers, the blueprint, the support case) is described "
                "in the steps and not counted."
            ),
            expert=(
                "Same site, one of four devices fails attestation (voucher "
                "or measured-boot mismatch). Steps up to the verdict match "
                "the happy path. The failed unit gets nothing; the other "
                "three keep the happy path's clock. On-site acts are split: "
                "one plug-in (operator actions) plus one unit swap (recovery "
                "actions). Central work is described, not counted."
            ),
        ),
        sources=SOURCES,
        illustrative=(
            "Sourced: the voucher mismatch event and its text, the serial "
            "listed in the estate before the device is powered on, the "
            "attestation key in the TPM, the minimal factory OS, FDO's "
            "two-way check, whole-unit replacement with a new voucher. "
            "Dell's KB documents that event with an Orchestrator-side cause "
            "and a central fix; a single device failing on its own, the "
            "tampered-firmware variant, reading Dell's replacement procedure "
            "(written for a unit that arrives non-functioning) as the answer "
            "to a device that cannot attest, the word quarantine, every "
            "timing, the three-day replacement, and recovery compressed into "
            "one step are illustrative."
        ),
    ),
]


def scenario_info(scenario_id: str) -> ScenarioInfo | None:
    for s in SCENARIOS:
        if s.id == scenario_id:
            return s
    return None


def _trust(*trusted: str) -> dict[str, bool]:
    return {e: e in trusted for e in _ALL}


def simulate_attestation_fails() -> list[ScenarioState]:
    """Four crates, one bad device, as pure data.

    The first three steps are the happy path's, verbatim: until the verdict
    lands nobody — on site or at the Orchestrator — can tell which box is
    the bad one, and the trace should not pretend otherwise.
    """
    shared = [
        ScenarioState(**s.model_dump(), endpoint_trust=_trust())
        for s in simulate()[:3]
    ]
    return shared + [
        ScenarioState(
            step=3,
            phase="quarantine",
            label="One device fails the check and is quarantined",
            description=L(
                novice=(
                    "Four verdicts come back and one of them is no. Every "
                    "NativeEdge device leaves the factory with a secret key "
                    "locked inside a security chip (the TPM, or Trusted "
                    "Platform Module), and Dell sends the customer a matching "
                    "digital receipt for each device, called an ownership "
                    "voucher. The third box cannot make the two line up: "
                    "either its startup measurements show firmware that Dell "
                    "did not sign, or its voucher belongs to a different "
                    "customer. So it gets nothing. Its serial number was "
                    "already on the central list of this site's devices, "
                    "because the receipts are loaded before the boxes ship, "
                    "and it simply never changes to onboarded: it sits on the "
                    "list, stuck, while the administrator far away sees one "
                    "event on the monitoring page saying the receipt does not "
                    "match. The box is drawn in red here. "
                    "Nobody on site has noticed anything, and nothing on the "
                    "company network has been exposed to it. The warning "
                    "message is a real one from Dell's support pages; one "
                    "box failing by itself is this model's example."
                ),
                standard=(
                    "Four verdicts land and one is a refusal. Each endpoint "
                    "is built with a Device Attestation Key in its TPM "
                    "(Trusted Platform Module), and Dell issues the customer "
                    "an ownership voucher tied to that one device, which the "
                    "administrator loads into the Orchestrator before the "
                    "device is powered on. The third device cannot reconcile the two: "
                    "its measured boot reports firmware Dell did not sign, or "
                    "its voucher was issued to a different tenant. The "
                    "twin calls what follows quarantine; Dell's documents "
                    "describe the behaviour without the word. What the "
                    "administrator sees is small, and it is not an absence: "
                    "the device's serial is listed in the estate before it is "
                    "powered on, because its voucher was uploaded first, and "
                    "it simply never becomes onboarded. It holds that state "
                    "while monitoring shows one event, in Dell's words "
                    "'Public Key of the voucher is not matching NativeEdge "
                    "Orchestrator'. What protects the estate is what the "
                    "device is still running: a minimal factory OS that can "
                    "do onboarding and nothing else, holding no site secrets. "
                    "The check also runs the other way: under FDO (FIDO "
                    "Device Onboard, the standard NativeEdge onboards with) "
                    "a device refuses an owner its voucher does not name, so "
                    "a stolen crate cannot be claimed by someone else. The "
                    "event and its text are Dell's; one device failing on "
                    "its own is this twin's example."
                ),
                expert=(
                    "Verdicts: three pass, Device 3 fails (voucher/owner "
                    "key mismatch, event 0x00301006, or measured boot off "
                    "Dell's signed references). Serial listed in the estate "
                    "(the voucher was uploaded first) and never transitions "
                    "to onboarded; still on the minimal factory OS; no "
                    "secrets delivered. "
                    "FDO (FIDO Device Onboard) authenticates both ways: the "
                    "device also rejects an owner its voucher does not "
                    "chain to. The verdict is per device, not per site."
                ),
            ),
            active_regions=_ALL + ["identity", "network"],
            endpoints_online=0,
            operator_actions=1,
            trust_established=True,
            progress_percent=25,
            elapsed_seconds=330,
            cycle_cost=2,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
        ),
        ScenarioState(
            step=4,
            phase="onboard",
            label="The Orchestrator claims the three that passed",
            description=L(
                novice=(
                    "The other three boxes carry on as if nothing happened, "
                    "because for them nothing did. The central control "
                    "system claims them and the online counter goes from "
                    "zero to three. It will not reach four today. The point "
                    "to notice is the clock: the three good machines are "
                    "claimed at exactly the moment they would have been if "
                    "the fourth had been fine. One bad device does not hold "
                    "up the site."
                ),
                standard=(
                    "The Orchestrator claims the three devices that proved "
                    "themselves, and endpoints-online moves from zero to "
                    "three. The quarantined unit is not counted and is not "
                    "waited for: each device's claim depends on its own "
                    "proof and on nothing else, so the healthy three are "
                    "claimed at the same second they are on the happy path. "
                    "A site's devices are still claimed as a set, and the "
                    "set is whichever devices earned trust. Operator "
                    "actions: one."
                ),
                expert=(
                    "Claim is per device, gated on that device's verdict. "
                    "online 0 → 3, same timestamp as the happy path. The "
                    "failed unit is excluded, not awaited."
                ),
            ),
            active_regions=_HEALTHY + ["identity", "orchestrator", "network"],
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=35,
            elapsed_seconds=360,
            cycle_cost=2,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
        ),
        ScenarioState(
            step=5,
            phase="provision",
            label="Software lands on three devices and not on the fourth",
            description=L(
                novice=(
                    "Operating systems and platform software download to the "
                    "three trusted machines. The red box stays dark. It is "
                    "plugged into the same network and sits on the same "
                    "shelf, and it still receives no software at all, because "
                    "downloads are only offered to devices that passed the "
                    "check. Being in the building earns a device nothing."
                ),
                standard=(
                    "The OS and the platform runtime land on the three "
                    "trusted endpoints, pulled and signature-checked as "
                    "before. The quarantined device shares their switch "
                    "port, their subnet and their shelf, and receives "
                    "nothing, because delivery is gated on the device's own "
                    "attestation and not on where it is plugged in. This is "
                    "the FortZero twin's argument at the scale of one box: "
                    "network location authorizes nothing."
                ),
                expert=(
                    "Pull-provision to the three trusted endpoints; "
                    "Device 3 is offered nothing. Delivery is gated on the "
                    "device's own attestation verdict, never on network "
                    "position."
                ),
            ),
            active_regions=_HEALTHY + ["orchestrator", "network"],
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=50,
            elapsed_seconds=600,
            cycle_cost=3,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
            deployed_to=list(_HEALTHY),
        ),
        ScenarioState(
            step=6,
            phase="blueprint",
            label="The blueprint applies to the devices that exist",
            description=L(
                novice=(
                    "The site's blueprint, the written description of what "
                    "this kind of site should run, is applied to the three "
                    "working machines. The blueprint still says four. The "
                    "control system notes the gap and works with what it "
                    "has, which is what a system that manages four hundred "
                    "sites has to be able to do."
                ),
                standard=(
                    "The Orchestrator applies the site blueprint to the "
                    "three endpoints it holds. The blueprint is declarative, "
                    "so a missing device is a difference between declared "
                    "and actual state that the Orchestrator keeps open, not "
                    "an error that stops the run. No blueprint content is "
                    "sent to the quarantined unit, which would include "
                    "configuration and credentials."
                ),
                expert=(
                    "Blueprint reconciles on three endpoints; the fourth is "
                    "open drift, not a failed run. No config or credentials "
                    "reach the quarantined unit."
                ),
            ),
            active_regions=_HEALTHY + ["orchestrator", "blueprint"],
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=60,
            elapsed_seconds=660,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
            deployed_to=list(_HEALTHY),
        ),
        ScenarioState(
            step=7,
            phase="workload",
            label="Workloads start on three devices",
            description=L(
                novice=(
                    "The applications arrive and start on three machines: "
                    "the tills, the camera model, whatever the site is for. "
                    "The site is doing its job with three quarters of its "
                    "computers, on the same day the crates arrived."
                ),
                standard=(
                    "Catalog workloads deploy to the three trusted "
                    "endpoints and start. The site is in service at three "
                    "quarters of its planned capacity, on the happy path's "
                    "schedule. Whether three is enough is a sizing decision "
                    "made in the blueprint long before today; the platform's "
                    "part is that the fourth device's failure did not decide "
                    "it for the other three."
                ),
                expert=(
                    "Workloads live on three endpoints, on schedule. "
                    "Capacity at 3/4 is a blueprint sizing question; "
                    "availability was not coupled to the failed unit."
                ),
            ),
            active_regions=_HEALTHY + ["orchestrator", "blueprint", "catalog"],
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=70,
            elapsed_seconds=720,
            cycle_cost=2,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
            deployed_to=list(_HEALTHY),
        ),
        ScenarioState(
            step=8,
            phase="managed",
            label="Three managed, one quarantined, and an open event",
            description=L(
                novice=(
                    "Three machines are managed and reporting. One is still "
                    "red. The shop manager has done one thing all day, which "
                    "was plugging in the devices, and does not know anything "
                    "went wrong. The administrator does know, from the event on "
                    "the monitoring page. If the mismatch had been caused by "
                    "the control system's own key changing, Dell's fix is a "
                    "script run centrally and a restart of the device. Here "
                    "the device itself is wrong, so it has to go back."
                ),
                standard=(
                    "Steady state for three endpoints: policy enforced, "
                    "telemetry flowing. The fourth remains quarantined with "
                    "its event open. Dell's KB documents one cause for this "
                    "event, and it is not the device: if the "
                    "Orchestrator's owner key changed after its identifier "
                    "was generated, the fix is central: run Dell's "
                    "identifier-rotation script on the Orchestrator, reboot "
                    "the endpoint, onboard again, and nobody visits the "
                    "site. That is the first thing to rule out. This trace "
                    "takes the other branch, which is illustrative: the "
                    "device is the problem, no central action can make it "
                    "trustworthy, and it is returned. Operator actions "
                    "still reads one; the next step adds a second on-site "
                    "act under its own name, recovery actions."
                ),
                expert=(
                    "3 managed, 1 quarantined. Orchestrator-side key "
                    "mismatch is fixed centrally (rotate identifier, reboot "
                    "endpoint); a device-side failure is not fixable "
                    "remotely by design. Return the unit."
                ),
            ),
            active_regions=(
                _HEALTHY
                + ["network", "identity", "orchestrator", "blueprint",
                   "catalog", "policy", "observability"]
            ),
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=75,
            elapsed_seconds=780,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[BAD],
            deployed_to=list(_HEALTHY),
        ),
        ScenarioState(
            step=9,
            phase="replace",
            label="The failed unit goes back and a replacement is plugged in",
            description=L(
                novice=(
                    "Three days later (an illustrative figure) a new box "
                    "arrives. The shop manager unplugs the red one, puts it "
                    "in the return packaging, and plugs the new one into the "
                    "same two cables. That is a second action by a person at "
                    "the site, and it is counted in its own row: recovery "
                    "actions goes to one, while operator actions stays at "
                    "one because it only counts the first plug-in visit. Add "
                    "the two rows for the total, which is now two. The "
                    "failure cost one swap by someone untrained. It did not "
                    "cost a technician's visit. The new box starts from "
                    "nothing, like any other: it has its own key and its own "
                    "voucher, and it is not trusted yet."
                ),
                standard=(
                    "The administrator has opened a case with Dell, which is "
                    "central work and not a site action. Dell's service "
                    "manual documents whole-unit replacement for a device "
                    "that arrives non-functioning or fails under warranty; "
                    "treating a device that cannot prove what it is as that "
                    "case is this twin's reading. It arrives three days on in "
                    "this trace (illustrative). Someone on site unplugs the "
                    "quarantined device, boxes it for return, and connects "
                    "the replacement to the same power and network. "
                    "Recovery actions moves to one; operator actions stays "
                    "at one, since it counts only the first plug-in visit. "
                    "The two rows together are honest about what a trust "
                    "failure costs: zero-touch onboarding needed one "
                    "on-site act for the whole site, and this device "
                    "brought a second. The replacement inherits "
                    "nothing from the slot it fills. It carries its own "
                    "attestation key, Dell's voucher system retires the old "
                    "Service Tag and associates the new unit's voucher with "
                    "the customer account, that voucher reaches the "
                    "Orchestrator centrally as for any device, and its trust "
                    "reads false."
                ),
                expert=(
                    "Support case (central), then whole-unit replacement: "
                    "a second on-site act, a swap by untrained staff, "
                    "tallied as a recovery action. New Device Attestation "
                    "Key (DAK), new voucher associated by Dell and loaded "
                    "centrally; not yet trusted. Nothing transfers from "
                    "the failed unit."
                ),
            ),
            active_regions=[BAD, "network"],
            endpoints_online=3,
            operator_actions=1,
            trust_established=True,
            progress_percent=80,
            elapsed_seconds=_REPLACEMENT_ARRIVES_S,
            endpoint_trust=_trust(*_HEALTHY),
            failed_endpoints=[],
            deployed_to=list(_HEALTHY),
            recovery_actions=1,
        ),
        ScenarioState(
            step=10,
            phase="recovered",
            label="The replacement attests and the site is whole",
            description=L(
                novice=(
                    "The new box goes through the same check the others "
                    "did, passes it, and only then is claimed, given its "
                    "software, its blueprint and its applications. This "
                    "screen shows that as one step to keep the story short; "
                    "the real sequence is the same one you watched the other "
                    "three go through. Four online. Two actions by people "
                    "at the site in total, one in each row, both of them "
                    "plugging in cables. At no point "
                    "did a machine that failed the check receive anything."
                ),
                standard=(
                    "The replacement runs the full sequence: attestation "
                    "first, then claim, provisioning, blueprint and "
                    "workloads, compressed into one step here. The blueprint "
                    "that had been holding an open difference converges, and "
                    "endpoints-online reads four. Final counters: operator "
                    "actions one, recovery actions one, and no step on which "
                    "an unattested device held any payload. The three "
                    "healthy endpoints never paused."
                ),
                expert=(
                    "Replacement: attest, claim, converge (one step, "
                    "compressed). Four online; on-site acts one plug-in "
                    "plus one swap; no payload ever reached a device "
                    "without its own passing verdict."
                ),
            ),
            active_regions=(
                _ALL
                + ["network", "identity", "orchestrator", "blueprint",
                   "catalog", "policy", "observability"]
            ),
            endpoints_online=4,
            operator_actions=1,
            trust_established=True,
            progress_percent=100,
            elapsed_seconds=_REPLACEMENT_ARRIVES_S + 780,
            cycle_cost=3,
            endpoint_trust=_trust(*_ALL),
            failed_endpoints=[],
            deployed_to=list(_ALL),
            recovery_actions=1,
        ),
    ]


def simulate_scenario(scenario_id: str) -> list[ScenarioState] | None:
    """The trace for a failure scenario id, or None when the id is unknown
    or names the happy path (which ``engine.simulate()`` owns)."""
    if scenario_id == ATTESTATION_FAILS:
        return simulate_attestation_fails()
    return None
