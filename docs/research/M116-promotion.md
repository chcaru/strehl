# M116 — promoting the dormant quality instruments: a measured verdict

Measured against pinned commit `4beac7300e318f6f0aaf10b6a88e57f311b9e814`, in an
isolated worktree, on the owner's real captures.

**Headline: none of the four instruments clears its pre-registered promotion
bar. No patch is recommended.** The best gain measured anywhere was
`+0.00916` dex against a registered bar of `+0.010`. The soft gate does worse
than fail to help — on the one subject where the metric has real power it
removes measurable detail, and 99.1% of that loss is *not* explained by the
noise reduction it also delivers.

**Second headline, and the one that bears on the owner's actual complaint:** the
default path is not the problem these instruments were built to solve. The
default merge beats the sharpest single source frame by `+0.152` to `+0.333` dex
and beats pure per-pixel selection visibly and grossly. The visible defects in
the owner's renders are waxy tonal plateaus and edge halos, and **not one of the
four instruments in this milestone's brief targets either of them.** A fifth,
undocumented, unmeasured instrument does: `STREHL_FIX_HALO`.

Note on numbering: candidate facts below are `P1`…`P14`. The placebo *arm* is
always written `P1-placebo` and is never the fact `P1`.

---

## 1. Verdict table

| instrument | bee-3-cpl (high contrast) | foam (low contrast) | tweezers-cpl (occluding edge) | verdict | decided by |
| --- | --- | --- | --- | --- | --- |
| photometric normalisation | KEEP-OFF | INCONCLUSIVE | KEEP-OFF | **KEEP-OFF** | ΔQ `+0.00477` / `-0.00003` / `+0.00835`, bar `+0.010`, fails B2 on 3 of 3 |
| soft gate (gaussian) | KEEP-OFF | INCONCLUSIVE | KEEP-OFF | **KEEP-OFF** | ΔD `-0.01218` on bee fails B1; ΔQ fails B2 on 3 of 3 |
| soft gate (exponential) | KEEP-OFF | INCONCLUSIVE | KEEP-OFF | **KEEP-OFF** | ΔD `-0.01434` on bee, worse than gaussian on every subject |
| photometric + soft gate | KEEP-OFF | INCONCLUSIVE | KEEP-OFF | **KEEP-OFF** | best measured: ΔQ `+0.00916`, still short of `+0.010` |
| outlier / robustness mask | not reachable | not reachable | not reachable | **UNREACHABLE** | `1043` lines, zero callers outside its own example harness at the pinned SHA |
| robust (election-time) | not reachable | not reachable | not reachable | **UNREACHABLE** | `509` lines, zero callers outside its own example harness at the pinned SHA |
| lateral-CA correction | not run | not run | not run | **out of scope** | excluded by dispatch; owned by M107 and M114 |

Supporting verdicts, not instruments:

| comparison | bee-3-cpl | foam | tweezers-cpl | reading |
| --- | --- | --- | --- | --- |
| merge vs sharpest single frame (M85 question) | `+0.15207` | `+0.16661` | `+0.33319` | merge wins decisively on all three |
| metric power (mask separation) | `1.1176` dex | `0.1249` dex | `0.8506` dex | foam has no power and can only return INCONCLUSIVE |
| noise share of detail-band variance | `0.58%` | `56.27%` | `1.99%` | foam's detail mask is more than half noise |

---

## 2. The pinned build, and how to reproduce

Five agents held uncommitted edits under `crates/` during this campaign. Every
number here was produced from a detached worktree at a named commit, so none of
them can contain another agent's in-flight work.

```
git -C C:\dev\blog\death-of-software\projects\strehl worktree add --detach C:\dev\strehl-out\M116-tree 4beac7300e318f6f0aaf10b6a88e57f311b9e814
cd C:\dev\strehl-out\M116-tree
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release

cd C:\dev\blog\death-of-software\projects\strehl\experiments\M116-promotion
pwsh -File .\run_measure.ps1      # 39 renders, the measurement grid
python pick_single.py             # sharpest single frame per subject
pwsh -File .\run_view.ps1         # 24 renders, the viewing grid
python score.py                   # metrics -> scores.json
python crops.py                   # crops and contact sheets
```

