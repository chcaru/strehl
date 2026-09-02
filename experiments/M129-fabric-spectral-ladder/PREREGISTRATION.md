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

*(none yet)*
