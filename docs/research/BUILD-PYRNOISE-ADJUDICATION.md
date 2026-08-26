# BUILD-PYRNOISE-ADJUDICATION — the README's `leaf-2-cpl` flat-ROI noise claim

**Verdict in one line: the claim survives, my admission test does not, and the
paragraph has a different and worse problem than the one I raised.**

This document adjudicates the README paragraph *"On a whole photograph,
measured"* against the flat-ROI admission test built in
[`BUILD-PYRNOISE.md`](BUILD-PYRNOISE.md) §5. That test disqualified
`leaf-2-cpl` at all five of its flattest windows, and the README makes a
flat-ROI noise claim on `leaf-2-cpl`. I raised the contradiction. It resolves
against me.

Everything below was produced by one pinned binary except where a cross-build
comparison is named as such and its purpose stated.

---

## 0. Provenance

| item | value |
| --- | --- |
| pinned binary | `C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe` |
| sha256 | `CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6` |
| size | 9,385,984 bytes |
| the claim's own build | `925d03da` "M100: apply the exposure patch I let sit for hours, and prove it inert" |
| the claim's own renders | `C:\dev\strehl-out\ORCH-thesis\leaf-2-cpl-{selection-gate0,estimation-gate2}.tif` |
| harness | `experiments/BUILD-PYRNOISE/{claim_roi,adjudicate,diagnose,gated,photom,levelterm,control,final}.py` |
| renders and logs | `C:\dev\strehl-out\BUILD-PYRNOISE\claim\` |

The 925d03d renders are read **only against each other and against the claim's
own published numbers**. Every comparison that carries a conclusion is within
the pinned build.

---

## 1. The claim, and its ROI, recovered exactly

`thesis_demo.py` computes its ROI at run time and never records it, so the
coordinates were recovered by replicating its selection arithmetic against the
same two renders it measured (`claim_roi.py`).

```
render shape (full-res, --srgb, demosaiced) : (4688, 7040, 3)
flat patch chosen on the MEAN of both arms  : y=912 x=384 (200x200)
  selection  --gate 0 : sigma 0.006381   README says 0.006381
  estimation --gate 2 : sigma 0.000987   README says 0.000987
  ratio               : 0.1546x          README says 0.1546x
  equivalent frames   : 41.82            README says 41.8
