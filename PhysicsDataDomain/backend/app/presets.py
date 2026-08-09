"""Presets and the teaching layer — backend data.

Dataset presets, guided scenarios (scripted walkthroughs that set the
scenario and narrate what to watch), and Explain-mode entries (the
arithmetic behind each key readout, live-substituted in the UI). Teaching
prose carries reading levels 1/3/5 via the shared leveling mechanism.
"""

from __future__ import annotations

from .leveling import L
from .models import (
    Dataset,
    DatasetPreset,
    Explain,
    GuidedScenario,
    Scenario,
    Schedule,
    SimEvent,
)

# --- Dataset presets --------------------------------------------------------

BRANCH = Scenario(
    appliance="dd3410",
    dataset=Dataset(full_tb=8, daily_change_pct=1.0, entropy_pct=25),
    schedule=Schedule(retention_days=30),
    duration_days=60,
)

DATACENTER = Scenario(
    appliance="dd9910",
    dataset=Dataset(full_tb=200, daily_change_pct=2.0, entropy_pct=30),
    schedule=Schedule(retention_days=60),
    duration_days=120,
)

THIRTY_FULLS = Scenario(
    appliance="dd9910",
    dataset=Dataset(full_tb=50, daily_change_pct=1.0, entropy_pct=30),
    schedule=Schedule(retention_days=30),
    duration_days=30,
)

HIGH_CHURN_DB = Scenario(
    appliance="dd9910",
    dataset=Dataset(full_tb=100, daily_change_pct=8.0, entropy_pct=40),
    schedule=Schedule(retention_days=30),
    duration_days=90,
)

DATASET_PRESETS = [
    DatasetPreset(
        id="branch-office", name="Branch office",
        blurb="8 TB of file shares on the edge appliance — 1%/day change, "
              "30 generations. The quiet baseline.",
        appliance=BRANCH.appliance, dataset=BRANCH.dataset, schedule=BRANCH.schedule,
    ),
    DatasetPreset(
        id="datacenter", name="Datacenter estate",
        blurb="200 TB mixed estate on the DD9910 — 2%/day, 60 generations. "
              "Watch the ratio climb with retention.",
        appliance=DATACENTER.appliance, dataset=DATACENTER.dataset,
        schedule=DATACENTER.schedule,
    ),
    DatasetPreset(
        id="thirty-fulls", name="Thirty fulls",
        blurb="The classic demo: 50 TB backed up in full for 30 days — and "
              "it all fits in under 2× one backup's footprint.",
        appliance=THIRTY_FULLS.appliance, dataset=THIRTY_FULLS.dataset,
        schedule=THIRTY_FULLS.schedule,
    ),
    DatasetPreset(
        id="database-churn", name="High-churn database",
        blurb="100 TB of databases at 8%/day change — dedupe still works, "
              "but churn is the ratio's enemy. Compare with the file share.",
        appliance=HIGH_CHURN_DB.appliance, dataset=HIGH_CHURN_DB.dataset,
        schedule=HIGH_CHURN_DB.schedule,
    ),
]