`4beac73` was HEAD at dispatch and is no longer HEAD; other agents have
committed since. That is the point of pinning, not a defect. The binary was
built once, in that worktree, and never rebuilt mid-campaign.

**Registration was frozen before measurement.** `prereg.txt` is commit
`0235330`, made before any scoring run existed.

---

## 3. The controls, stated before any positive result

Every arm below is byte-identical to the default arm A0. Not
"indistinguishable" — the same SHA-256.

| control | what it changes | bee-3-cpl | foam | tweezers-cpl | ΔQ |
| --- | --- | --- | --- | --- | --- |
| P1-placebo | a flag that cannot affect pixels | SHA `= A0` | SHA `= A0` | SHA `= A0` | exactly `0.00000` |
| N1 null | nothing; A0 re-run | SHA `= A0` | SHA `= A0` | SHA `= A0` | exactly `0.00000` |
| T1 trap | adds a byte-inert diagnostic dump | SHA `= A0` | SHA `= A0` | SHA `= A0` | exactly `0.00000` |
| T2 trap | `STREHL_SOFT_GATE=0`, which must mean "off" | SHA `= A0` | SHA `= A0` | SHA `= A0` | exactly `0.00000` |

A0 reference hashes (first 12): bee `478387EF2F9A`, foam `01B0E3913B99`,
tweezers `4881EC4EFA49`.

So the renderer is deterministic on this path, the run-to-run spread is exactly
zero, the harness contributes exactly zero, and a diagnostic dump is genuinely
byte-inert as AGENTS.md rule 26 requires. The registered FAILURE condition — a
non-identical null — did not occur.

**This makes bar B3 degenerate, and I am not going to pretend otherwise.** B3
requires `|ΔQ|` to exceed `3 x` the control floor. The floor measured exactly
`0`, so `3 x 0 = 0` and any non-zero difference satisfies that clause. B3's
binding half is therefore its absolute clause, `|ΔQ| >= 0.010 dex`, which is B2
restated. B3 did no independent work in this milestone. I registered it
expecting a non-zero floor; it is honest to record that it turned out
redundant rather than to claim four independent bars.

---

## 4. The registered bars, verbatim, with PASS/FAIL

Quoted exactly from `prereg.txt` at commit `0235330`:

```
  B1  NO DETAIL LOSS       DELTA-D >= -0.010 dex
  B2  A REAL GAIN          DELTA-Q >= +0.010 dex
  B3  ABOVE THE FLOOR      |DELTA-Q| >= 3 x max(|DELTA-Q| over P1, T1, T2)
                           and |DELTA-Q| >= 0.010 dex
  B4  NO VISUAL REGRESSION the 1:1 crops show no new artefact

Per-instrument verdict, over the three subjects:
  PROMOTE       passes B1-B4 on >= 2 of 3 subjects AND DELTA-Q > -0.010 on all 3
  KEEP-OFF      fails B2 on >= 2 of 3 subjects, OR fails B1 on any subject
  INCONCLUSIVE  anything else
```

