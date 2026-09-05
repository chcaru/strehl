# M189 — PTC-referenced noise-colour detail

**Status: NO-GO AS AN ADMISSIBLE DETAIL INSTRUMENT BEFORE
IMPLEMENTATION.** The exact proposal was not previously commissioned and
retired. Its narrow linear-filter mechanism is real: with an independently
measured noise realization and an externally fixed covariance reference, a
post-capture filter colours the noise while a pre-sensor optical change does
not. A one-sided correction can therefore make ordinary common linear USM tie
while making blur fall.

That result does **not** survive as M1. A single completed image does not expose
its noise realization; the legitimate stack, warp, gather, demosaic, and tone
pipeline already colours noise; and an adaptive renderer can denoise, sharpen
the estimated signal, then synthesize fresh signal-dependent noise with the
calibrated PTC distribution. The added noise replaces the expected sensor noise
rather than adding an independently detectable cost. The resulting output can
have the same calibrated noise law as a genuinely sharper optical capture.

No M189 candidate, holdout reading, or capture request was run.

## 0. Four-part ruling

| Question | Ruling |
|---|---|
| Was this route already retired? | **Not exactly.** The corpus contains failed noise-subtracted detail scores, failed output-spectrum estimators, and a successful raw-CFA PTC floor, but no separately commissioned external-covariance **noise-colour veto** with the one-sided construction derived below. |
| Does the algebra survive? | **Only under a restricted common-linear-filter contract.** External normalization retains the filter's noise transfer, and a one-sided score can make linear blur fall and linear USM not rise. It fails the broader renderer contract because sharpen-then-re-noise restores the expected covariance without undoing the sharpened deterministic estimate. |
| Does the data exist? | **Calibration and development nulls exist; an admissible positive set does not.** M61 already supplies the PTC slope, and 110 paper flats plus 506 darks exist. A single image is insufficient. The archive has no unused matched pair of complete output lineages for the physical positive arm. |
| What should be built? | **Nothing claim-bearing.** At most this is a pipeline-specific veto for naive post-filters. It is not an independent resolved-detail instrument, so no `experiments/M189-noise-colour-detail/` directory is justified. |

## 1. Corpus check

**VERIFIED BY READING COMMITTED `HEAD`.** The search covered
`docs/research/` and `experiments/`, including whitespace-collapsed searches
for wrapped forms of `noise spectrum`, `noise colour`, `PTC`, `re-whiten`,
`synthetic noise`, and `noise provenance`.

The exact candidate below was not found. The nearest work already establishes
most of its boundary:

1. M57 explicitly rejects single-image FRC against a noise model because the
   normalized crossing inherits common-filter blindness
   (`docs/research/M57-detail-metric-from-first-principles.md:98-120`). It says
   the calibrated temporal-noise model was considered but not built as its own
   candidate because independent-half cross-power already suppresses expected
   noise (`docs/research/M57-detail-metric-from-first-principles.md:122-131`).
   That is a level/SNR use of the model, not the post-filter covariance-shape
   veto derived here.
2. BUILD-SHARP tried to infer the completed merge's noise spectrum. A scalar
   white-noise estimate allowed `29.4x` peak deconvolution gain, while a fitted
   power law over-corrected to `0.70x`; the two calibrations were unusably far
   apart (`docs/research/BUILD-SHARP.md:986-1021`). Its proposed disjoint-half
   difference was then measured. The whole difference was a legible scene
   because the halves chose different winners and were not mutually registered;
   it represented noise only in flat regions
   (`docs/research/BUILD-SHARP.md:1205-1240`). A pure-texture subject had no
   usable flat region at all (`docs/research/BUILD-SHARP.md:1276-1283`).
3. M5 demonstrates the part that genuinely works. On raw green CFA data, a
   truly signal-free high-frequency plateau matched the photon-transfer model
   to `0.950-1.093x`; at f/8 and f/5.6, where scene signal remained in the
   apparent floor, the method refused the interpretation
   (`docs/research/M5-diffraction-measured.md:30-49,568-581`). This validates an
   external raw-noise level, not sharpening provenance.
