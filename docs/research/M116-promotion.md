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
undocumented instrument does: `STREHL_FIX_HALO`.

**Third headline, added after ORCH prioritised that fifth instrument above
everything else in the workstream (section 5d).** `STREHL_FIX_HALO` has now been
measured on four stacks, including both of M87's own. **It fails its deciding
pre-registered bar by a factor of six, and it fails it backwards.** The bar was
selectivity: the correction should act on an occluding edge and not on a bare
silhouette. Measured, it changes the halo index **`3.05x` more** on the stack
with *no* occluding background than on the stack with one. It is not that it
fails to tell a defect from an edge — on this pair it prefers the edge. And on
`flower-bud-with-background-fern-cpl`, one of the two stacks whose `84.6%`
removal figure is the case for shipping it, **it visibly destroys subject
texture**, replacing it with flat amoeba-shaped blobs. Verdict **KEEP-OFF**, and
the halo metric is not a quality metric.

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
| lateral-CA correction | see the CA table below | — | see the CA table below | **HOLD** | best-evidenced instrument in M116; CD1 fails on 2 of 4 subjects |
| soft gate, re-asked on the **background patchwork** | artefact visible, metric failed its plant | no artefact found | no artefact found | **NO INSTRUMENT** | section 5h; `G1` and `H1` both FAILED, so no recommendation is made despite the crops |

**Read the soft-gate rows together, because they disagree and the disagreement
is the point.** Campaign 1 judged the soft gate KEEP-OFF on a *detail* bar,
which was the wrong question: the instrument is aimed at flat and defocused
regions and was condemned on sharp ones. Section 5h re-asked it on the right
bar and found the artefact real, visible, and removed by the treatment — and
then failed to build a metric that could pass a plant. **`NO INSTRUMENT` is not
`KEEP-OFF`.** It means the question is still open and the pictures in
`C:\dev\strehl-out\M116\SOFTGATE-*.png` are currently the best evidence
anyone has.

The lateral-CA correction was measured on its own four `-cpl` stacks (section
5f), against the displacement that lateral CA physically is, so it gets its own
table. **The subjects split by whether the instrument could be calibrated at
all, and that split is the result:**

| subject | instrument | `RD_off` -> `RD_on` | CA removed | fine-structure cost | verdict |
| --- | --- | ---: | ---: | ---: | --- |
| `tweezers-cpl` *(TRANSFER, M110 never used it)* | **CALIBRATED** (+0.440 of +0.500) | −0.6861 -> +0.0332 px | **95.2 %** | `−0.00155` dex | **works** |
| `flat-on-ruler-cpl` | **CALIBRATED** (+0.485 of +0.500) | −0.7478 -> +0.0741 px | **90.1 %** | `−0.00101` dex | **works** |
| `bee-3-cpl` | **DEAD** (+0.015 of +0.500) | *void* | *void* | `−0.00169` dex | no number claimable |
| `flower-bud-…-fern-cpl` *(TRANSFER)* | **DEAD** (+0.120 of +0.500) | *void* | *void* | `−0.00184` dex | no number claimable |

| CA bar | result |
| --- | --- |
| CB3 — plant on the *chroma-excess* metric | **FAIL** (−16.45 %, and +104.05 % — wrong sign). Voids `+35.34 %` / `+66.79 %` |
| CD1 — plant on the *displacement* metric | **FAIL**, 2 of 4 subjects |
| CD2 — centre trap | **PASS**, 4/4, `\|RD\| <= 0.075 px` |
| CD3 — green null | **PASS**, `0.0 DN`, `0.0000 px`, `0.00000` of pixels moved |
| CD4 — `\|RD_on\| < \|RD_off\|` in support | **PASS** 4/4 literally; **2/2 on calibrated subjects**, incl. one transfer |
| CD7 — do-no-harm | **PASS**, 4/4, worst `−0.00184` dex |
| CB1 null / CB2 adversarial placebo | **PASS** — byte-identical, placebo run against the ON arm's own cache |

**The promotion rule fails on CD1 alone.** CD2, CD3, CD4 and CD7 all pass. And
CD1 is quantified `on every subject scored`, so it **cannot be rescued by
measuring more subjects** — bee's and fern's failures are permanent under a
universal quantifier. I had that render batch queued and cancelled it. Section
5g works through the arithmetic, states the admission-gate reading under which
the rule *would* be satisfied, and declines to adopt it, because choosing
between two readings of a bar after seeing which one the data favours is the
move pre-registration exists to prevent. **CA needs a new prereg in a new
milestone, not more rendering and not a code change.**

The occlusion-halo correction was measured on its own four stacks (section 5d),
so it gets its own table:

| instrument | bee-3-cpl | flower-bud-with-background-fern-cpl | flower-bud-alone-cpl (trap) | tweezers-cpl | verdict | decided by |
| --- | --- | --- | --- | --- | --- | --- |
| occlusion halo, delta 40 | KEEP-OFF | KEEP-OFF | KEEP-OFF | KEEP-OFF | **KEEP-OFF** | HB2 selectivity `R = 3.054`, bar `<= 0.50`, failed backwards |
| occlusion halo, delta 80 | KEEP-OFF | KEEP-OFF | KEEP-OFF | KEEP-OFF | **KEEP-OFF** | strictly worse than delta 40 on the registered index on 3 of 4 |

The dose ladder of section 5e does not change that verdict; it explains it, and
it finds two defects in the knob itself:

| finding | bee-3-cpl | flower-bud-with-background-fern-cpl | verdict | decided by |
| --- | --- | --- | --- | --- |
| `DELTA=0` is a silent alias for the shipped 40 | confirmed | not run | **DEFECT** | LB1, SHA `EEC72FA7CFE7` on both |
| `DELTA >= frame count` is a silent no-op reported as ON | confirmed | confirmed | **DEFECT** | `0 of 585886` and `0 of 573588` re-elected |
| ORCH's blur confound (treatment blurs the scored region) | **refuted**, `D = +0.14468` | **confirmed**, `D = -0.30177` | **SUBJECT-DEPENDENT** | P43, P44 |
| halo index degrades monotonically with dose | confirmed | confirmed | **CAUSED, not incidental** | LB3 PASS both |

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

powershell -File .\run_halo.ps1   # 30 renders, the occlusion-halo campaign
python score_halo.py              # -> halo\scores-halo.json
python bars_halo.py               # the section 5d bar table
python crops_halo.py              # 8 contact sheets

