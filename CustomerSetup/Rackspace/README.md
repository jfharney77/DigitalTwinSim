# Rackspace Technology — hosted private cloud

Open `setup.html` in a browser for the drawing.

The publicly reported facts: Rackspace runs its managed private-cloud services on VMware
Cloud Foundation over Dell VxRail, and publicly endorsed pairing that HCI base with
external PowerStore arrays when Dell announced VxRail dynamic nodes (June 2021) — Eric
Miller, Rackspace's VP of private cloud: "It's the perfect blend of resources, allowing us
to take advantage of HCI's automation, hybrid cloud's agility and enterprise storage's
performance and efficiency."

The setup is drawn as the argument it embodies: fused HCI nodes where coupling helps,
compute-only dynamic nodes + external storage where it doesn't — the exact debate the
VxRail and PrivateCloud twins stage against each other.

Twins referenced by the drawing (frontend ports — start each with its `scripts/start_all.sh`):

| Block | Twin | Port |
|---|---|---|
| VxRail cluster running VCF | `DellVxRail/` | 5179 |
| External PowerStore array | `DellPowerStore/` | 5175 |
| What one node is (inferred) | `DellPowerEdgeR760/` | 5174 |
| The disaggregation it points at (inferred) | `DellPrivateCloud/` | 5198 |

Sources:
- https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2021~06~20210602-dell-technologies-reimagines-dell-emc-vxrail-to-offer-greater-performance-and-storage-flexibility.htm
- https://www.rackspace.com/newsroom/rackspace-technology-makes-significant-investment-extending-its-vmware-multicloud
- https://www.dell.com/en-us/blog/scalable-transformation-with-vmware-cloud-foundation-5-0-on-vxrail/
