# M128 — razor-edge aperture ladder — PRE-REGISTRATION

Status: registered, not yet measured
Written: before any measurement pixel of the ladder is decoded
Stem: allocated in `AGENTS.md` at commit `74f91c4d` (rule 41)

Everything below is fixed before the data speaks. Section 9 lists what is *not*
fixed and why. A number in this document that is not either quoted from a named
prior source or emitted by `src/predict.py` is a defect.

Regenerate every number in section 2 with:

    python src\predict.py

---

## 0. Why this lane exists

M88 (`docs/research/M88-optical-ceiling.md`) wrote a capture specification in its
§8 and then could not execute it. Its §10.3 records the reason plainly: **no
aperture bracket on a fixed subject existed anywhere in the corpus.** The pair it
was forced to fall back on was shot eight days apart, which confounded its own
Bar 3 beyond repair. `D:\personal\macro\requests\19-razor-edge` is that capture,
finally taken: one session, subject untouched, f/5.6 and f/8 and f/11.

The question the corpus has never answered by a real-space method:

> Is the diffraction cutoff of this system at f/5.6 near **87 cy/mm** (fact 1149,
> which assumes a pupil factor `p` = 1), or in the range **105.54–135.17 cy/mm**
> (fact 1152, `p` ∈ [1.310, 1.940])?

**A finding that must be stated up front, because it changes what this lane is
for.** Fact 1152 is *not* independent of fact 27. M5
(`docs/research/M5-diffraction-measured.md`) measured the cutoff model-free from
the raw CFA green-quincunx PSD and bracketed `B` ∈ [2.412, 3.064]; M76b verified
its headline. Substituting M84b's **measured** magnification `m` = 2.7198 into
`p = m/(B−1)` gives `p` ∈ [1.318, 1.926] — which reproduces fact 1152's
[1.310, 1.940] to three decimals. Fact 1152 *is* M5's measurement re-expressed
with a corrected `m`. Likewise fact 1149 is already refuted *given* M84b's `m`,
because `p` = 1 requires `B` = 3.7198 and M5's upper bound is 3.064.

So M128 is not "settle an open question by finding a new number". It is:

1. **Method independence.** M5 works in frequency space on the noise floor of a
   PSD and depends on a photon-transfer noise model, on the green-quincunx
   frequency conversion, and on identifying a knee. A slanted-edge measurement in
   real space shares *none* of those. If two methods with disjoint assumptions
   agree, the result stops being a single method's artefact.
2. **The control M5 could not run.** M5's control C3 was monotonicity of `f_c`
   in `N`. It was **not testable**, because at f/8 and f/5.6 the subject spectrum
   never descended to the noise floor. The ladder *is* C3, run properly.
3. **A falsification test M5 has no analogue for.** Three apertures on a fixed
   subject over-determine a two-parameter model by one. That spare degree of
   freedom can fail.

If the ladder disagrees with M5, that is a more valuable result than agreement,
and it is to be reported as a disagreement, not reconciled away.

---

## 1. The design, and why it works where M88's did not

M88 was blocked by an identifiability problem it states in its §10.2. A measured
edge width is

    rise² = d² + c²

where `d` is the diffraction contribution and `c` is everything about the subject
and the rest of the system. One equation, two unknowns. M88 estimated `c` ≈ 30 µm
against a `d` of ~10 µm, so `c` dominated and the measurement could not proceed.

With **three apertures on a subject that never moved**, `c` is *shared*:

    rise²(N) = s²N² + c²        where  d(N) = a·λ·B·N ∝ N

Two unknowns, three measurements. `c` is solved for rather than assumed small —
**it cancels instead of having to be negligible**, which is the whole point — and
the third measurement is a goodness-of-fit test that can reject the model.
Then `B = s/(a·λ)`, `N_eff = B·N`, `p = m/(B−1)`.

`src/predict.py` §2.5 demonstrates this numerically: injecting `c` = 0, 10, 20
and 30 µm changes the recovered `c` but leaves the recovered `B` **identical to
four decimals** in every case. That is the design claim, checked before use.

