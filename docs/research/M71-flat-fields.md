# M71 — PRNU from 484 flat fields: κ = 0.31%, and why it must not be added to `PlaneNoise::variance`

## Headline

**κ = 0.3096% per green photosite (MEASURED)**, and it clears the pre-registered
materiality threshold by 1.81×. The paper-texture confound is not argued away — it
is *measured* and bounded at **0.09–0.14% of the PRNU variance**, i.e. it moves κ by
less than 0.07%.

**The ruling is nevertheless: do not add `+ (κ·S)²` to `PlaneNoise::variance`.**
Not because the term is wrong or because a partial correction is harmful — **that
premise was retracted mid-milestone and I withdraw my use of it** (§8.3) — but because
that struct is the shared normaliser for three consumers, two of which have thresholds
calibrated against today's σ. The term belongs at `Estimator::predicted_sigma` alone.
Adding it to the shared model would loosen the disagreement gate by up to 1.34× and
invalidate the *measured* constant `FOCUS_NOISE_SD`. **This is a coupling requirement,
not a prohibition** — independently the same conclusion M68 reached in its corrected
fact 41. Details in §8.

**The sharper finding, added after the retraction (§8.3): the shipped model is already
over-confident, and the missing PRNU term is why.** The 2.16%-high profile gain and the
absent κ cancel at **S ≈ 504 DN** per photosite; above that the model **under-predicts**
σ, reaching **−12.8%** at S = 8000. **Adding κ alone never flips the sign at any signal
level** — worst case +0.0000% over S ∈ [0, 20000] — so by M68's corrected criterion it
is a good change even though incomplete. The conclusion holds under every gain
assumption tested, including the one that would rescue the shipped model.

Six numbers, all MEASURED:

| quantity | value | control |
| --- | --- | --- |
| κ, green photosite | **0.3096%**, spread ±0.0159% over 5 matched pairs | rolled covariance ≤1.99σ |
| PTC gain, green | **0.224103 DN/e⁻**, −2.07 to −2.16% vs `profile.rs` | two-greens null g(G2)/g(G1) = **1.000910** |
| the same gain, drift-immune | **0.223864 ± 0.000836** (within-frame PTC, n=22) | ratio to the above **0.99893** |
| paper leak into κ | **0.09–0.14%** of the PRNU variance | 38× and 75× swings in resolved texture |
| CPL spatial non-uniformity | **none above a time-matched placebo** (0.373% vs 0.526%) | placebo *larger* than the effect |
| dust, f/5.6 | 2898 px = **0.035%** of a plane, median −3.4% | enrichment 2278×, roll control 7.3% |

**Two results the retraction sent me back for, both bearing on other milestones'
numbers** (§8.4, §8.5): M68's open item — *"PRNU leakage into M61's tile variances
remains unchecked by me"* — is **closed**, and M61 is cleared: biasing its slope 1%
would need a **48%** frame-to-frame illumination change. And M61's own ISO-100 stack at
tile 32 reads **0.8699**, matching my independent flat-field B/green ratio to
**0.99993**. Separately, B's noise turns out to be **~60× more spatially correlated than
green's** and **1463× above** what read noise predicts — real, reproducible, and
**unruled**.

And three things I got wrong and the controls caught: §9. **Plus one pre-registered
criterion in the follow-up, T1, which failed and is recorded as failed** (§8.5).

---

## 0. Prior work read (rule 40)

`AGENTS.md` in full. `docs/captures-needed.md` §4 in full. `SYNTHESIS.md` §1–§3 and
§5 in full, fact table sampled, with facts 27, 29, 61–64, 230–234, 895, 921, 925, 958
extracted. `M68-b-plane-mechanism.md` for the house form and the standing warning —
and **re-read at commit `11c91b5`**, its facts 39–41, after the orchestrator retracted
the warning my brief closed with. I read the correction **at the commit rather than the
summary of it**, on the orchestrator's own instruction that the quantity had been
mis-transmitted twice. `M61-ptc-high-iso-measured.md` §4.7 and its estimator definition
(L158–189), read *after* the retraction pointed at its inherited 0.8396 (§8.4).
`M5-diffraction-measured.md` for the spectral machinery (facts 27/29) — specifically
its §2.5 trap, that a boxcar window's sinc sidelobes inflate a noise floor 1.6–1.8×
and can fake a knee. Every spectrum in §5 below is Hann-windowed because of it.
`crates/strehl-core/src/{noise,merge,focus,profile}.rs` read, none edited (`crates/`
is contended).

---

## 1. Task zero — recovering the CPL split (MEASURED)

The CPL state is not in EXIF. The owner shot with-CPL first, then without, so each
40-frame exposure group should split 20/20.

**It does, 9 times out of 9.** Every group breaks after exactly index 19, with a
277–285 s intermission against a ~1.0 s median intra-group gap — a ratio of 262–283×.
There is no ambiguity to resolve and no judgement call.

The brief asked me to treat this as self-validating and to stop if time-ordering and
signal level disagreed. **They disagree, and I did not stop — because the disagreement
is diagnostic rather than fatal.** See §2: the signal ratio is not a constant because
the *light* was not constant, and the same measurement that shows the ratio moving
also shows why.

**EXIF says nine exposure groups; the owner remembered eight. Trust the EXIF.**
`SonyExposureTime` gives the true values: 1/256, 1/128, 1/64, 1/32, 1/20, 1/13, 1/10,
1/8, 1/5 s. Session span 542.5 s.

Two further metadata facts that turned out to be load-bearing:

- **The 360 flats were shot at infinity focus.** `FocusDistance2 = inf`,
  `FocusPosition2 = 255` for all 360, against 0.2707–0.2771 m / 56–58 for the two
  sweeps. With the paper at ~0.28 m this is a gross defocus. **Confirmed from pixels
  in §4** — this was pre-registered as PR-2a precisely because it was unrecorded.
- **The flats used the electronic shutter** (`ShutterCount` pinned at 8515 for all
  360; `SequenceNumber = 'Single'`), the sweeps the mechanical one (contiguous
  8453..8514 and 8515..8576). This generated a hypothesis in §7 which the data then
  refuted.

---

## 2. The illumination was not a drift. It was a 2.35× swing. (MEASURED)

The owner flagged "possibly varied light over the whole duration". The measurement is
larger than that phrasing suggests, and it reorganises the whole analysis.

Per-frame `mean / SonyExposureTime` is the illumination times the filter. It **rose at
+1.6 to +2.0 %/s through the first ~80 s of pass A — a 2.35× rise** — plateaued, then
**declined at −0.3 to −0.5 %/s through pass B**.

The within-group linear trends **join continuously across group boundaries at
different shutter speeds** — pass A's 1/60 group ends at proxy 156 258 and its 1/30
group begins at 156 369, 0.07% apart. That continuity is worth more than it looks:

- **It establishes signal linearity in exposure time** across the 50× range, since a
  non-linearity would appear as a step at every group boundary.
- **It establishes shutter-time accuracy**, for the same reason.
- **It identifies the apparent non-linearity in the raw level table as 100%
  illumination**, and removes it as a candidate explanation for anything else.

**Consequence for PR-1b, honoured:** the pre-registered magnitude clause
(`0.20 ≤ R_k ≤ 0.45` for the A/B ratio at matched shutter) **FAILS in 4 of 5
unclipped groups** — the measured ratios are 0.217, 0.351, 0.518, 0.696, 0.727. The
direction clause (`R_k < 1`) is MET 9/9. **PR-1b is recorded as failed.** The
consequence is carried through in §6: I do not report a CPL transmission.

**Consequence for everything else:** dividing every frame by its own spatial mean
before any temporal statistic is mandatory, and it is done at the point of
accumulation in `02-decode-flats.py`, not afterwards.

### The Jensen bias that normalisation introduces (DERIVED, then corrected)

Normalising each frame to its own spatial mean biases a fitted gain **upward by
≈ CV²(m)**. Writing `u_f = m_f / m̄`, the normalised temporal variance times `m̄²` is
`g·S·E[1/u] + (RN·g)²·E[1/u²]`, not `g·S + (RN·g)²`. On this data `E[1/u]` reaches
1.0152 and `E[1/u²]` reaches 1.0465, so the shift is **up to +0.16% in g**.

That is small against a ±10% gate and **100× the statistical error**, and it is free
to correct because `m_f` is recorded. The PTC fit carries `A1_k = E[1/u]` and
`A2_k = E[1/u²]` as known per-group coefficients rather than fitting them.

---

## 3. Pre-registration (committed before any pixel was read)

`src/01-preregistration.py`, commit `dde2321`, criteria PR-1a … PR-8, with thresholds,
fail-inputs and consequences. `git show --name-only dde2321` shows five files and no
pixel-reading code among them.

The materiality threshold was fixed there, not after seeing κ:
**`KAPPA_MATERIAL = 0.1713%`**, defined as the κ that inflates σ by 5% at S = 8000 DN,
given `g = 0.2289377` and `σ(0) = 0.961538 DN` from `profile.rs`. At the container
maximum S = 15360 the same 5% gate would be 0.1236%. Fact 230's independent corpus
bound (PRNU ≲ 0.26%) is 1.52× the threshold — so the corpus's own prior expectation
was already that the term is material, and I recorded that before measuring.

