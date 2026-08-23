# M5 — the diffraction cutoff, measured from the raw CFA

**Status: MEASURED at f/11. BOUNDED at f/8. CONSISTENCY CHECK ONLY at f/5.6.**
Measured on the owner's own three focus-bracket stacks, on single-colour sublattices of the raw
Bayer array, with a synthetic positive control, a real-texture positive control, a dark-frame null
control, a fixed-seed placebo and a two-directional falsification test. Nothing here is
demosaiced. Nothing under `C:\dev\macro` or `D:\macro-dark-frames` was written to.

Every claim below carries a label: **MEASURED**, **VERIFIED**, **DERIVED**, **ARGUED** or
**UNVERIFIED**. An unlabelled number in this project is a defect (SYNTHESIS §5).

Code: `experiments/m5-diffraction/`. Every number here comes from a command quoted in §12.

---

## 0. The verdict in one paragraph

**The diffraction-limited hypothesis survives, and the bellows factor is ~3, not ~5.** At f/11
the radially-averaged power spectrum of the green quincunx lattice has a genuine knee at
**f_sig = 0.2762 sensor cyc/px** (MEASURED, n=1 stack), above which the floor matches the
project's photon-transfer noise model to **0.950x** — i.e. it really is noise, not a fitted
plateau. That gives **B = (1 + m/p) ≤ 3.064** (DERIVED), against a `B=3` prediction of 0.2821;
the measurement lands at **0.979x the p=1 prediction**. `B=5` (p=0.5) is **REFUTED 5/5** by a
model-free test at both f/11 and f/8 — there is optical signal at frequencies where p=0.5 says
there can be none. `B=1` — the hypothesis that the camera's EXIF `FNumber` is already
bellows-corrected — is refuted by an enormous margin, so **H3 is answered: EXIF `FNumber` is the
marked f-number and every advisor formula that reads it must apply the bellows correction
itself**. Independently, the high-frequency floor gives a structure-free noise estimate that
agrees with the photon-transfer model to **0.950-1.093x** across 15 f/11 cases (**H4 answered:
the noise model is confirmed by a method that shares none of its assumptions**). **Two things
failed and are reported as failures, not smoothed over:** C3 (monotonicity of f_c in N) is **not
testable** on this data, because at f/8 and f/5.6 the subject spectrum never reaches the noise
floor inside the measurable band, so those knees are texture-limited rather than optics-limited;
and the null control fired a raw detection on **34.2% of 330 dark-frame cases**, caught only by
the dynamic-range gate — the estimator is *not* safe without that gate.

---

## 1. The headline numbers

| Stack | Marked N | ISO | n frames | What the data supports | Bound on B = (1+m/p) |
| --- | --- | --- | --- | --- | --- |
| `109MSDCF` | **f/11** | 160 | 22 | **A real knee.** GQ / centre, dyn 1297, floor **0.950x** the noise model | **B ≤ 3.064** (MEASURED→DERIVED) |
| `coffee-bean` | **f/8** | 50 | 105 | **No reachable floor.** Spectrum still falling at the top of the band; floor **4.58-20.19x** the noise model | **B < 3.317** (DERIVED, knee-free) |
| `119MSDCF` | **f/5.6** | 50 | 33 | Same, weaker: floor **1.70-2.52x** the model | **B < 4.739** (DERIVED, weak) |

Reverse direction, f/11 only: the floor at the top of the GQ band (0.3508 cyc/px) matches the
noise model, so there is no detectable signal there, so **f_c ≲ 0.3508 ⇒ B ≳ 2.412** (ARGUED —
see §4.5 for why this direction is weaker than it looks).

