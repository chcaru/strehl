# M95 -- Election quality: does the merge elect the sharpest frame available?

**Status: PRE-REGISTRATION. Bars fixed before any statistic was computed.**
**Milestone:** M95 (M85-sharpness lineage). **Commissioned by ORCH 2026-08-24 21:45.**

---

## 1. Why this is the last suspect

The owner's complaint is verbatim: *"those stacks don't look too good yet. i can
see the promise."* Four candidate causes have been closed by measurement:

| suspect | closed by | reading |
| --- | --- | --- |
| the gate / averaging | M85, fact 1196 | facet amplitude `0.985x` over a 61x change in `n_eff`; `0.997x` binned-linear |
| the combination stage | M95 merge-vs-frame | merged output **byte-identical** to the elected frame: 180,697 px, 47 frame/ROI combos, **100.0000 %** exact, max **0 DN** of 65535 |
| deconvolution headroom | M115 | headroom `1.0014 +/- 0.0184`; no reconstruction path to extra sharpness |
| the occlusion halo | M87, M121 | a selection artefact, not an averaging one; removal happens at `n_eff = 1.000` |

That leaves exactly one link in the chain untested. My own report says it in
§11.3, and it is the sentence this milestone exists to close:

> **I proved the merge faithfully emits the frame it chose. I did not prove it
> chooses the best frame.**

**Fidelity of emission does not imply optimality of choice.** If the election
systematically picks a slightly-defocused frame, every number in the table above
still holds and the renders are still soft.

---

## 2. The statistic under test, quoted from the product

`crates/strehl-core/src/focus.rs:1-8`:

```text
g(p)     = sqrt(Gx(p)^2 + Gy(p)^2)            3x3 Sobel, scaled by 1/8
focus(p) = box_mean_13(g)(p) / max(sigma_L(p), EPS)
```

Gradient **magnitude** (degree 1, not energy), box-averaged over `27x27`
(`boxfilter.rs:3`), divided by the predicted standard deviation of a **single**
luma sample. The merge elects, per pixel, the frame maximising `focus`.

### 2.1 The mechanism this milestone is testing

`focus.rs:44-48` already admits the weakness, in the product's own words:

> `sigma_L` is the noise standard deviation of a **single** luma sample at that
> signal level [...] It is **not** the standard deviation of the windowed
> gradient magnitude, which is smaller by roughly the window's tap count and is
> not even centred at zero, since `|grad|` is a rectified quantity with a
> **positive noise floor**.

And `focus.rs:26-28`:

> **No operator measured is** [noise-free]: 0 of 36 reached `N <= 1.02x`
> (fact 37). The escape from selection's noise penalty is estimation, not a
> better selector.

So the project already knows the selector is noisy. **What has never been
measured is how much focus that noise costs.** The hypothesis under test is the
**winner's curse**: an argmax over 299 draws of a rectified, positively-biased
statistic does not return the frame with the most signal, it returns the frame
where signal-plus-noise happened to be largest. With 299 frames the maximum of
the noise term is far into its upper tail, and the bias grows with the number of
frames and with the noise-to-detail ratio -- so it is **worst exactly where
detail is weakest**, which is where softness is visible.

This is a mechanism, not a mood. It predicts a specific, falsifiable signature,
and §5 states what would refute it.

---

## 3. The oracle, and why it is not the same statistic wearing a hat

ORCH's constraint: *"An oracle that is genuinely an oracle, not the same focus
measure under another name. If ground truth comes from the statistic under test,
the result is circular by construction."*

The oracle is **not another focus measure**. It is an unbiased estimator of the
*very quantity the elector is trying to maximise*:

```text
elector   E(f,p) = box27( |grad I_f| )(p) / sigma_L(p)          <- maximises signal + noise
oracle    O(f,p) = box27( |grad I_f|^2 )(p) - box27( E|grad n|^2 )(p)
```

For zero-mean noise `n` independent of the scene `s`:

```text
E[ |grad(s + n)|^2 ] = |grad s|^2 + E[ |grad n|^2 ]
```

The cross term vanishes, so the noise contribution is **exactly additive and
exactly computable** from the calibrated noise model and the Sobel tap weights.
Subtracting it yields an **unbiased estimate of `|grad s|^2`, the noise-free
squared gradient energy of the scene.**

That is the structural difference and it is the only one that matters:

- rectified **magnitude** carries a noise bias that **cannot** be subtracted,
  because rectification is nonlinear -- which is precisely `focus.rs`'s own
  admission;
- squared **energy** carries a noise bias that **can** be subtracted exactly.

The elector maximises the noisy quantity. The oracle estimates the clean one.

### 3.1 The confound this introduces, and the control for it

Magnitude and energy are different functionals of the within-window gradient
distribution, so **even with zero noise they could rank frames differently.**
That confound is real and it is controlled by **N0** below: on a noiseless
synthetic ramp the two must agree. If they do not, the measured offset is
"elector vs energy-oracle" and **must not** be reported as "elector vs truth".

---

## 4. The instrument: cross-fitting on G1 and G2

An oracle that is also an argmax has **its own** winner's curse. Comparing them
would measure the difference of two curses, which is not the question.

An RGGB quad carries two green photosites: `G1` at `(0,1)` and `G2` at `(1,0)`.
Measured this session, `o1_cube.py`: each is `(2344, 3514)`, **exactly the
product's `plane_shape`**. They view the same scene through the same optics at
the same instant with **independent read and shot noise**.

```text
SELECT the frame on G1        ->  e1(p) = argmax_f E_G1(f,p)      modelled elector
                                  o1(p) = argmax_f O_G1(f,p)      oracle
EVALUATE the detail on G2     ->  O_G2( e1(p), p )  vs  O_G2( o1(p), p )
```

Because the evaluation channel is independent of the selection channel, **the
curse cancels for whichever rule did the selecting, on exactly equal terms.**
Both rules select on G1 and are scored on G2. Neither gets to mark its own work.

This is the single design decision that makes the number mean anything, and it
costs nothing: the split was already in the sensor.

### 4.1 Why drift does not invalidate this

Arm M is unaligned (`STREHL_ALIGN=0`) and drift spans **73.4 to 165.3 plane px**
across the stack (`s2_rois.json`). That collage effect is what retired my own
`sigma_eq` axis, so it has to be faced rather than assumed away.

It does not bite here, because **the elector compares frames at a fixed pixel
coordinate with no alignment.** Whatever content sits at pixel `p` in frame `f`,
the elector's job is to pick the `f` with the most detail at `p`. Drift changes
*what the content is*; it does not change *whether the choice was right*. The
oracle answers the identical pointwise question on the identical data.

