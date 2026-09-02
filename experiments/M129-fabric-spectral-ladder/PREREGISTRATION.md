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
