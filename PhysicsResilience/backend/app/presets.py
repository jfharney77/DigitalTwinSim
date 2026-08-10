"""Presets and the teaching layer for the resilience simulator."""

from __future__ import annotations

from .leveling import L
from .models import (
    ConfigPreset,
    Explain,
    GuidedScenario,
    ResilienceConfig,
    Scenario,
    SimEvent,
)

# --- Config presets --------------------------------------------------------

VAULTED = ResilienceConfig(
    product="powerprotect", estate_tb=200, change_gb_day=500,
    backup_every_h=24, retention_copies=14, dedupe_ratio=10,
    vault=True, vault_sync_every_h=24, restore_gbps=1.0,
)
REPO_ONLY = VAULTED.model_copy(update={"vault": False})
DETECTING = ResilienceConfig(
    product="cyberdetect", estate_tb=200, change_gb_day=500,
    backup_every_h=24, retention_copies=30, vault=True,
    detection=True, sensitivity=6, restore_gbps=1.0,
)
BLIND = DETECTING.model_copy(update={"detection": False, "product": "powerprotect"})
MDR_247 = ResilienceConfig(
    product="mdr", estate_tb=100, detection=True, sensitivity=6,
    response="mdr", noise_alerts_day=40, vault=True,
)
INHOUSE = MDR_247.model_copy(update={"response": "inhouse"})
ZT = ResilienceConfig(
    product="fortzero", architecture="zerotrust", assets=100,
    grants_per_user=3, microseg_segments=5, review_cadence_days=30,
)
PERIMETER = ZT.model_copy(update={"architecture": "perimeter",
                                  "microseg_segments": 1})

CONFIG_PRESETS = [
    ConfigPreset(id="vaulted", compare_preset_id="repo-only", name="PowerProtect + vault", config=VAULTED,
                 blurb="Repository plus the air-gapped, locked copy."),
    ConfigPreset(id="repo-only", name="Repository only", config=REPO_ONLY,
                 blurb="Backups without isolation — the cautionary preset."),
    ConfigPreset(id="detecting", compare_preset_id="blind", name="Cyber Detect on", config=DETECTING,
                 blurb="Content analysis naming the last clean point."),
    ConfigPreset(id="blind", name="No detection", config=BLIND,
                 blurb="Restore-and-pray — the doubled-RTO branch."),
    ConfigPreset(id="mdr", compare_preset_id="inhouse", name="MDR 24/7", config=MDR_247,
                 blurb="The response clock that doesn't sleep."),
    ConfigPreset(id="inhouse", name="In-house SOC", config=INHOUSE,
                 blurb="Capable, diurnal, and behind a queue."),
    ConfigPreset(id="zerotrust", compare_preset_id="perimeter", name="Fort Zero · zero trust", config=ZT,
                 blurb="Blast radius = the grant list, divided by segments."),
    ConfigPreset(id="perimeter", name="Fort Zero · perimeter", config=PERIMETER,
                 blurb="Inside means trusted — the flood map."),
]

# --- Guided scenarios ------------------------------------------------------