| arm | subject | ΔN | ΔD | ΔQ | B1 | B2 | B3 | B4 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A1 photometric | bee-3-cpl | `+0.00175` | `+0.00652` | `+0.00477` | PASS | **FAIL** | **FAIL** | PASS |
| A1 photometric | foam | `+0.00326` | `+0.00323` | `-0.00003` | PASS | **FAIL** | **FAIL** | PASS |
| A1 photometric | tweezers-cpl | `-0.00251` | `+0.00583` | `+0.00835` | PASS | **FAIL** | **FAIL** | PASS |
| A2 softgate gaussian | bee-3-cpl | `-0.02044` | `-0.01218` | `+0.00826` | **FAIL** | **FAIL** | **FAIL** | PASS |
| A2 softgate gaussian | foam | `-0.00092` | `-0.00074` | `+0.00018` | PASS | **FAIL** | **FAIL** | PASS |
| A2 softgate gaussian | tweezers-cpl | `-0.00202` | `-0.00191` | `+0.00011` | PASS | **FAIL** | **FAIL** | PASS |
| A3 softgate exponential | bee-3-cpl | `-0.01943` | `-0.01434` | `+0.00509` | **FAIL** | **FAIL** | **FAIL** | PASS |
| A3 softgate exponential | foam | `-0.00108` | `-0.00090` | `+0.00018` | PASS | **FAIL** | **FAIL** | PASS |
| A3 softgate exponential | tweezers-cpl | `-0.00214` | `-0.00228` | `-0.00014` | PASS | **FAIL** | **FAIL** | PASS |
| A4 photometric + softgate | bee-3-cpl | `-0.01509` | `-0.00593` | `+0.00916` | PASS | **FAIL** | **FAIL** | PASS |
| A4 photometric + softgate | foam | `+0.00255` | `+0.00268` | `+0.00012` | PASS | **FAIL** | **FAIL** | PASS |
| A4 photometric + softgate | tweezers-cpl | `-0.00435` | `+0.00430` | `+0.00864` | PASS | **FAIL** | **FAIL** | PASS |

**B2 fails 12 times out of 12.** Not one arm, on any subject, reached the gain
bar. The bar was set at `0.010` dex (2.33% in linear sd) before any datum
existed, on the stated ground that the project should not move a shipped
default for less. I am not moving it. The two arms that came closest, A4 on bee
(`+0.00916`) and A4 on tweezers (`+0.00864`), missed by `0.00084` and `0.00136`
dex respectively, and I note that proximity precisely so that nobody has to
discover it later and wonder whether it was suppressed.

---

## 5. Candidate facts

**P1 — MEASURED. The default render path is deterministic to the byte, so every
difference in this report is attributable to the arm and not to run-to-run
spread.** Three subjects, four control arms each, all twelve outputs
SHA-256-identical to their subject's A0 (`478387EF2F9A`, `01B0E3913B99`,
`4881EC4EFA49`). Run-to-run spread is exactly `0`, not merely small.

**P2 — MEASURED. No dormant instrument reaches a `+0.010` dex gain on any real
capture; the maximum over 12 arm-subject pairs is `+0.00916`.** Twelve
consecutive B2 failures, table in section 4.

**P3 — MEASURED. The soft gate removes real detail on a high-contrast subject,
and the loss is not recycled noise.** On bee-3-cpl the gaussian kernel reads
ΔD `-0.01218`. Modelling detail-band variance as `sd_det^2 = S^2 + n^2` and
estimating `n` from the flat mask, the arm's own flat-region noise reduction
(ΔN `-0.02044`) accounts for only `-0.00011` dex of that. The unexplained
residual is `-0.01207` dex, **99.1% of the observed loss.** The exponential
kernel is worse: ΔD `-0.01434`, residual `-0.01423`.

**P4 — MEASURED. The soft gate's benefit is confined to the flat field and does
not survive into the detail band.** On bee-3-cpl it improves flat-region noise
by ΔN `-0.02044` — the largest single effect measured in this milestone, and
2.2x the B2 bar — while simultaneously failing B1 in the detail band. It buys a
visible quantity with a measurable one.

**P5 — MEASURED. Photometric normalisation never harms and slightly helps, on
every subject, and still fails its bar.** ΔD is positive on 3 of 3
(`+0.00652`, `+0.00323`, `+0.00583`); ΔQ is `>= -0.00003` on 3 of 3. It is the
only instrument tested that damages nothing. It is also below the bar
everywhere.

**P6 — MEASURED. Photometric benefit does not scale with photometric drift,
contradicting the registered directional predictor.** Fitted per-frame gain
spans: bee `1.0433`, tweezers `1.1451`, foam `1.5307`. Foam has by far the
largest drift — a 53% span — and shows the *smallest* Q response of the three
(`-0.00003`). The predictor registered in `prereg.txt` §8 anticipated the
opposite ordering. See P7 for the competing explanation I cannot exclude.