powershell -File .\run_ladder.ps1 # 17 renders, the DELTA dose ladder
python score_ladder.py            # -> halo\scores-ladder.json
python bars_ladder.py             # the section 5e bar verdicts
python crops_ladder.py            # 4 ladder contact sheets
python verify_ladder.py           # every section 5e number vs the raw data
python negctl_ladder.py           # commissions the verifier: 7/7 must be RED
```

`4beac73` was HEAD at dispatch and is no longer HEAD; other agents have
committed since. That is the point of pinning, not a defect. The binary was
built once, in that worktree, and never rebuilt mid-campaign.

**Registration was frozen before measurement.** `prereg.txt` is commit
`0235330`, made before any scoring run existed. The occlusion-halo contract is
`prereg-halo.txt`, committed before any halo arm ran, and the dose-ladder
contract is `prereg-ladder.txt`, commit `cc515f8`, committed before any ladder
arm ran.

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

## 5c. Addendum: the warp-cache poisoning check

**Also post-hoc**, prompted by ORCH at 20:24 after the campaign closed. It
changes no bar and no result. It tests whether the results are real at all.

**P20 — MEASURED. The campaign never used the warp cache, by construction, and
this is read from the source at the pinned SHA rather than from a `--help`
text.** `merge_cmd::alignment_for` at `4beac73`:

```rust
let Some(explicit) = std::env::var_os(WARPMAP_ENV) else {
    return align_cmd::load_or_solve(dir, paths, 0);   // the cached path
};
...
let map = WarpMap::load(&path)?;                       // direct load, no cache
```

`load_or_solve` — the entry point M97n found mis-keyed — is on the `else`
branch, reachable only when `STREHL_WARPMAP` is **unset**. Every arm in this
campaign set it, to a sidecar solved once per subject and thereafter read-only.
The cache was never read and never written. Separately, the M97n fix
`69f7b4c` (2026-08-24 13:41) **is** an ancestor of `4beac73` (17:33), confirmed
with `git merge-base --is-ancestor`, so the build carries the fix regardless.

**P21 — MEASURED. An adversarial poisoning attempt does not move a single byte,
and the probe used to test that is demonstrably live.** On bee-3-cpl:

| run | cache | hash | |
| --- | --- | --- | --- |
| COLD | private, empty | `478387EF2F9A` | equals the recorded campaign A0 |
| PRE-A2 | shared, soft gate on | `5D3461A99933` | equals the recorded campaign A2 |
| POISON | **that same shared cache**, default arm | `478387EF2F9A` | unchanged |
| PLANT | another subject's sidecar | refused, exit `1` | see below |

Running a differently-configured arm against a shared cache immediately before
the default arm changed nothing. The plant — pointing the default arm at
`tweezers-cpl`'s sidecar — was refused rather than silently served, with
`this warp map was fitted on stack "tweezers-cpl" (digest 392648f1c06e65b8) but
was applied to "bee-3-cpl" (digest 2a471653355ae126)`. Silent substitution is
the failure mode M97n describes, and on this path it is loud.

**P22 — MEASURED. Both A0 and A2 reproduce their campaign hashes exactly, hours
later, from a cold private cache in a separate process.** `478387EF2F9A` and
`5D3461A99933` were recorded during the campaign and re-derived by
`run_poison.ps1` afterwards. This is a stronger reproducibility claim than the
N1 null, which only re-ran within one campaign session.

**P23 — DERIVED. None of the four registered controls is a dead probe, and the
plant for each is already in the data.** Fact 1548's failure mode is a null
whose instrument was structurally incapable of expressing a difference. The
instrument here is the output SHA-256, and the same instrument on the same
wiring reads *different* for A1–A4. The tightest case is T2: it sets
`STREHL_SOFT_GATE=0` and reads identical to A0, and its plant is A2, **the same
environment variable with a different value**, which moves the hash to
`5D3461A99933`. So "`0` means off" is a real null and not an unwired one.

| control | reads | its plant | plant reads |
| --- | --- | --- | --- |
| P1-placebo | `= A0` | A1 `--photometric` | `0D2320544D4D` |
| N1 null | `= A0` | A1 `--photometric` | `0D2320544D4D` |
| T1 byte-inert dump | `= A0` | A1 `--photometric` | `0D2320544D4D` |
| T2 `SOFT_GATE=0` | `= A0` | A2 `SOFT_GATE=gaussian` | `5D3461A99933` |

**P24 — MEASURED. The retracted M99 `+6.88%` photometric figure was never used
here.** `prereg.txt` and this report contain no reference to it. The photometric
bars were set in absolute terms (`+0.010` dex) with no prior from M99, so
fact 1551's retraction leaves every number in section 4 untouched.

---

## 5d. Addendum: the occlusion-halo correction

ORCH dispatched this arm after the main campaign had closed, prioritising it
above everything else on the grounds that the halo "is the artifact that makes a
focus stack look wrong to a human" and that the owner's complaint is visual.
That reasoning is sound. The result does not support the instrument.

Bars were registered in `experiments/M116-promotion/prereg-halo.txt` and
committed **before any halo arm was run**, in their own commit. The premises
were read from the source at the pinned SHA per discipline 808, not from
`--help` and not from the dispatch brief. Arms: `H0` default, `H1`
`STREHL_FIX_HALO=1` (delta 40), `H2` delta 80, `H3` `STREHL_FIX_HALO=0` (trap),
plus a gate-0 pair on bee to approach M87's own terms.

### The registered bars

| bar | contract | measured | verdict |
| --- | --- | --- | --- |
| HB1 reproduction | bee `dHALO% <= -50%` | `+17.21%` at gate 4, `+19.24%` at gate 0 | **FAIL** |
| HB2 selectivity | `R <= 0.50` | `R = 3.054` | **FAIL, and backwards** |
| HB3 fine structure | `dQ >= -0.010`, delta 80 must move it | statistic was structurally `0`; repaired post-hoc | **VACUOUS as registered** |
| HB4 yoke noise | ratio rises `<= 20%` | ratio *fell* `3.55%` to `69.12%` | PASS, but one-sided and uninformative |
| HB5 trap | `STREHL_FIX_HALO=0` byte-identical to `H0` | identical on 4 of 4 | **PASS** |
| HB6 containment | no change beyond the 40 px yoke | 0-26 px on 3 subjects; `12 926` px, max `d = 89.0`, on tweezers | PASS on 3, unresolved on 1 |
| HB7 visual | inspect the crops and say | done, below | reported |

**The promotion rule registered in advance says HB2 failing means KEEP-OFF even
if every other bar passes.** HB2 failed by a factor of six.

### The measurements

| subject | `H(H0)` | `dHALO%` d40 | `dHALO%` d80 | bright-edge `dHALO%` | treated |
| --- | ---: | ---: | ---: | ---: | ---: |
| bee-3-cpl | `-0.16081` | `+17.21` | `+21.27` | `+36.12` | `7.109%` |
| flower-bud-with-background-fern-cpl | `-0.09300` | `+123.79` | `+125.84` | `+185.40` | `6.952%` |
| flower-bud-alone-cpl (trap) | `-0.05300` | `+378.10` | `+544.80` | `+165.81` | `3.190%` |
| tweezers-cpl | `-0.13421` | `+47.02` | `+26.60` | `-314.54` | `3.857%` |

| subject | `dD` treated d40 | d80 | control | yoke/out `H0` | `H1` |
| --- | ---: | ---: | ---: | ---: | ---: |
| bee-3-cpl | `-0.23689` | `-0.18446` | `+0.00000` | `3.6031` | `3.4752` |
| flower-bud-with-background-fern-cpl | `+0.24330` | `+0.38911` | `+0.00000` | `12.8286` | `4.7640` |
| flower-bud-alone-cpl | `-0.04380` | `+0.20130` | `+0.00000` | `6.1968` | `3.5605` |
| tweezers-cpl | `+0.80457` | `+1.01480` | `+0.00000` | `46.8945` | `14.4830` |

### Controls first

**P25. MEASURED.** The trap `H3` (`STREHL_FIX_HALO=0`) is byte-identical to the
default on all four subjects: bee `478387EF2F9A`, fern `182D38A74A4B`, alone
`75238075EACF`, tweezers `4881EC4EFA49`. Its plant is `H1`, the same variable
at a different value, which moves every one of those hashes. The off-switch is
a real null on live wiring, not an unwired path.

**P26. MEASURED.** `H0` reproduces the main campaign's `A0` hash exactly on both
subjects the two campaigns share — bee `478387EF2F9A` and tweezers
`4881EC4EFA49` — from a separate process, hours later, against warp sidecars
solved once and loaded read-only. Cross-campaign determinism holds.

**P27. MEASURED.** The fine-structure control reads `+0.00000` on all four
subjects, to five decimals, *after* being repaired. Before repair it read
`+0.10127` on bee for an arm whose control pixels are byte-identical to the
reference, because `highpass()` is a 5 px box and an untouched pixel within
2 px of a touched one still changes value. The control set is now the untreated
set eroded by the filter's support.

### The findings

**P28. MEASURED. The deciding bar failed backwards.** `dHALO%` is `+123.79` on
`flower-bud-with-background-fern-cpl`, which has an occluding background, and
`+378.10` on `flower-bud-alone-cpl`, which does not. `R = 3.054` against a bar
of `R <= 0.50`. M87's own module predicts non-selectivity at `R ~ 0.80` from
synthetic data; on this real matched pair the correction acts **three times more
strongly where there is no occlusion to fix**.

**P29. MEASURED. No bright rim exists in the linear background profile of these
renders for the registered index to remove.** The background radial profile on
bee is monotonic in distance from the silhouette, rising from `-0.25065` at
`d = 2` to `+0.04327` at `d = 98` with no local maximum anywhere. The
correction drives the near band further down, by `-0.032` to `-0.037` across
`d = 2..38`, and is exactly `0.00000` from `d = 46` outward. So under an
independently defined index the correction does not null a rim; it deepens an
already-monotonic skirt. `dHALO%` is positive — worse by the registered sign
convention — on all four subjects and at both gates.

**P30. MEASURED. Where a real positive rim does exist, the correction
overshoots it grossly.** `tweezers-cpl` is the only subject whose bright-edge
index is positive at all, `+0.02390`. The correction takes it to `-0.19732`:
past zero and roughly nine times the original excursion in the opposite
direction. The one case in this campaign that matches the instrument's stated
premise is also the case where it overcorrects hardest.

**P31. MEASURED, and the image the owner should look at first.** On
`flower-bud-with-background-fern-cpl` — one of the two stacks that supply the
`84.6%` figure justifying the instrument — the correction at the shipped delta
replaces large irregular regions of the bud's surface with flat, blurred mush,
in amoeba-shaped islands tens of pixels across. The mechanism is visible in the
mask: `foreground_mask` assumes "the subject is darker than its background", so
the *bright* parts of a bright subject are classified as background, fall within
the 40 px yoke of the dark parts, and are re-elected from frames at least 40
frames away from their own focus frame. The docstring states the assumption; no
one had checked it against a real bright subject.
See `flower-bud-with-background-fern-cpl__contact-halo-edge1.png`.

**P32. MEASURED. On the same stack, at the same setting, a different crop shows
the instrument doing exactly what it claims.** In
`flower-bud-with-background-fern-cpl__contact-halo-edge2.png` the pale rim
around the bud is visibly reduced and the edge reads cleaner. The correction is
not uniformly destructive; it is *indiscriminate*. Where the dark-subject
assumption holds it helps, and where it does not it guts the subject, on one
stack, in one run, at one parameter value.

**P33. MEASURED. The documented delta-40-versus-80 trade-off does not reproduce
as a monotone detail loss.** M87 chose `40` as "the largest value that did not
visibly soften hairs and claws". Scored on the pixels *both* deltas treat, delta
80 is *less* negative than delta 40 on bee (`-0.18446` against `-0.23689`) and
*more positive* on the other three. Whatever `80` does that `40` does not, it is
not a monotone reduction in detail amplitude by this statistic.

**P34. MEASURED. On bee the correction erases out-of-focus hairs.** In
`bee-3-cpl__contact-halo-edge1.png` the wispy hair strands crossing the
background in `H0` are replaced in `H1` by smooth mottled patches, consistent
with `dD` on treated pixels of `-0.23689`, a 42% fall in high-pass amplitude.
In `bee-3-cpl__contact-halo-edge2.png` a smooth out-of-focus gradient acquires
hard-edged polygonal facets and visible seams that are not present in `H0`. That
second artefact is a *new* defect introduced by the correction, not a failure to
remove an old one.

**P35. MEASURED, ATTRIBUTION UNRESOLVED.** On `tweezers-cpl`, `12 926` changed
pixels lie beyond the stated 40 px yoke, out to `d = 89.0`, against 0-26 px on
the other three subjects. I cannot cleanly attribute this between the
implementation exceeding its documented reach and my own reimplementation of
`foreground_mask` disagreeing with the tool's on a subject that is `70.35%`
foreground. Resolving it needs the tool's own mask dumped, which needs a code
change I am not permitted to make. Flagged for whoever owns `halo.rs`.

**P36. ARGUED.** The `87.9%` and `84.6%` removal figures are not evidence of
quality, and the module already contains the reason: on a synthetic region with
no defect at all the same metric "improves" by `63.9%` while RMSE against truth
rises `558.4%`. A metric that moves that far where there is nothing to fix
cannot certify a fix. This campaign's contribution is to show the same
non-selectivity on real captures, at `R = 3.054`, and to put a picture next to
it.

### Verdict

**KEEP-OFF**, by the rule registered before the data existed. Not
OFFER-AS-CHOICE either, on the strength of P31: an option that silently
destroys subject texture on one of the two stacks used to justify it should not
be offered without a warning attached to it. The module's own self-assessment —
cosmetic, anti-fidelity, off by default — is **correct and should stand**. The
honest summary is that M87 already knew this and wrote it down; what was missing
was a measurement on a real render, and the measurement agrees with the caution
rather than with the headline figure.

No patch is recommended. The instrument is already off.

---

## 5e. Addendum: the DELTA dose ladder

**Registered in `experiments/M116-promotion/prereg-ladder.txt`, committed as
`cc515f8` before any ladder arm was rendered.** ORCH's objection, in its own
terms: the correction forbids frames within `DELTA` of the local focus frame, so
the treated neighbourhood is rebuilt from more defocused ones; the treatment
therefore blurs the exact region in which the halo is scored, and a brightness
excess near a silhouette falls under blur alone. A binary on/off A/B cannot
separate the two. The remedy specified was a dose ladder with a fine-structure
curve at every rung, read between adjacent rungs rather than against off.

The objection is correct as a hypothesis and the ladder was the right
instrument. **It is confirmed on one subject and refuted on the other**, and
the ladder also found two silent no-ops in the knob it was run on.

### The knob's own defects, found before the ladder was designed

**P37. MEASURED. `STREHL_FIX_HALO_DELTA=0` renders byte-identical to the
shipped `DELTA=40`, silently.** `delta_in_use()` is
`env::var(..).ok().and_then(parse::<u16>).filter(|d| *d > 0).unwrap_or(DELTA)`.
The `.filter(|d| *d > 0)` discards zero and `unwrap_or(DELTA)` substitutes 40.
Predicted from source, then measured: bee at `DELTA=0` hashes `EEC72FA7CFE7`,
bee at `DELTA=40` hashes `EEC72FA7CFE7`, and off hashes `478387EF2F9A`. The
tool's own report prints `delta 40 frames` when 40 was never asked for. The
same fallback swallows any unparseable value, so a typo in the value renders
the default. **The `0/10/20/40/80` ladder as originally specified would have
measured 40 twice and reported a flat bottom rung that is an artefact of one
filter clause.** This is registered bar **LB1: PASS**.

**P38. MEASURED. When `DELTA` reaches the frame count the correction becomes a
total no-op and still reports itself as ON.** At `--limit 100`, `DELTA=160`
makes `allows(s,k) = |k - kf| >= 160` unsatisfiable for every frame. The tool
reports `0 of 585886 treated pixels re-elected; 585886 kept their original
value`, prints `halo fix : ON (STREHL_FIX_HALO=1). delta 160 frames`, exits 0,
and writes a file byte-identical to off. Both ends of the knob's range are
silent no-ops and neither is diagnosed as one.

**P39. MEASURED. At the documented `DELTA=80`, a large share of the yoke is
silently left untreated at this frame count.** Bee: `66265 of 585886` treated
pixels (**11.31 %**) kept their original value. Fern: `156036 of 573588`
(**27.20 %**). `Fix::undecided` counts exactly this and the tool prints it.

**P40. DERIVED. The dose is `DELTA` relative to the frame count, not `DELTA`.**
From P38 and P39: the fraction of the yoke that can be treated at all depends on
how many frames sit outside the forbidden band, which depends on the stack
depth. M87's documented `DELTA=80` result was measured on 299 frames; at
`--limit 100` the same setting is a partly-degenerate configuration. A user who
stacks 60 frames and one who stacks 300 get materially different corrections
from the same number with no indication. This is a caveat on my own ladder's
top rungs as much as on M87's.

### The ladder

All arms `--limit 100`, `--gate 4`, linear, frozen warps. `dHALO%` is the
addendum-2 halo index against off; positive means the index got **worse**.
`D` and `D_or` are log10 high-pass amplitude against off over the treated set,
`D_or` restricted to oriented content (structure-tensor coherence `>= 0.6`,
selected on off); negative means detail **lost**.

| subject | rung | delta | `dHALO%` | `D` | `D_or` | re-elected |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| bee-3-cpl | L1 | 1 | `-2.18` | `+0.14468` | `+0.14505` | 585886 |
| bee-3-cpl | L5 | 5 | `+3.59` | `+0.08641` | `+0.08600` | 585886 |
| bee-3-cpl | L10 | 10 | `+6.44` | `+0.03344` | `+0.01474` | 585886 |
| bee-3-cpl | L20 | 20 | `+11.13` | `+0.06231` | `+0.03114` | 585886 |
| bee-3-cpl | H1 | 40 | `+17.21` | `+0.05740` | `+0.02661` | 585886 |
| bee-3-cpl | H2 | 80 | `+21.27` | `+0.11914` | `+0.09706` | 519621 |
| bee-3-cpl | L160 | 160 | `-0.00` | `+0.00000` | `+0.00000` | 0 |
| fern | L1 | 1 | `-7.38` | `+0.00319` | `+0.02011` | 573588 |
| fern | L5 | 5 | `+5.07` | `-0.21843` | `-0.12387` | 573588 |
| fern | L10 | 10 | `+26.46` | `-0.26812` | `-0.15270` | 573588 |
| fern | L20 | 20 | `+64.00` | `-0.29321` | `-0.19099` | 573588 |
| fern | H1 | 40 | `+123.79` | `-0.30177` | `-0.22916` | 573588 |
| fern | H2 | 80 | `+125.84` | `-0.06574` | `-0.05261` | 417552 |
| fern | L160 | 160 | `-0.00` | `+0.00000` | `+0.00000` | 0 |

**P41. MEASURED. The treated region is identical at every rung, so the ladder
compares dose and nothing else.** Predicted from source: `Plan::build` fills
`treated` from `mask` and `YOKE` only and `delta` appears nowhere in the
predicate; `YOKE` is a `const` with no override; the mask comes from pass one,
which precedes the correction. Measured off the tool's own per-arm report:
13 gate-4 arms on bee all report `585886` treated, 10 on fern all report
`573588`. Registered bar **LB6: PASS**. My independent reconstruction of
`foreground_mask` reads `585894` and `573594`, `+8` and `+6` px adrift
(`0.0014 %`, `0.0010 %`) because scipy labels 8-connected and `halo.rs` labels
4-connected; the bar is decided on the tool's number.

**P42. MEASURED. The halo index degrades monotonically with dose on both
subjects.** Bee `-2.18 -> +3.59 -> +6.44 -> +11.13 -> +17.21 -> +21.27`; fern
`-7.38 -> +5.07 -> +26.46 -> +64.00 -> +123.79 -> +125.84`. Every live step
moves the same way on both stacks. Registered bar **LB3: PASS** (one violation
each, both the dead rung `L160`). A monotone dose-response is much harder for a
confound to imitate than a single on/off difference, so this upgrades
addendum 2's finding from a difference to a **caused** one: the correction, in
proportion to how hard it is applied, deepens the near-silhouette band relative
to the far background. Since addendum 2 established there is no bright rim in
these renders' background profile at all, that is a *dark* halo being created
where none existed, not a bright one being removed.

**P43. MEASURED. On bee the correction does not blur — it adds high-frequency
content.** `D` is **positive at every live rung**, peaking at `+0.14468` dex at
`DELTA=1`, which is a `39.6 %` **rise** in high-pass amplitude over the treated
band. `D_or`, on oriented content, is positive too (`+0.14505` at `DELTA=1`,
`+0.02661` at the shipped 40). **ORCH's blur confound cannot be operating on
this stack**, because the quantity it predicts should fall, rises.

**P44. MEASURED. On fern the correction blurs heavily, monotonically, and the
confound is real.** `D` falls `+0.00319 -> -0.21843 -> -0.26812 -> -0.29321 ->
-0.30177` across `DELTA = 1, 5, 10, 20, 40`. At the shipped 40 that is a
**50.1 % loss of high-pass amplitude** in the treated band, and `-0.22916` dex
(**41.1 % loss**) on oriented content specifically. Registered bar **LB2** is
**FAIL as registered on both subjects** (2 violations each), but the disclosed
live-rung variant is **1 violation on fern** — and both fern violations are at
or after `H2`, the rung where 27.20 % of the yoke silently falls back
(P39). Over the rungs where the tool actually treats the whole yoke, fern's
blur is perfectly monotone in dose. On bee, LB2 fails for a substantive reason:
there is no blur to be monotone in.

**P45. DERIVED. The mechanism of P43 is that the correction substitutes a
single frame's raw samples into an averaged image.** `Pass::fold` copies
`[top[2x], top[2x+1], bot[2x], bot[2x+1]]` from the winning frame's quad — it
selects, it does not average. At `--gate 4` the untreated surroundings are an
average over `n_eff` of order 23, while the treated band becomes single-frame
raw. The correction therefore injects single-frame noise into a denoised
neighbourhood, which raises high-pass amplitude and produces the visible seams
and patch boundaries. **M87 measured at `--gate 0`, where the baseline is
itself 100 % singleton, so this cost is identically zero in M87's
configuration and appears only at the shipped gate.** `halo.rs` anticipated
exactly this and called it "an additional, unmeasured cost"; it is now
measured.

**P46. ARGUED. The blur confound is subject-dependent, so no single control
retires it.** It dominates on fern (P44) and is absent on bee (P43). The
difference tracks what the yoke contains: fern's yoke is full of in-focus
background fern that defocuses badly when its own focus frames are forbidden,
while bee's yoke is smooth out-of-focus background where the substituted frame
differs mainly in noise. A blur-matched placebo calibrated on one of these
stacks would be mis-calibrated on the other. This is handed to M111, which owns
the metric audit; these per-rung curves are the input it needs.

**P47. MEASURED. Registered bar LB4 is VOID by premise failure, and its
arithmetic would have read PASS.** `X = dHALO% / (-D)` was registered as "how
much halo the rung buys per unit of detail it spends". On bee it is not
formable at any rung (`D >= 0` throughout — no detail was spent). On fern it is
formable and reads `X(L5) = +23.23`, `X(L10) = +98.68`, `X(L20) = +218.27`,
`X(H1) = +410.23`, `X(H2) = +1914.10`, spread `82.41`, which clears the
registered `>= 2.0` bar. **But every formable rung has `dHALO% > 0`: no rung
buys any halo, so `X` is a ratio of two losses and is not an exchange rate at
all.** Reported as VOID rather than PASS, with the arithmetic shown. A bar can
be arithmetically satisfiable while its premise is false — the same class of
defect as the vacuous HB3 of addendum 2, caught this time by writing the
premise into the bar's own text rather than only its formula.

**P48. MEASURED. The dead rung is the vacuity plant the null needed.**
Registered bar **LB5: PASS**. `L160` reads exactly `+0.00000` on `D`, `D_or`
and `dHALO%` while every live rung on the same wiring reads up to `0.30177`, so
the statistic demonstrably both can and cannot move, on the same subject and
the same code path. Disclosed degeneracy: the *untreated control* reads exactly
`0.000000` at every rung because control pixels are byte-identical to off, which
makes the registered "10x the control" clause trivially satisfiable; it is the
dead rung, not the control, that evidences sensitivity here.

### What the ladder does to the picture

`C:\dev\strehl-out\M116\images-ladder\`, four sheets, all 1:1 crops of sRGB
views at a frozen exposure, windows chosen on the off arm.

- `bee-3-cpl__ladder-SILHOUETTE-edge.png` — **the most honest single image in
  this milestone.** Four panels: off, `DELTA=1`, `DELTA=40` (shipped),
  `DELTA=160`. At `DELTA=1` the pale fringe along the leg is *brighter* than
  off. At the shipped `DELTA=40` **the fringe is genuinely gone — the owner can
  see that with his own eyes** — but the smooth background it sat in has been
  replaced by visibly blotchy patches with hard boundaries and a hard vertical
  seam. `DELTA=160` is indistinguishable from off, as P38 requires. Mean
  `|delta|` against off, printed on each panel: `0`, `3`, `0` DN/255.
- `bee-3-cpl__ladder-ORIENTED-fine-structure.png` — the same four rungs on
  oriented content in the yoke. The shipped rung carves flat amoeba-shaped
  patches out of what was a smooth gradient. This is P43 and P45 made visible:
  not softening, but patchwork.
- `flower-bud-with-background-fern-cpl__ladder-SILHOUETTE-edge.png` and
  `...__ladder-ORIENTED-fine-structure.png` — off versus the shipped `DELTA=40`.
  Whole regions of textured bud surface are replaced by flat mush with hard
  irregular borders; mean `|delta|` is `8` DN/255. This is the `-0.30177` dex
  of P44 in picture form.

**On ORCH's question 3 — does `DELTA=40` cost visible fine detail?** On bee, at
1:1, it does not soften hairs; it stipples and seams the background around them.
On fern it destroys texture outright. Either way the answer to "is 40 safely
below the threshold at which 80 was said to soften" is that **the threshold is
not the right frame**: the shipped dose already damages both stacks, in two
different ways, and neither damage is the softening that `DELTA=80` was rejected
for.


---

## 5f. Addendum: lateral chromatic aberration — the first instrument that works

Contract: `prereg-ca.txt` @ `188b55c`, and `prereg-ca2.txt` @ `bc38182` after the
first instrument failed its own plant. Both were committed before the results
they govern existed. Four `-cpl` subjects at the shipped `--gate 4`, `--limit
100`, frozen `STREHL_WARPMAP`, private cache per arm, 21 arms, all exit 0.

**Lead with the failures, because there are two and they are mine.**

### P49. THE REGISTERED METRIC FAILED ITS OWN PLANT, AND THAT VOIDED THE POSITIVES IT HAD ALREADY PRODUCED

`prereg-ca.txt` registered a chroma-excess metric and, with it, CB3: displace R
radially outward by 0.5 px and require `dX%` to read `<= -20%`. I predicted it
would pass and wrote "if it fails, the campaign stops here."

| subject | CB3 plant reads | bar | |
| --- | ---: | ---: | --- |
| `flat-on-ruler-cpl` | **−16.45 %** | ≤ −20 % | **FAIL** |
| `bee-3-cpl` | **+104.05 %** | ≤ −20 % | **FAIL — wrong sign** |

The diagnosis, which condemns my metric and not the correction: on `bee-3-cpl`
the excess baseline is **`X_off = −133.0 DN`, negative**. The construction
assumes chroma peaks at edges and decays to a clean far field. On a bee that is
false — the subject is large and strongly coloured, so median `|R−G|` five
pixels from an edge is dominated by *subject colour* and exceeds the edge value.
**A percentage reduction of a negative baseline is not a reduction of anything.**

By the time the plant failed, the broken metric had already produced
`+35.34 %` (bee) and `+66.79 %` (flat-on-ruler) — numbers that flatter the
correction and sit encouragingly near M110's 61.0/58.7. **Both are VOID and are
not reported as results.** CB4, the centre trap, failed at −4.05 % against a
±3.0 bar and is void by the same defect, being a ratio of the same quantity.
This is fact 1548's failure mode caught in the direction it is meant to be
caught in: by the plant, before publication, at the cost of the campaign's own
headline.

### P50. THE REPLACEMENT INSTRUMENT MEASURES THE DISPLACEMENT THAT LATERAL CA PHYSICALLY IS

Lateral CA is not a colour, it is a *geometry*: red is imaged at a slightly
different magnification from green, displaced radially in proportion to radius.
So `prereg-ca2.txt` measures that displacement directly — sub-pixel shift of R
against G by phase correlation, per annulus, per sector, projected radially. It
has a true zero, it cannot acquire a negative baseline, and phase correlation
keys on *structure*, so a flat yellow region cannot masquerade as a fringe.

### P51. THE INSTRUMENT IS CALIBRATED ON TWO SUBJECTS AND DEAD ON THE OTHER TWO — AND THAT DISTINCTION IS THE RESULT

CD1 required a planted **+0.500 px** displacement to be recovered to ±0.10 px.

| subject | planted +0.500 px recovered as | radial worst err | verdict |
| --- | ---: | ---: | --- |
| `flat-on-ruler-cpl` | **+0.485** | 0.085 px | **CALIBRATED** |
| `tweezers-cpl` | **+0.440** | 0.075 px | **CALIBRATED** |
| `bee-3-cpl` | **+0.015** | 0.330 px | **DEAD** |
| `flower-bud-with-background-fern-cpl` | **+0.120** | 0.310 px | **DEAD** |

**CD1 therefore FAILS as registered**, which required every subject scored.

The two dead subjects are organic and three-dimensional: much of each
correlation window is low-structure bokeh, so there is nothing for the
correlator to key on. The two calibrated subjects are flat and densely
textured.

**The consequence is the point.** `bee-3-cpl`'s `Q = 0.400` and fern's
`Q = 0.330` are **not small effects — they are VOID**, readings of an
instrument that demonstrably cannot see a half-pixel shift on those subjects. A
campaign that reported them as "CA helps less on organic subjects" would have
published an artefact of its own correlator as a property of the owner's
photographs.

### P52. ON THE SUBJECTS WHERE IT CAN BE MEASURED, THE CORRECTION REMOVES 90.1 % AND 95.2 % OF LATERAL CA

Radial R-vs-G displacement, in-support band `0.55 <= r <= 0.788`, linear
renders, calibrated subjects only:

| subject | `RD_off` | `RD_on` | removed | implied factor |
| --- | ---: | ---: | ---: | ---: |
| `flat-on-ruler-cpl` | **−0.7478 px** | **+0.0741 px** | **90.1 %** | 1.099× |
| `tweezers-cpl` *(TRANSFER)* | **−0.6861 px** | **+0.0332 px** | **95.2 %** | 1.048× |

`tweezers-cpl` is a subject **M110 never used**, and it is the better of the
two. That is the transfer result the campaign was built to get.

The "implied factor" is how far the correction moved red divided by how far it
needed to: `0.8219 / 0.7478` and `0.7193 / 0.6861`. Both land at or just below
**M107/M114's disputed 1.06–1.25× over-correction band**, reached by an
instrument that knows nothing about their dispute. I do not adjudicate it; I
report that a third method sees the same mild overshoot, and that both arms end
*past* zero rather than short of it.

### P53. IT COSTS NO MEASURABLE FINE STRUCTURE, AND IT PROVABLY DOES NOT TOUCH GREEN OR BLUE

CD7, worst of R / B / luminance on oriented content (coherence ≥ 0.6):

| subject | `D_R` | `D_B` | `D_L` | worst | bar −0.02 |
| --- | ---: | ---: | ---: | ---: | --- |
| `bee-3-cpl` | −0.00010 | +0.00000 | −0.00169 | −0.00169 | **PASS** |
| `flat-on-ruler-cpl` | −0.00101 | +0.00000 | +0.01031 | −0.00101 | **PASS** |
| `tweezers-cpl` | −0.00155 | +0.00000 | +0.00450 | −0.00155 | **PASS** |
| `flower-bud-…-fern-cpl` | −0.00184 | +0.00000 | +0.00067 | −0.00184 | **PASS** |

This is the sharpest contrast in M116. The halo correction destroyed **50.1 %**
of high-pass amplitude on fern (§5e). The CA correction costs at most
**0.42 %**, on the same subjects, measured by the same instrument. *That* is
what a correction with an evidenced coefficient looks like next to one without.

`D_B = +0.00000` **exactly**, on all four subjects, is not rounding. It is
`eps_b: None` in the profile, which `optics.rs:162-168` documents as
deliberate: M107 measured red's coefficient and never measured blue's, and "an
unmeasured coefficient is absent rather than zero". The render confirms the
source from the other side. **Any residual blue/cyan fringing is untouched by
this correction and is out of its scope.**

### P54. THE TRAP MY TRAP CAUGHT WAS MY OWN SOURCE READING

CB4 was premised on lateral CA being purely radial, so the frame centre must not
move. Reading `optics.rs` I then found `A7C2_FE100GM_2XTC_X4CPL.translation =
(0.6294, −0.4240)` and `compose` applying it — a **uniform 0.7589 px red shift
that does not vanish at r = 0** — and concluded my premise was wrong.

I measured it before writing that up. **The red plane's displacement at the
frame centre is 0.0224 px**, against 0.7589 px if the translation were applied
and ~1.5 px for the "absolute coordinates" failure mode the docstring warns of.
The source then confirmed the measurement: `profile_from_setting`
(`optics.rs:456-458`) resolves the key to `A7C2_FE100GM_2XTC_X4CPL_RADIAL`,
whose translation is `(0,0)`. **The translation is recorded as provenance and
not applied.** The measurement corrected my source reading, and I have kept both
in this order because the reverse order is how a confident misreading gets
published.

CD2, the re-premised trap, **PASSES**: `|RD(centre)| <= 0.075 px` in both arms
on all four subjects.

### P55. CONTROLS, BEFORE THE POSITIVES

| control | result |
| --- | --- |
| **CB1 null** — same arm, cold private cache | **byte-identical, 2/2** |
| **CB2 placebo** — same config, different output path, deliberately reusing *the ON arm's* cache | **byte-identical to OFF**, while ON differs |
| **CD3 green null** — green has no coefficient | `max\|dG\| = 0.0 DN`, **0.00000** of pixels moved, displacement `+0.0000 px` |
| **CD2 trap** | PASS, 4/4 |
| **CD1 plant** | **FAIL — 2 of 4** |

The placebo is the strongest single credential here: it was run *deliberately
against the ON arm's cache directory* — the M97n poisoning scenario staged on
purpose — and came back byte-identical to OFF while the ON arm differed.

### P56. THE HONEST VERDICT: HOLD, BY MY OWN FROZEN RULE

`prereg-ca2.txt` says recommend a default flip only if CD1 **and** CD2 **and**
CD3 **and** CD4 **and** CD7 pass. **CD1 failed on two of four subjects.** So I
do **not** issue a default-flip recommendation, and I am not going to narrow
CD1 to the subjects it passed on in order to manufacture one.

What I can say, and it is the strongest positive statement in M116:

> On every subject where the instrument could be calibrated, the lateral-CA
> correction removed **90.1 %** and **95.2 %** of the measured aberration, one
> of them a subject the coefficient was never fitted against, at a fine-structure
> cost of at most **0.42 %**, with a byte-identical null, a byte-identical
> adversarial placebo, a passing trap, and a green channel that provably does
> not move.

**What would convert HOLD into a recommendation:** the same 5 arms on two or
three more flat, densely textured `-cpl` subjects — `couch-fibers-cpl`,
`highly-angled-ruler-mm-cpl`, `lead-1-cpl` — where the plant should calibrate.
If CD1 passes there and CD4 holds, the rule is satisfied on its own terms. That
is roughly 40 minutes of rendering and it is the single highest-value thing
left in this milestone.

**And the gear caveat is not weakened by any of the above.** EXIF confirms
`ILCE-7CM2` + `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter` on **all 23**
subjects in `D:\personal\macro`. It cannot confirm the **X4 CPL**, because a
filter leaves no metadata. The profile's fourth element rests on the owner's
`-cpl` filename convention alone. The binary parses no camera identity, so a
default-on CA would apply a coefficient measured on one optical path to
photographs taken on any other.

### P57. THE PICTURES

`tweezers-cpl__CA-4x.png` is the one to look at first. The OFF panels carry
dense red/cyan speckle across the whole metal texture; the ON panels are
essentially neutral grey. On `bee-3-cpl` — where the *instrument* is dead but
the *eye* is not — the cyan fringes along the wing edge and the leg silhouettes
are clearly reduced, and the hairs are not softened, consistent with
`D = −0.00169`. **The instrument being dead on bee does not mean the effect is
absent there; it means my correlator could not put a number on it.** The crops
are captioned accordingly, and none of them is captioned as sharpening: per
M110 §16.4 the fringes get **fainter, not thinner**.

Crop windows are ranked by **green-plane** gradient energy at `r >= 0.55`.
Green is measured to move `0.0000 px` between the arms, so the ranking is
identical in both by construction and cannot have been chosen to flatter either.


---

## 5g. Addendum: my own promotion rule is now unsatisfiable, and I am not going to fix that by measuring more

This section exists because the obvious next move is available, cheap, and
would have converted the milestone's only positive result from HOLD into a
recommendation — and it is not legitimate. I had it queued. I am recording why
I am not making it, because the reasoning is more useful than the render would
have been.

**P58. CD1, as registered, can no longer pass, and no additional measurement
can make it pass.** Its text is `PASS = ... within +/-0.10 px of the planted
+0.50 px, **on every subject scored**`. `bee-3-cpl` (`+0.015`) and
`flower-bud-with-background-fern-cpl` (`+0.120`) are scored, and they failed.
Under a universal quantifier, a failure is permanent: adding
`couch-fibers-cpl`, `highly-angled-ruler-mm-cpl` and `lead-1-cpl` would give
five passes and two failures, and `∀` does not care about the ratio. **The plan
recorded in my own handoff — "re-run the five arms on three flat subjects, CD1
passes there, HOLD converts" — is arithmetically wrong about my own bar.** I
checked the frozen text before spending the forty minutes rather than after,
and this is the only reason the error is a paragraph instead of a retraction.

**P59. The defect is in how I registered the plant, not in the instrument or
the data.** A plant is naturally a **per-subject admission gate**: it asks "can
this instrument read this subject at all?", and a subject that fails it
contributes nothing — its readings are void, which is exactly how §5f treats
bee and fern. That is a *filter*. I registered it as a *global deciding bar*.
Under the gate reading the campaign has two admitted subjects, both passing
CD4, one of them a transfer subject, and the promotion rule is satisfied. Under
the registered reading, it is not. **The two readings disagree about the
headline verdict of this milestone, and I registered the stricter one.**

I am not switching to the gate reading. Choosing between two readings of a bar
*after seeing which one the data favours* is precisely the move the
pre-registration exists to prevent, and it would be a worse failure than the
HOLD. The verdict stays **HOLD**. The gate reading is stated here so a reader
can see exactly what is being given up and check my arithmetic, and it is
**not** claimed as a result.

**P60. The same document registered the same class of bar both ways, and the
inconsistency binds against the correction.** CD4 reads `on at least 3 of the 4
subjects`; CD1 reads `on every subject scored`. Both were written in one file,
by me, within an hour. Note that transplanting CD4's proportional form onto CD1
does *not* rescue it either: CD1 passed on 2 of 4, and `>= 3 of 4` fails at 2.
**There is no reading of my own prereg under which CD1 passes.** That is worth
knowing, because it means the universal quantifier is not the whole problem.
The honest count is that the instrument is dead on half the subjects I chose,
and that is a real limitation of a phase-correlation displacement reader on
organic 3-D subjects, where much of each correlation window is low-structure
bokeh. It does not go away under any quantifier.

**What the correct repair looks like, and why it is not mine to do.** A new
prereg, in a new milestone, written before its data exists, that registers
three things separately: (a) the plant as an admission gate with its threshold,
(b) the *minimum number of admitted subjects* required for a verdict, and (c)
the primary bar over admitted subjects only. Subject selection must be
registered too, and it must include organic subjects, so the milestone cannot
quietly become "the correction works on flat test charts". Re-running M116's
arms under that prereg would be sound. Re-running them under *this* one would
not be, and that is the distinction ORCH needs when it routes this.

**D-t (proposed discipline). Register a plant as an admission gate with a
registered minimum admitted count, not as a bar quantified over every subject
scored.** Under `∀ subjects scored`, every subject you add is pure liability —
it can only lose — and one failure is unrecoverable by any amount of further
measurement, which converts "measure more" from the correct response into an
unavailable one. Under a bare "N of M", a dead instrument's void readings get
counted as data. The gate plus a registered admitted-count is the only form
that survives both.

**P61. THE VERIFIER FOR THIS SECTION WAS WRONG UNTIL ITS OWN NEGATIVE CONTROL
BROKE IT, AND THE BLIND SPOT WAS A DUPLICATE**

`verify_ca.py` re-derives all of §5f from the artefacts and located every claim
at an anchored site: **100 checks, GREEN.** `negctl_ca.py` then planted 13
defects and required a RED naming the specific check that should catch each.
**Three walked straight past a green verifier.**

All three for one reason. `90.1 %`, `+0.0332 px` and `on every subject scored`
each appear at several sites, because §1 summarises what §5f measures. Falsify
§5f's own table and an anchored presence check is still satisfied — **by the
duplicate in the summary.** The verifier was reading a true statement about the
wrong copy.

The repair is `check_exact`: register the number of canonical sites for each
headline claim and require the count exactly, so **every site is load-bearing**
and a single-site falsification drops the count. With it, `13/13` are caught.

The inert plant — a prose-only rewording in §5d — correctly did **not** fire.
A verifier that reddens on any edit is as useless as one that never does
(discipline 797), and without that arm the `13/13` would only have shown the
instrument was noisy.

**D-v (proposed discipline). A presence check is satisfied by any duplicate of
the value, so a report that summarises itself cannot be verified by presence.**
Pin the occurrence count. The cost — a legitimate edit must update the count —
is the feature: on a finished report, a changing count *is* a changed claim and
should require a deliberate keystroke. Same family as the corpus's existing
one-canonical-site rule, met here from the other direction: I could not give
these numbers one site, because a report needs a summary, so I made every site
count instead.

**D-w (proposed discipline). A scale-invariant metric is immune to the
confound you feared and blind to a dense version of the artefact you want.**
Excess kurtosis was chosen because denoising cannot move it. It also cannot
read a patchwork that fills the ROI, because "heavy tails relative to the
distribution's own width" is a statement about *sparsity*, not about amount:
the gate-0 plant read `2.911` against the shipped arm's `26.660` while its
Laplacian standard deviation was `14.3x` larger. **Before adopting a metric for
its invariance, ask what else that invariance makes it blind to, and check the
saturated case explicitly** — the dose where the artefact covers everything,
not just the dose where it is visible.

**D-x (proposed discipline). Selecting an ROI by "most artefact-prone" using a
proxy can land on the one region where the artefact is structurally
impossible.** Twice here. "Flattest" chose the region where `n_eff = 99.00`, so
the elected winner never reaches the output and no election error can appear.
"Narrow gate plus low contrast" chose a region where one frame genuinely wins,
which is what being in focus looks like. **A proxy for "the mechanism can fire
here" is not the same as the mechanism firing, and both failures are only
visible if a plant is evaluated per-ROI rather than pooled.** Pooling would
have hidden ROI-N inside ROI-W's pass.

**D-y (proposed discipline). When a registered bar fails and the pictures
disagree with it, report both and promote neither.** The temptation at the end
of section 5h is to narrow `H1` to the ROI that passed, because the crops are
persuasive and the controls are exactly quiet. Section 5g refused exactly this
move for `CD1` when the stakes were a positive result; taking it here would
retroactively make that refusal a matter of convenience rather than of method.
**The value of a frozen bar is entirely in the cases where you want to move
it.** Record the visual evidence as visual evidence, hand the instrument
problem to someone who has not seen the answer, and let the verdict stand.

**D-z (proposed discipline). An anchored claim check must scan every occurrence
of its anchor, and a registered occurrence count must be boundary-aware.**
Both defects were found in `verify_patch.py` by its own negative control, and
both silently degrade a verifier into a rubber stamp. `find()` binds a check to
whichever occurrence of the anchor phrase comes first in the document, which is
rarely the one the claim lives at; substring counting lets a short numeric
token be satisfied by a chance match inside a longer number, so the registered
count drifts under unrelated edits until someone relaxes it. **Commission the
verifier before trusting its green, and treat a defect the commissioning finds
in the verifier as the more valuable result** — a plant caught in the report
confirms the instrument, a plant caught in the instrument repairs it.

---

## 5h. Addendum: the background patchwork — two instruments, two failed plants, and a picture that disagrees with both

This campaign was opened at ORCH's direction after it looked at strehl's output
for the first time and identified a **polygonal patchwork in the defocused
background** — "crazy paving" — as the worst artefact in the render, ahead of
the halo. Its proposed mechanism, which it correctly flagged as argued rather
than measured: in a region defocused in every frame the focus response is flat,
so the elected winner is noise; the spatial regulariser snaps that random field
into piecewise-constant regions; each region then draws from a different frame,
and frames differ in background brightness, so the boundaries become visible
steps. Its proposed fix: `STREHL_SOFT_GATE`, built and switched off.

**Two things should be said before the findings.** First, the mechanism was
already half-measured in this milestone's own section 5b — P17 recorded
flat-region argmax indeterminacy with an elected-frame histogram at `20.1 %`
against `20.0 %` chance, and P18 recorded the patchwork as directly visible and
surviving the shipped gate. Section 11 already recommended the soft gate be
re-measured on a flat-field bar rather than the detail bar that condemned it in
campaign 1. ORCH arrived at the same place independently and by eye, which is
worth more than either route alone.

Second, and this is the part that matters for anyone repeating the work:
**`STREHL_SOFT_GATE=1` does not mean "on". It panics.** `merge.rs:684-687` at
the pinned SHA constructs the estimator from `kernel_from_setting`
(`merge.rs:451`), which accepts only `gaussian` and `exponential`; `unset`,
`""`, `0`, `off` and `false` all return `Ok(None)`, the shipped hard gate, and
**everything else is an `Err` that aborts the run**. An experimenter reaching
for the obvious truthy value gets a crash, not a measurement. That fact is also
what makes `STREHL_SOFT_GATE="0"` a free, source-pinned trap arm, used below.

### P62. THE FIRST INSTRUMENT FAILED ITS REGISTERED PLANT, AND THE PICTURE PROVED THE PLANT WAS VALID

Registered in `prereg-patchwork.txt` at `5aa8fc7`: the primary metric is `K`,
the **excess kurtosis of the Laplacian** over a background ROI. Kurtosis and
not a magnitude, for a registered reason — the soft gate averages more frames,
so it denoises, so *any* magnitude-of-local-difference metric falls under the
treatment whether or not a single polygon is removed. Excess kurtosis is
scale-invariant, so uniform denoising reads zero.

`G1` was the plant: `K(M0) >= 2.0 * K(A0)` on `bee-3-cpl`, where `M0` is the
gate-0 arm in which P18 established the patchwork is largest. Bar: `>= 53.321`.

| arm | `K` | `lap_sd` |
| --- | ---: | ---: |
| `A0` shipped gate 4 | `26.660` | `32.78` |
| `A2` soft gate, gaussian | `0.034` | `29.61` |
| `M0` gate 0 — **the plant** | `2.911` | **`467.24`** |

**`G1` FAILED, with the sign reversed.** The plant read *lower* than the arm it
was planted against.

The crop adjudicates, and it is not close.
`images-patch/bee-3-cpl__roiG1__A0-A1-A2-M0.png` shows `M0` as textbook
patchwork — irregular flat polygons with hard brightness steps, their
boundaries drawn explicitly as a web of closed curves in the Laplacian panel —
while `A0` in the same ROI is smooth. **The plant is valid and the metric
cannot read it.**

The diagnosis is the same property that was supposed to be the design's
strength. Excess kurtosis measures how heavy the tails are *relative to the
distribution's own width*, which is what made it immune to denoising. At gate 0
the polygons **fill** the ROI: every pixel is inside a patch or on a boundary,
so the Laplacian is broadly distributed and its tails are not heavy relative to
that width. `K` collapses while `lap_sd` goes to `467.24` against `32.78` — a
factor of `14.3` in the correct direction, from the magnitude metric I had
rejected on principle. **Kurtosis reads sparse outliers. The patchwork is
dense.**

### P63. THE HEADLINE THE DEAD METRIC WOULD HAVE PRODUCED, AND WHAT IT WAS ACTUALLY MEASURING

Had the plant not been registered, this campaign's primary comparison read

> `K(A2) / K(A0) = 0.034 / 26.660 = 0.00127`

— a **99.9 % reduction** in the patchwork metric from switching on the soft
gate. It is the largest single effect measured anywhere in M116 and it is
**VOID**.

It is void twice over, and the second reason is worse than the first. The
registered ROI selector took the **lowest coarse-gradient decile**, which on
this subject is the pure white out-of-focus background. That ROI contains one
small localised blob at its right edge, visible in panels 1 and 2 of the crop
and absent from panel 3. A blob is a *sparse* outlier, which is exactly what
kurtosis reads. **`K(A0) = 26.660` was a dust-scale feature, and `A2` removed
it.** The metric's headline number on the shipped arm was never patchwork at
all.

Both defects were caught by the plant. Neither would have been caught by the
primary comparison, which would have been reported as a spectacular win.

### P64. THE FLATTEST REGION IN THE FRAME IS THE ONE PLACE THE ARTEFACT CANNOT EXIST

Selecting the ROI as "flattest" was not merely unlucky. It was structurally
guaranteed to miss.

`n_eff`, the effective number of frames the gate admits per pixel, dumped for
`A0` on `bee-3-cpl`:

| statistic | value |
| --- | ---: |
| median over the frame | `36.00` |
| median in the flattest-decile ROI | **`99.00`** |
| median on oriented detail | `21.00` |
| fraction of frame with `n_eff < 2` | `0.1339` |
| fraction with `n_eff < 10` | `0.3377` |
| fraction with `n_eff < 50` | `0.5502` |

In the pure white background the shipped hard gate **already admits
essentially every frame**. Where every frame is admitted the elected winner is
irrelevant, so a random election *cannot* propagate to the output. The flattest
region is the one region in the frame where the artefact is impossible by
construction — and it is the region a flatness-ranking selector will always
choose.

The artefact instead lives in **mid-tone, partially structured defocused**
regions: defocused limbs and wings, which carry enough local contrast to
narrow the gate but not enough real detail for the election to mean anything.
`images-patch/bee-3-cpl__neff-map.png` shows this directly — the defocused
limbs are dark, meaning a narrow gate, in the middle of a bright field meaning
a wide one.

### P65. ORCH'S MECHANISM: FIRST HALF CONFIRMED, SECOND HALF REFUTED WHERE IT WAS AIMED

`maps/bee-3-cpl__A0-index.tif`, rendered at
`images-patch/bee-3-cpl__election-index.png`, is ORCH's hypothesis made
visible. Off the subject, the elected-frame field is a dense random speckle
with no spatial coherence; on the subject it forms smooth coherent structures.
**The election in flat regions is indeterminate exactly as argued** — this is
P17 re-derived from a different artefact.

But the second half — *"each polygon then gathers its pixels from a different
frame, so the boundaries become brightness steps"* — **does not hold on the
shipped path in the region ORCH pointed at.** With `n_eff = 99.00` in the flat
background, the merge there is already the broad average ORCH proposed the soft
gate to produce. The hard gate is not committing to a winner in flat regions;
it is admitting everything.

The mechanism survives, relocated: the steps appear where the gate is **narrow
and the scene is defocused**, which is a strictly smaller region than "the
background". Reporting this precisely matters because a fix aimed at the flat
background would have nothing to act on.

### P66. THE REPLACEMENT INSTRUMENT ALSO FAILED ITS PLANT — ON ONE OF THE TWO ROIs IT REQUIRED

`prereg-patchwork2.txt` at `9253125`, written and committed before any
replacement number existed, registered `F4`: the **fraction of coarse-scale
gradient pixels exceeding `4.0x` the ROI's own median gradient**, at a `4x` bin.
`F4` is a ratio of the ROI's gradient distribution to itself, so a uniform
rescaling — which is approximately what denoising is — leaves it unchanged. Its
residual bias was registered in advance and runs *against* the soft gate:
removing noise lowers the median more than it lowers a contour, so the
threshold falls and `F4` tends to **rise** on a denoised field.

`H1` was the plant: `F4(M0) >= 1.5 * F4(A0)` **on ROI-W and on ROI-N**.

| ROI | `F4(A0)` | `F4(M0)` | ratio | bar `>= 1.5` |
| --- | ---: | ---: | ---: | --- |
| ROI-W `y=256 x=768 384px` | `0.00738` | `0.02029` | **`2.750`** | PASS |
| ROI-N `y=1024 x=2560 256px` | `0.05908` | `0.05811` | **`0.983`** | **FAIL** |

**`H1` FAILED as registered.** The bar is a conjunction over two named ROIs and
one of them did not fire.

The diagnosis is again selection, not arithmetic. ROI-N was chosen because its
median `n_eff(A0)` is `2.00` and its contrast is below the frame median — I
reasoned that low contrast plus a narrow gate implies indeterminate election. It
does not. **A narrow gate can equally mean one frame genuinely wins**, which is
what an in-focus feature looks like. At ROI-N nothing moves for any arm:
`F4` spans `0.05786` to `0.06323` across all nine arms including the plant, and
`L995` spans `1580.66` to `1649.91`. There is no artefact there to read.

`H1` is DECIDING, and its registered consequence is explicit: *"campaign 5
reports 'no working instrument', and NO soft-gate recommendation is made. I
will not write a third prereg for this artefact tonight."* **That stands.** The
correct reading of my own contract is that I picked one good ROI and one bad
one, wrote `and` between them, and lost. Narrowing `H1` to ROI-W after seeing
that ROI-W passed is precisely the move section 5g refused for `CD1`, and
refusing it there and taking it here would make both refusals worthless.

### P67. THE CONTROLS WERE EXACTLY QUIET — THREE ARMS, THREE SUBJECTS, EXACT EQUALITY

Reported before the positives, per section 3.

| bar | arm | result |
| --- | --- | --- |
| `H2` null | `N1` re-render | `F4(N1) - F4(A0) = 0.0` **exactly**, every ROI, 3/3 subjects |
| `H3` placebo | `P1`, private cache dir | `F4(P1) - F4(A0) = 0.0` **exactly**, every ROI, 3/3 subjects |
| `H4` trap | `T2`, `STREHL_SOFT_GATE="0"` | `F4(T2) - F4(A0) = 0.0` **exactly**, every ROI, 3/3 subjects |

Not "within tolerance" — identical to every printed digit on all three
subjects, `0.00738` at ROI-W, `0.05908` at ROI-N, `0.02026` / `0.16382` /
`0.00488` on the automatic tile sets. The same three arms were exactly equal
under the *dead* kurtosis metric too (`26.660` / `116.617` / `4.163`). **The
harness contributes nothing, and the trap confirms `"0"` is a genuine no-op at
the pinned source.** Both instruments failed on their plants, not on their
noise.

### P68. THE BLUR CONTROL PASSED, AT THE ONE ROI WHERE THE PLANT FIRED

`H5` was the bar the addendum was really built around: the soft gate must beat
what pure blur buys for free. Blur `A0` at a bisected `sigma` until its `L995`
matches `A2`'s to within `1 %`, then race on `F4`. Blur creates no contours and
corrects no election, so whatever it shows is the confound, priced. This is the
construction M87 used to refute its own halo blur hypothesis.

At **ROI-W**, `sigma = 0.7932 px`:

| quantity | value |
| --- | ---: |
| `F4(A0)` | `0.00738` |
| `F4(A2)` soft gate | `0.00380` |
| `F4(blur matched to A2's L995)` | `0.00618` |
| gain, soft gate | `+0.00358` |
| gain, blur | `+0.00119` |
| **ratio, bar `>= 2.0`** | **`3.000`** — PASS |

The soft gate's `F4` improvement is **three times** what an `L995`-matched blur
delivers. The magnitude metric shows why the control was necessary at all:
`L995` falls from `393.11` to `164.53`, a `58 %` drop, so a naive magnitude
reading would have credited the soft gate with far more than it earned.

`H5` is a real result and it is worth carrying forward. It is also **not
sufficient**, because `H1` gates it: a blur control tells you the effect is not
blur, not that the metric reads the artefact.

### P69. WHAT IT COSTS, AND WHERE THE EFFECT IS AND IS NOT

`H7`, the detail cost, on the identical oriented-highpass instrument used for
`CB6`/`CD7`:

| arm | `bee-3-cpl` | `foam` | `tweezers-cpl` | bar `>= -0.02` |
| --- | ---: | ---: | ---: | --- |
| `A1` photometric | `+0.00733` | `+0.00315` | `+0.00765` | PASS |
| `A2` soft gate gaussian | `-0.01868` | `-0.00076` | `-0.00114` | PASS, narrowly |
| `A3` soft gate exponential | `-0.02173` | `-0.00089` | `-0.00133` | **FAIL** |
| `A4` both | `-0.01118` | `+0.00278` | `+0.00667` | PASS |

The exponential kernel fails the cost bar on `bee-3-cpl` and the gaussian
clears it with `0.00132` dex to spare. Campaign 1 reached the same ordering on
a different bar. **If the soft gate is ever promoted it should be `gaussian`,
and `A4` — photometric *and* gaussian — costs less than the soft gate alone on
every subject.**

`H6`, the prevalence bar, on ROI-AUTO — tiles selected mechanically from the
untreated arm and the `n_eff` map only, so selection cannot favour the
treatment:

| subject | tiles | `F4(A0)` | `F4(A2)` | `F4(M0)` plant |
| --- | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | `3` | `0.02026` | `0.01392` | `0.01855` |
| `foam` | `58` | `0.16382` | `0.16431` | `0.16406` |
| `tweezers-cpl` | `24` | `0.00488` | `0.00476` | `0.00488` |

On `bee-3-cpl` the ratio is `0.687`, inside the `0.90` bar. **But the plant does
not fire on ROI-AUTO either** — `M0` reads `0.01855` against `A0`'s `0.02026` —
so that movement is uninterpretable by the same argument that killed `H1`. On
`foam` and `tweezers-cpl` nothing moves at all, on any arm, including the plant.
Only **three** tiles on the one subject where the artefact is visible met the
automatic criteria. **The honest statement of prevalence is that I could not
establish it**, and my own prereg section 6 named this outcome in advance:
*"If ROI-AUTO shows no effect while ROI-W does, the artefact is rare and a
default-on recommendation is not supported by two hand-found crops."*

`H8` was a registered prediction with no pass/fail attached, and **I got it
wrong.** I predicted photometric normalisation alone would move `F4` *much*
less than the soft gate, because the contours looked like boundaries between
different scene content rather than between different exposures of the same
content. Measured: `A1` delivers `66.7 %` of `A2`'s `F4` reduction at ROI-W
(`0.00738 -> 0.00499` against `0.00380`) and `46.2 %` on ROI-AUTO
(`0.02026 -> 0.01733` against `0.01392`). **Frame-to-frame brightness drift is
carrying between a half and two thirds of this effect**, which is ORCH's stated
mechanism and not mine. It also explains why `A4` is the best arm on both `F4`
and cost.

`H9`, election invariance, is **NOT VERIFIED**. It required the elected-frame
polygon count to be unchanged between `A0` and `A2`, since the soft gate acts
in pass two only. I have `A0`'s index map (`557` components in ROI-W, `154` in
ROI-N) but never dumped `A2`'s, so the check could not be run. The mechanistic
claim that the soft gate does not change the election therefore rests on my
reading of `merge.rs` alone and should be treated as source-argued, not
measured.