Consequence for reporting, fixed now: the **primary** unit is a *detail deficit*,
which is well-posed under drift. A **frame offset** is only physically meaningful
where drift is small, so it is reported for `ROI-LOWDRIFT` (0.403 px/step) and
reported-with-caveat elsewhere.

---

## 5. PRE-REGISTERED BARS

Fixed before any statistic was computed. The cube build (`o1_cube.py`, pure
decode, no statistics) was launched first; **no number had been produced when
this section was written and committed.**

### B1 -- model fidelity. KILL SWITCH.

The modelled elector must reproduce the **real** election. The real election map
is recovered from the rendered TIFFs by byte-identity -- at `--gate 0` the merged
output equals exactly one frame's bytes, which my own report established at
100.0000 % over 180,697 px, so the map is recoverable wherever the winning frame
is among the rendered set.

- **PASS:** `e1` agrees with the recovered map on **>= 80 %** of testable pixels.
- **FAIL:** below 80 % I **do not report an election offset at all.** I report
  that I could not faithfully model the shipped elector, and the milestone
  returns a negative result about my instrument rather than a claim about the
  product.

80 %, not 95 %, because `e1` selects on G1 alone while the product uses combined
luma; a residual disagreement is expected and is not evidence of infidelity.

### B2 -- oracle commissioning. Discipline 594.

On a synthetic ramp with **known** ground-truth peak, built by exact
frequency-domain blur (no resampling, per the standing warning that any plant
which resamples has already changed the quantity being measured):

- **PASS:** the cross-fitted oracle lands within **+/-1 frame** of truth on
  **>= 90 %** of pixels.
- **FAIL:** the oracle is not commissioned and no oracle-derived number is
  reported.

### B3 -- N0, the magnitude-vs-energy confound (§3.1).

- **PASS:** on a **noiseless** synthetic ramp, elector and oracle elect the same
  frame on **>= 99 %** of pixels.
- **FAIL:** the offset is reported as "elector vs energy-oracle", explicitly not
  as "elector vs truth", and the functional difference is quantified.

### B4 -- THE FINDING. Both directions stated before looking.

Primary statistic: the **cross-fitted detail deficit**

```text
D = 1 - mean_p O_G2( e1(p), p ) / mean_p O_G2( o1(p), p )
```

- **CONCLUDE THE ELECTION IS LOSING SHARPNESS** if `D > 5 %` on **all three**
  detail ROIs, **and** the flat control reads `|D| < 1 %`, **and** the power arm
  P1 is monotone.
- **CONCLUDE THE ELECTION IS SOUND** if `D < 1 %` on all three detail ROIs
  **and** P1 shows the metric would have detected a one-frame offset. A null is
  only admissible with that power reading attached (discipline 595).
- **INCONCLUSIVE-BUT-BOUNDED** for `1 % <= D <= 5 %`: report the bound, claim no
  mechanism.

I have no preference between these outcomes and will report whichever the data
gives. A finding that the election is sound closes the last suspect and forces
the conclusion that the softness is in capture or optics -- which is a
project-level result, not a disappointment.

### B5 -- the unit the owner can feel.

ORCH: *"not a dimensionless score."* Convert the median frame offset to an MTF
cost at the binned Nyquist (**48.94 cy/mm**) and at **74 cy/mm**, using the
**measured** through-focus response of this capture, never a theoretical defocus
model. Report as *"the elected frame is on average N frames off peak, costing
X % MTF at Y cy/mm."*

---

## 6. Controls

| id | control | what it proves | required reading |
| --- | --- | --- | --- |
| **N0** | noiseless synthetic ramp | magnitude vs energy is not itself the effect (§3.1) | agreement >= 99 % |
| **N1** | oracle scored against itself | the deficit has a zero | `D = 0` by construction |
| **N2** | noiseless ramp, both rules | the deficit reads zero when the election IS optimal | `D` ~ 0 for both |
| **N3** | `ROI-FLAT`, contrast **1.18** | no detail means no findable peak; the metric must not manufacture one | `\|D\| < 1 %`, frame choice scatters |
| **P1** | force election to `peak + k`, `k = 1,2,5,10,25` | the deficit responds, monotonically, with the right sign | strictly increasing in `k` |
| **P2** | plant exact frequency-domain blur in one frame | both rules demote it | planted frame not elected |
| **P3** | G1/G2 independence | the cross-fit is not a sham | G1 == G2 on far fewer than half of pixels |

**P1 is the discipline-595 power control and it is mandatory**: if my headline is
that the election is sound, P1 is the only thing standing between that null and
a metric that always returns zero. ORCH's own warning applies directly -- *"A
metric that always returns zero passes a null perfectly."*

**Sign convention will be read off P1's own control**, not assumed, per the
warning that a sign error with accurate magnitude is invisible.

---

## 7. What I am not claiming

- Not that the aligned path behaves the same. Arm C's geometry control (F3)
  failed on 2 of 3 ROIs, so the aligned path remains my largest characterisation
  gap and nothing here extends to it.
- Not anything about colour. The lateral-CA correction is another lane's.
- Not that a better selector is the fix. `focus.rs:26-28` says the escape is
  estimation, not selection, and this milestone tests the size of the problem,
  not the remedy.

---

## 8. Bearing on the resampler-kernel decision

Stated here at ORCH's request, from the agent that measured it:

**My `+0.1160 dex` resampler-kernel result is withdrawn (§23 of
`M95-kernel.md`), and its withdrawal removes the measured basis for promoting a
sharper resampler kernel by default -- so the "G3 met" milestone recorded in
`docs/research/ORCH-kernel-decision.md` makes the change cheaper and more
reversible, but it does not make it justified, and nobody should read "all gates
met" as "go".**

The band that result was scored in is **12.8 % subject detail (CI 12.2-13.4) and
87.2 % noise**, with a dark-frame placebo at **1.0006** and a defocus null at
**+0.0033**.

---
---

# RESULTS

Everything from here down was written after the run. Nothing above this line has
been altered since it was committed at `66c0d3f`, before any statistic existed.
Every number below was printed by code executed in this session; the printing
script and the JSON it wrote are named against each block.

## 9. The cube

`experiments/M95-oracle/src/o1_cube.py`, log `out/o1_cube.log`.

