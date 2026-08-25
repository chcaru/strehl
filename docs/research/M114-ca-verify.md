# M114 -- independent verification of the lateral-CA wiring, and three instrument audits

**Role.** M114 is a verifier. M107 authored the lateral-CA wiring (`4bc9abf`) and under
rule 12 may not verify it. Everything below is M114's own measurement, written in M114's
own code, against artefacts committed under `experiments/M114-ca-verify/`.

**Scope of this file.** The four instrument audits ORCH asked to be filed -- `r24` (the
PIL narrowing hazard), `r25` (`camera_to_srgb`), `r26`/`r26b` (quantisation
dose-response) -- together with M114's retractions. Every retracted number is stated
beside its own retraction, not in a separate file.

**Artefacts.** `experiments/M114-ca-verify/src/r24_pil_audit.py`, `r24d_ncc_depth.py`,
`r25_matrix_check.py`, `r26_quant_dose.py`, `r26b_threshold.py`. Outputs
`C:\dev\strehl-out\M114-ca-verify\{r24d,r25,r26,r26b}.json`. Commits `7c323ba`,
`7880a21`, `609cd45`.

---

## 1. Verdict

| item | result |
|---|---|
| **r24** did any reported M114 number read a TIFF through PIL? | **NO** -- all 23 TIFFs read `uint16` via `tifffile`; PIL is write-only in 3 scripts and reads one 8-bit PNG in a 4th |
| **r24d** did M114's own 8-bit narrowing move an answer? | **NO** -- 5/5 needles identical, against a live +3 px roll control |
| **r25** is ORCH's `camera_to_srgb` correction right? | **CONFIRMED** -- E1-E5 all PASS, and grounded in the capture's own metadata |
| **r26** does V-M113's 12-level immunity threshold transfer? | **NO** -- 3/5 needles exact at **2** realised levels |
| **r26b** does level count control quantisation failure? | **NO** -- identical realised counts give 0.00 px and 165.34 px |
| M114's own earlier render-domain numbers | **RETRACTED** -- measured in the sRGB space, see section 6 |

---

## 2. Reconciliation with fact 1783 -- the correction stays off by default

M114 reported that at 1:1 on real crops the wired correction is **better, clearly and
visibly**. Fact 1783 records that the correction **ships off by default**. **These do not
conflict and M114 does not dispute 1783.** The reconciliation, explicitly:

- M114's by-eye read was made on `bee-3-cpl`, which is **one of the two stacks the
  coefficient was fitted from** -- `optics.rs:309` records `measured_from: "M107
  Instrument A: 20 gated ROIs over tweezers-cpl and bee-3-cpl"`. It is an **in-sample**
  observation and was never a transfer claim.
- Default-off rests on **transfer**, which is a different question. M107's own registered
  bar **L4 split 0.950 / 0.541 against a 0.60 threshold**: one direction passes, one
  fails.
- **M114's own data independently supports default-off.** The scene-to-scene ratio of
  native lateral CA measured **1.227** between `bee-3-cpl` and `119MSDCF` (22.7 %),
  against M113's clean-space **1.236** (23.6 %) on a different stack pair. A coefficient
  fitted on one scene is roughly a quarter wrong on another.
- The CPL argument is decisive and lies outside anything M114 measured: the software
  cannot identify the filter, so it cannot know whether the profile applies at all.

**In-sample it visibly helps; out-of-sample it cannot be trusted; off by default is
correct.** Keeping the gain reachable behind an explicit profile name is the right shape
for a correction that cannot verify its own applicability.

---

## 3. r24 -- the PIL 16-bit RGB narrowing audit

ORCH found that `PIL.Image.open()` silently returns `uint8` for a 16-bit RGB TIFF.
Reproduced independently on a file M114 constructed, rather than by re-running ORCH's
probe:

| case | tifffile | PIL | levels source -> PIL |
|---|---|---|---|
| 16-bit RGB | `uint16` | **`uint8`, mode RGB** | 21 380 -> **235** (91x loss) |
| 16-bit greyscale | `uint16` | `uint16`, mode `I;16` | 11 973 -> 11 973 (exact) |