### P70. THE VERDICT, AND THE PICTURE THAT DISAGREES WITH IT

**Campaign 5 verdict: NO WORKING INSTRUMENT. No promotion recommendation for
`STREHL_SOFT_GATE`.** `H1` failed, `H1` is DECIDING, and the promotion rule
requires it.

That verdict is uncomfortable, and it should be recorded that it is
uncomfortable, because **the pictures look like a clear win**:

- `SOFTGATE-1-background-OFF-vs-ON.png` — the defocused wing on `bee-3-cpl`, a
  region out of focus in every one of the 100 frames. OFF: hard-edged waxy
  lobes with abrupt boundaries, reading as cut-out stickers. ON: smooth,
  continuous, photographic defocus. Shared stretch, so no step is manufactured
  by autoscaling.
- `SOFTGATE-3-plant-gate0-vs-shipped-vs-ON.png` — the same region with the
  gate-0 plant beside it, showing the same artefact at higher dose. The
  three-panel ordering is a dose response the eye can check.
- `SOFTGATE-2-detail-OFF-vs-ON.png` — the antenna and hairs. Detail survives:
  cuticle texture, individual hairs and specular highlights are all present in
  both, consistent with `-0.01868` dex.

So the state of the evidence is: **an artefact that is real and visible, a
treatment that visibly removes it, a blur control that says the removal is not
just smoothing, three controls that are exactly quiet — and no metric that
passes a plant.** What is missing is not the effect. It is an instrument that
can be shown to read the effect, on ROIs chosen without my eye in the loop.