299 frames of `bee-3-cpl` decoded from raw, four ROIs, and for each ROI the two
green sites `G1` and `G2` extracted separately. `G1` and `G2` are each exactly
`(2344, 3514)`, which is the product's own `plane_shape` -- the Bayer mosaic
hands over two independent noise realisations of the same scene for free, and
that is what makes the cross-fit in section 4 possible without a second capture.

- **299 unique crops**, no duplicates.
- **`G1 == G2` on 1.0715 % of pixels** (`r = 0.9965`), so the two channels are
  emphatically not copies of one another. This is control **P3** and it passes.
- Build time **381.2 s**; rawpy decode **2.39 s/frame**.

Noise model fitted from `G1 - G2` on the lowest 40 % of pixels by local
gradient, 24 bins: `gain = 0.233696`, `floor` clamped at the lower bound,
`black = 512.0`, **`R^2 = 0.99931`**. The floor clamping to zero is physically
odd -- real read noise is a few DN^2 -- and section 12 shows the result does not
depend on it.

## 10. Commissioning: nine controls, and the one that failed first

`src/o3_commission.py`, JSON `out/o3_commission.json`. **9/9 pass -- but only
after a failure I did not route around.**

| id | control | reading | bar |
| --- | --- | --- | --- |
| **K0** | Sobel noise kernel by Monte Carlo vs closed form | ratio **0.9999053** | `~1` |
| **K1** | my elector vs the product's formula | max abs diff **exactly 0.0** | `0` |
| **K2** | planted blur recovered | **-0.0657 / -0.0646 / -0.0631 / -0.0735 %** at sigma 0.25/0.5/1.0/1.5 | `< 1 %` |
| **P3** | G1/G2 independence | **1.0715 %** identical | `<< 50 %` |
| **N0** | noiseless ramp, magnitude vs energy | agree **99.8972 %**; each rule finds truth on **99.913 / 99.910 %** | `>= 99 %` |
| **N2** | deficit when the election is already optimal | **-0.0095 %** | `~0` |
| **B2** | both rules vs known truth, with noise | oracle **96.7082 %** within +/-1, elector **95.4246 %**, both median offset **0.0** | oracle better |
| **P1s** | forced offset, synthetic | **0 -> +1.985 -> +7.136 -> +30.031 -> +57.764 -> +77.304 %** at k = 0,1,2,5,10,25 | monotone |
| **P2** | exact spectral blur planted in one frame | elected on **58.0791 %** before, **0.0004 %** after | demoted |

**P1s also fixed the sign convention by measurement rather than assumption**: a
forced offset produces **positive** `D`, so positive `D` means the worse choice.
ORCH's warning that a sign error with accurate magnitude is invisible is exactly
why this was read off a control instead of reasoned about.

### 10.1 K2 failed, and the diagnosis convicted `scipy`

On the first run K2 read **6.9 to 10.3 % low**, and the error **grew with
sigma**. The tempting move -- swap in `scipy.ndimage.gaussian_filter` as the
plant and move on -- would have produced a green with no idea what had been
wrong.

`src/o3b_k2diag.py` compared my spectral plant against `scipy`. The disagreement
between them **shrank** as sigma grew: **11.3 % at sigma = 0.25 falling to
0.00004 % at sigma = 1.5**. That pattern is backwards for a real error in a
blur. It is the signature of a **discretisation artefact in a truncated kernel**,
which is worst when the kernel is narrow.

Two implementations disagreeing can never say which is wrong, so
`src/o3c_closedform.py` tested **both** against the analytic transfer function of
a Gaussian, `exp(-2 pi^2 sigma^2 f^2)`, at twelve `(sigma, f)` pairs:

| sigma | f (cyc/px) | closed form | my `fft_blur` err | `scipy` err |
| --- | --- | --- | --- | --- |
| 0.25 | 0.0625 | 0.9951925 | **-0.0000000 %** | **+0.4779 %** |
| 0.25 | 0.125 | 0.9809080 | **-0.0000000 %** | **+1.9263 %** |
| 0.25 | 0.25 | 0.9257915 | **-0.0000000 %** | **+7.9433 %** |
| 0.5 | 0.25 | 0.7346029 | **-0.0000000 %** | **+7.0024 %** |
| 1.0 | 0.25 | 0.2912129 | **-0.0000000 %** | **+0.0052 %** |
| 1.5 | 0.0625 | 0.8407263 | **-0.0000000 %** | **+0.0000 %** |

`fft_blur` is exact to **-0.0000 %** on all twelve pairs. `scipy` is wrong by up
to **+7.94 %** at sigma = 0.25 and the error is gone by sigma >= 1.0.

**So the plant was right and my estimator was wrong.** The unwindowed FFT of a
non-periodic crop leaks spectrally, and blurring mixes in content from outside
the crop; both bias the ratio low. The repaired estimator is windowed and
interior-only and recovers to **-0.06 %**.

**After repairing a gate you must prove it still measures.** Control **C3** hands
the repaired estimator a sigma = 1.0 blur against a sigma = 0.5 reference, where
the truth is `sqrt(1.0^2 - 0.5^2) = 0.8660`. It returns **0.8655**. An estimator
that merely echoes its input would have returned **1.0000**.

This one is fleet-relevant well beyond M95: **sub-pixel blur is exactly the
regime a sharpness experiment plants in**, and `scipy.ndimage.gaussian_filter` is
not accurate there.

## 11. B1, the kill switch: is my elector the product's elector?

`src/o4_b1.py`, JSON `out/o4_b1.json`.

The whole milestone rests on my Python elector standing in for `focus.rs`. B1
tests that against ground truth recovered by **byte-identity**: at `--gate 0` the
merge emits the elected frame exactly, so for each pixel the frame whose render
matches the merged output byte-for-byte **is** the frame the product elected.

- **Overall agreement 81.9058 %** against a pre-registered bar of **80 %**.
  **PASS**, by 1.9 pp.
- TIFF-to-plane registration offset **`dy = 0, dx = 0`, correlation
  `0.99999999`** -- so no resampling enters the comparison anywhere. Integer-only
  by construction, per the warning that any resampling plants blur.

| ROI | coverage | agree | within +/-1 |
| --- | --- | --- | --- |
| LOWDRIFT | 28.74 % | **85.88 %** | 95.32 % |
| MIDDRIFT | 24.85 % | **78.18 %** | 86.74 % |
| HIGHDRIFT | 25.18 % | **81.04 %** | 91.40 % |
| FLAT | 3.19 % | 24.27 % | 31.63 % |

