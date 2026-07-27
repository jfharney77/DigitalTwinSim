"""Site-map anatomy data: production, air gap, and Cyber Recovery vault.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

The view is a left→right data-path map, the way the CloudIQ twin drew its
telemetry pipeline: the production estate (workloads, backup server, and
the production Data Domain) on the left; the operational air gap in the
middle; and the Cyber Recovery vault — a twin Data Domain, CyberSense
analytics, and the clean-room recovery host — on the right. The two Data
Domain appliances are drawn as identical twins on purpose: the vault's
power is not different hardware but different *reachability*.
"""

from __future__ import annotations

from .leveling import L
from .models import Photo, SiteAnatomy, SiteRegion, SourceLink, Stat

# The only shipped visual is a self-contained schematic drawn for this
# project — not a Dell product image — with an honest credit line.
SITE_ILLO = Photo(
    url="/powerprotect-vault.svg",
    caption=(
        "The PowerProtect Cyber Recovery architecture, schematically: the "
        "production estate backs up to a Data Domain; a vault-controlled "
        "air gap opens briefly to replicate; and the vault's twin Data "
        "Domain holds an immutable copy that CyberSense scans and the "
        "clean room restores from."
    ),
    credit="Schematic illustration by this project — not a Dell product image",
)

_DD_PROD_DESC = (
    "The production PowerProtect Data Domain — the backup target the "
    "estate streams to every night. Data Domain's defining trick is "
    "variable-length deduplication: it slices incoming streams into "
    "segments, recognizes ones it has stored before regardless of shifting "
    "offsets, and keeps each unique segment once. Dell quotes up to 65:1 "
    "reduction on the all-flash appliance, which is why weeks of restore "
    "points fit in a few rack units — and why replication to the vault "
    "moves minutes of uniques, not days of raw data. The Data Invulnerability "
    "Architecture (end-to-end checksums, verify-after-write) guards what "
    "lands here."
)

_DD_VAULT_DESC = (
    "The vault Data Domain — deliberately the same appliance as "
    "production's, drawn the same size on purpose. What makes it a vault "
    "is not hardware but reachability and policy: it sits behind an air "
    "gap that only the vault itself opens, and every replicated copy is "
    "sealed under Retention Lock Compliance — WORM (write-once-read-many) "
    "enforcement in the filesystem that no administrator or stolen "
    "credential can override until the retention clock expires. The "
    "attacker's problem is not breaking in; it is that from production, "
    "this machine effectively does not exist."
)