The correct next step is a third campaign with a plant-first design — build the
metric *against* the `M0`/`A0` pair until it fires, then freeze it, then choose
ROIs — and it should be run by someone who has not already seen these crops.
**I am not the right person to design that instrument, having now failed twice
and seen the answer I want.**

### P71. THE VERIFIER FOR THIS SECTION, AND THE DEFECT IT FOUND IN ITSELF

`verify_patch.py` re-derives every number in section 5h from
`scores-patch.json`, `scores-patch2.json` and the raw `n_eff` map — never from
the report — and locates each claim by proximity to a registered anchor on
whitespace-collapsed text, with a registered occurrence count per token.
**141 checks, GREEN.** `negctl_patch.py` then plants 16 defects and one inert
prose change: **16/16 caught, inert correctly ignored.**

Two of the plants are worth naming because they test different organs. `D15`
mutates the *measurement* rather than the report — it raises the gate-0 plant's
kurtosis until `G1` would pass — and is caught because the verifier recomputes
the bar from the JSON instead of trusting the reported verdict. `D16` breaks
the null arm's exact equality with the shipped arm in the JSON and is caught by
the control check, not by any text check.

The verifier found two defects **in itself** before it found any in the report,
and both are the kind that produce a false GREEN:

1. **Anchoring with `find()` pins the check to the first occurrence of the
   anchor**, which for any common phrase is not the occurrence the claim lives
   at. It produced a false RED here, but the same construction produces a false
   GREEN whenever the first occurrence happens to sit near a *different* number
   of the same value. Fixed by scanning every occurrence of the anchor.