**Exposure.** All **23** TIFFs read by M114 probes are genuinely `uint16`, and PIL would
have narrowed **every one**. No M114 metric used PIL: `r5_crops.py`, `r6_damage.py` and
`r16_crops3.py` call it write-only via `Image.fromarray(...).save(...)`; `r10a`'s single
`Image.open` reads a contact-sheet **PNG**, measured natively 8-bit, so that read is
lossless. `r1_null_ab.py:48` hashes **raw file bytes**, so the cross-binary null is immune.

**The one narrowing M114 inflicted on itself.** `r10a:33` and `:125` do
`(tifffile.imread(...) >> 8).astype(np.uint8)` -- 59 092 realised levels reduced to 256.
Re-run at full depth rather than argued:

| needle | tile | 8-bit | 16-bit | delta |
|---|---|---|---|---|
| `fringe-1400x0` | 150x150 | (1400, 0) | (1400, 0) | (0, 0) |
| `hairs-300x4200` | 170x170 | (300, 4200) | (300, 4200) | (0, 0) |
| `neutral-3920x3080` | 150x150 | (3920, 3080) | (3920, 3080) | (0, 0) |
| `specular-900x2620` | 130x130 | (900, 2620) | (900, 2620) | (0, 0) |
| `wing-900x60` | 150x150 | (900, 60) | (900, 60) | (0, 0) |

Negative control: haystack rolled +3 px in x, recovered +3 px. **The bar can go red.**
The recovered coordinates also match the filenames' encoded origins exactly -- external
ground truth that was not used to build the estimator.

---

## 4. r25 -- independent re-derivation of `camera_to_srgb`

`color.rs:191-208` computes `inv(rownorm(A@S))`: step 1 builds `cam_from_srgb`, **step 2
row-normalises**, **step 3 inverts**. The corpus had quoted `rownorm(inv(A@S))`. The two
do not commute.

```
CRATE  inv(rownorm(A@S))              CORPUS rownorm(inv(A@S))
 R  1.636062 -0.448619 -0.187443       R  1.197506 -0.125014 -0.072492
 G -0.115165  1.488971 -0.373806       G -0.453042  2.230018 -0.776976
 B -0.004740 -0.323601  1.328341       B -0.008259 -0.214665  1.222924
```

Channel leak, each off-diagonal term as a percentage of its own row's diagonal:

| leak | crate (correct) | corpus (wrong) |
|---|---:|---:|
| green -> red | **27.4206** | 10.4395 |
| blue -> red | 11.4570 | 6.0536 |
| red -> green | **7.7345** | 20.3156 |
| blue -> green | 25.1050 | 34.8417 |
| red -> blue | 0.3569 | 0.6754 |
| green -> blue | 24.3613 | 17.5534 |

| bar | result |
|---|---|
| **E1** the two orderings differ | PASS |
| **E2** crate ordering matches `color.rs:221`'s doc comment | PASS -- max abs diff 0.000194 |
| **E3** corpus ordering does **not** match it | PASS -- max abs diff 0.741018 |
| **E4** corpus ordering reproduces the quoted 10.44 / 20.32 | PASS |
| **E5** the `#[cfg(test)]` fixture equals the real capture | PASS -- max abs diff 2e-8 |

**E4 matters more than the discrepancy.** Reproducing 10.4395 and 20.3156 exactly
identifies *which operation* produced the wrong value, rather than merely showing the
corpus disagreed.

**E5 is what M114 adds.** `A7C2_XYZ_TO_CAM` at `color.rs:812` is inside `#[cfg(test)]`
(`mod tests` opens at line 799), so every leak figure in this argument rested on a **test
fixture**, and E2 alone only establishes consistency between two statements in the same
file. Reading `rgb_xyz_matrix` out of `bee-3-cpl\DSC00001.ARW` via rawpy gives max abs
difference **2e-8**: the fixture is the capture's real matrix.

**The leak is strongly asymmetric.** green -> red is 27.4206 % but red -> green is only
7.7345 %. For a red-minus-green displacement the forged zero-lag term therefore lands
almost entirely in output red, so M114's retracted red-side numbers were the more
corrupted of the two.

