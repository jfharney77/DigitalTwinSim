# Student findings — taking the course as a reader

`Learn/` is written for people who have never seen these twins. The only way to
find out whether it works is to sit the course: open each page, answer its
prediction before running anything, follow every link into a twin that is
actually running, and check whether the page's claims survive contact with the
screen. Two cohorts have now done that. This file records how it was done, what
it found, what changed, what was refused, and what it would take to do again.
It was written on 2026-09-24, in the verification pass that closed the second
cohort's last findings.

Numbers here describe the course and the review, not hardware. Twin numbers
stay illustrative unless a twin sources them.

## 1. What was reviewed

| | |
|---|---|
| Pages | 19 — twelve spine modules (M1–M12) and seven electives (E1–E7) |
| Predictions | 19, one per page, answered before the trace runs |
| Checks | 57, each citing a pytest id or a screen |
| Twin entries | 40, carrying 84 deep links (tour beat, phase, step, scenario, lesson) |
| Twins referenced | 38 of the repo's components |
| Tracks | 9, from `full` to `executive-overview` and `what-goes-wrong` |

`Learn/course.js` is the source of truth. `Learn/modules/*.html` is generated
from it by `Learn/scripts/gen_pages.py`; editing the HTML is a mistake the
`--check` mode catches.

## 2. Method

**Three personas, one course.** Each page is read three times: a newcomer at
reading level 1, a practitioner at level 3, and a sceptical expert at level 5.
The personas are not a flourish — most of what both cohorts found is invisible
at level 3 and obvious at level 1 or 5. A level-1 reader meets undefined jargon;
a level-5 reader catches an overclaim or arithmetic that does not divide.

**In a browser, against running twins.** A reviewer starts the twin the page
links to (`scripts/dev.sh <Component>`), follows the link, reads the number off
the screen, and stops the twin afterwards. A page's claim is not confirmed by
reading the engine; it is confirmed by seeing it on the screen the reader is
sent to. Reviewers leave other people's servers alone and say in their report
which processes they started and stopped.

**Predict, then play.** The prediction is answered from the page alone, before
the twin runs. The score matters less than the misses: a prediction the page
gave away and a prediction the page made underivable are both defects, and they
look the same on a tally until you read why the answer was chosen.

**The report is per module, and says what it could not fix.** Findings that
belong to another module, another twin, or a shared file are reported, not
edited — one reviewer per module, one working tree, and a shared file touched by
two reviewers at once is how `course.js` briefly became invalid JSON twice
during cohort two.

## 3. Cohorts

| Cohort | Date | Scope | Outcome |
|---|---|---|---|
| First | 2026-09-19 | All 19 pages, three personas | Six clusters, each turned into a rule the tests now hold (`docs/COURSE_DESIGN.md` §11) |
| Second | 2026-09-22 | All 19 pages, three personas, re-reading the first cohort's fixes | Predictions right **174 of 191**; the first cohort's fixes confirmed resolved; a smaller, more specific set of remaining findings, mostly arithmetic and register |

**Limit of this record.** The second cohort's per-module reports live in the run
transcripts; what reached this file is the aggregate prediction score and the
module reports for M1 and M2 in full. The taxonomy below is therefore accurate
about *kinds* and about everything it names, and is not a complete per-module
tally. A third cohort should write its per-module counts into this file as it
goes rather than at the end.

## 4. Findings by kind

| Kind | What it looks like | Example |
|---|---|---|
| Arithmetic that does not divide | A caption states a rate the on-screen numbers do not produce | M1's tour caption gave 244 GB/s as read "off the counters"; the footprint is the lesson's own constant, and 0.537 GB ÷ 2.20 ms is where 244 comes from |
| Pointing at a label that does not exist | A how-to names a control or a line by a name the UI never shows | M1 sent the reader to a Roofline line called "your die, measured"; the line is labelled *last bandwidth measurement* |
| Unleveled prose | Part of a page does not change with the reading level | Cohort one: objectives, options, checks, link lines. Cohort two: info dots inside the twins (ridge point, arithmetic intensity, run controls) |
| Undefined jargon | A term used before it is glossed, usually at level 1 | "kernel" in M1's standard register; POST as a bare acronym in the R760's phase label |
| Evidence not on the linked screen | A check cannot be answered from where the link lands | M1's check 2 (load vs compute cycles) had no link that showed those lines |
| Prediction given away or underivable | The title, lede, objective or a locked link label settles the answer — or nothing on the page does | Cohort one replaced three predictions; cohort two added `lockedLabel` to M2's failure stop |
| Overclaim | A true-ish sentence that is false as stated | M1's "not a property of the chip"; M2's "cannot be skipped"; M5's "share that leaves through the liquid" |
| Unflagged toy-scale number | An absolute value that is an artefact of the model | M1's 18 joules per MAC, ~13 orders of magnitude off real silicon |
| Twin-side copy over-claiming | The twin says something stronger than it does | The R760's playback caption claims dwell is *proportional* to the printed seconds; dwell is a small ranked weight (8 s → 2 ticks, 110 s → 6) |
| Cross-twin disagreement | Two twins drawn separately quote different illustrative numbers for one thing | R760 and iDRAC standby watts; IR7000 and PhysicsCDU flows |
| Stale or ambiguous liveness | The page says a twin is running when the link will 404 | A GPU backend started before `/api/tour/recording` existed answered the ping and failed the link |