2. **Counting occurrences by substring is wrong for short numeric tokens.** A
   three-digit count matches inside a four-digit number and inside a decimal
   fraction, so the registered count drifts with unrelated edits and the
   natural response is to loosen the check. Fixed with a boundary-aware count
   that refuses a match adjacent to another digit or a decimal point. This is
   the same failure the corpus already records for last-digit decoy
   discrimination, reached from the maintenance side rather than the detection
   side.

`gen_counts.py` emits the occurrence table so that a legitimate edit updates it
deliberately, in one line, rather than by relaxing the bar.

---

## 6. Patches

**No default flips.** No instrument passed its registered promotion bar, so
there is no default to change and nothing of that kind to route to an owning
agent.

This is the deliverable. A patch would have been easy to justify — A4 misses by
`0.00084` dex on bee — and writing one would have meant narrowing a bar after
seeing the data, which is the one thing this project exists to refuse.

### Two defect patches, unapplied, for the owner of `merge_cmd/halo.rs`

These are **not** promotions and neither changes any default. Both fix silent
no-ops found by the dose ladder (P37, P38). Neither is applied; `crates/` is not
mine to edit. Both are written against
`crates/strehl-cli/src/merge_cmd/halo.rs` and `.../merge_cmd.rs` at the pinned
SHA `4beac73`.

