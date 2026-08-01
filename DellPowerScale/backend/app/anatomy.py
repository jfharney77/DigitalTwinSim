"""Cluster anatomy data: a PowerScale cluster, annotated.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over rack accuracy (project scope
guardrail).

The drawing is organized to make a refusal visible. A band of six
identical nodes runs across the middle, each with its own drives; the
multi-protocol access layer sits above; the back-end interconnect and
management sit below. And between the protocols and the nodes, drawn as
one continuous shape spanning every node, is the namespace — the single
file system. It is deliberately the only region in the map whose extent
crosses all the node boundaries, and ``tests/test_anatomy.py`` pins it
that way: everything else belongs to a node or sits in a band, and the
namespace is the one thing that refuses to be partitioned.

Six nodes are drawn; the trace lights four at first and all six after the
expansion. A real cluster runs from three nodes to 252, and the namespace
is one file system at every size in between.
"""

from __future__ import annotations

from .leveling import L
from .models import ClusterAnatomy, ClusterRegion, SourceLink, Stat

_NODE_DESC = (
    "A PowerScale node: an ordinary-looking box carrying compute, memory, "
    "networking, and drives, running OneFS — the operating system that "
    "joins every node into one cluster presenting one file system. Every "
    "node in the band is identical in role: it holds stripes of every "
    "file, answers clients over every protocol, and takes part in every "
    "repair. None is a controller, none is a head, and none is a spare. "
    "Adding one grows the single namespace and adds performance at the "
    "same time, which is why the cluster's shape can change while it is "
    "running. Nodes five and six are drawn dark at first — the trace "
    "lights them when they join."
)

_MEDIA_DESC = (
    "The drives inside one node — all-flash, hybrid, or high-density "
    "archive disk depending on the node tier. What they are *not* is a "
    "RAID group: protection in OneFS is applied per file, across nodes, "
    "with erasure coding — mathematical parity from which a lost stripe "
    "can be recomputed — so these drives hold fragments of every file in "
    "the cluster rather than whole files of their own. A drive failure "
    "here is repaired by the whole cluster, not by a partner disk."
)

_NODE_X = [2.0, 18.0, 34.0, 50.0, 66.0, 82.0]


def _node(idx: int, x0: float) -> ClusterRegion:
    return ClusterRegion(
        id=f"node-{idx}", kind="node", label=f"Node {idx}",
        x=x0, y=22, w=13, h=16, description=_NODE_DESC,
    )


def _media(idx: int, x0: float) -> ClusterRegion:
    return ClusterRegion(
        id=f"media-{idx}", kind="media", label=f"Drives {idx}",
        x=x0, y=40, w=13, h=6, description=_MEDIA_DESC,
    )