**P7 — MEASURED. On foam, photometric moved both bands by the same amount, which
is the signature of a level change rather than a quality change.** ΔN `+0.00326`
against ΔD `+0.00323` — equal to within `0.00003` dex. Q is a band *ratio* and
correctly cancels a global level shift; that is why it was chosen over an
absolute DN tolerance, which produced the waxy-blob artefact recorded in fact
1470. So foam's null is consistent with "photometric did the trivial part of its
job and nothing more", **and equally consistent with "the metric cannot see the
rest on this subject"** (P8). I cannot separate these two with the data I have.

**P8 — MEASURED. The foam subject has insufficient metric power to return any
verdict, and this is quantified rather than asserted.** Mask separation
`0.1249` dex, against `1.1176` on bee and `0.8506` on tweezers. The noise share
of detail-band variance is `56.27%` — foam's "detail" mask is more than half
noise. Independently, its detail and flat crop windows separate by only `1.4x`
in local structure, against `11.4x` on bee and `4.5x` on tweezers: foam has no
structurally flat region at all. Every foam cell in the verdict table is
therefore INCONCLUSIVE by construction, not by result.

**P9 — MEASURED. The default merge is substantially sharper than the sharpest
single source frame, on all three subjects.** `D(merge) - D(single frame)` reads
`+0.15207` (bee), `+0.16661` (foam), `+0.33319` (tweezers). The open M85 concern
— that the merge might be losing to a single frame — **does not reproduce here**,
and reproduces in the opposite direction by an order of magnitude more than any
instrument effect measured tonight. Measured with `STREHL_ALIGN=0` on both
sides so that one pixel-exact grid is shared and no resampling enters the
sharpness measurement.

**P10 — MEASURED, visual. Pure per-pixel selection produces gross visible
patchwork that the shipped gate removes.** At 1:1 on bee-3-cpl, the `--gate 0`
arm shows polygonal tile boundaries across the entire smooth background; the
shipped `--gate 4` default does not. This is the largest quality difference
visible anywhere in this campaign, and it is a difference the project has
*already banked*. Reported as visual-only: M0 is the mask arm, so scoring it
against masks derived from itself would be circular, and I did not do it.

**P11 — ARGUED, from visual inspection. The visible defects in the owner's
renders are tonal plateaus and edge halos, and no instrument in this
milestone's brief targets either.** At 1:1 the bee subject shows flat-edged
"waxy" contours around hair bases and along the wing edge; the tweezers subject
shows a dark halo above the occluding edge. Photometric, the soft gate and the
outlier mask all act on *frame admission and weighting*; none reshapes the
tonal transfer at an edge. This is an argument from what the instruments do,
supported by pictures, not a measurement of the artefact.

**P12 — MEASURED. The outlier / robustness mask is unreachable from any flag at
the pinned SHA and therefore cannot be measured end to end.** At `4beac73` the
only references to `strehl_core::outlier` outside the module are
`crates/strehl-core/src/lib.rs:23` (`pub mod outlier;`) and one example binary,
`crates/strehl-cli/examples/m97-outlier.rs`. There is no CLI flag and no
environment variable. Its verdict is decided by this audit and not by a render.
Determined by `git grep` at the commit, not by reading the working tree.

**P13 — MEASURED. The soft gate IS committed and reachable at HEAD; the
inventory this milestone was dispatched with was stale.** Commit `4247607`,
"merge: wire M111's soft admission gate behind `STREHL_SOFT_GATE`", landed
2026-08-24 16:48, roughly 48 minutes before dispatch. `merge.rs:75` imports it,
`merge.rs:1026` constructs it in the fold, and `Estimator::new` resolves the
variable. It accepts `gaussian` and `exponential`; `1`/`true`/`on` and typos
**panic** rather than silently disabling, which is why `STREHL_SOFT_GATE=0` was
usable as trap T2.

**P14 — MEASURED. A fifth dormant instrument exists that no brief has named:
`STREHL_FIX_HALO`, with a `STREHL_FIX_HALO_DELTA` companion and no CLI flag at
all.** Found by enumerating every environment variable the tool reads at the
pinned SHA. It is the only dormant instrument whose stated purpose matches the
artefact class in P11. **It was not measured by this milestone** — it was not in
the registered arm set, and adding an arm after seeing the data would make it
post-hoc. It is the highest-value candidate for the next milestone.

