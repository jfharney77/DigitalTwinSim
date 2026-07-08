"""The capabilities-and-options menu for iDRAC9.

Like anatomy.py, the catalog is data, not code: each ``CatalogCategory``
maps to the subsystem blocks it lives in (``region_ids`` from anatomy.py) and
lists the orderable/configurable options, described for a technically skilled
reader who is new to Dell systems management. Contents follow Dell's iDRAC9
documentation; option lists are representative, not exhaustive.

Unlike a server's build sheet, most of these are unlocked by *license*, not
bolted in as hardware — the SoC and flash are the same across a fleet; a
license key turns capabilities on. The license tier is therefore the first
category, and use cases lean on it.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="license",
        name="License tier",
        blurb=(
            "iDRAC ships with a Basic or Express license and can be upgraded "
            "to Enterprise or Datacenter with a key bound to the server's "
            "Service Tag. The tier gates which features unlock in the same "
            "firmware — the hardware does not change."
        ),
        limits="One active tier; Enterprise/Datacenter are perpetual or 30-day trial",
        region_ids=["flash", "soc"],
        options=[
            CatalogOption(
                id="lic-basic",
                name="iDRAC Basic",
                summary="Entry management on value PowerEdge lines.",
                details=(
                    "The baseline on some value servers: sensor monitoring, "
                    "the health tree, power on/off/reset, and basic access to "
                    "the interfaces. No Virtual Console, no Virtual Media. "
                    "Enough to see the server is alive and cycle its power, "
                    "not enough to run it headless."
                ),
            ),
            CatalogOption(
                id="lic-express",
                name="iDRAC Express",
                summary="The default on most PowerEdge servers.",
                details=(
                    "Standard on the mainstream lineup. Adds fuller "
                    "monitoring, logging, and RACADM/Redfish automation to the "
                    "Basic set, and a single-user Virtual Console/Virtual "
                    "Media session on some generations. Still short of the "
                    "multi-user remote presence and out-of-band performance "
                    "monitoring that define Enterprise."
                ),
            ),
            CatalogOption(
                id="lic-enterprise",
                name="iDRAC Enterprise",
                summary="Full lights-out: console, media, OOB monitoring.",
                details=(
                    "The tier most datacenters standardize on. Unlocks "
                    "multi-user Virtual Console and Virtual Media, out-of-band "
                    "performance monitoring, automatic server configuration, "
                    "and richer alerting — everything needed to deploy, "
                    "operate and recover a server with no one in the room."
                ),
            ),
            CatalogOption(
                id="lic-datacenter",
                name="iDRAC Datacenter",
                summary="Enterprise plus telemetry streaming and advanced thermal/power.",
                details=(
                    "The top tier: everything in Enterprise plus server data "
                    "telemetry streaming (high-rate metric reports pushed to "
                    "an external collector), advanced granular power and "
                    "thermal controls and insight, and extra automation aimed "
                    "at large fleets and high-end configurations. This is the "
                    "tier for predictive monitoring at scale."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="network",
        name="Management network",
        blurb=(
            "How iDRAC reaches the network. A dedicated port keeps management "
            "traffic physically separate from production; shared LOM borrows a "
            "host NIC over NC-SI to save a cable and a switch port."
        ),
        limits="Dedicated NIC or one shared LOM port; NC-SI 1.2",
        region_ids=["nic", "sb-ncsi"],
        options=[
            CatalogOption(
                id="net-dedicated",
                name="Dedicated 1GbE NIC",
                summary="Isolated management port — the secure default.",
                details=(
                    "iDRAC's own RJ-45, carrying only management traffic and "
                    "reachable even if every host NIC is down or "
                    "reconfigured. Put it on an isolated management VLAN and "
                    "the control plane is fully separated from production — the "
                    "recommended posture for anything security-sensitive."
                ),
            ),
            CatalogOption(
                id="net-shared-lom",
                name="Shared LOM (NC-SI)",
                summary="Borrow a host LAN-on-Motherboard port.",
                details=(
                    "Over NC-SI (Network Controller Sideband Interface, 1.2 on "
                    "iDRAC9) management shares one of the host's LOM ports "
                    "instead of using the dedicated NIC. It saves a cable and "
                    "a switch port, at the cost of coupling management to a "
                    "production link — a reconfigured or saturated host port "
                    "can take iDRAC with it."
                ),
            ),
            CatalogOption(
                id="net-shared-failover",
                name="Shared LOM with failover",
                summary="Shared LOM that rolls to another port on link loss.",
                details=(
                    "A shared-LOM mode that fails management traffic over to "
                    "another LOM port if the active one loses link — more "
                    "resilient than a single shared port, still without the "
                    "hardware isolation of the dedicated NIC. A middle ground "
                    "for builds that cannot spare a dedicated management "
                    "cable."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="interface",
        name="Interfaces & APIs",
        blurb=(
            "The control surfaces the SoC serves. Modern automation lives on "
            "Redfish and RACADM; the web GUI is for humans; IPMI and SNMP "
            "remain for older tooling."
        ),
        limits="All served by the embedded controller; available at every tier",
        region_ids=["soc"],
        options=[
            CatalogOption(
                id="if-webgui",
                name="HTML5 web console",
                summary="The point-and-click interface for one server.",
                details=(
                    "A browser-based GUI served directly by iDRAC: health, "
                    "logs, power control, configuration, firmware update, and "
                    "the launch point for Virtual Console. No client software "
                    "or Java/Flash plugin on iDRAC9 — the console is HTML5."
                ),
            ),
            CatalogOption(
                id="if-redfish",
                name="Redfish REST API",
                summary="The modern, schema-driven automation standard.",
                details=(
                    "A DMTF-standard RESTful API over HTTPS with JSON payloads "
                    "and a formal schema, designed to manage servers at scale "
                    "across vendors. The preferred surface for infrastructure-"
                    "as-code: everything the GUI does is scriptable here, and "
                    "it is how tools like Ansible and Terraform drive iDRAC."
                ),
            ),
            CatalogOption(
                id="if-racadm",
                name="RACADM CLI",
                summary="Dell's scripting command line, local or over SSH.",
                details=(
                    "Dell's remote/local command line for iDRAC. Run it over "
                    "SSH to the controller, locally from the host OS, or as "
                    "firmware RACADM — it predates Redfish and remains the "
                    "quickest path for one-off config and for scripts written "
                    "before the Redfish era."
                ),
            ),
            CatalogOption(
                id="if-ipmi-snmp",
                name="IPMI 2.0 & SNMP",
                summary="Legacy interfaces for existing monitoring stacks.",
                details=(
                    "IPMI 2.0 (including Serial-over-LAN) and SNMP get/traps "
                    "for compatibility with older management and monitoring "
                    "tools. Broadly supported but coarse and historically "
                    "weaker on security than Redfish — kept for interop, not "
                    "recommended as the primary surface on new builds."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="presence",
        name="Remote presence",
        blurb=(
            "Being at the server without being at the server: seeing its "
            "console, mounting media to it, and reaching it from the front "
            "panel or a phone."
        ),
        limits="Virtual Console/Media require Enterprise or higher",
        region_ids=["kvm", "vmedia", "direct"],
        options=[
            CatalogOption(
                id="pres-vconsole",
                name="Virtual Console (KVM)",
                summary="See and drive the real console remotely.",
                details=(
                    "Remote keyboard, video and mouse redirection: the host's "
                    "actual screen — BIOS setup, boot menu, a kernel panic — "
                    "relayed over the network in a browser. The difference "
                    "between rebooting blind and watching what the server "
                    "does. Licensed (Enterprise+)."
                ),
            ),
            CatalogOption(
                id="pres-vmedia",
                name="Virtual Media",
                summary="Mount an ISO to a server anywhere.",
                details=(
                    "Presents a remote ISO or drive to the host as a USB "
                    "CD/DVD or disk. With Virtual Console it turns a headless "
                    "server on another continent into one you can install an "
                    "OS on from your desk. Licensed (Enterprise+)."
                ),
            ),
            CatalogOption(
                id="pres-direct",
                name="iDRAC Direct",
                summary="Front micro-USB laptop access, no network.",
                details=(
                    "A micro-USB port on the server's front: connect a laptop "
                    "and reach the full iDRAC interface over USB with no "
                    "network configured. The rescue path when management "
                    "networking is broken or not yet set up."
                ),
            ),
            CatalogOption(
                id="pres-quicksync",
                name="Quick Sync 2",
                summary="Bluetooth/Wi-Fi management from a phone at the rack.",
                details=(
                    "A bezel module that pairs over Bluetooth (and Wi-Fi) with "
                    "the OpenManage Mobile app, so a technician standing at the "
                    "rack can read inventory and health and push basic config "
                    "from a phone — useful for at-the-rack work without a "
                    "crash cart."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="lifecycle",
        name="Lifecycle & automation",
        blurb=(
            "The embedded engine that deploys, updates and configures the "
            "server without external media — and the automation built on top "
            "of it for whole fleets."
        ),
        limits="Auto config & telemetry need Enterprise/Datacenter",
        region_ids=["flash", "monitor"],
        options=[
            CatalogOption(
                id="lc-controller",
                name="Lifecycle Controller",
                summary="On-board deploy, update, configure, diagnose (F10).",
                details=(
                    "The embedded engine in flash — reached with F10 at boot "
                    "or through Redfish/RACADM — that deploys operating "
                    "systems, applies firmware, configures hardware and runs "
                    "diagnostics, using its own driver repository and hardware "
                    "inventory. It works on a bare server with no OS installed."
                ),
            ),
            CatalogOption(
                id="lc-scp",
                name="Server Configuration Profiles",
                summary="Export/import a whole server config as one file.",
                details=(
                    "A Server Configuration Profile (SCP) captures BIOS, "
                    "iDRAC, RAID and NIC settings as a single XML/JSON "
                    "document. Export from a golden server, import to a "
                    "hundred others — configuration as a versionable "
                    "artifact rather than a checklist."
                ),
            ),
            CatalogOption(
                id="lc-ztp",
                name="Zero-Touch Provisioning",
                summary="Servers configure themselves on first power-on.",
                details=(
                    "On first AC, iDRAC reaches out to a provisioning server "
                    "and pulls a Server Configuration Profile automatically — "
                    "so a rack of new servers configures and deploys with no "
                    "technician touching each one. Requires automatic server "
                    "configuration (Enterprise+)."
                ),
            ),
            CatalogOption(
                id="lc-telemetry",
                name="Telemetry streaming",
                summary="High-rate metrics pushed to a collector.",
                details=(
                    "iDRAC streams detailed sensor and performance metric "
                    "reports out to an external collector (over Redfish) at "
                    "configurable rates — the raw material for predictive "
                    "analytics that catch a failing part or a thermal drift "
                    "weeks early. A Datacenter-tier feature."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="security",
        name="Security & integrity",
        blurb=(
            "Keeping the management plane — the most privileged access a "
            "server has — trustworthy: verified firmware, locked "
            "configuration, and strong authentication."
        ),
        limits="Lockdown & advanced features need Enterprise/Datacenter",
        region_ids=["rot", "soc"],
        options=[
            CatalogOption(
                id="sec-rot",
                name="Silicon Root of Trust",
                summary="Cryptographic firmware verification from power-on.",
                details=(
                    "A hardware-anchored chain that verifies iDRAC and BIOS "
                    "firmware signatures against keys fused into silicon "
                    "before that code is allowed to run, so tampering is "
                    "caught at boot. The foundation the other security "
                    "features build on."
                ),
            ),
            CatalogOption(
                id="sec-lockdown",
                name="System Lockdown Mode",
                summary="Freeze configuration and firmware against changes.",
                details=(
                    "A single switch that blocks configuration and firmware "
                    "changes across iDRAC and BIOS — accidental or malicious — "
                    "until an administrator explicitly lifts it. Prevents "
                    "drift and unauthorized updates on production fleets. "
                    "Licensed (Enterprise+)."
                ),
            ),
            CatalogOption(
                id="sec-scv",
                name="Secured Component Verification",
                summary="Prove the hardware matches what shipped.",
                details=(
                    "A cryptographic inventory certificate generated at the "
                    "factory that iDRAC checks against the components actually "
                    "present — supply-chain assurance that no part was swapped "
                    "between the factory and the rack."
                ),
            ),
            CatalogOption(
                id="sec-mfa",
                name="Multi-factor authentication",
                summary="MFA and directory integration for iDRAC logins.",
                details=(
                    "Two-factor authentication (including RSA SecurID on "
                    "recent firmware) and directory services (Active "
                    "Directory/LDAP) for iDRAC access, so the management "
                    "controller is not guarded by a single shared password. "
                    "Advanced options are gated by license."
                ),
            ),
        ],
    ),
]
