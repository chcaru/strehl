# M129 — the fabric-weave spectral aperture ladder: PREREGISTRATION

**Status: REGISTERED. No fabric pixel has been decoded at the time of writing.**

Written before measurement, per rule 20. Every prediction below is emitted by
`src/predict.py` and archived at `out/predict.txt` / `out/predict.json`, committed
at `cc98dded` **before** any reduction code existed. Nothing in this document was
chosen after seeing a result; deviations will be recorded as numbered amendments in
section 11, with the reason and the date, never by editing the text above them.

---

## 0. The question, in one sentence

**Measure the bellows factor `B = N_eff/N` on the five-aperture fabric capture, and
so decide between SYNTHESIS fact 1152's endpoints H2 (`B` = 3.0763) and H3
(`B` = 2.4020) — a 28.07% separation in cutoff frequency at every aperture.**

---

## 1. Why this lane exists, and what it is not allowed to re-derive

Rule 40 search run with `python experiments\ORCH-drift-check\prior_art.py power
spectrum ratio aperture ladder random texture cutoff frequency`. Reports surfaced
and read before this document was written:

| report | what it already settled | what this lane must NOT redo |
| --- | --- | --- |
| `M5-diffraction-measured.md` | `B` in [2.41, 3.06] from the GQ power spectrum, taking neither `m` nor `p` as input. Built and validated the estimator: synthetic positive control, real-texture positive control, dark-frame null, fixed-seed placebo, two-directional falsification. | Do not rebuild the estimator. Reuse it (discipline 716, rule 24 applies only to the *cross-check*). Do not re-derive the bracket. |
| `M70-through-focus-spectrum.md` | The through-focus spectrum is the same spectrum scaled down (eigen-share 0.9959). Deconvolution is a PLUGIN, not the core. | Do not re-ask whether off-peak frames carry harvestable mid-band signal. |
| `M84b` (via facts 1151, 1152) | `m` = 2.7198 +/- 0.0051 from a 1 mm rule, no lens model, no EXIF trust. `p` in [1.31, 1.94]. | Do not re-measure magnification. Take `m` as given and cite it. |
| `M88` (via fact 1184) | The inversion `f_c -> N_eff -> B -> p` is built and round-trips exactly. "MACHINE BUILT, NO FUEL". | Do not rewrite the inversion. Supply the fuel. |

**The one thing M5 asked for and could not get.** M5 section 5 records C3
(monotonicity of `f_c` in `N`) as **NOT TESTABLE**, because at f/8 and f/5.6 the
subject spectrum never reached the noise floor inside the measurable band, so those
knees were texture-limited rather than optics-limited. Its limitations list says in
as many words: *"C3 (monotonicity) is not tested. This needs a different subject."*

M5 had **f/5.6, f/8, f/11**. This capture has **f/5.6, f/8, f/11, f/14, f/18** on one
fixed broadband subject. **The two extra stops are the entire reason this lane can
answer what M5 could not.**

---

## 2. Registered predictions

From `out/predict.txt`. Sensor pitch 5.12 um (Sony ILCE-7CM2), `m` = 2.7198,
lambda = 550 nm, cutoff `f_c = 1/(lambda * N_eff)`, `N_eff = B * N`.

### 2.1 Lattice reach — the ceiling on what any spectral method can see

| lattice | pitch um | Nyquist cy/mm |
| --- | --- | --- |
| G1 or G2 | 10.2400 | 48.828 |
| GQ quincunx | 7.2408 | 69.053 |
| full sensor | 5.1200 | 97.656 |

`GQ` is M5 section 2.2's re-indexing `B[u,v] = A[u+v, u-v+1]` of both green planes
onto their quincunx lattice. It interpolates nothing, uses exactly the same
photosites, and reaches sqrt(2) further than a single green plane. M5 calls it
load-bearing and it is load-bearing here too.

### 2.2 The hypotheses

| hypothesis | `f_c` at f/5.6 | `N_eff` | `B` | `p` |
| --- | --- | --- | --- | --- |
| H1 fact 1149 (already refuted) | 87.00 | 20.899 | 3.7319 | 0.9956 |
| H2 fact 1152 low | 105.54 | 17.227 | 3.0763 | 1.3099 |
| H3 fact 1152 high | 135.17 | 13.451 | 2.4020 | 1.9400 |

H1 is carried only as a falsifier target. Fact 1153 already refuted it: `p` = 1
demands `B` = 3.72, exceeding M5's measured upper bound 3.064.

### 2.3 The ladder, and which apertures can see it

| N | H1 | H2 | H3 | H3 margin under GQ reach |
| --- | --- | --- | --- | --- |
| 5.6 | 87.00 out | 105.54 out | 135.17 out | -66.12 |
| 8.0 | 60.90 IN | 73.88 out | 94.62 out | -25.57 |
| 11.0 | 44.29 IN | 53.73 IN | 68.81 IN | **+0.24** |
| 14.0 | 34.80 IN | 42.22 IN | 54.07 IN | +14.99 |
| 18.0 | 27.07 IN | 32.83 IN | 42.05 IN | +27.00 |

**Registered reading of this table, before any data:** f/5.6 and f/8 cannot
discriminate — both live hypotheses are out of band. f/11's H3 margin of 0.24 cy/mm
is not a margin. **f/14 and f/18 are the measurement; f/11 is a supporting point;
f/5.6 and f/8 are controls that must show a texture-limited knee, not an
optics-limited one.**

### 2.4 A retrodiction that was available before this lane ran

The table predicts f/11 is the lowest marked aperture at which a knee can be
optics-limited. **M5 measured exactly one genuine knee, and it was at f/11**, with
f/8 and f/5.6 texture-limited. The prediction machinery reproduces M5's outcome
without having been fitted to it. This is a free positive control on the model and
is registered as such: had the table said f/8 should have worked, the model would
already be in trouble.

---

## 3. The primary instrument

**Reuse M5's estimator unmodified.** Black-subtract; crop to the active area only
(the padded buffer would contaminate any FFT that touched it); extract the GQ
quincunx lattice; Welch-average Hann-windowed periodograms; radially average; find
the highest frequency standing above a fitted constant high-frequency floor by
`z = 3` standard errors for a run of 3 consecutive bins. Thresholds fixed in source
and identical across every aperture and every control.

