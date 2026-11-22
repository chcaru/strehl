# Capture in flight: owner feedback after a full run (g-flight)

**Date:** 2026-11-21. **Branch:** `studio2/g-flight`, from main `7f83d3f22`; code
commit `e7840e26f`. **Scope:** the Capture station while a stack
is captured (the flight view), its rail, glance mode and the "Show" view, from
the owner's run-through. Files: `capture-flight.rs`, `capture-follow.rs`,
`capture-station.rs`, `capture-rail.rs`, `capture-style.rs`,
`capture-glance.rs`, `capture-fixture.rs`, `draft-preview.rs` (the proof's
run tail), `capture-workspace.rs` and `activity.rs` (one line each:
the eased time left, the checks' summary), `app-station-capture.rs` (Show
takes a try's RAW), `main.rs` (fixture names), their `-tests.rs` siblings,
`visual-check.py`; in the host crate only `MAX_RETAKES` became `pub` (no
behaviour change, no Pi redeploy). **Labels:** MEASURED, VERIFIED, DERIVED,
ARGUED, UNVERIFIED.

## The owner's words (verbatim)

on the Capture screen -> Stack -> while stacking:
- the timeline should auto-fit.
- the progress tracker at the top: the "Plane _ of _" the number's baselines
  aren't aligned. specifically, the first number floated above the correct
  baseline. / the timings for "LEFT" kept changing and shifted the progress
  bar every tick. this shouldn't happen. / would be good to have special
  treatment for retakes, how it impacted the progress vs original, otherwise
  changing time and "X of Y RAWs taken" gets confusing when X becomes larger
  than Y.
- the "proof so far" image size isn't correct -- it takes about half
  vertically that itt could. also it didn't change? seems broken overall? /
  when click "Show" on an activity item. this changes and fills the screen,
  but it clips the text at the top, not usable.
- in the "last planes" feed: "retaken, the second try passed" was pinned to
  the bottom of the feed for the entire stack... until another retake, which
  was then the pinned item. / i saw "offsets [...] do not cover" outside
  bounds... it didn't try to retake these at all... i would suspect it
  should? same for witness pairs misregistered..? not sure which should be
  retaken and not. / ok, maybe these are fine to not retake? when done
  stacking at the end, i think it's telling me that everything got worked
  out? it would be good to make it more clear what is going on. / can the
  activity feed here fill the screen vertically for it's area? and be
  scrollable? this way no pinning is needed. it would also be good to
  differentiate failed from retake, showing as separate items with different
  statuses. / the activity feed items were truncated a lot. should they
  newline?

## What the owner's run shows

Read only: `D:\StrehlCaptures\stack-1795300522964-6430` (`manifest.json`,
`events.jsonl`, `transfer-receipts.jsonl`, `result.json`), its checker
journal `%LOCALAPPDATA%\strehl\warpmaps\follow\stack-1795300522964-6430-264d33686dc89740.jsonl`,
the render's `render.log` and `activities.json`; copies in
`C:\strehl-scratch\g-flight` (scratch, not in Git).

| Fact | Value | Label |
| --- | --- | --- |
| Planned | 211 planes, 844 RAWs (four-shot), step 7, settle 2000 ms, error correction on | MEASURED (manifest) |
| Captured | 260 groups, 1,040 RAWs: 49 retakes of 34 planes | MEASURED (events: 260 `capture_buffered`, 49 `retake_intent`, 7 `retake_exhausted`) |
| Journal | 260 lines in the checker's order; a plane's retake follows the next plane (plane 3's retake after plane 4) | MEASURED |
| Outcomes | 159 passed first try; 34 retaken: 25 then passed, 9 failed every try (7 after two retakes on "witness tiles disagree", 2 whose retake then failed the shift-pattern check); 18 failed and not retaken (15 shift pattern, 3 residual misregistration) | MEASURED (journal) |
| Stacked from one shot | 27 planes; the render's log demotes exactly 27 distinct frames "to member 1" | VERIFIED (grep of `render.log`) |
| Time | a plane 5.69 s (median, focus intent to buffered); a retake 10.08-10.31 s (median 10.19 s, 49 retakes); run 1,720 s, about 499 s of it retakes | MEASURED (events) |

## Root causes

| Symptom | Cause | Label |
| --- | --- | --- |
| Plane number above the "of N" baseline | Both texts were anchored by the bottom of their galleys (`LEFT_BOTTOM`, the small one 4 px higher); a galley's bottom is its baseline plus the font's descent, which grows with the size, so the 64 px figures stood higher than the 20 px text | VERIFIED (test: baselines now within 0.6 px) |
| LEFT shifting the bar every tick | The bar ran from the plane block to the LEFT text's left edge; LEFT was laid out right of ENDS, both in proportional figures whose width changes with the digits, so each second moved the bar; and the host's estimate itself jumps when a plane's pace changes (`RunTiming::remaining`: cycle × planes left, re-averaged after every plane, a retake lengthening the plane) | VERIFIED (test: edges fixed across five values of LEFT) |
| "X of Y RAWs" with X > Y | Taken was the host's `captured_frames` (retakes included, 1,040) over planned planes × shots (844) | VERIFIED (owner's numbers) |
| Proof half the height | The proof's rectangle was capped at 620 px tall (`top + 620`) and filled "cover" | VERIFIED (code; test now fits it whole) |
| Proof label and planes | The proof's run tail took every fourth RAW as a new plane (`(ordinal - 1) / shots`), so each retake was offered as an extra plane out of focus order and the label counted groups ("planes 1–260" for 211) | VERIFIED (test with the owner's order; scratch run: 56 offered before, 55 planes after) |
| Proof "didn't change" | Not reproduced. On a scratch copy of 108 of the owner's RAWs, the proof job and the station's own path (`poll_station`, the texture) updated 13 times over 55 planes; composites go from blurry to sharp (images in scratch). A failed update was silent (kept, never shown): now shown in the proof's caption. The early composites differ little (planes 1-14 look alike at that size) | MEASURED / UNVERIFIED for the owner's session |
| Show clipped at the top | The pinned RAW's caption and Back button were drawn above the photo rectangle (`photo.left_top() - 8`, `right_top() - 30`), outside the canvas when the photo filled it | VERIFIED (render) |
| A retaken plane pinned at the bottom | By design: `recent_planes` kept the newest retaken plane in the fifth row "so Show stays in reach" | VERIFIED (code) |
| Truncated feed text | Each row's text had `max_rows = 1` in a 234 px column | VERIFIED (code) |
| The rail not fitting | In flight the fit took in the survey and the lens, and a view zoomed while planning stayed zoomed | VERIFIED (code; test) |