REPLICATION EXACT -- the recovered patch is the claim's.
```

The adjudication is therefore about the claim's own ROI, not one of my
choosing. That was the orchestrator's first requirement.

---

## 2. Banners — what actually ran

Argv records what the caller said; only the banner records what the program
did. Every arm below is on the pinned binary, at `--exposure=3.19`, with
`thesis_demo.py`'s argv copied exactly — which passes `--gate` *without*
`--merge` and so preserves the inference trap deliberately.

| arm | banner line, verbatim |
| --- | --- |
| `gate0` | `merge backend   : estimator (inferred from --gate; pass --merge pyramid to override)` |
| `gate2` | `merge backend   : estimator (inferred from --gate; pass --merge pyramid to override)` |
| `gate2_neff` | `merge backend   : estimator (inferred from --gate, --n-eff-map; pass --merge pyramid to override)` |
| `gate0_poff` | `merge backend   : estimator (inferred from --gate, --photometric; pass --merge pyramid to override)` |
| `gate2_poff` | `merge backend   : estimator (inferred from --gate, --n-eff-map, --photometric; pass --merge pyramid to override)` |

All five ran the **estimator**, as the claim intends. Alignment for every arm:
`alignment      : ON (sidecar), reference frame 91, 182 placed / 0 refused`,
`coverage      : field of view scaled to 0.9342`, and — load-bearing later —
`held-out err  : 13.227 px   cycle floor: 2.146 px`, which the binary itself
flags as above its own `T_usable` of 4.0 px.

**`--n-eff-map` purity null.** The help says that flag does not change the
merged image "by a byte". Checked rather than believed:

```
gate2      D902DB33BC7375465C5F714CFA606B6A608ED8DBE698C09CB4D356B1A90DE7C3
gate2_neff D902DB33BC7375465C5F714CFA606B6A608ED8DBE698C09CB4D356B1A90DE7C3
PASS -- --n-eff-map did not perturb the merge
```

The n_eff map therefore describes the arm that was measured. `gate2_neff.tif`
was deleted after hashing; the hash is the evidence.

Two further nulls on the map itself, against the same run's own banner:

| null | map | banner | result |
| --- | --- | --- | --- |
| whole-plane mean n_eff | 5.229 | `mean n_eff 5.229` | PASS |
| share at n_eff = 1 | 62.57% | `n_eff=1 % 62.57` | PASS |

---

## 3. The admission test fails the claim's ROI — and the test is the thing that is wrong

### 3.1 The raw verdict

At the claim's own patch, mapped onto the raw plane through the resolution
ratio and the inverse alignment magnification (1.070435, read from the run's
own banner), the ROI is `(292, 500, 100, 100)`:

| reading | temporal | spatial | ratio | bar 1.30 |
| --- | --- | --- | --- | --- |
| as measured | 126.94 | 84.96 | **1.494** | FAIL |
| drift-compensated, ±24 px per-frame NCC | 129.13 | 84.97 | **1.520** | FAIL |
| patch offset ±4 px | — | — | 1.48–1.52 | FAIL |

So on its face the contradiction is real. Three candidate explanations were
tested and **two were falsified**.

### 3.2 Falsified: misregistration

The ±10 px search used in `BUILD-PYRNOISE.md` §5 **saturated** on this subject,
which the banner explains (13.227 px held-out error). Widened to ±24 px the
per-frame shifts span dx −24…23, dy −22…23 — and the ratio does not fall. It
rises slightly, 1.494 → 1.520. Registration is not the cause.

### 3.3 Falsified: "the merge only averages near-winner frames"

My first replacement explanation was that the admission test measures variance
across the whole 182-frame bracket while a merge only ever combines frames near
the focus winner. Testable: restrict the temporal sd to each pixel's *k*
sharpest frames.

| frames used | claim patch ratio | pin-argmin patch ratio |
| --- | --- | --- |
| whole bracket (37 sampled) | 1.494 | 2.691 |
| 24 sharpest per pixel | 1.511 | 2.688 |
| 12 sharpest per pixel | 1.516 | 2.601 |
| 6 sharpest per pixel | 1.494 | 2.464 |
| 3 sharpest per pixel | 1.401 | 2.205 |

It barely moves. That explanation is wrong too, and is recorded here because it
was offered before it was tested.

### 3.4 Confirmed: a per-frame photometric level the merge removes and a single frame cannot

The run's own banner names the suspect: `gain span : 1.1010 (max/min across 182
frames)`. The **merge** fits and removes a per-frame gain. A **single unstacked
frame** cannot — there is nothing to normalise against — so the admission test
charges the subject for a term neither arm ever sees.

Removing a per-frame level before the temporal estimate:

| patch | level, DN | span | raw | minus gain | minus offset |
| --- | --- | --- | --- | --- | --- |
| claim patch | 3578 | 1.0920 | 1.494 | **1.000** | 0.999 |
| pin-argmin patch | 3596 | 1.1795 | 2.691 | 1.225 | 1.221 |
| `109MSDCF` admitted patch | 1843 | 1.0197 | 1.117 | 1.089 | 1.088 |

The claim's patch lands on **exactly 1.000**. And the correction is
**specific**: it moves `leaf-2-cpl` by 33.1% and `109MSDCF` — the corpus's
quietest stack, banner-quoted at 0.91% drift — by 2.6%. An instrument that
removed something other than drift would move both.

**The term is global, not local content.** A global gain is one number per
frame and must be the same everywhere:

| patch | level span | correlation with the whole-plane per-frame level |
| --- | --- | --- |
| claim | 1.0920 | **+0.9886** |
| pin-argmin | 1.1795 | +0.9898 |
| far-SE | 1.1223 | +0.9842 |
| far-NE | 1.1864 | +0.9800 |
| mid | 1.0804 | +0.9944 |

Whole-plane span over my 37-frame subsample: **1.0953**, against the binary's
own **1.1010** over all 182. Two independent reads of the same physical
quantity. Using **only** the whole-plane gain — one scalar per frame, which is
what the merge applies — the claim's patch reads **1.017, PASS**.

### 3.5 Commissioning: is the level term real, or is this a story?

**Arithmetic prediction.** For a stationary patch, adding a per-frame gain gives
`temporal² = noise² + (s_g·L)²`, so the admission ratio must be exactly
`sqrt(r0² + (sd_of_frame_means / spatial)²)`. Every term on the right is
measured independently of the ratio on the left.

| patch | sd(frame means) | spatial | predicted | observed | error |
| --- | --- | --- | --- | --- | --- |
| **claim** | 94.78 | 84.96 | **1.498** | **1.494** | **+0.3%** |
| pin-argmin | 207.02 | 86.05 | 2.605 | 2.691 | −3.2% |
| far-SE | 148.72 | 91.39 | 1.910 | 2.838 | −32.7% |
| mid | 64.29 | 81.19 | 1.275 | 1.977 | −35.5% |

The prediction is near-exact **at the claim's patch** and falls far short
elsewhere — i.e. it discriminates. At the claim's patch the excess is a level
term and nothing else; at other patches there is genuine content change the
level term does not explain.

**Planted positive control**, on a synthetic stationary bracket built from this
subject's own pixels. The first version of this control FAILED at +42.6% and
the control was wrong, not the finding: its predicted form assumed the
un-planted ratio is 1.0, but a bracket of `one real frame + planted noise` has
`spatial = sqrt(structure² + noise²)` and so a baseline of 0.70. Corrected to
add in quadrature against the *measured* baseline:

| planted s\_g | sd(means) | predicted | observed | error | statistic moved by |
| --- | --- | --- | --- | --- | --- |
| 0.00% | 0.84 | 0.7037 | 0.7037 | +0.00% | 0.0% |
| 0.50% | 14.58 | 0.7142 | 0.7140 | +0.03% | 1.5% |
| 1.00% | 33.56 | 0.7581 | 0.7576 | +0.07% | 7.7% |
| 2.64% | 108.91 | 1.1538 | 1.1522 | +0.14% | 63.7% |
| 5.00% | 136.77 | 1.3405 | 1.3387 | +0.13% | 90.2% |
| 10.00% | 431.44 | 3.7100 | 3.7099 | +0.00% | 427.2% |

Worst error **0.14%** against a 2.0% bar, across a range that brackets the
2.64% implied by the real patch, with a potency column so a plant too weak to
move anything cannot read as a pass. **Null**: the 0% row reproduces the
baseline exactly. **Specificity**: on `109MSDCF` the level term would explain
only 1.031 of the observed 1.117 — the instrument does not find a level term
where the corpus says there is not one.

### 3.6 Consequence: `BUILD-PYRNOISE.md` §5 is partially retracted

**The admission test as published is missing a photometric term and
over-rejects.** It should be read as `temporal` **after** removal of a
whole-plane per-frame gain. With that correction, on 400 windows of
`leaf-2-cpl`, admissible windows go from **1 to 17** and the median from **2.32
to 1.91**.

Two things this does *not* license:

* `leaf-2-cpl` is still largely non-stationary — 383 of 400 windows still fail
  after the correction. The subject is a deep focus sweep and that is real.
* The exclusions in `BUILD-PYRNOISE.md` were in the **safe** direction: I
  declined to publish rows. No published number rests on the defect. But the
  stated *reason* for excluding `leaf-2-cpl` and `tweezers-cpl` — "recovered
  structure scored as noise" — is **not established**, and at the claim's patch
  it is measurably false.

---

## 4. Does the mechanism apply to an arm-vs-arm ratio? No — and this is measured

This was the orchestrator's question 3, and the orchestrator's own answer
("it should apply to both") is **wrong**. Three independent measurements say so.

### 4.1 The decisive A/B: the same build, with and without the term

Photometric normalisation was wired into the merge at commit `27646057`
("M97q: wire photometric.rs into the merge behind `--photometric` (opt-in)"),
and `git merge-base --is-ancestor 27646057 925d03d` returns **false**. So the
claim's arms carried the **full uncorrected gain drift**. The pinned binary
lets that condition be reproduced exactly, within one build.

At the claim's own patch, y=912 x=384:

| condition | gate0 sigma | gate2 sigma | ratio | equiv frames |
| --- | --- | --- | --- | --- |
| 925d03d — the claim itself | 0.006381 | 0.000987 | 0.1546x | 41.82 |
| pin, `--photometric off` — the claim's condition | 0.009386 | 0.001297 | **0.1382x** | 52.37 |
| pin, flagless default (photometric on) | 0.009210 | 0.001297 | **0.1408x** | 50.45 |

**Inflation from the uncorrected per-frame gain: 1.02x.** Essentially nothing.
Applied to the claim's own figure that is 0.1546x → 0.1575x, 40.3 frames rather
than 41.8 — smaller than the difference between builds and far smaller than the
claim's own rounding.

**Why my simulation said otherwise, and why the simulation was wrong.** A
simulated selection arm drawn independently per pixel from the bracket reads
1.48x inflation at that patch; drawn in 8x8 blocks it reads 1.15x. The real
`--gate 0` winner field is spatially coherent over far larger areas than that,
and the claim's statistic is a 3x3 Laplacian, which only sees differences
between *adjacent* pixels. A per-frame gain mosaic lives at low spatial
frequency; a high-pass statistic cannot see it. **The independent-per-pixel
mosaic is the wrong model of a selection arm, and the real arms say so.**

### 4.2 The claim's statistic agrees with the binary's own `n_eff` map

An entirely separate check, using a quantity the claim never touches. Inside a
patch, variance adds, so the predicted sigma ratio is `sqrt(mean(1/n_eff))` — an
RMS, not `1/sqrt(mean n_eff)`.

| condition | patch | mean n\_eff | tool-predicted | measured | deviation |
| --- | --- | --- | --- | --- | --- |
| photometric on | claim | 69.51 | 0.1362x | 0.1408x | **+3.3%** |
| photometric off | claim | 69.58 | 0.1366x | 0.1382x | **+1.2%** |
| photometric on | pin argmin | 31.74 | 0.5310x | 0.6196x | +16.7% |
| photometric off | pin argmin | 31.73 | 0.5298x | 0.6182x | +16.7% |

At the claim's patch the claim's statistic and the binary's independent n_eff
map agree to **1.2–3.3%**. Both deviations are **positive** — the measurement
reads *less* improvement than the tool claims, which is the conservative
direction. There is no detectable content inflation.

### 4.3 Across the plane, admission does not predict the error at all

400 windows on the pinned arms, each with its measured ratio, the tool's
prediction from the n_eff map, and its admission ratio. Restricted to the 22
**informative** windows — those where the prediction is below 0.80, so the two
arms are not trivially the same image — over a predicted range of 0.107 to 0.80:

| quantity | value |
| --- | --- |
| corr(tool prediction, measured ratio) | **+0.997** |
| corr(admission ratio, log deviation) | **−0.002** |
| median absolute deviation | **2.8%** |

And in the band the claim lives in, predicted ratio below 0.20 — 13 windows
whose **median admission ratio is 1.66, all of them failing admission** — the
measured median is 0.1228x against a predicted median of 0.1213x, a deviation
of **+2.7%**.

**Thirteen windows that fail admission, and the arm-vs-arm ratio is right
anyway, to under 3%.**

### 4.4 The mechanism, stated correctly

An arm-vs-**single-frame** ratio has an arbitrary member of the bracket in the
denominator. That frame carries the bracket's full non-stationarity — its own
focus state, its own photometric level, its own everything — none of which the
merged arm shares. Admission is the right gate there.

An arm-vs-**arm** ratio between two merges of the same bracket has no such
denominator. Both arms elect the same near-winner frames through the same
spatially coherent winner field and render the same scene content; only the
number of frames averaged differs. The bracket's non-stationarity is
**common-mode and cancels**. Admission does not govern it.

So the answer to the orchestrator's question 3 is: **the mechanism applies to
arm-vs-single-frame only.** The README's paragraph is arm-vs-arm and is not
touched by it.

---

## 5. What is actually wrong with the paragraph

The claim's *number* is sound as a measurement of what its build did. What
fails is **reproduction on the shipping binary**, and it fails in three
separate places.

**(a) `thesis_demo.py`'s own ROI search lands somewhere else.**

| condition | argmin | gate0 | gate2 | ratio | equiv frames |
| --- | --- | --- | --- | --- | --- |
| 925d03d — the claim | y=912 x=384 | 0.006381 | 0.000987 | **0.1546x** | **41.82** |
| pin, photometric on | y=1344 x=368 | 0.010166 | 0.006299 | **0.6196x** | **2.61** |
| pin, photometric off | y=1344 x=368 | 0.010182 | 0.006295 | **0.6182x** | **2.62** |

Both pinned conditions agree with each other and disagree with the claim, so
this is **not** the photometric term — it is the merge itself having changed.
Re-run today, the paragraph's own script reports **0.6196x, equivalent to 2.6
frames**, not 0.1546x and 41.8 frames.

**(b) The paragraph's `n_eff` figure has moved by 2.88x.** The paragraph says
"`--gate 2` reports mean `n_eff` 15.077". The pinned binary's banner on the same
argv and subject reports **`mean n_eff 5.229`**, with **62.57%** of pixels at
n_eff = 1 and a self-reported whole-plane `pred sigma gain (model)` of
**0.8556x**.

**(c) The paragraph's `--gate 0` figures have moved slightly.** It says "mean
`n_eff` 1.000 with 100.00% of pixels at `n_eff` = 1". The pin reports **1.006**
and **99.37%**.

### What I would put in the paragraph's place

The claim is defensible **as a statement about the build it was made on**, and
that has to be said out loud, because its headline does not survive to the
shipping binary. If the orchestrator wants a number that holds today, the
honest options are:

* **Keep the ROI, re-quote on the pin.** At the claim's own patch the pinned
  shipping binary gives **0.009210 → 0.001297, a ratio of 0.1408x, equivalent
  to averaging 50.4 frames**, corroborated by the binary's own n_eff map to
  3.3% (`mean n_eff 69.51` in that patch). This keeps the paragraph's structure
  and its force. It requires stating that the ROI is inherited from the
  original run rather than re-chosen, because the re-chosen one is (b).
* **Re-run the script and quote what it says.** **0.6196x, 2.6 frames**, at
  `y=1344 x=368`, with `mean n_eff 5.229` — a far weaker paragraph, and an
  honest one. Note that this patch does **not** pass admission even after the
  photometric correction (2.691 raw, 1.738 corrected), so it is a worse ROI as
  well as a worse number.
* **Retract the "41.8 frames" framing regardless.** On the shipping binary,
  62.57% of this subject's pixels average exactly one frame, and the tool's own
  whole-plane model predicts a sigma gain of 0.8556x. A 41.8-frame figure from a
  200x200 patch is a best case by a factor of roughly 50 against the plane, and
  SYNTHESIS fact 1355 already says so. Nothing measured here contradicts that
  caveat; this document strengthens the case for keeping it prominent.

I have not edited `README.md`.

---

## 6. `tweezers-cpl` — checked, and the flag does not stand

`tweezers-cpl` appears in `README.md` at L288, L312 and L442 (qualitative), and
in exactly one quantitative table, L878–885: **gradient kurtosis inside
low-detail regions, merge against argmax**. That is not a flat-ROI noise claim,
and by §4 it is arm-vs-arm, so the admission test does not govern it.

One separate mechanism was worth testing, because the binary's own
`--photometric` help names `tweezers-cpl` at **13.765%** per-frame drift, the
largest figure it quotes: an uncorrected per-frame gain turns a selection arm
into a mosaic of differently-scaled frames, which is exactly the
"piecewise-constant plateaus with hard steps" that kurtosis is built to detect.
Measured on single frames, planting and removing the per-frame gain on a
selection mosaic:

| subject | patch drift | kurtosis, gain present | kurtosis, gain removed | ratio |
| --- | --- | --- | --- | --- |
| `tweezers-cpl` | 27.65% | 11.17 | 5.15 | **2.17x** |
| `leaf-2-cpl` | 9.20% | 4.10 | 3.85 | 1.06x |
| `109MSDCF` | 1.97% | 9.74 | 9.47 | 1.03x |

So the mechanism is real and large on `tweezers-cpl`. **But the table's own
numbers falsify it as an explanation of that table.** The mechanism predicts
that the highest-drift subject shows the largest argmax excess. The table has
`tweezers-cpl` at the **smallest** ratio, 1.17x, and `bee-3-cpl` — which the
same help text puts at 1.629% drift — at the **largest**, 2.79x. That is the
opposite ordering. The flag is raised, tested, and withdrawn.

(The 27.65% above is a max/min over one 100x100 patch across 9 sampled frames,
not the binary's globally fitted 13.765%; it is a local figure and is quoted
only to show the plant was potent.)

---

## 7. A defect found while checking this, unrelated to the claim

`stack --help` on the pinned shipping binary says of `--photometric`:

> Three-valued: `off` (the default), `on`, or `auto`.

Every estimator run in this campaign, with no `--photometric` on the command
line and `STREHL_PHOTOMETRIC` unset in process, user and machine scope, reports:

```
--- photometric normalisation (M99, OPT-IN) ---
mode            : on (unconditional, as asked)
```

Checked on a minimal argv (`stack <src> --out <dst> --gate 2`, nothing else) —
same banner. And checked by bytes:

| arm | sha256 |
| --- | --- |
| `gate0` flagless | `0A0548DEEE1801FF5A9C606B2AB73347E99A91FC46AAFCEF32EDBE66309F081A` |
| `gate0 --photometric off` | `53B66113B1FD0F2CC1FBC0427C91D18C5FA0F672FF589B50D00711B713049B29` |

**The renders differ, so the flagless default is `on`, and the help text is
wrong.** The banner's "as asked" is also wrong — nothing asked. This matters
beyond documentation: any corpus measurement that assumed the estimator merge
does not normalise photometry, or that compared a pre-`27646057` render against
a post-`27646057` one, has an uncontrolled per-frame gain term in it. On this
subject that term is worth 1.02x on an arm-vs-arm noise ratio (§4.1) and 33% on
a single-frame temporal statistic (§3.4), so its size is very much a function of
what is being measured.

---

## 8. What I could not measure

* **The 925d03d build's `n_eff` map.** That build predates `--n-eff-map` output
  I could regenerate without rebuilding, and rebuilding it would violate the
  one-binary rule for everything downstream. So the claim's own 41.8 frames
  cannot be reconciled against its own build's n_eff — only against the pin's
  (69.51 in that patch, predicting 0.1362x against the pin's measured 0.1408x).
* **The claim's original banner.** `thesis_demo.py` did not capture stderr and
  `C:\dev\strehl-out\ORCH-thesis\` holds only the TIFFs and PNGs. The 925d03d
  configuration is established from git rather than from a run log.
* **All 182 frames.** 37 evenly spaced single frames were rendered. The
  temporal statistic is a 37-sample estimate; the whole-plane level span it
  yields (1.0953) matches the binary's 182-frame figure (1.1010) to 0.5%, which
  bounds the sampling error on the term that matters.
* **The demosaic's contribution.** The claim's statistic is a 3x3 Laplacian on a
  render whose own banner says "Interpolated — do not measure resolution on it".
  Demosaic correlates neighbouring pixels, so the residual is not a clean
  per-pixel noise estimate. Both arms are demosaiced identically, and §4.2's
  agreement with the n_eff map to 1.2–3.3% bounds any residual asymmetry at
  under 3.3%. It is not separately measured.
* **Whether `tweezers-cpl`'s kurtosis table would move if re-rendered with
  `--photometric on`.** §6 tests the mechanism on single frames and finds the
  table's own ordering contradicts it, which was enough to withdraw the flag. A
  re-render was not done.

---

## 9. Reproduction

```
python experiments/BUILD-PYRNOISE/claim_roi.py      # recover the claim's ROI, exactly
powershell experiments/BUILD-PYRNOISE/render_claim.ps1      # the claim's argv, pinned binary
powershell experiments/BUILD-PYRNOISE/render_photom_ab.ps1  # the --photometric A/B
python experiments/BUILD-PYRNOISE/diagnose.py       # cross-build grid, n_eff reconciliation
python experiments/BUILD-PYRNOISE/gated.py          # near-winner gating; informative-window rebin
python experiments/BUILD-PYRNOISE/photom.py         # the level term, and its specificity
python experiments/BUILD-PYRNOISE/levelterm.py      # global vs local; arithmetic prediction
python experiments/BUILD-PYRNOISE/control.py        # null, potency, positive control, tweezers
python experiments/BUILD-PYRNOISE/final.py          # the damage number
```

`adjudicate.py` is kept unchanged although its central hypothesis is falsified,
because §3.2, §3.3 and §4.1 are only legible next to the thing they refute.
Its §7 reconciliation used `1/sqrt(mean n_eff)` where the correct predictor is
`sqrt(mean(1/n_eff))`; `diagnose.py` fixes it and says so in place.