Coverage is 25-29 % because only 23 of 299 frames were rendered, so only pixels
whose winner is in that candidate set are testable. **The modelled elector is
restricted to the same 23 candidates** -- comparing a 299-way argmax against a
23-way truth would manufacture disagreement out of nothing.

**This is a pass, not a triumph, and the residual ~18 % bounds everything
downstream.** ROI-FLAT's 24 % is the same story section 13 tells: on a field with
contrast 1.18 there is nothing to elect and the choice is noise.

## 12. The deficit: what the election actually costs

`src/o5_deficit.py`, JSON `out/o5_deficit.json`. Runtime ~17 min.

| ROI | **D** | one-frame cost (P1r) | exact agree | within +/-1 | mean / median / p90 abs offset |
| --- | --- | --- | --- | --- | --- |
| LOWDRIFT | **+1.3343 %** | +11.7008 % | 78.4632 % | 91.4790 % | 2.236 / 0.0 / 1.0 |
| MIDDRIFT | **+2.8310 %** | +12.3642 % | 66.4320 % | 82.2480 % | 6.400 / 0.0 / 14.0 |
| HIGHDRIFT | **+2.7989 %** | +11.4792 % | 66.1340 % | 83.7575 % | 4.453 / 0.0 / 10.0 |
| **FLAT (control)** | **+1.6251 %** | +13.0253 % | 66.9705 % | 88.6142 % | 1.897 / 0.0 / 2.0 |

300,304 pixels per ROI. **P1r is monotone on all four ROIs**, running
**+11.5 % -> +98.5 %** across forced offsets of 1 to 25 frames. That is the
discipline-595 power reading: this metric would have shouted if the election were
off by even one frame, so its near-silence is a measurement and not an artefact
of a metric that always returns zero.

**The scale is the point.** `D` of 1.3-2.8 % sits against a one-frame
sensitivity of 11.5-13.0 %. Whatever `D` is, it is worth **well under a quarter
of one frame off peak**.

### 12.1 The owner-facing number

`D` is dimensionless, so section 12 also rebuilds the picture both ways -- the
mosaic the elector emits and the mosaic a perfect election would emit -- and
takes their radial power spectra.

| band (cyc/px) | cy/mm | LOWDRIFT | MIDDRIFT | HIGHDRIFT | FLAT |
| --- | --- | --- | --- | --- | --- |
| 0.10-0.20 | 14.7 | -0.39 % | +1.24 % | **+2.00 %** | +0.29 % |
| 0.20-0.30 | 24.5 | -0.13 % | -0.48 % | -1.91 % | -0.62 % |
| 0.30-0.40 | 34.3 | -0.70 % | **-2.45 %** | -2.27 % | -1.21 % |
| 0.40-0.50 | 44.0 | -0.45 % | +0.92 % | -1.10 % | -2.14 % |

Amplitude, not power. **The entire range is -2.45 % to +2.00 %**, and it changes
sign between bands and between ROIs, which is what noise looks like rather than a
loss. **A perfect election would change this photograph by about two per cent of
amplitude, in both directions.** That is not visible, and it is not the owner's
complaint.

### 12.2 Does this rest on the fitted noise model?

No. Re-running LOWDRIFT with the fitted gain scaled by 0.80, 1.00 and 1.25:

**`D` = +1.3337 / +1.3343 / +1.3351 %.** A 56 % swing in the noise model moves
the headline by **0.0014 pp**.

### 12.3 The control that fired

**`ROI-FLAT` read `+1.6251 %` against a pre-registered bar of `|D| < 1 %`, and it
is above LOWDRIFT's `+1.3343 %`.** By the bars in section B4 the verdict is
therefore **INCONCLUSIVE-BUT-BOUNDED**, and I am reporting it that way rather
than quietly dropping the control.

A flat field has no findable peak, so any `D` there is instrument floor. That the
floor is comparable to the signal means `D` cannot be read as election error
without subtracting it -- and the flat ROI is a poor place to measure it, because
removing the detail removes the very thing being elected.

### 12.4 The blind spot was in my own control design

**N0 could not have caught this floor and that is my fault, not bad luck.** N0
ran on a synthetic ramp built from a **single** source frame, so every synthetic
frame sat at the **same exposure level**. On the real capture the levels vary
frame to frame, and the two rules treat level oppositely: the elector divides by
`box(sigma)` and so prefers lower-level frames, while the oracle scores absolute
gradient energy, which grows with level. That is a systematic disagreement with
nothing to do with focus, and a constant-level ramp is structurally blind to it.

Generalised: **a synthetic control built by varying one factor holds every other
factor constant, and is therefore blind to exactly the confounds that come from
the factors it froze.**

## 13. What the floor is NOT

`src/o6_decompose.py`, JSON `out/o6_decompose.json`.

Section 12.4's mechanism is a hypothesis, so it was tested rather than asserted.
o6 re-runs the deficit with the sigma divisor moved: `E_raw` is the elector
without its divisor, `O_div` is the oracle given one.

| ROI | headline `E` vs `O` | `E_raw` vs `O` | `E` vs `O_div` | `E_raw` vs `O_div` |
| --- | --- | --- | --- | --- |
| FLAT | **+1.6251 %** | +1.9058 % | +1.5253 % | +1.8063 % |
| LOWDRIFT | +1.3343 % | +1.2396 % | +1.2921 % | +1.1973 % |
| MIDDRIFT | +2.8310 % | +2.7823 % | +2.7948 % | +2.7460 % |
| HIGHDRIFT | +2.7989 % | +2.7258 % | +2.7378 % | +2.6647 % |

**Giving the oracle the same divisor moves the flat floor by `+0.0998 pp` of a
`+1.6251 pp` floor.** My hypothesis is **refuted** and I am recording it as
refuted. The floor is real, it is not the divisor, and o6 does not say what it
is.

o6 also printed the level variation N0 was blind to, which is real and large:

| ROI | mean level | spread |
| --- | --- | --- |
| FLAT | 1100.0 DN | 6.16 % |
| LOWDRIFT | 3096.6 DN | 7.07 % |
| MIDDRIFT | 3737.1 DN | 15.13 % |
| HIGHDRIFT | 3036.7 DN | **31.97 %** |

Level spread and `D` do rank together across ROIs, which is why the divisor was
worth testing -- and the divisor is nonetheless not the route.

## 14. The null arm: a floor measured where the detail still is

`src/o7_nullarm.py`, JSON `out/o7_nullarm.json`. Runtime 1230.8 s.
**Committed at `1593cee`, with its bars, before it was run.**

