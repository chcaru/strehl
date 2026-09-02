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
    python src\focus.py   --help          # bracket sweep, best-focus plateau
    python src\geom.py    --help          # edge geometry census
    python src\diag.py    --help          # ESF and locus diagnostic
    python src\sfr_run.py --help          # m88lib bridge with substituted locator

Captures are **read-only** at `D:\personal\macro\requests\19-razor-edge`.
Outputs go under `out/` here and to `C:\dev\strehl-out\M128\`.