## What was built

| Item | What |
| --- | --- |
| Auto-fit | In flight the rail fits the stack being captured (its planned planes and bounds, a tenth of padding); the survey and the lens (which goes below a plane to retake it) no longer move the fit. Entering (or leaving) flight lets a planning zoom go; a wheel or pan in flight holds the user's view until Fit. A narrow rail (1280 px window) shortens its legend so it clears the scale. |
| Baselines | `style::paint_on_baseline` and `style::baseline` (the first glyph's baseline in a galley): the 64 px plane and the 20 px "of 96" share one baseline. |
| Fixed figures | `style::figures`/`paint_figures`: digits in cells of the widest digit (one section a character, the padding as leading space), so a changing number keeps its width. The plane's slot is the total's digit count wide; LEFT's slot is "00:00" or "0:00:00" wide; ENDS "00:00". The bar is laid out between fixed slots. |
| Eased time left | `LeftClock`: counts down by the second, eases to the host's estimate (time constant 20 s), takes a change of more than a quarter (at least 90 s) at once, holds while paused; the flight headline, glance, the top bar's capture activity and the status line show the same value. Redraws every 250 ms while capturing. |
| Retakes | Row 2 under the bar: "272 RAWs taken · 24 for retakes" (never "X of Y"); at the right, in the warning colour, "▲ 6 retakes of 4 planes · +61 s". The pace is the plain plane's ("5.7 s a plane"). `RetakeClock` measures the cost from the host's counts: between two planes finished, the time beyond the plain pace (median of the last 31 intervals without a retake) whenever more groups than planes were captured; after the last plane all the time is the retakes'; retakes not seen (desktop started mid-run) at the measured average; none shown before one was timed. Glance: "Plane 61 of 96 · 6 retakes". Disk: written of about the planned RAWs plus the retakes' (never past the whole). |
| Proof | Fills the space beside the side column, fitted whole (aspect kept), its caption on the picture; the side column is a quarter of the canvas (340-460 px). The run tail knows each RAW's plane from the capture journal's bindings (`events.jsonl`: `capture_buffered`/`capture_complete` files carry `name` and `plane`): a retake is not a new plane; a RAW waits for its binding; without bindings (an older host) it falls back to every `shots` RAWs. The label says "planes 1–N" (and "one in k" when thinned). A failed update shows in the caption ("its last update failed: …"). |
| Show | A head row inside the canvas: "Plane 52 · frame-000213.ARW", a wrapped sentence, Back to the capture at the right; the picture fitted below. Show asks for that try's RAW (`ShowPlane { plane, raw }`); the Stack station is used when the stack holds it (only a plane's last try is a stack frame). |
| Feed | `Progress::feed`: every checked group in the checker's order, a plane's first try and each retake separate items (`FeedItem`: plane, try, verdict, retake asked, reason, first RAW, the distance to the plane's next try); `Tally`: each plane's outcome (first try, retake passed, retake failed, not retaken, retake asked, incomplete), kept line by line. The column fills its height and scrolls (wheel and bar; a press is for Show, not a drag), newest at the top, followed at the top; scrolled down, rows in view stay put as new ones arrive above (the offset grows by what was added). Only rows in view are laid out: heights by kind (one line 30 px, two 48, three 64), positions cached and extended as the feed grows, a binary search for the rows in view. |
| Statuses | First try passed: one line, its check time. Retake passed: "Retake passed · try 2", PASSED. Failed with a retake to come: RETAKING, "Taking it again (try 2 of 3)." Failed and retaken: RETAKEN, "Retaken: try 2 passed." / "failed too." Failed with no retake: ONE SHOT (the stack folds it to its first shot), with why in a few words ("Not retaken, by the checker's rule.", "…the shots are not at fault.", "Failed 3 tries; no retakes left.", "…error correction is off.", "…the capture ended."). Each row's hover gives the whole story, the policy and the engine's own reason. Text wraps (two lines); every combination fits at the narrowest column (test). |
| Counts | Above the feed: "● 159 first try ● 25 after a retake ▲ retaking ◆ 27 one shot". Health "Checks": "211 planes checked · 159 passed first time · 34 retaken (25 then passed) · 27 stacked from one shot"; the checker's activity in the same words. |
| Review | A capture this desktop watched that completes (or is stopped) stays in the flight view until Back to planning (or the next capture); not a test shot or a survey. LEFT/ENDS become TOOK/ENDED; the state reads Finished; the feed opens with the summary in words and each failure kind with its tries and its policy, scrolling with the rows. |
| Fixtures | `--capture-fixture flight` now has the owner's kinds of failure (a retake passing, one failing every try, shift pattern and correction failures not retaken, a retake pending); `flight+long` (5,400 of 6,000 planes, 281 retakes of 255 planes); `flight+done` (the review); `flight+show`. `visual-check.py` routes for them and Instrument/Lightbox. |

## The retake policy, as found (not changed)

The checker (`strehl follow`, `crates/strehl-cli/src/follow-cmd.rs`) writes
`retake: true` only when `pixel_shift_cmd::retake_helps` says a retake could
pass (`pixel-shift-cmd.rs` `demotion`); the host (`crates/strehl-capture/src/worker.rs`)
takes a group asking for one again after the next plane, through the approach
move, at most `MAX_RETAKES` = 2 times, then keeps it (`retake_exhausted`); a
check unanswered for 15 s turns error correction off for the run. The plane's
last group is the one the stack uses; a demoted group is folded to its first
shot ("demoted to member 1"), so every plane stays in the stack.

| Failure (engine reason) | Retaken | The engine's reason | Owner's run |
| --- | --- | --- | --- |
| witness tiles disagree locally | yes | motion, a focus slip or a wrong member: changed between exposures | 54 tries; 7 planes failed all three |
| witness pairs misregistered, in the exposures themselves | yes | the exposures are out of line | 2 tries, both retakes passed |
| witness pairs misregistered only after residual compensation | no | the residuals measured from the scene are what fails (MEASURED 2026-11-20 on a plain scene); a retake measures them the same way | 3 planes |
| offsets do not cover the four CFA parities | no | "a wrong shift pattern … a property of the plane or the camera mode" | 17 tries (15 planes, and 2 retakes) |
| offsets unmeasurable (too little scene structure) | no | the plane's own | 0 |
| shifted photosites leave the sensor buffer | no | the camera mode's | 0 |
| members disagree in black or white level | yes | changed between exposures | 0 |
| decode failed | yes (`follow-cmd.rs`) | another try can be read | 0 |

Finding (DERIVED, not acted on): in the owner's run the shift-pattern
failures do not look like a property of the plane. Their planes' measured
structure is as high as their passing neighbours' (0.97-0.999 against
0.99; plane 33 alone 0.85), the wrong offset is one member a photosite off
((1, 1) or (1, -1) for (1, 0)), and planes 140 and 146 measured the right
pattern on earlier tries and failed it only on a retake, in the stretch where
motion was failing planes (123-178). That points at the exposures (motion),
where a retake can help. Whether to retake them is the engine's decision and
needs a rig test (retake a shift-pattern failure and see whether it passes);
the UI states the rule as the checker's ("Not retaken, by the checker's
rule"; the policy line says it "expects a retake to fail the same way").