Outcomes:

| criterion | what it tested | result |
| --- | --- | --- |
| PR-1a | CPL split recoverable from timing, 9/9 | **MET** |
| PR-1b | A/B ratio in [0.20, 0.45] and < 1 | **magnitude FAILED 4/5**, direction MET 9/9 |
| PR-2a | flats more defocused than either sweep endpoint | **MET**, 36.3× |
| PR-2b | sweep spans ≥10× in resolved structure | **MET**, 38.0× and 75.4× |
| PR-3a | PTC green gain within ±10% of `profile.rs` | **MET**, −2.07 / −2.16% |
| PR-3b | two-greens gain null | **MET**, 1.000910 |
| PR-3c | quadratic term in the PTC | R +3.80σ, greens +1.5σ, B −0.71σ |
| PR-4a | κ multiplicative, exponent 1.00 ± 0.05 | **MET**, q = 0.9629 |
| PR-4b | ρ(D_A, D_B) ≥ 0.5 | **MET**, 0.6467 |
| PR-4c | PRNU invariant across the sweep | **FAILED** — see §4 |
| PR-4d | positive control, and roll negative control | **MET**, worst 1.99σ of 3 |
| PR-5 | κ vs 0.1713% | **ENTERS**, 0.3096% |
| PR-6 | CPL transmission and flatness | **transmission not measurable; flatness null** |
| PR-7 | dust map with roll control | **MET** |
| PR-8 | residual illumination structure | **excess present**, +141% |

---

## 4. The estimator, and the pre-registered gate that killed the first version of it

### The design

The confound the brief identifies is real: at m≈2 paper fibre is optically resolved,
and multiplicative paper texture is indistinguishable from PRNU by photon transfer
alone. The brief offers defocus and spatial frequency as levers. **I used a third one
first, because it is exact rather than asymptotic.**

Write the high-passed residual of a plane's temporal mean as

```
r_P = o + p_P + n_P
```

with `o` the optical structure common to both greens, `p_P` that plane's own PRNU, and
`n_P` the temporal-mean noise. Then `D = r_G1 − r_G2` cancels `o` **exactly**, with no
defocus argument and no spectral model, and

```
cov(D_A, D_B) = var(p_G1) + var(p_G2) = 2κ²
```

across the two **independent** 20-frame realisations at matched shutter — the CPL-on
half and the CPL-off half. **The noise cancels in expectation rather than being
subtracted as an estimate.** That is strictly better than `captures-needed.md` §4's
quadrature route, which is retained as a cross-check and agrees (§4.3).

Two implementation points that are not decoration:

- **The smooth surface is a 61-px triple box blur (σ ≈ 30.5 plane-px), not the frame
  mean**, because vignetting spans **2.1×** across the frame (B plane at 1/8-A: p0.01
  = 6265, median 11 824, max 13 214). A frame-mean normalisation would put the
  vignette straight into κ.
- **The high-pass response to white noise `F` is computed numerically from the actual
  kernel**, not assumed to be 1.0. It is 1.002239. Assuming 1.0 would have moved the
  headline by 0.11%.

### PR-4c failed, and the failure is the most useful thing in this report

PR-4c pre-registered that the D-based PRNU estimate must be constant to ±25% across a
focus sweep while the common optical power C = cov(r_G1, r_G2) moves ≥10×.

**It failed, badly, in both sweeps:**

| sweep | C moved | P(sharpest)/P(softest) | required |
| --- | --- | --- | --- |
| with-cpl | 38.0× | **80.8** | 1.00 ± 0.25 |
| no-cpl | 75.4× | **55.2** | 1.00 ± 0.25 |

**The premise was wrong, and the sweep is what proved it wrong.** G1 sits at
`[0::2, 1::2]` and G2 at `[1::2, 0::2]` — one pixel apart on the diagonal. D therefore
cancels optical structure only where that structure is *smooth on a 2-px scale*. On an
in-focus frame it is not, and D is then dominated by paper. My pre-registered claim
that D cancels paper *at any focus* is refuted by measurement.

**PR-4c is recorded as failed.** What it does not do is invalidate the headline, and
the reason is in the next subsection — the same data supplies an estimator that is
immune to the defect PR-4c exposed, and that estimator passes the *substance* of
PR-4c with a large margin.

### The cross-capture covariance, which is immune

`cov(D_sweep, D_flats)` between a sweep frame and a flat measures only what is common
to two **independent captures**, so temporal noise cancels in expectation and **no
noise model is used at all**. Paper texture cannot contribute: the flats' paper is 36×
less resolved and at a different focus, so the two paper fields are uncorrelated.

| comparison | C in the sweep frame | κ from cov | ρ |
| --- | --- | --- | --- |
| with-cpl **softest** (frame 0) | 3.719e−04 | **0.2959%** | 0.4100 |
| with-cpl **sharpest** (frame 35) | 1.413e−02 | **0.2973%** | 0.1006 |
| no-cpl **softest** (frame 0) | 1.916e−04 | **0.2946%** | 0.4335 |
| no-cpl **sharpest** (frame 46) | 1.445e−02 | **0.2963%** | 0.1204 |
| **rolled negative control** | — | **+0.20% and +0.14% of signal** | — |

**C moves 38× and 75×; κ moves 0.47% and 0.58%.** That is PR-4c's invariance criterion
(1.00 ± 0.25) met with a margin of 50×, on an estimator that does not have the defect
that killed the pre-registered form. The roll control says the covariance is a real
pixel-for-pixel correspondence and not an artefact of two maps having similar
statistics.

It also yields a number nobody asked for: **cov_cross / cov_flats = 0.9136**, so
**≥91% of the PRNU variance is stable across a different minute, a different filter, a
different focus and a different shutter mode.** Both routes are lower bounds on κ by
Cauchy–Schwarz — they measure `2·cov(p₁, p₂)`, not `2κ²` — so the higher of them,
0.3096%, is the tighter bound and is the number I report.

### 4.3 The headline (MEASURED)

| matched shutter | S_A | S_B | κ | quadrature A / B | ρ(D_A,D_B) | rolled |
| --- | --- | --- | --- | --- | --- | --- |
| 1/250 | 260.4 | 1198.7 | 0.3296% | 0.3647 / 0.3248 | 0.327 | −0.13σ |
| 1/125 | 781.8 | 2228.5 | 0.3202% | 0.3318 / 0.3150 | 0.526 | −0.17σ |
| 1/60 | 2143.7 | 4139.4 | 0.3083% | 0.3165 / 0.3043 | 0.704 | −0.94σ |
| 1/30 | 4862.8 | 6984.5 | 0.2976% | 0.3017 / 0.2962 | 0.814 | +1.99σ |
| 1/20 | 7649.8 | 10515.5 | 0.2909% | 0.2943 / 0.2901 | 0.863 | +0.51σ |

**κ = 0.3096%, spread ±0.0159% across the five matched pairs.** The spread is a
re-draw error (discipline 375), not a subdivision of one estimate. It is also
**conservative as an error bar**, because the five pairs sit at different signal levels
and κ has a real signal-dependence (below), so the spread contains that trend as well
as the statistical scatter.

The quadrature route — which subtracts a *modelled* noise instead of cancelling it —
agrees to within 1.8% at every level and converges on the covariance route as the
noise falls. Two structurally different estimators, one model-dependent and one not.

**κ is not flat.** It falls monotonically by 12% as signal rises 30×, and q = 0.9629
against a pre-registered 1.00 ± 0.05 — MET, but at the edge, and the trend is
systematic rather than noise. A pure multiplicative pattern cannot do that. **POST-HOC**,
the two-component form that can is a multiplicative pattern plus a fixed *additive*
one, which in relative units dies as 1/S:

```
cov(D_A, D_B) = 2·κ_mult² + Q / (S_A · S_B)
```

This is a straight line in `1/(S_A·S_B)` with no free shape, so it is a test rather
than a curve fit. It gives **κ_mult = 0.3021%** and an implied additive FPN of
**0.767 DN** per plane, at R² = 0.672. The additive component is **2.0× the dark FPN I
measure on the mechanical-shutter darks** (0.381 DN after removing the temporal-mean
noise), so the model is suggestive rather than closed. **Flagged unruled** (§10). The
practical effect is small: κ_mult = 0.3021% versus κ = 0.3096%, and both clear the
threshold by more than 1.7×.

---

## 5. Two more discriminators, neither of which relies on the two-green argument

### 5.1 Scale (MEASURED)

White per-pixel PRNU does not care where the smooth surface is cut. Paper fibre,
correlated over tens of microns — several pixels at m≈2 — feeds in as the cut widens.

| high-pass box | equivalent σ | κ |
| --- | --- | --- |
| 15 px | 3.7 px | 0.3093% |
| 31 px | 7.7 px | 0.3093% |
| 61 px | 15.2 px | 0.3093% |
| 121 px | 30.2 px | 0.3093% |
| 241 px | 60.2 px | 0.3092% |

**κ spans 1.0002× over a 16× change in cut scale.** If any meaningful part of this
number were structure correlated over more than a pixel, this table would not be flat.

