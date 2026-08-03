"""Use cases: three situations where the loop earns its keep.

Same integrity rule as every twin: every config line resolves to a real
catalog category and option (enforced in tests/test_catalog.py), and the
narratives keep the repo's register — skeptical, specific, willing to name
the trade.
"""

from __future__ import annotations

from .models import Stat, UseCase, UseCaseItem

USE_CASES: list[UseCase] = [
    UseCase(
        id="fleet-refresh",
        title="Refreshing 5,000 laptops without a skip",
        summary=(
            "An enterprise retiring a laptop fleet wants residual value "
            "and certified data destruction rather than a store-room "
            "full of liability."
        ),
        narrative=[
            (
                "The estate: 5,000 corporate laptops at end of their "
                "deployment, which is the cohort this twin's trace "
                "follows. The default outcome — the one that happens "
                "when nobody decides anything — is not recycling and "
                "not landfill; it is the store-room. Retired laptops "
                "accumulate in cupboards because the data risk of "
                "letting a drive leave the building outweighs any "
                "resale value anyone can name, and hardware that sits "
                "in a cupboard for five years exits the refurbishment "
                "window and becomes shredder feed with extra steps."
            ),
            (
                "Certified sanitization is what breaks the deadlock: "
                "cryptographic erasure logged per serial number, with a "
                "certificate the security team can file against the "
                "asset register. Once the data objection is retired, "
                "the fleet is inventory — graded, and split the way the "
                "trace's sort step shows: the majority refurbished and "
                "resold with the residual value credited back, the "
                "remainder reclaimed for materials, and a stated "
                "fraction lost. The credit is not charity; a "
                "three-year-old business laptop has a real market "
                "price, and the program works at scale precisely "
                "because it pays."
            ),
            (
                "The honest fine print: residual value decays with "
                "every CPU generation the fleet ages past, so the "
                "economics reward returning hardware promptly — which "
                "sits awkwardly alongside the fact that the greenest "
                "option is usually to keep using it. The resolution is "
                "to decide service life deliberately (with a mid-life "
                "battery refresh, not by default at year three) and "
                "then return the fleet the quarter it retires, rather "
                "than letting either the sales cycle or the cupboard "
                "decide."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="asset-recovery",
                option_id="secure-retirement",
                qty=5000,
                rationale=(
                    "The per-device sanitization certificate is what "
                    "gets 5,000 drives released by the security team."
                ),
            ),
            UseCaseItem(
                category_id="asset-recovery",
                option_id="residual-value",
                qty=5000,
                rationale=(
                    "Resale value credited against the replacement "
                    "purchase — the incentive that makes take-back "
                    "happen at all."
                ),
            ),
            UseCaseItem(
                category_id="refurbishment",
                option_id="refurb-resale",
                qty=3100,
                rationale=(
                    "The refurbishable majority goes back to work; "
                    "every unit defers a manufacturing cycle somewhere."
                ),
            ),
            UseCaseItem(
                category_id="reclamation",
                option_id="metal-recovery",
                qty=1900,
                rationale=(
                    "The non-refurbishable remainder is shredded and "
                    "separated; the metals come back, the fines do not."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Drives sanitized with certificate", value="5,000 of 5,000"),
            Stat(label="Units refurbished vs reclaimed", value="~3,100 vs ~1,900"),
            Stat(label="Mass not recovered", value="~4.5% — stated in the report"),
            Stat(label="Store-room liability", value="Zero units shelved"),
        ],
    ),
    UseCase(
        id="embodied-carbon",
        title="A datacenter refresh audited for embodied carbon",
        summary=(
            "An operator weighing replacement against life extension "
            "finds the interesting answer: keeping the racks usually wins."
        ),
        narrative=[
            (
                "The proposal on the table is familiar: replace "
                "three-year-old servers with new ones that are 20% more "
                "power-efficient, and book the energy saving as a "
                "sustainability win. The embodied-carbon audit runs the "
                "other side of the ledger: most of a server's lifetime "
                "footprint is committed at manufacture — metals, "
                "boards, and fabrication — before the first watt is "
                "drawn at the socket. At rack scale the numbers stop "
                "being abstract: this repo's DellPowerEdgeXE9712 twin "
                "is tonnes of copper, steel, and silicon in a single "
                "rack, and a refresh is all of that, again."
            ),
            (
                "Run honestly, the comparison usually lands on "
                "extension: a 20% operating efficiency gain takes years "
                "to repay a whole second manufacturing run, and the "
                "crossover moves further out wherever the grid feeding "
                "the datacenter is clean. The product carbon footprint "
                "data is what makes the calculation possible at all — "
                "estimates, not audits, but good enough to size the "
                "lever. The audit's usual conclusion is the trace's "
                "repair and extend steps wearing enterprise clothes: "
                "add memory, swap drives, defer the refresh."
            ),
            (
                "The trade-offs deserve naming: extension is not free "
                "(support contracts, failure rates, and performance "
                "per watt all age), and there are genuine crossover "
                "cases — grids running on coal, workloads starved for "
                "the new generation's accelerators. The point of the "
                "audit is not that replacement is always wrong; it is "
                "that the default assumption — newer is greener — "
                "reliably ignores the manufacture side of the ledger, "
                "and the manufacture side usually dominates."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="lifecycle-reporting",
                option_id="pcf-data",
                qty=1,
                rationale=(
                    "The manufacture-versus-use split per model is the "
                    "datum the whole decision turns on."
                ),
            ),
            UseCaseItem(
                category_id="life-extension",
                option_id="upgrade-in-place",
                qty=400,
                rationale=(
                    "Memory and storage raise the deployed fleet's "
                    "ceiling for a fraction of a refresh's footprint."
                ),
            ),
            UseCaseItem(
                category_id="life-extension",
                option_id="fleet-refresh-deferral",
                qty=1,
                rationale=(
                    "The deferral is the decision: two more years of "
                    "service before manufacture is paid again."
                ),
            ),
            UseCaseItem(
                category_id="lifecycle-reporting",
                option_id="sustainability-dashboard",
                qty=1,
                rationale=(
                    "Energy and outcome telemetry to check the "
                    "deferral's arithmetic against reality next year."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Refresh deferred", value="~2 years"),
            Stat(label="Embodied carbon avoided", value="A second manufacturing run"),
            Stat(label="Efficiency payback honestly stated", value="Years, not months"),
            Stat(label="Decision basis", value="Both sides of the ledger"),
        ],
    ),
    UseCase(
        id="provenance-reporting",
        title="Reporting material provenance under regulatory pressure",
        summary=(
            "A manufacturer facing disclosure rules must state where "
            "material came from and where it went — including the "
            "fraction that went nowhere."
        ),
        narrative=[
            (
                "Disclosure regimes — CSRD-style sustainability "
                "reporting, right-to-repair rules, battery-passport "
                "requirements — are converging on the same demand: not "
                "a pledge but a ledger. What fraction of input material "
                "was recovered, from where; what fraction of retired "
                "product was reused, reclaimed, or lost. The structure "
                "being demanded is exactly this twin's conservation "
                "invariant: reused plus reclaimed plus lost must equal "
                "mass in, and a report that cannot make those columns "
                "balance is describing a diagram, not a supply chain."
            ),
            (
                "The compliance path assembles from the loop's parts: "
                "provenance from the material-inputs side (with the "
                "recycled share stated per material, because a blended "
                "34% hides that the cobalt fraction is the hard one), "
                "end-of-life outcomes from asset recovery's certified "
                "records, and the whole thing aggregated by the "
                "reporting layer into the estate-level evidence an "
                "auditor can test. The per-device sanitization and "
                "outcome certificates turn out to be the load-bearing "
                "documents — they are the only place the reported "
                "kilograms attach to serial numbers."
            ),
            (
                "The uncomfortable line in the report is the honest "
                "one: the loss row. A filing that claims zero loss "
                "invites the auditor to find it; a filing that states "
                "4.5% lost as fines and slag, with the process it was "
                "lost in, is credible precisely because it admits the "
                "leak. Regulation is, in effect, mandating the loss "
                "region onto everyone's lifecycle map — which is this "
                "twin's argument arriving with penalties attached."
            ),
        ],
        config=[
            UseCaseItem(
                category_id="material-inputs",
                option_id="recycled-metals",
                qty=1,
                rationale=(
                    "Provenance starts at procurement: recovered-content "
                    "share stated per metal, not blended."
                ),
            ),
            UseCaseItem(
                category_id="reclamation",
                option_id="battery-reclamation",
                qty=1,
                rationale=(
                    "Battery-passport rules make cobalt and lithium "
                    "recovery the most scrutinized row in the filing."
                ),
            ),
            UseCaseItem(
                category_id="asset-recovery",
                option_id="secure-retirement",
                qty=1,
                rationale=(
                    "Certified outcomes per serial number are what let "
                    "reported kilograms survive an audit."
                ),
            ),
            UseCaseItem(
                category_id="lifecycle-reporting",
                option_id="sustainability-dashboard",
                qty=1,
                rationale=(
                    "Aggregates the ledger — including the loss row — "
                    "into the disclosure the regulator actually reads."
                ),
            ),
        ],
        outcomes=[
            Stat(label="Ledger structure", value="Reused + reclaimed + lost = mass in"),
            Stat(label="Recycled input", value="Stated per material, not blended"),
            Stat(label="Loss row", value="Stated at 4.5% — not zero"),
            Stat(label="Audit anchor", value="Certificates per serial number"),
        ],
    ),
]