4. M95's first in-band PTC floor failed its own held-out null and 50% power
   plant, so its `S_detail=0.1698` was void
   (`docs/research/M95-kernel.md:2388-2404`). A later physically selected
   defocus calibration did measure a level exponent `p=1.0751` and a
   `0.1281` signal fraction (`docs/research/M95-kernel.md:2481-2515`), showing
   that calibrated noise can estimate band composition. It did not identify
   whether a deterministic high-frequency component came from optics or
   rendering.
5. BUILD-SHARPMETRIC's S2 subtracts additive noise exactly in expectation and
   held its noise plants near unity
   (`docs/research/BUILD-SHARPMETRIC.md:254-289`). It still raised its score
   under USM by `1.0345 / 1.0987 / 1.1697`, and the report says no local
   reference-free energy statistic can distinguish an edge from manufactured
   overshoot (`docs/research/BUILD-SHARPMETRIC.md:343-353`).
6. The Phase-0 slanted-edge battery also tried fixed/noise-floor variants.
   Native `S_25` rewarded USM by `1.028294x`; variants that suppressed USM
   reversed blur and genuine improvement, and a fixed floor let USM raise
   repeat-difference energy selectively
   (`docs/research/M-PHASE0-SLANTEDGE.md:258-285`).

**Corpus ruling:** this is not a rediscovery of one exact retired
implementation. It is a previously uncommissioned *veto architecture* assembled
from known components. The corpus already warns that observing the relevant
output noise and turning the veto into positive detail are the hard parts.

## 2. What the PTC reference actually supplies

M61-E1 is a temporal adjacent-frame estimator on raw CFA planes:

\[
d=F_k-F_{k+1},\qquad
s=(F_k+F_{k+1})/2,
\]

with per-tile \(v=\operatorname{var}(d)/2\). The sum/difference independence is
what permits aggressive low-texture selection without selecting on the noise
estimate itself. The estimator is never demosaiced, and temporal differencing
cancels PRNU, DSNU, and scene-fixed structure
(`docs/research/M61-ptc-high-iso-measured.md:158-181`).

For one CFA plane, write the conditional temporal sensor model as

\[
x=\mu+n,\qquad
E[n\mid\mu]=0,\qquad
C_0(\mu)=\operatorname{diag}(v_i),\qquad
v_i=g\mu_i+r_i^2,
\]

where \(\mu=HO\) is the irradiance after the optics, \(g\) is the PTC slope, and
\(r_i^2\) is an independently sourced read-noise term.

**Constraint:** M61 reports **only the slope**
(`docs/research/M61-ptc-high-iso-measured.md:183-188`). The PTC intercept is not
an admissible read floor: 68.8% of independent subject-frame fits were negative
(`docs/research/M-PHASE0-PTC.md:119-137`). Therefore M61 alone is not a complete
absolute covariance at low signal. The signal-dependent part is calibrated; a
low-signal implementation would need an independent dark/read-noise source and
must not recover \(r^2\) from the PTC intercept. The shipped temporal model has
the same permitted form, \(gS+(RN_e g)^2\)
(`docs/research/M90-prnu-noise-model.md:175-192`).

PRNU is separate. It is fixed across frames, contributes zero to temporal
disagreement, and does not average like shot/read noise
(`docs/research/M90-prnu-noise-model.md:201-228`). A temporal raw difference
removes it only when the same scene point samples the same photosites. Warping
and resampling require a separate fixed-pattern covariance model.

## 3. The part of the hypothesis that survives

### 3.1 Signal-dependent shot noise does not by itself colour the raw PSD

**DERIVED.** Let \(W=\operatorname{diag}(w_i)\) be a spatial window and \(F\)
the unitary DFT. Even though \(C_0(\mu)\) is nonstationary, the expected
periodogram marginal at Fourier cell \(k\) is