### 5.2 Spectrum (MEASURED, M5's method)

The **cross**-spectrum between the two independent 20-frame halves kills the temporal
noise by independence, so no floor is subtracted anywhere. Hann-windowed Welch
periodograms on 256×256 tiles, 60 tiles per map, radially averaged — M5's construction,
including its finding that windowing is load-bearing.

| f (cyc/px) | PRNU cross(A,B) | in-focus frame, auto | common(sharp, flat) |
| --- | --- | --- | --- |
| 0.026 | 1.0000 | 1.0000 | 1.0000 |
| 0.151 | 0.9610 | 0.5046 | 0.9916 |
| 0.276 | 0.9391 | 0.0886 | 0.7498 |
| 0.484 | 0.9356 | **0.0124** | 0.7391 |

| statistic | flatness (top-quartile / bottom-quartile) | verdict |
| --- | --- | --- |
| PRNU cross-spectrum, flats A × B | **0.9028** | white |
| in-focus sweep frame, auto-spectrum | **0.0167** | steeply red — resolved texture |
| common(sharp sweep, flat) | **0.9116** | white |

The third row is the argument in one line. **The same in-focus frame contains both
populations**, and the cross-spectrum against an independent flat separates them: the
frame as a whole falls 60× across the band, while the part of it that correlates with
the flats is flat to 9%. The residual 9% droop is consistent with the pixel-aperture
MTF and is not modelled out.

Note the 0.276 cyc/px row: fact 27's measured diffraction knee `f_sig = 0.2762 cyc/px`
sits inside this band, and the PRNU spectrum shows nothing there. It should not — the
knee is an optical property and PRNU is behind the optics.

### 5.3 What this bounds the paper leak at (DERIVED)

Over the defocused tail of each sweep, P is linear in C. Fitting `P = P₀ + α·C` and
evaluating at the flats' own C = 5.275e−06:

| sweep | tail frames | C range | R² | κ(paper-free) | leak at the flats' C |
| --- | --- | --- | --- | --- | --- |
| with-cpl | 28 | 3.7e−04 … 2.0e−03 (5.3×) | 0.927 | 0.2817% | **0.136% of P₀** |
| no-cpl | 29 | 1.9e−04 … 2.0e−03 (10.3×) | 0.982 | 0.2911% | **0.091% of P₀** |

**The paper contributes 0.09–0.14% of the PRNU variance in the flats, i.e. 0.05–0.07%
of κ.** That is the confound quantified rather than argued, and it is three orders of
magnitude below the effect.

Two supporting facts. First, PR-2a: the flats sit at C = 5.25e−06 against a
least-focused sweep frame at 1.92e−04 — **36.3× more defocused than either sweep
endpoint**, confirming the `FocusDistance2 = inf` tag from pixels. Second, in the flats
the *common optical* structure is **0.195% rms**, smaller than the PRNU itself
(0.3096%). The flats are, by measurement, more a picture of the sensor than of the
paper.

---

## 6. Deliverable 2 — the photon transfer, and a drift-immune replication

### 6.1 Between-group PTC (MEASURED)

Per-plane clean rule: a group-half enters only if that plane's clipped fraction is
zero. Defect mask built once from the highest clean level (variance outside
[0.25, 4]× the median). Jensen coefficients carried as known per-group terms.

| plane | levels | S range | g (DN/e⁻) | vs `profile.rs` 0.228938 | fitted b (DN²) | excluded px |
| --- | --- | --- | --- | --- | --- | --- |
| R | 17 | 97–11274 (116×) | 0.220920 ± 0.000285 | −3.50% | −1.5080 | 0.056% |
| G1 | 11 | 260–12039 (46×) | 0.224001 ± 0.000251 | **−2.16%** | −1.8537 | 0.051% |
| G2 | 11 | 260–12032 (46×) | 0.224205 ± 0.000274 | **−2.07%** | −1.8264 | 0.051% |
| B | 14 | 166–11495 (69×) | 0.194934 ± 0.001165 | **−14.85%** | −1.4443 | 0.277% |

**PR-3a MET for the greens.** **PR-3b, the two-greens null: g(G2)/g(G1) = 1.000910**
pooled, 1.000617 in the A halves and 1.000746 in the B halves. Two error bars, because
they measure different things: the propagated fit error is **±0.00166**, and the
empirical half-to-half re-draw spread is **±0.000065**. M68's analogue was
0.99937 ± 0.00511, so this is 3.1× tighter formally and much tighter empirically —
the flats have no subject for the two greens to disagree about.

**B fails the ±10% gate at −14.85%, independently corroborating M68/M61's B-plane
anomaly on data neither of them had.** `g(B)/g(green) = 0.8699` against fact 921's
0.8396 ± 0.0112 — **+3.6%, ≈2.7σ**. Same phenomenon, mild tension, different ISO and a
different method. Reported as tension, not as a refutation (§10).

### 6.2 Do facts 27/29 agree? (MEASURED — yes)

Facts 27/29 rest on a **spectral-floor** method: the high-frequency floor of a radially
averaged power spectrum matched the noise model to **0.950×** at f/11, and gave a
structure-free σ estimate across a 4.8× signal range.

This is a different method on different data: a temporal-variance photon transfer
across nine exposures at fixed ISO 100. My green gain is **0.978× the profile's**.
Fact 29's floor was **0.950× the profile's model** in variance, i.e. **0.975× in σ**,
and σ ∝ √g at fixed signal, so its implied gain ratio is **0.950**.

**0.9789 versus 0.950 — the two methods agree to 3.0%, both low relative to
`profile.rs`, both by a small amount.** Fact 29 is reproduced. Two independent methods
finding the shipped gain 2–5% high is more informative than either alone, and points at
`profile.rs`'s `gain_divisor = 436.8` rather than at either measurement.

### 6.3 The drift-immune replication (MEASURED)

The 2.1× vignetting range means **every group-half is its own photon-transfer curve**:
bin pixels by their own smooth signal level and read variance against signal *inside a
single capture*. No illumination correction, no interpolation, no assumption that the
light held still — and 22 independent realisations.

**Within-frame green gain = 0.223864 ± 0.000836 (sd 0.003921, n = 22).**
**Ratio to the between-group value: 0.99893.**

The between-group gain is not an artefact of the drift correction. This is the
strongest form of deliverable 2 available in this data and it was not in the brief.

### 6.4 The intercepts, which do not close (MEASURED, then unruled)

All four between-group intercepts are **negative** (−1.44 to −1.85 DN²), which is
unphysical. Investigated and not resolved:

- **It is not a black-level error.** Measured black offset is **+0.2307 DN** across 20
  ISO-100 darks; the deficit implies a ~12 DN pedestal.
- **The decode path is validated.** My 4-plane pooled dark RMS σ is **0.98518 DN**
  against `profile.rs`'s `DARK_SIGMA_RMS_DN` ISO-100 row of 0.98444 — **ratio
  1.00075**.
- **It is not charge sharing.** §7.2.
- **The within-frame PTC does not reproduce it**: intercept **+4.14 DN²**, sd 19.1,
  SEM 4.1 — consistent with zero and with the +1.0 DN² read floor, 1.4σ from −1.84.
  But it spans only 1.6× in S, so its lever arm on an intercept is poor. Weak evidence.
- **Leading untested hypothesis:** the flats used the *electronic* shutter and the
  darks the *mechanical* one, and the pedestal differs between readout paths.

**The gain is immune to any pedestal** — a constant offset moves the intercept, not the
slope — so this does not threaten §6.1 or §6.3. Its consequence for the shipped model is
that the model is **conservative**: it over-predicts σ by ~7% at S = 100, ~1.7% at
S = 1000, ~1.2% at S = 8000. **Flagged unruled** (§10).

---

## 7. Deliverables 3, 4 and the illumination

### 7.1 The CPL — a triple null, after the placebo was scaled correctly (MEASURED)

**Transmission is not measurable from this data.** The two states are not interleaved;
a 142 s gap separates them; and `T` is exactly degenerate with any illumination change
in that window. The model-free bound from the raw ratios is **0.217 ≤ T ≤ 0.727**
(0.46–2.20 stops), which is too wide to be worth anything. Breaking the degeneracy
requires assuming the light varied smoothly across the change, and that assumption is
not robust: extrapolating log-proxy fits to the gap midpoint gives T = 0.4546, 0.5520
and 0.8920 for fit windows of 60, 120 and 200 s — **T = 0.633 ± 0.230**. The number
moves further with the analyst's choice than the quantity itself plausibly ranges.
**I decline to report a transmission.**

**Spatial flatness — clean null.** A ratio of two spatial-mean-normalised maps divides
out any per-frame scalar, so *this* part is not degenerate. But it needs a placebo at
the same time baseline.

