"""Lifecycle map data: Dell's circular design, drawn as a loop.

Like the other twins, the layout is *data*, not code: regions placed in a
normalized coordinate space the frontend renders as SVG. Geometry is
stylized — favor a correct mental model over supply-chain accuracy
(project scope guardrail).

The drawing is organized to make a shape visible, and the shape is a
cycle. Every other map in this repo is a box, a rack, or a left-to-right
path; this one has no end. Materials feed manufacture at the top-left,
devices flow right into deployment, the service loop keeps them there,
and recovery at the bottom forks three ways: the inner return (refurbish,
back up to deployment — the short loop, and the better one), the outer
return (reclaim, back across to materials — the long loop), and the leak
(loss, bottom-left, with no outgoing edge, because that is what a leak
is). ``flows_to`` carries the directed edges; ``tests/test_anatomy.py``
walks them and pins the loop closed — recovery must reach both materials
and deployment, and only ``loss`` may be a terminus.

The loss region is not decoration. A lifecycle map that shows only the
virtuous paths is marketing; this one draws the leak at full size and the
trace measures it.
"""

from __future__ import annotations

from .leveling import L
from .models import LifecycleMap, LifecycleRegion, SourceLink, Stat

ANATOMY = LifecycleMap(
    id="circular-design",
    name="Dell circular design — the material loop",
    vendor="Dell Technologies",
    form_factor="A product lifecycle drawn as a closed loop with a measured leak",
    generation="Circular design + Asset Recovery Services",
    year=2026,
    width=100,
    height=70,
    overview=L(
        novice=(
            "This picture is different from every other map in this "
            "collection: it is a circle, not a machine. It follows the "
            "materials inside a batch of laptops — the metal, the "
            "plastic, the battery chemicals — through their whole life. "
            "Raw material (about a third of it already recycled from "
            "older products) goes into the factory, becomes laptops, and "
            "the laptops go out to people who use them. The loop on the "
            "right is repair: fixing a battery or a keyboard keeps a "
            "laptop in use for years longer, and that matters more than "
            "any recycling, because building a new laptop is by far the "
            "most wasteful step — avoiding a rebuild saves more than "
            "recovering one ever can. When the laptops are finally taken "
            "back, they are sorted three ways: the good ones are cleaned "
            "up and used again (the short arrow back), the broken ones "
            "are shredded so their metals can go into new products (the "
            "long arrow back to the start), and a small amount — drawn "
            "honestly in the bottom corner — is simply lost, as dust and "
            "scrap nobody can recover. That lost box has no arrow "
            "leaving it. It is the only dead end in the picture, and "
            "how small it is tells you how well the whole circle works."
        ),
        plain=(
            "A product lifecycle drawn as a loop instead of a line. "
            "Materials — roughly a third of them already recovered from "
            "earlier products — feed manufacture; manufacture feeds "
            "deployment; the service loop on the right keeps devices in "
            "use through repairs, which is the largest lever in the "
            "whole diagram, because manufacture is where most of a "
            "device's lifetime energy and emissions are spent and every "
            "repair defers repeating it. At take-back, recovery forks "
            "three ways: refurbished devices return to deployment (the "
            "short loop, preferred), reclaimed materials return to the "
            "materials pool (the long loop), and a measured remainder "
            "goes to loss — the one region with no exit, drawn "
            "deliberately, because a lifecycle map showing only the "
            "virtuous paths would be marketing. The trace keeps the "
            "books: reused plus reclaimed plus lost equals the mass "
            "that went in, exactly."
        ),
        standard=(
            "Dell's circular design, drawn as the loop it claims to be: "
            "materials (about a third recovered content on the first "
            "pass — recycled cobalt, copper, steel, and plastics) feed "
            "manufacture, manufacture feeds deployment, and the service "
            "loop returns repaired devices to use — the largest lever "
            "in the arithmetic, since manufacture dominates lifetime "
            "footprint and each repair defers an entire manufacturing "
            "cycle. Recovery forks three ways: refurbish rejoins "
            "deployment at the inner radius (reuse is strictly better "
            "than recycling), reclaim rejoins materials at the outer "
            "radius, and loss — the only region with no outgoing edge — "
            "takes the fraction that does not come back. The geometry "
            "is pinned by the tests: following the flow arrows from "
            "recovery must reach both materials and deployment, and "
            "only loss may be a terminus. This twin's sibling is "
            "DellIR7000 — its heat balance applied to matter: from "
            "recovery onward, reused + reclaimed + lost equals the "
            "cohort's mass exactly, and the nonzero loss is the honest "
            "measure of how circular the design actually is. The "
            "layout is a stylized mental model."
        ),
        technical=(
            "Material-flow graph for a device cohort: materials → "
            "manufacture → deployment, service loop for repair-driven "
            "life extension (the dominant term — embodied carbon "
            "concentrates in manufacture), recovery forking to "
            "refurbish (inner return, to deployment), reclaim (outer "
            "return, to materials), and loss (no outgoing edge — the "
            "only permitted terminus). Conservation invariant from "
            "recovery onward: reused + reclaimed + lost == input mass, "
            "no tolerance — the IR7000 heat balance applied to matter. "
            "Recycled input share is nonzero at step one and strictly "
            "higher on the second pass; the loss fraction, not the "
            "recycling rate, is the figure of merit."
        ),
        expert=(
            "Cohort mass-flow loop: materials→manufacture→deployment; "
            "service loop defers refresh (dominant lever); recovery "
            "forks refurbish→deployment, reclaim→materials, loss "
            "(sole terminus, no egress). Invariant: "
            "reused+reclaimed+lost == mass, exact, from recovery on. "
            "Recycled input >0 at t0, strictly higher on pass two. "
            "Figure of merit: the loss fraction."
        ),
    ),
    regions=[
        LifecycleRegion(
            id="materials", kind="materials", label="Materials pool",
            x=4, y=26, w=16, h=12,
            flows_to=["manufacture"],
            description=(
                "Where every cycle starts and where the outer return "
                "delivers: aluminium, steel, copper, cobalt, lithium, "
                "and plastics, part virgin and part recovered. Dell "
                "reports more than 95 million pounds of recycled and "
                "renewable material flowing into products in a year — a "
                "real number worth stating precisely: recycled content "
                "is easiest in steel and plastics, where recovery "
                "chains are decades old, and hardest in the rare "
                "elements that matter most. Recycled cobalt exists in "
                "the pool because battery packs came back through the "
                "reclaim path; it is the difficult, expensive fraction, "
                "and it is the one the loop is really being judged on."
            ),
        ),
        LifecycleRegion(
            id="manufacture", kind="manufacture", label="Manufacture",
            x=26, y=14, w=18, h=12,
            flows_to=["deployment"],
            description=(
                "Fabrication and assembly — and the expensive step, "
                "which the trace marks with the longest dwell in the "
                "loop. Most of a device's lifetime energy, water, and "
                "emissions are committed here, before it computes "
                "anything; the term for that is embodied carbon. This "
                "region is why the service loop matters more than the "
                "recycling paths: a repair that keeps a device in use "
                "defers repeating this step entirely, while even "
                "perfect reclamation only feeds it cheaper inputs. "
                "Design decisions made here — screws instead of glue, "
                "a battery that lifts out, simplified cabling — decide "
                "what the recovery fork can do seven years later."
            ),
        ),
        LifecycleRegion(
            id="packaging", kind="packaging", label="Packaging",
            x=26, y=2, w=16, h=9,
            flows_to=["manufacture", "deployment"],
            description=(
                "The solved corner: about 97% of Dell packaging comes "
                "from recycled or renewable material — cardboard, "
                "moulded fibre, ocean-bound plastics. It feeds both "
                "manufacture and the shipment out to deployment, and it "
                "deserves its win stated at honest scale: packaging is "
                "grams against a device's kilograms, and it is also the "
                "easiest material class on Earth to recycle. Celebrate "
                "it, and keep reading — the hard problems are all "
                "inside the box, in the battery chemistry and the "
                "board-level metals."
            ),
        ),
        LifecycleRegion(
            id="deployment", kind="deployment", label="Deployment",
            x=58, y=14, w=18, h=12,
            flows_to=["service", "recovery"],
            description=(
                "Devices in users' hands, doing the work they were "
                "built for — the phase every other twin in this repo "
                "treats as the destination. The client devices whose "
                "afterlife this map traces are this repo's "
                "DellProMaxPlus and DellAlienware twins; both of their "
                "traces end with the machine running, and this map is "
                "what their final states are the middle of. Two edges "
                "leave here: down into the service loop (repair, and "
                "back), and — eventually, for every device ever built — "
                "into recovery. There is no edge labelled 'forever'."
            ),
        ),
        LifecycleRegion(
            id="service", kind="service", label="Service & repair",
            x=80, y=30, w=16, h=12,
            flows_to=["deployment", "recovery"],
            description=(
                "The repair loop, and the largest lever in the diagram. "
                "Customer-replaceable batteries, spare parts kept "
                "available, repair tutorials and an AR (augmented "
                "reality) repair assistant — none of it sentimental: a "
                "300-gram battery swap defers replacing a two-kilogram "
                "device, which defers another pass through manufacture, "
                "the step that dominates the footprint. Service-life "
                "extension beats recycling in the arithmetic every "
                "time, and it is also the path that competes hardest "
                "with the commercial incentive to sell new units — a "
                "tension worth naming rather than smoothing over. "
                "Devices that can no longer be economically repaired "
                "exit downward, to recovery."
            ),
        ),
        LifecycleRegion(
            id="recovery", kind="recovery", label="Asset recovery",
            x=58, y=48, w=18, h=12,
            flows_to=["refurbish", "reclaim", "loss"],
            description=(
                "Take-back: collection, inventory, and certified data "
                "sanitization — a wipe certificate per drive, which is "
                "the feature that makes enterprises hand hardware back "
                "at all instead of shelving it in a store-room as a "
                "data-breach precaution. Then triage, and the fork that "
                "defines the whole map: refurbish for what can live "
                "again (assessed first, deliberately), reclaim for what "
                "can only be material, and loss for what neither path "
                "can hold. Three edges leave this box, and the trace's "
                "conservation invariant opens here: from this point on, "
                "every kilogram is on exactly one of them."
            ),
        ),
        LifecycleRegion(
            id="refurbish", kind="refurbish", label="Refurbish",
            x=48, y=30, w=14, h=10,
            flows_to=["deployment"],
            description=(
                "The inner return: devices retested, re-batteried, "
                "regraded, and sold or redeployed whole. Drawn at the "
                "shorter radius on purpose — reuse and recycling are "
                "not the same thing, and reuse is strictly better, "
                "because a refurbished device defers an entire "
                "manufacturing cycle while shredded material only "
                "discounts one. A device broken down for materials "
                "that could have been refurbished is a loss even "
                "though the mass balances, and the trace is tested to "
                "attempt this path before the reclaim path. In this "
                "cohort it carries the majority of the mass: 6,200 kg "
                "of the ten tonnes goes back to work."
            ),
        ),
        LifecycleRegion(
            id="reclaim", kind="reclaim", label="Reclaim",
            x=26, y=48, w=18, h=12,
            flows_to=["materials"],
            description=(
                "The outer return: shredding, magnetic and eddy-current "
                "separation, precious-metal recovery from boards, and "
                "hydrometallurgy — chemical leaching — to pull cobalt "
                "and lithium back out of battery packs. It ends where "
                "the map began, at the materials pool, which is what "
                "makes the loop a loop. Honest yields vary wildly by "
                "material: steel and aluminium come back at high "
                "purity almost indefinitely, plastics downgrade a "
                "little each pass, and the rare elements are recovered "
                "at real cost in energy and chemistry. Reclamation is "
                "the loop's safety net, not its engine — the engine is "
                "the service loop above."
            ),
        ),
        LifecycleRegion(
            id="loss", kind="loss", label="Loss",
            x=4, y=52, w=14, h=10,
            flows_to=[],
            description=(
                "The leak, drawn at full size and given no exit — the "
                "only region in this map with no outgoing edge, because "
                "that is what a leak is. Shredder fines too small to "
                "sort, mixed-plastic fractions no process wants, cobalt "
                "left dissolved in slag, and everything in the cohort "
                "that never came back at all. In this trace it is 450 "
                "kg of 10,000 — 4.5% — and the number is the point: a "
                "lifecycle map that omits this box is marketing, and a "
                "vendor claiming zero here is not describing a supply "
                "chain that exists. The loss fraction, not the "
                "recycling rate, is the honest measure of how circular "
                "the design actually is. The DellIR7000 twin meters "
                "its heat for exactly the same reason."
            ),
        ),
    ],
    stats=[
        Stat(label="Shape", value="A loop with two returns and one measured leak"),
        Stat(label="Recycled & renewable input", value="95M+ lbs into products in a year (Dell)"),
        Stat(label="Packaging", value="~97% recycled or renewable material"),
        Stat(label="Largest lever", value="Service-life extension, not recycling"),
        Stat(label="Preferred return", value="Refurbish — reuse beats reclamation"),
        Stat(label="This cohort's leak", value="450 kg of 10,000 (4.5%) — stated, not hidden"),
        Stat(label="Conservation", value="Reused + reclaimed + lost = mass in, exactly"),
        Stat(label="Second-pass input", value="46% recovered vs 34% on the first pass"),
    ],
    photo=None,
    sources=[
        SourceLink(
            label="Dell — circular economy",
            url="https://www.dell.com/en-us/lp/dt/circular-economy",
        ),
        SourceLink(
            label="Dell blog — circular economy in action: leading the fight against e-waste",
            url="https://www.dell.com/en-us/blog/circular-economy-in-action-leading-the-fight-against-e-waste/",
        ),
        SourceLink(
            label="Dell blog — from vision to reality: circular design & AI PCs",
            url="https://www.dell.com/en-us/blog/from-vision-to-reality-circular-design-ai-pcs/",
        ),
        SourceLink(
            label="Dell — sustainable devices",
            url="https://www.dell.com/en-us/lp/dt/sustainable-devices",
        ),
        SourceLink(
            label="Dell blog — repair, reuse, recycle: the circular economy in action",
            url="https://www.dell.com/en-in/blog/repair-reuse-recycle-the-circular-economy-in-action/",
        ),
    ],
)