GUIDED_SCENARIOS = [
    GuidedScenario(
        id="backups-arent-enough",
        title="Backups aren't enough",
        narration=[
            L(
                novice=(
                    "Day ten: corruption begins spreading through the "
                    "estate — and through the backup repository too, "
                    "because the repository is reachable from the "
                    "systems it protects. Watch the repo-copies "
                    "counter fall to zero while the vault copies, "
                    "behind their almost-always-closed gap, hold. "
                    "Then the restore runs from the vault. Rerun on "
                    "the repository-only preset: the same incident, "
                    "and nothing left to restore from. Backups are "
                    "not the product; unreachable backups are."
                ),
                standard=(
                    "The spec's devastating-common pattern, run twice: "
                    "the incident (abstract corruption at 500 GB/h "
                    "from hour 240) marks every repository copy "
                    "corrupt, while vault copies behind the "
                    "operational air gap stay intact — the tests "
                    "assert the gap holds. Recovery proceeds from the "
                    "vault at the RTO arithmetic the validation panel "
                    "quoted. The repo-only preset ends with "
                    "recovery_succeeded = false. Isolation, not "
                    "copies, is the claim."
                ),
                expert=(
                    "Repo copies → 0 intact; vault holds "
                    "(asserted). Vault restore at quoted RTO; "
                    "repo-only run: nothing to restore. Isolation is "
                    "the product."
                ),
            ),
        ],
        question="How many intact copies existed on each side of the gap when the restore began?",
        scenario=Scenario(
            config=VAULTED, duration_h=720,
            events=[
                SimEvent(at_h=240, action="incident", value=500),
                SimEvent(at_h=280, action="contain"),
                SimEvent(at_h=290, action="attempt-restore"),
            ],
        ),
    ),
    GuidedScenario(
        id="rto-surprise",
        title="The RTO surprise",
        narration=[
            L(
                novice=(
                    "The restore works perfectly. It also takes more "
                    "than two days, because two hundred terabytes "
                    "moving through a one-gigabyte-per-second pipe "
                    "is arithmetic no vendor can negotiate with: "
                    "200,000 gigabytes ÷ 1 GB/s ≈ 56 hours, plus "
                    "the hours spent deciding and validating first. "
                    "Watch the progress bar crawl and do the "
                    "division alongside it. Recovery time is mostly "
                    "a bandwidth purchase, made — or not — years "
                    "before the incident."
                ),
                standard=(
                    "RTO decomposed live: 6 decision hours + 200 TB ÷ "
                    "1 GB/s ≈ 61.5 h. The validation panel stated it "
                    "before the run; the trace pays it out. Doubling "
                    "restore bandwidth halves the dominant term — "
                    "the cheapest RTO improvement is usually a "
                    "bigger pipe, and the sim makes that argument "
                    "quantitative."
                ),
                expert=(
                    "RTO = 6 + 200e3/1/3600 ≈ 61.5 h. The pipe is "
                    "the knob. Buy bandwidth before the incident."
                ),
            ),
        ],
        question="What fraction of the RTO was decision time, and what would 4 GB/s have saved?",
        scenario=Scenario(
            config=VAULTED, duration_h=480,
            events=[
                SimEvent(at_h=100, action="incident", value=500),
                SimEvent(at_h=110, action="contain"),
                SimEvent(at_h=120, action="attempt-restore"),
            ],
        ),
    ),
    GuidedScenario(
        id="slow-burn",
        title="Slow burn",
        narration=[
            L(
                novice=(
                    "This corruption doesn't announce itself — it "
                    "creeps at twenty gigabytes an hour for two "
                    "weeks. With content-level detection, the "
                    "scanner notices within days and names the last "
                    "clean copy; the eventual restore works the "
                    "first time. Without it, nobody knows anything "
                    "until the newest backup restores ruined, and "
                    "recovery starts over from an older copy at "
                    "double the time. Same incident, same backups — "
                    "the difference is entirely in knowing which "
                    "copy to trust."
                ),
                standard=(
                    "Low-and-slow at 20 GB/h: detection latency "
                    "doubles (the quiet signal), but sensitivity 6 "
                    "still fires within ~20 h and pins the clean "
                    "point. The blind rerun restores the newest "
                    "(corrupt) copy first and pays the failed-"
                    "restore penalty — RTO roughly doubles, the "
                    "branch the tests compare directly. Two weeks of "
                    "quiet corruption is also an RPO lesson: the "
                    "clean point is dated days before anyone acted."
                ),
                expert=(
                    "20 GB/h × 2 weeks; detect ≈ 20 h, clean point "
                    "named. Blind: corrupt-first restore, RTO ×~2 "
                    "(compared in tests). The date is old; that IS "
                    "the RPO."
                ),
            ),
        ],
        question="How much older is the named clean point than the detection moment — and what did blindness cost in RTO?",
        scenario=Scenario(
            config=DETECTING, duration_h=1080,
            events=[
                SimEvent(at_h=200, action="slow-incident", value=20),
                SimEvent(at_h=560, action="contain"),
                SimEvent(at_h=570, action="attempt-restore"),
            ],
        ),
    ),
    GuidedScenario(
        id="two-am",
        title="The 2 a.m. problem",
        narration=[
            L(
                novice=(
                    "The incident begins at two in the morning on a "
                    "Saturday — hour 122 of the simulated week. The "
                    "detector fires promptly; nobody is at a desk "
                    "until Monday at eight. Watch the blast-radius "
                    "counter integrate all weekend. Then rerun on "
                    "the MDR preset: the same detection, a 24/7 "
                    "clock, containment in minutes. The service "
                    "isn't buying better detection; it is buying "
                    "the hours between an alert and a human."
                ),
                standard=(
                    "Incident at t=50 (Saturday 02:00; the engine's "
                    "week starts Monday 00:00). In-house: detection "
                    "fires, containment waits for Monday 08:00 plus "
                    "queue drain — blast radius = rate × ~55 h. "
                    "MDR: triage in 15 minutes, radius ~three orders "
                    "smaller. Same estate, same detector; the "
                    "response clock is the entire difference, and "
                    "the tests pin the ordering."
                ),
                expert=(
                    "t=50 = Sat 02:00. In-house TTC ≈ 55 h; MDR ≈ "
                    "0.25 h. Radius ∝ TTC. The clock is the "
                    "product."
                ),
            ),
        ],
        question="What was the time-to-contain on each preset, and what did each hour cost in gigabytes?",
        scenario=Scenario(
            config=INHOUSE, duration_h=336,
            events=[SimEvent(at_h=122, action="incident", value=300)],
        ),
    ),
    GuidedScenario(
        id="alert-fatigue",
        title="Alert fatigue",
        narration=[
            L(
                novice=(
                    "The same in-house team, but now the tools cry "
                    "wolf three hundred times a day — far more than "
                    "anyone can read. Watch the queue grow through "
                    "every night and weekend, and when the real "
                    "alert arrives mid-week, it waits its turn "
                    "behind the noise. Adding alerts without adding "
                    "readers doesn't add security; it adds queue. "
                    "Tuning the noise down, or hiring a night shift, "
                    "are the only two exits."
                ),
                standard=(
                    "Noise at 300/day against 60/day of capacity, "
                    "worked business hours only: the backlog "
                    "integrates upward and the mid-week incident's "
                    "containment waits behind it (the engine gates "
                    "in-house triage on a drained queue). The "
                    "validation panel called it before the run: "
                    "alert fatigue is a queueing problem, the same "
                    "1/(1−ρ) family as every knee in this suite, "
                    "wearing a SIEM's clothes."
                ),
                expert=(
                    "300/day vs 60/day, diurnal service: backlog "
                    "diverges, TTC gated behind it. ρ > 1 in a "
                    "SIEM costume."
                ),
            ),
        ],
        question="How deep was the queue when the real alert arrived, and how long did it wait?",
        scenario=Scenario(
            config=INHOUSE.model_copy(update={"noise_alerts_day": 300}),
            duration_h=336,
            events=[SimEvent(at_h=100, action="incident", value=300)],
        ),
    ),
    GuidedScenario(
        id="stolen-laptop",
        title="One stolen laptop",
        narration=[
            L(
                novice=(
                    "One identity is marked hostile — a stolen "
                    "laptop, reduced to a flag on the map. Inside "
                    "the perimeter model, watch the reachable-asset "
                    "counter flood toward ninety percent of "
                    "everything, because inside means trusted. Rerun "
                    "under zero trust: the same theft reaches only "
                    "what that one identity was explicitly granted, "
                    "divided further by segmentation — single "
                    "digits. The cost meter is honest too: every "
                    "session now clears nine checks instead of one. "
                    "Security bought with friction, priced on two "
                    "gauges."
                ),
                standard=(
                    "The compromise event under both architectures: "
                    "perimeter floods to ~0.9 × assets (hop rate 8/h "
                    "— an abstract reachability flood, no technique); "
                    "zero trust caps at grants ÷ segments + stale-"
                    "grant decay. The friction meter (9 vs 1 checks "
                    "per session) keeps the argument honest, and the "
                    "no-review preset shows the radius quietly "
                    "regrowing — least-privilege decay, prunable by "
                    "the access-review event. The DellFortZero twin "
                    "argues this; here it is counted."
                ),
                expert=(
                    "Perimeter: → 0.9N. ZT: grants/segments + decay. "
                    "Friction 9 vs 1. Review prunes. Counted, not "
                    "argued."
                ),
            ),
        ],
        question="What did the flood reach under each architecture, and what does a session cost in checks?",
        scenario=Scenario(
            config=PERIMETER, duration_h=336,
            events=[SimEvent(at_h=100, action="compromise")],
        ),
    ),
]