## 5. What was fixed

**Cohort one — six clusters, six rules.** Each is now a test in
`Learn/tests/test_links.py`, so the finding cannot come back silently:

- Everything is authored in both registers — `test_a_novice_reader_meets_no_unleveled_prose`.
- Answers quote the screen, not the engine: on-screen step numbering, UI phase
  labels, displayed values with a test's bound named as a bound.
- Predictions do not give themselves away: `lockedLabel` holds a neutral label
  until the reader commits.
- Every check has a link that sets up its evidence, and every physics-app link
  carries a `how` naming the control, the instrument and the moment to read.
- Modules with several twins bridge between them —
  `test_modules_with_several_twins_bridge_between_them`.
- Quoted scenario figures are read through the app's own routes —
  `scenarioPins` and `test_scenario_quoted_numbers`.

Plus `pageTitle` on every entry, so the liveness chip can tell "something
answers on 5173" from "the GPU twin answers on 5173"
(`test_entries_know_their_twin_by_its_page_title`).

**Cohort two — narrower, mostly numbers and register.** In the twins: M1's tour
caption rewritten at all five registers with the arithmetic shown and the
footprint attributed; the GPU info dots leveled; the "4 MACs per cycle" versus
"128 drawn lanes" apparent contradiction reconciled in the ridge-point dot; the
joules-per-MAC dot flagged as toy-scale; the iDRAC and R760 block descriptions
and map labels leveled; the R760's longest-step marker added; R760 cycle costs
re-ranked so dwell order follows the printed seconds; the bootable-image counter
explained where it reads wrong. In `Learn/course.js`: the M1 lesson-tour how-to
rewritten to the real arithmetic and the real label, "kernel" and MAC glossed,
M1's check 2 given its evidence link, the quantization reveal corrected (lower
precision moves the kernel *further* below the ridge, demonstrated in tensor
mode), M2's objective quoted word for word from the twin, M2's watts attached to
the phase names the screen shows, M2's failure stop given a neutral label and a
`how` that lands on the step carrying the message sequence, and its provenance
labelled as published for an iDRAC10 case.

Also fixed in this pass, from the same reports: `pageTitle` on M5's two entries
(`DellIR7000`, `PhysicsCDU`), the last modules the new test was failing on.

## 6. What the reviewers reported rather than fixed

Reviewers own a module, not the repo, so three findings were reported instead of
edited. All three were real, and the verification pass closed three of them:

- **The five reading-level buttons over two authored registers.**
  `CustomerSetup/shared/setup.js` renders the twins' five named registers, but
  the Learn and CustomerSetup pages author two (1–2 novice, 3–5 standard), so a
  reader who clicks Expert sees nothing change and the only disclosure was a
  hover tooltip — invisible on touch. **Closed:** the control now carries a
  visible line saying which registers read alike here and that the twins
  distinguish all five. Authoring the course at five registers remains a
  course-wide decision nobody has taken.
- **The R760's playback caption.** "Holds each step on screen in proportion to
  the seconds the counter prints" over-claims: dwell is `cycleCost`, a ranked
  weight (8 s → 2 ticks, 110 s → 6). **Closed:** the caption and the Telemetry
  caveat now say the dwell is a rank, not a scale. Making dwell track the
  duration was not done — it would change every twin's playback feel for one
  sentence's sake.
- **`LessonTour.tsx`'s hardcoded "the 244 GB/s worked out in the caption".**
  True today, silently wrong if the lesson's recording or footprint changes.
  **Closed:** the note now points at the caption's figure without repeating it,
  so the number lives in one place (`GPU/backend/app/tour.py`).

Still open, and deliberately:

- **The liveness chip only pings the port.** A twin whose deep-linked page 404s
  still advertises "running" — as happened in cohort two, where a GPU backend
  started before `/api/tour/recording` existed answered the ping and failed the
  link. `learn.js`'s `checkIdentity` already fetches the answering page's title;
  extending it to fetch one endpoint the links depend on would catch the stale
  backend too. Left open because it is a change to how every chip on every page
  decides what "running" means, which deserves its own pass rather than a
  reviewer's patch.

Nothing was declined as "not a real finding".

## 7. Repeating the exercise

1. Start clean: stop dev servers left over from earlier runs (check `cwd` under
   the repo before killing anything — the machine runs other projects), and
   serve the course from the repo root on :5172.
2. Assign one reviewer per module. Give each the three personas and the rule
   that shared files (`Learn/course.js`, `CustomerSetup/shared/*`,
   `packages/twin-ui`) are reported unless the module owns the line.
3. For each page: answer the prediction from the page alone; then start the
   twins it links to, follow every link at level 1 and at level 5, and read each
   quoted number off the screen.
4. Record per module: predictions right, findings by kind, what was fixed, what
   was reported on. Write the tally into this file as you go.
5. Finish with `python3 Learn/scripts/gen_pages.py --check`, `pytest Learn`, and
   `pytest` at the repo root; stop every server you started.

The rule that made both cohorts worth the time: a finding is not "the page is
confusing", it is "this sentence says X, the screen says Y". Everything in §4
has that shape.