---

## 5. r26 / r26b -- quantisation dose-response, and why the dose axis is not the mechanism

M114's r24 clearance was **single-dose**: it showed the estimator had not broken at 8
bits, not where it breaks. Replaced with a 13-point sweep of the NCC localisation, ground
truth external, commissioned by a planted +3 px roll.

### 5.1 The 12-level threshold does not transfer

| needle | realised levels at nominal 256 | lowest realised level count still exact |
|---|---:|---:|
| `fringe` | 131 | 2 |
| `hairs` | 180 | 2 |
| `neutral` | 162 | 2 |
| `specular` | 93 | 2 |
| `wing` | 202 | 2 |

Three of five needles -- `hairs`, `neutral`, `wing` -- localise **exactly at 2 realised
levels**, a binary image, with no failure anywhere in the sweep.

This is **not** a claim that V-M113 is wrong on its own ground. M114's templates are
130x130 = **16 900** to 170x170 = **28 900** px. A 12-level floor is plausible for
small-window sub-pixel peak fitting, where levels are what define curvature; a large
binary silhouette is highly localisable at one bit. **The threshold is a property of the
estimator and the window area, not of "location statistics" as a class** -- which makes
the 12-level rule itself a form-based screen of exactly the kind ORCH has withdrawn.

### 5.2 The identical-dose divergence -- replicated within the experiment

**Two** needles give opposite outcomes at the **same realised level count**:

| needle | nominal | realised | error |
|---|---:|---:|---:|
| `specular` | 4 | 2 | **0.00 px** |
| `specular` | 3 | 2 | **165.34 px** |
| `fringe` | 3 | 2 | **0.00 px** |
| `fringe` | 2 | 2 | **159.00 px** |

Same needle, same estimator, same realised count, opposite result. **The level count
cannot be the controlling variable.**

### 5.3 Holding the level count fixed and sweeping only the boundary

19 thresholds across the luminance range, level count pinned at 2 -- the maximally
degraded case:

| needle | exact at realised == 2 | worst failure at realised == 2 |
|---|---:|---:|
| `specular` | **3 / 8** | **242.13 px** |
| `wing` | **14 / 18** | **2.24 px** |

At one bit, whether the estimator localises perfectly or misses by 242 px depends on
**where the single decision boundary falls relative to the content**. Level count does not
predict it. Content does not fully predict it either -- and note the two needles fail
*differently in kind*: `wing` degrades gracefully (worst 2.24 px) while `specular` fails
catastrophically (worst 242.13 px), so even the failure mode is content-dependent.

**This generalises ORCH's withdrawal one step.** It is not only the *form of the
statistic* that fails to predict exposure -- **a dose parameterised by level count fails
too.** The controlling quantity is the interaction between the quantiser's decision
boundaries and the signal's structure, and no summary of the quantiser alone captures it.

---

## 6. Retractions, each beside its own number

All M114 render-domain numbers from probes r10-r23 were measured on TIFFs rendered
`--srgb --auto-exposure`. That space carries a non-diagonal colour matrix (green -> red
**27.4206 %** at zero displacement, section 4) and a green-guided MHC demosaic whose
smoothness assumption a CA fringe violates (`demosaic.rs:482`). `main.rs:116` documents
`--srgb` as **"For looking at, NOT for measuring."**