The purest form of the test needs no calibration at all. The ratio

    d(N₁)/d(N₂) = N₁/N₂

is free of `m`, of `p`, and of `λ`. If the measured ratio is not 8/5.6 = 1.4286
and 11/5.6 = 1.9643, something other than diffraction is driving the widths.

### 1.1 Two reductions, with primary and secondary named in advance

**Primary — `m88lib.fit_fc`.** Fits `A × diffraction(f_c) × pixel × gauss(σ)` to
the measured SFR. It separates the cutoff from the subject term by the *shape* of
the rolloff, not by width alone, so `σ` absorbs bevel softness and residual
defocus while `f_c` stays free. Yields `f_c` per aperture directly. The test is
`f_c(N)·N` = const. Registered requirement: **`f_c` to 5% relative per aperture**,
which `predict.py` §2.8 shows buys 7.4σ between adjacent hypotheses.

**Secondary — the rise ladder** as written above. Registered requirement: **rise
to 0.35 µm (≈1.4%) per aperture** for 4.3σ (`predict.py` §2.7). It is the weaker
instrument by a wide margin and is registered as a cross-check on the primary,
never as the headline.

The two share the same ESF and so are *not* statistically independent. They are
different reductions of it, sensitive to different systematics: the rise metric is
dominated by the core of the ESF, `fit_fc` by the tails and the rolloff shape.
Disagreement between them is diagnostic and must be reported, not averaged.

---

## 2. Registered predictions

Emitted by `src\predict.py`, output archived at `out/predict.txt`.

| hypothesis | `f_c` at f/5.6 | `N_eff` | `B` | `p` |
| --- | --- | --- | --- | --- |
| H1 — fact 1149 | 87.00 | 20.899 | 3.7319 | 0.9956 |
| H2 — fact 1152 low | 105.54 | 17.227 | 3.0763 | 1.3099 |
| H3 — fact 1152 high | 135.17 | 13.451 | 2.4020 | 1.9400 |

Predicted 10–90% rise in µm, from M88's dense calibration
`rise(f_c) = sqrt((1009.41/f_c)² + 7.19²)` with a negligible subject term:

| hypothesis | f/5.6 | f/8 | f/11 |
| --- | --- | --- | --- |
| H1 | 13.650 | 18.067 | 23.898 |
| H2 | 11.965 | 15.440 | 20.116 |
| H3 | 10.366 | 12.865 | 16.336 |

In green-plane pixels (10.24 µm), which is the unit the ESF is binned in:

| hypothesis | f/5.6 | f/8 | f/11 |
| --- | --- | --- | --- |
| H1 | 1.3330 | 1.7644 | 2.3338 |
| H2 | 1.1685 | 1.5078 | 1.9644 |
| H3 | 1.0123 | 1.2563 | 1.5953 |

**f/11 is the best-conditioned aperture** and f/5.6 the worst: the minimum
adjacent gap grows from 11.71% of the largest rise at f/5.6 to 15.82% at f/11,
and the absolute widths are better sampled. This is stated in advance so that a
later preference for f/11 cannot be mistaken for choosing the aperture that gave
the wanted answer.

---

## 3. The instrument

**Reused unmodified** (discipline 716 — M104c already paid the cost of rebuilding
a slanted-edge estimator, and the repository has ruled that it is not to be paid
twice): `m88lib.sfr_from_sites2`, `esf_from_sites`, `sfr_from_esf`, `deramp_esf`,
`mtf_diffraction`, `fit_fc`, from
`experiments/M88-optical-ceiling/src/m88lib.py`.

**Replaced — the locator, and only the locator.** `m88lib.fit_edge_line`
**fails on this subject**, MEASURED: on `DSC00045.ARW` it returns **+1.3134°**
with residual 2.425 px where a 50%-crossing fit returns **−0.6759°**; the
downstream MTF then exceeds 1.0 and spikes at exactly sensor Nyquist. The cause
is isolated: its stage-1 argmax of the smoothed gradient locks onto the blade's
**specular bevel ridge**, which sits 14.7 green px before the silhouette and is
brighter than the silhouette step itself.