Section 12.3's floor was measured on `ROI-FLAT`, which removes the detail as well
as the focus dependence. o7 builds a null that removes **only** the answer: one
real scene, taken from the frame each ROI's oracle scores highest, replayed
across all 299 frames with the **real per-frame level variation** and freshly
drawn noise at the real magnitude, so no frame is sharper than any other and any
`D` is floor by construction.

- **ARM A** -- real detail, real level variation, no focus dependence.
- **ARM A2** -- identical but every frame at the same level, so the only
  difference left between frames is the noise realisation.
- **ARM B** -- the same scene with a focus ramp planted by `fft_blur`, so the
  true best frame is **exactly `f0 = 149`** at every pixel and election error can
  be read directly in frames with no yardstick at all.

### 14.1 The kill switch, checked first

**Worst oracle mean `|offset from f0|` at rate 0.20 px/frame: 3.489 frames**,
against a pre-registered bar of `< 25`. The oracle finds a peak it was handed, so
the instrument is not retired and a verdict may be issued.

### 14.2 The floor, and what it is made of

| ROI | scene frame | level spread above black | **N4** arm A | **N4b** arm A2 | level share |
| --- | --- | --- | --- | --- | --- |
| LOWDRIFT | 172 | 8.74 % | **+0.5224 %** | **-0.0297 %** | +0.5521 pp |
| MIDDRIFT | 124 | 19.80 % | **+0.4695 %** | **-0.0228 %** | +0.4922 pp |
| HIGHDRIFT | 144 | 49.61 % | **+0.4196 %** | **+0.0338 %** | +0.3858 pp |
| FLAT | 104 | 12.00 % | **+0.4354 %** | **-0.0149 %** | +0.4503 pp |

(o6's spreads are `(max - min) / mean` on raw DN; these are `max / min` above
black, which is the physically meaningful one. The two agree exactly: FLAT's
`(1144.1 - 512) / (1076.4 - 512) = 1.1200`.)

Three things fall out, and one of them corrects my own previous section.

**First, the statistic's zero is real and it was measured on real detail.** Arm
A2 reads `-0.030 / -0.023 / +0.034 / -0.015 %` -- indistinguishable from zero --
while the two rules agree on which frame to take on only **33.9 % to 39.0 %** of
pixels. **When every frame is equally good, disagreeing about which one to take
costs nothing.** That is the correct behaviour and it is exactly what a deficit
statistic should do; it also means the low agreement percentages in section 12
are not by themselves evidence of anything.

**Second, essentially the whole floor is level.** Arm A minus arm A2 accounts for
`+0.55 / +0.49 / +0.39 / +0.45` pp of floors of `+0.52 / +0.47 / +0.42 / +0.44`
%. Section 12.4's mechanism is therefore right in substance even though section
13's specific route through the sigma divisor was refuted -- the two rules do
weigh exposure level differently, and o6 showed that difference does not live in
the divisor. **I have measured that the floor is level-driven without isolating
which term carries it, and I am not claiming more than that.** The level share is
also nearly constant at `+0.39` to `+0.55` pp while the level spread it is
supposed to be driven by varies from 8.74 % to 49.61 %, which does not fit a
simple proportionality and is unexplained.

**Third, `ROI-FLAT` was the wrong null and it overstated the floor by 3.7x.**
Measured on the same ROI with the detail left in, the floor is **+0.4354 %**, not
the **+1.6251 %** the flat field reported. A featureless field does not merely
remove the focus dependence, it removes the quantity being elected, and the
argmax then wanders somewhere the real problem never goes.

### 14.3 The pre-registered verdict, which goes against where section 12 was heading

```text
excess = D_real (o5) - D_null (o7 arm A)
```

| ROI | `D_real` | `D_null` | **excess** | as frames off peak |
| --- | --- | --- | --- | --- |
| LOWDRIFT | +1.3343 % | +0.5224 % | **+0.8119 pp** | **0.069** |
| MIDDRIFT | +2.8310 % | +0.4695 % | **+2.3615 pp** | **0.191** |
| HIGHDRIFT | +2.7989 % | +0.4196 % | **+2.3793 pp** | **0.207** |

The bar committed at `1593cee` says `> +1.0 pp on two or more` detail ROIs means
**REAL ELECTION ERROR**, and two of the three clear it.

**So the verdict is: the election error is real.** Section 12 was heading for
"floor, election exonerated" and a better null took that away. I am reporting the
rule the way it was written rather than the way it was going.

**And the size is the whole story.** Converted through o5's own P1r yardstick,
the error is worth **0.069 to 0.207 of one frame off peak.** Real, resolved, and
smaller than a quarter of a single focus step.

### 14.4 The planted truth: the same answer by a route with no yardstick in it

Arm B knows the true best frame exactly, so it measures each rule's distance from
truth directly. `gap` is elector mean `|offset|` minus oracle mean `|offset|`, in
frames -- positive means the elector is further from truth.

| ROI | rate 0.05 px/frame | rate 0.20 px/frame |
| --- | --- | --- |
| LOWDRIFT | elector 5.414 / oracle 5.480 -> **-0.065** | elector 4.554 / oracle 3.489 -> **+1.065** |
| MIDDRIFT | elector 3.439 / oracle 2.892 -> **+0.547** | elector 1.101 / oracle 0.845 -> **+0.256** |
| HIGHDRIFT | elector 2.417 / oracle 2.688 -> **-0.271** | elector 1.365 / oracle 1.666 -> **-0.301** |
| FLAT | elector 1.640 / oracle 1.636 -> **+0.004** | elector 0.313 / oracle 0.444 -> **-0.131** |

The pre-registered bar for direct evidence was a gap **> 2 frames**, and nothing
reaches it: the spread is **-0.301 to +1.065 frames**, and it changes sign
between ROIs. This is a different statistic from the deficit, computed against a
different ground truth, and it lands in the same place -- **the elector is within
about one frame of the best available choice, and on two ROIs it is marginally
closer to truth than the oracle is.**

### 14.5 The limitation I declared in advance, and its measurement

The null's scene is built from one real frame, so it carries that frame's own
noise at variance `v/2`. Under arm B that embedded noise gets blurred along with
the scene and therefore peaks at `f0` too, making the planted peak easier to find
than a real one -- for **both** rules, so the gap is a lower bound.

**P5b** bounds it by pre-smoothing the scene at sigma = 0.8 before planting, on
LOWDRIFT at rate 0.20:

- absolute offsets get **worse** for both rules (elector **9.933**, oracle
  **8.587**, against 4.554 and 3.489), confirming the embedded noise really was
  aiding findability;