# --- Guided scenarios --------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="thirty-fulls",
        title="Why 30 backups fit in 2×",
        narration=[
            L(
                novice=(
                    "Thirty nights in a row, the same 50 terabytes are "
                    "backed up in full. Naively that needs 1,500 terabytes "
                    "of disk. Watch the physical-capacity line instead: "
                    "after the first night, almost nothing gets added, "
                    "because almost nothing changed — the appliance "
                    "recognizes the pieces it already holds and just "
                    "points at them. By night thirty, all thirty backups "
                    "together occupy less than twice what the first one "
                    "did. Nobody configured that. It emerged from how "
                    "little the data changes day to day."
                ),
                standard=(
                    "Thirty daily fulls of 50 TB at 1%/day change. Logical "
                    "protected data climbs linearly to 1,500 TB; physical "
                    "creeps: first full ≈ 50/cf TB, then ~1% of that per "
                    "day. The final store is under 2× the first backup's "
                    "footprint, and the dedupe-ratio dial ends near 30× "
                    "for generational data — a number that emerged from "
                    "change rate × retention, configured nowhere."
                ),
                expert=(
                    "30 fulls, c = 1%: physical = (F/cf)·(1+29c) ≈ "
                    "1.29 F/cf < 2 F/cf. Ratio ≈ R·cf/(1+(R−1)c). Emergent, "
                    "linear in R for small c."
                ),
            ),
        ],
        question="How many terabytes did backup #30 actually add to the store?",
        scenario=THIRTY_FULLS,
    ),
    GuidedScenario(
        id="encrypted-source",
        title="The encrypted-source mistake",
        narration=[
            L(
                novice=(
                    "A well-meaning security team turns on encryption on "
                    "the servers — before backup — on day 30. Encrypted "
                    "data looks completely random, and it looks like "
                    "*different* random data every night, because the "
                    "encryption keys change per session. So the appliance "
                    "can never say 'seen this before.' Watch the physical "
                    "line: for a month it crawls, then it turns into a "
                    "ramp climbing a full dataset every night. The dedupe "
                    "ratio collapses toward 1, and a store sized for a "
                    "year of backups fills in weeks. Encrypt after "
                    "deduplication, not before."
                ),
                standard=(
                    "100 TB at 2%/day on the DD9910; on day 30 the source "
                    "enables host-side encryption. Fresh session keys mean "
                    "every backup is unique ciphertext: novelty jumps from "
                    "~2% to 100%, local compression dies too (cf → 1), and "
                    "the physical curve breaks from a crawl to +100 TB per "
                    "night. The capacity forecast that justified this "
                    "appliance is void from that day — the store fills "
                    "mid-simulation. This is why encryption belongs at the "
                    "target (or in DDOS itself), downstream of dedupe."
                ),
                expert=(
                    "Day 30: session-keyed ciphertext ⇒ novelty 1.0, cf 1.0. "
                    "dPhys/dt: c·F/cf → F. Ratio → retention-weighted 1:1; "
                    "store full ≈ day 30 + (usable − used)/F. Encrypt "
                    "downstream of dedupe."
                ),
            ),
        ],
        question="On what day does the store hit 100% — and how many months early is that versus the pre-encryption trend?",
        scenario=Scenario(
            appliance="dd9910",
            dataset=Dataset(full_tb=100, daily_change_pct=2.0, entropy_pct=30),
            schedule=Schedule(retention_days=30),
            duration_days=60,
            events=[SimEvent(at_day=30, action="enable-host-encryption")],
        ),
    ),
    GuidedScenario(
        id="entropy-alarm",
        title="Entropy as a smoke alarm",
        narration=[
            L(
                novice=(
                    "On day 40, ransomware starts quietly encrypting about "
                    "three percent of the files every day. Nothing looks "
                    "wrong at first: capacity charts bend so slowly that "
                    "nobody would notice for weeks. But watch the entropy "
                    "instrument — it measures how random today's *changed* "
                    "data looks. Ordinary edits look like documents; "
                    "ransomware's writes look like static. The alarm fires "
                    "within a day or two of the attack, long before any "
                    "capacity number moves. This same physics, read from "
                    "the storage side, is how Dell's Cyber Detect finds "
                    "corrupted snapshots."
                ),
                standard=(
                    "Ransomware begins at day 40, encrypting 3% of the "
                    "dataset per day. The capacity effect is a gentle "
                    "slope change — undetectable for weeks against normal "
                    "variance. The stream-entropy instrument, though, "
                    "watches what *changed* today: churn at baseline "
                    "entropy plus ciphertext at ~98%, and the blend "
                    "crosses the alarm threshold almost immediately. "
                    "The lesson pairs with the encrypted-source scenario: "
                    "the same entropy that ruins your dedupe ratio is the "
                    "earliest honest signal of an attack — one fact, two "
                    "sides. Cyber Detect (see the DellCyberDetect twin) "
                    "reads it from snapshots; the backup appliance reads "
                    "it from the ingest stream."
                ),
                expert=(
                    "rw 3%/day from d40. ΔPhys slope +3F/100 per day — "
                    "weeks to surface. Entropy of deltas: (c·e + r·98)/"
                    "(c+r) ≈ 71% at d41 ⇒ alarm in O(1) days. Capacity "
                    "detects in O(weeks). Same signal as Cyber Detect, "
                    "opposite endpoint."
                ),
            ),
        ],
        question="How many days pass between the entropy alarm and the day the capacity curve visibly breaks trend?",
        scenario=Scenario(
            appliance="dd9910",
            dataset=Dataset(full_tb=100, daily_change_pct=2.0, entropy_pct=30),
            schedule=Schedule(retention_days=45),
            duration_days=90,
            events=[
                SimEvent(at_day=40, action="ransomware-start", value=3.0),
                SimEvent(at_day=70, action="ransomware-stop"),
            ],
        ),
    ),
    GuidedScenario(
        id="index-knee",
        title="The fingerprint-index knee",
        narration=[
            L(
                novice=(
                    "The little branch-office appliance is given a dataset "
                    "on the large side for it, with a busy change rate. "
                    "There is plenty of disk left — but watch the ingest "
                    "speed instrument. Every piece of every backup "
                    "requires one lookup in the fingerprint catalog, and "
                    "that catalog must live in fast memory to keep up. As "
                    "unique data accumulates, the catalog outgrows memory, "
                    "lookups slow down, and backups take longer — while "
                    "the disks sit half empty. Appliances run out of "
                    "*index* before they run out of disk more often than "
                    "people expect."
                ),
                standard=(
                    "A 20 TB, 3%/day dataset on the DD3410 with 60-day "
                    "retention. The store fills slowly — but the "
                    "fingerprint index crosses its RAM budget around "
                    "week two, and ingest throughput degrades past the "
                    "knee from that day on: same disks, same network, "
                    "slower backups. The backup window instrument shows "
                    "the operational symptom. Index pressure, not raw "
                    "capacity, is the entry appliance's real ceiling."
                ),
                expert=(
                    "Chunks = phys/8 KB; RAM-resident sample × 64 B ⇒ "
                    "index > 8 GB near phys ≈ 20 TB; ingest = base/(1+k·"
                    "pressure). Knee precedes disk-full by weeks. Size "
                    "the index, not the shelf."
                ),
            ),
        ],
        question="On what day does ingest first drop below 80% of its rated speed — and how full is the store that day?",
        scenario=Scenario(
            appliance="dd3410",
            dataset=Dataset(full_tb=20, daily_change_pct=3.0, entropy_pct=30),
            schedule=Schedule(retention_days=60),
            duration_days=60,
        ),
    ),
    GuidedScenario(
        id="retention-dial",
        title="Retention is the ratio's engine",
        narration=[
            L(
                novice=(
                    "Ninety days of backups are kept instead of thirty. "
                    "Watch the dedupe ratio climb the whole time "
                    "generations accumulate: every extra night of history "
                    "adds a full backup's worth of *logical* protection "
                    "while adding only a day's small changes to the disk. "
                    "Then, on day 91, the oldest backup expires, the "
                    "cleaner wakes up for the first time, and everything "
                    "levels off. More history makes deduplication look "
                    "better — which is the opposite of how most storage "
                    "intuition works."
                ),
                standard=(
                    "50 TB at 1%/day with 90-generation retention, run for "
                    "180 days. The ratio rises for exactly 90 days — the "
                    "numerator (logical) gains a full 50 TB per night, the "
                    "denominator gains ~0.3 TB — then generation 1 expires, "
                    "GC reclaims its stranded chunks, and both curves "
                    "plateau. The steady-state ratio is roughly R·cf/"
                    "(1+(R−1)c): retention length is a *first-order* input "
                    "to the ratio, which is why quoted dedupe figures are "
                    "meaningless without the retention behind them."
                ),
                expert=(
                    "Ratio(t) = t·cf/(1+(t−1)c) until t = R, then flat; "
                    "GC begins at R+1. Quoted ratios embed R — 'we get "
                    "40×' means nothing without it."
                ),
            ),
        ],
        question="What is the ratio on day 30, day 90, and day 180 — and why does the middle number never improve again?",
        scenario=Scenario(
            appliance="dd9910",
            dataset=Dataset(full_tb=50, daily_change_pct=1.0, entropy_pct=30),
            schedule=Schedule(retention_days=90),
            duration_days=180,
        ),
    ),
]