| retracted claim | the number, as reported | why it dies |
|---|---|---|
| application-path over-delivery, hypothesis H3 | factor **1.130 - 1.286**, consolidated ~1.20 | it is the colour matrix; M113's transfer check reads 1.3073 in sRGB and 0.9399 / 0.9813 in binned linear |
| steer to M107 to hunt a quad-grid radius convention | -- | no anomaly remains for it to explain; **withdrawn** |
| fit-quality factors (r23) | **0.903 / 1.040 / 0.847** | contaminated space |
| gains derived from them | **1.161 / 1.279 / 0.957** | contaminated space |
| scene gains (r18, refused at the time; r20) | r18 **1.4208** / **1.4927**; r20 **1.241** / **1.052** | contaminated space |
| earlier gain estimates | r10e 1.117-1.344, r10d 1.284, r11 1.225-1.416, and the proposed ~0.78 scalar | contaminated space |
| **r18 tangential-arm blue floor** | **6 of 7 rings** (`bee-3-cpl`) and **4 of 7 rings** (`119MSDCF`) clear the floor | the sRGB matrix mixes blue into output green at **25.1050 %** and green into output blue at **24.3613 %**; the reading is not separable from the transform |
| `hp\|B-Y\|` exceeds `hp\|R-Y\|` after correction | -- | same reason |
| blue is "the WORST contaminated channel" | asserted on a **34.8 %** figure from the mis-ordered matrix | with the correct matrix the largest single leak is **green -> red at 27.4206 %**, which exceeds blue -> green at **25.1050 %**. Blue is heavily contaminated but not the worst. The retraction stands; the **superlative** did not |
| recovered translation (r23 Y3) | **0.375 / 0.250 / 0.450 px** | the azimuthal-pairing **method** is space-independent and sound; these numbers are not |

**Why M114's own controls did not catch it.** Bars W3 and X3 required the application
factor to be **scene-independent** and it passed at **3.4 %** and **7.2 %** spread, which
was read as evidence the factor belonged to the code. **A fixed colour matrix is also
scene-independent.** Constancy across scenes cannot distinguish a property of the system
under test from a property of one's own transform. Worse, `eps_r = -704.5 ppm` was present
in those scripts as `NOMINAL` and `applied/declared` was computed on every ring: the
calibration was in hand and was read as a finding.

**What survives**, because it is space-independent or externally grounded: the
byte-identical cross-binary null; the decile decomposition being a
regression-to-the-mean instrument; W3's keep-sign bar having negative power (noise
**93.0 %**, a strictly damaging wrong-sign correction **84.8 %**, the real correction
**75.1 %**); `support_r_max` being read only at `optics.rs:853` inside a test; the CFA
site mapping; gear matching from EXIF; the solve-cache-key call graph; and the tangential
placebo's ordering and sign, though its percentages are contaminated.

---

## 7. Candidate facts -- r24, the narrowing audit

1. **`PIL.Image.open()` narrowing independently reproduced by M114** on a self-constructed file: 16-bit RGB 21 380 -> 235 levels (91x), `dtype=uint8`, `mode=RGB`; 16-bit greyscale 11 973 -> 11 973, exact, `mode=I;16`.
2. **`Image.open(p).mode` cannot distinguish a narrowed 16-bit RGB TIFF from a genuine 8-bit RGB TIFF** -- both report `mode=RGB`, `dtype=uint8`. The mode test is one-directional and cannot establish true depth.
3. **All 23 TIFFs read by M114 probes are genuinely `uint16` and PIL would have narrowed every one.** No M114 metric used PIL.
4. **`r10a`'s self-inflicted 8-bit narrowing** (59 092 -> 256 levels) **changed no located position** -- 5/5 needles identical, against a live +3 px roll control.
5. **M114's cross-binary null is immune**: `r1_null_ab.py:48` hashes raw file bytes, never decoded pixels.
6. **The hazard fails toward the null on this project's live problem.** A -704.5 ppm lateral-CA displacement is about 0.07 px, entirely beneath the ~128-count 8-bit quantisation floor, so a PIL-read fringe metric would read about zero while byte-hash A/B bars continued to pass.

### Disciplines

7. **Assert the dtype you expect on the line after you load.** The cost is one line and the failure it catches is a plausible number rather than an exception.
8. **A depth diagnostic must read the file's true depth, not the reader's report of it.** A reader that narrows silently also reports the narrowed form confidently.
9. **Before trusting a small-signal null, state the measurement's quantisation floor in the same units as the effect.** A null is informative only if the instrument could have resolved the effect.
10. **When triage lists a script as exposed, check which file the risky call actually opens.** Grep-level exposure lists over-report and must be resolved per call site.

---

## 8. Candidate facts -- r25, the matrix