**Patch 1 — make `DELTA=0` mean zero dose instead of silently meaning 40.**
This is what makes ORCH's blur confound directly testable: `DELTA=0` builds the
region, forbids nothing, and is the exact placebo the ladder could not reach.
It also stops a typo in the value from rendering the default without a word.

```diff
--- a/crates/strehl-cli/src/merge_cmd/halo.rs
+++ b/crates/strehl-cli/src/merge_cmd/halo.rs
@@
 /// The forbidden half-band actually in use.
 pub fn delta_in_use() -> u16 {
-    std::env::var(DELTA_ENV)
-        .ok()
-        .and_then(|v| v.trim().parse::<u16>().ok())
-        .filter(|d| *d > 0)
-        .unwrap_or(DELTA)
+    // `0` is a legal dose: `allows()` is `|k - kf| >= delta`, so delta 0
+    // admits every frame and the correction becomes the identity while still
+    // building the plan. That is the only configuration that isolates the
+    // treatment from the region it treats, and it was previously unreachable
+    // because `.filter(|d| *d > 0)` mapped it onto the shipped default.
+    match std::env::var(DELTA_ENV) {
+        Err(_) => DELTA,
+        Ok(v) => match v.trim().parse::<u16>() {
+            Ok(d) => d,
+            Err(_) => {
+                eprintln!(
+                    "warning         : {DELTA_ENV}={v:?} is not a number; \
+                     using the default {DELTA}."
+                );
+                DELTA
+            }
+        },
+    }
 }
```

**Patch 2 — say so when the correction did nothing.** At `--limit 100`,
`DELTA=160` re-elects zero pixels, writes a file byte-identical to off, prints
`halo fix : ON`, and exits 0. The count is already reported; what is missing is
that nothing distinguishes "worked" from "was structurally impossible".

```diff
--- a/crates/strehl-cli/src/merge_cmd.rs
+++ b/crates/strehl-cli/src/merge_cmd.rs
@@
         eprintln!(
             "                  This is NOT a fidelity improvement. On a synthetic scene with known \
              truth it cuts the halo metric 79.8% and raises RMSE against truth 254.6%."
         );
+        if fix.undecided == fix.treated {
+            eprintln!(
+                "warning         : the halo fix changed NOTHING. delta {} exceeds the frame \
+                 span, so every frame was forbidden at every treated pixel and the output is \
+                 identical to the fix being off.",
+                hplan.delta()
+            );
+        }
```

Patch 2 needs `delta` readable off the `Plan`; it is a private field at the
pinned SHA, so the owner should add `pub fn delta(&self) -> u16 { self.delta }`
beside `treated_len()`, or pass `halo::delta_in_use()` at the call site.

The nearest thing to an actionable *promotion* finding is still P14, and the
correct response to it remains a measurement milestone, not a patch.

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
- **It does not claim M87 was wrong about its own numbers.** My halo index is
  independently defined and is not M87's "halo metric ISO". A different
  instrument disagreeing is weaker evidence than the same instrument failing to
  reproduce. What I claim without qualification is narrower and does not depend
  on matching M87's definition: the background radial profile of these renders
  has no local maximum near the silhouette (P29), and the correction acts
  `3.05x` more strongly on a stack without an occluding background than on one
  with it (P28).
- **It does not claim the halo correction always damages an image.** P32 is a
  crop from the same stack, the same run and the same delta in which it plainly
  improves the edge. The claim is indiscriminacy, not uniform harm.
- **It does not resolve the tweezers containment excursion.** `12 926` pixels
  changed beyond the stated 40 px yoke (P35). That is either the implementation
  exceeding its documented reach or my reimplementation of `foreground_mask`
  disagreeing with the tool's, and distinguishing them needs the tool's own mask
  dumped, which needs a code change this milestone may not make.
- **It does not claim delta 80 is safe.** P33 reports only that delta 80 is not
  a monotone *detail-amplitude* loss relative to delta 40 by my statistic. M87's
  "visibly softens hairs and claws" is a visual claim; I did not design a visual
  test that isolates it, and the two crops that bear on it disagree.
- **It does not claim the halo correction is what the owner is complaining
  about.** It is the instrument whose purpose is closest to a visible artefact,
  which is why ORCH prioritised it and why I measured it. It failed. The
  complaint remains unexplained by any instrument measured in this milestone.
- **It does not adjudicate the lateral-CA correction's coefficient.** Section 5f
  measures the shipped constant as shipped. It does not refit it and it does not
  settle M107/M114's over-correction dispute; it reports that a third,
  independent method reads an implied factor of `1.099x` and `1.048x`, which
  sits at the bottom of their disputed `1.06-1.25x` band.
- **It does not claim CA helps on `bee-3-cpl` or on fern by any measured
  amount.** CD1 failed on both: a planted `0.500 px` displacement read back as
  `0.015` and `0.120 px`. Their `Q = 0.400` and `Q = 0.330` are VOID. The crops
  show a visible improvement on bee and the report says so, but a visible
  improvement is not a measurement and it is not reported as one.
- **It does not claim `90.1%` and `95.2%` are M110's `61.0%` and `58.7%`
  reproduced.** They are different quantities. M110 measured a chroma
  *amplitude* against a far-band baseline; section 5f measures a radial
  *displacement* in pixels. They are consistent in direction and are not
  comparable in magnitude, and neither was used as a prior for the other.
- **It does not claim the CA correction removes blue fringing.** `eps_b` is
  `None` on the shipped profile, and `D_B = +0.00000` exactly on all four
  subjects confirms blue is an exact no-op. Residual blue/cyan fringing is
  outside this correction's scope.
- **It does not confirm the X4 CPL on any stack.** EXIF confirms body, lens and
  2x teleconverter on all 23 subjects and cannot see a filter. The profile's
  fourth element rests on the owner's `-cpl` filename convention.
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
- **It does not claim that `DELTA=40` is safe on 299 frames.** The whole ladder
  ran at `--limit 100`. By P40 the effective dose is `DELTA` relative to the
  frame count, so a 299-frame stack — which is what M87 measured — sits at a
  different point on this ladder than the same `DELTA` here does. The two dead
  rungs and the `11.31 %` / `27.20 %` fallbacks at `DELTA=80` are properties of
  `DELTA=80` **at 100 frames** and would move at another depth.
- **It does not claim to have reproduced or refuted M87's own halo metric.**
  `dHALO%` throughout sections 5d and 5e is my independently defined index, not
  M87's "halo metric ISO", so the `+123.79 %` on fern is a failure of *my*
  index and is weaker evidence than a same-instrument failure would be.
  Section 7's earlier statement of this applies unchanged to the ladder.
- **It does not claim the blur confound is absent in general.** P43 refutes it
  on bee and P44 confirms it on fern. Two stacks do not establish which case is
  typical, and P46 argues only that no single control settles both.
- **It does not adjudicate whether halo removal is a distinct mechanism from
  blur.** LB4, the bar registered to decide that, is void by premise failure
  (P47). The question is open and it belongs to M111, which owns the metric
  audit; these per-rung curves are handed over as its input, not as its answer.
