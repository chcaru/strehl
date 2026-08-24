# M103b — PRE-REGISTRATION

Written before the analysis in `src/curvature.py` was run and before any change
to `align.rs` in this arm. Bars are stated with their refutation thresholds. If a
bar moves after a result is seen, that is recorded here in place, loudly, with
the reason.

## Disclosure, up front

`data/truth-dense.json` (39-rung independent RAW ladder, no strehl code in the
measurement path) was produced and committed in M103's first arm. **I read it
before writing bars C1 and C2 below.** I could see, from the printed rungs, that
the midpoint sits near `ln = -0.057` where a straight line through the endpoints
predicts `-0.0771`. So C1 and C2 are not blind — they are a formalisation of
something I had already glimpsed. They are stated anyway, with thresholds, so the
claim is falsifiable and so an independent verifier can re-run them. C3-C5 and S1
are genuinely blind: nothing bearing on them has been computed.

## The commission for this arm

The orchestrator's instruction is to **ship the correction**, because M97b has now
priced it: a matched-content, band-limited, masked instrument with a ZOOMNULL
denominator reads **19-32% sharpness win** on `dry-erase-marker-head-cpl` at
`--gate 2`, against a shipped alignment that is a measured null (1.033 / 0.979 /
1.000).

The orchestrator also raises a hypothesis and asks me to try to kill it:

> M102 planted a **linear** breathing track and recovered 96.96%. If the solver
> assumes linear and the plant is linear, that is a statement about arithmetic,
> not about breathing. If the real track is curved, the fix is not a scalar gain
> but a per-frame one.

**This is the gating question for what ships, so it is answered first.**

## Bars

### C1 — is the true breathing track linear? (diagnostic)

MEASURE: deviation of the independent RAW ladder from the straight line through
`(0, 0)` and `(298, ln 0.857140)`, expressed in plane px at the corner radius
`R_PLANE = 2112.8` px.

- **Linear** if max |deviation| <= 10 plane px. A scalar gain is then a
  defensible *shape* correction.
- **Materially curved** if max |deviation| > 10 plane px. A scalar gain is then
  refuted as a shape correction, and M102's 96.96% on a linear plant does not
  transfer to real captures.

10 px is chosen because M97's whole end-to-end residual bar was 150 px and B3's
accepted result was 2.9 px; a shape error of 10 px would be several times the
residual the corrected solve now achieves, so it is the level at which shape
starts to dominate.

### C2 — is the shortfall uniform per frame? (THE GATING BAR)

For each ladder rung `j`, `r(j) = ln_solve(j) / ln_truth(j)`. Restricted to rungs
with `|ln_truth(j)| >= 0.01` so a ratio is not formed against noise.

- **Scalar gain sufficient** if the coefficient of variation `CV(r) <= 10%`. Then
  multiplying the solved log-scales by `1/mean(r)` is a complete correction and
  is the smallest thing that ships.
- **Per-frame solve required** if `CV(r) > 10%`. Then a scalar gain over-corrects
  at some frames and under-corrects at others, and what must ship is the corrected
  *solve* (`AlignConfig::iterated_wide`), not a multiplier.

### C3 — PLACEBO

The truth ladder compared against itself must give `r(j) == 1.0` at every rung and
`CV = 0` exactly. If the analysis moves on identical inputs it is measuring
itself.

### C4 — POSITIVE CONTROL, two arms

1. **Uniform plant.** A synthetic solve track equal to `truth * 0.543` exactly.
   C2 **must** report `mean(r) = 0.543` and `CV = 0`. This proves C2 can return
   "scalar gain sufficient" when that is the truth, so a large CV on the real
   solve is a finding and not a property of the statistic.
2. **Shaped plant.** A synthetic track with a known frame-dependent shrinkage
   (`r(j) = 0.4 + 0.3 * j/298`, CV computable in closed form). C2 must recover
   that CV to within 1 percentage point.

Per discipline 615 neither plant may perturb the mechanism it is measured
through: both are applied to the *log-scale track only*, downstream of every
correlation, so no plant touches tile selection, capture range or peak-locking.

### C5 — the curvature must not be an artefact of the truth instrument

`truth-dense.json` carries its own SELF and PLANT controls. C1 is void unless
SELF reads 1.000 and every PLANT recovers its planted scale. Additionally, the
ladder's NCC must not collapse across the range being called curved — a curvature
that coincides with a confidence collapse is a measurement of the instrument.

### S1 — the shipping bar (sharpness), for an INDEPENDENT verifier

I may not verify my own fix. This bar is registered here so someone else can run
it and so I cannot move it afterwards.

**Named frequency band, per discipline 643.** M104 measured the resample cost as a
null at the comb and **+0.1623 dex near Nyquist**, so a band-averaged number
dilutes exactly the effect in question. Bars are therefore stated in:

- **PRIMARY — `D_nyq` = [0.30, 0.48] cyc/px** (M104's near-Nyquist band).
- **SECONDARY — comb band [0.210, 0.351] cyc/px** (M104's `D_hi`), reported but
  not decisive.
- **Band-averaged numbers are inadmissible for acceptance.** A "no measurable
  difference" from a metric integrating below 0.30 cyc/px does not refute S1.

**PASS** if, on `bee-3-cpl` at `--gate 2`, the corrected solve beats the shipped
solve in `D_nyq` by a margin exceeding the measurement's own dispersion, using
matched content and a ZOOMNULL-style denominator so that resampling and field of
view are not credited to registration.

**FAIL, and I will report it as such,** if `D_nyq` shows no separation. Note that
M103's first arm already established a null on `bee-3-cpl` at `--gate 2` with an
orientation instrument over a *lower* band ([0.20, 0.40] cyc/px, pooled) — so a
null here would be consistent with that and would mean M97b's 19-32% does not
transfer from `dry-erase-marker-head-cpl` to this subject.

### S2 — the waxy-blob artefact

M97b reported "waxy, smeared blobs in the bright low-texture region" in its
GAINED arm, cause unknown, not present in the shipped render. If the correction
ships, this must be looked for on `bee-3-cpl` and reported whether or not it is
found. MEASURE: local variance in bright (top-quartile luma) low-texture regions,
corrected vs shipped, plus a direct look at crops chosen *at fixed coordinates*
rather than by texture ranking — M103's first arm established that texture-ranked
crop selection is circular.

## What I am not permitted to conclude

- That cycle consistency validates anything: M102 measured it under-states real
  alignment error by ~6x (0.604 px against a 0.103 px floor). No bar here rests
  on it.
- That M102's 96.96% exonerates the solver, until C1 is answered.
- That my own S1 measurement is acceptance. It is evidence for a verifier.