Substituting the locator is legitimate here for a specific reason: **locating an
edge is geometry and computes no frequency quantity.** M88 makes the same
separation itself, in `s05_find_edges.py`. The replacement is
`src/geom.py::crossings` → `src/sfr_run.py::line_from_crossings`, a 50%-crossing
locus with an IRLS-robust polynomial fit.

**The consequence for controls, registered here so it cannot be quietly skipped:
every control in section 5 must be run with the substituted locator in place.**
A control that does not exercise the replaced part certifies nothing. Re-running
M88's battery through M88's own locator would be a green light for code this lane
does not use.

**Regression check that `m88lib` itself was not disturbed:** re-run M88's frozen
battery and require `out/s03_controls.json` to reproduce at SHA-256
`7d08a7ea…c950`, byte-identical, as M88 §9 records.

**Independent cross-check (rule 24):** every headline is re-measured with
`experiments/M104c-mtf/mtf.py`, an independently written slanted-edge
implementation carrying its own commissioning (analytic V1 +0.03%/+0.36%,
positive control V2 0.6689 vs 0.6667, disjoint-crop null V3 +0.00%). Rule 24
requires verification to **re-choose, not re-compute**: the verifier picks its own
ROIs, its own frames and its own settings within the registered bars.

---

## 4. What the subject actually is — measured, not read off the README

Do not trust the capture READMEs over these numbers. All from `DSC00045.ARW`,
`19-razor-edge/horizontal-flat/...-f5.6-cpl`, via `src/geom.py`, `src/diag.py`,
`src/focus.py`.

| property | measured | README says |
| --- | --- | --- |
| slant, horizontal-flat | −0.53° to −0.68° | ~1° |
| slant, diagonal set | ~34° | ~45° |
| green plane | 2344 × 3514 | — |
| black level | 512 DN | — |
| container ceiling | 15871 DN, and frames **reach it** | — |

The edge-spread function, from the silhouette outward: blade face at ~2600–3100
DN, then a **specular bevel ridge peaking at 6394 DN, 14.7 green px (150 µm)
before the silhouette**, then a smooth monotone ramp through the 50% crossing at
~1500 DN, asymptoting to **~480 DN by +8 px** — near-edge veiling glare, with the
true far background at ~90 DN some 80 px away.

Three consequences that the measurement must respect:

1. **The silhouette step carries only ~906 DN of the ~2800 DN total contrast.**
   The rest is bevel ramp. Anything keying on total contrast is measuring the
   bevel.
2. **M88's frozen `HALF_UM` = 192 µm swallows the bevel ridge at 150 µm.** The
   half-width is therefore a settings choice this lane must commission for
   itself, not inherit. Note `Δf = 1/(2·half_width)`: at 64 µm that is 7.8 cy/mm,
   giving ~18 SFR points across `F_LO..F_HI` = 10..150 cy/mm.
3. **The edge is ragged, and this is the live blocker.** Locus scatter about a
   straight line is **1.23 green px RMS** against a photon-noise prediction of
   **0.044 px** — 28× larger, so it is real subject raggedness, not estimator
   noise. Block IQR ranges **0.18 to 4.0 px along the same edge**. Segment
   selection is therefore mandatory.

### 4.1 Why raggedness is survivable, and the exact condition under which it is

Registration jitter of SD `σ_j` adds in quadrature to the measured width, so it
enters the ladder inside **`c`**, which is aperture-independent and cancels —
*provided `σ_j` is the same at all three apertures.* It will not be exactly: the
crossing estimate is noisier on a blurrier edge.

This is registered as a **control, not an assumption** (§5, C7): measure the
per-segment locus scatter separately at each aperture and require it to be
constant within 20%. If it is not, the jitter is aperture-dependent, it does not
cancel, and its trend must be propagated into the error budget or the lane
refuses.

**Forbidden, stated explicitly:** registering each column on its own *measured*
crossing. That removes the very blur being measured and biases every result
sharp. Registration is on the fitted low-order curve only, order pre-registered
at ≤ 3, where ~10³ crossings make a 4-parameter fit unable to absorb the blur.

---

## 5. Controls — run FIRST, and all with the substituted locator