# --- Explain-mode entries -----------------------------------------------------

EXPLAINS = [
    Explain(
        id="dedupe-ratio",
        title="Dedupe ratio",
        equation="ratio = logical protected ÷ physical stored",
        inputs=["retained generations", "logical TB", "physical TB", "ratio"],
        explanation=L(
            novice=(
                "The headline number is just a division: all the data you "
                "are protecting (every kept backup counted at full size) "
                "divided by the disk actually used. Nothing sets it "
                "directly — it gets better when backups repeat unchanged "
                "data, and worse when data churns or arrives encrypted."
            ),
            standard=(
                "Logical is the sum of retained generations at full size; "
                "physical is the ledger of unique chunks plus metadata "
                "overhead. The ratio is their quotient and nothing else — "
                "it emerges from change rate, retention, and entropy, "
                "approximately R·cf/(1+(R−1)·c) at steady state."
            ),
            expert=(
                "ratio = Σ_gens logical / ledger phys ≈ R·cf/(1+(R−1)c). "
                "Emergent; quoting it without R and c is marketing."
            ),
        ),
    ),
    Explain(
        id="novelty",
        title="Today's novel data",
        equation="novel = churn/cf + encrypted-writes × 1.0",
        inputs=["change rate", "entropy", "novel TB", "physical TB"],
        explanation=L(
            novice=(
                "Each night, only the pieces the appliance has never seen "
                "get stored. Normally that is just what changed since "
                "yesterday, squeezed smaller by compression. Encrypted "
                "writes are the exception: they are always brand new to "
                "the appliance, and they refuse to compress."
            ),
            standard=(
                "The day's physical addition: changed clean data enters "
                "at 1/cf (it compresses), while ciphertext enters at full "
                "size (novel by construction, incompressible by "
                "definition). Host-side encryption makes the entire "
                "stream take the second path."
            ),
            expert=(
                "novel = c·(1−F)·full/cf + r·full. Session-keyed "
                "ciphertext ⇒ novel = full, cf = 1."
            ),
        ),
    ),
    Explain(
        id="compression",
        title="Local compression vs entropy",
        equation="cf = 1 + (cf_max − 1) × (1 − entropy/100)",
        inputs=["entropy", "compression factor", "novel TB"],
        explanation=L(
            novice=(
                "After deduplication, the appliance also compresses what "
                "it stores — like zipping a file. Orderly data (text, "
                "databases) shrinks well; random-looking data (already-"
                "compressed video, encrypted anything) barely shrinks at "
                "all. The entropy dial is exactly this randomness."
            ),
            standard=(
                "Novel chunks get lz-class local compression on top of "
                "dedupe. The factor runs from ~2× on low-entropy business "
                "data down to 1× at entropy 100 — ciphertext and "
                "pre-compressed media are already at maximum density."
            ),
            expert=(
                "cf ∈ [1, cf_max], linear in (1 − H). Ciphertext: H ≈ 98 "
                "⇒ cf ≈ 1. Dedupe and lz die of the same disease."
            ),
        ),
    ),
    Explain(
        id="index-pressure",
        title="Ingest vs index pressure",
        equation="ingest = base ÷ (1 + k × max(0, index/RAM − 1))",
        inputs=["unique chunks", "index GB", "index RAM", "ingest GB/s"],
        explanation=L(
            novice=(
                "Every piece of every backup triggers one question — seen "
                "before? — against a catalog of fingerprints. While the "
                "catalog fits in fast memory, the question is instant. "
                "Once it outgrows memory, some questions go to much "
                "slower storage, and the whole backup slows down. More "
                "unique data means a bigger catalog, so appliances can "
                "slow down before they fill up."
            ),
            standard=(
                "The fingerprint index costs ~64 B per unique chunk, with "
                "a RAM-resident sample keeping lookups fast. Past the RAM "
                "budget, throughput divides by (1 + k·pressure) — the "
                "knee. Unique chunks scale with *physical* data, so low "
                "dedupe ratios reach the knee sooner."
            ),
            expert=(
                "chunks = phys/8 KB; index = chunks·64 B·sample. "
                "Pressure = index/RAM − 1; throughput hyperbolic past "
                "the knee. Ratio collapse ⇒ index blowup — coupled "
                "failures."
            ),
        ),
    ),
    Explain(
        id="backup-window",
        title="Backup window",
        equation="window = logical TB ÷ (ingest × dedupe speedup)",
        inputs=["logical TB", "novel TB", "ingest GB/s", "window hours"],
        explanation=L(
            novice=(
                "How long the nightly backup takes. Because unchanged "
                "pieces never even cross the network, a quiet night "
                "'backs up' terabytes in minutes. The morning after "
                "encryption is turned on, everything must actually "
                "travel and be stored — and the window explodes from "
                "minutes to hours."
            ),
            standard=(
                "Effective logical throughput is physical ingest times "
                "the day's dedupe factor (capped — client-side dedupe "
                "can't be infinitely fast). The window is logical size "
                "over that rate: it collapses when novelty does, which "
                "is why an encrypted source shows up first as backups "
                "that stop finishing overnight."
            ),
            expert=(
                "window = L/(ingest·min(L/novel, cap)). Novelty → 1 ⇒ "
                "window → L/ingest: the SLA breach arrives before the "
                "capacity alarm."
            ),
        ),
    ),
]