**Combined bracket (DERIVED): B ∈ [2.41, 3.06] at λ = 550 nm.**
Bias-corrected point estimate (DERIVED, applying the crossing rule's measured low bias from §2):
**B ≈ 2.6-2.9**. Correcting for the wavelength assumption (§10) at λ = 500 nm moves that to
**2.9-3.2**.

**`B = 3` (m = 2, p = 1) is supported. `B = 5` (p = 0.5) is refuted (MEASURED, model-free).
`B = 2` is excluded by the lower bound (ARGUED — §4.5). `B = 1` is refuted by a factor of ~3
(DERIVED).**

If m = 2.0 as the brief states (DERIVED, not measured), then m/p ∈ [1.4, 2.1] and **p ≈ 1.0-1.4**
— a near-unity pupil magnification, which is what a symmetric-ish design plus a teleconverter
should give.

---

## 2. Why you should believe the estimator: the positive controls

Nothing downstream of this section is worth anything if the estimator cannot recover a cutoff
that was planted by hand. That test was run **first, before any real data was touched**.

### 2.1 The method in one paragraph

Subtract black level 512; crop to the 7032x4688 active area only (the 7168x5120 buffer is
zero-padded and would contaminate any FFT that touched it); extract a single-colour sublattice
straight from the Bayer array; take 512x512-sample ROIs; Welch-average Hann-windowed 128x128
periodograms; radially average; find the highest frequency whose power stands above a fitted
constant high-frequency floor by more than `z=3` standard errors for a run of `RUN_LEN=3`
consecutive bins. All thresholds are **fixed in the source and identical for the synthetic
control, the dark frames and all three stacks** (VERIFIED by reading `m5_lib.py`: `Z_DETECT=3.0`,
`RUN_LEN=3`, `DYN_GATE=10.0`, `F_LO_ABS=0.025`, `DYN_BAND=(0.025,0.050)`, fixed `ROI_FRACTIONS`).
Nothing is tuned per stack. The Welch periodogram's absolute normalisation is asserted against a
known white-noise variance on all three lattices and all three windows to within ±0.7%
(MEASURED, `m5_selftest.py`), so the floor level is a calibrated noise power, not an arbitrary
scale.

### 2.2 Three lattices, and the factor of 2 that would have faked the answer

| Lattice | Definition | Pitch | Isotropic reach (sensor cyc/px) |
| --- | --- | --- | --- |
| `G1` | `raw[0::2, 1::2]` | 10.24 µm | 0.2500 |
| `G2` | `raw[1::2, 0::2]` | 10.24 µm | 0.2500 |
| `GQ` | both greens on their quincunx lattice, re-indexed `B[u,v] = A[u+v, u-v+1]` | 7.2408 µm | 0.3536 |

**MEASURED (self-test).** Getting the sublattice-to-sensor frequency conversion wrong by 2x
would produce *exactly* the p=0.5 answer, so it is proved rather than asserted: `m5_selftest.py`
plants a sinusoid at a known *sensor* frequency and asserts all three lattices place it in the
same radial bin. All 10 test groups pass.

**`GQ` is an extension beyond the method the brief prescribed, and it is load-bearing.** All
three of the brief's p=1 predictions (0.554, 0.388, 0.282) lie **above** the 0.25 reach of a
single green sublattice. G1 and G2 alone could therefore never have returned anything but bounds
— the prescribed method cannot see the answer it was asked to find. GQ uses exactly the same
photosites, interpolates nothing, and reaches 0.3536.

### 2.3 C1 — synthetic positive control (MEASURED)

1/f² scene rendered on a 5120² fine grid, convolved with a **known** diffraction MTF, sampled onto
the CFA, Gaussian noise at a **known** sigma, then run through the unmodified estimator.
9 planted cutoffs x 3 lattices x 3 noise levels.

| Lattice | in-band cases | crossing-rule bias | model-fit bias |
| --- | --- | --- | --- |
| G1 | 15, 0 missed | **−8.5%** [−20.4, −0.4] | −0.2% [−1.5, +0.5] |
| G2 | 15, 0 missed | **−7.9%** [−18.0, −0.4] | −0.1% [−1.2, +0.7] |
| GQ | 24, 0 missed | **−7.4%** [−19.7, +2.2] | +0.2% [−0.5, +1.3] |

**It recovers what was planted.** The model fit is essentially unbiased in band. The crossing rule
runs **low**, and its bias is a strong function of spectral dynamic range (MEASURED):

| dyn | n | crossing bias |
| --- | --- | --- |
| 0-100 | 2 | −10.2% |
| 100-400 | 13 | −14.5% [−20.4, −8.8] |
| 400-1200 | 7 | −10.9% [−19.7, −2.3] |
| >1200 | 32 | **−4.3%** [−10.3, +2.2] |

**DERIVED, and it is the single most important interpretive fact in this document: because the
crossing rule is biased low, every `f_sig` is a *lower* bound on f_c, and every `B_max` is an
*upper* bound on B.** The mechanism is physical, not statistical: near cutoff the diffraction
MTF² behaves as ≈1.44(1−s)³, so the last ~10% of the band is ~28 dB down and is always buried in
the floor. **Defocus cannot bias this the other way** — defocus does not move the OTF support, it
only depresses the MTF inside it (ARGUED, standard Fourier optics), so a defocused mixture inside
an ROI pushes the detected knee *down*, never up.

**The out-of-band guard works, and an earlier one did not.** The first guard tried was "the fitted
floor slope turns positive when aliased signal folds in" — it fired **0 times out of 36** and was
**refuted and removed**; the slope goes strongly *negative*, not positive. Its replacement is the
model fit's own `above_reach` flag: **fired 36/36 when the planted cutoff was above the lattice
reach, 0 false alarms in 54 in-band cases** (MEASURED). The refuted guard is documented in
`m5_lib.floor_flatness`'s docstring so nobody re-invents it.

**Misspecification probe (MEASURED).** Given a Gaussian PSF, which has *no* hard cutoff at all,
the estimator returns something near the Airy 10% point it was matched to and its fit residual
rises ~3x (0.08-0.10 vs 0.031-0.035). It does not confidently invent a hard cutoff.

### 2.4 C1b — the same test on real texture (MEASURED, and it is much harsher)

A real crop already carries the rig's real MTF, so planting a second cutoff into it produces a
*doubly*-blurred image. This is a deliberately pessimistic control.

On `109MSDCF/DSC00018.ARW`, 3 ROIs x 3 planted cutoffs x 2 lattices, n=18:

```
   crossing  bias  -29.1%  [-40.3, -14.1]  n=18
   model fit bias  +15.2%  [-12.8, +112.2]  n=16
```

At the **high**-dynamic-range ROI (base dyn 322-511, the regime the f/11 result lives in) the
crossing bias is **−14.1% to −27.3%**, and the model fit is usable (−2.3% to −12.8%). At low dyn
the model fit **runs away**: +32.1%, +62.2%, +112.2%.

Repeated on a second, much flatter frame (`DSC00009.ARW`, base dyn 1.8-74.7) the crossing bias
is **−44.4%** [−52.6, −33.6] (MEASURED, n=18).

**Two conclusions, both acted on.** (a) The model fit is **not trusted on real data** and its
cutoff is never quoted here; only its `above_reach` flag is used. (b) The crossing rule's low
bias on real texture is between −14% and −44% depending on dynamic range, so the "upper bound on
B" reading is *conservative* and the true B is somewhere below `B_max`.

### 2.5 Trap 2 — windowing was load-bearing (MEASURED)

Same synthetic scene, three windows. A boxcar's sinc sidelobes decay as 1/f and can fake exactly
the plateau being hunted:

| f_c true | lattice | hann | none (boxcar) | kaiser8 |
| --- | --- | --- | --- | --- |
| 0.130 | GQ | 0.1215, floor sd 20.0 | **0.1740, floor sd 35.0** | 0.1215, floor sd 20.0 |
| 0.169 | GQ | 0.1602, sd 20.0 | **0.1740, sd 35.0** | 0.1602, sd 20.0 |
| 0.233 | GQ | 0.2154, sd 20.0 | 0.2016, sd 33.5 | 0.2154, sd 20.0 |
| 0.282 | GQ | 0.2569, sd 20.0 | 0.2375, sd 32.5 | 0.2569, sd 20.0 |

**The boxcar inflates the recovered noise floor by 1.6-1.8x and reports a nearly
cutoff-independent knee at 0.174 for two different true cutoffs** — the leakage plateau, exactly
as the trap predicted. Hann and Kaiser-8 agree with each other to within one radial bin
everywhere. **Windowing mattered; all results here use Hann.**

### 2.6 Two things about the estimator itself that were wrong and were fixed

Recorded because both would have produced confidently wrong answers, and because the second one
moved the result.

- **The floor-slope out-of-band guard was refuted.** See §2.3: 0/36. Documented in
  `m5_lib.floor_flatness`'s docstring so it is not re-invented.
- **The detection threshold originally assumed a per-bin variance that had never been measured.**
  Replacing it with a self-calibrating `kappa` — the *measured* MAD-based scatter of the floor for
  the actual tiling geometry — showed the assumed value was **2.4x too conservative at tile=256
  and 10x too conservative at tile=128** (MEASURED: `kappa` = 0.402 and 0.095 against observed
  scatter 0.431 and 0.116). A second failure mode then appeared: on a lucky ROI the data-driven
  `kappa` can fall *below* its pure-noise value (0.020 was observed), making detection too
  aggressive. It is therefore floored at `reference_kappa()`, a cached Monte-Carlo of the same
  tiling geometry on white noise, so scene structure can only ever make the test **more**
  conservative. **Measured false-alarm rate after the fix: 3 of 240 white-noise cases (1.25%),
  against a nominal z=3 / run-of-3 design** (MEASURED, `m5_selftest.py`).

---

## 3. The null control, and the 34% it exposed

### 3.1 C2 — dark frames (MEASURED, and it is a partial failure)

The identical estimator, identical geometry, run on `D:\macro-dark-frames`, all 11 folders,
first 2 frames of each discarded as stabilisation shots (following M4). 11 folders x 5 ROIs x
3 lattices x 2 policies = **330 cases**.

```
C2 VERDICT
   cases                                    330
   raw detections (any f_sig at all)        113 (34.2%)
   detections that also passed the dynamic-   0 (0.0%)
   range gate, i.e. a claimed cutoff
```

**Read this as a failure of the raw rule and a success only of the gated rule.** On pure noise
the crossing rule found a "cutoff" in **one third of all cases**, at values like 0.2817, 0.2983,
0.2596, 0.2431 — *the same range as the real measurement*. If this document quoted `f_sig` without
the dynamic-range gate, it would be quoting an artifact.

**Root cause, MEASURED:** dark frames are **not spectrally white**. They carry M4's row/column
fixed-pattern noise, which puts structure at low frequency, depresses the fitted floor and lets
isolated bins clear the threshold. The gate that saves it is `dyn ≥ 10` (ratio of low-band to
floor power): every dark case has dyn ≈ 1.0-1.7, and every one is rejected. **The claimed f/11
result has dyn = 1297, i.e. ~1000x above the gate** (MEASURED).

The 0/330 gated false-alarm rate is the number that licenses the primary result. The 113/330 raw
rate is reported because hiding it would misrepresent how much of the estimator's safety comes
from one threshold.

### 3.2 C2b — subtracting the dark spectrum changes nothing (MEASURED)

Since darks are contaminated, the obvious worry is that the *light* frames' knee is FPN too. So a
matched-ISO dark reference spectrum was measured on the identical geometry (8 averaged frames from
`123MSDCF`, ISO 200 — the nearest available *above* ISO 160, deliberately the conservative
direction) and subtracted, and `f_sig` recomputed.

**Result: `f_sig` changed by exactly +0.00% in all 15 f/11 cases. `B_max` unchanged to 3 decimals.**

The band-excess table shows why. At f/11 centre / GQ, the light frame's median power sits
**9.06x, 1.64x, 0.22x and 0.003x** above its floor in the bands 0.10-0.15, 0.15-0.20, 0.20-0.25
and 0.25-0.35; the matched dark's excesses in the same bands are **0.41x, 0.26x, 0.13x, 0.010x**.
Real subject signal dominates dark structure by more than an order of magnitude wherever the knee
is detected.

### 3.3 The placebo — is the estimator selecting noise? (MEASURED)

Trap 4 says to use the sharpest frame at the ROI. This is a per-tile argmax, and SYNTHESIS fact 7
plus M2 both warn that an argmax over a noise-sensitive measure selects the *noisiest* sample.
So the identical pipeline was re-run with tiles chosen by a **fixed-seed lottery** instead of by
focus.

At f/11, best-tile vs placebo floor sd:

| ROI / lattice | best f_sig | placebo f_sig | best floor sd | placebo floor sd |
| --- | --- | --- | --- | --- |
| centre / G1 | 0.2109 | 0.1953 | **13.66** | **13.44** |
| centre / G2 | 0.1992 | 0.1758 | **13.90** | **13.41** |
| centre / GQ | **0.2762** | 0.2154 | **11.91** | **12.00** |

**Selection raises the signal (dyn 1297 vs 894) and does not raise the floor (11.91 vs 12.00).**
It is choosing focus, not noise. This is the opposite of the M2 argmax defect and it is the
control that licenses per-tile frame selection here.

At f/8 the same placebo gives 220 vs 18 DN floor sd — a 5-13x inflation. **The placebo correctly
detected that at f/8 there is no noise floor to select against.** A control that only ever passes
is not a control; this one fails where it should.

---

## 4. The primary result

### 4.1 f/11 — the one aperture that yields a real measurement

`C:\dev\macro\test\109MSDCF`, 22 frames, ISO 160, 1.3 s, marked f/11, `FocusPosition2` 57-58
(VERIFIED by exiftool: `LensModel = "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"`,
`FocalLength = 200`, `FNumber = 11`, uniform over all 22).

Predicted cutoffs at λ = 550 nm, pitch 5.12 µm:

| Candidate | N_eff | f_c predicted |
| --- | --- | --- |
| B=2 (bare lens, p=1) | 22.0 | 0.4231 |
| **B=3 (m=2, p=1)** | **33.0** | **0.2821** |
| B=5 (m=2, p=0.5) | 55.0 | 0.1693 |

Tightest valid case (MEASURED):

```
   centre / GQ / tile   dyn 1297   kappa 0.056   floor 0.950x model
   f_sig  = 0.2762 sensor cyc/px = 53.9 cyc/mm     nfrm 4
   B_max  = 3.064
```

**f_sig / f_c(B=3) = 0.2762 / 0.2821 = 0.979.** The measured knee lands within 2.1% of the p=1
prediction, on the low side, which is the side the C1 bias says it must land on.

**13 of the 15 f/11 tile cases have a floor consistent with the photon-transfer model (<1.15x),
pass the dyn gate and detect a knee.** The 2 exclusions are the `lower-right` G1/G2 cases, whose
dyn is 6.8 and 7.2 — **rejected by the dynamic-range gate, not by the floor test** (VERIFIED by
reading the gate in `m5_measure.py`).

**Bias-corrected point estimates (DERIVED):** applying C1's high-dyn crossing bias of −4.3% gives
f_c = 0.2886 → **B = 2.93**; applying C1b's harsher high-dyn real-texture bias of −14.1% gives
f_c = 0.3215 → **B = 2.63**.

### 4.2 f/8 — a bound, and no knee at all

`C:\dev\macro\test\coffee-bean`, 105 frames, ISO 50, marked f/8.

```
cases with a floor consistent with the photon-transfer model (<1.15x): 0 of 15
cases with an inflated floor: 15, ratio 4.58-20.19x
NO VALID BOUND from a detected knee at this aperture.
```

Every f/8 case reports `kappa` clipped at its 50.0 ceiling — the estimator's own signal that the
"floor" is not flat. The subject (a coffee bean at 2:1) is so rich in high-frequency texture that
its spectrum is **still falling** at the top of the GQ band. There is no plateau, so there is no
knee, so `f_sig = 0.2817` at f/8 is **not a cutoff** — it is the estimator pinning at 0.8x reach,
which is where the initial floor band starts. **Do not quote it** (§11).

But the *absence* of a floor is itself a measurement, and it is knee-free:

**MEASURED:** power at 0.3508 cyc/px exceeds the photon-transfer noise model on 15 of 15 cases,
by 4.58-20.19x in sd (21-408x in power). **PRNU cannot account for this (ARGUED, with the
arithmetic):** the worst case is mean 2048 DN with a modelled sd of 15.3 DN and a measured
high-frequency sd of 292 DN. A multiplicative fixed-pattern term would have to be
√(292² − 15.3²) / 2048 = **14.2% PRNU** to explain it. Sensor PRNU is of order 0.3-1%. Therefore
there is optical signal at 0.3508 ⇒ **f_c > 0.3508 ⇒ B < 3.317** (DERIVED). This uses no knee
detection whatsoever.

**This is the second independent estimate, and it agrees with f/11's B ≤ 3.064 to within 8%.**

### 4.3 f/5.6 — a consistency check, exactly as the brief predicted

`C:\dev\macro\test\119MSDCF`, 33 frames, ISO 50, marked f/5.6. The B=3 prediction is
f_c = 0.5541, **above the sensor's own Nyquist of 0.5** and far above any lattice's reach. This
stack was never capable of producing a third equal-weight number and is **not reported as one**.

```
cases with a floor consistent with the photon-transfer model (<1.15x): 0 of 15
cases with an inflated floor: 15, ratio 1.70-2.52x
Out-of-band bound: f_c > 0.3508  =>  B < 4.739
```

**Weaker than it looks, and here is the arithmetic that shows why (ARGUED).** Run the same PRNU
test as §4.2 on the f/5.6 excess: at `lower-right` / G2 / roi the mean is 4541 DN, the modelled sd
22.8 DN and the measured high-frequency sd 38.4 DN, so a multiplicative fixed-pattern term of
√(38.4² − 22.8²) / 4541 = **0.68%** would fully explain the excess. **That is squarely inside the
plausible PRNU range** (0.3-1%), and PRNU has never been measured for this sensor — M4 explicitly
could not see it, because dark frames cannot. C2b's dark reference contains FPN but by
construction contains no PRNU. So **B < 4.739 is by far the weakest of the three bounds**; it is
quoted only as a consistency check. It is consistent, and it does not on its own refute B=5.

### 4.4 The three estimates and their agreement — which IS the validation

| Stack | Estimate | Kind | Depends on knee detection? |
| --- | --- | --- | --- |
| f/11 | **B ≤ 3.064** | knee + clean floor | yes |
| f/8 | **B < 3.317** | out-of-band excess | **no** |
| f/5.6 | **B < 4.739** | out-of-band excess | **no** |

**They agree (MEASURED/DERIVED).** All three are upper bounds and all three are mutually
consistent. The two informative ones — obtained by **two different mechanisms**, one relying on
finding a knee and one relying on there being no floor — bracket B at 3.06 and 3.32, an 8%
spread. The f/5.6 bound is consistent but carries no discriminating power.

**This is the model validation the brief asked for, and the model passes**: a single value of B
near 3 explains a knee at 0.2762 when N=11, an absence of any floor when N=8, and an absence of
any floor when N=5.6, with no per-stack parameter.

### 4.5 The falsification table (MEASURED)

Two one-sided tests, both from measured quantities only:
**(a)** signal detected *above* a candidate's predicted f_c refutes that candidate outright —
there is no optical signal above the cutoff. **(b)** if a candidate predicts f_c *above* the
lattice reach, the top of the band must still carry signal; a floor matching the photon-transfer
model to better than 1.15x refutes it instead.

f/11:

| Candidate | f_c pred | G1 | G2 | GQ |
| --- | --- | --- | --- | --- |
| B=2 | 0.4231 | REFUTED(b) 5/5 | REFUTED(b) 5/5 | REFUTED(b) 5/5 |
| **B=3** | **0.2821** | REFUTED(b) 5/5 | REFUTED(b) 5/5 | **survives** |
| B=5 | 0.1693 | REFUTED(a) 2/4 | REFUTED(a) 2/4 | **REFUTED(a) 5/5** |

f/8: **B=5 (f_c 0.2327) REFUTED(a) 5/5 on GQ.** B=2 and B=3 are unreachable at f/8.

**Test (a) is the strong one and it is model-free.** B=5 predicts f_c = 0.1693 at f/11 and 0.2327
at f/8; signal is detected at 0.2762 and 0.2817 respectively, on 5 of 5 ROIs each time.
**B=5 is dead.**

**Test (b) is weaker than the table makes it look, and this must be said.** It does not model the
MTF roll-off. B=3 predicts f_c = 0.2821 against a G1/G2 reach of 0.25, where s = 0.886 and the
diffraction MTF² is ≈0.002 — 27 dB down. A signal that far down would not lift the floor sd by
the 15% the test demands, so **test (b) "refutes" B=3 on G1/G2 for a reason that has nothing to
do with B**. That apparent internal contradiction with GQ is an artifact of test (b), not
evidence. Test (b) is only meaningful when the predicted f_c is comfortably above the reach: at
B=2, s = 0.591 and MTF² ≈ 0.086 (11 dB down), which *is* detectable, so **the refutation of B=2
is real but should be labelled ARGUED, not MEASURED**. The same caveat applies to the
B ≳ 2.412 lower bound in §1.

**B=1 is refuted with no such caveat (DERIVED).** If EXIF `FNumber` already included the bellows
factor, f_c at f/11 would be 0.846 cyc/px; at 0.30 cyc/px that gives s = 0.355 and MTF² = 0.31 —
5 dB down, so the spectrum at the top of the band would tower over the floor. It does not; it
*matches the noise model to 0.950x*. There is a factor-of-3 margin here, not a marginal call.

---

## 5. C3 — monotonicity is NOT testable on this data

The brief requires f_c to decrease monotonically with marked N, and says to report loudly if it
does not. **It does not, and the reason is that the test is inapplicable, not that the physics
fails.** Reporting this as a passed or failed monotonicity test either way would be dishonest.

Best `f_sig` per stack (MEASURED): f/5.6 → **0.2431**, f/8 → **0.2817**, f/11 → **0.2762**.
That is not monotone. But:

- At f/11 the knee is **optics-limited**: the floor matches the noise model at 0.950x, kappa is
  0.056, and the spectrum genuinely flattens.
- At f/8 and f/5.6 the knee is **texture-and-floor-limited**: 0 of 15 cases have a clean floor,
  every `kappa` clips at 50.0, and `f_sig` pins at 0.2817 = 0.8x reach, which is a structural
  artifact of where the initial floor band begins.

**Comparing an optics-limited number with two artifacts is not a monotonicity test.** The
monotonicity that *is* testable is the one in §4.4: as N falls from 11 to 8 to 5.6, the frequency
at which the spectrum reaches the noise floor moves from *inside* the band to *outside* it, and
stays outside. That is the predicted direction, and it is what is observed. **C3 in its literal
form: NOT TESTED. C3 in the form the data can support: PASSED (ARGUED).**

To test C3 properly one needs a subject whose spectrum falls to the noise floor **inside** the
measurable band at *every* aperture. Concretely (ARGUED, a capture request rather than a result):
a low-contrast, fine-but-not-unlimited-texture target — matte paper, fabric or a printed noise
chart — filling the frame at the same 2:1 working distance, shot at f/5.6, f/8 and f/11 with
exposure set to put the subject at 2000-4000 DN, tripod, IBIS **off**, 5-10 frames per aperture at
identical focus. The coffee bean fails at f/8 not because of the optics but because it is too
rich in high-frequency detail: its spectrum outruns the noise floor to the top of the band.

---

## 6. C4 (ROI independence) and C5 (sublattice replicate)

### 6.1 C4 — five ROIs, one centre and four off-axis at 30%/70% of the frame (MEASURED)

f/11, tile policy:

| Lattice | n | f_sig median | min | max | cv | B_max median [range] |
| --- | --- | --- | --- | --- | --- | --- |
| G1 | 5 | 0.1367 | 0.1172 | 0.2109 | 24.8% | 6.190 [4.012, 7.222] |
| G2 | 5 | 0.1875 | 0.1250 | 0.1992 | 15.8% | 4.513 [4.248, 6.770] |
| **GQ** | 5 | 0.2099 | 0.2044 | **0.2762** | **11.8%** | 4.031 [**3.064**, 4.140] |

f/8 GQ: cv **1.0%** (but every case is an artifact, §4.2). f/5.6 GQ: cv **23.9%**.

**The spread is dominated by texture availability, not by field position (ARGUED).** The
`upper-left` ROI has dyn 30.7 and the `lower-right` ROI has dyn 10.7, versus 1297 at centre —
a 40-120x difference in how much subject signal there is to find a knee in. C1's bias table says
the crossing rule loses 10-15% at those dynamic ranges before any optics enter. Since every
`f_sig` is a lower bound, low-dyn ROIs simply produce looser bounds; they do not contradict the
centre. **There is no evidence of a systematic radial trend**, which is what field-invariant
diffraction predicts — but with n=5 ROIs on n=1 subject this is a weak statement and is labelled
ARGUED.

**Consequence, and it is a real limitation: only the highest-dyn ROI produces a usable bound.
The measurement is effectively n=1 ROI.**

### 6.2 C5 — the two green sublattices (MEASURED)

G1 and G2 are disjoint sets of photosites sampling the same optics, so they are a genuine
replicate.

| ROI (f/11, tile) | G1 | G2 | difference | floor sd G1 / G2 |
| --- | --- | --- | --- | --- |
| centre (dyn 782/754) | 0.2109 | 0.1992 | **−5.6%** | 13.66 / 13.90 |
| upper-left (dyn 32/31) | 0.1289 | 0.1250 | −3.0% | 27.31 / 27.67 |
| upper-right (dyn 329/322) | 0.2031 | 0.1875 | −7.7% | 22.14 / 22.35 |
| lower-left (dyn 160/166) | 0.1367 | 0.1641 | +20.0% | 22.11 / 21.60 |
| lower-right (dyn 6.8/7.2) | 0.1172 | 0.1953 | **+66.7%** | 29.47 / 28.43 |

**They agree to 3-8% where there is signal and diverge to 20-67% where there is not.** The
divergence tracks dyn almost perfectly and the floor sds agree to ~2% everywhere. This is the
expected behaviour of a detector running out of SNR, and it is a further reason to trust only the
high-dyn cases. **Their mean levels agree to ≤0.20% at every ROI** (MEASURED — the mean-DN column
of the §8 table: 516.7/517.6, 1771.0/1767.7, 1136.3/1134.0, 1206.0/1204.5, 2027.4/2026.3), so the
GQ combination of the two is not introducing a cross-lattice step.

---

## 7. H3 — does the camera's reported FNumber include the bellows factor?

**Answered: NO (DERIVED, with a factor-of-3 margin).**

EXIF reports `FNumber = 11`, `FocalLength = 200 mm`, `LensSpec = "FE 200mm F5.6 Macro OSS"` —
i.e. the body composes the teleconverter into the reported focal length and marked aperture, but
**does not** apply the bellows correction for working at 2:1. The measurement recovers
**B ≈ 2.4-3.1, not ≈1.0**.

**This is directly actionable and it invalidates any naive reading of EXIF.** Every advisor
formula in this project that reads `FNumber` from EXIF and treats it as N_eff is wrong by a factor
of ~3 at this magnification — which means it under-predicts diffraction blur by ~3x and will
happily recommend f/11 as "safe". At 2:1 the marked f/11 is optically **f/33**.

The correction to apply (DERIVED from this measurement plus the brief's m):

```
N_eff = FNumber_exif * (1 + m/p)     with (1 + m/p) ~= 3 at m ~= 2, p ~= 1
```

**UNVERIFIED:** whether p ≈ 1 holds across the lens's focus range, and whether the same B applies
at lower magnifications. This measurement is at one focus distance only
(`FocusDistance2 = 0.2738-0.2771 m`, VERIFIED by exiftool). At infinity B → 1 trivially; the
interpolation between is not measured.

---

## 8. H4 — the high-frequency floor as an independent noise measurement

Above f_c there is only noise, so the floor is a **structure-free** sigma estimate — exactly what
M2 had to work for with an Immerkaer high-pass.

**First, the estimator itself was validated on data where sigma was known (C1, MEASURED):**

| planted sigma | recovered | error | sd | n |
| --- | --- | --- | --- | --- |
| 5.0 DN | 5.02 | +0.4% | 0.02 | 18 |
| 20.0 DN | 20.05 | +0.3% | 0.05 | 18 |
| 60.0 DN | 60.23 | +0.4% | 0.15 | 18 |

and, critically: **out-of-band cases inflate the recovered sigma by 3.81x (range 1.03-18.69x)** —
aliased signal is not noise. That is the same failure mode that shows up at f/8 (4.6-20x), which
independently corroborates the "no reachable floor" diagnosis.

**Then, on the real f/11 stack where the floor is genuinely a floor (MEASURED, n=15 cases):**

| ROI / lattice | mean DN | floor sd | photon-transfer model sd | ratio | Immerkaer | Immerkaer/model |
| --- | --- | --- | --- | --- | --- | --- |
| centre / G1 | 516.7 | 13.66 | 13.85 | **0.986** | 13.07 | 0.943 |
| centre / G2 | 517.6 | 13.90 | 13.86 | **1.002** | 13.09 | 0.945 |
| centre / GQ | 422.0 | 11.91 | 12.54 | **0.950** | 12.12 | 0.967 |
| upper-left / GQ | 1835.9 | 26.18 | 25.98 | **1.008** | 26.26 | 1.011 |
| upper-right / GQ | 1498.3 | 25.17 | 23.48 | **1.072** | 22.41 | 0.954 |
| lower-left / GQ | 1123.7 | 20.11 | 20.35 | **0.988** | 18.93 | 0.930 |
| lower-right / GQ | 2027.4 | 27.74 | 27.30 | **1.016** | 27.60 | 1.011 |

**Full f/11 range across all 15 tile cases: 0.950x to 1.093x.** Signal levels span 422 to 2027 DN,
a 4.8x range, and the agreement holds across all of it — so it is testing the *slope* of the
photon-transfer relation, not just one point.

**H4 answered: the project's noise model is independently confirmed to within ~±10% by a method
that shares none of its assumptions.** It uses no dark frames, no flat fields, no Immerkaer
kernel, no gain constant fitted to this data — only the height of the plateau in a Fourier
spectrum. Immerkaer on the same ROIs agrees with the model to 0.896-1.020x, so all three methods
now concur.

**Where they disagree, the disagreement is diagnostic, not troubling:** at f/8 the ratio is
4.58-20.19x and at f/5.6 it is 1.70-2.52x, because in those stacks the "floor" contains subject
signal. The floor-derived sigma is only a noise estimate when the floor is genuinely flat, and
the estimator says when it is not (`kappa` clipping at 50.0).

---

## 9. What this decides for the design

### 9.0 It retires the corpus's largest stated uncertainty — partially

`F-camera-lens-optics.md` §F1.7b calls the unknown pupil magnification `p` **"the dominant
uncertainty in the whole advisor"**, worth ±38% at m = 1.4, and lists two bench procedures to
obtain it (an exposure-loss measurement and a direct pupil-diameter measurement). Neither was
ever run.

**M5 obtains the same quantity by a third route, from data the owner already had, and it is the
better route: it measures `N_eff / N_marked = (1 + m/p)` *directly*, which is the number the
advisor actually consumes — `p` is only ever a means to it.** (DERIVED.)

Against F1.7b's tabulated range, conditional on m = 2.0 and λ = 550 nm (DERIVED):

| F1.7b candidate | implied B at m=2 | M5 verdict |
| --- | --- | --- |
| p = 0.5 (the brief's second candidate) | 5.00 | **REFUTED** — model-free, 5/5, two apertures |
| p = 0.7 | 3.86 | **excluded** — above the measured bound B ≤ 3.064 |
| p = 1.0 | 3.00 | **survives**, and is the best-supported value |
| p = 1.3 | 2.54 | survives |
| p → ∞ (B → 1) | 1.00 | **REFUTED** by a factor of ~3 |

So `F-camera-lens-optics.md`'s working assumption of **p = 1 was right**, and the ±38% advisory
tightens: B is now bracketed to **[2.41, 3.06]**, i.e. **−20% / +2% about B = 3** — but **it does
not vanish**, because M5 measures the product (1 + m/p) and cannot separate `p` from `m`, and
because `m ≈ 2.0` is itself DERIVED from the brief rather than measured. The bench procedures in
F1.7b are still worth running: they would give `p` alone, and hence `B` at *any* magnification,
whereas M5 gives `B` at one.

**Two existing corpus tables are confirmed by direct measurement (VERIFIED against
`F-camera-lens-optics.md`).** Both were DERIVED under the assumption p = 1 and had never been
tested against data:

- **F1.9's Nyquist-extinction threshold, `N_eff = 18.6`.** M5's independently computed
  crossover — the marked aperture at which f_c falls to sensor Nyquist — is f/6.21, and
  3.0 x 6.21 = **18.6**. Same number, reached from a measurement rather than from the identity.
- **F1.10's `m = 2.00` row for the SEL20TC: MTF_d at Nyquist = 0.036 at f/5.6, 0.000 at f/8 and
  f/11.** M5's measured B, put back through the diffraction MTF, gives **0.036, 0.000, 0.000**
  — identical to three decimals on the only non-zero entry. The row was a prediction; it is now
  a prediction that has been checked against data.

**F1.10's headline conclusion is unaffected and is now on firmer ground:** at m = 2 the rig
delivers essentially no contrast at sensor Nyquist except wide open, and none at all from f/8.
The advisor should keep refusing to promise 33 MP.

### 9.1 The per-aperture table (DERIVED at B = 3.0, λ = 550 nm, pitch 5.12 µm, m ≈ 2)

| Marked N | N_eff | f_c (cyc/px) | f_c (cyc/mm) | Airy FWHM (µm) | Airy FWHM (px) | Nyquist BW used (1-D) | Nyquist BW used (2-D area) | MTF_d at 0.25 cyc/px | MTF_d at Nyquist |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **f/5.6** | 16.8 | 0.5541 | 108.2 | 9.52 | 1.86 | **100%** (capped; raw 111%) | **100%** | **0.446** | 0.036 |
| **f/8** | 24.0 | 0.3879 | 75.8 | 13.60 | 2.66 | **77.6%** | **60.2%** | **0.240** | 0.000 |
| **f/11** | 33.0 | 0.2821 | 55.1 | 18.69 | 3.65 | **56.4%** | **31.8%** | **0.045** | 0.000 |

Sensor Nyquist = 0.5 cyc/px = 97.66 cyc/mm. The last two columns are the diffraction MTF
`MTF_d(s) = (2/π)(arccos s − s√(1−s²))`, `s = f/f_c`, evaluated at 4-pixel detail (0.25 cyc/px)
and at pixel-level detail (0.5 cyc/px). **They are there because bandwidth utilisation counts
where the OTF is non-zero, not where it is useful** — f/5.6 nominally "uses 100% of Nyquist" but
delivers only 3.6% contrast at Nyquist, which is not a usable image structure. **The 0.25 cyc/px
column is the honest resolution comparison**: the contrast available at 4-pixel detail collapses
by **10x** between f/5.6 and f/11.

**Quantifying the loss (DERIVED):**

- **f/8 throws away 39.8% of the sensor's two-dimensional Nyquist bandwidth.**
- **f/11 throws away 68.2% of it** — the optics deliver less than a third of the spatial-frequency
  area the sensor can record. A 33 MP sensor is being used as an effective ~10.5 MP one.
- The marked aperture at which the diffraction cutoff exactly reaches sensor Nyquist is
  **N_marked = pitch / (λ · 0.5 · B) = 5.12 / (0.55 · 0.5 · 3) = f/6.21**. (This one number is
  sensitive to the λ assumption: at λ = 500 nm it is f/6.83, at λ = 600 nm it is f/5.69.)

### 9.2 The shooting recommendation

**ARGUED (this experiment measures only the bandwidth side of the trade):**

- **f/5.6 marked gives the most detail, by a wide margin.** At B = 3 it is the only one of the
  three that does not discard sensor bandwidth, and at 4-pixel detail it delivers **10x the
  contrast of f/11** (MTF_d 0.446 vs 0.045) and **1.9x that of f/8** (0.240). Its raw predicted
  f_c is 111% of Nyquist, so it is also the only one where **aliasing is possible** — relevant
  because the A7C II is believed (UNVERIFIED) to have no OLPF. Note that "100% of Nyquist" does
  not mean pixel-level detail is *usable* there: MTF_d at Nyquist is only 0.036 even at f/5.6.
- **f/6.3 marked is the "just critically sampled" setting** (f/6.21 exactly). If aliasing on
  high-contrast detail is a concern, this is the defensible default: full bandwidth, no
  supra-Nyquist content.
- **f/8 costs 40% of the bandwidth area and 46% of the contrast at 4-pixel detail; f/11 costs
  68% and 90%.** These are not free choices made for depth of field; they are large, quantified
  resolution costs, and f/11 in particular is close to throwing the sensor away.
- **What this experiment does NOT measure:** the other side of the trade. Stopping down buys
  depth of field per frame and therefore fewer frames for the same total depth. That relationship
  was **not measured here** and no number for it is offered — publishing an unverified DoF formula
  is exactly the failure mode this project has already had to retract once.
- **Consequence for the stacker itself (ARGUED):** with f_c at 0.28-0.55 cyc/px, any focus
  measure, alignment estimator or sharpening kernel that assumes usable content near sensor
  Nyquist is assuming content the optics cannot deliver at f/8 or f/11. Band-limiting focus
  measures to below the *effective* cutoff is justified by this measurement, and the advisor should
  compute that cutoff from N_eff = FNumber_exif x 3, not from FNumber_exif.

---

## 10. Gaps — what is still not verified

- **n = 1 everywhere.** One camera, one lens, one teleconverter, one subject per aperture, one
  focus distance, one session. The *mechanism* is general; these specific numbers are not claimed
  to generalise.
- **The measurement is effectively n = 1 ROI.** Only the centre / GQ case at f/11 has enough
  spectral dynamic range to produce the tight bound. C4 confirms the others do not contradict it,
  but they do not confirm it either.
- **λ = 550 nm is an assumption, and it is the dominant systematic.** B ∝ 1/λ. The support of a
  polychromatic OTF is set by λ_min, not λ_mean, and a Bayer green filter passes usefully down to
  ~480-500 nm. λ = 500 nm ⇒ **B x 1.10**; λ = 600 nm ⇒ **B x 0.917**. That is roughly a ±10%
  systematic, and it happens to move the bias-corrected estimate from 2.6-2.9 back onto 3.0.
  **This has not been measured and the green channel's effective λ_min is UNVERIFIED.**
- **m ≈ 2.0 is DERIVED from the brief, not measured.** No ruler was photographed. The experiment
  measures B = (1 + m/p) as a single quantity and **cannot separate m from p.** Every statement
  about p in this document is conditional on m = 2.0.
- **C3 (monotonicity) is not tested.** See §5. This needs a different subject.
- **f/5.6 contributes nothing beyond consistency**, exactly as the brief predicted. Its bound is
  additionally weakened because **PRNU has never been measured for this sensor** (M4 could not see
  it; dark frames cannot), and **0.68% PRNU would fully explain its floor excess** (§4.3). This is
  a concrete, cheap capture request: a flat-field pair at ISO 50 would settle it.
- **`ImageStabilization = 1` (On) on tripod exposures of 1.3 s** (VERIFIED by exiftool). IBIS
  active on a static tripod can add motion blur. This is **unquantified** and would bias measured
  f_c *down*, i.e. B *up* — the same direction as the residual gap to 3.0. It is a candidate
  explanation for it and has not been tested.
- **Whether the A7C II has an OLPF is UNVERIFIED.** If it does, its cutoff multiplies into the
  measured one and the recovered B is an overestimate.
- **The GQ corner spike.** The quincunx re-indexing puts a strong feature in the corner of the
  rotated spectrum (corner/nearby power 20-510x). It lies **outside** the analysed isotropic
  radius, and the empirical proof that it is not leaking in is that the f/11 floor matches the
  photon-transfer model at 0.950x. That justification is **empirical, not analytic** — no
  derivation is offered that it must be harmless.
- **The model fit's cutoffs are suppressed and should stay suppressed.** At f/11 it consistently
  returns 0.36-0.40 (⇒ B ≈ 2.2-2.5) at high-dyn ROIs, but those are **above-reach extrapolations**
  outside the data, and C1b showed it running away by up to +112% on real texture. They are
  reported here only so nobody rediscovers them and mistakes them for evidence. **UNVERIFIED.**
- **Test (b) of the falsification table does not model MTF roll-off** (§4.5), so the refutation
  of B=2 and the B ≳ 2.41 lower bound are ARGUED, not MEASURED.
- **The raw crossing rule has a 34% false-alarm rate on pure noise** (§3.1). Its safety rests
  entirely on one fixed threshold, `DYN_GATE = 10`. That threshold was not tuned on this data, but
  neither was it derived from first principles.
- No frame was ever averaged with another. Periodograms were averaged; pixels were not.
  (Deliberate — see `experiments/m5-diffraction/README.md`.)

---

## 11. How to quote this result

> On a Sony A7C II with the FE 100mm F2.8 Macro GM OSS plus a 2x teleconverter at ~2:1, the
> diffraction cutoff was measured directly from the raw green quincunx lattice of a marked-f/11
> stack: **f_c ≥ 0.2762 cycles/pixel (53.9 cyc/mm)**, with the power above it matching the
> project's photon-transfer noise model to **0.950x**. That gives a bellows factor
> **(1 + m/p) ≤ 3.06**, bracketed to **B ∈ [2.4, 3.1]**, consistent with **p ≈ 1** at m ≈ 2.
> An independent, knee-free bound from the f/8 stack gives **B < 3.32**. **p = 0.5 (B = 5) is
> refuted 5/5 by a model-free test at two apertures.** The camera's EXIF `FNumber` is the marked
> f-number and is **not** bellows-corrected: at 2:1 the marked f/11 is optically **f/33**.
> Separately, the high-frequency floor gives a structure-free noise estimate agreeing with the
> photon-transfer model to **0.950-1.093x** over a 4.8x range of signal level. n = 1 stack per
> aperture, n = 1 camera, n = 1 subject.

**Do not quote any of the following. They are artifacts, extrapolations or both:**

- **`f_sig` at f/8 (0.2817) or at f/5.6 (0.2431) as a cutoff.** There is no noise floor inside the
  measurable band in those stacks; 0.2817 is the estimator pinning at 0.8x the lattice reach.
- **Any model-fit `f_c`, at any aperture** — in particular the f/11 values of 0.36-0.40 and the
  B ≈ 2.2-2.5 they imply. Every one of them is an extrapolation above the lattice reach.
- **Any `f_sig` or `B_max` from an ROI with dyn < ~300.** The C4 and C5 tables include them for
  completeness; they are SNR-starved, not measurements. That includes every G1/G2 f/11 number
  except centre and upper-right.
- **A two-sided point estimate of B.** "B = 2.93" and "B = 2.63" appear in §4.1 as bias-corrected
  *illustrations* of where inside the bracket the answer probably sits. The defensible statement
  is "**B ≈ 3, bracketed [2.4, 3.1]**".
- **Anything about C3 / monotonicity as a passed test.** It was not testable. §5.
- **Any claim that f/5.6 measured anything.** It bounded B < 4.74 and that bound is weak.
- **The 0/330 dark-frame false-alarm rate without the 113/330 raw rate beside it.** Quoting the
  gated number alone misrepresents where the estimator's safety comes from.

---

## 12. Reproducing it

All commands are run from `experiments/m5-diffraction/`. Python 3.12.10, numpy 2.4.4,
scipy 1.17.1, rawpy 0.27.0 (VERIFIED). Approximate wall times on the reference machine in
brackets. **Nothing writes to `C:\dev\macro` or `D:\macro-dark-frames`.**

```powershell
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m5-diffraction

# 0. the estimator's arithmetic: frequency axis, periodogram normalisation,
#    the factor-of-2 guard, kappa calibration, false-alarm rate       (~4 min)
python m5_selftest.py

# 1. C1 - recover a cutoff we planted ourselves, plus the Trap 2
#    windowing control and the H4 sigma-recovery check              (~112 s)
python m5_synthetic.py

#    C1b - the same on real texture with a planted extra cutoff (~45 s;
#    --quick shortens the synthetic sweep that runs ahead of it, whose full
#    results are the ones quoted above)
python m5_synthetic.py --quick --real-crop C:\dev\macro\test\109MSDCF\DSC00018.ARW

#    the second C1b crop, a much flatter frame (reported in section 2.4)
python m5_synthetic.py --quick --real-crop C:\dev\macro\test\109MSDCF\DSC00009.ARW

# 2. C2 - the null control. 330 dark-frame cases, 11 ISOs.            (~5 min)
python m5_measure.py null D:\macro-dark-frames --tile 128

# 3. the measurement, one command per aperture. --dark supplies the
#    matched-ISO dark reference for C2b.                        (~35 s / ~160 s)
python m5_measure.py measure C:\dev\macro\test\109MSDCF    --n 11.0 --tile 128 --dark D:\macro-dark-frames\123MSDCF
python m5_measure.py measure C:\dev\macro\test\coffee-bean --n  8.0 --tile 128 --dark D:\macro-dark-frames\122MSDCF
python m5_measure.py measure C:\dev\macro\test\119MSDCF    --n  5.6 --tile 128 --dark D:\macro-dark-frames\122MSDCF

# audit: EXIF over a whole stack, per-value counts
python m5_measure.py exif C:\dev\macro\test\109MSDCF

# audit: print the radial spectrum itself rather than a fitted number.
# This is how the f/8 "no reachable floor" finding was established.
python m5_measure.py dump C:\dev\macro\test\coffee-bean --at centre --lattice GQ --tile 128
```

Sensor constants used (all from the corpus, MEASURED there): pitch **5.12 µm**, CFA **RGGB**,
black level **512**, white level **15360**, active area **7032x4688** at origin (0,0) inside a
zero-padded 7168x5120 buffer. Dark-folder ISO map (MEASURED by exiftool): 118→100, 119→400,
120→800, 121→1600, 122→50, 123→200, 124→640, 125→500, 126→250, 127→1000, 128→2000; first 2 frames
of each folder discarded as stabilisation shots, following M4.
