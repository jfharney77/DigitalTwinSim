"""The client-brand map (physics_specs/10-additional-products.md §8) —
a static explainer, not a sim: Dell's January 2025 client rebrand, which
is the naming scheme this app's two products live inside. Served from
``GET /api/brandmap`` so the reading-level mechanism applies server-side,
like every other piece of teaching prose here.

Verification status (checked August 2026): the 2025 three-brand scheme
and its Base/Plus/Premium tiers are confirmed by CES 2025 coverage. Two
2026 course-corrections are noted below — the XPS revival is widely
reported (CES 2026); the "Dell Pro Max" → "Dell Pro Precision" workstation
rename is reported by fewer outlets and is labeled accordingly in the
prose rather than stated as settled fact.
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
                "is the sturdy fleet workhorse."
            ),
            standard=(
                "The commercial brand, née Latitude (mobile) and "
                "OptiPlex (desktop): manageability, security, and "
                "lifecycle stability over consumer flash. "
                "Base/Plus/Premium maps the old sub-range spread — "
                "Premium takes the old Latitude 9000-class slot. "
                "Naming runs brand · size · tier: 'Dell Pro 14 Plus'."
            ),
            expert=(
                "Commercial. Latitude + OptiPlex. Premium ≈ old "
                "9000-class. Brand · size · tier naming."
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
                "tokens-per-joule instrument is about. In 2026, "
                "several reports say Dell began renaming these "
                "machines 'Dell Pro Precision', bringing the old "
                "name back — treat that as reported, not settled."
            ),
            standard=(
                "The workstation brand, née Precision: ISV-certified "
                "sustained-performance machines. The tier ladder is "
                "where this app's subject sits — 'Pro Max Plus' is "
                "the Plus tier of this brand, the mobile workstation "
                "with the discrete AI-100-class NPU option (see the "
                "DellProMaxPlus narrative twin and this simulator's "
                "promax personality). 2026 update, reported but less "
                "uniformly sourced than the XPS revival: the Pro Max "
                "name giving way to 'Dell Pro Precision' for new "
                "workstations."
            ),
            expert=(
                "Workstation. Précision → Pro Max (2025); 'Pro Max "
                "Plus' = this app's promax subject. Reported 2026: "
                "→ 'Dell Pro Precision'."
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
            "brought the XPS name back in 2026."
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
            "Two 2026 corrections are noted honestly: XPS returned at "
            "CES 2026 (widely reported), and the Pro Max name is "
            "reportedly giving way to 'Dell Pro Precision' (less "
            "uniformly sourced)."
        ),
        expert=(
            "CES 2025: Dell / Dell Pro / Dell Pro Max × "
            "Base/Plus/Premium, brand · size · tier; Alienware exempt. "
            "'Pro Max Plus' = workstation brand, Plus tier — this "
            "app's promax. 2026: XPS revived; Pro Max → 'Pro "
            "Precision' reported."
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
            "means Base. Desktops and towers follow the same pattern."
        ),
        expert=("Brand · size · tier; omitted tier = Base."),
    ),
    since_note=L(
        novice=(
            "What changed after 2025: at CES 2026 Dell admitted the "
            "backlash was right and brought back the XPS name for its "
            "best consumer laptops. Several reports also say the "
            "workstation line is being renamed from 'Pro Max' to "
            "'Dell Pro Precision' — that one is less certain, so this "
            "page labels it as reported rather than fact."
        ),
        standard=(
            "Status as of August 2026: the XPS revival is confirmed "
            "and widely covered (CES 2026, XPS 14/16 first); the "
            "reported 'Pro Max' → 'Dell Pro Precision' workstation "
            "rename has thinner sourcing and is labeled as reported "
            "throughout this page. The 2025 tier structure itself — "
            "Base/Plus/Premium — remains in use across the Dell and "
            "Dell Pro ranges."
        ),
        expert=(
            "Aug 2026: XPS revival confirmed; 'Pro Precision' rename "
            "reported, unconfirmed. Tier ladder unchanged."
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
        {"label": "DellProMaxPlus narrative twin (this repo) — the on-device inference data path",
         "url": "http://localhost:5186/"},
        {"label": "DellAlienware narrative twin (this repo) — the AC power path",
         "url": "http://localhost:5176/"},
    ],
    brands=BRANDS,
)
