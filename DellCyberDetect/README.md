# DellCyberDetect — ransomware-detection digital twin (seventeenth component)

A digital twin of **Dell Cyber Detect** — machine-learning ransomware
detection that runs directly against snapshots on primary storage,
inspecting data at the **byte level** rather than reasoning about metadata,
file activity, or known signatures. Content analysis by Index Engines;
Dell puts accuracy at 99.99%, trained across thousands of variants.
Available for PowerStore in Q3 2026 and PowerMax in 2H 2026.

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
  99.99% figure is Dell's own and is labelled as such.
- The only shipped visual is `frontend/public/cyberdetect-timeline.svg`, a
  self-contained schematic drawn for this project with an honest credit
  line — not a Dell product image.

## Sources

- [Dell Cyber Detect — product page](https://www.dell.com/en-us/shop/storage-servers-and-networking-for-business/sf/cyber-detect)
- [Dell — faster, more confident recovery starts on primary storage](https://www.dell.com/en-us/blog/faster-more-confident-recovery-starts-on-primary-storage/)
- [Dell Technologies reimagines the modern data center for the AI era (May 2026)](https://www.dell.com/en-us/dt/corporate/newsroom/announcements/detailpage.press-releases~usa~2026~05~dell-technologies-reimagines-the-modern-data-center-for-the-ai-era.htm)
- [Dell PowerMax cybersecurity — security and compliance](https://infohub.delltechnologies.com/en-us/l/dell-powermax-cybersecurity-3/security-and-compliance-9/)
