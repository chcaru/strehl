# V-ADJ13 — the thirteen unresolved subjects, adjudicated against their own source frames

Status: MEASURED. Author: V-ADJ13 (adjudication lane). Subject: the 6 ACQUITTAL
EXPIRED and 7 REVIEW masters left unresolved by
`experiments/ORCH-drift-check/orch_printready.py` over the 33-master DELIVER-V6
corpus. Arm: **DELIVER-V6**, renderer `C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`,
sha256 `2A7BCD7B…D0712B7`, built at commit `6af834da`, verified by SHA256 against
DELIVER-V6's own manifest before each measurement. Masters read-only; every one
of the 13 verified by SHA256 against `MANIFEST.txt` (the 6 expired) or
`MANIFEST-ORCH7.txt` (the 7 review). Source frames read-only from
`D:\personal\macro\<subject>\*.ARW`. Instruments `experiments/V-ADJ13/`,
raw artifacts `C:\dev\strehl-out\V-ADJ13\`. Peak scratch **0.369 GB** of the
15 GB allowance; one 198 MB render on disk at a time, deleted as soon as it was
measured and after its numbers were written to stdout and to JSON.

No threshold was changed. `ACQUIT_TOL`, `ACQUIT_WINDOW_TOL`, `BLOTCH_REVIEW`,
`CHROMA_REVIEW` and `elevated_multiple` are byte-identical to what they were
before this lane started. The only pre-existing file this lane wrote to is the
acquittal record store `experiments/V-REVIEW/vr_baseline.json`, and it wrote
records, not rules; everything else it added is new — this report and
`experiments/V-ADJ13/`.

## The answer, first

**No subject is a real defect.** All 13 were measured against the frames they
were built from and none reads worse than the worst of its own sources by more
than 1.257x, under a rule that admits 1.3x. **thirteen ACQUIT, zero CONVICT.**

The finding worth more than the sweep is about the *gate*, not the masters:

> **Five of the six expired acquittals had not changed in the way the gate said
> they had.** Four expired because the statistic was measured somewhere else —
> the window moved — and a fifth had its drift overstated 2.7x by an unreported
> window move. Only `113MSDCF` expired on a genuine same-window change in the
> render, and that change was an *improvement*.

Two of those four window moves were invisible to the gate as window moves,
because `orch_printready.py` cannot report a chroma window move at all (F6).
It printed them as value drift, which is the one thing they were not.

## What was measured, and against what

The rule is not mine and was not chosen after seeing the numbers. It is the one
frozen in `experiments/V-REVIEW/vr_baseline.json` under `gate_rule`, the rule the
nine acquittals already on record were granted under:

| element | value | meaning |
|---|---|---|
| `source_baseline` | `max over registered source frames` | low is good for both statistics, so the max is the **worst** source frame |
| `elevated_multiple` | 1.3 | master at or under 1.3x its worst own frame is not exhibiting a merge defect |
| `blotch_review` | 0.02 | above this the gate has no standing to judge alone |
| `chroma_review` | 0.015 | as above |

Source frames are rendered by **the master's own invocation** — the DELIVER-V6
binary, `stack <dir> -o <out> --srgb`, no exposure flag, `STREHL_CACHE_DIR`
privately scoped — plus `STREHL_ONLY_FRAME=k`, which renders frame `k` alone
with no election (`crates/strehl-cli/src/merge_cmd.rs:1775`). Demosaic, CA
correction, alignment resample, colour matrix, sRGB curve and exposure policy
are therefore common mode by construction rather than by a transcribed table.
Registration, warping, NCC gating and both statistics are imported unmodified
from `vr_reg2.py`, `vr_lib.py`, `orch_blotch.py` and `orch_chroma.py`; the
master's own gate windows are warped into each source frame so both arms are
measured on the same piece of the scene. Frames below `NCC_MIN = 0.75` are
POOR-REG and are excluded from the source max.

## Verdicts — all thirteen

| subject | was | flagged on | blotch m/src | chroma m/src | worst | frames | verdict |
|---|---|---|---|---|---:|---:|---|
| `112MSDCF` | EXPIRED | both | 0.14009 / 0.14015 = **1.000x** | 0.02896 / 0.02623 = **1.104x** | 1.104x | 21/21 of 79 | **ACQUIT** |
| `113MSDCF` | EXPIRED | both | 0.25186 / 0.23444 = **1.074x** | 0.02395 / 0.02323 = **1.031x** | 1.074x | 19/19 of 63 | **ACQUIT** |
| `coffee-bubbles` | EXPIRED | both | 0.10071 / 0.10822 = **0.931x** | 0.05384 / 0.06056 = **0.889x** | 0.931x | 13/13 of 19 | **ACQUIT** |
| `couch-fibers-cpl` | EXPIRED | blotch | 0.04310 / 0.06232 = **0.692x** | 0.00419 / 0.00527 = **0.795x** | 0.795x | 20/22 of 299 | **ACQUIT** |
| `flower-inner-edge-cpl` | EXPIRED | blotch | 0.09783 / 0.09655 = **1.013x** | 0.01225 / 0.01483 = **0.826x** | 1.013x | 22/22 of 299 | **ACQUIT** |
| `foam` | EXPIRED | both | 0.45950 / 0.52064 = **0.883x** | 0.03065 / 0.03111 = **0.985x** | 0.985x | 15/19 of 100 | **ACQUIT** |
| `chia-seeds-cpl` | REVIEW | both | 0.42716 / 0.42072 = **1.015x** | 0.07104 / 0.07331 = **0.969x** | 1.015x | 23/23 of 130 | **ACQUIT** |
| `dime-flat-narrow-slices-cpl` | REVIEW | both | 0.04785 / 0.03808 = **1.257x** | 0.03314 / 0.03354 = **0.988x** | 1.257x | 22/22 of 207 | **ACQUIT** |
| `duck-tape-side-layers-cpl` | REVIEW | blotch | 0.14189 / 0.14120 = **1.005x** | 0.00613 / 0.00610 = **1.005x** | 1.005x | 22/22 of 197 | **ACQUIT** |
| `maldon-sea-salt-cpl` | REVIEW | blotch | 0.07794 / 0.06978 = **1.117x** | 0.00171 / 0.00203 = **0.842x** | 1.117x | 25/25 of 255 | **ACQUIT** |
| `medication-pill-cpl` | REVIEW | blotch | 0.10534 / 0.15402 = **0.684x** | 0.01461 / 0.01545 = **0.946x** | 0.946x | 23/23 of 146 | **ACQUIT** |
| `pottery-art-glazed-cpl` | REVIEW | both | 0.18172 / 0.18613 = **0.976x** | 0.14373 / 0.15073 = **0.954x** | 0.976x | 21/21 of 123 | **ACQUIT** |
| `unpopped-popcorn-kernels-cpl` | REVIEW | both | 0.46149 / 0.37430 = **1.233x** | 0.03721 / 0.03987 = **0.933x** | 1.233x | 22/22 of 234 | **ACQUIT** |

`frames` is *registered / sampled of available*. Six of the 13 read **below**
their worst source frame outright on the statistic that flagged them; the rest
sit between 1.00x and 1.257x. Nothing is close to the 1.3x line except
`dime-flat-narrow-slices-cpl`, and its excess is explained in the next section.

The same numbers in the grammar `vr_recheck.py` binds against, so its checker
can hold this report to the baseline rather than taking its word:

| subject | stat | master | source (max of N) | ratio | verdict |
|---|---|---:|---:|---:|---|
| 112MSDCF | blotch | 0.14009 | 0.14015 (max of 21) | **1.000** | ACQUIT |
| 112MSDCF | chroma | 0.02896 | 0.02623 (max of 21) | **1.104** | ACQUIT |
| 113MSDCF | blotch | 0.25186 | 0.23444 (max of 19) | **1.074** | ACQUIT |
| 113MSDCF | chroma | 0.02395 | 0.02323 (max of 19) | **1.031** | ACQUIT |
| coffee-bubbles | blotch | 0.10071 | 0.10822 (max of 13) | **0.931** | ACQUIT |
| coffee-bubbles | chroma | 0.05384 | 0.06056 (max of 13) | **0.889** | ACQUIT |
| couch-fibers-cpl | blotch | 0.04310 | 0.06232 (max of 20) | **0.692** | ACQUIT |
| couch-fibers-cpl | chroma | 0.00419 | 0.00527 (max of 20) | **0.795** | ACQUIT |
| flower-inner-edge-cpl | blotch | 0.09783 | 0.09655 (max of 22) | **1.013** | ACQUIT |
| flower-inner-edge-cpl | chroma | 0.01225 | 0.01483 (max of 22) | **0.826** | ACQUIT |
| foam | blotch | 0.45950 | 0.52064 (max of 15) | **0.883** | ACQUIT |
| foam | chroma | 0.03065 | 0.03111 (max of 15) | **0.985** | ACQUIT |
| chia-seeds-cpl | blotch | 0.42716 | 0.42072 (max of 23) | **1.015** | ACQUIT |
| chia-seeds-cpl | chroma | 0.07104 | 0.07331 (max of 23) | **0.969** | ACQUIT |
| dime-flat-narrow-slices-cpl | blotch | 0.04785 | 0.03808 (max of 22) | **1.257** | ACQUIT |
| dime-flat-narrow-slices-cpl | chroma | 0.03314 | 0.03354 (max of 22) | **0.988** | ACQUIT |
| duck-tape-side-layers-cpl | blotch | 0.14189 | 0.14120 (max of 22) | **1.005** | ACQUIT |
| duck-tape-side-layers-cpl | chroma | 0.00613 | 0.00610 (max of 22) | **1.005** | ACQUIT |
| maldon-sea-salt-cpl | blotch | 0.07794 | 0.06978 (max of 25) | **1.117** | ACQUIT |
| maldon-sea-salt-cpl | chroma | 0.00171 | 0.00203 (max of 25) | **0.842** | ACQUIT |
| medication-pill-cpl | blotch | 0.10534 | 0.15402 (max of 23) | **0.684** | ACQUIT |
| medication-pill-cpl | chroma | 0.01461 | 0.01545 (max of 23) | **0.946** | ACQUIT |
| pottery-art-glazed-cpl | blotch | 0.18172 | 0.18613 (max of 21) | **0.976** | ACQUIT |
| pottery-art-glazed-cpl | chroma | 0.14373 | 0.15073 (max of 21) | **0.954** | ACQUIT |
| unpopped-popcorn-kernels-cpl | blotch | 0.46149 | 0.37430 (max of 22) | **1.233** | ACQUIT |
| unpopped-popcorn-kernels-cpl | chroma | 0.03721 | 0.03987 (max of 22) | **0.933** | ACQUIT |

## The two closest cases, and why they are not defects

Blotch is a contrast: a band amplitude in DN divided by the window's own mean
DN. A ratio above 1 can therefore come from the master having a *larger band*
(a merge defect) or from the master's window being *darker* (not a defect — the
same innocent mechanism V-REVIEW recorded for `112MSDCF`). Decomposing the two
closest cases separates those:

| subject | blotch ratio | band DN ratio | master mean / source median mean | argmax frame |
|---|---:|---:|---:|---:|
| `112MSDCF` | 1.000x | 0.912x | 0.940x | 47 |
| `113MSDCF` | 1.074x | 0.898x | 0.908x | 34 |
| `coffee-bubbles` | 0.931x | 0.858x | 1.068x | 17 |
| `couch-fibers-cpl` | 0.692x | 0.651x | 0.942x | 101 |
| `flower-inner-edge-cpl` | 1.013x | 0.979x | 1.033x | 251 |
| `foam` | 0.883x | 0.525x | 0.882x | 37 |
| `chia-seeds-cpl` | 1.015x | 1.003x | 0.982x | 56 |
| `dime-flat-narrow-slices-cpl` | 1.257x | 1.017x | 0.957x | 180 |
| `duck-tape-side-layers-cpl` | 1.005x | 0.806x | 0.905x | 147 |
| `maldon-sea-salt-cpl` | 1.117x | 0.934x | 0.921x | 175 |
| `medication-pill-cpl` | 0.684x | 0.583x | 0.989x | 145 |
| `pottery-art-glazed-cpl` | 0.976x | 0.978x | 1.001x | 58 |
| `unpopped-popcorn-kernels-cpl` | 1.233x | 1.056x | 0.843x | 174 |

`dime-flat-narrow-slices-cpl` reads 1.257x on contrast but **1.017x on the band
itself**: the band the merge emits is within 2% of the worst single frame's, and
the window is 4.3% darker in the master. `unpopped-popcorn-kernels-cpl` reads
1.233x on contrast, 1.056x on the band, with the master window 15.7% darker.
In both, most of the excess is in the denominator. Neither is exculpated *by*
this decomposition — both already acquit on the frozen rule — but it says what
the residual is, which the ratio alone does not.

## The six expiries: real render change, or measured somewhere else

The gate expires an acquittal when today's statistic differs from the recorded
one by more than `ACQUIT_TOL` (5%), or when the window it was measured in has
moved by more than `ACQUIT_WINDOW_TOL` (8 px). What it never does is measure
today's master **at the old window**, which is the only measurement that can
tell those two apart. `vadj_master.py` takes it: it re-measures each master at
today's window and then forces the statistic into the coordinates the record
was made in.

| subject | stat | recorded | window then -> now | moved | today @ old window | delta | cause |
|---|---|---:|---|---:|---:|---:|---|
| `112MSDCF` | blotch | 0.14667 | [2254, 5926] -> [2254, 5926] | 0 px | 0.14009 | -4.49% | same window |
| `112MSDCF` | chroma | 0.03485 | [2616, 1458] -> [1744, 1458] | 872 px | 0.03268 | -6.23% | MOVED |
| `113MSDCF` | blotch | 0.25168 | [14, 1558] -> [14, 1558] | 0 px | 0.25186 | +0.07% | same window |
| `113MSDCF` | chroma | 0.02538 | [1744, 1458] -> [1744, 1458] | 0 px | 0.02395 | -5.64% | same window |
| `coffee-bubbles` | blotch | 0.09892 | [38, 14] -> [54, 14] | 16 px | 0.09900 | +0.08% | MOVED |
| `coffee-bubbles` | chroma | 0.05460 | [0, 1458] -> [0, 1458] | 0 px | 0.05384 | -1.39% | same window |
| `couch-fibers-cpl` | blotch | 0.04511 | [558, 6110] -> [3422, 2334] | 3776 px | 0.04508 | -0.09% | MOVED |
| `couch-fibers-cpl` | chroma | 0.00418 | [1744, 2920] -> [1744, 2920] | 0 px | 0.00419 | +0.14% | same window |
| `flower-inner-edge-cpl` | blotch | 0.09921 | [3670, 3150] -> [3710, 3150] | 40 px | 0.09979 | +0.58% | MOVED |
| `flower-inner-edge-cpl` | chroma | 0.01226 | [1744, 0] -> [1744, 0] | 0 px | 0.01225 | -0.05% | same window |
| `foam` | blotch | 0.46075 | [518, 2054] -> [518, 2054] | 0 px | 0.45950 | -0.27% | same window |
| `foam` | chroma | 0.03250 | [872, 2916] -> [0, 2916] | 872 px | 0.03212 | -1.19% | MOVED |

Read down the `today @ old window` column. **Every statistic whose window did
not move agrees with its record to within 5%, except one.** That one is
`113MSDCF`'s chroma.

- **`coffee-bubbles`, `couch-fibers-cpl`, `flower-inner-edge-cpl` — WINDOW MOVE,
  not a render change.** At the coordinates the acquittal was granted in, the
  three masters read +0.08%, −0.09% and +0.58% from their records. The blotch
  window is chosen by the statistic (the worst window wins), so a change far
  below the expiry tolerance can still relocate the argmax to a different tie —
  and did, by 16 px, 3776 px and 40 px. The gate reported these correctly, as
  "measured somewhere else". Nothing in the render moved.
- **`foam` — WINDOW MOVE, reported as value drift.** Its chroma window moved
  872 px, from [872, 2916] to [0, 2916]. At [872, 2916] today's master reads
  0.03212 against a record of 0.03250: −1.19%, well inside tolerance. The gate
  printed `chroma 0.03250 -> 0.03065 (5.7% > 5%)` because it cannot see a chroma
  window move (F6). Its blotch window did not move and its blotch agrees to
  −0.27%. Nothing in the render moved.
- **`112MSDCF` — MIXED, and the reported drift is inflated 2.7x.** The chroma
  window moved 872 px, same displacement as `foam`. At the recorded window
  today's master reads 0.03268 against 0.03485: −6.23%, which still exceeds the
  5% tolerance, so this acquittal was due to expire on its own merits — but on
  −6.23%, not on the −16.9% the gate printed. Its blotch, at an unmoved window,
  moved −4.49%: real, and just inside tolerance.
- **`113MSDCF` — REAL RENDER CHANGE.** The chroma window did not move by a
  pixel, and at that window the statistic moved −5.64%. This is the only one of
  the six that expired on what the gate said it expired on. The direction is an
  improvement: less chroma noise, not more (F5, F7).

## What changed in the render, for the one case where something did

`113MSDCF`'s −5.64% is real, so the follow-up question the gate asks — "find out
what changed in the render" — has a real answer. Two controls narrow it.

**The exposure policy did not change the pixels (F8).** SHIP-V3's recorded ARGV
carried `--auto-exposure`; DELIVER-V6's carries no exposure flag, which would
make every record-vs-today comparison in the table above a comparison between
two tone operating points. It is not. Rendering the same frame through the
SHIP-V3 pin with and without the flag gives files that differ **by at most 1 DN
on 0.26% of samples** — `max |delta| = 1`, on a 16-bit image — while the pin's
banner announces `+2.42 stops (gain 5.352x), chosen from the image`. An
explicit `--exposure=2.33` behaves the same way: max |delta| 1 DN on 0.24% of
samples. Every statistic in both windows agrees to seven significant figures.
The flag is inert in this path; the comparison is legitimate.

**The single-frame path barely changed between binaries (F7).** Same frame, same
flags, pin `740e7056` versus DELIVER-V6's `6af834da`:

| subject | frame | blotch | chroma | band DN | mean DN | noise DN |
|---|---:|---|---|---|---|---|
| `113MSDCF` | 31 | 0.238589 -> 0.237549 (-0.44%) | 0.021956 -> 0.021969 (+0.06%) | 2255.83 -> 2254.60 (-0.05%) | 9454.89 -> 9491.11 (+0.38%) | 1023.84 -> 1048.10 (+2.37%) |
| `112MSDCF` | 39 | 0.139646 -> 0.139480 (-0.12%) | 0.028918 -> 0.029116 (+0.69%) | 2132.43 -> 2130.83 (-0.08%) | 15270.19 -> 15276.89 (+0.04%) | 1261.63 -> 1297.10 (+2.81%) |

`STREHL_ONLY_FRAME` renders one frame with no election, so this arm exercises
decode, demosaic, CA, colour and the sRGB curve but **not the merge**. Chroma
moves +0.06% there and −5.64% in the master. The change therefore lives in the
election/merge stage between those two binaries, not in the front end. This
lane did not bisect it further; that is a renderer question, not an adjudication
question, and the master acquits either way at 1.031x its worst source frame.

## Facts

**F1 (MEASURED).** All 13 unresolved subjects acquit against their own source
frames under the frozen rule. Worst ratio across all 26 subject-statistic pairs:
1.257x (`dime-flat-narrow-slices-cpl`, blotch), against an `elevated_multiple`
of 1.3. Six read below their worst source frame outright. Zero convictions.

**F2 (MEASURED).** Three of the six expiries — `coffee-bubbles`,
`couch-fibers-cpl`, `flower-inner-edge-cpl` — are pure blotch-window moves. At
their recorded windows today's masters read +0.08%, −0.09% and +0.58% from the
recorded values, i.e. 6x to 60x inside the 5% expiry tolerance.

**F3 (MEASURED).** `foam`'s expiry is a chroma-window move of 872 px, not value
drift. At the recorded window it reads 0.03212 against 0.03250 (−1.19%). The
gate reported it as a 5.7% drift.

**F4 (MEASURED).** `112MSDCF`'s chroma window also moved 872 px. At the recorded
window the drift is −6.23%, not the −16.9% printed; the acquittal expires either
way, on a number 2.7x smaller than the one on the gate's face.

**F5 (MEASURED).** `113MSDCF` is the only one of the six whose expiry is a real
same-window change: chroma window unchanged at [1744, 1458], 0.02538 -> 0.02395,
−5.64%. The change reduces the measured chroma noise.

**F6 (MEASURED).** `orch_printready.py` cannot report a chroma window move.
`verdict()` builds its `meas` dict with `blotch_window_yx` and no
`chroma_window_yx`, so in `check_acquittal` the current window for chroma is
always `None` and the "measured somewhere else" branch is unreachable for that
statistic. Consequence: two of six expiries (F3, F4) were misattributed to value
drift. This is a one-line fix in a file shared with ~20 concurrent lanes and
this lane did not make it — the fix is to put `chroma_window_yx` into `meas`
beside the blotch window. Until it is made, every chroma expiry the gate prints
should be re-measured at the recorded window before it is believed.

**F7 (MEASURED).** On identical single-frame input with identical flags, pin
`740e7056` -> DELIVER-V6 `6af834da` moves blotch by −0.44% / −0.12% and chroma by
+0.06% / +0.69% on `113MSDCF` frame 31 and `112MSDCF` frame 39. Since
`STREHL_ONLY_FRAME` bypasses the election, F5's −5.64% is not attributable to
decode, demosaic, CA, colour matrix or transfer curve.

**F8 (MEASURED).** On pin `740e7056` with `--srgb`, `--auto-exposure` changes at
most **1 DN** on 0.26% of samples and an explicit `--exposure=2.33` at most 1 DN
on 0.24% of samples, while the banner announces a 5.352x gain "chosen from the
image". Measured on `113MSDCF` frame 31 by full-array comparison of the two
decoded renders. Scope: one pin, one subject, one frame, sRGB output — enough to
license this lane's SHIP-V3-record-vs-DELIVER-V6-measurement comparisons, not
enough to characterise the flag across the product.

**F9 (MEASURED/DERIVED).** In the two subjects closest to the 1.3x line the
excess is mostly in the denominator: `dime-flat-narrow-slices-cpl` band ratio
1.017x with the master window 4.3% darker than the source median; popcorn band
ratio 1.056x with the master window 15.7% darker. MEASURED for the ratios,
DERIVED for the attribution, which follows from blotch being band/mean.

**F10 (DERIVED).** The sampling is one-directional in favour of conviction, not
acquittal: the baseline is a **max** over sampled frames, so sampling more
frames can only raise it and lower every ratio. Each acquittal here therefore
holds a fortiori under exhaustive sampling. A conviction would not have enjoyed
this property, and none was recorded.

**F11 (MEASURED).** With the 13 records written, `orch_printready.py` over
`C:\dev\strehl-out\DELIVER-V6\masters` partitions the corpus as 17 PASS, 0 FAIL,
16 ACQUITTED, 0 ACQUITTAL EXPIRED, 0 REVIEW, 0 NOT EXAMINED, 33 total.

**F12 (MEASURED).** Registration held on 11 of 13 subjects at 100% of sampled
frames. `foam` registered 15 of 19 and `couch-fibers-cpl` 20 of 22; the excluded
frames fell below `NCC_MIN = 0.75` and were kept out of the source max, which is
the conservative direction for acquittal (F10) — a rejected frame cannot raise
the bar the master has to clear.

**F13 (MEASURED).** `flower-inner-edge-cpl`'s master cover was fitted by ORB with
only **45 inliers**, against 575–3874 for the other twelve. Its 22 of 22 source
frames then registered at NCC ≥ 0.75, so the fit was serviceable, but this is the
weakest geometric prior in the set and the one number here most worth an
independent re-derivation.

**F14 (MEASURED).** `vr_recheck.py`'s `--only` filter scopes its master
re-derivation but not its report binding: `bind_report` is called with the
unfiltered baseline (`vr_recheck.py:210`), so any report that adjudicates a
subset of a shared store ends RED on the subjects other lanes own. Scoped by
`--baseline` to this lane's 13, the checker returns GREEN with 13 masters held,
26 rows bound and 0 contradicted.

## The acquittal records written

`orch_printready.py` reads acquittals from `experiments/V-REVIEW/vr_baseline.json`
and from nowhere else (`BASELINE_PATH`, line 164), so that is where these 13
went, in the schema `vr-baseline/1` that `vr_freeze.py` established:
`flagged_for`, `verdict`, `reason`, `n_source_frames_registered`, `master{blotch,
blotch_band_dn, blotch_mean_dn, blotch_window_yx, chroma, chroma_window_yx}`,
`source_frame_max{...}`, `ratio{...}`. The store went from 10 subjects to 17.

Three properties of the write, each deliberate:

1. **`gate_rule` was not touched.** No threshold, tolerance or multiple was
   edited anywhere, in this file or in the gate. The 13 subjects cleared the
   rule that was already there.
2. **The six superseded SHIP-V3 records were not deleted.** Each new record
   carries the old one verbatim under `superseded_record`, together with the
   gate's own expiry string and this lane's finding about it. A baseline that
   forgets what it used to say cannot be audited, and the expiry mechanism
   exists precisely so nobody has to trust an unexamined number.
3. **Each new record names its own arm and provenance** — `arm: DELIVER-V6`,
   the renderer path and SHA256, the master's SHA256, the sampled and registered
   frame counts, the argmax source frame, the ratio against the *median* source
   frame as well as the max, and `report: docs/research/V-ADJ13.md`. The
   top-level `arm` string now reads `SHIP-V3 (10 subjects, V-REVIEW) +
   DELIVER-V6 (13 subjects, V-ADJ13)`, because it is no longer a single-arm file
   and `vr_recheck.py` prints that string on every run.

One consequence to declare rather than discover later: `vr_recheck.py` binds a
report against the **whole** store — its `--only` filter scopes the master
re-derivation but `bind_report` is handed the unfiltered baseline
(`vr_recheck.py:210`). Bound against this report, V-REVIEW's three remaining
SHIP-V3 acquittals (`flat-on-ruler-cpl`, `lead-1-cpl`, `leaf-2-cpl`) are
therefore reported as adjudicated-but-unstated, and the run ends RED. That is
the arithmetic of two lanes sharing one store, not a contradiction in any
number: those three are stated in `experiments/V-REVIEW/report.md`, which is
where they belong. Scoped to the 13 subjects this lane adjudicated, the same
checker runs **GREEN** — 13 masters held, 26 rows bound, 0 contradicted,
headline agreeing with the store. Both commands are in the next section; the
RED one is not hidden.

## Commands

Every number above came from one of these. Run from
`C:\dev\blog\death-of-software\projects\strehl`.

| purpose | command |
|---|---|
| the gate, before and after | `python experiments\ORCH-drift-check\orch_printready.py C:\dev\strehl-out\DELIVER-V6\masters` |
| master at today's and the recorded windows | `python experiments\V-ADJ13\vadj_master.py` |
| source-frame arm, one subject | `python experiments\V-ADJ13\vadj_source.py <subject>` |
| renderer control on one frame | `python experiments\V-ADJ13\vadj_binary.py 113MSDCF 31 1744 1458 14 1558` |
| exposure-flag control, pixel identity | `python experiments\V-ADJ13\vadj_autoexp.py 113MSDCF 31` |
| exposure-flag control, explicit stops | `python experiments\V-ADJ13\vadj_autoexp.py 113MSDCF 31 --exposure=2.33` |
| three-arm exposure statistics | `python experiments\V-ADJ13\vadj_exposure.py 113MSDCF 31` |
| merge the 13 records (dry run first) | `python experiments\V-ADJ13\vadj_freeze.py` then `--write` |
| scoped baseline copy for the self-check | `python experiments\V-ADJ13\vadj_freeze.py --scoped-copy` |
| regenerate every table in this report | `python experiments\V-ADJ13\vadj_report.py` |

The report-to-baseline self-check, which is the one that holds this document to
the store rather than the other way round. Scoped to this lane's 13 subjects it
returns **GREEN — 13 masters held, 26 report rows bound, 0 contradicted**:

```
python experiments\V-ADJ13\vadj_freeze.py --scoped-copy
python experiments\V-REVIEW\vr_recheck.py --masters C:\dev\strehl-out\DELIVER-V6\masters --suffix "" --baseline C:\dev\strehl-out\V-ADJ13\vr_baseline_vadj13.json --report docs\research\V-ADJ13.md
```

Unscoped, against the whole shared store, the same checker returns RED for the
three V-REVIEW subjects this report does not restate. The command and its
result are recorded rather than suppressed:

```
python experiments\V-REVIEW\vr_recheck.py --masters C:\dev\strehl-out\DELIVER-V6\masters --suffix "" --report docs\research\V-ADJ13.md --only 112MSDCF,113MSDCF,coffee-bubbles,couch-fibers-cpl,flower-inner-edge-cpl,foam,chia-seeds-cpl,dime-flat-narrow-slices-cpl,duck-tape-side-layers-cpl,maldon-sea-salt-cpl,medication-pill-cpl,pottery-art-glazed-cpl,unpopped-popcorn-kernels-cpl
```

`bound 26, contradicted 0, unparsed 0, no-row 3` — the three being
`flat-on-ruler-cpl/blotch`, `lead-1-cpl/chroma`, `leaf-2-cpl/chroma`, all of
them V-REVIEW's and all of them stated in V-REVIEW's own report.

Banked raw output, all text, all written before the pixels that produced it were
deleted: `C:\dev\strehl-out\V-ADJ13\` — `gate-v6-33.txt` and
`gate-v6-33-after.txt` (the gate before and after), `vadj_master.txt` /
`.json`, `source_<subject>.txt` / `.json` for all 13 (per-frame tables, not just
the summaries), `binary_112MSDCF.txt`, `binary_113MSDCF.txt`,
`autoexp_113MSDCF.txt`, `autoexp_113MSDCF_explicit.txt`, `vadj_exposure.txt`,
`freeze_dryrun.txt`, `freeze_write.txt`, `report_tables.txt`,
`recheck_vadj13.txt` and `recheck_vadj13_scoped.txt` (the RED and GREEN
self-checks), `vr_baseline_vadj13.json` (the scoped copy).

## Verified vs. assumed

**Verified by measurement in this lane.** F1 through F14, each labelled above.
The 13 master SHA256s against DELIVER-V6's two manifests. The renderer's SHA256
against the manifest, re-checked at every subject. That the gate reproduces the
partition it was reported to produce, before the write (17/0/3/6/7) and after
(17/0/16/0/0). That `STREHL_ONLY_FRAME=k` renders frame `k` alone with no
election, read in `crates/strehl-cli/src/merge_cmd.rs:1775`. That the merged
baseline re-reads as valid JSON and drops none of the 10 pre-existing records
(`vadj_freeze.py` refuses to write if any would be lost).

**Assumed, and the assumption named.**

- That the ARW set in `D:\personal\macro\<subject>` today is the set each master
  was built from. Not independently verifiable — DELIVER-V6's manifest records
  frame *counts*, which match, but no per-frame hashes. If a frame were replaced
  in place, this arm would compare a master against sources it does not have.
- That sampling 13–25 frames per subject bounds the source max well enough. This
  is not verified, it is *argued* by F10: the bias runs against acquittal, so a
  denser sample can only strengthen these verdicts, never reverse one.
- That the recorded SHIP-V3 statistics in the baseline are what that arm
  actually measured. The SHIP-V3 TIFFs have been purged from
  `C:\dev\strehl-out\acceptance\SHIP-V3` (only logs, `.ok` sidecars and
  provenance files remain), so the 2x2 of binary x window cannot be completed;
  the record supplies the V3-at-old-window cell and nothing can re-derive it.
  This is the single largest hole in the expiry analysis, and it is a hole in
  the *evidence available*, not in the reasoning: it means "the render changed"
  for `113MSDCF` rests on the record's honesty about V3's number, while "the
  window moved" for the other four rests only on measurements taken today.
- That the master cover ratios used to initialise registration are correct.
  Seven came from the render logs; six were fitted by ORB (F13 flags the weakest).
- That `--auto-exposure` is inert beyond the one pin, subject, frame and output
  mode measured (F8). Not assumed for any conclusion here; stated as scoped.

**Not measured at all.** Whether the merge-stage change behind F5 is an
improvement in any sense other than the chroma statistic. Whether the other 20
subjects' acquittals or passes would survive the same source-frame treatment —
17 of them never read high enough to need it. Any statistic outside blotch,
chroma, banding, clipping and crush: this gate certifies the absence of the
defects it measures and nothing else.

## Closing line

`orch_printready.py` over all 33 DELIVER-V6 masters, after this adjudication:
**17 PASS, 0 FAIL, 16 ACQUITTED, 0 ACQUITTAL EXPIRED, 0 REVIEW, 0 NOT EXAMINED,
33 total.** The 13 formerly unresolved subjects were adjudicated against their
own source frames and acquitted — **thirteen ACQUIT, zero CONVICT** — with no
threshold, tolerance or multiple changed anywhere; five of the six expired
acquittals had expired on where the statistic was measured rather than on a
change in the render, and the sixth, `113MSDCF`, expired on a real merge-stage
change of −5.6% in the improving direction.