\[
\begin{aligned}
E\left|[FWn]_k\right|^2
 &= [FWC_0(\mu)WF^*]_{kk}\\
 &= \sum_i |F_{ki}|^2 w_i^2 v_i\\
 &= \frac1N\sum_i w_i^2v_i.
\end{aligned}
\]

It is independent of \(k\). Heteroscedasticity creates cross-frequency
covariance, but independent raw photosite noise remains flat in its marginal
spectral shape. If the local means were known, the variance-stabilized residual

\[
z=C_0(\mu)^{-1/2}(x-\mu)
\]

would have identity covariance under the model.

This distinction matters:

- a flat scene is **not mathematically required** for independent
  heteroscedastic raw noise to have a flat expected marginal PSD;
- a flat scene or a repeat **is observationally required** to separate that
  noise from the unknown deterministic scene in a finite image.

The derivation must be applied per CFA plane. Pooling colour planes with
different gains or read floors manufactures periodic covariance before any
post-filter is present.

### 3.2 Optics and a post-capture filter produce different covariance

**DERIVED.** A genuine optical change gives

\[
x_H=HO+n_H,\qquad
\operatorname{Cov}(n_H\mid HO)=C_0(HO).
\]

The optics change the mean reaching the sensor. They do not multiply the
subsequently generated temporal sensor noise by \(H\).

A post-capture linear filter gives

\[
y=K(\mu+n),\qquad
\operatorname{Cov}(y\mid\mu)=K C_0(\mu)K^T.
\]

For locally constant variance and an LSI filter,

\[
P_{n,y}(f)=|K(f)|^2P_{n,x}(f).
\]

Thus the proposed physical distinction is correct. It is not the normalized
cross-repeat statistic rejected in the first M189 report. It is an independent
measurement of the post-sensor transfer applied to noise.

### 3.3 The required normalization does not automatically cancel \(K\)

**DERIVED.** The crucial denominator is an **external pre-filter covariance
prediction**, not the filtered image's own empirical noise spectrum. Define

\[
G_N(f)=\frac{P_{n,\mathrm{observed}}(f)}
             {P_{n,\mathrm{PTC+baseline}}(f)}.
\]

For a genuine optical change, the denominator is recomputed from the changed
post-optics signal level, so \(G_N(f)=1\) under the calibrated raw model. A wider
aperture can raise photon count and shot-noise magnitude without changing this
ratio. For a downstream common filter, \(G_N(f)=|K(f)|^2\).

Consequently:

- dividing by the externally predicted level does **not** recreate the earlier
  \(|K|^2/|K|^2\) blindness;
- normalizing only the *shape* of \(G_N\) preserves a frequency-varying USM
  signature but discards a constant gain over the admitted band;
- estimating the denominator from the same observed post-filter spectrum does
  cancel \(K\) and returns to the retired branch;
- the strongest form is therefore the absolute external ratio, conditioned on
  signal level, not a freely normalized empirical spectrum.

The unusable PTC intercept limits this absolute form in read-noise-dominated
regions, but does not invalidate it in shot-dominated regions or where read
noise is independently calibrated.

### 3.4 A restricted one-sided score really can pass the three directions

**DERIVED.** Suppose two registered independent-noise observations provide,
per Fourier cell,

\[
C(f)=E[X_1X_2^*]=P_\mu(f),\qquad
N(f)=\tfrac12E|X_1-X_2|^2=P_n(f).
\]

After a common LSI filter, both become \(|K|^2\) times their base values. Unlike
ordinary coherence, retain the external noise-gain estimate
\(G_N=N/N_{\rm ref}\) and define

\[
Q(f)=\frac{C(f)}{\max(1,G_N(f))}.
\]

Under a common post-capture filter,

\[
Q_K(f)=P_\mu(f)\min(|K(f)|^2,1).
\]

Therefore, in the ideal linear model:

- post-capture blur, \(|K|<1\), makes \(Q\) fall;
- post-capture amplification, \(|K|>1\), is divided back out and cannot raise
  \(Q\);
- genuine pre-sensor improvement raises \(P_\mu\) while \(G_N=1\), so \(Q\)
  can rise.