---

## 5b. Addendum: the reachability correction, and what it led to

**This section is post-hoc and is marked as such.** ORCH issued a corrected
instrument inventory at 19:24, after `prereg.txt` was frozen (`0235330`) and
after the campaign had completed. No registered bar was changed, no arm was
re-run, and none of sections 1–5 was rewritten to accommodate it. What follows
is additional observation.

**P15 — MEASURED. Two tested modules totalling `1552` lines are unreachable from
the product binary at the pinned SHA.** `outlier.rs` (`1043` lines) is
referenced outside itself only by `crates/strehl-cli/examples/m97-outlier.rs`;
`robust.rs` (`509` lines) only by `crates/strehl-cli/examples/m93-election.rs`.
No CLI flag, no environment variable, no call from `merge.rs`. Verified by
`git grep '<mod>::' 4beac73 -- crates/`, which reads the commit rather than the
working tree. ORCH's independent audit script reports the same two modules
unreached at a later HEAD (`e49281f`) at `1094` and `544` lines — the modules
have grown by 86 lines since my SHA while remaining uncalled. Both counts are
reported because they are counts of different commits.

Verdict for these two is **UNREACHABLE**, deliberately not INCONCLUSIVE: no
measurement was attempted, because none is possible from the product.

**P16 — MEASURED, and it refutes my own detector. An election-map motion proxy
fires at `2.076%` on a rigid steel subject, so it is not measuring motion.**
Following ORCH's pointer to corpus fact 1189 (M89: a moved frame presents a
displaced edge, a displaced edge is sharper, so motion *wins* the election), I
looked for isolated pixels electing a frame far from their neighbourhood
median. Isolated discrepant pixels (`>= 8` frames from the local median, in a
connected component `<= 64` px): bee `3.306%`, tweezers `2.076%`, foam
`0.305%`. **`tweezers-cpl` is a rigid steel tool on a stand and cannot move
between exposures**, and `foam` — the subject M89 measured at `4.78%` beyond
8 sigma — ranks *last*. A motion detector that ranks a rigid object second and
the known-motion subject last is refuted by its own control. I did not ship
these crops under ORCH's requested `MOTION-ARTEFACT` filename, because that
name asserts a cause this measurement does not support.

**P17 — MEASURED. The isolated election outliers are flat-region argmax
indeterminacy, and the subject without flat regions reads exactly chance.**
Median local structure at outlier pixels, divided by the median over the whole
frame: bee `0.443`, tweezers `0.487` — outliers sit in markedly flatter pixels
than average. Fraction of outliers falling in the flattest 20% of the frame,
against a chance rate of `20.0%`: bee `49.6%`, tweezers `57.1%`. **foam reads
`20.1%` — chance to within `0.1` points**, and its structure ratio is `1.012`,
because foam has no structurally flat region for the mechanism to operate in
(P8). The prediction was registered in the script's docstring before the
numbers were read. A flat region gives a focus response that is nearly
constant across the sweep, so pass one's per-pixel argmax is decided by noise
and can land anywhere, including 99 frames from its neighbours.

**P18 — MEASURED, visual. The mechanism is directly visible, and the shipped
gate is what suppresses it.** `tweezers-cpl__ELECTION-OUTLIER__1.png` shows, at
one location on a rigid subject: an election map that is a random mosaic
spanning the entire `0..99` sweep; the same region at `--gate 0`, where that
mosaic appears as visible patchwork; and at the shipped `--gate 4`, where
averaging over `mean n_eff = 46.6` frames removes most but **not all** of it —
a faint residual mottle survives into the default render. This unifies P10 with
P17: the gate-0 patchwork and the election speckle are one mechanism.

