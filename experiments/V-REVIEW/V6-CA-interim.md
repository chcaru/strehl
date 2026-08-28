# V-REVIEW: independent scoring of DELIVER-V6's CA re-fit -- INTERIM

Written 2026-08-28 01:38, at session wind-down. **This is unfinished and says so.** 11 of 26
subjects are scored; the remaining 15 had not rendered when compute was handed
back to the render.

I am the independent eye on this render per ORCH's assignment. I scored the
images, not DELIVER-V6's report; I have read none of its conclusions.

## 1. Endpoint, and why it is not the statistic you distrusted

Signed radial displacement of R against G, in ppm of radius, measured at
gradient sites and **sign-symmetric by construction**. It is deliberately NOT a
magenta counter. The statistic that scored `--fix-ca off` as 1.82x better counts
magenta specifically and is therefore blind to the opposite-sign orange/cyan
shape that over-correction produces. This endpoint sees both signs.

Sites are chosen once from the OLD master's green channel and applied to both
images, so every comparison is **paired per site**. That is not cosmetic: the
unpaired form injected +16.8 ppm of phantom signal on `dry-erase` and -97.7 ppm
on the ruler, purely from which sites voted.

## 2. Commissioning (MEASURED, through the shipped entry point `score()`)

| arm | result |
|---|---|
| identity, old vs itself | `d_ppmR` 0.000000000, ratio 1.000000000, width_ratio 1.000000000 |
| positive, planted -508.4 ppm | recovered **-508.6 ppm** at 41.5 sigma |
| specificity, blue untouched | **+0.0 ppm** |
| confound null, pure resample | width_ratio **1.0000** |

The positive plant is deliberately the exact magnitude of the coefficient under
test. An identity test alone proves only that the instrument is quiet.

## 3. Result

| subject | n | ppmR old | ppmR new | delta | sigma | ratio | d_ppmB | widthR |
|---|---|---|---|---|---|---|---|---|
| `112MSDCF` | 153 | +261.7 | +89.0 | -175.3 | 24.8 | 0.358 | -16.7 | 0.9956 |
| `113MSDCF` | 247 | +263.1 | +88.8 | -181.8 | 33.7 | 0.340 | -14.9 | 0.9964 |
| `bee-1-cpl` | 253 | +469.6 | +251.4 | -211.2 | 56.8 | 0.535 | -17.4 | 0.9943 |
| `bee-2-cpl` | 237 | +328.3 | +135.9 | -214.0 | 40.3 | 0.459 | -16.9 | 0.9951 |
| `bee-3-cpl` | 238 | +315.3 | +105.8 | -227.4 | 51.1 | 0.404 | -20.1 | 0.9950 |
| `coffee-bean` | 149 | +248.8 | +61.2 | -237.3 | 28.9 | 0.615 | -9.7 | 0.9977 |
| `coffee-bubbles` | 34 | +177.8 | +30.9 | -152.1 | 7.2 | 0.459 | -8.9 | 1.0010 |
| `couch-fibers-cpl` | 215 | +304.6 | +120.9 | -186.6 | 36.5 | 0.517 | -10.8 | 0.9944 |
| `dry-erase-marker-head-cpl` | 248 | +315.1 | +85.8 | -226.9 | 42.5 | 0.428 | -18.1 | 0.9985 |
| `flat-on-ruler-cpl` | 260 | +275.3 | +143.9 | -131.6 | 59.8 | 0.530 | -13.4 | 1.0239 |
| `flower-bud-alone-cpl` | 158 | +282.5 | +104.8 | -178.5 | 23.6 | 0.596 | -15.3 | 0.9992 |

| subject | verdict | why |
|---|---|---|
| `109MSDCF` | UNSCORED | picker refused: 11 sites < 12 floor |
| `119MSDCF` | UNSCORED | too few sites voted |

- scored: **11**; ratio < 1 (improved) on **11 of 11**; ratio > 1 on **0**
- `d_ppmR` median **-186.6 ppm**, range -131.6 .. -237.3, all at 7.2 sigma or better
- ratio median **0.459**, range 0.340 .. 0.615

**Reading: the re-fit reduces red-green misregistration on every subject that
could be scored, by roughly half to two-thirds. No subject got worse.**

## 4. What this does NOT say

1. **Improvement, not cure.** `ppmR_new` remains positive (+30.9 .. +251.4).
   Residual outward CA is present on every subject.
2. **Pre-registered P3 -- "blue unchanged" -- is REFUTED as stated.** Blue moved
   at 3.1 to 32.8 sigma. It moves ~12x less than red (median |dB/dR| 0.082), so
   it cannot account for red's change, and a generic build difference would have
   moved both alike. But P3 failed and is recorded as failed.
3. **The pre-named control subject is UNRESOLVED.** `highly-angled-ruler-mm-cpl`
   never rendered. See section 6.
4. **2 subjects are UNSCORED, which is not the same as clean.**

## 5. Build-difference confound, bounded by measurement

Old and new masters come from different builds, so any difference not
attributable to CA is confounded. Bound rather than argument:

- paired edge-width variance ratio old vs new: **0.9943 .. 1.0239**; worst is
  `flat-on-ruler-cpl` at 1.0239, about 0.23 px of added sigma.
- measured paired blur sensitivity of the CA endpoint: **exactly +0.0 ppm at
  sigma=0.3 on all four subjects tested**; non-zero only at sigma >= 0.6, worst
  -77.2 ppm at sigma=1.2 on the ruler.

A ~187 ppm effect therefore sits far above the confound floor in this regime.

## 6. The ruler prediction is OPEN

`PREDICT-ruler.md` was committed in `82b1c411` with the master verified absent
from disk. It predicts `d_ppmR` in -237 .. -132, `ppmR_new` about **-394**,
ratio about **1.9** -- i.e. the one subject the fix makes worse, because its
baseline is already the opposite sign (`ppmR_old` = -207.1, MEASURED).

**It never rendered, so the prediction is neither confirmed nor refuted.** To
resolve it, one command after the master exists:

    python vc_score.py highly-angled-ruler-mm-cpl

## 7. Instrument failures I am disclosing rather than hiding

- **`vc_ca.py` FAILS its BLUR-ONLY arm on the ruler** (4/5 arms; paired -77.2 ppm
  at sigma=1.2, 7.3 sigma from zero) while passing **5/5** on `dry-erase`. I did
  not loosen the tolerance to make it pass.
- **`vc_sharp.py`'s sigma-equivalent estimator FAILED commission** on all three
  width statistics below ~0.5 px (errors -0.19 to -0.59 against planted sigma).
  Its numbers are used nowhere. Only the raw paired width RATIO, whose null is
  exactly 1.000, is used.
- Two defects in my own estimator were found by commissioning and fixed before
  any scoring: a missing `align` division, and orientation-dependent aliasing in
  `profile()` that measured gain **0.170 at 45 degrees**. The latter alone had
  produced a spurious 1.114 "real-edge asymmetry" that vanished to 0.988 once
  fixed.
