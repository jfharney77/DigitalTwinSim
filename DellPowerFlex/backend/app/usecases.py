"""Use cases: three PowerFlex pools, as backend data.

Each is a build sheet whose category and option ids must resolve against
``catalog.py`` — enforced in ``tests/test_catalog.py``. The narratives are
written for a reader who understands servers but has not run storage that
is made of them.

All three lean on the same property from different angles: with no
controller in the middle, the system's shape is free to change while it is
running. What differs is which consequence is being bought — recovery
speed, elastic scale, or the ability to refresh hardware without a
migration.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="database-consolidation",
        title="Consolidating a database estate that cannot pause",
        summary=(
            "Several hundred production databases onto one pool, where a "
            "hardware failure costs a proportional dip rather than a "
            "failover pause."
        ),
        narrative=[
            "Database teams are not, on the whole, persuaded by peak "
            "throughput figures. What they care about is the tail: the "
            "slowest one percent of operations, and what happens to it "
            "when something breaks. On a controller array, losing a "
            "controller means a failover — paths renegotiated, I/O paused "
            "for a period measured in seconds, and a set of applications "
            "that each handle that pause differently and badly.",
            "The relevant PowerFlex property is that there is nothing to "
            "fail over to, because there was never anything in the middle. "
            "A lost node removes its share of the throughput and nothing "
            "else; clients simply stop addressing one server and keep "
            "addressing the others, because a redundant copy of "
            "everything the dead node held was already sitting on them. "
            "The trace in this twin shows the shape: a dip to roughly "
            "ninety percent, a rebuild running underneath live traffic, "
            "and full protection restored without an administrator being "
            "involved.",
            "Two configuration choices carry most of the risk. Fault sets "
            "must be declared, because scattering copies across nodes only "
            "protects you if the nodes actually fail independently, and a "
            "rack losing power will disabuse you of that assumption at the "
            "worst moment. And the fabric must be sized for rebuild rather "
            "than for steady state, since recovery speed is bounded by how "
            "fast survivors can shuttle fragments between themselves.",
        ],
        config=[
            UseCaseItem(
                category_id="nodes", option_id="pflex-rack", qty=1,
                rationale=(
                    "At this size the network design is the deployment's "
                    "biggest risk; buying it integrated removes the most "
                    "common way a first pool disappoints."
                ),
            ),
            UseCaseItem(
                category_id="topology", option_id="two-layer", qty=1,
                rationale=(
                    "Databases should not compete with the storage path "
                    "for cycles on the same server."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="mesh-mirror", qty=1,
                rationale=(
                    "The fastest possible recovery, bought with half the "
                    "raw capacity — the right trade when the tail latency "
                    "during a rebuild is what people will judge."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="fault-sets", qty=1,
                rationale=(
                    "The most commonly skipped step, and the one whose "
                    "absence is discovered during a rack power event."
                ),
            ),
            UseCaseItem(
                category_id="fabric", option_id="eth-100", qty=1,
                rationale=(
                    "Rebuild speed is a fabric property; sizing for "
                    "steady state alone under-buys it."
                ),
            ),
            UseCaseItem(
                category_id="clients", option_id="sdc", qty=1,
                rationale=(
                    "Direct addressing keeps the gateway hop out of the "
                    "latency budget."
                ),
            ),
            UseCaseItem(
                category_id="integration", option_id="databases", qty=1,
                rationale=(
                    "A proportional dip during hardware loss is the "
                    "property being purchased."
                ),
            ),
            UseCaseItem(
                category_id="services", option_id="snapshots", qty=1,
                rationale=(
                    "Snapshots cheap enough to take before every schema "
                    "change change how willingly teams deploy."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Failover pause", value="None — there is nothing to fail over"),
            Stat(label="Throughput during node loss", value="~90% of steady"),
            Stat(label="Rebuild participants", value="Every surviving node"),
            Stat(label="Protection after rebuild", value="100%, on a smaller cluster"),
        ],
    ),
    UseCase(
        id="elastic-platform",
        title="A container platform whose storage grows a node at a time",
        summary=(
            "Persistent volumes for Kubernetes, where capacity and compute "
            "are bought separately and added whenever they run short."
        ),
        narrative=[
            "Platform teams have an awkward relationship with storage "
            "arrays. An array is bought in a lump, sized against a guess "
            "about three years from now, and expanded in increments that "
            "have more to do with the vendor's shelf sizes than with what "
            "anyone needs. Meanwhile the platform above it grows one node "
            "at a time, continuously, in response to demand nobody "
            "predicted.",
            "A pool made of servers matches that rhythm because the "
            "increment is a server. Need capacity: add a storage node and "
            "let the pool rebalance onto it. Need compute: add an "
            "application node, which costs no drives. There is no shelf "
            "size, no forklift, and — because there is no controller "
            "defining the system's shape — no upper bound imposed by a "
            "component you bought at the start.",
            "The mixed topology is worth taking seriously here rather than "
            "treating as a curiosity. Estates arrive at inconsistency by "
            "evolution: a few hyperconverged nodes bought for a project, a "
            "block of dedicated storage nodes bought later, and a strong "
            "wish not to run them as two systems. An architecture that "
            "tolerates both in one pool turns what would have been a "
            "migration into a configuration.",
        ],
        config=[
            UseCaseItem(
                category_id="nodes", option_id="pflex-appliance", qty=1,
                rationale=(
                    "Validated nodes mean a firmware mismatch stays a "
                    "server problem instead of becoming a storage "
                    "problem."
                ),
            ),
            UseCaseItem(
                category_id="topology", option_id="mixed", qty=1,
                rationale=(
                    "The estate will become inconsistent whether or not "
                    "it was designed to; better that this is supported."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="erasure-coding", qty=1,
                rationale=(
                    "Far less capacity overhead, and 5.0 Ultra keeps the "
                    "many-to-many rebuild rather than trading it away for "
                    "the saving."
                ),
            ),
            UseCaseItem(
                category_id="lifecycle", option_id="rebalance", qty=1,
                rationale=(
                    "Growth is the normal operating mode here, not an "
                    "event that needs a change window."
                ),
            ),
            UseCaseItem(
                category_id="integration", option_id="virt", qty=1,
                rationale=(
                    "Persistent volumes that scale without dragging "
                    "hypervisor licences along."
                ),
            ),
            UseCaseItem(
                category_id="fabric", option_id="eth-25", qty=1,
                rationale=(
                    "Adequate for a general-purpose platform, with "
                    "redundant links mattering more than raw speed."
                ),
            ),
            UseCaseItem(
                category_id="clients", option_id="nvme-tcp", qty=1,
                rationale=(
                    "Some platform nodes are locked down and cannot carry "
                    "a vendor kernel module."
                ),
            ),
            UseCaseItem(
                category_id="services", option_id="reduction", qty=1,
                rationale=(
                    "Included rather than tiered, which removes the usual "
                    "argument about whether encryption is worth paying "
                    "for."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Growth increment", value="One server"),
            Stat(label="Capacity and compute", value="Scaled independently"),
            Stat(label="Expansion outage", value="None"),
            Stat(label="Topology", value="Hyperconverged and two-layer, one pool"),
        ],
    ),
    UseCase(
        id="refresh-without-migration",
        title="Replacing every server in the pool without a migration project",
        summary=(
            "A three-year hardware refresh performed as a background task: "
            "add the new generation, rebalance, retire the old."
        ),
        narrative=[
            "Storage refreshes are among the least popular projects in "
            "infrastructure. The old array and the new array coexist for "
            "months, data is migrated volume by volume, every application "
            "owner has to be persuaded to accept a maintenance window, and "
            "the schedule slips because one team will not. The cost is "
            "rarely the hardware; it is the coordination.",
            "When the storage system is made of interchangeable servers, "
            "the refresh stops being a migration and becomes an expansion "
            "followed by a contraction. Add nodes of the new generation to "
            "the existing pool. Let the software rebalance chunks onto "
            "them — the same mechanism that handles a rebuild, doing the "
            "same many-to-many work. Then tell it to remove the old nodes, "
            "and it drains them the same way. Hosts keep running "
            "throughout and never see a dropped path, because from a "
            "client's point of view nothing happened except the map "
            "changing.",
            "This is the property that is hardest to appreciate from a "
            "specification sheet and easiest to appreciate after living "
            "through the alternative. It is also the clearest illustration "
            "of what removing the controller actually bought: not "
            "primarily speed, but the freedom for the system's shape to "
            "change while it is running.",
        ],
        config=[
            UseCaseItem(
                category_id="nodes", option_id="pflex-software", qty=1,
                rationale=(
                    "If the product is software, the hardware generation "
                    "underneath is allowed to be a detail."
                ),
            ),
            UseCaseItem(
                category_id="lifecycle", option_id="rebalance", qty=1,
                rationale=(
                    "The refresh is add, rebalance, remove — the same "
                    "machinery a rebuild uses."
                ),
            ),
            UseCaseItem(
                category_id="topology", option_id="two-layer", qty=1,
                rationale=(
                    "Storage nodes can be replaced without touching the "
                    "servers running applications."
                ),
            ),
            UseCaseItem(
                category_id="coordinator", option_id="mdm-cluster", qty=1,
                rationale=(
                    "The referee must survive the servers it is refereeing "
                    "being replaced under it."
                ),
            ),
            UseCaseItem(
                category_id="protection", option_id="fault-sets", qty=1,
                rationale=(
                    "During a refresh the failure domains genuinely move; "
                    "the software has to be told."
                ),
            ),
            UseCaseItem(
                category_id="lifecycle", option_id="observability", qty=1,
                rationale=(
                    "A slowly failing drive in one node of hundreds is a "
                    "statistical anomaly, not something anyone spots."
                ),
            ),
            UseCaseItem(
                category_id="services", option_id="replication", qty=1,
                rationale=(
                    "A second pool at another site, so the refresh has "
                    "somewhere to fall back to."
                ),
            ),
            UseCaseItem(
                category_id="integration", option_id="ai-rack", qty=1,
                rationale=(
                    "The block tier of the unified Exascale rack, where "
                    "the same refuse-the-controller instinct shows up in "
                    "file and object too."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Migration project", value="None"),
            Stat(label="Host-visible interruption", value="Not even a dropped path"),
            Stat(label="Mechanism", value="The same rebalance a rebuild uses"),
            Stat(label="Coordination required", value="No application owners"),
        ],
    ),
]
