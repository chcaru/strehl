# M22 — Hot pixels: how bad is this sensor, actually?

> **NOT INDEPENDENTLY VERIFIED.** Same author as the measurements. Rule 12.
> Labels are MEASURED / DERIVED / ARGUED throughout.

Tests review item **R11**, which asserted that hot pixels and dust are
"the kind of defect reviewers of a 'SOTA' claim find in five minutes" and
should be fixed from the 242 already-delivered dark frames.

The review is right that it is cheap. It is wrong about the urgency, and the
delivered darks turn out to be **shot at the wrong exposure** to answer the
question properly.

## 1. MEASURED — the dark frames

242 frames, 11 groups of 22, ISO 50/100/200/250/400/500/640/800/1000/1600/2000.
First two of each group dropped as the owner instructed (stabilisation). All 11
groups are **1/100 s**. Mean dark level sits at +0.15 to +0.26 DN above the 512
black point — essentially nothing, as expected for a 10 ms exposure.

A pixel is flagged when its 20-frame mean exceeds its same-colour 3x3 plane
median by 8x the robust sigma of that excess.

| flagged in | pixels | fraction |
|---|---:|---:|
| >= 1 group | 188,815 | 0.5731% |
| >= 6 groups | **11,393** | **0.0346%** |
| all 11 groups | 352 | 0.0011% |

## 2. MEASURED — recurrence proves the map, and kills 95% of it

108,776 pixels were flagged in exactly one group. A real hot pixel is a property
of the silicon and must recur. Against a Binomial(11, p) independence baseline
with the observed per-group rate p = 0.001055:

| groups | observed | expected by chance |
|---:|---:|---:|
| 1 | 108,776 | 3.78e+05 |
| 2 | 37,202 | 2.0e+03 |
| 3 | 16,775 | 6.33 |
| 6 | 3,947 | 2.09e-08 |
| 11 | 352 | 5.94e-26 |

Single-group flags are *fewer* than chance predicts — they are the threshold's
false positives. From k=3 upward the excess over chance is astronomical. So the
population is unambiguously real, and **recurrence, not the sigma threshold, is
the correct discriminator.** The defensible map is the >=6 set: 11,393 pixels,
346 per Mpx.