This is the narrow positive result. It breaks the original
normalize-and-blind / do-not-normalize-and-reward dichotomy by using an external
one-sided anchor. A binary `SHARPENING_UNSAFE` refusal when \(G_N\) exceeds its
calibrated envelope would be safer than subtracting an estimated halo penalty.
A nonnegative, clipped score cannot charge an arbitrarily strong halo below
zero; it can only tie or refuse it.

The construction nevertheless already requires an independently observable
noise realization. It is not a single-image statistic.

## 4. Why it does not become a completed-output instrument

### 4.1 One image plus a PTC slope is insufficient

**DERIVED.** A completed image supplies

\[
Y=M+N,
\]

not \(N\). Its periodogram contains deterministic scene power, noise power, and
their finite-sample cross term. The PTC predicts \(E[NN^*]\); it does not reveal
which observed oscillations were the realized \(N\). For every apparent
noise-colour residual, an alternative deterministic scene component can
produce the same pixels.

The committed M5 measurement is the empirical boundary: the PTC floor was
valid only where an independently gated, genuinely signal-free plateau existed,
and it failed as a noise estimate where scene signal remained
(`docs/research/M5-diffraction-measured.md:568-581`).

The current M167 acceptance contract gives an ordinary candidate either one
completed image or two completed independent-noise observations, not a latent
scene, renderer Jacobian, or raw-noise realization
(`experiments/M167-detail-battery/PREREGISTRATION.md:49-58`). The single-image
mode cannot identify noise colour from PTC alone.

### 4.2 Repeats and flats can expose noise, with narrower scope

A matched repeat pair can use its difference to isolate temporal noise. A known
flat can estimate pipeline noise colour spatially. Both can commission a
post-filter veto.

Completed *stack* repeats are harder. BUILD-SHARP's even/odd experiment found
that output differences retained the scene because the half-stacks elected
different focused frames and had sub-pixel mutual registration error
(`docs/research/BUILD-SHARP.md:1224-1240`). PTC calibration does not subtract
that deterministic mismatch. The difference is a noise observation only on a
flat or under a renderer construction that guarantees identical signal
transfer in both lineages.

### 4.3 The stacker's legitimate output noise is already coloured

For fixed linear weights and known operators, write

\[
A_i=D_{\rm demosaic}W_iR_i,
\]

where \(R_i\) is the warp/resampler and \(W_i\) the spatially varying merge
weight. The temporal component would be

\[
C_{\rm out,temporal}=\sum_i A_iC_iA_i^T.
\]

This is computable in principle from the full operators, not from a scalar
\(n_{\rm eff}\). Fixed-pattern terms also contain cross-frame covariances
\(\sum_{i,j}A_iC^{\rm PRNU}_{ij}A_j^T\).

Three complications are load-bearing:

1. Strehl's weights and winners depend on noisy observations. Treating the
   realized weights as fixed omits selection/noise coupling.
2. PRNU does not simply average down. Its warped inter-frame correlation is a
   separation-dependent curve, from `0.68` for adjacent deep-stack frames to
   approximately zero at large separation
   (`docs/research/M90-prnu-noise-model.md:633-680`).
3. The resampler itself attenuates fixed-pattern variance. M90 measures
   within-frame factors `0.4793` for bilinear and `0.6816` for Catmull-Rom, and
   supplies an explicit stationarity validity check
   (`docs/research/M90-prnu-noise-model.md:690-716`). Its noise result also
   changes with the consumer's bandwidth because a low-frequency PRNU tail
   survives warps that decorrelate pixel-scale pattern
   (`docs/research/M90-prnu-noise-model.md:775-819`).

BUILD-SHARP independently measured the completed noise spectrum as white sensor
noise shaped by the gather kernel and demosaic, with a slope changing from
about `-2.85` at low frequency to `-1.47` near Nyquist
(`docs/research/BUILD-SHARP.md:1254-1274`).