1. **ORCH's `camera_to_srgb` correction is confirmed by independent re-derivation.** `color.rs:191-208` normalises then inverts; the true matrix is R `[1.636062, -0.448619, -0.187443]`, G `[-0.115165, 1.488971, -0.373806]`, B `[-0.004740, -0.323601, 1.328341]`.
2. **The corpus ordering `rownorm(inv(A@S))` reproduces the erroneous 10.4395 % / 20.3156 % exactly**, identifying the mechanism of the error rather than merely its existence.
3. **`A7C2_XYZ_TO_CAM` (`color.rs:812`) is a `#[cfg(test)]` fixture** but is **bit-identical to `rgb_xyz_matrix` in the real capture** `bee-3-cpl\DSC00001.ARW` (max abs diff 2e-8, via rawpy). The leak figures are grounded in the capture, not in a test constant.
4. **The sRGB channel leak is strongly asymmetric**: green -> red 27.4206 %, red -> green 7.7345 %, blue -> green 25.1050 %, green -> blue 24.3613 %, blue -> red 11.4570 %, red -> blue 0.3569 %.
5. **M114's own claim that blue was "the worst contaminated channel" is corrected** -- green -> red (27.4206 %) exceeds blue -> green (25.1050 %). The blue retraction stands; the superlative did not.
6. **No M114 probe performed matrix arithmetic**; the corpus matrix reached M114 only as prose, corrected in commit `7880a21`.

### Disciplines

7. **When correcting a wrong constant, show that the wrong procedure reproduces the wrong value.** Exact reproduction converts "the corpus disagreed" into "the corpus applied this operation".
8. **A cross-check between two statements in the same file establishes internal consistency, not truth.** Ground a constant against an artefact outside the source that quotes it.
9. **Check whether a constant you are reasoning from lives inside `#[cfg(test)]`.** A fixture may be faithful, but that is a claim to verify rather than assume.
10. **A superlative is a separate claim from the measurement under it and needs its own check.** Ranking claims break under corrections that leave the underlying finding intact.

---

## 9. Candidate facts -- r26 / r26b, the dose-response

1. **V-M113's 12-realised-level immunity threshold does not transfer to large-template NCC localisation.** 3 of 5 needles localise exactly at **2** realised levels; templates were 16 900 to 28 900 px.
2. **Realised level count does not determine quantisation failure, and this replicates within the experiment.** `specular` at nominal 4 and nominal 3 both realise 2 levels and give **0.00 px** and **165.34 px**; `fringe` at nominal 3 and nominal 2 both realise 2 levels and give **0.00 px** and **159.00 px**.
3. **At a fixed level count of 2, outcome varies with threshold placement alone**: `specular` **3 of 8** exact with worst failure **242.13 px**, `wing` **14 of 18** exact with worst failure **2.24 px**. The failure *mode* is also content-dependent -- graceful for `wing`, catastrophic for `specular`.
4. **`r10a`'s operating point is far above any break**: nominal 256 gives **93 to 202** realised levels per window, against a break at **2 to 3**.
5. **No M114 metric ever ran on narrowed data** -- all 23 TIFFs read `uint16` via `tifffile` -- and **no M114 clearance used a split-half or frame-difference noise estimate.**
6. **`STREHL_ALIGN` appears in no M114 script**; all M114 renders used a frozen `STREHL_WARPMAP` sidecar with alignment on, so no M114 result sits behind the inert-gate hazard.

### Disciplines

7. **A single-dose clearance is not a clearance.** It shows the estimator had not broken at one point; it cannot show where it breaks, so it cannot tell you your margin. Sweep until it fails, then report the margin in the units the failure is in.
8. **Do not replace a withdrawn form-based rule with another form-based rule.** A scalar threshold applied across estimators by class is the same error at a different granularity.
9. **When a dose-response has a controlling variable, check that the variable controls it.** Identical doses giving opposite outcomes means the dose axis is not the mechanism.
10. **Report the realised value of a parameter inside the window you actually fit, not its nominal value.** Nominal 256 gave 93 to 202 realised; nominal 4 and nominal 3 both gave 2.
11. **When linting a file another agent is folding into, hash it and record its mtime.** A violation that fires and then cannot be reproduced is more likely a moving tree than a broken linter, and the two demand opposite responses.