## Commands and results

Worktree `C:\w\g-flight`, Windows 11, 32 logical CPUs, `CARGO_BUILD_JOBS=12`,
other agents building in their own worktrees at the same time.

| Command | Result |
| --- | --- |
| `cargo test --locked -p strehl-ui` | MEASURED: Compiling strehl-ui (the preceding `cargo test ... capture` on the same sources; the test binary is newer than every edited file); 1,522 tests: 1,483 passed, 0 failed, 39 ignored. Base `7f83d3f22`: 1,504 tests, 36 ignored |
| `cargo clippy --locked -p strehl-ui --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-ui; exit 0 |
| `cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings` | MEASURED: Checking strehl-capture; exit 0 (only `MAX_RETAKES` became `pub`) |
| `cargo fmt -p strehl-capture -- --check` | MEASURED: exit 1, every difference in `receiver.rs` (untouched; differs at `7f83d3f22` too); `worker.rs` clean |
| `cargo fmt -p strehl-ui -- --check` | MEASURED: exit 0 |
| Release `capture_station_pointer_sweeps` and the new `capture_flight_feed_sweeps` (whole shell, paint and tessellation, 6 sweeps of 80 frames, minimum), base binary (main's flight code with this branch's fixtures and benchmark) and this branch interleaved, two rounds | see "Frame cost" below |
| `STREHL_PROOF_RUN=<scratch copy> proof_follows_a_real_run` and `the_station_proof_follows_a_real_run` (release, `--ignored`) | MEASURED: preview decode 6-13 ms a `.straw` RAW; the job: 13-14 updates for 55-56 planes; the station's path: 13 texture updates "planes 1–2" … "planes 1–55", no error; a verbatim `\\?\` run path behaves the same |
| `visual-check.py --exe <debug strehl-ui.exe> --out C:\strehl-scratch\g-flight\shots capture-flight capture-flight-lightbox capture-flight-instrument capture-flight-long capture-flight-done capture-flight-done-lightbox capture-flight-show capture-flight-show-instrument glance` and `--size 1280x800 capture-flight capture-flight-done` (scratch catalog and settings, fixtures, no camera host) | VERIFIED by eye: square, ruled; plane and total on one baseline; no text clipped or overlapping in Graphite, Instrument and Lightbox at 1680 x 1050 and 1280 x 800; the review's summary scrolls with the feed |

### Frame cost (MEASURED, release, ms a frame, minimum of six sweeps)

| Fixture | Base, round 1 / 2 | This branch, round 1 / 2 | Vertices base / branch |
| --- | --- | --- | --- |
| plan | 0.183 / 0.183 | 0.183 / 0.183 | 12,788 / 12,788 |
| flight (61 planes) | 0.116 / 0.113 | 0.126 / 0.130 | 6,878 / 8,458 |
| flight+long (5,400 planes, 5,681 feed items) | 0.116 / 0.116 | 0.128 / 0.130 | 8,130 / 9,294 |
| feed sweep, flight (pointer over the feed, wheel back and forth) | 0.115 / 0.114 | 0.129 / 0.132 | 6,838 / 8,484 |
| feed sweep, flight+long | 0.116 / 0.116 | 0.130 / 0.128 | 8,090 / 9,346 |

The flight view costs about 0.012-0.016 ms a frame more: the column now shows about
fifteen rows instead of five. The 5,400-plane feed costs the same as the
61-plane one (a test holds the rows laid out under 30 of 5,681 items).

## Tests added

Each fails if its rule is removed (ARGUED from their assertions):
`the_owners_run_is_told_try_by_try` (the owner's 260 journal lines encoded in
order: counts, statuses, the end summary, the failure kinds),
`a_retake_asked_for_is_pending_until_it_comes`,
`feed_rows_fit_their_lines_at_the_narrowest` (every reason, try and context
laid out in the studio face at 340 px), `the_headline_counts_planes_once_and_retakes_apart`,
`the_retake_clock_times_what_retakes_add` (paced as the owner's run: 10.2 s a
retake), `the_time_left_counts_down_smoothly`,
`the_canvas_reads_the_headline_and_g_opens_glance` (baselines within 0.6 px),
`the_headline_does_not_shift_as_the_time_left_ticks`,
`the_feed_scrolls_follows_the_newest_and_shows_a_try` (5,400 planes),
`a_scrolled_feed_stays_put_as_it_grows`, `feed_rows_are_positioned_once`,
`the_proof_is_fitted_whole_into_its_space`, `the_review_says_what_happened_and_why`,
`in_flight_the_fit_is_the_stack`, `a_capture_starts_fitted_and_fit_restores_following`,
`the_run_tail_knows_a_retake_by_its_binding`,
`an_ended_capture_is_reviewed_until_back_to_planning`; ignored:
`proof_follows_a_real_run`, `the_station_proof_follows_a_real_run`,
`capture_flight_feed_sweeps`.

## Not done, or not verified

- UNVERIFIED: why the proof did not visibly change in the owner's session.
  Everything this side reproduces updating; what was wrong with it (cap,
  cover fill, retakes counted as planes, a failed update kept silent) is
  fixed. Next capture: watch the caption's "planes 1–N" and any "last update
  failed" note.
- UNVERIFIED on the rig: the retake cost against a live host (the clock is
  tested on synthetic counts paced as the owner's events); the eased LEFT's
  feel; the review's appearance after a real completion.
- The shift-pattern retake question above is the engine's to decide.
- The proof uses each plane's first try (its RAW arrives first); a plane
  whose first try moved is shown from that try.
