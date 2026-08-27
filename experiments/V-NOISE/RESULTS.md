# V-NOISE — results

The noise half of the free-field head-to-head. Pre-registration committed as
`d29074e2` **before** any number here existed; read
`experiments/V-NOISE/PREREGISTRATION.md` first, including its §0 disclosure
that the registration was **not blind**.

This file is the lane's working report. A `docs/research/` home for it needs a
milestone number, which I have asked for and not yet received.

---

## 0. Verdict

**On identical linear inputs, strehl is measurably cleaner than `enfuse` on
chroma noise, by 1.54–1.76×. On luma the advantage is real but its size is not
pinned: the bracket is [1.02, 1.54] and the lower end is LEVEL.**

Against `focus-stack` strehl is cleaner on everything, by 1.16× luma and
2.03–2.24× chroma **after** removing that arm's 8-bit output penalty, which
this lane measured rather than assumed.

And the finding that costs me the most:

> **My own pre-registered primary statistic is withdrawn.** Flat-ROI residual
> sigma — the thing §3.1 named as the headline — is **84.6% scene and 15.4%
> noise** on strehl, measured. Its chroma form additionally failed a guard I
> added after seeing it produce a flattering result. The verdict above comes
> from the estimator I registered as the *secondary* cross-check.

| question | answer | strength |
|---|---|---|
| chroma noise vs `enfuse` | **strehl cleaner, 1.54–1.76×** | MEASURED, robust |
| luma noise vs `enfuse` | **strehl cleaner, [1.02, 1.54]** | MEASURED, size not pinned |
| chroma/luma vs `focus-stack` | **strehl cleaner, 1.16× / 2.03–2.24×** | MEASURED, format-corrected |
| is it a tone measurement? | **no** — −153.1% and +1.2% explained | MEASURED |
| is it a saturation measurement? | **not on the surviving estimator** | MEASURED |

---

## 1. Why these arms are comparable, and why that matters more than usual

