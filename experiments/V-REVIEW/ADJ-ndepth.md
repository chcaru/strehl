# Adjudication: deeper-vs-shallower, and whether `fit_to_cover` explains it

Instrument: `experiments/ORCH-drift-check/contrast_ms.py`, **unmodified**, invoked
as a subprocess. Arms are V-SOFTCHECK's and V-DILUTE's own rendered masters, both
produced by the pin `9b05d0b7` with an explicit `--exposure` and **no
`--auto-exposure`** (arm 3). Everything below is MEASURED.

---

## 0. Verdict

1. **There is no contradiction to adjudicate. The two lanes measured different
   subjects.** V-SOFTCHECK's `0.114 softer` is `113MSDCF`
   (`experiments/V-SOFTCHECK/PREREG-ninvariance.md:76`). V-DILUTE's `1.74x
   sharper` is `bee-3-cpl` (`experiments/V-DILUTE/PREREGISTRATION.md:5`, arms
   named `A_*`). V-DILUTE raised this possibility itself and was right to.
2. **Both comparisons are VOID on the instrument null**, in opposite directions.
3. **Both were scored at 0.30-0.35 cyc/px, which lies inside band 0
   (0.25-0.500), qualified NOISE.** Neither number is an acuity measurement.
4. **`fit_to_cover` is real, costs 1.6-2.1% of band-1 EDGE, and is far too small
   to explain either claim.** Its premise -- `k` falling with `N` -- is refuted.

---

## 1. The instrument, commissioned before use

A null that is quiet on everything is not a null, it is a broken probe. Three
arms on `bee-3-cpl N=63`:

| arm | band-0 FLAT | band-1 EDGE (acuity) | coarsest EDGE (null) |
| --- | ---: | ---: | ---: |
| **IDENTITY** (byte copy) | **1.0000** | **1.0000** | **1.0000** |
| ROUND TRIP `k=0.9208` | 0.6710 | 0.9820 | 1.0016 |
| **BLUR sigma=0.5** (positive control) | 0.5350 | **0.8593** | 0.9983 |

IDENTITY returns exactly `1.0000` in all six bands on both site classes. BLUR
drops band-1 EDGE by 14.07% **while the null stays at 0.9983** -- so the null is
**specific**, not merely quiet: the instrument can see a fine-scale loss without
the null moving. Only after this does a null failure mean anything.

## 2. The two comparisons, re-taken

`A` = shallow, `B` = deep, so ratio > 1 means the deeper stack has MORE energy.

| subject | lane | N | band-0 FLAT | **band-1 EDGE** | **NULL** | tolerance | verdict |
| --- | --- | --- | ---: | ---: | ---: | --- | --- |
| `113MSDCF` | V-SOFTCHECK | 31 vs 63 | 1.2317 | 1.0102 | **0.9866** | +-0.005 | **VOID** |
| `bee-3-cpl` | V-DILUTE | 33 vs 63 | 1.2371 | 1.2433 | **1.0213** | +-0.005 | **VOID** |

`|0.9866 - 1|` = 0.0134, **2.7x** the tolerance. `|1.0213 - 1|` = 0.0213,
**4.3x** the tolerance. Per criterion 3 both comparisons are void and I stop
there, as instructed.

**The two nulls fail in OPPOSITE directions, and that is the whole shape of the
disagreement.** On `113MSDCF` the deep arm has less energy at every coarse
scale; on `bee-3-cpl` it has more, at every band, rising monotonically from
1.0213 coarse to 1.2622 fine. Two subjects differing globally in opposite
senses will hand two lanes opposite signs no matter which band they read.

**Both arms are unclipped**, so this is not the saturation trap: `113MSDCF`
0.09% / 0.09%, medians 14130 and 14380 (`clipcheck.py`).

**A note on the band.** `0.30-0.35 cyc/px` sits inside band 0, `0.25-0.500`,
which this corpus qualified as NOISE. V-SOFTCHECK's own `ninvariance.py:22-23`
records `PRIMARY=3  # 0.20-0.25 ... the only promotable band` and `SECOND=4  #
0.25-0.30, reported, NOT gated`. Fact 1789 promotes `0.30-0.35`, a band beyond
even the one that lane declined to gate on.

**On the qualified acuity bar, neither subject shows deeper as softer**:
band-1 EDGE is 1.0102 and 1.2433, both >= 1. That does not promote to a finding,
because the null voids both comparisons -- but "deeper is softer" does not
survive on the qualified band even on its own subject.

## 3. `k` versus `N`, from each run's own banner

| subject | N | k | 1/k upsample |
| --- | ---: | ---: | ---: |
| `bee-3-cpl` | 33 | 0.9198 | 8.72% |
| `bee-3-cpl` | 63 | 0.9208 | 8.60% |
| `bee-3-cpl` | 105 | 0.9174 | 9.00% |
| `bee-3-cpl` | 299 | 0.9321 | 7.28% |
| `bee-1-cpl` | 32 | 0.9279 | 7.77% |
| `bee-1-cpl` | 64 | 0.9307 | 7.45% |
| `bee-1-cpl` | 149 | 0.9321 | 7.28% |
| `bee-3-cpl` (HEAD) | 22 | 0.9021 | 10.85% |
| `bee-3-cpl` (HEAD) | 299 | 0.9321 | 7.28% |

**`k` does not shrink as `N` grows. Within every subject it RISES**, so the
upsample gets *smaller* on deeper stacks -- the opposite of the premise. The two
data points behind the hypothesis, `109MSDCF` N=22 `k=0.9870` and `bee-1-cpl`
N=299 `k=0.9321`, are **different subjects**, so they measure subject-to-subject
variation, not an `N` effect.

**And `k` is not a function of `N` at all -- it is a function of which frames you
took.** At N ~ 150 on the same subject: `0.9228` (step2), `0.9359` (odd149),
`0.9595` (first150), a spread of **0.0367**. Across N=33 -> 299 the whole spread
is **0.0147**. **The selection spread is 2.5x the count spread**, so the count
effect is not resolvable against it. V-DILUTE reached this independently
(`V-DILUTE.md` point 5, `0.9228` vs `0.9359`).

## 4. Attribution: the upsample is real, and far too small

Round trip = downscale by `k`, upscale by `1/k`, scored against the original.

| k | 1/k upsample | band-0 FLAT | band-1 EDGE | NULL | null ok |
| ---: | ---: | ---: | ---: | ---: | --- |
| 0.9021 | 10.85% | 0.6590 | 0.9793 | 1.0000 | yes |
| 0.9198 | 8.72% | 0.6683 | 0.9802 | 1.0000 | yes |
| 0.9208 | 8.60% | 0.6710 | 0.9820 | 1.0016 | yes |
| 0.9321 | 7.28% | 0.6764 | 0.9810 | 1.0000 | yes |
| 0.9359 | 6.85% | 0.6785 | 0.9823 | 1.0012 | yes |
| 0.9595 | 4.22% | 0.6928 | 0.9824 | 1.0000 | yes |
| 0.9870 | 1.32% | 0.7100 | 0.9844 | 1.0000 | yes |

**Three findings.**

**(a) The full round trip costs only 1.6-2.1% of band-1 EDGE energy**, and the
cost is nearly flat across the entire realistic `k` range.

**(b) The differential between the two arms actually compared is negligible.**
`bee-3-cpl` N=33 `k=0.9198` against N=63 `k=0.9208`: **band-0 FLAT 0.0027,
band-1 EDGE 0.0018.** V-DILUTE's claim is `1.74x`, i.e. +74%. The mechanism is
smaller than the claim by roughly **270x**. **The upsample does not account for
the effect.**

**(c) A round trip cannot cause a null failure.** It passes at every `k`
(1.0000-1.0016), because it is geometrically neutral -- net magnification 1. So
whatever makes the lane comparisons fail the null, it is not `fit_to_cover`.

A pure magnification difference *does* move the null, and the observed failures
are too large for the measured `k` difference to produce:

| magnification | band-0 FLAT | band-1 EDGE | NULL | null ok |
| ---: | ---: | ---: | ---: | --- |
| 1.0011 (the arms' real `k` ratio) | 0.8031 | 0.9933 | **1.0025** | yes |
| 1.0050 | 0.8259 | 0.9973 | 1.0113 | NO |
| 1.0134 | 0.8487 | 1.0005 | 1.0273 | NO |
| 1.0213 | 0.8683 | 0.9988 | 1.0348 | NO |

The arms' true magnification ratio, `0.9208/0.9198 = 1.0011`, yields a null of
**1.0025 -- which passes**. The observed `bee-3-cpl` null is **1.0213**, needing
roughly `1.0105`, about **8x** more magnification difference than the arms have.

## 5. The one place the mechanism IS potent, and it is where both lanes measured

The round trip moves **band-0 FLAT to 0.659-0.710, a 29-34% attenuation** --
and band 0 is `0.25-0.500`, which contains the `0.30-0.35` both lanes scored.
`fit_to_cover` is nearly harmless where acuity lives and severe where they were
reading. It did not bias these two comparisons only because the compared arms
happened to share a `k` to within 0.11%. **Any future comparison across arms
with materially different `k` is contaminated in that band**, which is exactly
V-DILUTE's point 5, reproduced here from the other direction.

## 6. What I did NOT establish

- **Why the lane comparisons fail the null.** Not the resample, not the tone
  placement (medians rescale by 1.0030 and 0.9863). The `bee-3-cpl` deep arm has
  more energy in *every* band at *both* site classes. Mechanism unidentified.
- **Whether deeper is softer at all.** Both comparisons are void; I am not
  substituting my own sign for theirs.
- **`113MSDCF` `k` values.** All five `master-N*.tiff.log` files in
  `V-SOFTCHECK/ncurve/113MSDCF` are **0 bytes**, so that subject's coverage
  lines are unrecoverable and its `k` is absent from the table above.
- **Crop mode.** Not implemented, not tested, per instruction.