- the gap widens from **+1.065 to +1.346 frames**.

So the declared limitation runs in the conservative direction, as predicted, and
correcting for it moves the gap by 0.28 frames -- still far inside the 2-frame
bar.

### 14.6 The caveat that limits section 14.3

**The excess ranks with drift, and the null does not reproduce drift.** MIDDRIFT
and HIGHDRIFT carry the larger drift and the larger excess (+2.36 and +2.38 pp);
LOWDRIFT, the only ROI where a frame offset is physically meaningful at all
(section 4.1), carries the smallest (+0.81 pp). Arm A replays a single fixed
scene, so any content change caused by drift lands in `D_real` and not in
`D_null`, and part of the excess on the two high-drift ROIs may be that rather
than election error.

That can only inflate the excess, never deflate it. **So 0.069 to 0.207 frames
is an upper bound on election error, and LOWDRIFT's 0.069 frames is the cleanest
single estimate.** Removing this caveat needs a null with integer-shift drift
replayed on top, which is a run I have not made.

## 15. The unit the owner can feel (bar B5)

`src/o8_owner.py` and `src/o9_sigma.py`, JSON `out/o8_owner.json`,
`out/o9_sigma.json`.

Converting a deficit into something visible needs the capture's **own**
through-focus response, so o8 rebuilds the emitted mosaic at forced offsets of
0, 1, 2 and 5 frames from the oracle's choice and takes the same radial spectra
as section 12.1.

**Amplitude cost of being one frame off peak, measured:**

| ROI | 14.7 cy/mm | 24.5 cy/mm | 34.3 cy/mm | 44.0 cy/mm |
| --- | --- | --- | --- | --- |
| LOWDRIFT | -4.218 % | -15.544 % | -28.097 % | **-33.047 %** |
| MIDDRIFT | -4.405 % | -15.135 % | -21.978 % | -17.740 % |
| HIGHDRIFT | -3.982 % | -13.274 % | -17.396 % | -14.696 % |

o9 fits those four bands to the closed form `exp(-2 pi^2 sigma^2 f^2)`, which is
a test as well as a conversion -- if the bands disagree on a single sigma the
response is not a defocus blur and must not be quoted as one. At one frame the
fit holds, with band residuals of **-0.62 to +4.44 %** on LOWDRIFT:

> **One focus step on this capture is equivalent to 0.2342 to 0.3341 px of
> Gaussian blur on the emitted plane -- 2.39 to 3.41 um at the 10.2163 um
> emitted pitch.**

(At offsets of 2 and 5 frames the single-sigma fit breaks down badly, residuals
reaching +56 %, so sigma is quoted only for one step. A defocus PSF is not
Gaussian far from focus and this is that.)

**Scaling the measured one-frame cost by the measured deficit ratio gives the
answer to bar B5:**

| ROI | frames off peak | 14.7 cy/mm | 24.5 cy/mm | 34.3 cy/mm | 44.0 cy/mm |
| --- | --- | --- | --- | --- | --- |
| LOWDRIFT | 0.0694 | -0.293 % | -1.079 % | -1.950 % | -2.293 % |
| MIDDRIFT | 0.1910 | -0.841 % | -2.891 % | **-4.198 %** | -3.388 % |
| HIGHDRIFT | 0.2073 | -0.825 % | -2.751 % | -3.606 % | -3.046 % |

> **The election is costing this photograph between 0.3 % and 4.2 % of
> amplitude, worst at 34.3 cy/mm on the highest-drift ROI. A perfect election
> would be an improvement of at most about four per cent, and that is an upper
> bound (section 14.6).**

Four per cent is at or below the threshold of visibility. **This is not what the
owner is looking at.**

## 16. The second arm: the 74 cy/mm floor

`src/o10_optics.py`, JSON `out/o10_optics.json`. My brief asked whether M85's
artefact floor at 74 cy/mm is in the optics, the demosaic, the resample or the
merge. **It is in none of them, and the reason is arithmetic.**

From the capture's own geometry, printed by o10:

- CFA **4688 x 7028 = 32.9 MP**; sensor pitch **5.1081 um**, sensor Nyquist
  **97.88 cy/mm**.
- The green plane the product emits is **2344 x 3514**, pitch **10.2163 um**,
  Nyquist **48.94 cy/mm**.
- **8.2 MP emitted from a 32.9 MP capture -- 25.0 %.**

**74 cy/mm is 1.512x the emitted Nyquist and 0.756x the sensor Nyquist.** The
sensor can represent it. Nothing the product emits can. So no stage operating on
that plane -- demosaic, resample or merge -- can be the floor, because none of
them can represent the frequency in the first place.

### 16.1 The optics still have contrast there, and this is the whole point

EXIF is verified as `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`,
`FNumber 5.6`, `MaxApertureValue 5.6` -- **f/5.6 is wide open with the
teleconverter fitted and there is zero aperture headroom.** The working aperture
is `N_eff = N (1 + m/p)`; magnification is not in EXIF, so it is bounded rather
than assumed, over `m = 0.5` (loose) to `m = 2.8` (the 1.4:1 bare lens times the
2X TC), at `lambda = 550 nm`:

| m | N_eff | cutoff | MTF at 48.94 (emitted Nyq) | MTF at 74 | MTF at 97.88 (sensor Nyq) |
| --- | --- | --- | --- | --- | --- |
| 0.5 | 8.40 | 216.5 cy/mm | **71.5 %** | 57.3 % | 44.4 % |
| 1.0 | 11.20 | 162.3 cy/mm | **62.2 %** | 44.0 % | 28.2 % |
| 1.4 | 13.44 | 135.3 cy/mm | **55.0 %** | 34.0 % | 16.7 % |
| 2.0 | 16.80 | 108.2 cy/mm | **44.4 %** | 20.3 % | 3.5 % |
| 2.8 | 21.28 | 85.4 cy/mm | **31.3 %** | 5.8 % | 0.0 % |

The 20.3-34.0 % window at `m = 1.4` to `2.0` reproduces **M85 section 7's
19-34 %**, independently and from primary constants, which is a check on that
earlier number as well as on this one.

**Across the entire plausible magnification range, the optics deliver 31.3 % to
71.5 % MTF at the very edge of what the product emits.** Diffraction is not the
binding constraint at 48.94 cy/mm at any magnification this lens can reach. The
constraint is the decision to emit one pixel per 2x2 Bayer cell.

---

# 17. THE ANSWER