**P19 — ARGUED. Neither unreachable module obviously addresses the mechanism
found here, so wiring them is not the implied fix.** `robust.rs` acts at
election time on a frame that *disagrees* — a discrepant sample to be refused.
P17's mechanism is not disagreement but indifference: in a flat region no frame
meaningfully disagrees, and the argmax is a coin toss between near-identical
candidates. A discrepancy test has nothing to bite on. This is an argument from
what the module is documented to do, not a measurement of it running, and it
would be settled by wiring `robust` and measuring — which is a decision for the
owner of `merge.rs` and not for this milestone.

---

## 6. Patches

**None.** No instrument passed its registered promotion bar, so there is no
default to flip and nothing to route to an owning agent.

This is the deliverable. A patch would have been easy to justify — A4 misses by
`0.00084` dex on bee — and writing one would have meant narrowing a bar after
seeing the data, which is the one thing this project exists to refuse.

The change I would route if asked for the *most* defensible one is still
nothing. The nearest thing to an actionable finding is P14, and the correct
response to it is a measurement milestone, not a patch.

---

## 7. What this does NOT claim

- **It does not claim these instruments are useless.** It claims that at
  `--gate 4`, `--limit 100`, on three subjects, they do not clear a `0.010` dex
  bar. Photometric in particular never harms anything (P5) and may well be
  correct engineering whose benefit this metric cannot resolve (P7).
- **It does not claim the soft gate is harmful in general.** It fails B1 on one
  subject of three. On the other two its detail effect is within noise, and its
  flat-field benefit is real and visible. A future milestone that registers a
  flat-field bar rather than a detail bar could reach a different verdict
  honestly, and P4 is the number it should start from.
- **It does not adjudicate the lateral-CA correction.** `STREHL_FIX_CA` was
  never enabled in any arm, by instruction. Nothing here bears on the disputed
  1.444x over-correction.
- **It does not claim `STREHL_FIX_HALO` helps.** It was not measured. P14 is an
  inventory finding and P11 is an argument about artefact class, not evidence
  of a fix.
- **It does not describe the full bee-3-cpl stack.** bee-3-cpl was truncated to
  the first 100 of 299 frames. The most-elected frame was index 99 — the last
  frame of the truncated set, winning 31.55% of pixels — which means the sweep
  was still gaining focus at the cut and the merge was denied frames it wanted.
  The bee numbers describe a partial sweep.
- **It does not describe the aligned path in the M85 comparison.** P9 was
  measured with alignment disabled on both sides, deliberately, to avoid the
  `fit_to_cover` rescale (`0.9634` on bee) that would otherwise force a
  resampling into a sharpness measurement.
- **It does not claim four independent bars were cleared or failed.** B3 was
  degenerate given a zero control floor and restated B2 (section 3).
- **It does not claim the metric can see everything.** Q is a band ratio and is
  by construction blind to a global level change (P7). An instrument whose whole
  effect is a level change would read zero here and would deserve better.
- **It does not claim subject motion is absent from these captures.** P16
  refutes *my proxy* for motion, not motion itself. M89's `4.78%` figure is a
  measurement of value discrepancy beyond 8 sigma, which is a different
  statistic from election-index isolation, and nothing here contradicts it. A
  real motion measurement needs per-frame residuals, which this milestone did
  not compute.
- **It does not claim the election indeterminacy of P17 is what the owner is
  complaining about.** It is visible at `--gate 0` and mostly suppressed at the
  shipped `--gate 4`. The residual mottle in the A0 panel of P18's figure is
  real but small, and no bar was registered against it.
- **It does not claim wiring `robust` or `outlier` would help or harm.** P19 is
  an argument from documentation. Neither module was ever executed by this
  milestone, because neither can be.

---

## 8. Disciplines this milestone would add

**D-a. A crop window is evidence, so measure what it actually contains rather
than trusting the arithmetic that produced it.** This milestone's first contact
sheets were blank background. `uniform_filter` carries a running sum, so
`cval=np.nan` propagated NaN across the entire window-mean field; `argmax` over
an all-NaN array returned index 0 and every crop silently pinned to the
top-left corner of the frame. Nothing failed, no exception was raised, and the
pictures looked like a plausible smooth region. The fix that caught it was not
the NaN audit — it was asserting that the detail window's mean local structure
exceeds the flat window's, which read `1.0x` at identical coordinates and
aborted. A second, independent off-by-`CROP/2` error was found by the same
assertion. *Two* silent coordinate bugs, one guard.