An exact baseline is therefore pipeline-specific. A complete known renderer
could approximate it by propagating or Monte-Carlo resampling the calibrated
input noise through the frozen pipeline. An opaque comparator output cannot.

### 4.4 CFA-native operation does not cover delivered sharpening

Operating on raw CFA avoids demosaic colour and gives the cleanest PTC
reference. It can establish whether a filter was applied **before that
measurement point**. It cannot detect USM applied after demosaic or after the
final render.

A known linear demosaic can be included in \(A_iC_iA_i^T\). An adaptive
demosaic, nonlinear tone curve, clipping stage, or content-adaptive denoiser
requires a scene-dependent Jacobian or direct noise probes. Without that known
baseline, legitimate processing and illicit sharpening are not separable by
output colour alone.

## 5. The adversarial re-whitening test

### 5.1 Exact linear re-whitening removes exact linear sharpening

**DERIVED.** Let a second LSI filter \(R\) follow the sharpening filter \(K\).
To restore the baseline noise PSD at every frequency,

\[
|R(f)K(f)|^2P_n(f)=P_n(f),
\]

so

\[
|R(f)K(f)|=1.
\]

The deterministic signal is multiplied by the same \(RK\). Exact linear
re-whitening therefore removes the amplitude gain that constituted the
sharpening. Within the strict common-linear-filter threat model, the witness
survives, and the cost is separately visible: the net signal-amplitude
sharpening is gone. Partial linear re-whitening leaves the residual noise gain
visible.

### 5.2 Adaptive denoise–sharpen–re-noise defeats the witness

**DERIVED.** A renderer need not use one common linear operator on signal and
noise. It can form an estimate \(\hat\mu\) from its input stack and output

\[
Y_{\rm adv}=K\hat\mu+\epsilon,
\qquad
\epsilon\mid K\hat\mu\sim
\mathcal P_{\rm calibrated}(K\hat\mu),
\]

where \(\mathcal P_{\rm calibrated}\) has the expected signal-dependent PTC
variance and the declared baseline pipeline colour. It may also synthesize the
known fixed-pattern component. This renderer:

- retains the sharpened deterministic estimate \(K\hat\mu\);
- discards or suppresses the sensor-noise realization that \(K\) would have
  coloured;
- adds fresh noise with the expected level, colour, and signal dependence.

Matching only second-order covariance is easy. Matching a fuller Poisson-plus-
read distribution does not restore provenance either: the renderer can sample
that distribution conditional on its output mean.

The construction is particularly available to a focus stacker because it owns
many observations of overlapping scene content. As repeat count and local SNR
increase, the estimation cost in \(\hat\mu\) can shrink. A learned or
content-adaptive renderer can also trade estimation error for plausible
deterministic texture.

### 5.3 The PTC model does not identify physical noise ancestry

Let \(\mu_G=K\mu_B\). Consider:

- **genuine world:** better optics produce mean \(\mu_G\), followed by fresh
  calibrated sensor/pipeline noise \(\epsilon\);
- **rendered world:** worse optics produce \(\mu_B\), and the renderer emits
  \(K\mu_B+\epsilon\) after replacing the captured noise.

Couple the same \(\epsilon\) in the two constructions. Their completed outputs
are identical, and both satisfy the same external PTC noise law, while one
label is genuine optical resolution and the other is post-capture
manufacture. This is the model-qualified form of the general
identical-observation/opposite-label criterion
(`docs/research/M168-m2-identifiability.md:22-34,73-83`).

The external model narrows the admissible worlds, but it does not remove this
collision because it constrains the **distribution** of output noise, not its
physical lineage.

### 5.4 The cost is not separately guaranteed detectable

The adversary pays:

1. estimation error or prior bias in \(\hat\mu\);
2. the computation needed to denoise and synthesize noise; and
3. an ordinary calibrated noise floor in the delivered image.

Only the first is potentially an image-quality cost. It has no
distribution-free positive lower bound: it can be small on high-SNR,
redundantly sampled, known, or model-friendly scenes. The third is not an
extra penalty; it replaces the noise a genuine output is expected to contain.