# --- Explain-mode entries --------------------------------------------------

EXPLAINS = [
    Explain(
        id="rpo",
        title="RPO — the last clean point",
        equation="RPO = now − newest intact copy (schedule + detection delay)",
        inputs=["backup cadence", "corruption onset", "clean copies", "RPO"],
        explanation=L(
            novice=(
                "How much work would vanish if you restored right "
                "now? That is the age of the newest copy you can "
                "trust. Backing up nightly makes the best case one "
                "day; quiet corruption makes it worse, because "
                "copies taken after the onset are worthless even "
                "though they exist."
            ),
            standard=(
                "The gauge tracks the newest *intact* copy, which "
                "is the honest definition: cadence sets the floor, "
                "detection latency sets how much history the "
                "incident silently poisons. The slow-burn scenario "
                "is this equation's worst case — weeks of retained, "
                "worthless copies."
            ),
            expert=(
                "RPO = age(newest clean), not age(newest). Cadence "
                "floors it; dwell time poisons it."
            ),
        ),
    ),
    Explain(
        id="rto",
        title="RTO — decision plus bandwidth",
        equation="RTO = decision hours + TB × 1000 ÷ (GB/s × 3600), ×~2 if the first restore is corrupt",
        inputs=["estate TB", "restore throughput", "decision time", "RTO"],
        explanation=L(
            novice=(
                "Recovery time is mostly moving bytes: two hundred "
                "terabytes through one gigabyte per second is "
                "fifty-six hours before anyone celebrates. Add the "
                "meeting where someone decides which copy to use — "
                "and if that copy turns out corrupt, start again "
                "from an older one. The pipe was sized years before "
                "the bad day."
            ),
            standard=(
                "The two terms the spec names, plus the branch "
                "detection removes: a corrupt first restore pays the "
                "failed-restore penalty and a second full pass. "
                "Restore bandwidth dominates at scale, which makes "
                "RTO primarily a procurement decision — the "
                "validation panel computes it before any incident "
                "exists."
            ),
            expert=(
                "decide + TB/BW (+ retry on corrupt-first). BW "
                "dominates; buy the pipe in peacetime."
            ),
        ),
    ),
    Explain(
        id="blast",
        title="Blast radius",
        equation="blast = spread rate × time-to-contain  (or reachable assets, Fort Zero)",
        inputs=["spread rate", "detection", "response clock", "radius"],
        explanation=L(
            novice=(
                "Damage is a rectangle: how fast it spreads, times "
                "how long nobody stops it. Detection shortens one "
                "side, a faster response clock the other. The "
                "access-graph version counts what a stolen identity "
                "can reach instead — same rectangle, different "
                "units."
            ),
            standard=(
                "The integral the MDR mode exists to shrink: rate × "
                "TTC, where TTC = detection latency + queue wait + "
                "triage, and the queue term is diurnal for in-house "
                "teams. Fort Zero's radius is the graph version — "
                "reachable set, capped by architecture rather than "
                "by clocks."
            ),
            expert=(
                "∫rate dt over TTC; TTC = detect + queue(t) + "
                "triage. Graph mode: |reachable|, architecture-"
                "capped."
            ),
        ),
    ),
    Explain(
        id="roc",
        title="The sensitivity trade",
        equation="detection latency ∝ 1/sensitivity;  false alarms ∝ sensitivity",
        inputs=["sensitivity", "latency", "false alarms", "investigation hours"],
        explanation=L(
            novice=(
                "Turn the detector up and it notices trouble sooner "
                "— and cries wolf more often, and every false cry "
                "costs an afternoon of checking. Turn it down and "
                "the afternoons return, paid for in later "
                "discovery. There is no setting that costs nothing; "
                "tuning is choosing which bill to pay."
            ),
            standard=(
                "The classic ROC trade as one slider: latency = "
                "base ÷ sensitivity, false alarms = rate × "
                "sensitivity at 3 h each. PhysicsData's anomaly "
                "detector carries the same knob deliberately — the "
                "spec notes the rhyme — because every detector in "
                "every domain is this trade wearing different "
                "units."
            ),
            expert=(
                "latency ∝ 1/s, FP ∝ s. Same knob as the AIOps "
                "detector — the rhyme is intentional."
            ),
        ),
    ),
]