**The election is real but small, and it is not the softness.**

1. **Is the merge as sharp as the sharpest frame that went into it?** Yes,
   exactly. At `--gate 0` the merged output is **byte-identical** to the frame it
   elected -- 180,697 px over 47 frame/ROI combinations, **100.0000 % exact,
   max deviation 0 DN**. The combination stage destroys nothing.

2. **Does it elect the best frame?** Almost. The election error is **real**
   (pre-registered verdict, section 14.3: `+0.8119 / +2.3615 / +2.3793 pp`
   excess over a properly built null) and it is worth **0.069 to 0.207 of one
   frame off peak**, an upper bound, costing **0.3 % to 4.2 % of amplitude** at
   14.7 to 44.0 cy/mm.

3. **So where is the softness?** Every stage of the pipeline is now eliminated:
   the gate (fact 1196, 61x change in `n_eff` moved facet amplitude 0.985x), the
   combination (byte-exact, above), deconvolution (M115, headroom
   `1.0014 +/- 0.0184`), the halo (M87/M121, a selection artefact at
   `n_eff = 1.000`), and now the election (at most 4.2 % of amplitude).
   **What is left is that the product emits 25.0 % of the pixels it was given,
   while the optics still deliver 31-72 % MTF at the frequency where that
   truncation bites.**

**The single most consequential sentence in this report:** the pipeline is not
losing the detail, it is never asked to carry it. `bee-3-cpl` is a 32.9 MP
capture rendered as an 8.2 MP picture.

## 17.1 What I am NOT claiming

- **Not** that full-resolution demosaic would recover all of it. Bayer green is
  a quincunx lattice with a diagonal Nyquist above the axis-aligned one, and how
  much of the 48.9-97.9 cy/mm band a demosaic actually recovers is an
  **unmeasured** question and the obvious next milestone.
- **Not** that the election should be changed. 4.2 % of amplitude is not worth
  touching `focus.rs`, and `focus.rs:26-28` says the escape is estimation rather
  than a better selector anyway.
- **Not** that section 14.3's excess is purely election error -- section 14.6
  says drift may carry part of it on two of three ROIs.
- **Not** anything about the aligned path. Arm C's geometry control failed on 2
  of 3 ROIs and that remains my largest characterisation gap.
- **Not** anything about colour.

## 17.2 Instrument exposure, declared

- **PIL 16-bit hazard:** measured, not asserted. `m95lib.py:48-55` reads through
  `tifffile` and carries `assert a.dtype == np.uint16` at line 54. The magnitude
  on my own headline file `armM-gate0-binlin.tif` was measured anyway:
  **11035 -> 149 distinct green levels (74.1x loss)** and spurious exact-match
  inflation of **0.1304 % -> 10.5624 % (81x)** (`x21_pilhazard.py`, commit
  `913fd0e`). Nothing in this report is exposed. The two scripts ORCH flagged of
  mine are the ones that **discovered** the bug and stop before reporting.
- **`--srgb` exposure:** none. Every number here is computed on linear raw
  green-plane values from `rawpy`, or on 16-bit linear TIFFs read via
  `tifffile`.
- **Warp cache exposure (fact 1561):** none. Arm M is the **unaligned** path and
  no warp is computed or read.
- **Reachability:** `focus.rs` is on the live render path -- B1 confirms it by
  byte-identity against actual renders, which is a reachability proof by
  construction, not a `pub` that compiles.
- **`$LASTEXITCODE`:** no gate in this milestone was read through
  `Select-Object -First`; every pass/fail here is decided inside Python on
  values in the JSON.

(The byte-identity figures in section 17 were re-derived from
`experiments/M95-merge-vs-frame/out/s5b_election_checks.json` in this session
rather than recalled: **47 frame/ROI combinations, 180,697 px, 100.000000 %
exact, max 0.0 DN**.)

---

# 18. For the orchestrator to fold

Facts. Every number was printed by code run in this session and the printing
script is named.

1. **The `strehl` election error on `bee-3-cpl` is real but worth less than a
   quarter of one focus step.** Cross-fitted detail deficit `D` measured against
   a noise-subtracted energy oracle, both selecting on green site G1 and scored
   on G2: `+1.3343 / +2.8310 / +2.7989 %` on three detail ROIs, minus a properly
   constructed null of `+0.5224 / +0.4695 / +0.4196 %`, gives excess
   `+0.8119 / +2.3615 / +2.3793 pp` = **0.069 / 0.191 / 0.207 frames off peak**,
   an upper bound. `o5_deficit.py`, `o7_nullarm.py`.

2. **In the owner's unit, a perfect election would improve this photograph by
   between 0.3 % and 4.2 % of amplitude** across 14.7 to 44.0 cy/mm, worst at
   34.3 cy/mm. `o8_owner.py`.

3. **One focus step on `bee-3-cpl` equals 0.2342 to 0.3341 px of Gaussian blur
   on the emitted plane** (2.39 to 3.41 um at the 10.2163 um pitch), fitted
   across four bands to `exp(-2 pi^2 sigma^2 f^2)` with residuals -0.62 to
   +4.44 %. The single-sigma fit breaks down beyond one step (residuals to
   +56 %), so it is a one-step number only. `o9_sigma.py`.

4. **M85's 74 cy/mm artefact floor cannot be in the demosaic, the resample or
   the merge.** 74 cy/mm is **1.512x the Nyquist of the plane those stages
   operate on** (emitted pitch 10.2163 um, Nyquist 48.94 cy/mm) and 0.756x the
   sensor Nyquist (5.1081 um, 97.88 cy/mm). No stage downstream of the mosaic
   can represent it. `o10_optics.py`.

5. **`strehl` emits 8.2 MP from a 32.9 MP capture -- 25.0 % of the pixels --
   while diffraction still leaves 31.3 % to 71.5 % MTF at the emitted Nyquist**
   over the whole plausible magnification range `m = 0.5` to `2.8` at f/5.6 wide
   open with the 2X TC (`N_eff` 8.40 to 21.28, cutoff 216.5 to 85.4 cy/mm).
   Diffraction is not the binding constraint at 48.94 cy/mm at any magnification
   this lens can reach. `o10_optics.py`.

6. **The same computation reproduces M85 section 7's 19-34 % at 74 cy/mm**
   independently, from primary constants: 20.3 % at `m = 2.0` and 34.0 % at
   `m = 1.4`. `o10_optics.py`.

