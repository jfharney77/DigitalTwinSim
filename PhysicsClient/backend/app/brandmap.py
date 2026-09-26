"""The client-brand map (physics_specs/10-additional-products.md §8) —
a static explainer, not a sim: Dell's January 2025 client rebrand, which
is the naming scheme this app's two products live inside. Served from
``GET /api/brandmap`` so the reading-level mechanism applies server-side,
like every other piece of teaching prose here.

Verification status (fact-checked September 2026): the 2025 three-brand
scheme and its Base/Plus/Premium tiers are confirmed by CES 2025 coverage.
Two 2026 course-corrections are both confirmed by Dell's own releases —
the XPS revival (CES 2026, January 6) and the return of Precision as
"Dell Pro Precision" (March 25, 2026 commercial-PC release, which also
introduced the numbered Dell Pro 3/5/7 notebooks). What stays labeled
*reported*: the model-by-model mapping (Pro Precision 5/7 replacing Pro
Max / Pro Max Premium, per Notebookcheck) and whether the Pro Max name
is eventually retired — Dell still launched Pro Max products in March
2026 (Pro Max 16, Pro Max with GB300).
"""

from __future__ import annotations

from .leveling import L
from .models import Brand, BrandMap

BRANDS: list[Brand] = [
    Brand(
        id="dell",
        name="Dell",
        formerly="XPS · Inspiron (consumer lines)",
        audience="Consumer — everyday work, school, play",
        tiers=["Base", "Plus", "Premium"],
        description=L(
            novice=(
                "The plain 'Dell' name became the consumer brand in 2025, "
                "absorbing two older names: Inspiron (the everyday "
                "laptops) and XPS (the fancy thin ones). A machine is "
                "then placed on a three-step ladder — Base, Plus, "
                "Premium — so 'Dell 14 Premium' means the nicest "
                "consumer 14-inch, roughly where an XPS used to sit. "
                "One year later Dell brought the XPS name back for its "
                "top consumer laptops, because customers missed it."
            ),
            standard=(
                "The consumer brand: in January 2025 it absorbed "
                "Inspiron and XPS, with the Base/Plus/Premium tier "
                "carrying what the sub-brands used to signal — 'Dell 14 "
                "Premium' occupied the old XPS slot. Note the 2026 "
                "correction: after sustained backlash, XPS returned at "
                "CES 2026 as the premium consumer line (XPS 14/16, then "
                "13), sitting back on top of the plain-Dell range."
            ),
            expert=(
                "Consumer. Absorbed Inspiron + XPS (2025); Premium tier "
                "≈ old XPS slot. XPS revived at CES 2026 above it."
            ),
        ),
    ),
    Brand(
        id="dell-pro",
        name="Dell Pro",
        formerly="Latitude · OptiPlex",
        audience="Business — fleet, security, manageability",
        tiers=["Base", "Plus", "Premium"],
        description=L(
            novice=(
                "'Dell Pro' is the business brand — the machines a "
                "company's IT department buys by the hundred. It "
                "replaced two old names: Latitude (business laptops) "
                "and OptiPlex (business desktops). The same three-step "
                "ladder applies, so a 'Dell Pro 14 Premium' is the "
                "thin-and-light executive laptop, while a Base model "
                "is the sturdy fleet workhorse. In 2026 Dell swapped "
                "the Base and Plus words on its business laptops for "
                "numbers: Dell Pro 3, 5, and 7."
            ),
            standard=(
                "The commercial brand, née Latitude (mobile) and "
                "OptiPlex (desktop): manageability, security, and "
                "lifecycle stability over consumer flash. "
                "Base/Plus/Premium maps the old sub-range spread — "
                "Premium takes the old Latitude 9000-class slot. "
                "Naming runs brand · size · tier: 'Dell Pro 14 Plus'. "
                "The March 2026 notebooks moved to numbered series — "
                "Dell Pro 3, 5, and 7 — with Premium reported to "
                "remain above them."
            ),
            expert=(
                "Commercial. Latitude + OptiPlex. Premium ≈ old "
                "9000-class. Brand · size · tier naming (2025); "
                "Pro 3/5/7 numbering from Mar 2026."
            ),
        ),
    ),
    Brand(
        id="dell-pro-max",
        name="Dell Pro Max",
        formerly="Precision (workstations)",
        audience="Workstation — ISV, rendering, on-device AI",
        tiers=["Base", "Plus", "Premium"],
        description=L(
            novice=(
                "'Dell Pro Max' became the workstation brand — the "
                "heavy machines for 3-D work, engineering, and AI, "
                "which used to be called Precision. This app's second "
                "product lives here: the 'Pro Max Plus' is the "
                "middle-tier mobile workstation, and its optional "
                "dedicated AI chip is what the simulator's "
                "tokens-per-joule instrument is about. In March 2026 "
                "Dell brought the old name back as 'Dell Pro "
                "Precision' for its new workstations. Some machines "
                "still carry the Pro Max name, and it is reported — "
                "not settled — that the name will fade out as models "
                "are replaced."
            ),
            standard=(
                "The workstation brand, née Precision: ISV-certified "
                "sustained-performance machines. The tier ladder is "
                "where this app's subject sits — 'Pro Max Plus' is "
                "the Plus tier of this brand, the mobile workstation "
                "with the discrete AI-100-class NPU option (see the "
                "DellProMaxPlus narrative twin and this simulator's "
                "promax personality; the shipping product is the 'Dell "
                "Pro Max 16 Plus'). 2026 update: Dell's March 25, 2026 "
                "release brought Precision back as 'Dell Pro "
                "Precision' for new workstations. Reported by trade "
                "press rather than stated by Dell: Pro Precision 5 and "
                "7 succeed the Pro Max and Pro Max Premium laptops, "
                "while Pro Max continues on a few AI-focused systems."
            ),
            expert=(
                "Workstation. Précision → Pro Max (2025); 'Pro Max "
                "Plus' = this app's promax subject. Mar 2026: Dell "
                "Pro Precision returns (Dell PR); model mapping and "
                "Pro Max's retirement are reported, not stated."
            ),
        ),
    ),
    Brand(
        id="alienware",
        name="Alienware",
        formerly="Alienware (unchanged)",
        audience="Gaming — burst performance, spectacle",
        tiers=["(own model lines — no Base/Plus/Premium)"],
        description=L(
            novice=(
                "Alienware is the gaming brand, and it was the one "
                "name the 2025 rebrand did not touch — it kept its own "
                "identity and its own model names. This app's first "
                "product is an Alienware: the gaming laptop whose "
                "burst-then-fade behavior the simulator teaches."
            ),
            standard=(
                "The gaming brand, deliberately left outside the 2025 "
                "scheme: it keeps its own identity and model naming "
                "rather than the Base/Plus/Premium ladder. This "
                "simulator's alienware personality (and the "
                "DellAlienware narrative twin's AC power path) model "
                "its laptops and towers."
            ),
            expert=(
                "Gaming; exempt from the 2025 scheme. Own model "
                "naming. This app's first personality."
            ),
        ),
    ),
]