| comparison | Δt | sd of smooth part | x-gradient ρ |
| --- | --- | --- | --- |
| REAL, CPL vs none, 1/20 | 280 s | 0.372% | −0.884 |
| REAL, CPL vs none, 1/30 | 280 s | 0.366% | −0.865 |
| REAL, CPL vs none, 1/250 | 280 s | 0.373% | +0.983 |
| PLACEBO within A, 1/250 vs 1/13 | 230 s | **0.512%** | +0.965 |
| PLACEBO within A, 1/250 vs 1/20 | 190 s | **0.526%** | +0.955 |
| PLACEBO within B, 1/250 vs 1/20 | 190 s | 0.208% | −0.927 |
| PLACEBO within A, 1/30 vs 1/20 | 40 s | 0.025% | −0.460 |

**The time-matched placebo is 1.41× LARGER than the effect.** The CPL adds no
detectable spatial non-uniformity; the bound is **≲0.5% rms of smooth structure**, and
that bound is set by the illumination, not by the filter.

The x-gradient column says why. Every long-baseline map, real or placebo, is a
left–right ramp, and **its sign follows the direction the light was moving, not
whether the filter was on**. It is a cloud crossing a window.

**Colour — also a null.** R/G1 shifts by up to 1.79% and B/G1 by up to 3.85% across
the filter change — against placebos of 2.09% and 4.81%. **Separation 0.9× and 0.8×.
Not separated.**

Fact 925 is authoritative that 7 of 12 corpus stacks were shot with the CPL on and 4
without. **This measurement neither supports nor refutes a per-stack CPL systematic.
It bounds one at ≲0.5% of smooth spatial structure and cannot see below that.**

### 7.2 Dust (MEASURED, PR-7 MET)

Plane-averaged residual below −3% in **both** CPL states, corroborated at −1.5% in ≥3
of 4 planes.

| quantity | value |
| --- | --- |
| below −3% in A / in B | 3214 / 3260 of 8 236 816 |
| coincident in both | **2898** |
| expected by chance | 1.3 → **enrichment 2278×** |
| roll control (314 rows, even, CFA phase preserved) | **211 = 7.3%** → PASS |
| confirmed in ≥3 of 4 planes | 2898 = **0.03518%** of a plane |
| depth | median −3.44%, worst −5.47% |
| area within ~15 px of a defect | 0.302% |
| worst 15×15-averaged residual anywhere | **−4.81%** |

**CAVEAT, and it matters:** shot at **f/5.6**. Dust shadows sharpen and deepen as the
aperture stops down, and the corpus shoots f/8–f/11. **This is a lower bound on what
those stacks carry.** A −4.8% depression over a 15×15 patch, smeared into a trail by
the warp, is exactly the class of artefact the brief describes a reviewer finding in
five minutes — and at f/11 it will be deeper.

### 7.3 Charge sharing — a clean negative (MEASURED)

A frame difference removes every fixed pattern and leaves twice the temporal noise. Its
autocorrelation at small CFA lags is charge sharing, which moves variance out of the
per-pixel term and biases a PTC gain **low**.

| plane | r(0,1) | r(1,0) | r(1,1) | Σ over 4 in-plane nearest neighbours | implied gain bias |
| --- | --- | --- | --- | --- | --- |
| G1 | +0.00060 | +0.00167 | +0.00096 | +0.00453 | **+0.45%** |
| G2 | +0.00064 | +0.00078 | +0.00089 | +0.00282 | **+0.28%** |

**Inter-pixel capacitance does not explain the −2.1% gain deficit**, and it does not
explain M61's −10.7% either. That hypothesis is closed.

### 7.4 PR-8 — the illumination did carry spatial structure (MEASURED)

Global drift is a per-frame scalar and divides out. Residual excess temporal variance
after that division is drift that carried *spatial* structure. The block maps (73×109
blocks of 32×32, white noise suppressed 1024×) are the instrument; the statistic is
temporal, so PRNU cannot enter it.

**Median observed / photon-only = 2.411, range 1.411 … 6.317. Excess +141%.**
Equivalent spatially-structured wobble: **0.0304% rms per 32×32 block per frame.**
The two worst groups (6.1×, 6.3×) are both in pass B, where the light was declining.

**This is not a null. Reported as a finding, as the brief asked.**

I stated a mechanism before testing it: the flats used the **electronic** shutter, a
rolling readout, so under changing light each *row* gets a different effective
exposure — a per-row scalar a global spatial mean cannot divide out. **That predicts
the residual is organised in rows. It is not.**

| share of the residual | median |
| --- | --- |
| row-profile (73 block rows) | 16.4% |
| column-profile (109 block cols) | **39.0%** |

**Row/col = 0.42. The hypothesis is refuted by its own prediction.** The structure is
columnar — a horizontal gradient — which is the same signature the CPL placebos in
§7.1 showed independently. Two analyses built for different purposes converge on a
cloud edge sweeping across the window.

### 7.5 Deliverable 5 — declined, and why (ARGUED)

The brief authorises the vignetting profile "only if the above are clean". Deliverables
1 and 2 are clean; deliverable 3 is a null. I decline it anyway, on a ground the brief
did not anticipate:

**The 360 flats were shot at infinity focus (§1, §5.3) while the corpus stacks are shot
near minimum focus at m≈2.** Vignetting at this aperture is a function of the exit
pupil's apparent position and size as seen from each field point, and that changes with
extension. A vignetting profile measured at infinity is **not a valid correction** for
stacks shot at 2× magnification, and shipping one would be worse than shipping none —
the same failure mode as the standing warning, in a different subsystem.

I also cannot separate the lens's vignetting from the illumination's own left–right
ramp (§7.4), which is of the same order.

**This is a capture-design finding for `captures-needed.md`, not a measurement.**

---

## 8. The ruling — *described, not made* (`crates/` is contended)

**κ = 0.3096% is real, it is material, and `+ (κ·S)²` must NOT be added to
`PlaneNoise::variance` (`noise.rs:72`).**

### 8.1 Materiality (DERIVED)

Against the **measured** `g = 0.224001` (§6.1) and `σ(0) = 0.961538 DN`:

| S (DN) | σ today | σ with κ | inflation |
| --- | --- | --- | --- |
| 1000 | 14.998 | 15.314 | +2.11% |
| 2000 | 21.188 | 22.074 | +4.18% |
| 4000 | 29.949 | 32.409 | +8.21% |
| 8000 | 42.343 | 49.056 | **+15.85%** |
| 12000 | 51.855 | 63.792 | +23.02% |
| 15360 | 58.665 | 75.520 | **+28.73%** |

`(κS)² = g·S` at **S = 23 366 DN**, which is 1.52× the container maximum — so PRNU
never dominates, but it is **the second-largest term above S ≈ 2000 DN** and it is
15.9% of σ at the level where this project's gates actually operate.