**D-b. Guard on the signature of the harness bug, not on subject character.**
The guard above initially aborted whenever the detail/flat separation fell
below `3x`. That fired correctly on the bug (`1.0x`, both windows at the same
coordinate) and then fired again on foam at `1.43x` — where it was reporting a
true property of a subject with no flat region, not a defect. The discriminating
signature was *both windows at the same coordinate*, not the ratio. A guard that
conflates instrument health with subject character will be tuned away the first
time it is inconvenient.

**D-c. When a harness bug is found mid-campaign, prove the reported numbers were
independent of it rather than arguing that they were.** The crop windows feed
only the images; the masks come from whole-field quantiles. That is a sound
argument and it is not evidence. `verify_crop_independence.py` compared all
`132` metric values across every arm from before and after the fix: `0` differ.
Separately, `verify_report.py` re-derives all `36` deltas in section 4's table
from `scores.json` by (arm, subject) anchor, and `negctl_report.py` commissions
it by planting a one-digit defect and requiring RED — a verifier that has never
been shown to fail is not evidence either.

**D-d. A control floor of exactly zero makes a "3x the floor" bar degenerate,
and the honest response is to say so, not to count it as passed.** See
section 3.

**D-e. State a subject's metric power as a number before reading its verdict off
the table.** foam returns INCONCLUSIVE because its mask separation is `0.1249`
dex and `56.27%` of its detail-band variance is noise — decided by the
subject's structure, before any arm was compared. Without that number, foam's
twelve near-zero readings would have looked like twelve pieces of evidence that
the instruments do nothing.

**D-f. Give a proposed detector a subject on which the mechanism is physically
impossible, and believe the control over the hypothesis.** The election-map
motion proxy of P16 was built to find motion-won pixels and it produced a
confident-looking `3.306%` on the first subject. It was refuted by
`tweezers-cpl` — a rigid steel tool that cannot move between exposures — reading
`2.076%`. Without a rigid subject in the set, that number would have been
published as a motion rate. The control was available only because the subject
was chosen for a different reason (an occluding edge), which is an argument for
picking subjects that differ in more ways than the one under test.

**D-g. A statistic that reads exactly chance where the mechanism is absent is
worth more than the same statistic reading large where it is present.** P17's
concentration test reads `49.6%` and `57.1%` against a `20.0%` chance rate on
the two subjects with flat regions, and `20.1%` on the one subject that has
none. The null is what makes the two positives mean something; either alone
would be a number without a scale.

**D-h. When an instruction names the file you are to produce, the name encodes a
conclusion — do not adopt it before the measurement supports it.** ORCH asked
for crops named `<subject>__MOTION-ARTEFACT__<n>.png`. Producing them under
that name would have shipped "motion" as a finding on evidence that had already
refuted it. The frames ship as `ELECTION-OUTLIER`, and the discrepancy between
the requested and delivered filename is itself reported.

---

## 9. Images