BRAND_MAP = BrandMap(
    overview=L(
        novice=(
            "In January 2025 Dell renamed nearly its whole PC range. "
            "Decades-old names — Inspiron, Latitude, OptiPlex, "
            "Precision, XPS — were replaced by three brands that say "
            "who the machine is for: plain 'Dell' for home, 'Dell Pro' "
            "for business, 'Dell Pro Max' for heavy professional work. "
            "Inside each brand, a machine is Base, Plus, or Premium — "
            "good, better, best. Alienware, the gaming brand, kept its "
            "name. The map below is worth learning because this "
            "simulator's two machines are named by it: an Alienware "
            "gaming laptop, and a 'Pro Max Plus' workstation — the "
            "Plus tier of the Pro Max brand. One footnote from a year "
            "later: customers pushed back hard enough that Dell "
            "brought the XPS name back in 2026, and the Precision name "
            "too, as 'Dell Pro Precision'."
        ),
        standard=(
            "Dell's January 2025 client rebrand collapsed the legacy "
            "portfolio into three audience-named brands — Dell "
            "(consumer, absorbing XPS and Inspiron), Dell Pro "
            "(business, née Latitude/OptiPlex), Dell Pro Max "
            "(workstation, née Precision) — each with Base/Plus/"
            "Premium tiers, named brand · size · tier. Alienware "
            "stayed itself. The scheme is why this app's products are "
            "named as they are: the promax personality is the 'Pro "
            "Max Plus', i.e. the Plus tier of the workstation brand. "
            "Two 2026 corrections, both from Dell's own releases: XPS "
            "returned at CES 2026, and Precision returned in March "
            "2026 as 'Dell Pro Precision'. How far the Pro Max name "
            "recedes is reported rather than stated."
        ),
        expert=(
            "CES 2025: Dell / Dell Pro / Dell Pro Max × "
            "Base/Plus/Premium, brand · size · tier; Alienware exempt. "
            "'Pro Max Plus' = workstation brand, Plus tier — this "
            "app's promax. 2026: XPS revived (CES); Dell Pro "
            "Precision returns (Mar 25); Pro Max retirement reported."
        ),
    ),
    naming_note=L(
        novice=(
            "How to read a 2025-scheme model name: brand first, then "
            "screen size, then tier. 'Dell Pro 14 Premium' = business "
            "brand, 14-inch, top tier. No tier word means Base."
        ),
        standard=(
            "Names run brand · size · tier: 'Dell Pro 14 Premium' is "
            "the business brand's 14-inch top tier; tier omitted "
            "means Base. Desktops put the form factor where the size "
            "goes: 'Dell Pro Max Tower', 'Dell Pro Slim'."
        ),
        expert=("Brand · size · tier; omitted tier = Base."),
    ),
    since_note=L(
        novice=(
            "What changed after 2025: at CES 2026 Dell brought back "
            "the XPS name for its best consumer laptops. In March "
            "2026 it brought back Precision as well — new "
            "workstations are 'Dell Pro Precision' — and gave its "
            "business laptops numbers: Dell Pro 3, 5, and 7. Both "
            "come from Dell's own announcements. Which exact model "
            "replaces which, and whether the Pro Max name disappears "
            "completely, is reported by the press rather than said "
            "by Dell, so this page labels it that way."
        ),
        standard=(
            "Status as of September 2026: the XPS revival is "
            "confirmed by Dell (CES 2026 release: XPS 14 and 16 "
            "first, XPS 13 later in the year). Dell's March 25, 2026 "
            "commercial release confirms 'Dell Pro Precision' "
            "workstations and numbered Dell Pro 3/5/7 notebooks, so "
            "the Base/Plus wording is receding from the business "
            "range. Reported by Notebookcheck rather than stated by "
            "Dell: Pro Precision 5 replaces the Pro Max laptop and "
            "Pro Precision 7 the Pro Max Premium. Pro Max has not "
            "vanished — Dell launched a Pro Max 16 and a Pro Max with "
            "GB300 the same month — and this app's subject, the Pro "
            "Max 16 Plus, keeps its 2025 name."
        ),
        expert=(
            "Sep 2026: XPS revival and Dell Pro Precision both "
            "confirmed by Dell; Dell Pro → 3/5/7. Model mapping and "
            "Pro Max retirement reported only."
        ),
    ),
    sources=[
        {"label": "Tom's Hardware — Dell kills XPS and OptiPlex, adopts three-tier naming (CES 2025)",
         "url": "https://www.tomshardware.com/laptops/dell-kills-xps-and-optiplex-brands-adopts-apple-inspired-three-tiered-naming-scheme-for-its-pcs"},
        {"label": "TechRadar — Dell launches rebranded laptops at CES 2025",
         "url": "https://www.techradar.com/computing/dell-launches-newly-rebranded-laptops-at-ces-2025-to-replace-storied-xps-inspiron-and-other-product-lines"},
        {"label": "Windows Central — Dell brings back XPS at CES 2026 after backlash",
         "url": "https://www.windowscentral.com/hardware/dell/dell-xps-returns-in-2026-after-rebrand-flop"},
        {"label": "ChannelPro — Dell at CES 2026: XPS revival",
         "url": "https://www.channelpronetwork.com/2026/01/08/dell-revives-xps-brand-new-displays/"},
        {"label": "Dell — CES 2026 press release: XPS returns (January 6, 2026)",
         "url": "https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~1~dell-technologies-at-ces-2026.htm"},
        {"label": "Dell — commercial PC press release: Dell Pro Precision, Dell Pro 3/5/7 (March 25, 2026)",
         "url": "https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~03~dell-reimagines-commercial-pcs-with-new-sleek-and-powerful-designs.htm"},
        {"label": "Notebookcheck — 2026 Dell Pro hands-on: numbered naming, Pro Precision 5/7 replace Pro Max (reported)",
         "url": "https://www.notebookcheck.net/Dell-is-back-in-the-laptop-game-2026-Dell-Pro-laptops-hands-on.1271200.0.html"},
        {"label": "StorageReview — Dell's March 2026 workstation lineup: Pro Precision alongside Pro Max 16 and Pro Max with GB300",
         "url": "https://www.storagereview.com/news/dell-expands-professional-workstation-portfolio-with-new-precision-and-pro-max-systems"},
        {"label": "DellProMaxPlus narrative twin (this repo) — the on-device inference data path",
         "url": "http://localhost:5186/"},
        {"label": "DellAlienware narrative twin (this repo) — the AC power path",
         "url": "http://localhost:5176/"},
    ],
    brands=BRANDS,
)