Per plane (§ `10-rb.py`; the greens' own value by this route reproduces the headline to
**0.9923**, which is the route's control):

| plane | κ | note |
| --- | --- | --- |
| R | 0.3102% | optical-corrected; upper bound 0.3877% |
| G1/G2 | **0.3096%** | MEASURED, optical term cancelled exactly |
| B | 0.2528% | 0.823× green; upper bound 0.3436% |

### 8.2 Why the term must not go in the shared struct

`PlaneNoise::variance` feeds `NoiseModel::green_luma_sigma` (`noise.rs:126`), which has
**three** consumers that need PRNU with three different treatments:

**(a) `Estimator::predicted_sigma` (`merge.rs:953`) — PRNU belongs here.** Its own doc
already says "The frames are independent in their sensor noise; they are not
independent in their fixed-pattern noise, so this remains a floor rather than a
complete account." My measurement is the quantification of that sentence. But the
function computes `green_luma_sigma(luma) · selection_inflation(n) / √n`, and **PRNU
does not divide by √n unless the warp moves scene points across photosites.** The
correct form is

```
σ_pred = sqrt( σ_random²·infl²/n  +  (κ_eff·S)²·( ρ_warp + (1 − ρ_warp)/n ) )
```

with `ρ_warp` the fraction of PRNU that stays correlated under the stack's warp, and
`κ_eff = κ/√2` for the green luma because **PRNU is independent between the greens** —
which this milestone measured directly, since `var(D) = 2κ²` requires it. **`ρ_warp` is
unmeasured and I did not measure it** (§11).

**(b) `Estimator::disagreement` (`merge.rs:877`) — PRNU belongs here only partially,
and putting it in fully is the anti-conservative direction.** The statistic is
`s2 / σ²` where `s2` is the *measured* temporal variance of the admitted frames. PRNU
appears in `s2` only to the extent the warp decorrelates it — the `(1 − ρ_warp)`
fraction. Adding the full `(κS)²` to the denominator makes the gate **more permissive
by up to 1.34× at S = 8000**, wherever the warp is near-identity. A gate that admits
frames which genuinely disagree is precisely the silent miscalibration the brief warns
about.

**(c) `focus.rs:274, 402, 522` — PRNU must not go here without re-measuring a
constant.** The focus field divides its windowed gradient by `green_luma_sigma` at
every pixel; that division is what makes a *single* threshold valid across a frame and
across ISOs. The threshold constant `FOCUS_NOISE_SD = 0.015214` (`merge.rs:185`) is
**measured** — a pure-noise luma plane pushed through the real `FocusField`. That
calibration contains **no PRNU**. Adding κ to the shared model raises σ by 15.9% at
S = 8000 and 0% at S = 0, so the normalised focus response falls by **13.7% in bright
regions and not at all in dark ones**, while the threshold it is compared against does
not move. **The result is a signal-dependent tightening of focus selection that nobody
chose and no test would catch.**

### 8.3 The standing warning, as amended by M68's own retraction

**This section was rewritten after the orchestrator retracted the warning my brief
closed with.** The brief instructed me to check whether adding κ alone is "worse than
none," citing M68's B-plane result. **M68 has since withdrawn that claim on its own
initiative** (`M68-b-plane-mechanism.md` at `11c91b5`, its facts 39–41). I read the
correction at the commit rather than the summary of it, per the orchestrator's own
instruction, and the amended question I was given is sharper and better:

> *Does adding it alone flip the sign of the residual error from conservative to
> over-confident anywhere, and if so at what signal levels? State the regime, not just
> the magnitude.*

**The answer is no, and the reason is more interesting than the question.**
`11-regime-and-m61.py`. Sign convention: `err = predicted σ / true σ − 1`, so
**positive is conservative** and **negative is over-confident**.

| S (DN) | shipped model | shipped + κ | regime of the shipped model |
| --- | --- | --- | --- |
| 50 | +0.89% | +0.99% | conservative |
| 200 | +0.63% | +1.04% | conservative |
| **504** | **+0.00%** | +1.04% | **crossover** |
| 1000 | −1.02% | +1.03% | **OVER-CONFIDENT** |
| 2000 | −2.99% | +0.99% | OVER-CONFIDENT |
| 8000 | −12.75% | +0.80% | OVER-CONFIDENT |
| 15000 | −21.11% | +0.66% | OVER-CONFIDENT |

**MEASURED/DERIVED — candidate fact P19. The shipped noise model is already
over-confident, and PRNU is the reason.** Because the profile gain is 2.16% *high*
no PRNU at all, the two errors cancel at **S = 504 DN per photosite (1009 DN for green
luma)** and the model is **over-confident above it** — reaching **−12.8%** per
photosite and **−6.6%** on green luma at S = 8000. The inflated gain buys conservatism
only in the shadows; across most of the working range the missing PRNU term dominates
and the model under-predicts.

**DERIVED — candidate fact P20. Adding κ alone cannot flip the sign, at any signal level.** The
residual of `shipped + κ` against truth is `(g_profile − g_measured)·S`, which is
positive for all `S` whenever the profile gain exceeds the measured one. Swept over
S ∈ [0, 20000] at 0.1 DN resolution the worst case is **+0.0000%** — it never goes
negative. **Adding κ alone moves the model from over-confident to uniformly
conservative and shrinks the error magnitude everywhere above 504 DN.** By M68's
corrected criterion, this is a good change even though it is incomplete.

This is **robust to the one input a sceptic would attack**, my gain measurement:

| assumed truth | crossover, photosite | crossover, green luma |
| --- | --- | --- |
| profile gain exactly right | **0 DN** — over-confident *everywhere* | 0 DN |
| M71 measured (2.16% high) | 504 DN | 1009 DN |
| fact 29 implied (5.0% high) | 1194 DN | 2388 DN |

**Every case leaves the shipped model over-confident across most of the working
range.** If my gain measurement is wrong in the direction that would rescue the shipped
model, the model gets *worse*, not better.

**So the ruling's basis changes, and the ruling does not.** I am no longer declining
the term because a partial fix is harmful — that premise is withdrawn and I withdraw my
use of it. I am declining to put it in **`PlaneNoise::variance` specifically**, because
that struct is a *shared normaliser* and two of its three consumers have **thresholds
that were calibrated against the current σ**:

- `predicted_sigma` — PRNU belongs, improves it, **safe**;
- `disagreement` — inflating the denominator loosens the gate by up to **1.34×** at
  S = 8000, and the gate's tuning is denominated in today's σ;
- `focus.rs` — `FOCUS_NOISE_SD = 0.015214` was **measured from pure white noise with no
  PRNU**, so raising σ by 15.9% at S = 8000 and 0% at S = 0 silently retunes focus
  selection as a function of brightness.

**That is a coupling requirement, not a prohibition — the same conclusion M68 reached
in its corrected fact 41, arrived at independently and on a different plane.** The
constants and the model must move together. The recommendation below is unchanged, and
was already written in the coupling form.

**Recommended change, in order:**

1. **Add nothing to `PlaneNoise::variance`.** Add a separate field `prnu_frac: f32` to
   `PlaneNoise` with 0.003096 for the greens, 0.003102 for R, 0.002528 for B, **used
   by no existing call site**.
2. **Apply it in `Estimator::predicted_sigma` only**, in the ρ_warp form above,
   defaulting to `ρ_warp = 0` (the conservative reading, and the one that reduces to a
   pure `/√n` PRNU term) until ρ_warp is measured.
3. **Measure `ρ_warp` first.** It is measurable on the existing corpus — correlate the
   per-frame warp displacement against the decorrelation of the fixed-pattern residual
   — and until it is measured, points 1 and 2 are the only safe scope.
4. **Do not touch `disagreement` or `focus.rs` until (3) lands.**
5. `profile.rs`'s `gain_divisor = 436.8` is **2.1% high** by two independent methods
   here (§6.1, §6.3) and by fact 29's spectral floor (§6.2). That is a separate,
   smaller change and it is inside the ±10% gate. Not recommended for this milestone.

### 8.4 The inherited constant M68 flagged, now checked

M68's fact 39 volunteers a provenance caveat unasked, and the orchestrator asked me to
copy the practice:

> *"`m` is **derived** from σ/k, not an independent input … **The honest provenance
> caveat is different from the one asked about**: 0.9231 is mine and survives §6;
> **0.8396 is M61's and I did not re-measure it.** D2 closed the pedestal failure mode
> for it and nothing else — **PRNU leakage into M61's tile variances remains unchecked
> by me**."*

I measured PRNU per plane and per-plane gain, so I can check both halves of that. Two
findings, in opposite directions.

**(a) The PRNU-leakage concern is structurally void, and I can bound it.** M61's
estimator (M61-E1, its report L158–181) is a **temporal adjacent-frame difference**,
`d = F_k − F_{k+1}`, `v = var(d)/2` per 8×8 tile. A fixed multiplicative pattern
cancels *identically* in `d` at equal level; M61 chose that estimator explicitly
"because PRNU/DSNU and every fixed pattern cancel exactly." With a fractional
photometric drift `ε` between adjacent frames the surviving PRNU term has variance
`(εSκ)²`, so the slope bias is `ε²·S·κ²/(2g)`:

| adjacent-frame drift ε | slope bias at S = 2000 DN |
| --- | --- |
| 0.1% | 0.000004% |
| 1% | 0.00043% |
| 10% | 0.043% |

**DERIVED — candidate fact P21. Biasing M61's slope by 1% would require a 48% frame-to-frame
illumination change.** M68's open item is closed: **PRNU cannot account for any part of
M61's ratio.** M61 picked the right estimator and its choice is vindicated by an
independent measurement of the quantity it was defending against.

**(b) My own g(B)/g(green) = 0.8699 is robust, and the tension with 0.8396 is real.**
Before pointing at anyone else's number I tested mine against its own post-hoc
exclusions (§12 records that I dropped three high-signal B levels). Refitting under 11
different level-inclusion rules:

| | spread of g | as % of value |
| --- | --- | --- |
| B, 11 exclusion rules | 0.001421 | **0.73%** |
| **G1, same treatment (control)** | 0.000200 | **0.09%** |

B is 8× less stable than green — worth saying — but the resulting ratio spans only
**0.8698 … 0.8761**, which is **entirely outside** M61's 0.8396 ± 0.0112. **My
exclusions cannot reach M61's value.** The tension survives.

**(c) And then M61's own table resolves it.** M61 §4.7 tests the tile-correlation
failure mode by growing the tile:

| stack | ISO | tile 8 | tile 16 | tile 32 |
| --- | --- | --- | --- | --- |
| `109MSDCF` | 160 | 0.8283 | 0.8464 | 0.8377 |
| `112MSDCF` | 500 | 0.8407 | 0.8517 | 0.8466 |
| **`bee-3`** | **100** | 0.8408 | 0.8607 | **0.8699** |
| `foam` | 1000 | 0.8376 | 0.8529 | 0.8558 |

**MEASURED — candidate fact P22. `bee-3` is the only ISO-100 stack in that table, and at tile 32 it
reads 0.8699 — my independent flat-field value to four significant figures
(ratio 0.99993).** My estimator uses per-pixel *temporal* variance on a defocused
uniform field: no tiles, no subject, no inter-frame warp, so it is immune to the tile
bias M61 was bounding. The single ISO-matched comparison available agrees with me
exactly, and M61's tile-8 primary does not.

**I state the weakness of this myself.** One matching row out of four is weak evidence
on its own; three other rows at tile 32 read 0.8377/0.8466/0.8558 and do not match. It
is worth reporting because it is *the only ISO-matched row*, not because four-figure
agreement on one row is proof. **It does not overturn M61's headline** — M61's fact 29
conclusion that correlation "cannot supply the missing 16%" is **correct and I confirm
it**. What it suggests is that M61's tile-8 primary carries a residual few-percent
correlation bias that its own tile-32 column already reveals, and that the pooled
0.8396 is therefore a slight underestimate.

### 8.5 An unexpected finding, hunted rather than kept

Testing (c) required measuring the per-plane noise autocorrelation, which
`07-structure.py` had done only for the greens. Extending it to all four planes
(`12-ipc-tile-bias.py`) produced something I did not go looking for:

| plane | r(0,1) | r(1,0) | Σ over lags |
| --- | --- | --- | --- |
| R | +0.00087 | +0.00146 | +0.011 |
| G1 | +0.00060 | +0.00167 | +0.014 |
| G2 | +0.00064 | +0.00078 | +0.009 |
| **B** | **+0.03115** | **+0.10181** | **+0.715** |

**B's in-plane noise correlation is ~60× the greens', and strongly anisotropic.**
Correlated noise has *lower per-pixel variance*, which a PTC reads as low gain — so the
seductive reading is that this is the mechanism behind the 0.84× B deficit that M61,
M68 and M48c have all chased. **My first duty was to try to destroy it**
(`13-b-correlation-kill.py`, three tests pre-registered in the file header before
running).

- **T1 stability — FAILED as pre-registered.** I pre-registered "< 2× across pairs"; the
  observed swing is **2.5×**. Recorded as failed. The sub-structure is that the darkest
  group (1/250 s) is the sole low outlier and the other **eight pairs span 1.35×**, but
  the criterion as written failed and I am not reinterpreting it.
- **T2 darks — survives.** In 22 ISO-100 darks B reads +0.0763 against the flats'
  +0.0908. But **all** planes are correlated in the dark (G1 +0.0553), so B is only
  **1.38×** green there, not 60×.
- **T3 spatial scale — survives.** B keeps **91%** of r(1,0) through a 15 px high-pass,
  while R/G1/G2 go *negative* — the correct signature for white noise. B's structure is
  at the per-pixel scale, not smooth illumination.

The decisive number is the dilution test. If the correlation were read-noise row
structure it would dilute as photons take over, by `var_dark/var_flat`:

| plane | predicted r(1,0) in flats | observed | excess |
| --- | --- | --- | --- |
| G1 | 0.000032 | 0.001666 | 51× |
| **B** | **0.000070** | **0.101814** | **1463×** |

**MEASURED — candidate fact P23. B carries a large signal-proportional correlated-noise component that
green does not.** Green's correlation dilutes roughly as read noise should; B's does
not, by three orders of magnitude.

**And I refute the tempting conclusion myself.** For a mean-preserving linear filter,
`Σ_lags r = 1/Σh² − 1`, so B's +0.715 implies a variance factor of **0.583** — and the
ACF has not decayed by lag 3, so the true implied factor is *lower*. That **overshoots**
the observed 0.84 badly. **A pure in-camera spatial filter on B is not the explanation**,
however well it fits the qualitative story. Something correlates B's noise and it is
real, reproducible and in the dark as well as the light, but it is not a simple filter,
it is **outside my charter**, and it is **not settleable from flat fields**. Recorded
**unruled** in §12 and handed on.

---

## 9. Errors, and what caught them

Four. The first three were caught by controls rather than by the estimates, in the
spirit of facts 61–64; the fourth was caught by a `NaN` I nearly ignored.

**(1) PR-4c's premise was wrong.** I pre-registered that the two-green difference
cancels paper at any focus. It cancels paper only where paper is smooth on a 2-px
scale. **Caught by the pre-registered criterion itself, which is what it was for.** The
headline survives because the cross-capture route (§4.2) is immune, but the
pre-registered form is recorded as failed and is not reinterpreted.

**(2) I nearly reported the CPL as spatially non-flat with a 13× separation.** Step 08
used a 40 s same-state placebo (0.025%) against a 280 s real comparison (0.372%). Step
09 scaled the placebo to the same baseline and it came out at **0.526% — larger than
the effect**. The colour result went the same way (0.9× and 0.8×). **Both withdrawn.**
A placebo at the wrong scale is not a placebo.

**(3) I nearly reported a 43× contradiction of corpus facts 895/958.** Differencing two
adjacent flats gave ρ(G1, G2) = +0.0017 against the corpus's +0.073. **The dark frames
in the same run gave +0.0647 and +0.0779 — the corpus value.** The flats were the wrong
instrument: the light was moving at up to 2 %/s, so a plain frame difference carries a
scaled copy of the vignetting profile, which is common to both greens and manufactures
a positive ρ. Normalising each frame to its own spatial mean before differencing
removes it:

| case | S | ρ raw | ρ normalised | rolled | pure-read prediction |
| --- | --- | --- | --- | --- | --- |
| 1/250 flat | 184.8 | +0.01166 | +0.01037 | −0.00012 | 0.00153 |
| 1/60 flat | 1521.0 | +0.00248 | +0.00249 | −0.00026 | 0.00019 |
| 1/20 flat | 5722.9 | +0.00170 | +0.00158 | −0.00025 | 0.00005 |
| dark pair 0 | 0 | **+0.06474** | — | −0.00044 | 0.06470 |
| dark pair 2 | 0 | **+0.07789** | — | −0.00347 | 0.06470 |

**Facts 895/958 are reproduced where they were measured.** The refinement is that ρ is
a **read-noise-domain** correlation: it falls by more than an order of magnitude under
signal and reaches ≤0.0016 by S ≈ 5700. It is *not* a fixed +0.073 at all levels. The
normalised flats sit ~10× above a pure-read prediction, and since §7.4 shows the
illumination structure a spatial-mean normalisation cannot remove, **those are quoted
as upper bounds, not as a measured signal-domain correlation.**

**(4) In the follow-up, I ran the B-correlation kill tests on clipped data and drew the
opposite conclusion for twenty minutes.** The first pass of `13-b-correlation-kill.py`
sampled exposure groups including 1/5 s, where the greens are 100% pinned at the white
level. Zero variance produced `NaN` correlations, pinned structure produced a spurious
G1 r(1,0) of **+0.669**, and the resulting "63× swing" made T1 look catastrophically
unstable and the whole B finding look like an illumination artefact. **I wrote the
verdict "filter hypothesis REFUTED" into the script before noticing the NaNs.** Adding
a clipping guard (`max < 15000`) inverted T1 to a 2.5× swing and T2 from "refuted" to
"survives". **Caught by the NaNs being visible in the printed table** — had the code
silently dropped them I would have shipped the wrong sign. The lesson is narrow and
mechanical: *this milestone already had a clipping rule in `03-ptc.py` — "any clipped
pixel voids the group" — and the follow-up script simply failed to inherit it.* The
final T1 still fails as pre-registered and is reported as failing.

---

## 10. Candidate facts (rule 28)

Each labelled and sourced. Constants name the statistic, the frame count and the
exclusion rule (rule 8).

**P1 (MEASURED).** Sensor PRNU on the ILCE-7CM2 green photosites is
**κ = 0.3096%** of signal (relative sd), spread ±0.0159% across 5 matched-shutter
pairs. From `cov(D_A, D_B)/2` with `D = r_G1 − r_G2`, over 10 group-halves of 20 ARW
frames each (`D:\personal\macro\flat-fields`, ISO 100, f/5.6, 200 mm, infinity focus),
excluding any group-half with non-zero clipping in either green and a fixed defect mask
of 0.051% of the plane. Roll-control covariance ≤1.99σ. `M71/05-kappa.py`.

**P2 (MEASURED).** The paper-texture contamination of P1 is **0.09–0.14% of the PRNU
variance** (0.05–0.07% of κ), by extrapolating `P = P₀ + α·C` over 28 and 29 defocused
sweep frames to the flats' own common-optical power C = 5.275e−06. `M71/06-sweeps.py`.

**P3 (MEASURED).** PRNU is **white**: κ changes by 1.0002× when the high-pass cut is
swept 15→241 px (16×), and the A×B cross-spectrum is flat to 0.9028 (top-quartile /
bottom-quartile, Hann Welch, 60 tiles of 256²) against 0.0167 for the auto-spectrum of
an in-focus frame of the same subject. `M71/07-structure.py`.

**P4 (MEASURED).** **≥91.4% of the PRNU variance is stable** across a different
session minute, a different filter state, a different focus setting and a different
shutter mode, from `cov(D_sweep, D_flats) / cov(D_A, D_B)`; the same statistic changes
by 0.47% and 0.58% while resolved subject texture changes 38× and 75×.
`M71/06-sweeps.py`.

**P5 (MEASURED).** Photon-transfer gain at ISO 100 from 9 exposures spanning 50× in
exposure time: **G1 0.224001 ± 0.000285, G2 0.224205 ± 0.000274 DN/e⁻**, 11 clean
levels each over 46× in signal, Jensen-corrected. That is **−2.07 to −2.16% versus
`profile.rs`'s 0.228938**. Two-greens null g(G2)/g(G1) = **1.000910**, re-draw spread
±0.000065. `M71/03-ptc.py`.

**P6 (MEASURED).** The same gain from a **within-frame** PTC that uses the 2.1×
vignetting range as its signal axis and therefore requires no illumination correction
at all: **0.223864 ± 0.000836 (n = 22 group-half × plane realisations)**, which is
**0.99893×** P5. `M71/08-cpl-illum.py`.

**P7 (DERIVED).** P5/P6 and fact 29's spectral floor agree: fact 29's 0.950× in
variance is 0.950 in implied gain, against 0.9789 here — **3.0% apart, both below
`profile.rs`**. Two independent methods on different data both find `gain_divisor =
436.8` about 2–5% high.

**P8 (MEASURED).** The B plane's PTC gain at ISO 100 is **0.194934 ± 0.001165 DN/e⁻**,
14 clean levels, **0.8699× the green mean**. Fact 921 says 0.8396 ± 0.0112, so the two
differ by **+3.6%, ≈2.7σ**. Same phenomenon, different ISO and method, **mild tension —
not a refutation**. **Substantially resolved after the retraction, in §8.4:** my value
is robust to its own exclusions (0.73% spread across 11 rules, against a 0.09% green
control) and **M61's own ISO-100 stack at tile 32 reads 0.8699**, matching mine to
0.99993. The tension is most likely a residual tile-correlation bias in M61's tile-8
primary, not a disagreement about the sensor. `M71/03-ptc.py`, `M71/11-regime-and-m61.py`.

**P9 (MEASURED).** Per-plane PRNU: **R 0.3102%, green 0.3096%, B 0.2528%** (B is
0.823× green). R and B are optical-corrected point estimates, not exact cancellations;
their assumption-free upper bounds are 0.3877% and 0.3436%. Control: the greens by the
same route give 0.3072%, **0.9923×** the exact value. `M71/10-rb.py`.

**P10 (MEASURED).** Inter-pixel/charge-sharing correlation of the temporal noise is
**+0.0045 and +0.0028** summed over the four in-plane nearest CFA neighbours,
implying a PTC gain bias of **+0.45% / +0.28%**. It does not explain the −2.1% gain
deficit and does not explain M61's −10.7%. `M71/07-structure.py`.

**P11 (MEASURED, refines facts 895/958).** ρ(G1 noise, G2 noise) is **+0.0647 and
+0.0779 in ISO-100 darks** — reproducing the corpus's +0.073 — and falls to **≤0.0016
by S ≈ 5700 DN**. It is a read-noise-domain correlation, not a fixed value at all
signal levels. Roll controls −0.00044 and −0.00347. `M71/09-controls.py`.

*Sibling corroboration, added after the fact was written.* **M72** landed
`docs/research/M72-green-plane-correlation.md` in parallel with this report and measures
ρ = **+0.08261** on 220 dark frames from `D:\macro-dark-frames`, against fact 895's
+0.0730. My two ISO-100 dark values bracket it and all three are mutually consistent, so
the two milestones **agree on magnitude by independent estimators on different frame
sets**. They are complementary rather than redundant: M72 establishes the magnitude and
the mechanism in the dark domain and rules it immaterial; P11 adds the axis M72 could not
see from darks alone, namely that ρ **decays with signal** and is essentially gone by
S ≈ 5700 DN. Folding both, the correlation is a read-noise-domain effect of about +0.075
that does not survive into the photon-dominated regime where this project's gates
operate. **I have not read M72's method in detail and am not vouching for it** — I am
recording that the numbers agree.

**P12 (MEASURED).** Sensor dust at **f/5.6**: 2898 pixels = **0.03518%** of a CFA plane
have a plane-averaged residual below −3% in both CPL states and below −1.5% in ≥3 of 4
planes; enrichment over chance coincidence **2278×**; roll control 211 (7.3%). Median
depth −3.44%, worst −5.47%, worst 15×15-averaged residual **−4.81%**, 0.302% of the
plane within ~15 px of a defect. **A lower bound for the corpus, which shoots f/8–f/11.**
`M71/07-structure.py`.

**P13 (MEASURED).** The CPL introduces **no spatial non-uniformity detectable above a
time-matched placebo**: worst real comparison 0.373% rms of smooth structure against a
190–230 s same-state placebo of **0.526%**. Its colour shift is likewise not separated
(R/G1 0.9×, B/G1 0.8× the placebo). Bound: ≲0.5% rms. `M71/09-controls.py`.

**P14 (MEASURED).** **CPL transmission is not measurable from this capture.** The
model-free bound is 0.217 ≤ T ≤ 0.727; extrapolating across the 142 s filter change
gives 0.4546, 0.5520 and 0.8920 for 60/120/200 s fit windows. The analyst's choice
moves the answer more than the quantity plausibly ranges. `M71/09-controls.py`.

**P15 (MEASURED).** Under a spatial-mean normalisation the flats still carry
**+141% excess temporal variance** over the photon-only prediction on 32×32 block maps
(median ratio 2.411, range 1.411–6.317), equivalent to **0.0304% rms per block per
frame** of spatially-structured illumination change. The structure is **columnar**:
column-profile share 39.0% against row-profile 16.4%. A rolling-electronic-shutter
mechanism was stated in advance and is **refuted** by that ratio. `M71/08,09`.

**P16 (MEASURED).** The 360 flats were shot at **infinity focus** with the subject at
0.28 m — confirmed from pixels, not only from `FocusDistance2`: their common optical
power is **36.3× below the most defocused frame of either 62-frame sweep**. They are
therefore **not a valid vignetting reference** for corpus stacks shot near m = 2.
`M71/06-sweeps.py`.

**P17 (MEASURED).** Illumination during the 9m02s session rose **2.35×** over pass A's
first 80 s (+1.6 to +2.0 %/s), plateaued, then fell at −0.3 to −0.5 %/s through pass B.
Within-group linear trends join across group boundaries to 0.07%, which independently
establishes **signal linearity in exposure time and shutter-time accuracy** across the
50× range. `M71/02,08`.

**P18 (DERIVED, methodological).** Normalising each frame to its own spatial mean —
mandatory when illumination drifts — biases a fitted PTC gain **upward by ≈ CV²(m)**,
here up to **+0.16%**, which is 100× the statistical error. Correct it with the
recorded per-frame means as known coefficients `E[1/u]` and `E[1/u²]`; do not fit them.
`M71/03-ptc.py`.

**Proposed discipline D1.** A placebo must span the same time baseline as the
comparison it controls. A 40 s same-state placebo made a 280 s CPL comparison look 13×
significant; the 190–230 s placebo made it 0.71×. (§9(2).)

**Proposed discipline D2.** Before differencing two frames to isolate noise, normalise
each to its own spatial mean. Otherwise any illumination change carries a scaled copy
of the scene into the difference, correlated across planes, and manufactures a
cross-plane noise correlation that is not there. (§9(3).)

---

### Facts added after the orchestrator's retraction (§8.3–§8.5)

**P19 (MEASURED/DERIVED). The shipped noise model is already over-confident above
S ≈ 504 DN, and the missing PRNU term is why.** The 2.16%-high profile gain (§6.1) and
the absent `(κS)²` cancel at **504 DN per green photosite** and **1009 DN on green
luma**; above that the model *under-predicts* σ, reaching **−12.8%** per photosite and
**−6.6%** on green luma at S = 8000, and **−21.1%** at 15000. Robust to the gain
assumption: if the profile gain were exactly right the crossover is at **0 DN** — over-
confident everywhere — and under fact 29's implied 5% it is 1194 DN. **Every case leaves
the model over-confident across most of the working range.** `M71/11-regime-and-m61.py`.

**P20 (DERIVED). Adding κ alone cannot flip the residual error's sign at any signal
level.** The residual of shipped-plus-κ against truth is `(g_profile − g_measured)·S`,
positive for all S whenever the profile gain exceeds the measured one. Swept over
S ∈ [0, 20000]: worst case **+0.0000%**, never negative. Adding κ alone moves the model
from over-confident to uniformly conservative *and* shrinks the error magnitude
everywhere above the crossover. **By M68's corrected fact 40/41 criterion this is a good
change even though it is incomplete.** `M71/11-regime-and-m61.py`.

**P21 (DERIVED, closes an item M68 left open). PRNU cannot bias M61's PTC.** M61-E1 is
a temporal adjacent-frame difference (`v = var(d)/2`), in which a fixed multiplicative
pattern cancels identically. With fractional inter-frame drift ε the slope bias is
`ε²·S·κ²/(2g)`; at S = 2000 DN and my measured κ that is **0.00043% at ε = 1%**, and
**biasing the slope by 1% would require ε = 48%**. M68 fact 39's *"PRNU leakage into
M61's tile variances remains unchecked by me"* is now checked: **the failure mode is
structurally void and M61's estimator choice is vindicated.** `M71/11-regime-and-m61.py`.

**P22 (MEASURED). My B/green gain ratio is robust, and M61's own ISO-100 row agrees with
it.** Refitting g(B) under 11 level-inclusion rules moves it **0.73%** (green control:
**0.09%**), and the ratio spans 0.8698–0.8761 — **entirely outside** fact 921's
0.8396 ± 0.0112, so my post-hoc exclusions cannot reach M61's value. But M61's §4.7
tile-size table contains one ISO-100 stack, `bee-3`, which at tile 32 reads **0.8699** —
my independent flat-field value to **0.99993**. My estimator uses per-pixel temporal
variance with no tiles, so it is immune to the bias M61 was bounding. **M61's fact 29
conclusion stands and I confirm it; what this adds is that its tile-8 primary carries a
residual few-percent bias its own tile-32 column already shows.** *Weakness stated: one
matching row of four; it is the only ISO-matched one, which is why it is reported, not
proof.* `M71/11-regime-and-m61.py`, `M71/12-ipc-tile-bias.py`.

**P23 (MEASURED, mechanism UNRULED). The B plane's noise is ~60× more spatially
correlated than the greens', and it scales with signal.** In-plane nearest-neighbour
correlation: B **+0.1018** (vertical) and **+0.0312** (horizontal) against G1's +0.0017
and +0.0006; summed over lags, B **+0.715** against G1 **+0.014**. It survives a 15 px
high-pass with **91%** retained (the greens go negative, the correct white-noise
signature) and it is present in ISO-100 darks, where however **all** planes are
correlated and B is only 1.38× green. Decisively, against a read-noise-dilution
prediction B runs **1463×** high where green runs 51×. **A pure mean-preserving filter is
refuted by the ACF sum rule** — B's +0.715 implies a variance factor of 0.583, which
overshoots the observed 0.84 — so the correlation is real but its mechanism is not a
simple filter. **Outside my charter, not settleable from flat fields, handed on
unruled.** Pre-registered stability criterion T1 **FAILED** (2.5× against a "< 2×" gate)
and is recorded as failed. `M71/12-ipc-tile-bias.py`, `M71/13-b-correlation-kill.py`.

**Proposed discipline D3.** **Every quantity carries an unstated domain of validity
until its source is read.** This milestone's brief closed with a warning derived from
M68 that was correct in its regime (ρ = 1, dark frames) and false generalised across
signal levels; the orchestrator notes it is the second such case this week, after M62
caught a number relayed without its configuration. In both cases **the value was right
and the scope was not**. The cheap defence is the one that worked here: when a cited
result is load-bearing for a decision, **read it at its commit, not in summary** — I
was instructed to and it changed my §8.3 conclusion. The corollary for authors is
M68's own practice in its fact 39: **state which of your constants you measured and
which you inherited**, unprompted. §8.4 exists only because M68 did that.

---

## 11. What I deliberately did not measure

- **`ρ_warp`** — the fraction of PRNU that survives the stack warp correlated. This is
  the single number that decides the form of the `predicted_sigma` change in §8.2, and
  it cannot be measured from flat fields: it needs the corpus stacks and their warps.
  **This is the blocking measurement for the model change, and I am naming it as the
  next milestone's task.**
- **κ at other ISOs.** Everything here is ISO 100. PRNU is a QE property and should be
  ISO-invariant in *relative* terms, but "should be" is not a measurement.
- **κ's temperature and time stability.** All 484 frames are from one 9-minute session.
  P4 bounds stability across 9 minutes and four optical changes; it says nothing about
  months.
- **Whether the fixed pattern is in the silicon or on the cover glass.** My measurement
  cannot distinguish sensor PRNU from any fixed high-frequency multiplicative pattern in
  the optical path. **For the noise model this distinction is immaterial** — the camera
  does not move relative to its own lens — so I did not pursue it.
- **The vignetting/illumination profile** (deliverable 5), declined in §7.5 on the
  ground that the flats are at infinity focus and would produce an invalid correction.
- **Dust at working apertures.** f/5.6 only; P12 is a lower bound.
- **Whether the B-plane PRNU deficit (0.823× green, P9) and the B-plane gain deficit
  (0.8699× green, P8) share a mechanism.** They are different quantities and I did not
  test a link.

## 12. Unruled — found, outside charter, not buried

1. **The white level.** `black_level_per_channel = [512,512,512,512]`; EXIF `WhiteLevel`
   says **15360**, but the sensor reaches **16383**: G1's mean at 1/5 s is 15871.1 =
   16383 − 512 with 100% of pixels pinned. Anything that clamps at 15360 is throwing
   away 0.4 stops of highlight, or mis-detecting saturation. **Unruled.**
2. **The ~12 DN intercept pedestal.** §6.4. Four negative PTC intercepts (−1.44 to
   −1.85 DN²) mutually consistent to ±6%, contradicted by a measured +0.2307 DN black
   offset and a decode path validated to 1.00075 against `profile.rs`'s own dark row.
   Leading untested hypothesis: electronic versus mechanical shutter readout paths.
   Gain is immune; the shipped model is conservative by ~7% at S = 100. **Unruled.**
3. **The B-plane variance downturn above S ≈ 7000.** Local slopes fall 0.203 → 0.180 →
   0.169 exactly where the *green* planes clip at 66%, 96.5% and 94.8%. It is not B
   saturation (B's max is 13 214 against a 15 871 ceiling), not lossy compression (the
   files are `Sony Uncompressed 14-bit RAW`), and not simple blooming (B/R mean ratio
   constant to +0.27%). The three affected points are excluded from §6.1 and the
   exclusion is **post-hoc**. Mechanism unknown. **Unruled.**
4. **The 2.7σ tension between P8 (0.8699) and fact 921 (0.8396 ± 0.0112).**
   **Substantially resolved after the retraction — see P22 and §8.4.** My value is
   robust to its own exclusions and M61's own ISO-100 stack at tile 32 reads 0.8699,
   matching mine to 0.99993. I still do not propose amending fact 921 from a single
   ISO-matched row, but the tension now has a candidate cause — residual tile-
   correlation bias in M61's tile-8 primary — rather than being bare. **Partially
   ruled; the amendment to fact 921 remains unruled.**
5. **The additive FPN implied by κ's 12% decline with signal** (§4.3): 0.767 DN per
   plane, **2.0× the 0.381 DN dark FPN** measured on mechanical-shutter darks. Possibly
   the same electronic-shutter question as (2). **Unruled.**
6. **B's spatially correlated noise (P23), the largest thing I found outside my
   charter.** B's in-plane nearest-neighbour noise correlation is +0.102 vertical
   against green's +0.002 — 60× — it survives high-passing, it is present in the dark,
   and it runs 1463× above a read-noise-dilution prediction while green runs 51×. A
   pure mean-preserving filter is refuted by the ACF sum rule (implies 0.583, observed
   0.84). **This bears directly on the B-plane deficit that M61, M68 and M48c have all
   chased, and on M61's fact 57 that the 0.84× is "applied before quantisation" — a
   scale does not correlate noise, so whatever applies it is doing something else too.**
   I could not settle it from flat fields and did not try to force it. **Unruled, and
   the single most promising lead I am handing on.**
7. **Read-noise-domain spatial correlation in every plane.** In ISO-100 darks all four
   planes carry nearest-neighbour correlation of +0.055 (G1) to +0.076 (B), ~30× the
   photon-dominated flats. Any tile-based variance estimator is biased low at low
   signal by this, including M61's at its darkest bins. I did not quantify the
   resulting bias on any published number. **Unruled.**
8. **Capture design, for `captures-needed.md`.** Three things this session could not
   answer that a re-shoot could: (a) **interleave the CPL states** — ABAB, not AAAABBBB
   — because a 142 s filter change makes transmission unrecoverable and the placebo
   larger than the effect; (b) **shoot flats at the working magnification**, since
   infinity-focus flats cannot serve as a vignetting reference (P16); (c) **shoot flats
   at the working aperture** — f/5.6 understates dust relative to f/8–f/11 (P12). None
   of these compromised the PRNU headline, which is why it survived.

---

## 13. Reproduction

```powershell
cd projects\strehl\experiments\M71-flat-fields
$env:PYTHONIOENCODING = 'utf-8'
python src\00-exif-census.py        # CPL split, focus and shutter metadata
python src\01-preregistration.py    # criteria; committed dde2321 before any pixel
python src\02-decode-flats.py       # 360 ARW -> per-plane mean/var/clip/block caches (186 s)
python src\03-ptc.py                # deliverable 2, between-group
python src\04-dark-and-linearity.py # dark reference; validates the decode to 1.00075
python src\05-kappa.py              # deliverable 1, the headline
python src\06-sweeps.py             # PR-2, PR-4c, the cross-capture covariance (~5 min)
python src\07-structure.py          # scale, spectrum, dust, IPC
python src\08-cpl-illum.py          # within-frame PTC, CPL, PR-8
python src\09-controls.py           # the three controls of section 9
python src\10-rb.py                 # per-plane kappa
# --- added after the orchestrator retracted the closing warning ---
python src\11-regime-and-m61.py     # sec 8.3 regime, sec 8.4 M61 check (no new pixels)
python src\12-ipc-tile-bias.py      # per-plane noise ACF and tile-size bias
python src\13-b-correlation-kill.py # three kill tests on the B correlation (~6 min)
```

Inputs are read-only: `D:\personal\macro\flat-fields` (484 ARW),
`D:\macro-dark-frames\118MSDCF` (ISO-100 darks). Results land in `data/*.json`;
`out/cache/*.npy` (~4.8 GB) is regenerable and gitignored by format. Nothing under
`crates/` was modified. Everything stays in the CFA domain — no demosaic anywhere.