`C:\dev\strehl-out\M116\images\`

Contact sheets, one per subject per crop region, every arm side by side at 1:1,
each panel labelled with its arm, the pinned commit and its metric values:

```
bee-3-cpl__contact-detail.png        tweezers-cpl__contact-detail.png
bee-3-cpl__contact-flat.png          tweezers-cpl__contact-flat.png
foam__contact-detail.png             foam__contact-flat.png
```

Individual crops and full renders are `<subject>__<arm>__{detail,flat,full}.png`
over arms `B0` (sharpest single frame), `M0` (pure selection, `--gate 0`), `A0`
(the shipped default) and `A1`–`A4`.

Crop windows were located on the `M0` arm, which is not one of the compared
arms, so the choice of what to look at was not made by an arm under test.
Exposure was solved once per subject by `--auto-exposure` on A0 and passed as a
literal to every arm including `B0` — bee `1.49`, foam `-0.32`, tweezers `1.13`
— so the arms differ in the merge and not in the gain applied to it.

The single most useful pair for the owner: `bee-3-cpl__M0__detail.png` against
`bee-3-cpl__A0__detail.png`. That is what the shipped gate already buys (P10).

The single most explanatory figure: `tweezers-cpl__ELECTION-OUTLIER__1.png`
(also `__2`, `__3`, and three for `bee-3-cpl`). Three panels at one location on
a **rigid** subject — election map, `--gate 0`, `--gate 4` — showing the
per-pixel argmax behaving randomly in a flat region and the shipped gate
suppressing most of the result (P17, P18).

---

## 10. Method, in brief

**Subjects**, chosen by looking at scout renders of eight candidates before
registering:

| subject | character | frames | why |
| --- | --- | --- | --- |
| bee-3-cpl | high-contrast insect, dense hairs, large flat white ground | 100 of 299 | the M111 complaint subject; maximum detail/flat separation |
| foam | low-contrast dense grey texture, no strong edges | 100 | the case where a gate has least to work with |
| tweezers-cpl | hard occluding edge, specular highlights, smooth field | 100 | occlusion is where an admission gate should matter most |

**Registration was frozen once per subject and shared by every arm.**
AGENTS.md rule 45 records that `strehl align` writes its sidecar into the
read-only capture library and caches a re-solve back over it — which, with
several agents live, no control can catch, because it contaminates treatment and
control identically. Each subject was aligned once to a scratch path and every
arm loaded that frozen file through `STREHL_WARPMAP`, which validates stack
identity and frame count and never caches back. Registration is therefore
bit-identical across arms by construction and cannot be a confound.

**Metrics.** On the default binned linear camera-native output, never on the
`--srgb` viewing file:

- `N` = log10 sd of a high-pass over the flattest 20% of pixels (noise band)
- `D` = log10 sd of the same high-pass over the most structured 20% (detail band)
- `Q` = `D - N`, a band ratio, deliberately scale-invariant

Masks come from a structure field computed on the `M0` arm, downsampled 4x
first so that mask ranking is driven by scene structure and not by the mask
arm's own pixel noise. Failure directions, per AGENTS.md rule 18: `Q` is blind
to a global level change (P7); `D` falls both for real detail loss and for noise
reduction inside the detail mask, which is why P3 decomposes it rather than
reading it directly.

**Environment hygiene.** All 15 `STREHL_*` variables are cleared before and
after every run, so no arm can inherit another's state. Every run logs its
commit, binary path, full argv, every environment variable read, exit code,
wall time, output byte count and SHA-256 (AGENTS.md rule 47). 63 runs, all
exit 0.

---

## 11. For the orchestrator

- No patch to route.
- M114, M115 and M116 are absent from the AGENTS.md milestone allocation ledger,
  which rule 41 requires at dispatch. I did not edit AGENTS.md; it is not an
  owned path for this milestone.
- The dispatch inventory for this milestone was stale on the soft gate (P13),
  and was corrected on `outlier`/`robust` at 19:24, after registration. The
  correction is honoured in section 5b as a disclosed post-hoc addendum; no
  registered bar moved.
- `outlier` and `robust` are recorded UNREACHABLE with line counts at both the
  pinned SHA and ORCH's HEAD (P15), as requested.
- The requested `MOTION-ARTEFACT` crops were **not** produced under that name.
  The motion reading was refuted by its own rigid-subject control (P16) and the
  mechanism was identified as flat-region argmax indeterminacy (P17). The
  figures ship as `<subject>__ELECTION-OUTLIER__<n>.png`. If ORCH still wants
  the motion question answered, it needs per-frame residuals, not an election
  map — that is a new milestone.
- The highest-value next milestone is a registered measurement of
  `STREHL_FIX_HALO` on an occluding edge (P14, P11).
- The soft gate deserves one more milestone with a flat-field bar rather than a
  detail bar, starting from ΔN `-0.02044` (P4). It should not ship on tonight's
  evidence.
- `experiments/ORCH-drift-check/reachability.py` was run, not edited.