- **It does not claim the soft gate removes the background patchwork.** The
  crops show it doing so on one region of one subject, and the `H1` plant that
  was registered to license that claim FAILED. Section 5h's verdict is NO
  INSTRUMENT, and the images are offered as images.
- **It does not claim the patchwork is rare.** ROI-AUTO found `3` qualifying
  tiles on `bee-3-cpl` and none that moved on the other two subjects, but the
  plant did not fire on ROI-AUTO either, so that tile set is not shown to be
  sensitive to the artefact. **Prevalence is unmeasured in both directions.**
- **It does not claim the soft gate leaves the election unchanged.** `H9` was
  registered and **not run**: `A2`'s elected-frame index map was never dumped.
  The claim rests on reading `merge.rs:451-483` at the pinned SHA and is
  source-argued only.
- **It does not claim `K(A2)/K(A0) = 0.00127` means anything.** That `99.9 %`
  reduction is the largest effect measured anywhere in M116 and it is VOID by
  its own plant, twice over — see P63. It is stated in this report only so that
  it cannot be quoted from the raw JSON as a result.
- **It does not claim ORCH's mechanism is wrong.** Its first half is confirmed
  (P65) and `H8` shows photometric normalisation — which targets exactly the
  frame-to-frame brightness drift ORCH blamed — carrying `46.2 %` to `66.7 %`
  of the effect. What is refuted is only that the mechanism operates *in the
  flat background*, where `n_eff = 99.00` prevents it.

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

**D-i. A null is only a null once something has been shown able to move it, and
the best plant is the same knob set to a different value.** Fact 1548's dead
probe read `0` for both the real case and its broken plant. Here, T2
(`STREHL_SOFT_GATE=0`) reads byte-identical to the default, and its plant is A2
— the same variable set to `gaussian` — which moves the output hash. A plant
that shares the wiring with the null it certifies cannot be satisfied by an
unwired path.

**D-j. Immunity by construction still has to be measured, because the
construction is a claim about code you did not write.** `STREHL_WARPMAP`
bypasses the mis-keyed cache on the `else` branch, which is a correct reading of
`alignment_for` and would have been a perfectly good-sounding reason to skip
ORCH's poisoning check. Running it cost two renders and returned something the
source reading could not: that A0 and A2 both reproduce their campaign hashes
exactly from a cold cache in a later process (P22).

**D-k. In PowerShell, never name a local after a parameter — the language will
not tell you.** `$out = & $EXE @cmdArgs` silently overwrote the `$Out` parameter
with the captured log, so `Test-Path $Out` tested a block of text and every arm
reported `(none)`, which the script then read as a failed poisoning check.
Variables are case-insensitive, so `$out` and `$Out` are one variable. The
first version of the same script also assigned to `$args`, an automatic
variable, and produced an argv with an empty `--out`. Both bugs presented as an
alarming red result rather than as an error.

**D-l. A pre-registered vacuity clause is worth more than the bar it guards.**
HB3's registered statistic was `Q = D - N` evaluated with the same pixel set
passed for both the flat and the detail term, which makes `D` and `N` the same
number and `Q` identically zero for every arm on every subject. It would have
been reported as a clean pass. What caught it was the clause registered
alongside it — that delta 80 *must* move the number, or the bar is vacuous —
which is fact 1548 written down in advance instead of learned again afterwards.

**D-m. Expand a control in the operations it is built from, not in the
variable it holds fixed.** The natural control for "did the correction soften
detail" is the untreated pixels, which are byte-identical to the reference and
so must read zero. It read `+0.10127`. `highpass()` is a 5 px box, so the
control's value depends on treated neighbours within 2 px; the perturbed
quantity appears in the control's own expansion. Eroding the control set by the
filter's support took it to `+0.00000` on all four subjects.

**D-n. When a brief tells you which number to reproduce, check whether that
number can distinguish success from failure before you spend a night
reproducing it.** The dispatch asked for an independent check of `87.9%` halo
removal. The module defining that metric also records it reading `-63.9%` on a
region with no defect. Reproducing it would have been a night's work confirming
a quantity already known to be uninformative. The bar that mattered was
selectivity, and it was cheap: one extra stack, chosen because it lacks the
thing the instrument exists to fix.

**D-o. A one-sided bar can pass while the quantity it guards moves violently in
the unguarded direction.** HB4 registered "the yoke/outside noise ratio rises by
at most 20%". It fell, by up to `69.12%`, and so passed. The fall is evidence of
the same flattening the crops show. A bar written as a band would have caught
what a bar written as a ceiling waved through — the same defect as B3 in the
main campaign, committed twice in one milestone.

**D-p. `$ErrorActionPreference = "Stop"` turns a native tool's progress output
into a terminating error.** `strehl` reports to stderr; under `2>&1` PowerShell
wraps each stderr line in an `ErrorRecord`, and with `Stop` in force the first
one killed the halo campaign on arm one, having written no output and no log.
The same harness had run 39 arms successfully under a different invocation, so
the defect was in the *composition*, not the script. Drop to `Continue` across
the native call only, and take `$LASTEXITCODE` into a variable immediately.

**D-q. Enumerate a knob's dead values before you build a ladder on it.** Both
ends of `STREHL_FIX_HALO_DELTA` are silent no-ops: `0` renders the shipped
default because of a `.filter(|d| *d > 0)`, and any value at or above the frame
count re-elects nothing while still reporting the fix as ON. A ladder run
`0/10/20/40/80` would have measured the shipped dose twice and called the
duplicate a bottom rung. Read the parser and the predicate that consumes its
output, then check the ends of the range against the actual data volume — a
knob measured in frames is dead above the frame count, and `--limit` is
therefore part of its meaning.

**D-r. A dose ladder is worth its cost even when it disagrees with itself
across subjects — that disagreement is the result.** The confound under test
(treatment blurs the region in which the effect is scored) was confirmed on one
stack, `-0.30177` dex, monotone in dose, and refuted on the other, where the
same treatment at the same doses *raised* high-pass amplitude by up to
`+0.14468` dex. A single blur-matched placebo calibrated on either stack would
have been wrong about the other. Where a confound is subject-dependent, no one
control retires it and the honest deliverable is the pair of curves, not a
verdict.

**D-s. A bar can be arithmetically satisfiable while its premise is false.**
`X = dHALO% / (-D)` was registered as "how much halo a rung buys per unit of
detail it spends", with a spread bar of `>= 2.0` to distinguish two mechanisms
from one. It read `82.41` and would have been recorded as a PASS. But every
formable rung had `dHALO% > 0` — no rung bought any halo — so `X` was a ratio of
two losses and not an exchange rate at all. Write the premise into the bar's
text, not only its formula, and check the premise before reading the number.
Same family as the vacuous HB3, and it needed a different guard to catch.

**D-t. Register a plant as an admission gate with a registered minimum admitted
count, not as a bar quantified over every subject scored.** CD1 read
`within +/-0.10 px ... on every subject scored`. Under `∀ subjects scored`
every subject added is pure liability, since it can only lose, and one failure
is unrecoverable by any further measurement — which converts "go and measure
more" from the correct response into an unavailable one, and leaves a positive
result stranded at HOLD with no legitimate path forward inside its own
milestone. Under a bare "N of M" the void readings of a dead instrument get
counted as data. Only the gate plus a separately registered admitted-count
survives both failure modes. Corollary, and the reason this cost a whole
section: **check whether your bars are still satisfiable before you plan the
work that is supposed to satisfy them.** See section 5g, P58–P60.

**D-u. When two readings of your own bar disagree about your headline verdict,
you must take the one you registered, and you must state the other.** §5g's
admission-gate reading of CD1 satisfies the promotion rule; the registered
reading does not. Choosing between them after seeing which the data favours is
the exact move pre-registration exists to prevent, so the verdict stays HOLD.
But suppressing the alternative reading is its own dishonesty: it hides the
size of what the discipline is costing and denies the reader the arithmetic to
check it. State both, mark which one binds, and claim only that one.

---

## 9. Images

### 9a. The background patchwork (section 5h) — `C:\dev\strehl-out\M116\`

**Open these first.** They are the answer to the owner's *"those stacks don't
look too good yet"* that this milestone can actually show him, and they are the
strongest visual evidence in M116 — while carrying a verdict of NO INSTRUMENT,
which the captions must not hide.

| file | what it shows |
| --- | --- |
| `SOFTGATE-1-background-OFF-vs-ON.png` | `bee-3-cpl`, a defocused wing that is out of focus in all 100 frames. **OFF:** hard-edged waxy lobes with abrupt boundaries — the cut-out-sticker look. **ON:** smooth continuous defocus. A defocused scene cannot physically contain a hard edge, so the OFF panel is a defect statement that needs no aesthetics. |
| `SOFTGATE-3-plant-gate0-vs-shipped-vs-ON.png` | the same region with the gate-0 plant beside it: plant / shipped / soft gate. A three-rung dose response the eye can check without trusting any metric. |
| `SOFTGATE-2-detail-OFF-vs-ON.png` | the antenna and hairs, the detail the soft gate could have averaged away. Cuticle texture, individual hairs and specular highlights survive, consistent with `-0.01868` dex. |
| `images-patch/bee-3-cpl__roiG1__A0-A1-A2-M0.png` | **the picture that killed the first metric.** Panel 4 is textbook patchwork; the Laplacian row below draws its polygon boundaries explicitly. The metric read this as `K = 2.911` against the smooth panel 1's `26.660`. |
| `images-patch/bee-3-cpl__neff-map.png` | why "flattest" was the wrong ROI. White is a wide gate. The bright field is where the artefact **cannot** occur; the dark defocused limbs are where it does. |
| `images-patch/bee-3-cpl__election-index.png` | ORCH's hypothesis made visible: the elected-frame field is random speckle off the subject and coherent on it. P17, re-derived from a different artefact. |

All six use a **shared stretch across panels**, computed from the first panel,
because per-panel autoscaling would manufacture or hide exactly the brightness
step under discussion. All are gamma-encoded **for looking only**; every number
in section 5h comes from the linear renders.

### The dose ladder (section 5e) — `C:\dev\strehl-out\M116\images-ladder\`

Four sheets, 1:1 crops of sRGB views at a frozen exposure, windows chosen on the
off arm. Every panel is captioned with its ladder position and its mean
`|delta|` against off in DN/255.

| file | what it shows |
| --- | --- |
| `bee-3-cpl__ladder-SILHOUETTE-edge.png` | off / `d1` / `d40` shipped / `d160`. The pale fringe on the leg is **worse** at `d1`, **genuinely gone** at `d40`, and `d160` is indistinguishable from off. The cost at `d40` is a blotched background and a hard seam. |
| `bee-3-cpl__ladder-ORIENTED-fine-structure.png` | the same four rungs on oriented content: flat amoeba patches carved into a smooth gradient at the shipped dose. |
| `flower-bud-with-background-fern-cpl__ladder-SILHOUETTE-edge.png` | off vs `d40`. Textured bud surface replaced by flat mush with hard borders. |
| `flower-bud-with-background-fern-cpl__ladder-ORIENTED-fine-structure.png` | the same, on oriented content; `-0.30177` dex in picture form. |

### The halo campaign (section 5d) — look at these first

