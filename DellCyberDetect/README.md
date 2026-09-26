# DellCyberDetect — ransomware-detection digital twin (seventeenth component)

A digital twin of **Dell Cyber Detect** — machine-learning ransomware
detection that runs directly against snapshots on primary storage,
inspecting data at the **byte level** rather than reasoning about metadata,
file activity, or known signatures. Content analysis by Index Engines
(CyberSense); Dell puts accuracy at 99.99% — a vendor claim resting on a
June 2024 ESG report commissioned by Index Engines — trained on 7,500+
ransomware variants. Sold as Cyber Detect for Storage: PowerStore announced
for Q3 2026 and listed as supported, PowerMax planned for 2H 2026. The
vault-side CyberSense offering is now named Cyber Detect for PowerProtect.

The companion to this repo's PowerProtect twin, which models the isolated
vault. That twin answers "will a copy survive?"; this one answers the
question isolation leaves open — **which copy?**

## The one idea

**It reads the data, not the metadata.**

Nearly every ransomware defence watches descriptions of data rather than
data. Did extensions change? Did entropy spike? Was there a mass rename? Is
the I/O rate unusual? Those are cheap to measure and they worked well for
years, which is exactly why attackers stopped triggering them: encrypt
slowly, preserve extensions, raise entropy gradually, imitate the I/O
profile of a busy Tuesday. Every one of those choices costs the attacker
time and they make it anyway. Metadata is a description the adversary also
controls.

What the adversary cannot control is whether a file still means anything.
So the analysis opens files and database pages inside each snapshot and
reads the bytes.

The second half matters as much. The output is not an alert — by the time
anyone runs this, being under attack is not news. The output is a **date**:
*snapshot 3, taken Tuesday 03:00, is the last copy whose contents are
provably intact*. Without that, the options are the newest copy, which
reinstates the attack, or something far enough back to feel safe, which
discards weeks of legitimate work. The gap between those two is usually the
largest single number in the incident's cost.

`metadataAlerts` is zero throughout — including while four snapshots are
being ruined — and `test_engine.py` asserts it.

## What it shows

- **The incident** (`/`) — six days of a real attack shape: a quiet
  intrusion, corruption deliberately built to keep detectors silent, the
  blind step where four snapshots are ruined and nothing has noticed,
  content inspection, classification, the verdict, and a recovery from the
  named copy.
- **Inside the detection** (`/#anatomy`) — unlike the other maps in this
  repo, the middle band is an axis of *time*: seven snapshots, oldest to
  newest, with the analysis machinery below and the verdict below that.
- **Components & options** (`/#components`) — where detection runs,
  detection method, the trained model, what the analysis produces, snapshot
  and retention policy, immutability and isolation, estate coverage,
  operations.
- **Use cases** (`/#usecases`) — a manufacturer choosing between last night
  and last month, a bank that has to prove when it started, and a hospital
  that cannot go back a month.

## The interaction worth seeing

Pause on the **detectors silent** step. Every snapshot on the timeline is
drawn identically, because at that moment they genuinely are
indistinguishable — four of them are ruined and nothing visible from
outside says which. That is the position an administrator is actually in.
The copies only turn red once the analysis has read the bytes inside them.
`TimelineView.tsx` takes a `revealed` prop for exactly this reason: marking
corruption early would quietly undo the whole lesson.

## Failure scenario: dwell time exceeds retention

The baseline incident ends well: three clean snapshots are still on the
array and the analysis names the newest of them. The second scenario
(`GET /api/detect?scenario=dwell-exceeds-retention`, listed by
`GET /api/scenarios`, deep link `#scenario=dwell-exceeds-retention`, which
composes as `#scenario=dwell-exceeds-retention&phase=verdict`) is the one
where that does not happen.

The array keeps seven daily snapshots. The attacker corrupts slowly for
longer than seven days, and the retention policy deletes the last clean
copy on schedule, working as designed. When content inspection finally
runs, it reads and scores all seven copies exactly as in the baseline and
reports that none is clean. `lastCleanSnapshot` stays `-1` for the whole
trace and `verdict` is `no-clean-copy-on-array`. The product does not fall
back to the least-damaged copy, because certifying a corrupted copy is the
error it exists to prevent. Recovery then comes from the PowerProtect Cyber
Recovery vault (the `DellPowerProtect/` twin): `recoverySource` is
`powerprotect-vault`, no array snapshot takes part, and the restored data
is about 310 hours old against 134 in the baseline.

The vault holds backup copies replicated from a production Data Domain, not
array snapshots, and recovery runs through a recovery host inside the vault.
The scenario therefore assumes two things and says so in the step prose: the
volume was in the backup set, and the vault keeps copies for longer than the
attacker waited. Where either is false, the recover step has no good version.