Rule 9. No measurement number is computed until every control below has run and
its verdict is recorded in `out/controls.json`.

| id | control | bar |
| --- | --- | --- |
| C0 | `m88lib` regression: M88's frozen battery | `s03_controls.json` byte-identical, SHA-256 `7d08a7ea…c950` |
| C1 | analytic plant: `synth_edge_frame2` at known `f_c`, through substituted locator + SFR | recovered `f_c` within ±3% |
| C2 | **the control that matters**: analytic plant with a synthetic bevel ridge at 150 µm and injected raggedness matching the measured 1.23 px | recovered `f_c` within ±5%; if it fails, the lane's method is wrong and no data is analysed |
| C3 | disjoint-crop null: two non-overlapping segments of the same edge, same frame | `f_c` agree within 5% |
| C4 | flat-ROI null: no edge present | refuses, or returns a fit whose quality metric is clearly rejected |
| C5 | planted-ladder control: synthesise three apertures with a known `B` and a known shared `c` | recovered `B` within ±5% of planted |
| C6 | positive-improvement control: plant a *sharper* edge and check the instrument reports it sharper | monotone, and by the predicted amount ±5% |
| C7 | jitter-constancy: per-segment locus scatter at all three apertures | constant within 20%, else propagate or refuse |
| C8 | M104c cross-check on the identical ROI | `f_c` within 5% |

C6 exists because a defect that makes the number *better* passes every
degradation-only battery trivially. That failure mode is documented in this
repository and the control is not optional.

**Rule 20 — the input that would make each gate FAIL must exist.** For C3 that
input is known to exist already: the 4.0 px-IQR blocks measured in §4 will fail
any straightness gate. For C1/C2/C5/C6 the planted parameters are chosen so that
a deliberately wrong `f_c` is outside the bar by construction; the commissioning
run must demonstrate one such failure, not merely assert it.

---

## 6. Acceptance conditions for a measured segment

Fixed now, before it is known which segments pass.

| condition | bar | rationale |
| --- | --- | --- |
| phase traversal | edge crosses ≥ 4.0 sublattice px over the ROI | slanted-edge phase coverage |
| segment length | ≥ 200 clean columns | fit stability; ~10³ crossings for the locus fit |
| straightness | locus RMS about the fitted curve reported per segment, segments ranked by it, and the achieved value propagated into `c` | raggedness enters `c`, which cancels — see §4.1 |
| clipping | **zero** samples at ≥ 15871 DN inside the ESF window | frames are known to reach the ceiling |
| step contrast | ≥ 500 DN at the silhouette | below this the crossing locator degrades |
| min bin count | ≥ 16 samples per ESF bin | binning stability |
| same segments across apertures | the three apertures use the same subject coordinates, verified by cross-correlating the edge locus | `c` only cancels if it is the same `c` |

Focus selection: the best-focus **plateau** per aperture, not a single frame.
`focus.py` gives a clean single peak (`step_dn` 905.9 at frame 27 of 67, falling
monotonically both ways), so the plateau is well defined. Results are reported per
frame across the plateau, and the frame-to-frame spread is part of the error bar.

---

## 7. Verdict rules

Written before the data is seen, so the verdict is a lookup rather than a
judgement.

- **Ladder consistency first.** If the three-aperture fit fails its
  goodness-of-fit test, or `f_c(N)·N` is not constant within the registered
  precision, **no `p` is reported.** The model is rejected and the lane reports a
  model rejection. This gate runs before any hypothesis is compared.
- **Then, and only then**, `B` is recovered and assigned to the nearest of
  H1/H2/H3, with the separation in σ stated.
- **Agreement with M5** is reported as *corroboration by an independent method*,
  with the explicit note from §0 that fact 1152 was never independent of fact 27.
- **Disagreement with M5** is reported as a disagreement. It is not reconciled,
  averaged, or explained away. Both numbers stand and the conflict is recorded.
- **A clean refusal is a complete result.** If no segment satisfies §6, the lane
  reports that this capture cannot support the measurement and says exactly why,
  and the next capture request goes to `docs/captures-needed.md`. Refusing is not
  failing.

---