Every arm is built from **strehl's own linear TIFFs** (`--linear-srgb
--demosaic`, pinned binary sha256 `15EA7346…82A7B0`). Demosaic and white
balance are therefore identical on both sides and the only remaining difference
is the stacking algorithm. This is the property that made
`docs/research/V-LINEAR2.md` §9's sharpness table trustworthy, and it is worth
restating because for *noise* it is doing even more work: two decoders would
differ in chroma denoise alone by more than the entire effect measured here.

---

## 2. What the instrument actually measures, after the primary failed

Two estimators were registered. They fail in different directions, which is the
only reason to run both — and here one of them simply failed.

**§3.1 PRIMARY — flat-ROI residual sigma. WITHDRAWN as a noise measure.**

`census_src.py` selected FLAT tiles from the **63 source frames**, never from a
stacker output, as the bottom quartile of max-over-frames high-pass variance.
That rule is sound and I would use it again. It is also not sufficient: the
separation between the flat quartile and the median detail tile is only
**2.02×**, and `halfdiff.py` measured the consequence directly, on the same
image, with no assumption about stack depth:

| arm | flat-ROI σ | half-diff σ (noise) | scene term | **noise fraction** |
|---|---:|---:|---:|---:|
| strehl | 0.13211976 | 0.05187 | 0.12151 | **15.4%** |
| `enfuse` | 0.13585008 | 0.08394 | 0.10682 | **38.2%** |
| `focus-stack` | 0.13585464 | 0.09953 | 0.09247 | **53.7%** |

Look at the two comparator rows. They agree to **five decimal places** while
differing by 19% in noise and 15% in scene content — the two effects cancel.
I checked for a loader bug first (different files, different checksums); the
agreement is real. A statistic that reads two materially different images as
identical cannot adjudicate between them.

**§3.2 CROSS-CHECK — half-stack difference. This carries the verdict.**
`0.5·Var(A−B)` on two half-stacks of the same scene. The scene cancels
identically, so no flatness assumption is needed, and any artifact reproducible
across both halves cancels with it.

---

## 3. Commissioning — including the two arms whose answers were fixed in advance

| arm | result | verdict |
|---|---|---|
| NULL — image against itself | 1.000000 | PASS |
| POTENCY — planted σ, flat-ROI, ×0.5 and ×2 | 0.9995, 0.9999 | PASS |
| **POTENCY — planted σ, half-diff, 3 levels over 16×** | **0.9997, 0.9997, 0.9997** | **PASS** |
| TONE — 4×4-block fit, `enfuse` | −153.05% explained | PASS |
| TONE — 4×4-block fit, `focus-stack` | +1.24% explained | PASS |
| **CHROMAGAIN — `enfuse`** | **109.9%, 68.6% explained** | **FAIL** |
| CHROMAGAIN — `focus-stack` | 46.2%, 31.8% explained | PASS |
| QUANT8 — 8-bit penalty, half-diff | +12.4% luma, +33.3%, +54.8% chroma | measured |

Four things in that table are worth more than their line.

**The tone confound is dead here, and the sign says so.** V-HEADTOHEAD2's
fine-scale table died because a 4×4-block tone fit reproduced 89–212% of the
gap. Here the same fit, imported unmodified from `gradetest.py`, explains
**−153%** for `enfuse` — applying it moves strehl's sigma *away from* the
comparator. This is not a tone measurement.

**CHROMAGAIN failed, and it withdrew my headline.** I added it *after* the
first run, because chroma turned out to carry the result and the tone arm only
guards luma. A stacker rendering more saturated chroma raises chroma sigma
without being noisier. It explained **110%** of the `enfuse` chroma-R-Y gap —
so the flat-ROI chroma number is withdrawn too, on top of §2.

**Then I checked whether that guard was itself circular**, because block-
averaged chroma still contains noise and a noisier arm could fake a higher
"gain". `chromagain.py` ran two noise-immune estimators:

| estimator | `enfuse` R-Y | `enfuse` B-Y | reads as |
|---|---:|---:|---|
| DC — per-tile mean signed chroma (noise cancels in the mean) | 1.093 | 0.912 | **level** |
| HALF — coarse variance with measured noise subtracted | 1.986 | 1.378 | **more structure** |

They disagree, and that disagreement is the honest finding: there is **no
saturation difference** (DC straddles 1.0), but `enfuse` does carry more coarse
chroma *structure*. Whether that structure is scene chroma it preserves or
chroma mottling it creates **cannot be determined by this instrument**. Either
way it contaminates the flat-ROI statistic and not the half-diff one, which is
why the verdict rests where it does.

**The 8-bit arm caught a bug in me.** Measured on the half-diff estimator it
inflates chroma B-Y by **54.8%** — so `focus-stack`'s chroma disadvantage is
materially its container, not only its algorithm, and is corrected below. An
earlier version of that arm returned **exactly 1.000 in all three channels**
because a loop variable had rebound to the already-8-bit arm, making the
requantisation a no-op. An impossible-looking answer from an arm whose true
answer is known in advance is what exposed it. That is the second time tonight
a fixed-by-construction arm has paid for itself.

---

## 4. The verdict table (half-stack difference, n = 110 tiles)

Ratios are comparator ÷ strehl; **>1 means the comparator is noisier**.
Medians of paired per-ROI ratios, 95% CI from 2000 bootstrap resamples.

### vs `enfuse --hard-mask` (16-bit, GPL)

| channel | RAW | integer-shift corrected |
|---|---|---|
| luma Y | 1.021 [0.923, 1.155] | 1.540 [1.408, 1.691] |
| chroma R−Y | 1.610 [1.507, 1.752] | 1.763 [1.624, 1.878] |
| chroma B−Y | 1.542 [1.483, 1.663] | 1.538 [1.451, 1.663] |

### vs `focus-stack` merge on Hugin-aligned frames (8-bit, MIT)

| channel | RAW | shift corrected | **RAW, 8-bit penalty removed** |
|---|---|---|---|
| luma Y | 1.269 [1.210, 1.353] | 1.898 [1.790, 2.027] | **1.161** |
| chroma R−Y | 2.211 [2.091, 2.439] | 2.371 [2.264, 2.602] | **2.028** |
| chroma B−Y | 2.530 [2.433, 2.664] | 2.532 [2.407, 2.728] | **2.237** |

**Why two columns, and which to believe.** `docs/research/V-LINEAR2.md` §7
measured strehl's own half-stacks sitting **1.319 px** apart against the
comparators' 0.03 px. Misregistration inflates `Var(A−B)` in proportion to
local gradient, so the RAW column is biased **against strehl**. The shift-
corrected column removes it, and the objection to *that* is that a
min-over-49-candidates search could bias variance downward for everyone.

It does not, and the control is free:

| arm | known misregistration | RAW → corrected |
|---|---|---|
| `enfuse` | 0.03 px | 0.08394 → 0.08436 (**+0.5%**) |
| strehl | 1.319 px | 0.07859 → 0.05187 (**−34.0%**) |

A selection bias would have moved both. Only the misregistered arm moved. So
the correction is removing shift, not fitting noise — and as a by-product this
independently reproduces the prior lane's geometry finding from an unrelated
statistic.

**Chroma is registration-insensitive** (1.610→1.763, 1.542→1.538) because
chroma has low spatial gradient, which is why the chroma verdict is stated
tightly and the luma one is stated as a bracket.

**Band treatment.** §3.3 pre-registered that 0.30–0.48 cyc/px is **SIGNAL** for
a noise question, having been rejected as contamination for the sharpness
question in `docs/research/V-LINEAR2.md` §2. Band-resolved luma noise power
(ratio vs strehl, flat-ROI statistic, so subject to §2's dilution):

| arm | 0.02–0.05 | 0.05–0.10 | 0.10–0.20 | 0.20–0.25 | 0.25–0.30 | 0.30–0.40 | 0.40–0.48 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `enfuse` | 0.700 | 0.827 | 1.008 | 2.096 | 3.267 | 5.487 | 9.404 |
| `focus-stack` | 0.801 | 0.852 | 0.896 | 2.016 | 4.074 | 7.694 | 15.659 |

The ratio rises monotonically with frequency, which is the signature of added
broadband noise rather than a tone or gain difference — an independent
corroboration of the TONE arm from the spectrum's shape.

---

## 5. The obvious objection, and why it fails

**"strehl has less A−B variance because it is blurrier."** A merge that
smooths would show low noise *and* low detail. Two independent measurements
refute it:

1. `docs/research/V-LINEAR2.md` §9 measured strehl **level** with `enfuse` on
   sharpness at 0.20–0.25 cyc/px: 0.977, CI [0.810, 1.181].
2. The scene-term column in §2 above — derived from a *different* statistic in
   this lane — puts strehl **highest**: 0.1215 against `enfuse` 0.1068 and
   `focus-stack` 0.0925, in the same tiles where its noise is lowest.

So strehl carries more scene content and less noise than `enfuse` in the same
regions. That is the first claim this project has that is measured against a
real comparator, on identical inputs, on something other than sharpness.

---

## 6. What this does NOT establish

- **Not a full-stack number.** The half-diff estimator measures half-stacks
  (~31 frames each). Whether the ratio holds at full depth depends on how each
  algorithm's noise scales with frame count, which is unmeasured.
- **Not clipping or rim behaviour.** Those advantages are still measured only
  against strehl's predecessor and single frames. The gap the orchestrator
  named is now half closed, not closed.
- **Not a chroma-detail verdict.** §3's DC/HALF disagreement means "does
  `enfuse` preserve chroma detail strehl loses?" is open, and it is a real
  question, not a rhetorical one.
- **Not shadow-independent.** The FLAT quartile is also the **dark** quartile
  (median tile luma 0.0134 linear). This is a shadow-noise comparison. That is
  the region where noise is most visible in a print, so it is the right place
  to look, but it is one region.
- **One frame set, one scene.** `113`, 63 frames.

---

## 7. Pre-registration deviations, stated plainly

1. **The clip guard was restated.** §2 item 4 fixed "max ≥ 0.98 **or min ≤
   0.02**, any channel". In linear light the featureless quartile is also the
   dark quartile, so that rejected **110 of 110** tiles while the highlight
   half rejected 0. `clipdiag.py` measured this before anything was changed.
   The guard was restated to hard clipping only — a sample on the encoding
   floor or ceiling — and **both tile sets are reported** in `noisefree.py`
   (STRICT n=62, FULL n=110) rather than the deviation being asserted harmless.
   It is: `enfuse` chroma R−Y reads 1.740 STRICT against 1.760 FULL.
2. **CHROMAGAIN was added after the first run**, not pre-registered. It is the
   arm that withdrew the flat-ROI chroma headline, so the direction of the
   addition was against this lane's interest, but it was still added with the
   result in view and should be discounted accordingly.
3. **The primary and cross-check swapped roles.** §3.1 was registered as the
   headline and §3.2 as the check. §2 above is the measured reason for the
   swap; it is not a preference.

---

## 8. Reproduce

```
python census_src.py      # 63 source frames -> flat tile census (cached)
python clipdiag.py        # the clip-guard deviation, measured
python noisefree.py       # primary statistic + full commissioning
python halfdiff.py        # THE VERDICT: half-stack estimator + commissioning
python chromagain.py      # is the CHROMAGAIN guard circular?
```

Reads only `C:\dev\strehl-out\V-LINEAR\lintiff`, `C:\dev\strehl-out\V-H2H2\lin`
and `C:\dev\strehl-out\V-LINEAR2\out`. Writes only
`C:\dev\strehl-out\V-NOISE\census.npz`. `D:\` is not touched.
`C:\dev\strehl-out\SHIP-V2\` is never read.

Reused unmodified: `gradetest.fit_map`/`apply_map` and `h2.BANDS` from
`experiments/V-HEADTOHEAD2/`, and the measured geometry scales in
`experiments/V-LINEAR2/h2free.py`.