**M5's dynamic-range gate is mandatory, not optional.** M5's null fired a raw
detection on **113/330 dark-frame cases (34.2%)**, with **0** surviving the
`dyn >= 10` gate. An estimator that is unsafe without a gate must never be run
without it, and the raw rate must be quoted beside the gated rate in the report
(M5's own "do not quote" list requires this).

**The ladder is over-determined, and that is the falsifier.** Five apertures give
five estimates of one constant `B`. Registered primary statistic: `f_c(N) * N`,
which must be constant. Its scatter across apertures is the instrument's own error
bar, obtained without any external calibration.

---

## 4. Registered threats, in the order I judge them dangerous

### T1 — the depth-of-field confound (PRIMARY THREAT)

Depth of field grows 3.2x from f/5.6 to f/18. The capture README states the fabric
is *"slightly non-planar and slightly waved"*. So at f/18 more of any ROI lies
within the in-focus depth, which **adds high-frequency content exactly where
diffraction should be removing it**.

**Direction, stated before measuring (rule 18):** this biases toward finding *too
little* aperture dependence, i.e. `f_c` too high at large N, i.e. **toward H3**. If
this lane reports H3, T1 is the first thing that must be excluded; if it reports H2,
T1 worked against the result and the result is stronger for it.

**Controls:** (a) small ROIs, chosen for local planarity; (b) per-aperture
best-focus frame rather than a shared frame index; (c) a planarity check that the
best-focus frame index agrees across sub-patches of the ROI, with the spread
reported; (d) an ROI-size sweep, since the confound must grow with ROI area and a
genuine optical cutoff must not.

### T2 — unequal noise floors by aperture

Exposure time is constant at 1.3 s across all five apertures (EXIF, verified), so
f/18 receives ~1/10.3 the light of f/5.6. The noise floor therefore differs by
aperture **by construction**.

**Control:** the `G1 x G2` cross-spectrum. The two green planes carry independent
photon and read noise, so their cross-spectrum has zero noise expectation while
retaining the common scene power. This removes the floor by construction rather
than by fitting it. Registered as a required arm, reported beside the single-plane
result; disagreement between them is diagnostic and must be published, not averaged.

### T3 — the subject spectrum is not flat

A ratio between apertures cancels the subject spectrum only if the subject is the
same. It is (one capture, subject untouched), but the *sampled* subject differs if
focus differs. Covered by T1's controls.

### T4 — CPL and colour

The capture uses a circular polariser and the fabric is white, blue and dark grey.
The green sublattice sees a green-filtered band, so lambda is an effective mean, not
550 nm exactly. **Carried as a stated systematic, not a correction.** Sensitivity is
registered: at 500 nm, `B` at H2/H3 becomes 3.3840 / 2.6422; at 600 nm, 2.8200 /
2.2018. This shifts both hypotheses together and so cannot manufacture a
discrimination, but it does move the absolute `B`.

### T5 — clipping

M128's reconnaissance found frames reaching 15871 DN, the container ceiling. Any
clipped ROI is disqualified. Registered gate: reject any ROI whose 99.9th percentile
exceeds 15000 DN, and report the rejection count.

---

## 5. Registered acceptance conditions

The lane reports a value for `B` only if **all** of these hold. Any failure is
published as a refusal, and **a clean refusal is a complete result.**

- **A1** The commissioning battery recovers a planted cutoff to within 5% at each of
  H2 and H3, on synthetic data, before any real frame is reduced (rule 9).
- **A2** The dark-frame null produces zero detections after the dynamic-range gate,
  with the raw pre-gate rate reported beside it.
- **A3** `f_c(N) * N` is constant across the apertures declared in-band in section
  2.3, to within the scatter the commissioning predicts.
- **A4** f/5.6 and f/8 show a texture-limited knee, i.e. the spectrum does **not**
  reach the noise floor inside the band. If they show a clean optics-limited knee
  where section 2.3 says they cannot, the model is wrong and the lane must stop and
  say so.
- **A5** The ROI-size sweep shows the recovered `f_c` independent of ROI area, while
  T1's confound is shown to depend on it.
- **A6** The `G1 x G2` cross-spectrum and the single-plane reduction agree.

---

## 6. What would falsify the whole approach

Registered now so it cannot be explained away later:

1. `f_c(N) * N` not constant, beyond commissioned scatter, with no identified
   defect. Then the diffraction-limited model is wrong for this rig and the
   inversion in fact 1184 has no fuel of this kind.
2. A recovered `B` outside M5's [2.41, 3.06] bracket. Two independent routes
   disagreeing is a finding, not a number to average, and would be reported as such.
3. f/14 and f/18 disagreeing with each other by more than they disagree with H2 and
   H3. That would mean the measurement resolves nothing.
4. The best-focus frame index varying across sub-patches by more than the focus step
   spacing. Then the ROI is not locally planar and T1 is uncontrolled.

---

## 7. Not in scope

- Magnification. Taken from M84b.
- The value of lambda. Carried as a systematic per T4.
- Anything about the merge, the gate, or the stacker. This is an optics measurement.
- The razor lane. M128 is a separate milestone with a separate subject; its outcome
  does not license or forbid anything here.

---

## 8. Deviations and amendments

None yet. Amendments are numbered A1, A2, ... in section 11 as they arise, each
recording what changed, why, and what evidence forced it.

---

## 11. Amendments

### Amendment 1 — A1's 5% bar is unachievable as written, and is restated

**Raised before any real frame was reduced; forced by prior art, not by a result.**

A1 as registered requires the commissioning battery to recover a planted cutoff "to
within 5%". **M5 has already measured that the primary estimator cannot do this.**
`m5_lib.knee_floor_crossing`'s own docstring records: *"C1 measures this estimator to
be biased 5-23% LOW, always in the same direction: the diffraction MTF approaches
zero as (1 - f/f_c)^1.5, so the last stretch below the cutoff is always buried in
noise. It is therefore read as a lower bound on f_c, hence an upper bound on
(1 + m/p)."*

So a 5% bar on the raw crossing estimate fails by construction. I registered a bar
the corpus had already measured to be unreachable. That is my error, and it is the
same class rule 43 and fact 1157 name: **reaching for an assumption without checking
whether a measurement of it already existed.** It is recorded here rather than
silently relaxed.

**Why this does not sink the lane, and why the bias matters less than it looks.**
The bias is multiplicative and common across apertures, because it is a property of
where the roll-off disappears into the floor, not of `N`. The registered primary
statistic is `f_c(N) * N`, and a common multiplicative bias leaves its **constancy**
untouched. So the falsification test in section 3 and condition A3 survive the bias
unchanged; only the **absolute** `B` is displaced.

**But the bias cannot simply be ignored**, because at 5-23% it is comparable to the
28.07% H2-H3 separation this lane exists to resolve. It must be measured, not
assumed.

**A1 is therefore restated as A1':**

> **A1'** The commissioning battery measures the crossing estimator's bias and its
> scatter as a function of planted `f_c`, signal-to-noise ratio and texture spectral
> slope, across the range this ladder actually uses. The **bias-corrected** estimator
> must then recover planted truth to within 5%, and the scatter of the correction
> must be reported as an uncertainty carried into every quoted `B`. If the bias
> depends on `N` — that is, if it does **not** cancel in `f_c(N) * N` — the ladder's
> falsification test is compromised and the lane must say so and stop.

The last sentence is the part that can fail, and it is registered before the battery
runs so that it cannot be quietly dropped.

**Consequence for the model fit.** `knee_model_fit` is not biased in this way,
because it uses the whole roll-off rather than the last detectable bin. It is
nevertheless **not** promoted to primary: it assumes the diffraction MTF shape, which
is the hypothesis under test, and M5 registered it as *"a cross-check, never the
headline"*. That standing remains. Its `above_reach` flag, which M5 validated at
36/36 with no false alarms, **is** promoted to the primary instrument for condition
A4, because A4 is a question about band coverage rather than about the cutoff value.

---

### Amendment 2 — gate T5 is applied per (ROI, aperture), not per ROI

**Raised after selecting ROIs and before reducing any spectrum. Forced by data, and
recorded here for that reason.**

T5 as registered says: *"reject any ROI whose 99.9th percentile exceeds 15000 DN"*.
Applied literally that rejects an ROI at every aperture if it clips at any one of
them. Measured on the six flattest non-overlapping ROIs (`out/rois-w2.json`):

| ROI | rc | cc | f/5.6 | f/8 | f/11 | f/14 | f/18 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 832 | 2880 | **16383** | 14207 | 7712 | 4637 | 3244 |
| 1 | 576 | 3648 | **16383** | 13685 | 7082 | 4281 | 3041 |
| 2 | 3392 | 4416 | **15410** | 8477 | 4597 | 2821 | 2069 |
| 3 | 3392 | 3136 | **15950** | 9312 | 4965 | 3038 | 2167 |
| 4 | 832 | 576 | **15603** | 9270 | 5465 | 3289 | 2294 |
| 5 | 1344 | 4672 | 12786 | 7068 | 3869 | 2432 | 1787 |

**Only f/5.6 clips.** Exposure was held at 1.3 s across all five apertures, so f/5.6
receives about 10x the light of f/18 and saturates. Every ROI is clear at f/8 and
far clear at the three in-band apertures.

Applying T5 per ROI would therefore discard five of six ROIs on account of an
aperture that section 2.3 has **already declared out of band**, and that appears in
this lane only as the A4 control. That is not a conservative reading of the gate, it
is an irrelevant one.

**T5 is therefore applied to each (ROI, aperture) cell.** A cell over 15000 DN is
rejected and takes no part in any statistic. The consequences are registered now:

- The in-band fit over f/11, f/14, f/18 uses **all six ROIs**, unaffected.
- The **A4 control at f/5.6 is available at ROI 5 only.** A4 is thereby weakened
  from six independent replicates to one, and the report must say so rather than
  quote A4 as if it were as well supported as the fit.
- At f/8, ROIs 0 and 1 sit at 14207 and 13685 DN. Those are under the gate but close
  to it, and the expected f/8-to-f/11 ratio of `(11.314/8)^2 = 2.00` is observed as
  only 1.84 and 1.93 there, which is the signature of mild tail compression starting
  below the white level. **The f/8 arm is therefore taken from ROIs 2 and 5 only**,
  where the ratio is clean, and this restriction is registered before use.

**This is a change of granularity, not of threshold.** The 15000 DN level is
untouched. The rejection count is still reported, now as a matrix rather than a
scalar.

---

### Amendment 3 — T1's mechanism is wrong as registered; its direction survives

**Raised after measuring the subject's focus geometry, before any spectrum.**

T1 is registered on this premise: *"Depth of field grows 3.2x from f/5.6 to f/18. So
at f/18 more of any ROI lies within the in-focus depth."* That is correct for a
single frame at a fixed focus setting. **It is not what this capture is.**

`planarity.py` establishes that the bracket stepped in **depth-of-field units**:
frame counts fit `n = 1162/N + 4.7` with 1.76-frame rms against 50.6 for a constant
count, better by 28.8x. The reduction then selects the best-focus frame *per ROI*.
So the residual defocus across an ROI is its physical relief divided by the depth of
field, and that **shrinks as `1/N`**; it does not grow.

The registered **direction is unchanged** — there is still less defocus penalty at
f/18, so the confound still pushes toward H3 — but the mechanism is different and,
more usefully, the magnitude is now measured rather than assumed.

**Supporting control, obtained free from data already in hand.** The subject was not
touched between apertures, so its tilt and relief are fixed physical depths, and
every geometric quantity read off the best-focus index map must scale as `1/N`.
Tested on three independently:

| quantity | spread of `y*N` | spread of `y` alone |
| --- | --- | --- |
| tilt gradient (steps/mm) | 7.5% | 48.9% |
| planar-fit residual (steps) | 6.2% | 47.7% |
| full range (steps) | 8.0% | 49.7% |

This certifies the cadence model from evidence independent of the file counts that
suggested it, shows the index map measures real subject geometry rather than
estimator noise (which would be constant in frames, not proportional to `1/N`), and
shows the rig was not disturbed between the five stacks.

The residual drift in that control is itself well determined: `y ~ N^-gamma` with
**gamma = 1.160** across all three quantities, log-residual rms 0.015 to 0.034. The
step grows slightly faster than `N`. This is recorded, not explained. It does not
enter the primary measurement, which selects frames by search and never converts a
frame index into micrometres; it is used only to put ROI relief into common physical
units when comparing ROIs across apertures.

**T1 is now self-diagnosing, which is the substantive gain.** Defocus blur scales as
relief divided by `N_eff` while diffraction blur scales as `lambda * N_eff`, so their
ratio goes as `1/N^2`. T1 therefore imprints a **trend** of `B` against `N`, whereas
a wrong value of `B` is a **constant offset**. Registered condition A3, the constancy
of `f_c(N) * N`, is thus a T1 detector and not merely a consistency check. A3 failing
with a monotone trend in `N` is diagnostic of T1; A3 failing with scatter is not.

---

### Amendment 4 — a threat absent from the original document

`m5_lib.focus_score`'s default band is 0.05 to 0.14 sensor cyc/px, that is 9.8 to
27.3 cy/mm. Its docstring describes this as *"well below every candidate cutoff"*,
which was true for M5's apertures. It is **not** true here: section 2.3 puts `f_c` at
f/18 at 32.83 cy/mm under H2, so the band's top edge sits at **0.83 of the cutoff**.
A focus measure whose band overlaps the roll-off would preferentially select frames
with a higher cutoff, biasing toward H3 — the same direction as T1, so the two would
compound rather than cancel.

**Registered control, and its result.** The focus score is computed in three bands:
the `m5_lib` default, a narrow band of 0.04 to 0.09 cyc/px chosen to lie below every
candidate cutoff at every aperture in the ladder, and a deliberately contaminated
wide band of 0.05 to 0.20. If frame selection were contaminated the three would
disagree. Measured at f/18 on a 512-sample ROI: **all three select frame 38.** The
control passes. It is nonetheless retained for every ROI, and the narrow band is used
for all map work, because passing once is not passing everywhere.

---

### Amendment 5 — an SNR-equalised arm, registered before the verdict that needs it

**Raised from synthetic evidence, before the commissioning battery reported, and
before any real spectrum was reduced. Registered now precisely so that it cannot
later look like a rescue invented to save a result.**

**The problem.** `xspec.py`'s commissioning measured the crossing estimator's bias
against signal-to-noise ratio on a diffraction roll-off, five seeds per point:

| spectral SNR | auto arm | cross arm |
| --- | --- | --- |
| 15.0 | -4.5% | -4.9% |
| 5.0 | -12.3% | -14.5% |
| 2.0 | -22.7% | -25.8% |
| 1.0 | -36.6% | -33.6% |

The bias is **strongly SNR-dependent**, spanning 32.1 points for the auto arm and
28.6 for the cross arm across a 15x range of noise.

**Why that is nearly fatal here.** Exposure was held constant, so the mean patch
level falls 4377 to 484 DN from f/5.6 to f/18 (measured, `out/smoke.txt`). Photon
noise variance goes as the signal while scene power goes as the signal squared, so
**spectral SNR goes as the signal**: a 9.0x range across the ladder. A bias that
varies with SNR therefore varies with `N`, and Amendment 1's A1' registered exactly
this as the outcome under which *"the ladder's falsification test is compromised and
the lane must say so and stop."*

Note also that the cross-spectrum arm does **not** rescue this. It removes the floor
from the spectrum but not the floor's influence on where the crossing lands. T2's
registered control is necessary and insufficient.

**The mitigation, registered as a second arm rather than a replacement.** Equalise
the SNR across apertures by *degrading* the bright ones to match the worst:

1. Measure, per (ROI, aperture), the scene power in a fixed low-frequency band and
   the noise power from the top of the band.
2. Take the worst ratio over the five apertures as the common target, which is f/18
   by construction.
3. Add independent Gaussian noise to each plane of every other aperture to bring its
   ratio down to that target. Added independently to G1 and G2, so the cross arm's
   noise-independence is preserved.

Every aperture then carries the **same** spectral SNR, so whatever bias the estimator
has is **identical across the ladder by construction** and cancels exactly in
`f_c(N) * N`. The price is precision at the bright apertures, paid knowingly: the
falsification test needs a bias that cancels far more than it needs a small one.

**Both arms are run and both are reported.**

- **native SNR** — best precision, requires the commissioning battery's bias
  correction, and that correction is large and therefore fragile.
- **equalised SNR** — needs no correction for the constancy test, at a cost in
  precision.

**Registered in advance:** if the two arms agree, that is a strong internal control
and the native arm may be quoted. **If they disagree, the equalised arm is the
trustworthy one and the disagreement must be published, not averaged.** If the
equalised arm cannot separate H2 from H3 because of its degraded precision, the
honest report is that this capture cannot decide the question, and what a capture
that could decide it would need — namely per-aperture exposure compensation, so that
every aperture lands at the same mid-scale level instead of at a constant 1.3 s.

**That last point is a capture requirement and is recorded as one**, independent of
how this lane resolves: a spectral aperture ladder should hold the *exposure level*
constant, not the *exposure time*.

---

### Amendment 6 — Amendment 5 did not say in which band, and the obvious band is wrong

**Raised by measurement, one day after Amendment 5 and still before any cutoff was
estimated on real data.** `src/snr_survey.py`, `out/snr-w2.json`, `out/snr-survey.txt`.

Amendment 5 registered "equalise the spectral SNR" without naming the band it is
measured in. Measuring it exposed that the choice is not free, and that the obvious
choice destroys the experiment.

**The measured spectral SNR is not monotone in aperture.** Power ratio, scene over
floor, in the band containing the candidate cutoffs (29.3-44.9 cy/mm), median over
the six ROIs:

| band | f/5.6 | f/8 | f/11 | f/14 | f/18 |
| --- | --- | --- | --- | --- | --- |
| knee, 29.3-44.9 cy/mm | 18.6 | 23.1 | 39.7 | 23.2 | 7.7 |
| low, 7.8-17.6 cy/mm | 2011 | 1707 | 2802 | 2591 | 1730 |

It rises and then falls. That is not a nuisance behaving oddly; it is two different
things being added together. The floor falls with aperture because exposure was held
constant, which is the artefact. And the roll-off moves down into the band as `N`
grows, which is **the signal**. f/18's knee-band SNR is low in large part *because its
cutoff lies inside that band.*

**So equalising on the knee band would have equalised away the effect under test.**
It would degrade f/11 and f/14 until they matched f/18's *optics* rather than
f/18's *noise*, and the ladder would measure nothing. This is the same error class as
T1 and the focus-band threat of Amendment 4: a control chosen inside the signal.

**The band is therefore fixed to `low`, 0.040-0.090 sensor cyc/px (7.8-17.6 cy/mm)**,
which sits below every candidate cutoff at every aperture in the ladder, so it carries
texture contrast over noise floor with the roll-off excluded by construction. It is
the same band, and for the same reason, that Amendment 4 fixed for focus scoring.

**What equalisation then costs, measured.** f/18 sets the target at every one of the
six ROIs, with no reordering:

| ROI | f/11 floor x | f/14 floor x | knee ratio before | after |
| --- | --- | --- | --- | --- |
| 0 | 1.84 | 1.67 | 5.81 | 3.16 |
| 1 | 1.60 | 1.47 | 4.45 | 2.78 |
| 2 | 1.65 | 1.48 | 5.59 | 3.39 |
| 3 | 1.79 | 1.50 | 5.45 | 3.04 |
| 4 | 2.23 | 1.55 | 6.10 | 2.73 |
| 5 | 1.63 | 1.51 | 5.80 | 3.55 |

The floor rises by 1.47x to 2.23x, which is a real but modest cost. **The residual
knee-band ratio of 2.7x to 3.6x is not a failure to equalise: it is the roll-off
difference between f/11 and f/18, which is precisely what the ladder exists to
measure.** Before equalising, that residual was confounded with a 1.6x to 2.2x
exposure artefact; after, it is not.

**A units error I made and caught, recorded because it changes the number by 6x.**
`xspec.py` indexes its bias surface by *amplitude* SNR, sigma_signal over
sigma_noise, at about 11.4 points of bias per e-fold. Everything in this amendment is
a *power* ratio. Amplitude is the square root of power, so the slope in power terms is
**5.7** points per e-fold, not 11.4. The differential bias across the primary arm is
therefore:

| read from | ratio | differential bias |
| --- | --- | --- |
| low band, the artefact alone | 1.72x | **3.1 points** |
| knee band, contaminated by the signal | 5.69x | 9.9 points |

against a 28.07-point H2-H3 separation. My first pass wrote 18.6 points, from the
contaminated band and the wrong exponent. Both errors pushed the same way, toward
declaring the lane hopeless.

**And this is an extrapolation, not a measurement, and is not to be used as a
correction.** `xspec.py`'s surface spans amplitude SNR 1 to 15; the low band here
sits at amplitude 31 to 74, well outside it, on a texture whose spectral slope was
not the one planted. The figures above size the problem. The commissioning battery
measures the bias where the ladder actually sits, and **its numbers supersede these.**

### Amendment 6a — condition A4 is already satisfied, by evidence that quotes no cutoff

Falls out of the same survey, and is recorded here because it is a result rather than
a change. `src/a4_evidence.py`, `out/a4-evidence.txt`.

A4 asks whether f/5.6 and f/8 show a texture-limited knee. That is answerable without
estimating any cutoff, which is worth doing while the estimator's bias is still
uncommissioned: excess power in 50.8-64.5 cy/mm lies above every candidate cutoff at
f/14 and f/18 and below every candidate cutoff at f/5.6 and f/8. Excess as a fraction
of the floor, median over six ROIs, all six agreeing in sign:

| f/5.6 | f/8 | f/11 | f/14 | f/18 |
| --- | --- | --- | --- | --- |
| 0.557 | 0.708 | 0.823 | 0.083 | **-0.021** |

f/5.6 and f/8 have not reached the floor; f/14 and f/18 have. **A4 is consistent with
section 2.3, on a prediction made before the data existed.** f/18's -0.021, a value
indistinguishable from zero, is a second and unplanned result: it says the floor
estimator is unbiased, since the excess it reports above the cutoff is nil.

f/11 reads 0.823, not at floor. Section 2.3 already registered that band as straddling
f/11's two candidates, so this is **undecided by construction** and is not read as
evidence for H3. It is recorded, not interpreted.

### Amendment 6b — the equalisation is commissioned, and it works

`src/equalise.py`, `out/equalise-selftest.txt`. Amendments 5 and 6 asserted two things
about equalisation without testing either. Both are now tested.

**(a) The arithmetic.** The prescription `add_var = scene/target - floor` is only
valid if adding spatially white noise of variance `v` raises the measured PSD floor by
exactly `v`. Measured:

| added v | floor rise | rise / v |
| --- | --- | --- |
| 500 | 475.4 | 0.951 |
| 2000 | 1955.5 | 0.978 |
| 8000 | 7936.1 | 0.992 |

Confirmed, and the small shortfall is understood: the floor is read from the top of
the band, which still holds a little scene power, so the *baseline* floor is slightly
over-read and the ratio approaches 1 as `v` grows past it.

**(b) The claim that actually matters.** Two copies of one synthetic scene with the
*same* planted cutoff, degraded to low-band SNR 170 and 19 — a 8.9x power ratio,
deliberately larger than the 1.72x the real ladder shows. Any difference in recovered
`f_c` is bias and nothing else. Twelve replicates:

| arm | low-band SNR | bias | sd |
| --- | --- | --- | --- |
| quiet, as captured | 170 | -7.77% | 1.88 |
| loud, as captured | 19 | -17.53% | 2.51 |
| quiet, equalised | 19 | -18.62% | 1.88 |
| loud, unchanged | 19 | -17.53% | 2.51 |

**Differential bias falls from 9.77 points to 1.09 points**, a factor of 9.

**The potency control is the part that makes this mean anything.** "After equalising
the biases agree" is worth nothing unless "before equalising they did not" — the
lesson of `xspec.py`'s test 4, where a hard band limit made two arms look identical
and certified nothing. The registered gate is that the un-equalised gap must exceed
3.0 points; it is 9.77.

**A measured slope, in the right units and on the right lattice, replacing an
extrapolation.** Amendment 6 quoted 5.7 points per e-fold of power ratio, carried
across from `xspec.py`'s amplitude-indexed surface. Here the same quantity is measured
directly: 9.77 points across a 9.0x power ratio is **4.4 points per e-fold**. Applied
to the real ladder's 1.72x, the expected differential bias is **2.4 points** against a
28.07-point separation. The extrapolation was the right order and slightly
pessimistic, which is the direction one wants to be wrong in.

**What this does not show, stated because the residual is not zero.** 1.09 points
remain. Equalising the low band equalises the floor relative to the texture, but the
estimator also sees the roll-off's own shape, and two apertures genuinely differ
there. On real data that residual is entangled with the signal. This is precisely why
Amendment 5 registered **both** arms and required them to be compared rather than
averaged.

---

### Amendment 7 - the texture slope was an assumption, and a new threat T6

Three things are recorded here. The subject's spectral slope is now measured rather
than assumed; the bias depends on it, in the direction predicted before the run; and
a threat specific to a *woven* subject, absent from T1-T5, is registered, tested and
retired for the two apertures that carry the measurement.

**The fabric's MEASURED low-band slope is alpha = 3.126, ROI-to-ROI sd 0.294.**
`src/slope_survey.py`, `out/slope-survey.txt`. Fitted as `log P = a - alpha log f`
over the low band 0.040-0.090 sensor cyc/px with the noise floor subtracted, at each
cell's own best focus, over 30 (ROI, aperture) pairs.

> **Read Amendment 7a before using this number.** It is a *measured* slope, and the
> *object* slope that synthetic work must plant is 2.26 to 2.52, not 3.126. Two
> claims below are superseded there and are marked where they appear.

| aperture | mean alpha |
| --- | --- |
| f/5.6 | 3.402 |
| f/8 | 3.080 |
| f/11 | 2.949 |
| f/14 | 3.031 |
| f/18 | 3.168 |

**~~Every synthetic test in this lane planted 2.2.~~ SUPERSEDED by Amendment 7a.**
The claim that 2.2 "was never the subject's" was wrong: as an *object* slope 2.2 is
within 0.06 of the inferred value. T3 registered that the subject spectrum is not flat
and argued the ratio cancels it; that argument is untouched. What was never checked is
whether the *estimator's bias* depends on the slope. It does, and that part stands.

**~~The slope is aperture-independent, which is the load-bearing part.~~ SUPERSEDED
by Amendment 7a: it is aperture-DEPENDENT, at p = 0.031.** Amendment 6's equalisation
assumes that below the cutoff the spectrum differs between apertures only in scale, so
that matching the low-band SNR matches the noise and not the optics. Between-aperture
spread of the mean slope is **0.1553**; within-aperture, ROI to ROI, it is **0.2467**;
ratio **0.63**. That comparison is the error: the same six ROIs are measured at every
aperture, so ROI-to-ROI variation is a shared block effect that does not inflate the
between-aperture difference at all. Discarding the pairing hid a real effect.

**A potency control, and two failures before it worked.** A verdict of "the spreads
are comparable" is worth nothing from a test that cannot tell them apart.

1. *Floor subtraction as the disturbance.* Moved the fitted slopes by 0.003. This is
   not a failed control but a measurement: in the low band the signal sits 1000-5000x
   above the floor, so floor subtraction cannot matter there. It retires the worry
   that the low band might be floor-contaminated - the worry that motivated choosing
   that band in Amendment 6.
2. *A planted aperture ramp, specified by span.* The fit recovered the plant with
   **0.0000** error and the verdict still did not flip. A linear ramp across five
   points has a standard deviation of only **0.354** times its span, so a ramp of span
   0.5 is a spread of 0.177 - smaller than the within-aperture spread it had to beat.
   The lesson is general: **specify a plant by the statistic the test compares.** Here
   the test compares standard deviations, so the plant must be sized in standard
   deviations.
3. *The same ramp, specified by standard deviation.* Recovered exactly, verdict
   flipped. The control passes.

**The bias is worse on a steeper texture, as predicted in writing beforehand.**
`src/slope_bias.py`, `out/slope-bias.txt`. Low-band SNR held at 2000 by adding noise
so the slope is the only variable, planted `f_c` = 0.1273 sensor cyc/px, 16 replicates
per point. The prediction registered in the script's docstring before it was ever run
was that the bias becomes **more negative** as alpha grows, because a steeper spectrum
reaches the floor at a lower frequency.

| alpha | bias | sd |
| --- | --- | --- |
| 2.000 | -0.44% | 1.05 |
| 2.200 | -1.53% | 2.01 |
| 2.600 | -3.97% | 1.44 |
| 3.000 | -3.43% | 1.88 |
| 3.126 | -4.24% | 1.05 |
| 3.400 | -4.24% | 1.05 |
| 3.800 | -5.06% | 1.44 |

**-2.35 points per unit of alpha.** At 2.2, what every earlier test planted: -1.53%.
At 3.126, what the fabric is: -4.24%. **Every bias figure this lane quoted before
today is optimistic by about 2.7 points.**

**The individual estimates are quantised, and the sweep says how much that matters.**
`src/slope_quant.py`, `out/slope-quantisation.txt`. Two rows above are identical to
four decimals in both mean and sd, which does not happen by chance across 16
independent replicates. The cause is quantisation: the estimator returns a radial bin
index, and one radial bin is **4.340%** of `f_c`. The smallest gap between any two
distinct bias values is **0.2713** points, which is exactly one bin divided by 16
replicates - the signature of a quantised estimator averaged over replicates.

The means are still usable, because replicate standard deviations are 0.24-0.46 bins,
so replicates scatter across adjacent bins and the mean interpolates. Standard error
per row is 0.263-0.503 points, so the endpoint difference of 4.61 points is **10.4
sigma**. But a single row-to-row step of about 0.8 points is only 1.8 sigma.
**Registered rule for quoting this result: quote the fitted slope and the endpoints;
do not quote row-to-row differences.** The tie at alpha 3.126 and 3.400 is the grid,
and the non-monotone step from 2.6 to 3.0 is replicate scatter.

**An unplanned second result, and it is about the ladder rather than the sweep.** One
radial bin being 4.340% of `f_c` is the estimator's intrinsic resolution on a single
(ROI, aperture) cell, and that applies to the real ladder, not only to this synthetic.
Section 2.2 separates H2 from H3 by 28.07% in `f_c*N`, so **the hypotheses lie 6.5
bins apart**, and averaging over the six ROIs would give a per-aperture standard error
near 0.58 points if the real data scatter like the synthetic. Resolution is not what
threatens this lane. The bias is.

### T6 - the subject is a weave, and a weave is periodic

**Registered here rather than in section 4 because it was not thought of then.** T1-T5
all treat the subject spectrum as smooth: a power law rolled off by a diffraction MTF.
A weave is periodic, and a periodic structure puts discrete peaks in the spectrum. If
a harmonic lands near the cutoff, the spectrum can fall to the floor at the end of the
roll-off and then be lifted back out of it, so the last detectable bin is the harmonic
and not the cutoff. That biases `f_c` **high**, toward H3. It is the only mechanism
found in this lane that pushes opposite to T1 and to the SNR bias, so it cannot be set
aside as conservative.

**Test and result.** `src/weave_peaks.py`, `out/weave-peaks.txt`. Reads the saved
radial PSDs; estimates no cutoff. A bin counts as a re-emergence if it stands 3 sigma
above the floor - the same rule `m5_lib.knee` uses - at a frequency **above** the one
where that spectrum first reaches the floor. Danger zone 30-55 cy/mm, bracketing the
H2 and H3 candidates at f/14 and f/18.

| | measured |
| --- | --- |
| bins examined, 6 ROIs x 5 apertures | 1350 |
| false positives expected at 3 sigma | 1.8 |
| re-emergent bins observed | 1 |
| most cells sharing one frequency | 1 of 30 |

The single detection is ROI 4 at f/5.6, 54.5 cy/mm, standing 0.166 of the floor. **The
count is below chance and nothing repeats at a fixed frequency**, which is the
discriminating test: a genuine weave harmonic is a property of the fabric, so it must
sit at one frequency and recur across ROIs and apertures. An isolated bin is what
chance looks like. f/5.6 is in any case an out-of-band control under section 2.3, not
part of the measurement.

**Sensitivity, stated rather than implied.** The smallest re-emergence this null
covers is 0.234 of the floor at 29.7 cy/mm, 0.208 at 36.1, 0.195 at 43.7 and 0.170 at
52.3, set by the number of samples in each radial bin. A harmonic smaller than that is
invisible here - **and equally invisible to the crossing estimator, which uses the same
rule**, so it cannot move the measurement either.

**Three control failures, all of them mine, all caught by the control.** Recorded
because the third is the one that would have produced a false all-clear.

1. *Wrong reference.* Peaks were first measured against the power law extrapolated from
   the low band. Above the cutoff that extrapolation carries no roll-off and so sits
   far above the data; planted harmonics of 3x, 4x and 8x were **all missed**. The
   reference has to be the floor, because the floor is what the estimator compares
   against.
2. *Wrong demand.* The control then required the detector to see a re-emergence of 30%
   of the floor at a frequency where its own threshold was 50%. But the detector shares
   the estimator's rule, so a harmonic it cannot see is one the estimator cannot see;
   demanding more sensitivity than the estimator has tests the wrong thing. Replaced by
   a threshold calibration: plant at 1.5x the local threshold and require a hit, at
   0.5x and require a miss.
3. *Wrong position.* The calibration planted at fixed frequencies of 36 and 44 cy/mm,
   which on that spectrum lie **below** where it first reaches the floor, so the
   re-emergence rule excluded them by construction and the control read FAIL against a
   detector that was behaving correctly. Plant positions must be derived from the
   spectrum being planted into. With that fixed the control passes at all three
   positions, hit and miss.

**Verdict: T6 is retired for f/14 and f/18**, the two apertures section 2.3 calls the
measurement, at the stated sensitivity. It is not retired in general and the test is
kept in the reduction, because passing on this capture is not passing on every capture.

---

### Amendment 7a - the low band is not free of the optics, and Amendment 7 mis-stated its own headline

Amendment 7 was written and machine-checked before this was noticed. Two of its claims
are wrong and are corrected here rather than edited away. The error was found by its
own checker: a tolerance disagreement on an unrelated figure forced a reading of the
per-ROI table, and f/18 turned out to be steeper than f/11 in every single ROI.

**The measured slope IS aperture-dependent.** `src/slope_paired.py`,
`out/slope-paired.txt`. Amendment 7 compared the spread of the five aperture means
(0.1553) against the mean ROI-to-ROI spread within one aperture (0.2467) and read
independence from 0.1553 <= 0.2467. **That test throws away the pairing.** The same
six ROIs are measured at every aperture, so ROI-to-ROI variation is a shared block
effect and contributes nothing to the difference between apertures. Removing the ROI
main effect first:

| aperture | mean alpha | effect | t |
| --- | --- | --- | --- |
| f/5.6 | 3.402 | +0.2761 | +3.91 |
| f/8 | 3.080 | -0.0462 | -0.65 |
| f/11 | 2.949 | -0.1773 | -2.51 |
| f/14 | 3.031 | -0.0951 | -1.35 |
| f/18 | 3.168 | +0.0425 | +0.60 |

Residual sd 0.1730 on 20 df, standard error of each effect 0.0706. And the test that
assumes nothing at all: **f/18 minus f/11 is positive in 6 of 6 ROIs**, mean
difference +0.2198, sign-test **p = 0.031**.

**There is no aperture in this ladder at which the low band is free of the optics.**
This is the substantive finding and it corrects Amendment 6, not only Amendment 7. The
incoherent diffraction MTF falls monotonically from zero frequency; it has no flat
region. Amendment 6 chose the low band because it sits *below every candidate cutoff at
every aperture* and treated it as optics-free. **Being below the cutoff and being
unaffected by it are different things.** Planting an object slope of exactly 3.000 and
fitting the same low band returns:

| aperture | f_c H2 | steepening H2 | f_c H3 | steepening H3 |
| --- | --- | --- | --- | --- |
| f/5.6 | 0.5404 | +0.3349 | 0.6921 | +0.2525 |
| f/8 | 0.3783 | +0.5131 | 0.4844 | +0.3805 |
| f/11 | 0.2751 | +0.7740 | 0.3523 | +0.5608 |
| f/14 | 0.2161 | +1.0879 | 0.2768 | +0.7675 |
| f/18 | 0.1681 | +1.6190 | 0.2153 | +1.0942 |

Pure model arithmetic; no measurement enters. The fitting harness was verified first:
with the MTF removed it recovers a planted index to **1.7e-11**.

**A NaN walked through that harness gate on the first attempt.** The check passed
`n_eff = 1e9` intending "no MTF", but a large effective f-number is a *tiny* cutoff,
so the MTF was zero everywhere, the fit returned `nan`, and the gate `nan > 1e-6`
evaluated False and printed "harness OK". No MTF means an *infinite* cutoff, `n_eff`
approaching zero. Recorded because the failure mode is general: **a numerical gate
must test for finiteness explicitly, or NaN satisfies it silently.**

**The object slope is 2.26 to 2.52, and 2.2 was approximately right all along.**
`src/slope_object.py`, `out/slope-object.txt`. `equalise._scene` builds amplitude as
`r**(-slope/2)` and *then* multiplies by the MTF, so its `slope` argument is an
**object** slope. Amendment 7 put the measured value into it. Inverting each measured
per-aperture slope through that aperture's own MTF:

| aperture | measured | object H2 | object H3 |
| --- | --- | --- | --- |
| f/5.6 | 3.402 | 3.0671 | 3.1494 |
| f/8 | 3.080 | 2.5665 | 2.6991 |
| f/11 | 2.949 | 2.1745 | 2.3877 |
| f/14 | 3.031 | 1.9428 | 2.2633 |
| f/18 | 3.168 | 1.5493 | 2.0741 |

Mean object slope **2.260** under H2, **2.515** under H3 - within **0.060** of the
long-assumed 2.2 under H2. **Amendment 7's claim that every earlier synthetic planted
the wrong slope is withdrawn.** Synthetic work in this lane must plant an object slope
near **2.3**, swept over 1.9 to 2.7.

**Amendment 7's bias-versus-slope result survives, with its axis relabelled.** The
measurement that bias moves **-2.35 points per unit of slope** is unaffected, because
`slope_bias.py` swept `_scene`'s argument, which is the object slope. What changes is
where the subject sits on that axis: near 2.3, not 3.126. So the applicable bias is
about **-1.8%**, not -4.24%, and **Amendment 7's figure is pessimistic rather than
optimistic.** The lane is not endangered by the error; the number was simply wrong.

**A residual confound remains, and its sign identifies it.** The inferred object
slopes above are not constant - they fall monotonically from 3.07 at f/5.6 to 1.55 at
f/18 under H2. The subject cannot change with aperture, so something is left over.
Removing the full MTF steepening **overshoots**: observed steepening across f/11 to
f/18 is +0.2198 where diffraction alone predicts +0.5335 (H3) to +0.8450 (H2). A
second aperture-dependent effect is therefore present **with the opposite sign to
diffraction**. The registered candidate is **T1, the primary threat**: wider apertures
have shallower depth of field, so more of the ROI is defocused, and defocus steepens
the spectrum - largest at f/5.6, smallest at f/18, exactly the sign required. This is
the first *quantitative* handle this lane has on T1's size, and it was obtained
without a defocus sweep.

**f/5.6 is the odd one out and diffraction predicts the opposite.** Diffraction makes
f/5.6 the *shallowest* measured slope, its cutoff being furthest above the band. It is
instead the steepest, at 3.402, with the largest effect in the blocked table
(+0.2761, t = +3.91). That is T1 again, and it is consistent with section 2.3 already
treating f/5.6 as an out-of-band control rather than a measurement.

**What this costs the equalised arm, stated rather than absorbed.** Equalising the low
band assumes the band's *shape* is common and only its *level* differs. That
assumption is now measurably false. A residual slope difference of 0.2198 across a
band spanning 2.25x in frequency tilts one end relative to the other by **1.195x**,
against a level ratio of **1.72x** being corrected - so the shape error is about
**27%** of the level difference. Not negligible, not dominant. It is carried as an
uncertainty on the equalised arm, and it is a further reason Amendment 5 required both
arms to be reported rather than averaged.

### Amendment 8 - the bias does not cancel, so the ladder stops inverting and compares forward

Condition A1' asked whether the crossing estimator's bias cancels in the product
`f_c . N`. It does not, and the phrasing was loose enough to hide why. If the estimator
returns `f_c_hat = f_c (1+b)` then `K = mean(f_c_hat . N) = K_true (1+b)` and
`B_hat = B/(1+b)`. Nothing cancels anywhere. The bias passes through the product
undiminished and lands entirely on `B`. The only real questions are how big it is
against the **28.07%** that separates the hypotheses, and whether it is the same at
every aperture.

`src/bias_ladder.py` answers both by synthesising a ladder at each hypothesis' own
cutoffs, with the object slope Amendment 7a inferred for that hypothesis, degraded
to each aperture's measured low-band SNR, and running the real estimator over it.
Predictions P1-P5 were written into its docstring before the first run.

**P1 holds.** `f_c` is read low in all 12 measured cells, worst -16.90%, best -5.12%.
**P2 holds.** `B` is therefore inferred high, in every arm.

**P3 IS FALSIFIED.** I predicted the inflation of `B` would stay under 5%, reasoning
from Amendment 7a's applicable bias near 1.8%. It reaches **13.02%** - seven
times my estimate, and **46.4%** of the gap between the hypotheses. The reason is
in the harness table below: the bias grows with the cutoff, and Amendment 7a
quoted a single number for a quantity that is not a single number. The registered
falsifier was P4 failing or the error exceeding 14%, and neither happened, so the
lane continues - but the analysis it was going to use does not.

| planted `f_c` | recovered | ratio | low-band SNR |
| --- | --- | --- | --- |
| 0.1200 | 0.1215 | 1.0128 | 4794 |
| 0.1800 | 0.1761 | 0.9783 | 7845 |
| 0.2500 | 0.2403 | 0.9612 | 9747 |
| 0.3000 | 0.2845 | 0.9483 | 10505 |

The noise floor in that table is pushed far below anything the ladder sees - SNR
4794 to 10505 against 1730 to 2802 on the real ladder - and the ratio still runs from
1.0128 at `f_c` 0.12 down to 0.9483 at 0.30. A cutoff-dependent bias with almost no
noise to blame is the one kind that does not divide out of a ladder: it tilts
`f_c . N` across the apertures and so tilts the fitted `B`.

**P4 passes, and hides the result.** Asking only which side of the boundary
`B_hat` falls on gives four passes out of four. Asking by how much, in units of the
replicate scatter, gives this.

| built at | arm | `B_hat` | s.e. | distance from boundary | sigma |
| --- | --- | --- | --- | --- | --- |
| H2 | native | 3.2951 | 0.0067 | 0.5560 | 83.2 |
| H2 | equalised | 3.3172 | 0.0061 | 0.5780 | 94.4 |
| H3 | native | 2.6853 | 0.0105 | 0.0539 | 5.2 |
| H3 | equalised | 2.7147 | 0.0106 | 0.0245 | 2.3 |

The boundary sits at `B` = 2.7391. **H2 clears it by 94 sigma and H3 by
2.3.** That asymmetry is the finding. Under H3 every cutoff sits higher, nearer
the lattice Nyquist, exactly where the harness shows the bias is largest, and
f/11's replicate scatter under H3 is 3.6 times its scatter under H2. The lane's weak
case is H3, and on the inverse analysis it is close to being no case at all.

**P5 is falsified too, and in the interesting direction.** Equalising was expected
to flatten `f_c . N`. It does the opposite: 2.36% native becomes
3.19% equalised. Equalisation can only add noise, so it moves every
aperture toward the worst one's bias rather than toward a common value, and the
aperture whose bias moves furthest is the one with the highest cutoff. This does
not retire the equalised arm - Amendment 5 requires both arms reported - but it
removes the reason to prefer it, and Amendment 6's equalisation is now a control
on the SNR explanation rather than the primary analysis.

#### The registered change: compare forward, do not invert

The inverse analysis pays the bias in full because the bias sits between the
measurement and the answer. The forward comparison asks the other question: what
cutoff would the estimator **report** under each hypothesis, and how does that
compare with what it did report. The bias is then on both sides and cancels by
construction rather than by subtraction. Read off the same runs, with no new
simulation:

| arm | ap | reported under H2 | reported under H3 | gap | sigma |
| --- | --- | --- | --- | --- | --- |
| native | f11 | 0.2524 | 0.3004 | 16.0% | 14.2 |
| native | f14 | 0.2020 | 0.2520 | 19.9% | 42.4 |
| native | f18 | 0.1595 | 0.1982 | 19.5% | 40.9 |
| equalised | f11 | 0.2486 | 0.2928 | 15.1% | 14.1 |
| equalised | f14 | 0.2009 | 0.2500 | 19.6% | 34.7 |
| equalised | f18 | 0.1595 | 0.1982 | 19.5% | 40.9 |

Combined separation **60.6 sigma** native, **55.5 sigma** equalised, against **2.3**
for the inverse analysis on its weakest arm. The hypotheses stand 15% to 20%
apart in the quantity the estimator actually reports, and that gap does not
require knowing the bias - only that the bias is the same for a predicted cutoff
and a measured one at the same frequency, which is the one thing about it that
is certain.

**These sigmas are an upper bound and must not be quoted as a forecast.** The
scatter above is replicate-to-replicate on statistically identical synthetic
scenes. The real measurement's scatter is ROI-to-ROI on one piece of fabric and
will be larger, plausibly much larger. What the table establishes is the ordering
- that the forward comparison is the stronger test - not the margin the real data
will have. The real margin is measured by `ladder.py` and by nothing before it.

**Registered now, before it touches real data:** the ladder's primary statistic
is the forward comparison. For each hypothesis, predict the cutoff the estimator
would report at each aperture by running the estimator over a synthetic scene at
that hypothesis' cutoff, that aperture's measured SNR, and the object slope
Amendment 7a infers for that hypothesis; then compare against the measured
cutoffs by chi-squared over the primary arm, with the ROI-to-ROI scatter as the
denominator. The inverse `B_hat` continues to be reported, because it is the
interpretable number and because a large disagreement between the two would be
evidence that the forward model is wrong. It is no longer the statistic that
decides.

#### f/11 has no margin under H3, in the units that decide it

A scene planted at lattice cutoff `fc_lat` reads back at `fc_lat / LATTICE_PITCH_PX['GQ']`,
so the largest cutoff the GQ lattice can represent is `0.5 / sqrt(2)` = **0.35355**
sensor cyc/px. This is not a property of the simulation; it is the lattice's
Nyquist and it applies to the real measurement identically.

| ap | `f_c` H2 | / Nyquist | `f_c` H3 | / Nyquist | reachable |
| --- | --- | --- | --- | --- | --- |
| f5.6 | 0.5404 | 1.5284 | 0.6921 | 1.9575 | neither |
| f8 | 0.3783 | 1.0699 | 0.4844 | 1.3702 | neither |
| f11 | 0.2751 | 0.7781 | 0.3523 | 0.9965 | both |
| f14 | 0.2161 | 0.6114 | 0.2768 | 0.7830 | both |
| f18 | 0.1681 | 0.4755 | 0.2153 | 0.6090 | both |

**Under H3, f/11's cutoff is 0.35% below the GQ lattice's Nyquist.** Section 2.3 called f/11's
H3 margin "+0.24 cy/mm - not a margin". This says the same thing in the units
that decide it: under H3 the lattice cannot resolve f/11's cutoff at all. f/14
and f/18 are the measurement, as registered, and f/5.6 and f/8 are unreachable
under either hypothesis, which is exactly the out-of-band role section 2.3 gave
them.

### Amendment 9 - all three hypotheses are rejected, and B is measured instead

Amendment 8 registered the forward comparison as the primary statistic and
`ladder.py` ran it. It rejected **both** live hypotheses, with every residual
of the same sign: the real cutoffs sit ABOVE what either predicts.

| ap | n | measured `f_c` | s.e. | H2 predicted | z | H3 predicted | z |
| --- | --- | --- | --- | --- | --- | --- | --- |
| f11 | 6 | 0.2946 | 0.0044 | 0.2482 | +10.19 | 0.3004 | -1.18 |
| f14 | 6 | 0.2753 | 0.0026 | 0.2020 | +26.91 | 0.2496 | +8.97 |
| f18 | 6 | 0.2311 | 0.0030 | 0.1640 | +21.89 | 0.2023 | +9.37 |

Chi-squared over the arm as registered: H2 1307.20, H3 169.53, on 3 terms. H3 is the better of the two and
is still rejected outright.

A rejection in which every residual shares a sign is not a coin landing
badly; it is a parameter set wrongly. This amendment records what was wrong,
retracts one diagnosis that turned out to be a consequence rather than a
cause, and replaces the two-way test with a measurement of `B` itself.

#### 9.1 f/11 is out of band, so the primary arm was mis-scoped

The out-of-band detector is not a judgement call. `knee_model_fit` reports
`above_reach` when the fitted cutoff exceeds the highest frequency the
lattice can measure, and M5's commissioning validated it at 36/36 with no
false alarms. Asked about this data it says:

| ap | `above_reach` | crossing `f_c` | model-fit `f_c` | floor slope |
| --- | --- | --- | --- | --- |
| f5.6 | 6/6 | 0.2771 | 0.4322 | -3.217 |
| f8 | 6/6 | 0.2955 | 0.4033 | -3.210 |
| f11 | 6/6 | 0.2946 | 0.3685 | -3.618 |
| f14 | 0/6 | 0.2753 | 0.3043 | -0.374 |
| f18 | 0/6 | 0.2311 | 0.2554 | -0.028 |

**f/11 is out of band, 6/6.** Section 2.3 registered it as "a supporting
point" whose H3 margin "is not a margin", and Amendment 8 sharpened that to
0.35% below the lattice Nyquist. The data has now demoted it the rest of the
way: at f/11 the crossing rule is not reporting a diffraction cutoff at all.

An independent statistic agrees without being asked. The fitted floor slope
is -3.22, -3.21 and -3.62 at the three out-of-band apertures - steeply
negative, which is signal still falling, not a floor - against
-0.374 and -0.028 at f/14 and
f/18, which are flat. The three apertures whose guard fires are exactly the
three that never reach a floor, and their crossing cutoffs cluster at
0.2771, 0.2955, 0.2946 - the fabric's own texture limit, which is a
property of the subject and not of the aperture.

**The chi-squared that rejected H2 and H3 included f/11 and should not
have.** That does not rescue either hypothesis - section 9.3 rejects them
far more decisively on the two apertures that are in band - but the
mis-scoping is recorded as an error in the registered analysis, not
silently corrected.

#### 9.2 R2 was mis-scoped by me, and both scores are reported

R2 was registered as "`f_c` falls monotonically with f-number in every
ROI", over all five apertures. The registered wording does not say whether
a tie counts as falling, and the two readings differ:

* ties allowed, which is how `ladder.py` scored it: **1/6**
* ties disallowed, the literal reading of "falls": **0/6**

Either way it failed. The ambiguity is not a loophole worth arguing over,
because the ties are an artefact of the instrument rather than of the
subject: the crossing rule reports a radial bin, bins are 4.34% of `f_c`
wide, and two apertures whose cutoffs differ by less than a bin must report
the same number.

Over the three-aperture primary arm R2 is **6/6** and over the
two in-band apertures **6/6**, both under the strict reading.

**Every tie and every rise involves only f5.6, f8, f11.** The f/11 -> f/14 -> f/18 chain
never ties and never rises in any ROI. The prediction failed exactly and
only where section 9.1 has just shown the estimator is not measuring optics.

The registered scoring is the one that counts and it failed. But the
prediction was unsatisfiable as written, and that is my error rather than
the subject's: an aperture whose cutoff lies beyond the lattice cannot roll
off inside the band, so f/5.6 and f/8 cannot be monotone with anything. A
prediction that no possible sensor could satisfy tested nothing. Both
numbers are quoted here permanently so the failure cannot be read off as a
success by quoting only the primary arm.

#### 9.3 Retraction: the "shape excess" was a wrong B, not a wrong shape

`ladder_diag.py` compared the real spectrum against the model's with each
normalised by its own low band, so only shape was compared, and found the
real spectrum running above the model through the roll-off. It named the
candidate causes before testing them and concluded the real MTF rolls off
more slowly than ideal diffraction. **That conclusion is withdrawn.** It was
computed at H3's `B`, and H3's `B` is wrong. Rebuilt at the fitted `B`, in
the same bins with the same normalisation, the excess collapses:

| ap | peak real/synth at H3 | peak at fitted `B` |
| --- | --- | --- |
| f14 | 1.48 | 1.19 |
| f18 | 2.17 | 1.16 |

The registered threshold was that both peaks fall below 1.25, and both do.
The diffraction MTF shape was never in trouble; the cutoff it was evaluated
at was. This is recorded as a retraction because the earlier reading would
have sent the lane after a new optical model it did not need.

#### 9.4 `B` measured two ways, and why they agree

`B` is the effective-f-number multiplier, `N_eff = B N`. All three
hypotheses of section 2.2 carry the same magnification - `(B-1)p` is
2.7199, 2.7197, 2.7199
- so they differ only in pupil magnification through `B = 1 + m/p` with
`m` = 2.7198. **Measuring `B` measures `p`.**

| route | what it assumes | what it pays | `B` |
| --- | --- | --- | --- |
| A model fit | diffraction shape | no crossing bias | 2.0888 +- 0.0219 |
| B forward | diffraction shape | the bias, on both sides | 2.11 |

The two routes agree to 0.0212 in `B`. That agreement was checked
rather than admired. Route A calls `knee_model_fit`, whose `pixel_mtf`
argument defaults to true, so it models the 5.12 um photosite; route B
synthesises through `equalise._scene`, which applies `mtf_diffraction` and
nothing else, so it does not. Refitting route A with the photosite term off
is therefore a like-for-like comparison, and it was registered in advance
that `B` must RISE:

| route A setting | f/14 `B` | f/18 `B` | mean `B` | distance to route B |
| --- | --- | --- | --- | --- |
| photosite on | 2.1466 | 2.0309 | 2.0888 | 0.0212 |
| photosite off | 2.1697 | 2.0444 | 2.1070 | 0.0030 |

Modelled like for like the two routes differ by 0.0030. The entire original disagreement was
the photosite, and it is now accounted for rather than merely small. An
independent estimator that does not pay the crossing bias and a forward
comparison that pays it on both sides land in the same place.

#### 9.5 One `B` does not fit both apertures

| ap | route A `B` | route B `B` | route B |z|<=1 | implied `p` |
| --- | --- | --- | --- | --- |
| f14 | 2.1466 +- 0.0186 | 2.17 | 2.13 to 2.19 | 2.3246 |
| f18 | 2.0309 +- 0.0204 | 2.06 | 2.02 to 2.08 | 2.5658 |

The gap is +0.1157 by route A and
+0.11 by route B - two routes, one answer - and the intervals
do not overlap. **The apparent `B` falls as the aperture closes**, which a
single bellows factor cannot do.

The photosite is excluded as the cause, and was excluded by a test that
expected to fail so that a pass would have been news. Removing the term
moves the gap by only 0.0096, against a registered
threshold of 0.05. A term already in the model cannot explain a residual the
model still has.

**What this lane cannot decide.** The surviving candidates are residual
defocus - registered as threat T1 - lens aberration, and vibration. All
three inflate the apparent `B`, and all three inflate it more at the wider
aperture: defocus and aberration because they worsen as the pupil opens, an
absolute blur because diffraction has less roll-off of its own to hide
behind. They share a sign, so two in-band apertures cannot separate them,
and section 9.1 has just removed the third. **This lane does not identify
which, and no later section should claim it did.**

#### 9.6 What survives: a one-sided bound, which is what the evidence supports

Because every surviving candidate biases `B` upward, the aperture least
contaminated by them bounds the true value from above. That is a weaker
claim than a two-sided interval and it is the one the evidence actually
supports - a two-parameter fit to two apertures would have zero degrees of
freedom and could not be wrong.

**`B` <= 2.0309 +- 0.0204** (at f18, n = 6), hence **`p` >= 2.6383**.

| hypothesis | `B` | `p` | s.e. above the bound | verdict |
| --- | --- | --- | --- | --- |
| H1 | 3.7319 | 0.9956 | +83.2 | EXCLUDED |
| H2 | 3.0763 | 1.3099 | +51.1 | EXCLUDED |
| H3 | 2.4020 | 1.9400 | +18.2 | EXCLUDED |

All three registered hypotheses are excluded, H3 - the survivor the lane was
built to test - by 18.2 standard errors. The pupil
magnification is larger than any of them assumed, so the bellows factor at
2.72x magnification is smaller, the true cutoff is higher, and
there is more recoverable detail at a given marked aperture than the
registered hypotheses allowed.

**Registered now, before anything acts on it:** the successor lane must
recover a third in-band aperture before the residual trend can be
attributed. f/16 sits between the two survivors and is in band under the
measured `B`; a capture at f/16 and f/22 would give four in-band points and
two spare degrees of freedom, which is the minimum that can distinguish a
defocus term from an absolute blur. Until then the one-sided bound is the
result.

---

## Amendment 10 - residual defocus is excluded, and by the opposite sign

Amendment 9 left one thing unresolved: apparent `B` falls as the aperture
closes, f/14 above f/18 by a gap that no candidate could be pinned on.
Threat T1 named residual defocus as the leading suspect, because f/14's
depth of field is shallower and an identical residual focus step therefore
costs more defocus there. This amendment closes T1. It is excluded, and not
by a bound that happened to come out small - by the direction of the effect,
which is opposite to the one T1 requires.

Four scripts, run in this order. Two of them failed as registered and both
failures are recorded here rather than repaired out of sight.

### 10.1 The direct test failed its own control

`defocus_b.py` walked the frame offset from -3 to +3 in each of the twelve
in-band cells, refitted `B` at every offset and fitted a parabola. Its
control C1 required the parabola vertex to sit within one frame of the
frame the focus map had already chosen.

| check | registered | measured | verdict |
| --- | --- | --- | --- |
| P8 | curvature positive at both apertures | -0.0149 and -0.0134 | FAIL |
| P9 | f/14 curvature exceeds f/18 | larger in magnitude, smaller in sign | FAIL as coded |
| P10 | gap below 0.05 after correction | +0.1467 at the vertices | FAIL |
| C1 | vertex within 1 frame of the focus map | worst +2.46 frames | VOID |

P9 has the same prose-versus-code split that 10.3 records for S3, and it is
noted here for the same reason. Its prose says the f/14 curvature exceeds
f/18, glossed as rising faster; the code compared the two signed values.
Under P8's premise that both parabolas open upward those are the same
comparison. Once the curvatures came out negative they are opposites, and
the two readings disagree. Nothing turns on it, because C1 voided the whole
group, but a discrepancy found and left unrecorded is one that gets
rediscovered as a contradiction later.

C1 failed, so P8 through P10 are not interpretable and **are not claimed**,
here or anywhere else. They are listed because a registered prediction that
is quietly dropped is indistinguishable from one that was never made.

The curvature is negative at 12 of 12 cells: fitted `B` is
**highest** near best focus and falls away on both sides. I read that at the
time as the estimator failing, on the reasoning that a fit which assumes a
diffraction-limited MTF has no business being trusted on a deliberately
defocused frame. That reading is retracted in 10.3. The reasoning was sound
and the conclusion was wrong.

### 10.2 What the voided test still established

`defocus_robust.py` asked what the per-offset values say about Amendment 9
regardless of where the true optimum lies, since they are measurements and
not fits to any theory of focus.

| question | measured | verdict |
| --- | --- | --- |
| does the exclusion of H3 survive an adversarial frame choice | the largest `B` any f/18 cell reaches at any offset is 2.0883, still 15.3 s.e. below H3 | PASS |
| could a frame-selection bias have made the gap | letting the two apertures take different offsets, the reachable gap spans +0.0878 to +0.1674 | PASS, never closes |

The gap keeps its sign at every offset held in common:

| offset | gap |
| --- | --- |
| -1 | +0.1175 |
| +0 | +0.1157 |
| +1 | +0.1271 |
| +2 | +0.1587 |

Within a single stack `B` swings by about 0.21 across the seven offsets, which is
larger than the gap under investigation. That the gap survives anyway is
because the swing is largely cell-specific and averages away over six ROIs,
while the gap does not.

**That conclusion rested on an unexamined premise**: that moving the frame
moves the estimator. A blind instrument would also have shown a gap that
survives every offset. Closing that is what 10.3 is for.

### 10.3 Commissioning the estimator against a known defocus

`defocus_sens.py` measures the estimator's defocus response on synthetic
data where the truth is known exactly. Each real in-band PSD is fitted once,
a clean PSD is regenerated from those parameters on the identical frequency
grid and bin counts, defocus is applied to that, and the fit is repeated.
Nothing but the defocus changes.

The defocused MTF is computed from first principles as the normalised
autocorrelation of the complex pupil, not from a published closed form.
Closed forms for the defocus MTF circulate with several different constants
inside the Bessel argument, and the wrong one would silently rescale the
wave axis and every number derived from it.

| check | registered | measured | verdict |
| --- | --- | --- | --- |
| S0 | pupil code matches `mtf_diffraction` at zero defocus, rms < 2e-3 | 7.482e-05 | PASS |
| S1 | round trip recovers the seeded cutoff to 1% | 0.016% worst | PASS |
| S2p | fitted `B` rises with defocus | it falls | FAIL |
| S5 | null control: 0.01 waves moves `B` under 0.01 | 0.0002 worst | PASS |
| S3 | a quarter wave moves `B` by more than 0.05 | 0.1009 at the least responsive ROI | PASS as worded |

**S3 was written two ways and they disagree.** The registered prose asks
whether the estimator moves `B` by more than 0.05 and glosses a pass as
"the estimator is not blind", which is a question about magnitude. The code
as first written also demanded the sign S2 predicted. Once that direction
turned out to be wrong the two readings separated, so both are reported and
the script prints both. The blindness question is the magnitude one and it
passes by a factor of 2.0 at the
worst cell. The signed reading fails for the same reason S2p fails and is
not independent evidence.

**An earlier run of this script failed and the failure was mine.** Run 1
multiplied the analytic diffraction MTF by the value returned from the pupil
code, which already contains that envelope, so the envelope was applied
twice. The signature was unmistakable in hindsight: fitted `B` jumped +0.51
at 0.05 waves, a defocus that is optically negligible. Run 1 is preserved at
`out/defocus-sens-run1.txt`. S5, the null control, was added afterwards
precisely because it is the check that would have caught it, and it now
stands permanently alongside S3: a positive control alone cannot tell a
sensitive instrument from one that lurches at any input.

**The measured response.** Defocus LOWERS fitted `B`, by
-1.7308 per wave over the monotone range
[0.0, 0.01, 0.05, 0.1, 0.15, 0.25, 0.4]. Lower `B` means a LARGER fitted cutoff, which is
the opposite of the naive expectation registered as S2. The reason is
visible in S4: the slope absorbs the defocus, alpha steepening from
2.3341 to 2.7708 over a quarter wave, and a
steeper scene term needs a wider diffraction term to trace the same curve.
The two free parameters trade, and the cutoff moves against the eye.

**This overturns 10.1's diagnosis.** The peak in `B` at best focus is not
the estimator failing. It is the estimator's genuine response, in the same
direction, measured where the answer is known. The real B-versus-offset
curves are defocus curves. C1 still stands as failed and P8 through P10 are
still not claimed, because P8 asked for a curvature sign now known to be the
wrong way round, and a registered prediction cannot be reinterpreted into a
pass after the fact.

### 10.4 The real curves match the calibrated law

`defocus_verdict.py` puts the twelve measured curvatures through the
synthetic law. The two ends were measured independently - the synthetic side
knows nothing about focus rails, the real side nothing about wavefronts - so
agreement is not built in anywhere.

| check | registered | measured | verdict |
| --- | --- | --- | --- |
| V1 | the law is quadratic, exponent in [1.8, 2.2] | abs(dB) = 3.3427 W20^2.1775 | PASS |
| V2 | implied defocus per frame below a quarter wave everywhere | worst 0.09736 waves | PASS |
| V3 | spread across the six ROIs, cv below 0.40 | 0.149 at f/14, 0.134 at f/18 | PASS |
| V4 | defocus has the sign needed to explain the gap | it has the opposite sign | PASS, T1 excluded |

V1 matters beyond itself. A quadratic in wavefront error, with defocus
linear in frame offset, makes `B` a parabola in offset - which is the form
`defocus_b.py` fitted before any of this was known.

The implied defocus is 0.08246 waves per frame at f/14 and
0.07869 at f/18, so 3.03 frames at f/14 and 3.18 at f/18 to
the Rayleigh quarter wave. That is a sensibly sampled stack, and V3 says
the whole field agrees on it.

**A consistency observation, and it is labelled as such because the ratio
was worked out by hand before the check was written.** It carries no pass or
fail. A constant physical step would give f/14
1.480 times the defocus per frame, since the
wavefront error goes as the reciprocal of the squared effective f-number,
which is 30.05 at f/14 and 36.56 at
f/18. A step scaled to the diffraction depth of field would give exactly 1,
since that depth carries the same squared factor. Measured:
1.048.
That favours depth-of-field scaled stepping, which is the standard way to bracket a macro
stack, and it means the two stacks carry comparable defocus per frame rather
than f/14 carrying half again as much.

### 10.5 What is settled and what is not

**Threat T1 is excluded.** T1 says f/14 carries more residual defocus. More
defocus lowers fitted `B`. So T1 predicts f/14 measures **lower** than f/18
and the gap should be negative. The measured gap is +0.1157,
positive. The prediction and the
observation have opposite signs.

This does not depend on the calibration constant, on the focus step, on
which frame the focus map chose, or on the parabola fit. It depends on two
independently measured signs, both large.

**What it does not settle.** The aperture trend itself remains unexplained.
Defocus is now off the list; aberration and rig geometry remain, they share
a sign, and two in-band apertures cannot separate them. Section 34 of
`docs/captures-needed.md` still stands and its priority is unchanged: a
third and fourth in-band aperture are what distinguishes the survivors.

**A side result worth carrying forward.** The estimator's defocus response
is now calibrated, so `B` measured across a focus sweep is a usable focus
metric with a physical scale attached, reading out directly in waves. The
vertex of the parabola locates best focus to a fraction of a frame. Whether
that beats the mid-band focus score the survey currently uses is untested
and is not claimed.

**A pattern in my own errors, recorded because three is enough to be one.**
Amendment 9 retracted a shape diagnosis that was an artefact of a wrong `B`.
This amendment retracts a failure diagnosis that was an artefact of a wrong
assumed direction, and records a registered direction, S2, that was simply
backwards. In all three the magnitudes were sound and the signs and
baselines were not. The corrective that worked every time was the same:
compute the thing forward from a known truth instead of reasoning about
which way it ought to go. House rule 18 asks for the direction to be stated
before measuring, which these did. Stating it did not make it right; only
the synthetic forward model did.