`C:\dev\strehl-out\M116\images-halo\`

```
flower-bud-with-background-fern-cpl__contact-halo-edge1.png   <- P31, the damage
flower-bud-with-background-fern-cpl__contact-halo-edge2.png   <- P32, the benefit
bee-3-cpl__contact-halo-edge1.png                             <- P34, hairs erased
bee-3-cpl__contact-halo-edge2.png                             <- P34, new faceting
flower-bud-alone-cpl__contact-halo-edge{1,2}.png              <- the HB2 trap
tweezers-cpl__contact-halo-edge{1,2}.png                      <- P30, overshoot
```

Each sheet is four panels at 1:1 on an identical pixel region: `H0` correction
OFF (the shipped default), `H1` delta 40, `H2` delta 80, and `|H1 - H0| x 8`
showing exactly which pixels the correction touched. Individual crops are
`<subject>__<arm>__halo-edge<n>.png`, full renders `<subject>__<arm>__full.png`.

The crop windows were chosen **on `H0`, the correction-OFF arm**, by maximising
near-yoke coverage subject to the window straddling a silhouette — never on a
treated arm, and never by where the arms differ most, which would have selected
for maximum effect. Exposure was solved once per subject on `H0` and passed as
a literal to `H1` and `H2` — bee `1.49`, fern `1.89`, alone `1.57`, tweezers
`1.13`.

The panels are `--srgb` renders because they are for looking at. Every number
in this report is measured on the linear renders, because `--srgb` applies a
non-diagonal colour matrix and a guided demosaic and its own `--help` says
"For looking at, NOT for measuring."

### 9c. Lateral chromatic aberration — UN-ADJUDICATED, and labelled as such

**Every image in this subsection is un-adjudicated pending ORCH's `V-CA`
verifier**, which is auditing whether the `61.0 %` / `58.7 %` figures come from
the shipped pipeline and whether the correction was ever raced against a
negative-strength arm rather than only against OFF. The same eight files are
duplicated into `C:\dev\strehl-out\M116\` with a
`CA-UNADJUDICATED--` prefix, so that a reader who opens the output folder
without reading this report cannot mistake them for a promoted result. Section
5f's own verdict is **HOLD** on independent grounds — my plant `CD1` failed on
two of four subjects — so nothing here is blocked on `V-CA` alone.

One caveat to carry into any caption: the correction makes fringes **fainter,
not thinner**. The peak drops faster than the tail and the half-max width is
unchanged, so it must not be described as sharpening.

`C:\dev\strehl-out\M116\images-ca\`

```
tweezers-cpl__CA-4x.png                       <- OPEN THIS ONE FIRST
tweezers-cpl__CA-1to1.png                     <- the same crops at 1:1
flat-on-ruler-cpl__CA-{1to1,4x}.png           <- the second calibrated subject
bee-3-cpl__CA-{1to1,4x}.png                   <- instrument dead, effect visible
flower-bud-with-background-fern-cpl__CA-{1to1,4x}.png
INDEX.txt
```

Each sheet is three crop pairs, OFF on the left and ON on the right, on an
identical pixel region, at `r >= 0.55` where lateral CA lives. Both `1:1` and
`4x` nearest-neighbour versions exist because the aberration is sub-pixel: at
1:1 it reads as a faint colour grain, and at `4x` it is unmistakable.

On `tweezers-cpl` the OFF panels carry dense red/cyan speckle across the whole
metal texture and the ON panels are essentially neutral grey. On `bee-3-cpl` the
cyan fringes along the wing edge and leg silhouettes are clearly reduced while
the hairs are not softened — **shown despite the instrument being dead there,
and captioned as such, because the eye and the correlator disagree and the
reader is entitled to both.**

Crop windows were ranked by **green-plane** gradient energy. Green is the
profile's reference channel, has no coefficient, and is measured to move
`0.0000 px` between the arms, so the ranking is bit-identical in both arms and
cannot have been chosen to flatter the correction. This is M87 §16.10's device,
reused for the same reason.

**No crop here is captioned as sharpening.** M110 §16.4 measured that the
correction makes fringes *fainter, not thinner* — the peak falls faster than the
tail and the half-maximum width is unchanged — and the captions say so.

### The main campaign

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

- **No default flip to route.** Two *defect* patches are in section 6 for the
  owner of `merge_cmd/halo.rs`: `DELTA=0` silently means 40 (P37), and
  `DELTA >= frame count` is a silent no-op that still reports ON (P38). Neither
  promotes anything; the second is a one-line diagnostic and the first is what
  makes the blur confound directly testable.
- **The ladder was run and it changed the picture, not the verdict.** ORCH's
  blur confound is confirmed on fern (`D = -0.30177` dex at the shipped dose,
  monotone in dose) and refuted on bee (`D = +0.14468` dex — the treatment
  *raises* high-pass amplitude). It is subject-dependent, so no single
  blur-matched placebo retires it (P46). Handing the per-rung curves to M111
  rather than duplicating its audit, as instructed.
- The bar registered to decide blur-versus-halo, LB4, is **void by premise
  failure** and its arithmetic would have read PASS (P47). The question is open.
- The dose ladder's own bars: LB1 PASS, LB3 PASS both subjects, LB5 PASS,
  LB6 PASS both subjects, LB2 **FAIL** both subjects as registered (predicted in
  advance for bee), LB4 VOID, LB7 delivered.
- Ladder images are in `C:\dev\strehl-out\M116\images-ladder\`. The one to open
  first is `bee-3-cpl__ladder-SILHOUETTE-edge.png`: at the shipped dose the pale
  fringe really is gone, and the background it sat in is visibly blotched.
- **Caveat that bounds all of it:** the ladder ran at `--limit 100` and the
  effective dose is `DELTA` relative to the frame count (P40). M87 measured at
  299 frames. The two dead rungs are properties of this depth.
- No patch to route for any of the four originally dispatched instruments.
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
- P14 is now **discharged**: `STREHL_FIX_HALO` was measured on a genuine
  occluding edge, across four stacks and a seven-rung dose ladder.
- The soft gate deserves one more milestone with a flat-field bar rather than a
  detail bar, starting from ΔN `-0.02044` (P4). It should not ship on tonight's
  evidence.
- **Lateral CA is the one to act on, and the action is a new pre-registration,
  not more rendering and not a code change.** Section 5f is the only positive
  result in M116: `90.1%` and `95.2%` of measured lateral CA removed at a
  fine-structure cost of at most `0.42%`, with a byte-identical null and a
  byte-identical adversarial placebo. It is HELD because CD1 — my own plant —
  failed on two of four subjects.
- **Do not ask me to fix that by measuring more subjects; I checked, and it
  cannot work.** CD1 is quantified `on every subject scored`, so bee's and
  fern's failures are permanent and three more passing subjects would still
  leave CD1 FAILED. I had that render batch queued and cancelled it. Section 5g
  and P58–P60 give the arithmetic. **The repair is a new milestone with a
  prereg that registers the plant as an admission gate plus a minimum admitted
  count (proposed discipline D-t), and re-runs these arms under it.** Re-running
  them under *this* prereg would not be sound, and that distinction is the one
  thing I most need ORCH to carry forward correctly.
- **The gear caveat survives any of that.** The profile describes one optical
  path; the binary parses no camera identity at all; EXIF confirms body, lens
  and 2x TC on all 23 subjects and cannot see a filter. The X4 CPL rests on the
  owner's `-cpl` filename convention. A default flip would apply a
  single-optical-path correction to whatever anyone stacks.
- **Two ORCH claims from message #5 are confirmed at source, and one carries
  something ORCH did not relay.** M87 §16.9 is titled "why I am telling you not
  to enable it", records `72.9%` on the shipped path, and describes the
  "smooth, milky, **scalloped** band ... **It looks worse.**" But §16.9's
  withdrawal notice also records that the correction **FAILS registered bar V3**
  because "it removes fine structure (0.9058) harder than it removes the veil
  (0.9146)" — **a selectivity failure**. My HB2 was an independently
  constructed selectivity bar and it failed at `R = 3.054`. Two instruments
  built without knowledge of each other convict the same correction on the same
  axis.
- **My ladder corroborates ORCH's withdrawal of the blur confound, from the
  opposite direction.** On bee, `D` is *positive at every rung* (up to
  `+0.14468` dex): the treatment adds high-frequency content rather than
  removing it, because it substitutes a single frame's raw quad into a
  neighbourhood averaged over `n_eff ≈ 23`. A treatment that roughens cannot be
  a blur. That is a different route to M87's σ-race conclusion and it agrees
  with it. The ladder was already run and committed at `5a99350` before the
  withdrawal arrived; it cannot be un-spent, and §5e's two silent-no-op defects
  stand regardless.
- **The "milky scalloped band" is in my crops already.**
  `flower-bud-with-background-fern-cpl__contact-halo-edge1.png` shows flat,
  amoeba-shaped mush with hard scalloped borders carved out of textured bud
  surface. I named it differently because I reached it independently; it is the
  same artefact and it is the visual evidence for *not* shipping the halo fix.
- **My `+17.21%` / `+123.79%` halo figures are NOT comparable to `87.9%` or
  `72.9%`.** They are my own index, at `--gate 4`, full frame, on 100 frames.
  M87's are its own halo-metric ISO at `--gate 2` on 299 frames. I did not
  reproduce `72.9%` and do not claim to have refuted it.
- `experiments/ORCH-drift-check/reachability.py` was run, not edited.

### Campaign 5 — the background patchwork, in reply to ORCH's message #6

- **Your hypothesis was already half-measured in my own section 5b, before you
  sent it.** P17 recorded flat-region argmax indeterminacy with an
  elected-frame histogram at `20.1 %` against `20.0 %` chance; P18 recorded the
  patchwork as directly visible. Section 11 already recommended the soft gate be
  re-measured on a flat-field bar. You reached the same place by eye and
  independently, which is worth more than either route alone.
- **The first thing to fix in your instructions to anyone else:
  `STREHL_SOFT_GATE=1` PANICS.** `merge.rs:451` accepts only `gaussian` and
  `exponential`; `unset`/`""`/`0`/`off`/`false` return the shipped hard gate and
  **everything else aborts the run** at `merge.rs:684-687`. Anyone told to "set
  it to 1" gets a crash, not an OFF arm.
- **Your mechanism's first half is confirmed and its second half is refuted
  where you aimed it.** `images-patch/bee-3-cpl__election-index.png` shows the
  election is random speckle off the subject. But `n_eff` in the flat white
  background is `99.00` of 100 frames — **the shipped hard gate already averages
  everything there**, so the random winner never reaches the output. The steps
  occur where the gate is *narrow* and the scene is *defocused*, which is a
  strictly smaller region than "the background". A fix aimed at the flat
  background would have had nothing to act on.
- **Your ROI advice would have failed, and mine did.** You proposed "a pure
  background region — out of focus in every frame, no subject". I registered the
  equivalent, flattest-decile selection, and it chose exactly the region where
  the artefact is structurally impossible. Two independent routes to the same
  wrong ROI, which is worth recording as a hazard rather than as either of our
  mistakes.
- **Both metrics failed their plants, and I am reporting NO INSTRUMENT.**
  `G1`: excess Laplacian kurtosis read `2.911` on the gate-0 plant against
  `26.660` on the shipped arm — reversed. `H1`: `F4` passed on ROI-W (`2.750x`,
  bar `1.5x`) and failed on ROI-N (`0.983x`); the bar was a conjunction and I am
  not narrowing it. Section 5g refused the identical move for CA when the prize
  was a positive result.
- **You asked me to quantify the patchwork rather than only show it. I could
  not, and that is the finding.** Your suggested metrics were Laplacian
  kurtosis or a count of locally flat components. I built the first. It is
  blind to a *dense* patchwork, because heavy-tails-relative-to-own-width is a
  statement about sparsity: at gate 0 the polygons fill the ROI, so `K` falls
  while `lap_sd` rises `14.3x`. Discipline D-w.
- **The pictures are in `C:\dev\strehl-out\M116\` and they are the deliverable
  you asked for.** `SOFTGATE-1-background-OFF-vs-ON.png` is the one to open:
  hard-edged waxy lobes in a region that is defocused in all 100 frames, gone
  on the treated arm. `SOFTGATE-3-` adds the gate-0 plant as a third rung.
  `SOFTGATE-2-` is the detail check and detail survives. Shared stretch across
  panels throughout; gamma for looking, linear for every number.
- **Your strongest-available-control suggestion is superseded by a better one I
  could actually run.** You proposed comparing merged high-frequency energy
  against single input frames. I could not: geometry differs between the
  aligned merges and the surviving unaligned singles. Instead `H5` bisects a
  Gaussian on the untreated arm until its `L995` matches the treated arm's, then
  races on `F4` — M87's own construction. **The soft gate beats matched blur by
  `3.000x`**, bar `2.0x`. So the improvement is not smoothing. It still does not
  license a promotion, because a blur control tells you what the effect is not.
- **Photometric normalisation carries between `46.2 %` and `66.7 %` of the
  effect, which is your mechanism and not mine.** I registered a prediction that
  it would move `F4` much less than the soft gate, and I was wrong. `A4`
  — photometric **and** gaussian soft gate — is the best arm on both the metric
  and the cost on every subject. If anything here is ever promoted it is that
  pair, and the exponential kernel should be dropped: it fails the `-0.02` dex
  cost bar on `bee-3-cpl` at `-0.02173`.
- **What I did not run:** `H9`, election invariance, needed `A2`'s index map and
  I never dumped it, so "the soft gate does not change the election" is
  source-argued from `merge.rs` and not measured. And prevalence is unmeasured
  in both directions — ROI-AUTO found `3` qualifying tiles on bee and the plant
  did not fire there either.
- **What I recommend, and it is not a render.** A third campaign with a
  **plant-first** design: build the metric against the `M0`/`A0` pair until it
  demonstrably fires, freeze it, *then* choose ROIs, *then* look. Run it with
  someone who has not seen these crops. I have now failed twice and I have seen
  the answer I want, which disqualifies me from designing the instrument that
  would license it.
- `python scripts/corpus_lint.py` reports **OK — no violations** over 190
  markdown and 61 rust files. Earlier in this milestone it reported 2, both in
  `docs/research/M95-election-quality.md:241`; that file's owner has since fixed
  them. The linter caught 4 violations of my own in section 5f's tables —
  unescaped `\|` inside code spans on table rows, which the renderer discards
  silently — and they are fixed.
- **Section 5h is verified and the verifier is commissioned.**
  `python experiments/M116-promotion/verify_patch.py` re-derives every number
  from the scorer JSONs and the raw `n_eff` map and reports **GREEN, 141
  checks**; `python experiments/M116-promotion/negctl_patch.py` plants 16
  defects — including two that mutate the *measurement* rather than the report —
  and reports **16/16 caught, 0 missed, inert plant ignored**. Section 5f's pair
  still reports GREEN 100 / 13-of-13. Nothing in this milestone rests on an
  unchecked number.