Detecting wrong deterministic texture would require a reference, a validated
scene prior, authenticated input-to-output noise ancestry, or a restricted
renderer contract. That is additional identifying information, not a
noise-colour statistic. A noise witness can therefore veto naive common
post-filters, but it cannot certify resolved detail against an adaptive
renderer.

## 6. Data and exact minimum observations

M189 opened no new capture pixels for this route and did not access
`D:\personal\macro\requests\7-aperture-pairs\`.

### 6.1 What exists

1. **PTC calibration:** M61-E1 has already run on 12 subject stacks / 1554
   frames, ISO 50-1000, with a passing control
   (`docs/research/M-PHASE0-PTC.md:64-83`). Its admissible output is the
   per-stack slope under `CONSIST = half_pct < 5% AND ac_pct < 10%`
   (`docs/research/M-PHASE0-PTC.md:142-176`), not a read-floor intercept.
2. **Development nulls:**
   `D:\personal\macro\requests\10-paper-iso-var` contains **110 ARWs**, and
   `D:\personal\macro\requests\6-11-extended-dark-frames` contains **506 ARWs**.
   They can commission level/colour null behavior but contain no positive
   detail arm
   (`docs/research/M189-repeat-referenced-detail.md:184-192`).
3. **Fixed-focus repeats:**
   `D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light`
   contains **576 ARWs**, two passes by nine ISOs by 32 repeats. It is a QUALITY
   holdout, its second-light geometry gate already failed, and it is not a pair
   of complete bracket lineages
   (`docs/research/M189-repeat-referenced-detail.md:184-187`).
4. **Nominal complete-stack pairs:** `112MSDCF` / `113MSDCF` contain
   **79 + 63 ARWs** but differ by 1/60 versus 1/30 second; `bee-2-cpl` /
   `bee-3-cpl` contain **299 + 299 ARWs** but differ by ISO 400 versus ISO 100;
   `wrapped-text-1` / `wrapped-text-2` contain **130 + 120 ARWs** but are a
   re-framing with first-frame NCC `0.3834`
   (`docs/research/M189-repeat-referenced-detail.md:187-190`).

There is therefore ample data to validate the sensor model and simple
flat-field transfer, but no unused matched real positive set for a
completed-output detail instrument.

### 6.2 What the restricted witness would need

A single completed image plus a PTC slope is **not enough**.

The algebraic minimum for a fixed-focus synthetic commission is:

- **2** matched independent RAW exposures for the base repeat pair;
- **2** matched independent RAW exposures for a real optical-improvement pair;
- derive post-capture blur and USM from the base pair.

That is **4 RAW frames minimum**. If the degradation must also be physical,
add **2** matched degraded exposures, for **6 RAW frames minimum**. These are
mathematical minima, not a powered sample-size claim.

For a completed focus-stack output, replace every exposure above with a
complete independent bracket lineage: **4 full brackets minimum**, or **6 full
brackets** with a physical degradation arm. Every lineage must share subject,
geometry, exposure/ISO or an explicitly calibrated level change, and a frozen
renderer baseline. Matched flats/darks are additionally required to validate
the declared baseline covariance.

No such capture is requested. More repeats can improve estimation of a naive
linear-filter veto; they cannot repair the adaptive re-noise collision.

## 7. Decision

No `experiments/M189-noise-colour-detail/` candidate is created.

The route produces one useful but non-claim-bearing statement:

> With independently isolated temporal noise and a frozen baseline pipeline,
> PTC-referenced noise transfer can veto an ordinary common linear sharpening
> filter without becoming blind to common linear blur.

It cannot produce the required stronger statement:

> A completed image whose noise matches the calibrated PTC covariance contains
> genuine optically resolved detail rather than a sharpened deterministic
> estimate with regenerated noise.

That second statement is false under an adaptive renderer. The witness is at
most a pipeline-specific sharpening sentinel, not an independent M1 detail
instrument. This finding requires no change to M135's owned route and no owner
capture action.