7. **`scipy.ndimage.gaussian_filter` is inaccurate for sub-pixel sigma.**
   Against the closed form `exp(-2 pi^2 sigma^2 f^2)`: **+7.94 % at
   sigma = 0.25, f = 0.25 cyc/px**, +7.00 % at sigma = 0.5, decaying to
   +0.0000 % by sigma >= 1.0. An FFT-domain blur matched the closed form to
   **-0.0000 %** on all 12 `(sigma, f)` pairs. Sub-pixel blur is precisely the
   regime a sharpness experiment plants in. `o3c_closedform.py`.

8. **When every frame is equally sharp, two argmax rules disagree about which to
   take on 61 to 66 % of pixels and it costs nothing:** `D` reads
   `-0.030 / -0.023 / +0.034 / -0.015 %` at agreement of 33.9 to 39.0 %. Low
   election agreement is not by itself evidence of a defect. `o7_nullarm.py`
   arm A2.

9. **A featureless ROI is the wrong null for a focus-election experiment and
   overstates the floor by 3.7x here** -- `ROI-FLAT` reported `+1.6251 %` where
   the same ROI with its detail retained and only the focus dependence removed
   reports `+0.4354 %`. `o5_deficit.py` vs `o7_nullarm.py`.

10. **The floor that remains is level-driven, and it is not the elector's sigma
    divisor.** Moving the divisor onto the oracle changes the flat floor by
    `+0.0998 pp` of `+1.6251 pp` (refuted), while flattening exposure level
    removes `+0.386 to +0.552 pp` of floors of `+0.420 to +0.522 %`. Which term
    carries it is **unmeasured**. `o6_decompose.py`, `o7_nullarm.py`.

11. **PIL's 16-bit RGB defect, measured on M95's own headline file**
    `armM-gate0-binlin.tif`: distinct green levels **11035 -> 149 (74.1x
    loss)**, and spurious exact-match fraction against a different frame
    **0.1304 % -> 10.5624 %, an 81x inflation**. A byte-identity result read
    through PIL would have been manufactured. `x21_pilhazard.py`, commit
    `913fd0e`.

12. **`focus.rs` is reachable from the product, proved by byte-identity rather
    than by inspection.** B1 recovers the product's actual per-pixel election
    from renders and a Python reimplementation of `focus.rs` agrees on
    **81.9058 %** of pixels (bar 80 %), at registration offset `dy = 0, dx = 0`,
    `r = 0.99999999`. `o4_b1.py`.

Disciplines.

13. **A disagreement that shrinks as the effect grows is not an effect, it is a
    discretisation artefact.** Two blur implementations differed by 11.3 % at
    sigma = 0.25 and 0.00004 % at sigma = 1.5; that shape, not the magnitude,
    is what identified the truncated kernel. `o3b_k2diag.py`.

14. **Two implementations disagreeing can never say which is wrong.** Only an
    external closed form can convict either, and here it convicted the one that
    was not mine. `o3c_closedform.py`.

15. **After repairing a gate, prove it still measures.** A repaired estimator
    handed a sigma = 1.0 blur against a sigma = 0.5 reference returned
    **0.8655** for a true `sqrt(0.75) = 0.8660`; an estimator that merely echoed
    its input would have returned exactly 1.0000. `o3c_closedform.py` control
    C3.

16. **A synthetic control built by varying one factor holds every other factor
    constant and is therefore structurally blind to the confounds carried by the
    factors it froze.** My N0 ramp came from a single source frame, so every
    synthetic frame sat at the same exposure level, and it could not have seen a
    level-driven floor no matter how it was run.

17. **A null must remove the answer without removing the question.** Removing
    the detail removes the thing being elected and puts the argmax somewhere the
    real problem never goes; removing only the focus dependence, with the detail
    and the noise and the level variation left in place, gives a floor 3.7x
    smaller and defensible.

18. **Declare a control's known bias in advance and then measure its size.** The
    null scene carried its source frame's own noise at `v/2`, which peaks with
    the planted focus peak and flatters both rules; pre-smoothing at sigma = 0.8
    widened the measured gap from `+1.065` to `+1.346` frames, confirming the
    declared direction and bounding the effect at 0.28 frames.

19. **Restrict a model to the same candidate set as the truth it is scored
    against.** B1's truth covers only the 23 rendered frames, so the modelled
    elector argmaxes over those 23; a 299-way argmax against a 23-way truth
    manufactures disagreement out of nothing.

## 18.1 Two corrections to my own earlier reporting

20. My section 12 verdict of **INCONCLUSIVE-BUT-BOUNDED** was reached with the
    wrong null and the honest verdict under the pre-registered rule with the
    right null is **REAL ELECTION ERROR** -- which is the *less* flattering
    direction for the exoneration section 12 was heading toward, and it is
    reported that way.

21. **My `+0.1160 dex` resampler-kernel result is withdrawn, and its withdrawal
    removes the measured basis for promoting a sharper resampler kernel by
    default.** The band it was scored in is 12.8 % subject detail (CI 12.2-13.4)
    and 87.2 % noise, with a dark-frame placebo at 1.0006 and a defocus null at
    +0.0033. So `docs/research/ORCH-kernel-decision.md`'s "G3 met" makes the
    change cheaper and more reversible, **but nobody should read it as "go".**

---

# 19. What I recommend, and what I would need

**Do not touch `focus.rs`.** At most 4.2 % of amplitude, upper-bounded, and
`focus.rs:26-28` already says the escape is estimation rather than selection.

**The next milestone should be full-resolution output**, and it is the only
remaining candidate large enough to be what the owner is looking at. The
question to answer first, and it is unmeasured: **how much of the 48.9 to
97.9 cy/mm band does a demosaic actually recover from the Bayer green quincunx,
on this capture?** That is answerable on data already on disk, with the same
cross-fitting instrument built here -- G1 and G2 are the quincunx, and the
answer is the amplitude a full-resolution reconstruction retains in a band the
current output cannot represent at all.

**Capture request, for the orchestrator to file if it is wanted** (I do not edit
`docs/captures-needed.md`): a **slanted-edge target at the same magnification,
aperture and working distance as `bee-3-cpl`**, ten frames, no focus bracket.
Everything in section 16.1 is bounded over `m = 0.5` to `2.8` because
magnification is not in EXIF, and the bound spans 31.3 % to 71.5 % MTF at the
emitted Nyquist. A slanted edge would collapse that to one measured number, and
it would also settle whether the optics reach the diffraction limit at all
rather than being assumed to.

**Patches for files I do not own: none.** Nothing in this milestone requires a
change to product code.