## 8. Known systematic threats, registered before measurement

1. **Residual defocus scales as 1/N_eff**, so it adds to the *N-dependent* term
   `d`, not to `c`, and biases `B`. This is the most serious threat to the lane.
   Lever: `misc-diagnostic/razor-flat-vertical-slightly-tilted-sw1-cpl`, 51
   frames at **step width 1**, four times finer focus sampling than the ladder's
   sw4 — enough to characterise how much width the focus step itself contributes.
   Single-aperture, so it bounds the effect rather than removing it.
2. **Wavelength.** `λ` = 550 nm is assumed, following M5 §10, which records that
   500 nm moves `B` by about +0.3. The captures are CPL-filtered white light on a
   steel blade; no narrowband control exists. This enters `B` linearly and is
   carried as a stated systematic, not a statistical error.
3. **Bellows factor.** `N` is the marked f-number from EXIF. M5 established it is
   *not* bellows-corrected. The ladder's ratio test uses marked numbers, which is
   correct if the bellows factor is common to all three — it is, since the
   subject never moved.
4. **Aperture-dependent jitter** — see §4.1 and control C7.
5. **Veiling glare** at ~480 DN near the edge against ~90 DN far away is a
   large-scale gradient across the ESF window. `deramp_esf` is the registered
   mitigation; its adequacy at the chosen half-width is part of commissioning.

---

## 9. What is deliberately NOT fixed here

- **The half-width**, because §4 shows M88's frozen 192 µm is wrong for this
  subject. It is chosen by the commissioning sweep in §5, on *synthetic* data
  with known truth, and frozen before touching measurement frames.
- **Which segments** are measured — chosen by the §6 conditions, which are fixed.
- **Which of the six razor stacks** carries the headline. Horizontal-flat is the
  default; the diagonal set's larger slant and the sw1 vertical set are fallbacks
  named in advance so that switching to one is not an unregistered choice.

---

## 10. Reproduction

    cd projects\strehl\experiments\M128-razor-ladder
    python src\predict.py                 # section 2, all registered numbers
    python src\check_prereg.py            # re-derives every number in this doc
    python src\commission_check.py        # proves check_prereg can fail
    python src\census.py  --help          # section 6 acceptance, the go/no-go
    python src\focus.py   --help          # bracket sweep, best-focus plateau
    python src\geom.py    --help          # edge geometry census
    python src\diag.py    --help          # ESF and locus diagnostic
    python src\sfr_run.py --help          # m88lib bridge with substituted locator

