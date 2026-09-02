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