ANATOMY = ClusterAnatomy(
    id="powerscale",
    name="Dell PowerScale — scale-out NAS cluster",
    vendor="Dell Technologies",
    form_factor="Scale-out network-attached storage over an internal fabric",
    generation="PowerScale OneFS — one file system, one volume, one namespace",
    year=2026,
    width=100,
    height=60,
    overview=L(
        novice=(
            "This is a group of storage machines, called nodes, that "
            "together present a single enormous shared folder to the "
            "network. Most storage systems make you divide space up front "
            "into fixed containers called volumes — you guess how big each "
            "one should be, and when a guess turns out wrong, someone has "
            "to move data between containers, which means planned downtime "
            "and a lot of coordination. This system never divides the "
            "space at all. The software on every node, called OneFS, "
            "spreads every file in small pieces across all the machines, "
            "and everyone sees one shared space no matter which machine "
            "they connect to or what kind of computer they use — Linux, "
            "Windows, web tools, and analytics platforms all reach the "
            "same files. When the space starts to fill up, you plug in "
            "another node, and the shared space simply gets bigger while "
            "everyone keeps working. The wide bar in the picture that "
            "stretches across every machine is that shared space. It is "
            "drawn as one unbroken shape on purpose: it is the only thing "
            "here that cannot be split up, and that is the whole idea."
        ),
        plain=(
            "PowerScale is scale-out network-attached storage: a cluster "
            "of nodes, each with its own compute, network, and drives, "
            "presenting one file system to everything that connects. Most "
            "NAS makes you carve capacity into fixed volumes before you "
            "know what you will need, and then pays for the wrong guesses "
            "with migrations and maintenance windows. OneFS, the operating "
            "system every node runs, refuses to carve: every file is "
            "striped across all the nodes with parity-based protection, "
            "and clients on NFS, SMB, S3, or HDFS all see the same single "
            "namespace through any node. When capacity runs short you add "
            "a node; the one file system becomes larger and the cluster "
            "redistributes data onto the new hardware while clients keep "
            "reading. The continuous bar spanning every node in this "
            "diagram is the namespace, and it is deliberately the only "
            "region drawn across all the node boundaries — the one thing "
            "in the picture that refuses to be partitioned."
        ),
        standard=(
            "PowerScale is Dell's scale-out network-attached storage: a "
            "cluster of nodes — each contributing compute, memory, "
            "networking, and drives — joined by OneFS, the operating "
            "system that presents them as one file system, one volume, "
            "one namespace. Conventional NAS partitions capacity into "
            "volumes sized against a guess, then spends its life paying "
            "for the guesses: one container 95% full while another sits "
            "empty, and every correction a migration with a maintenance "
            "window. OneFS declines to partition. Files are striped "
            "across every node with erasure coding, clients reach the "
            "same data over NFS, SMB, S3, and HDFS through any node, and "
            "growth is a node joining the cluster — the single volume "
            "becomes larger and AutoBalance redistributes data onto the "
            "new hardware while clients keep reading. The map makes the "
            "refusal visible: the namespace is the continuous bar "
            "spanning all six nodes, and it is pinned by the tests as the "
            "only region whose extent crosses every node boundary. Its "
            "sibling twin in this repo is DellPowerFlex — that one "
            "removed the controller from block storage; this one removed "
            "the volume from file storage. Six nodes are drawn; the "
            "layout is a stylized mental model."
        ),
        technical=(
            "Scale-out NAS: OneFS joins 3–252 nodes into a single file "
            "system and namespace, striping every file across the cluster "
            "with per-file erasure coding rather than device-level RAID. "
            "Multi-protocol access — NFS, SMB, S3, HDFS — to the same "
            "data through any node; no protocol heads. Expansion is "
            "node-join: capacity and performance scale together, the "
            "namespace grows in place, and AutoBalance restripes onto new "
            "hardware under live load. No volume layer exists, so the "
            "migration and reprovisioning costs of conventional NAS have "
            "no object to attach to. The namespace bar spans every node "
            "in the diagram and is the only region that does — the "
            "geometry states the invariant. Sibling refusal: PowerFlex "
            "deletes the controller, OneFS deletes the volume."
        ),
        expert=(
            "OneFS scale-out NAS, 3–252 nodes: one namespace, per-file "
            "erasure coding, symmetric multi-protocol access (NFS/SMB/S3/"
            "HDFS) via any node. Node-join expansion; AutoBalance "
            "restripes live. No volume layer, hence no migration surface. "
            "Namespace drawn as the sole region spanning all nodes. "
            "PowerFlex deletes the controller; this deletes the volume."
        ),
    ),
    regions=[
        ClusterRegion(
            id="proto-nfs", kind="protocol", label="NFS",
            x=2, y=2, w=22, h=6,
            description=(
                "The Network File System — the file protocol Unix and "
                "Linux clients mount. On PowerScale it is served by every "
                "node at once: a client can mount the namespace through "
                "any node and see the same single file system, and a "
                "cluster-wide address pool spreads client connections "
                "across the nodes automatically. There is no NFS head to "
                "size, upgrade, or fail over — the whole cluster is the "
                "NFS server."
            ),
        ),
        ClusterRegion(
            id="proto-smb", kind="protocol", label="SMB",
            x=26, y=2, w=22, h=6,
            description=(
                "Server Message Block — the Windows file-sharing "
                "protocol. The same files an NFS client sees are shares "
                "to a Windows desktop, with permissions mapped between "
                "the two worlds, and every node serves them. Instruments "
                "and desktops write over SMB, pipelines read the same "
                "bytes over NFS, and nothing is copied in between — "
                "multi-protocol access to one namespace is what makes "
                "mixed estates workable."
            ),
        ),
        ClusterRegion(
            id="proto-s3", kind="protocol", label="S3",
            x=50, y=2, w=22, h=6,
            description=(
                "The S3 object protocol — HTTP-based access in the style "
                "of cloud object storage, where applications read and "
                "write objects in buckets rather than files in folders. "
                "On PowerScale a bucket is a view onto the same "
                "namespace: a file written over SMB can be published as "
                "an object without being copied. For the sharper version "
                "of this trade, see the DellObjectScale spec in this repo "
                "— object storage gave up the directory tree entirely, "
                "where OneFS kept the tree and gave up the volume."
            ),
        ),
        ClusterRegion(
            id="proto-hdfs", kind="protocol", label="HDFS",
            x=76, y=2, w=22, h=6,
            description=(
                "The Hadoop Distributed File System interface, spoken by "
                "analytics and big-data platforms. Instead of copying "
                "data into a dedicated analytics cluster, the compute "
                "farm reads the namespace in place, from every node at "
                "once. It is the same lesson as the other three protocol "
                "blocks: the data does not move to meet the access "
                "method, the access method comes to the data."
            ),
        ),
        ClusterRegion(
            id="namespace", kind="namespace", label="One namespace — /ifs",
            x=2, y=11, w=96, h=7,
            description=(
                "The single file system, traditionally rooted at /ifs, "
                "and the reason this twin exists. It is drawn as one "
                "continuous shape spanning every node because that is "
                "what it is: there are no volumes underneath it, no "
                "containers to size, and no boundaries inside it for data "
                "to be migrated across. Every file is striped across the "
                "cluster with erasure coding; every node serves every "
                "part of it; and when a node joins, this shape simply "
                "gets larger. It is deliberately the only region in the "
                "map that crosses all the node boundaries — everything "
                "else belongs to a node or sits in a band, and the "
                "namespace is the one thing that refuses to be "
                "partitioned."
            ),
        ),
        *[_node(i + 1, x) for i, x in enumerate(_NODE_X)],
        *[_media(i + 1, x) for i, x in enumerate(_NODE_X)],
        ClusterRegion(
            id="interconnect", kind="interconnect", label="Back-end interconnect",
            x=2, y=49, w=70, h=7,
            description=(
                "The private network reserved for traffic between nodes — "
                "historically InfiniBand, now typically Ethernet. Every "
                "stripe written, every parity block computed, and every "
                "rebalance after an expansion crosses this fabric, which "
                "is what lets the cluster behave as one machine: a client "
                "talks to one node, and that node assembles the file from "
                "all of them. Clients never see this network; it is the "
                "cluster's spinal cord, not its face."
            ),
        ),
        ClusterRegion(
            id="mgmt", kind="management", label="Cluster management",
            x=75, y=49, w=23, h=7,
            description=(
                "One cluster, one management surface — adding a node is "
                "minutes of work here, not a provisioning project. This "
                "is also where the background jobs that keep the "
                "namespace healthy are scheduled: AutoBalance spreading "
                "data onto new nodes, per-node-pool tiering policies, "
                "snapshots and replication. Telemetry feeds this repo's "
                "CloudIQ twin, which is where a slowly failing drive in "
                "one node of many actually gets noticed."
            ),
        ),
    ],
    stats=[
        Stat(label="Architecture", value="Scale-out; every node is identical in role"),
        Stat(label="Namespace", value="One file system, at every cluster size"),
        Stat(label="Scale", value="3 to 252 nodes in one cluster"),
        Stat(label="Protocols", value="NFS, SMB, S3, HDFS — all via any node"),
        Stat(label="Protection", value="Per-file erasure coding across nodes"),
        Stat(label="Expansion", value="Add a node; the volume becomes larger"),
        Stat(label="Migrations required to grow", value="Zero"),
        Stat(label="Operating system", value="OneFS on every node"),
    ],
    photo=None,
    sources=[
        SourceLink(
            label="Dell PowerScale — scale-out NAS",
            url="https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/powerscale",
        ),
        SourceLink(
            label="Dell PowerScale OneFS product overview (white paper)",
            url="https://www.delltechnologies.com/asset/en-us/products/storage/industry-market/h8202-wp-powerscale-onefs-product-overview.pdf",
        ),
        SourceLink(
            label="OneFS scalability (Dell Info Hub)",
            url="https://infohub.delltechnologies.com/en-us/l/dell-powerscale-onefs-operating-system/scalability-96/",
        ),
        SourceLink(
            label="OneFS architectural overview (Dell Info Hub)",
            url="https://infohub.delltechnologies.com/en-us/l/high-availability-and-data-protection-with-dell-powerscale-scale-out-nas/onefs-architectural-overview-1/",
        ),
    ],
)