Captures are **read-only** at `D:\personal\macro\requests\19-razor-edge`.
Outputs go under `out/` here and to `C:\dev\strehl-out\M128\`.

---

## 11. Amendments

Every change to this document after registration is recorded here, with the
measurement that forced it. Nothing above is edited in place.

### A1 — registration of the ESF is reopened, and made a commissioned choice

Registered in §4.1: *"Forbidden, stated explicitly: registering each column on
its own measured crossing. That removes the very blur being measured and biases
every result sharp."*

**The measurement that forced the change.** `src/census.py` on `DSC00045.ARW`,
horizontal-flat f/5.6, best focus, band-half 60, at three window lengths:

| along-edge window | locus RMS about a straight line |
| --- | --- |
| 64 columns (best block) | 0.296 green px = **3.03 µm** |
| 64 columns (median block) | 0.963 green px = 9.86 µm |
| 800 columns (best window) | 1.309 green px = **13.40 µm** |
| 800 columns, cubic instead of line | 1.283 green px = 13.14 µm |

Command:

    python src\census.py <frame> --win 800 --stride 200 --band-half 60

Two things follow, neither of which was known when §4.1 was written.

1. **The wander is dominated by long along-edge wavelengths.** A cubic removes
   almost none of it (13.40 → 13.14 µm), so it is not a bow; it is wander at
   scales of tens to hundreds of columns, which a low-order polynomial cannot
   follow and a short window does not contain.
2. **The wander is 30× the crossing-estimation noise.** Predicted σ_c is 0.044
   green px = **0.45 µm**, from σ ≈ 25.5 DN at S ≈ 1500 against an ESF slope of
   ≈ 580 DN/px. So straight-line registration is not the conservative choice —
   it *imports* 13.4 µm of subject geometry into the measured width in order to
   avoid a 0.45 µm estimation penalty. Against a smallest predicted rise of
   10.37 µm, that is the difference between a measurement and a null result.

**Why the original prohibition was over-broad.** Blur is an entirely
*across-edge* quantity. Along-edge wander is geometry. Displacing each column by
its own measured crossing therefore cannot remove blur *in principle*; the only
mechanism by which it can bias the result is correlation between the noise in a
column's crossing estimate and the noise in that same column's ESF samples. That
is a real effect, it sharpens, and its scale is σ_c — not the scale of the
wander. §4.1 conflated the two.

**The amended rule.** Registration is on a locus **smoothed along the edge over
`W` columns**. This is the correct family, because:

- Along-edge smoothing over `W` columns cannot remove across-edge blur at any
  `W`, since blur has no along-edge signature at all.
- It reduces the estimation noise, and hence the self-registration bias, by
  √`W`. At `W` = 16 that is σ_c = 0.011 green px = **0.11 µm**.
- It still tracks wander at along-edge scales ≫ `W`, which is where the census
  shows the wander lives.

`W` → ∞ recovers the straight line; `W` = 1 recovers the forbidden per-column
case. **`W` is therefore not assumed, it is commissioned**, on synthetic data
with a planted blur and a planted wander drawn to match the measured 1.23 green
px RMS. The bar: recovered `f_c` within 3% of planted, with the bias reported as
a function of `W` so the choice is made on evidence rather than on the argument
above. Registered as **control C9**.

**Rule 20 — what would make C9 fail.** If the recovered `f_c` rises monotonically
as `W` falls, with no plateau, then self-registration bias dominates at every
usable `W` and there is no safe choice; the lane reverts to straight-line
registration and reports the inflated `c` honestly. That outcome is a valid
result of C9 and must be reported as such rather than treated as a reason to
pick the `W` that gives the wanted answer.

**What does not change.** `c` still cancels across the ladder (§1), so a large
`c` costs precision, not validity. The verdict rules in §7 are untouched. The
choice of `W` is frozen before any real measurement frame is analysed, exactly
as the half-width is.

### Amendment A2 — the registration jitter is aperture-dependent; it is measured and subtracted

**What was registered.** Section 4.1 argued that edge-locus registration error
enters the ESF as a smear that is common to all three apertures, and so joins
the subject term `c` and cancels. Control C7 made that falsifiable: the
aperture-dependent part of the jitter had to be constant within 20%, or the
argument fails.

**The measurement that changed it.** `src\across.py` splits the locus into a
shared part and an independent part by correlating the two green sublattices of
a single frame -- identical geometry, independent photon noise. Measured on the
best-focus frame of each aperture, on common columns:

| aperture | independent locus component | um | 10-90% smear it contributes |
| --- | --- | --- | --- |
| f/5.6 | 0.2672 px | 2.74 | 7.01 |
| f/8   | 0.2885 px | 2.95 | 7.57 |
| f/11  | 0.3555 px | 3.64 | 9.33 |

The spread is 33%, so **C7 fails as written**. Two nulls bound the reading: the
same-frame two-plane null is 0.2672 px, and three adjacent focus positions at
one aperture give 0.2501 px, so focus-step and frame-to-frame variation add
nothing beyond the noise floor and averaging over the focus plateau is safe.

**A quantity that was measured and then set aside.** A three-way comparison
ACROSS apertures gave an independent component of 0.7070 px (7.24 um), which
looked disqualifying. It is the wrong quantity. Each aperture's ESF is
registered on its OWN locus, so what governs its width is that aperture's
self-consistency, not its agreement with a different aperture. Cross-aperture
disagreement is expected whenever the apertures resolve the blade differently,
and the correlation structure says they do: f/8 and f/11 agree with each other
at 0.9154 while both agree with f/5.6 at only ~0.80. The sharpest aperture is
the outlier, which noise cannot produce, because noise is worst at f/11. This
paragraph is recorded so that setting the number aside is on the record rather
than silent.

**The size of the bias if nothing is done.** A jitter of `sigma` contributes
`2.563*sigma` to a 10-90% rise, the 10-90% width of a Gaussian. Regressing that
contribution's variance on `N^2` across the three apertures puts an extra
0.4336 um^2 into the fitted `s^2`. Against `s^2 = 2.917 um^2` under H2 -- the
least-squares slope of `rise^2` against `N^2` over the three registered
apertures, not a hand-copied constant -- that is **+7.2% in `s`, hence +7.2% in
`B`**: 3.076 becomes 3.297, which is a third of the way to H1 at 3.732. Large
enough to matter, small enough not to refuse.

**The new plan, frozen here.** The jitter is measured per aperture, so it is
subtracted rather than merely quoted.

- *Secondary reduction (rise ladder).* Fit
  `rise^2_corrected(N) = rise^2_measured(N) - (2.563 * sigma_e(N))^2`
  where `sigma_e(N)` is the independent locus component reported by
  `across.py` in its two-plane configuration, on the same frames that produce
  the ladder point.
- *Primary reduction (`fit_fc`).* A Gaussian jitter multiplies the MTF by
  `exp(-2*pi^2*sigma_e^2*f^2)`. The measured MTF is divided by that factor
  before `fit_fc` is called. Applying the correction in the transform rather
  than to a summary statistic is the reason the primary reduction stays
  primary.
- `sigma_e(N)` is measured on the ladder frames themselves and is not a free
  parameter. Both corrected and uncorrected results are reported, always
  together.

**Direction of the residual error, stated in advance.** G1 and G2 are offset by
one sensor pixel, so they do not sample identical sub-pixel geometry and their
disagreement includes real subject structure as well as estimation noise.
`sigma_e` is therefore an over-estimate of pure registration noise, the
correction is an over-correction, and the residual bias in `B` is **negative** --
toward H3 (2.402) and away from H1 (3.732). Any result favouring H1 is
therefore conservative under this correction; a result favouring H3 must be
discounted by this amount.

**Rule-20 failure mode.** If the corrected and uncorrected ladders assign
different hypotheses, the lane does not choose between them. It reports the
pair and refuses, because the correction would then be carrying the verdict
rather than the data. If `sigma_e` measured on the ladder frames differs from
the table above by more than 50%, the correction is void and the lane refuses,
because that would mean `sigma_e` is a property of the frame rather than of the
aperture.

**What does not change.** The verdict rules in §7 are untouched, and the
ladder-consistency gate is still applied before any hypothesis is assigned.

### Amendment A3 — the two-pass locator was built, commissioned, and rejected

`src\yield_diag.py` established that the 74.3% / 70.6% / 61.3% crossing yields
are an estimator limit, not a data limit: **no column anywhere fails to cross
the mid level**. Rejections are low contrast (2-3%) or a profile crossing the
mid level more than once -- 23.7% at f/5.6, rising to 35.5% at f/11.

Because that rate is aperture-dependent, recovering those columns looked like a
way to remove an aperture-dependent selection effect. `src\locate2.py`
implements the two-pass locator that does it -- seed a locus from the
unambiguous columns, then take the crossing nearest that prediction -- and
commissions it by planting a known sub-pixel shift into the real band and
requiring the shift back.

It is **not adopted**. The commissioning shows it provably does not disturb the
columns the one-pass locator already reports (0.1201 px vs 0.1201 px on the
identical set, at `smooth_w` 129 and `min_margin` 2.0 px), but the recovered
columns carry 0.3576 px against 0.1201 px for the easy ones. The ambiguous
columns are ambiguous for a reason. Recovery buys 14% more edge at three times
worse locus quality, which would raise the ESF smear the ladder is trying to
minimise.

The aperture-dependent selection effect it was meant to remove is separately
excluded: `across.py` already restricts every comparison to columns common to
all frames being compared, so a differing column set cannot explain the
cross-aperture disagreement.

Recorded because the instrument exists and a later reader will otherwise
rebuild it. It is available behind `crossings2` if a future subject has a
genuinely higher ambiguity rate.