This is a reusable pattern: the darks were delivered as 11 ISO groups for a
different reason (M4's read-noise work), and that grouping turns out to supply a
free, built-in replication test. Threshold choice stopped mattering.

## 3. MEASURED — and it does not matter much

The number that decides whether to care is not the count. It is the magnitude
**in a real frame**. Measured on 6 real frames of `109MSDCF` (ISO 160, 1.3 s),
residual against the same-colour local median, against a random control set:

| set | mean | median | p99 |
|---|---:|---:|---:|
| stable-hot (>=6 groups) | +3.112 DN | 0.000 | +62 |
| random control | +0.094 DN | 0.000 | +53 |
| **excess** | **+3.018 DN** | 0.000 | +9 |

The always-hot 352 are barely worse: **+3.72 DN**. Only **3 pixels** on the
entire sensor are both always-hot and above 100 DN dark excess. There is no
severe tail.

Stratified by local signal, against the calibrated noise floor
`sigma = sqrt(g*S + (RN*g)^2)`, `g = 0.3663 DN/e-`, `RN = 4.20 e-` at ISO 160:

| band | n | excess | sigma(S) | **excess/sigma** |
|---|---:|---:|---:|---:|
| shadow 50–200 DN | 5,364 | +2.65 | 6.75 | **0.39** |
| midtone 200–1k | 19,540 | +2.92 | 12.99 | **0.22** |
| upper mid 1k–4k | 43,376 | +3.09 | 24.01 | **0.13** |

The excess is flat at ~3 DN across bands — the signature of a fixed additive
dark-current offset, which is what the physics predicts and a useful sanity
check on the measurement. Its significance falls as signal rises, and even in
the darkest well-populated band it is **0.39 sigma**.

**MEASURED VERDICT: on this sensor at these settings, hot pixels displace a
pixel by at most about four tenths of its own noise.** R11's premise — that this
is a five-minute embarrassment waiting to happen — is not supported here. The
A7C II is clean.

Limit: this scene has almost no deep shadow (78 pixels below 50 DN), so the
`<50 DN` band could not be measured. A genuinely dark subject is untested.

## 4. MEASURED — but the delivered darks are at the wrong exposure

Dark current scales with **time**. The darks are 1/100 s. The real stacks are
not:

| stack | ISO | exposure | vs the darks |
|---|---:|---:|---:|
| `112MSDCF` | 500 | 1/60 s | 1.7x |
| `113MSDCF` | 500 | 1/30 s | 3.3x |
| `119MSDCF` | 50 | 1/8 s | 12.5x |
| `coffee-bean` | 50 | 4/5 s | 80x |
| `109MSDCF` | 160 | 13/10 s | **130x** |
| `coffee-bubbles` | 1000 | 5/2 s | **250x** |

So §1's map is the set of pixels detectable at 10 ms. A pixel with *moderate*
dark current would be invisible there and plainly visible in a 1.3 s frame. The
map is therefore **complete for the wrong exposure**. (This does not retroactively
affect M4, whose read-noise work is exposure-independent.)

## 5. MEASURED — closing that gap without new captures, and a control that nearly killed it

A pixel anomalous in **two different scenes** is scene-independent, hence a
sensor defect. Comparing mean residual maps from `109MSDCF` (1.3 s, ISO 160) and
`coffee-bean` (0.8 s, ISO 50):

The first version of this test reported overlap against an *independence*
baseline and gave 1.9–6.0x enrichment with over a million "defects" — which is
absurd, and the reason is that both subjects sit centre-frame, so the two flag
maps share large-scale spatial structure that has nothing to do with defects.

**The shift control fixes it.** Rolling one map by an even offset preserves CFA
phase and every spatial statistic while destroying per-pixel correspondence:

| threshold | aligned | shifted (mean of 4) | ratio | verdict |
|---:|---:|---:|---:|---|
| 10 DN | 1,240,872 | 754,056 | 1.65x | spatial structure; inconclusive |
| 20 DN | 173,830 | 75,156 | 2.31x | real excess |
| 40 DN | 1,091 | 252 | **4.33x** | real excess |

**Positive control:** the same shift test applied to the known-real dark-derived
map gives 1.91x / 2.36x / 16.00x — the same range. A population known to be real
behaves as the statistic says it should, which is what makes the 4.33x readable.

At the 40 DN bar (~4 sigma of an 8-frame mean), the excess over the shifted
baseline is **~839 scene-independent defects, of which the 1/100 s dark map
contains 5.** The darks miss essentially all of them.

## 6. What follows

1. **Build it, but do not prioritise it.** A recurrence-derived hot-pixel map is
   cheap, correct, and belongs in the calibration path. It should not preempt the
   merge. MEASURED impact at the current operating point is <= 0.39 sigma.
2. **The map must come from darks at working exposure**, not 1/100 s. Added to
   [`../captures-needed.md`](../captures-needed.md) as a new request.
3. **Recurrence beats thresholding.** Whatever ships should derive the map from
   agreement across independently captured groups, not from a sigma cut on one.
   This removed the threshold as a tuning knob entirely.
4. ARGUED: because the in-situ excess is *additive and constant* (~3 DN across
   three signal decades), it is naturally handled as an offset term in the
   existing noise/calibration model rather than as a separate inpainting stage.
   The review proposed detect-and-inpaint; subtract-and-widen-sigma is simpler
   and does not invent pixel values. Untested.

## 7. What was NOT measured

- **Dust.** Dust is a *multiplicative* attenuation, visible in flats, not darks,
  and shows as a negative residual. Every test here looks at positive excess
  only. Dust remains blocked on the flat-field capture (`captures-needed.md` §4).
- **Dead/cold pixels.** 23,710 flags on the low side at ISO 1600, never tested
  for recurrence. Unmeasured.
- **Smearing under warp.** The review's specific worry — that fixed-sensor
  defects smear into trails once frames are warped — was not tested at all.
  It requires the aligner, and it is the right follow-up if this is built.
- **Deep shadow.** See §3.
- Only 6–8 frames per stack, one crop-free plane pass, two scenes.

## 8. Reproducing

```
experiments/m22-hot-pixels/src/
  01-map-from-darks.py             the 242-frame map; writes hotcount.npy
  02-chance-and-light-frames.py    Binomial baseline + first light-frame test
  03-exposure-and-severe-tail.py   exposure mismatch table; always-hot subset
  04-stratified-by-signal.py       excess/sigma by signal band -- the verdict
  05-cross-scene.py                cross-scene overlap, WITHOUT the shift control
  06-shift-control.py              the control that makes 05 readable; run both
```

Needs read access to `D:\macro-dark-frames`, `C:\dev\macro\test\`. Script 05 is
kept deliberately: its independence baseline is wrong and the diff between 05
and 06 is the lesson.