The state model is extended additively (`snapshotsExpired`, `verdict`,
`recoverySource`, `recoveryPointAgeHours`, `failedRegions`). The trace lives
in `backend/app/scenarios.py`, which is held to the same purity rule as the
engine. `backend/tests/test_scenarios.py` pins the signature invariants:
no corrupted copy is ever certified clean, in any scenario; confidence
still comes only from content; inspection is still the longest stage;
recovery names an off-array source; the recovery point is strictly worse
than the baseline's; and every pre-existing field of the baseline trace
hashes to the value it had before this work.

What is sourced: the per-copy Good / Suspicious / Partial results and the
alert on Suspicious (Dell Cyber Recovery product guide), last-known-clean
identification with forensic reports and impacted-file lists (Index
Engines), and the vault architecture (Dell H18661). Neither vendor
publishes a worked "every copy is suspicious" walkthrough, so the sequence
is this twin's reading of those behaviours. The seven-day window, hours and
counts are illustrative. Most ransomware dwell times are days, not weeks
(Mandiant M-Trends 2025); this is the patient tail. The guided tour stays
on the baseline incident.

## Run

```
./DellCyberDetect/scripts/start_all.sh   # backend :8019, frontend :5192
./DellCyberDetect/scripts/stop_all.sh
```

`start_all.sh` creates the backend venv, installs dependencies, starts
uvicorn in the background (logs to `logs/backend.log`), and runs Vite in the
foreground — Ctrl-C stops both. Then open <http://localhost:5192>.

Backend tests: `cd backend && . .venv/bin/activate && python -m pytest -q`
Frontend build: `cd frontend && npm run build`

Vite proxies `/api` → `http://localhost:8019`. If that port is taken, run
the backend elsewhere and point Vite at it:
`API_TARGET=http://localhost:8119 npm run dev`.

Trace endpoint is `GET /api/detect`, returning `DetectResponse`;
`/api/anatomy`, `/api/catalog`, and `/api/usecases` follow the same shape as
the other twins.

## Key invariants (backend/tests/)

- Engine purity (AST-checked); the playback clock lives in `App.tsx`.
- Phase order
  `clean→intrusion→encrypt→blind→inspect→classify→verdict→recover→restored`
  never regresses.
- **Metadata detection is blind while corruption spreads** — during the
  corruption phases, `snapshotsCorrupted > 0` *and* `metadataAlerts == 0`.
  Both halves are asserted: silence proves nothing unless damage is
  demonstrably happening. The defining property.
- **Confidence comes only from reading content** — zero until the
  inspection stage has run, ≥99 once the classifier has scored it. There is
  no shortcut to certainty.
- **The deliverable is a date, not an alert** — `lastCleanSnapshot` is `-1`
  for every step before the verdict, and names a real snapshot after it.
- **The named copy is actually clean** — it must be strictly older than the
  first corrupted snapshot. This is the one way the product can genuinely
  fail a customer: a false negative is somebody restoring the attack from a
  copy that was certified safe.
- **No verdict without evidence** — the verdict region never lights before
  the inspection region has.
- **Corruption only grows until it is repaired**; snapshots are never lost.
- **Recovery uses the copy the verdict named** — not the newest, not an
  over-cautious ancient one.
- **Content inspection is the longest stage** (unique max `cycleCost`) —
  reading every byte is expensive, and that expense is the product.
- Geometry carries the lesson: snapshots are uniformly sized, on one row,
  in chronological order (`test_the_middle_band_is_a_timeline`); evidence
  is drawn above conclusion (`test_evidence_sits_above_conclusion`); and
  the analysis band sits beneath the timeline it reads.

## Honesty notes

- Seven snapshots and a six-day incident are illustrative. Real dwell times
  are routinely measured in weeks, which is the uncomfortable arithmetic
  the retention catalog entry raises: if dwell time exceeds retention,
  every surviving copy is corrupt and there is nothing for the analysis to
  find.
- Counts, confidences, and timings are illustrative but plausible; favor a
  correct mental model over measured numbers (project scope guardrail). The
  99.99% figure is Dell's own (from an ESG report commissioned by Index
  Engines, June 2024, "actual results may vary") and is labelled as such.
- Dell has announced Cyber Detect for PowerStore, PowerMax, and the
  PowerProtect Cyber Recovery vault. The catalog's file/object (PowerScale)
  and backup-appliance placements are illustrative and say so.
- The only shipped visual is `frontend/public/cyberdetect-timeline.svg`, a
  self-contained schematic drawn for this project with an honest credit
  line — not a Dell product image.

## Sources

- [Dell Cyber Detect — product page](https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/cyber-detect)
- [Dell — faster, more confident recovery starts on primary storage](https://www.dell.com/en-us/blog/faster-more-confident-recovery-starts-on-primary-storage/)
- [Dell Technologies reimagines the modern data center for the AI era (May 2026)](https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm)
- [Index Engines — Dell Cyber Detect, powered by CyberSense](https://indexengines.com/products/dell-cyber-detect/)
- [Dell PowerMax cybersecurity — security and compliance](https://infohub.delltechnologies.com/en-us/l/dell-powermax-cybersecurity-3/security-and-compliance-9/)