ANATOMY = SiteAnatomy(
    id="powerprotect",
    name="PowerProtect Data Domain + Cyber Recovery vault",
    vendor="Dell Technologies",
    form_factor="Production site + air-gapped vault (two Data Domain appliances)",
    generation="PowerProtect Data Domain All-Flash · Cyber Recovery · CyberSense",
    year=2025,
    width=100,
    height=56,
    overview=L(
        novice=(
            "This follows what happens to a backup copy of a company's data, "
            "including the part where criminals try to destroy it. Backups are "
            "first shrunk dramatically by noticing that most of the data is "
            "identical to data already stored — only the genuinely new pieces "
            "are kept, which is why the stored figure ends up ten or more times "
            "smaller than the original. Then a copy is sent to a vault: a "
            "separate, isolated environment with no route in from the ordinary "
            "network. The connection between them is opened only briefly, and "
            "only from the vault side, which is the crucial detail. Watch the "
            "attack step: the production systems are ruined, and the vault is "
            "not touched, because at that moment there is simply no path to it."
        ),
        plain=(
            "PowerProtect Data Domain with Cyber Recovery and CyberSense, drawn "
            "as a data path across two sites: production estate on the left, an "
            "air gap in the middle, the vault on the right. The trace is the "
            "lifecycle of the data itself — backed up, deduplicated, replicated "
            "through a briefly-open gap, locked immutable, scanned for "
            "integrity, attacked, and recovered. Two things are asserted: the "
            "gap is open during replication and recovery and at no other time, "
            "both opened from the vault side; and at the moment of attack no "
            "vault component and no gap is active while production's blast "
            "radius is."
        ),
        standard=(
            "PowerProtect Data Domain is Dell's purpose-built backup appliance "
            "— the deduplication machine behind most large backup estates — "
            "and PowerProtect Cyber Recovery is the architecture that turns a "
            "second one into a ransomware vault. The map reads left to right, "
            "the way the data flows: the estate backs up to the production "
            "appliance, where deduplication collapses hundreds of logical "
            "terabytes into a few physical ones; on the vault's own schedule, "
            "an operational air gap opens briefly and replication pulls the "
            "copy across; then the gap closes, Retention Lock makes the copy "
            "immutable, and CyberSense's machine-learning analytics decide "
            "which restore points are provably clean. The attack the "
            "architecture assumes is the modern one — ransomware that hunts "
            "backups first with stolen admin credentials — and its answer is "
            "a copy that has no network path, no writable surface, and a "
            "rehearsed way back. The 2025 all-flash appliance is what makes "
            "the way back fast."
        ),
        technical=(
            "Data Domain plus Cyber Recovery and CyberSense as a two-site data "
            "path: production, operational air gap, vault. Phase order backup → "
            "dedupe → replicate → airgap → scan → attack → recover → restored. "
            "Asserted: `storedTb <= logicalTb` always with ratio ≥10:1 from "
            "dedupe onward; the gap region is active in exactly {replicate, "
            "recover}; at the attack step no vault region and no gap is active; "
            "the vaulted copy is sealed strictly before the attack; CyberSense "
            "scan holds max dwell. Both appliances are drawn identical in size "
            "— the vault's power is reachability, not hardware."
        ),
        expert=(
            "Two-site protection path with an operational air gap. Gap active "
            "in exactly {replicate, recover}, both vault-initiated. At attack: "
            "no vault region, no gap, production blast radius only; vaulted "
            "copy sealed strictly prior. Dedupe ratio ≥10:1 from dedupe onward. "
            "CyberSense scan holds max dwell. Appliances drawn identical — "
            "reachability is the differentiator, not hardware."
        ),
    ),
    regions=[
        SiteRegion(
            id="workload-vm", kind="workload", label="VMs & apps",
            x=1, y=6, w=16, h=14,
            description=(
                "The virtualized estate — VMware or Hyper-V virtual "
                "machines, application servers, file shares. In backup "
                "terms these are 'clients': PPDM orchestrates their "
                "image-level and agent-based backups on policy. In attack "
                "terms they are the blast radius — the systems ransomware "
                "encrypts, and the systems the vault exists to bring back."
            ),
        ),
        SiteRegion(
            id="workload-db", kind="workload", label="Databases",
            x=1, y=24, w=16, h=14,
            description=(
                "The transactional core — Oracle, SQL Server, SAP HANA, "
                "and their kin. Databases back up through application-"
                "aware agents so the copy is consistent and point-in-time "
                "recoverable, and they are where recovery-time promises "
                "get hard: the business measures an outage in transactions "
                "lost per minute. CyberSense pays them special attention, "
                "since page-level database corruption is a signature "
                "ransomware behavior."
            ),
        ),
        SiteRegion(
            id="backup-server", kind="backup", label="PPDM",
            x=1, y=42, w=16, h=12,
            description=(
                "PowerProtect Data Manager (PPDM), Dell's backup "
                "orchestration software: policies, schedules, catalogs, "
                "and the console the backup team lives in. It is also — "
                "uncomfortably — a prime target: modern ransomware "
                "playbooks delete the backup catalog and expire the "
                "backups with stolen admin credentials before detonating. "
                "That is precisely why the vault does not trust anything "
                "on this side of the gap, this server included."
            ),
        ),
        SiteRegion(
            id="dd-prod", kind="appliance", label="Data Domain — production",
            x=20, y=6, w=22, h=48,
            description=_DD_PROD_DESC,
        ),
        SiteRegion(
            id="gap", kind="gap", label="Air gap",
            x=45, y=21, w=10, h=16,
            description=(
                "The operational air gap — the architecture's hinge. It is "
                "not a cable someone unplugs; it is an automated control "
                "the *vault* owns: on the vault's schedule the link comes "
                "up, replication syncs the uniques, and the link is "
                "severed again — minutes of exposure per day, initiated "
                "only from inside. Production holds no credential that can "
                "open it, so an attacker who owns every production system "
                "still faces a door with the handle on the other side."
            ),
        ),
        SiteRegion(
            id="dd-vault", kind="appliance", label="Data Domain — vault",
            x=58, y=6, w=22, h=48,
            description=_DD_VAULT_DESC,
        ),
        SiteRegion(
            id="cybersense", kind="analytics", label="CyberSense",
            x=83, y=6, w=16, h=20,
            description=(
                "CyberSense — machine-learning integrity analytics that "
                "run inside the vault, on the vaulted copies. It indexes "
                "content (not just metadata) and evaluates 200+ signals — "
                "entropy shifts that betray encryption, file-type "
                "corruption, mass renames, database page damage — against "
                "the history of every previous scan. Its output is the "
                "vault's real product: a verdict per restore point, so a "
                "3 a.m. recovery starts from 'this copy is clean' instead "
                "of restoring the malware along with the data."
            ),
        ),
        SiteRegion(
            id="recovery-host", kind="recovery", label="Clean room",
            x=83, y=29, w=16, h=13,
            description=(
                "The clean-room recovery host: isolated compute inside the "
                "vault where restores are rehearsed. During an incident "
                "the team mounts candidate copies here — off any network "
                "the attacker ever touched — validates applications "
                "actually start, and only then pushes data back toward "
                "production. Rehearsal is the unglamorous half of cyber "
                "resilience: a vault you have never restored from is a "
                "hypothesis, not a plan."
            ),
        ),
        SiteRegion(
            id="mgmt", kind="mgmt", label="DDMC / consoles",
            x=83, y=45, w=16, h=9,
            description=(
                "The management planes: Data Domain Management Center "
                "(DDMC) for fleets of appliances, the Cyber Recovery "
                "console inside the vault, and PPDM's own UI outside it. "
                "Deliberately split — vault management lives in the vault "
                "and is reachable only from it, because a shared console "
                "would be a bridge across the gap, and bridges are what "
                "attackers commute on."
            ),
        ),
    ],
    stats=[
        Stat(label="Appliance", value="PowerProtect Data Domain (All-Flash, 2025)"),
        Stat(label="Data reduction", value="Up to 65:1 dedupe + compression"),
        Stat(label="Restore speed", value="Up to 4× faster (all-flash vs disk)"),
        Stat(label="Immutability", value="Retention Lock Compliance (WORM)"),
        Stat(label="Air gap", value="Vault-controlled, closed by default"),
        Stat(label="Analytics", value="CyberSense — 200+ ML integrity signals"),
        Stat(label="Entry point", value="DD3410 · 8–32 TBu grow-in-place (Q1 2026)"),
    ],
    photo=SITE_ILLO,
    sources=[
        SourceLink(
            label="Dell PowerProtect Data Domain",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/powerprotect-data-domain",
        ),
        SourceLink(
            label="Dell announcement — all-flash Data Domain & cyber resilience (Sept 2025)",
            url="https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2025~09~dell-technologies-data-center-breakthroughs-power-smarter-faster-and-more-secure-private-clouds.htm",
        ),
        SourceLink(
            label="Dell PowerProtect Cyber Recovery",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/cyber-recovery-solution",
        ),
        SourceLink(
            label="Dell Data Domain family data sheet",
            url="https://www.delltechnologies.com/asset/en-us/products/cyber-resilience/technical-support/dell-powerprotect-data-domain-family-datasheet.pdf",
        ),
    ],
)
