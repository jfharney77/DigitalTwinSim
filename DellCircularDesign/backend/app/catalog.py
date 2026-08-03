"""Catalog data: the circular-design toolkit, as categories and options.

Not a bill of materials — the subject is a set of practices, so the
catalog lists them the way the CloudIQ twin lists capabilities. Each
category maps onto the lifecycle map via ``region_ids``, and each
``limits`` line carries the honest constraint rather than a spec-sheet
boast: recycled content is easiest where it matters least, refurbishment
competes with the incentive to sell new units, and the largest lever in
the whole loop is keeping devices in service longer — not recycling them.
"""

from __future__ import annotations

from .models import CatalogCategory, CatalogOption

CATALOG: list[CatalogCategory] = [
    CatalogCategory(
        id="material-inputs",
        name="Material inputs",
        blurb=(
            "What goes into the pool: recovered metals and plastics "
            "alongside virgin material, plus bio-based alternatives."
        ),
        limits=(
            "Easiest in steel and plastics; hardest in the rare elements "
            "that matter most. 34% recycled input is not 34% of the cobalt."
        ),
        region_ids=["materials"],
        options=[
            CatalogOption(
                id="recycled-metals",
                name="Recycled cobalt, copper, steel & aluminium",
                summary=(
                    "Closed-loop metals recovered from returned hardware "
                    "and fed back into new products."
                ),
                details=(
                    "Closed-loop means the material comes back from the "
                    "same industry that used it: chassis aluminium "
                    "smelted from recovered chassis, recycled cobalt "
                    "from take-back battery packs going into new cells. "
                    "The metals differ enormously in difficulty. Steel "
                    "and aluminium recycle nearly indefinitely at high "
                    "purity through infrastructure a century old; cobalt "
                    "requires hydrometallurgy — chemical leaching of "
                    "shredded battery material — and comes back at real "
                    "cost in energy and reagents. Dell reports more than "
                    "95 million pounds of recycled and renewable "
                    "material flowing into products in a year; the "
                    "number is real, and most of its mass is the easy "
                    "fraction."
                ),
            ),
            CatalogOption(
                id="recycled-plastics",
                name="Post-consumer & reclaimed plastics",
                summary=(
                    "Recycled plastics, including reclaimed and "
                    "ocean-bound streams, in enclosures and components."
                ),
                details=(
                    "Post-consumer recycled plastic — material that has "
                    "already been a product once — displaces virgin "
                    "polymer in bezels, fan housings, and enclosure "
                    "parts. The honest caveat is that plastics "
                    "downgrade: each melt shortens the polymer chains, "
                    "so recycled resin tends to move down-market rather "
                    "than around in a true circle. That makes plastic "
                    "recycling a ramp with a few turns, not a loop — "
                    "useful, and not the same claim as closed-loop "
                    "aluminium."
                ),
            ),
            CatalogOption(
                id="bio-based",
                name="Bio-based & renewable alternatives",
                summary=(
                    "Renewable inputs — bio-based rubber, tree-based "
                    "fibres, reclaimed carbon fiber — where chemistry allows."
                ),
                details=(
                    "Some fractions can be swapped from fossil to "
                    "renewable feedstock outright: bio-based rubber in "
                    "keyboard feet, tree-based fibre composites, "
                    "reclaimed carbon fiber from aerospace scrap in "
                    "lids. These substitutions are genuinely good and "
                    "genuinely small — grams per device — and they do "
                    "not touch the battery or the board, where the "
                    "material problems that decide the loop's fate "
                    "actually live."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="packaging",
        name="Packaging",
        blurb=(
            "The solved corner: about 97% of packaging from recycled or "
            "renewable material."
        ),
        limits=(
            "Grams against the device's kilograms. Recycled cardboard "
            "does not offset a virgin cobalt supply chain."
        ),
        region_ids=["packaging"],
        options=[
            CatalogOption(
                id="fibre-packaging",
                name="Recycled & moulded-fibre packaging",
                summary=(
                    "Cardboard and moulded fibre cushions from recycled "
                    "and renewable sources."
                ),
                details=(
                    "Packaging is where circular targets get hit first "
                    "and hardest, because cardboard and moulded fibre "
                    "are the easiest material class on Earth to recycle "
                    "and the recovery chain already exists in every "
                    "city. Dell's ~97% recycled-or-renewable packaging "
                    "figure is credible for exactly that reason. The "
                    "win is real; its scale should be stated honestly — "
                    "a few hundred grams per shipped device, gone from "
                    "the ledger within weeks of delivery."
                ),
            ),
            CatalogOption(
                id="multipack",
                name="Multipack & reduced shipping material",
                summary=(
                    "Bulk packing for fleet orders — less material per "
                    "device and denser freight."
                ),
                details=(
                    "For an enterprise taking 5,000 units, single-boxing "
                    "is waste with extra steps. Multipack ships devices "
                    "in shared cartons, cutting packaging mass per "
                    "device and improving pallet density, which quietly "
                    "reduces freight emissions too. It is the rare "
                    "circular measure that also saves the buyer money "
                    "with no trade-off to name."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="design-for-repair",
        name="Design for repair",
        blurb=(
            "Decisions made at the CAD stage — screws not glue, modular "
            "parts — that decide what recovery can do seven years later."
        ),
        limits=(
            "Repairability trades against thinness and water resistance, "
            "and against the incentive to sell replacement units."
        ),
        region_ids=["manufacture", "service"],
        options=[
            CatalogOption(
                id="replaceable-battery",
                name="Customer-replaceable battery",
                summary=(
                    "A pack that lifts out with a screwdriver instead of "
                    "a heat gun."
                ),
                details=(
                    "The battery is the component that ages fastest and "
                    "the one most likely to end a laptop's life, so "
                    "whether it is screwed or glued in is arguably the "
                    "single most consequential circular-design decision "
                    "in the product. A customer-replaceable pack turns "
                    "end-of-life at year four into a ten-minute service "
                    "event — a 300-gram part deferring a two-kilogram "
                    "replacement and the manufacturing run behind it. "
                    "The trade is real: glued packs allow thinner "
                    "chassis, and thin sells."
                ),
            ),
            CatalogOption(
                id="modular-design",
                name="Modular, simplified internals",
                summary=(
                    "Standard screws, simplified cabling, and modular "
                    "keyboards, fans, and ports."
                ),
                details=(
                    "Modularity is what makes the second and third "
                    "repairs economic, not just the first: a keyboard "
                    "that swaps without removing the mainboard, fans on "
                    "connectors rather than solder, USB-C ports on "
                    "daughterboards. It also speeds refurbishment at "
                    "end of life — triage time per device is a direct "
                    "cost in the recovery fork, and simplified "
                    "internals are why the refurbish path can carry "
                    "most of the cohort's mass profitably."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="repair-support",
        name="Repair support",
        blurb=(
            "Spare parts, tutorials, and an AR repair assistant — the "
            "infrastructure that turns repairability into repairs."
        ),
        limits=(
            "A replaceable part with no spare-part supply or guide is a "
            "brochure feature. Support has to outlive the sales cycle."
        ),
        region_ids=["service"],
        options=[
            CatalogOption(
                id="spare-parts",
                name="Spare parts availability",
                summary=(
                    "Batteries, keyboards, fans, and boards stocked for "
                    "years after the product ships."
                ),
                details=(
                    "Design-for-repair is only half the transaction; "
                    "the other half is a battery still being orderable "
                    "in year six. Parts availability is a warehouse "
                    "commitment with real carrying cost, and it is "
                    "where repair programs quietly die when the "
                    "commercial pressure to sell new units wins. An "
                    "enterprise buyer evaluating circular claims "
                    "should ask for the parts-availability window in "
                    "writing before asking anything else."
                ),
            ),
            CatalogOption(
                id="ar-assistant",
                name="AR repair assistant & tutorials",
                summary=(
                    "Guided repair — augmented-reality overlays and "
                    "step-by-step tutorials for common procedures."
                ),
                details=(
                    "An AR (augmented reality) assistant overlays the "
                    "procedure on the actual device through a phone "
                    "camera — which screws, in which order, with which "
                    "part — turning a battery or keyboard swap into "
                    "something IT technicians and confident users do "
                    "at a desk rather than a depot. The point is "
                    "throughput: a repair that needs a mail-in program "
                    "gets skipped, and a skipped repair is an early "
                    "retirement."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="life-extension",
        name="Service-life extension",
        blurb=(
            "The largest lever in the loop: every extra year of service "
            "defers a pass through manufacture."
        ),
        limits=(
            "Competes directly with the incentive to sell new units — "
            "and, eventually, with real performance and security limits."
        ),
        region_ids=["service", "deployment"],
        options=[
            CatalogOption(
                id="fleet-refresh-deferral",
                name="Refresh deferral program",
                summary=(
                    "Mid-life battery and part refresh instead of "
                    "whole-fleet replacement at year four."
                ),
                details=(
                    "The standard corporate refresh cycle — replace "
                    "everything at 3–4 years — is timed to the fade of "
                    "a non-replaceable battery. A mid-life refresh "
                    "(battery, maybe SSD and keyboard) stretches the "
                    "same fleet toward seven years, and the arithmetic "
                    "dominates everything else in this catalog: "
                    "manufacture is where the footprint lives, and "
                    "deferring it beats any recovery rate. The honest "
                    "counterweights are OS support windows, security "
                    "baselines, and users' patience with ageing "
                    "hardware — service life ends when any one of "
                    "those does, not when the chassis wears out."
                ),
            ),
            CatalogOption(
                id="upgrade-in-place",
                name="Upgrade in place",
                summary=(
                    "RAM, storage, and battery upgrades that raise a "
                    "deployed fleet's ceiling."
                ),
                details=(
                    "Where memory and storage are socketed rather than "
                    "soldered, a deployed device's working ceiling can "
                    "be raised for a fraction of replacement cost — "
                    "16 GB to 32 GB is often the difference between "
                    "'unusably slow' and two more years of service. "
                    "Soldered RAM, the industry's default in thin "
                    "designs, closes this door at purchase time; a "
                    "buyer who wants it open has to choose it on the "
                    "order form, not at year four."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="asset-recovery",
        name="Asset Recovery Services",
        blurb=(
            "Certified take-back: collection, inventory, data "
            "sanitization with a certificate per device, and residual value back."
        ),
        limits=(
            "Only collects what customers actually return — drawers and "
            "store-rooms full of retired laptops are the leak this "
            "service exists to plug."
        ),
        region_ids=["recovery"],
        options=[
            CatalogOption(
                id="secure-retirement",
                name="Secure retirement & data sanitization",
                summary=(
                    "Cryptographic erasure with a per-device "
                    "certificate, or physical destruction where policy demands."
                ),
                details=(
                    "The reason enterprises hoard retired hardware is "
                    "not sentiment, it is data: the residual risk on "
                    "5,000 used drives outweighs any resale value "
                    "unless erasure is provable. Asset recovery leads "
                    "with certified sanitization — cryptographic "
                    "erasure logged per serial number, with physical "
                    "destruction as the fallback for drives that fail "
                    "to verify — because the certificate is what "
                    "converts a compliance problem into a returnable "
                    "asset. Everything else in the recovery fork "
                    "depends on this step happening first."
                ),
            ),
            CatalogOption(
                id="residual-value",
                name="Residual value return",
                summary=(
                    "Resale value of refurbishable units credited back "
                    "against the next purchase."
                ),
                details=(
                    "A three-to-seven-year-old business laptop is not "
                    "waste; it is inventory with a market price, and "
                    "asset recovery audits, grades, and resells the "
                    "working fraction, returning the value to the "
                    "customer. This is the mechanism that aligns the "
                    "incentives: take-back happens at scale when it "
                    "pays, not when it is virtuous. It is also, "
                    "candidly, in tension with new-unit sales — a "
                    "healthy secondary market is a competitor the "
                    "vendor chose to host."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="refurbishment",
        name="Refurbishment & second life",
        blurb=(
            "The inner return: devices retested, re-batteried, regraded, "
            "and redeployed whole."
        ),
        limits=(
            "Only worth doing while the resale market wants the model — "
            "refurbishment value decays with every CPU generation."
        ),
        region_ids=["refurbish", "deployment"],
        options=[
            CatalogOption(
                id="refurb-redeploy",
                name="Refurbish & redeploy",
                summary=(
                    "Recovered units returned to the customer's own "
                    "fleet for lighter roles."
                ),
                details=(
                    "The shortest loop of all: a device too slow for "
                    "engineering is still ample for a kiosk, a "
                    "conference room, or a spare pool. Internal "
                    "redeployment skips the resale market entirely — "
                    "no freight, no regrading margin — and keeps the "
                    "asset under the same security baseline. Its limit "
                    "is appetite: most estates can absorb a fraction "
                    "of a retiring cohort in lighter roles, not the "
                    "majority."
                ),
            ),
            CatalogOption(
                id="refurb-resale",
                name="Certified refurbished resale",
                summary=(
                    "Graded, warrantied second-life units sold into the "
                    "secondary market."
                ),
                details=(
                    "The majority path for refurbishable units: tested, "
                    "re-batteried, cosmetically graded, and sold with a "
                    "short warranty into markets where a three-year-old "
                    "business laptop is exactly the right product at "
                    "exactly the right price. Every unit sold here "
                    "defers a manufacturing cycle somewhere — usually "
                    "of a cheaper, worse device — which is why reuse "
                    "beats reclamation in the arithmetic even before "
                    "counting the embodied carbon."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="reclamation",
        name="Materials reclamation",
        blurb=(
            "The outer return: shredding, separation, smelting, and "
            "hydrometallurgy, back to the materials pool."
        ),
        limits=(
            "Yields vary by material: metals return at high purity, "
            "plastics downgrade, and some mass is lost as fines and slag "
            "every pass — the leak is a property of the process."
        ),
        region_ids=["reclaim", "materials", "loss"],
        options=[
            CatalogOption(
                id="metal-recovery",
                name="Metal recovery & closed-loop smelting",
                summary=(
                    "Steel, aluminium, copper, and board-level precious "
                    "metals separated and returned to production."
                ),
                details=(
                    "Shredded material passes magnets for steel, "
                    "eddy-current separators for aluminium, and "
                    "smelters that recover copper, gold, and palladium "
                    "from board fractions. The metals are reclamation's "
                    "success story — recoverable at high purity, "
                    "repeatedly. They are also where the leak is "
                    "measured: shredder fines too small to sort and "
                    "metal left in slag are physical properties of the "
                    "process, and any accounting that reports 100% "
                    "recovery has stopped counting somewhere."
                ),
            ),
            CatalogOption(
                id="battery-reclamation",
                name="Battery reclamation",
                summary=(
                    "Cobalt and lithium recovered from packs by "
                    "hydrometallurgy and returned to cell production."
                ),
                details=(
                    "Battery packs are removed before shredding — a "
                    "fire risk otherwise — and processed separately: "
                    "discharged, dismantled, and leached "
                    "hydrometallurgically to recover cobalt, lithium, "
                    "and nickel. This is the hardest and most "
                    "important corner of reclamation, because these "
                    "are the elements with the ugliest virgin supply "
                    "chains, and the recovered fraction of them — not "
                    "the recycled steel — is the number that decides "
                    "whether 'recycled cobalt in new batteries' is a "
                    "supply chain or a press release."
                ),
            ),
        ],
    ),
    CatalogCategory(
        id="lifecycle-reporting",
        name="Lifecycle reporting",
        blurb=(
            "Provenance, per-product carbon footprint data, and "
            "end-of-life outcome reporting for the estate."
        ),
        limits=(
            "A report is evidence, not an outcome — reported kilograms "
            "still have to balance against collected ones."
        ),
        region_ids=["recovery", "materials"],
        options=[
            CatalogOption(
                id="pcf-data",
                name="Product carbon footprint data",
                summary=(
                    "Published per-model estimates of lifetime and "
                    "embodied emissions."
                ),
                details=(
                    "Product carbon footprint (PCF) documents estimate "
                    "a model's lifetime emissions and — the useful part "
                    "— how they split between manufacture and use. For "
                    "client devices the manufacture share dominates, "
                    "which is the datum that justifies every repair "
                    "and deferral decision upstream of it. PCFs are "
                    "estimates built on factors and assumptions; they "
                    "are for comparing options and sizing levers, not "
                    "for auditing grams."
                ),
            ),
            CatalogOption(
                id="sustainability-dashboard",
                name="Sustainability dashboard & outcome reports",
                summary=(
                    "Fleet-level telemetry: energy, estimated "
                    "emissions, and certified end-of-life outcomes."
                ),
                details=(
                    "The reporting layer aggregates what the estate "
                    "actually did — energy drawn, refresh cycles, "
                    "devices returned, kilograms refurbished versus "
                    "reclaimed, sanitization certificates — into the "
                    "evidence regulators and CSRD-style disclosure "
                    "regimes increasingly demand. It is the same "
                    "telemetry-to-insight shape as this repo's "
                    "DellCloudIQ twin, pointed at material instead of "
                    "failures; and like all telemetry it is only as "
                    "honest as the leak it is willing to print."
                ),
            ),
        ],
    ),
]
