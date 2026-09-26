"""The traces this twin can play, as data: the bring-up, and the failure
scenario. ``sources`` carry the documents each scenario's behaviour is drawn
from; ``basis`` says in one sentence what is sourced and what is illustrative.
The traces themselves live in the pure engine."""

from __future__ import annotations

from .leveling import L
from .models import ScenarioInfo, SourceLink

DEFAULT_SCENARIO = "bring-up"

SCENARIOS: list[ScenarioInfo] = [
    ScenarioInfo(
        id="bring-up",
        name="Bring-up",
        summary=L(
            novice=(
                "The management computer inside the server starting itself, "
                "from the moment the power cord goes in. The server stays "
                "switched off the whole time."
            ),
            standard=(
                "iDRAC's own firmware bring-up, from AC applied to ready and "
                "watching. The host stays powered off throughout."
            ),
            expert="BMC bring-up from AC to ready; host off throughout.",
        ),
        intro=L(
            novice=(
                "Plug in a Dell PowerEdge server and, before anyone presses "
                "its power button, a small computer inside it starts up by "
                "itself. It is called iDRAC, and its job is to look after the "
                "big server: check its health and let an administrator "
                "control it from far away. A trickle of standby power wakes "
                "iDRAC's chip. The chip checks that its own software has not "
                "been tampered with, starts that software, and then opens "
                "the web page and the other tools administrators use. Only "
                "after that can anyone reach the server to switch it on. "
                "Play the trace and watch each stage light up the block it "
                "runs in."
            ),
            standard=(
                "Plug in a PowerEdge and, seconds before the host can do "
                "anything, a small always-on computer boots inside it: "
                "iDRAC, the management controller. Standby power wakes its "
                "SoC, a Root of Trust verifies its firmware, embedded Linux "
                "comes up, and the management services — web console, "
                "Redfish, Lifecycle Controller, sensor monitoring — come "
                "online. Only then is the server reachable to be powered "
                "on. Play the trace and watch each stage light up the block "
                "it runs in."
            ),
            expert=(
                "BMC cold start on standby power: SoC reset, Root of Trust "
                "verification, embedded Linux, then web console, Redfish, "
                "Lifecycle Controller and monitoring. Host off throughout."
            ),
        ),
        phases=["off", "standby", "reset", "bootldr", "kernel", "services", "ready"],
        hero_label="init progress",
        basis="Order and mechanism follow Dell's iDRAC9 documentation; watts and timings are illustrative.",
    ),
    ScenarioInfo(
        id="firmware-update-rollback",
        name="Firmware rollback",
        summary=L(
            novice=(
                "An update to the management computer's software goes wrong. "
                "The new copy fails its safety check when it starts, so the "
                "management computer goes back to the old copy on its own. "
                "The server keeps running the whole time. What is lost, for "
                "about two minutes, is the ability to manage it."
            ),
            standard=(
                "An iDRAC firmware update is uploaded, signature-verified and "
                "staged to the inactive flash partition. iDRAC restarts, the "
                "new image fails its boot check, and the bootloader rolls "
                "back to the previous partition. The host stays up "
                "throughout: management is lost for a bounded time, the "
                "workload is not."
            ),
            expert=(
                "Signed update staged to the inactive partition; boot check "
                "fails; automatic fallback to the running image in A. Host up throughout; "
                "management outage bounded."
            ),
        ),
        intro=L(
            novice=(
                "An administrator updates the software of iDRAC, the small "
                "management computer inside the server, while the server "
                "itself carries on with its work. iDRAC first checks that "
                "the update really came from Dell. It then writes the new "
                "software into the spare half of its storage chip, not the "
                "half it is running from. iDRAC restarts, the new copy "
                "fails its safety check, and iDRAC goes back to the old "
                "copy by itself. For about two minutes (an example figure) "
                "nobody can manage the server. The server never switches "
                "off. Play the trace and watch which numbers move and which "
                "do not."
            ),
            standard=(
                "An administrator updates iDRAC's firmware while the host "
                "runs its workload. The package is signature-checked and "
                "written to the flash partition iDRAC is not running from. "
                "iDRAC restarts, the new image fails its boot check, and "
                "the bootloader goes back to the old partition by itself. "
                "Management is dark for about two minutes, an illustrative "
                "figure. The host never changes power state. Play the trace "
                "and watch which numbers move and which do not."
            ),
            expert=(
                "Signed update staged to the inactive partition; boot-time "
                "verification rejects it; the bootloader falls back to A. "
                "Management dark for about two minutes (illustrative); host "
                "power state unchanged."
            ),
        ),
        phases=[
            "ready",
            "upload",
            "verify",
            "stage",
            "reboot",
            "bootcheck",
            "rollback",
            "restored",
        ],
        hero_label="management outage",
        basis=(
            "Sourced: signed packages (SHA-256, RSA-2048) and "
            "abort-on-failed-validation, two iDRAC images to ensure a "
            "bootable iDRAC, no server reboot for an iDRAC update, rollback "
            "or reset, and SD card or TFTP recovery. Sourced with a "
            "qualification: RED007 is published for iDRAC7 and iDRAC8, and "
            "the SUP0516, RAC0182, SUP0520 sequence is published for an "
            "iDRAC10 case on 17G servers, so the identifiers are Dell's and "
            "the generation is not this twin's. Inferred: that the switch "
            "to the other image is automatic, which Dell's two-image KB "
            "implies and does not describe. Reported rather than "
            "documented: the fans ramping up while iDRAC is away. "
            "Illustrative: every timing, the version strings, the partition "
            "letters, the cause of the failed boot check, the single boot "
            "attempt, and the RAC0182 reason text. Real failures do not "
            "always recover this cleanly."
        ),
        sources=[
            SourceLink(
                label="Dell iDRAC9 Security Configuration Guide: signed firmware updates, rollback to a prior trusted version",
                url="https://www.dell.com/support/manuals/en-us/idrac9-lifecycle-controller-v5.x-series/idrac9_security_configuration_guide/signed-firmware-updates?guid=guid-fea7bf03-d09a-4492-b782-be09234c037a&lang=en-us",
            ),
            SourceLink(
                label="Dell KB 000120131: iDRAC recovery procedure (two operating-system images, SD card and TFTP recovery)",
                url="https://www.dell.com/support/kbdoc/en-us/000120131/poweredge-idrac-recovery-procedure-with-firmimg-d7",
            ),
            SourceLink(
                label="Dell KB 000213056: rolling back iDRAC9 firmware (no server reboot required)",
                url="https://www.dell.com/support/kbdoc/en-us/000213056/steps-to-roll-back-idrac9-firmware-via-idrac9-gui",
            ),
            SourceLink(
                label="Dell KB 000343194 (iDRAC10 on 17G): a failed iDRAC update in the Lifecycle log (SUP0516, RAC0182, SUP0520), and a case that needed AC power removed",
                url="https://www.dell.com/support/kbdoc/en-us/000343194/customer-may-notice-idrac-update-failure-from-1-20-25-52-to-1-20-50-50-on-17g-servers",
            ),
            SourceLink(
                label="Dell KB 000126703: resetting iDRAC (only the iDRAC reboots; the running operating system is not affected)",
                url="https://www.dell.com/support/kbdoc/en-us/000126703",
            ),
            SourceLink(
                label="Dell KB 000135299 (iDRAC7/iDRAC8): RED007, unable to verify the update package signature",
                url="https://www.dell.com/support/kbdoc/en-us/000135299/idrac7-idrac8-red007-error-when-applying-latest-idrac-firmware-from-out-of-band-interface",
            ),
            SourceLink(
                label="Dell Community: reconnecting to the management port after an iDRAC9 7.00 update",
                url="https://www.dell.com/community/en/conversations/poweredge-hardware-general/idrac9-update-to-ver7000000-problems-reconnecting-to-management-port-after-flash/64c105fcf4ccf8a8decf4e66",
            ),
            SourceLink(
                label="Dell white paper: Cyber Resilient Security in PowerEdge Servers",
                url="https://dl.dell.com/manuals/common/dell-emc-poweredge-cyber-resilient-security.pdf",
            ),
        ],
    ),
]

SCENARIO_BY_ID = {s.id: s for s in SCENARIOS}
