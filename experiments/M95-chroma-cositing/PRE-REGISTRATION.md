# M95 arm 2 (chroma co-siting) — pre-registration

**Frozen before any displacement was measured.** Committed ahead of the first
result. The prediction below is *derived from the CFA geometry*, not fitted to
data.

## The question

Does strehl's default binned output misregister the red and blue channels
against each other by a fixed sub-pixel amount, because the R and B photosites
sit at opposite corners of the 2×2 quad and are written into one pixel as if
co-sited?

## The derivation, done before looking

`merge_cmd.rs` writes, for binned output pixel `(px, py)`:

```
R = est.value(R,  i)          -> sensor site (2px,   2py)
G = est.green_mean(i)         -> mean of (2px+1, 2py) and (2px, 2py+1)
B = est.value(B,  i)          -> sensor site (2px+1, 2py+1)
```

Quad centre in sensor coordinates is `(2px+0.5, 2py+0.5)`. Therefore:

| channel | sampling centroid, relative to quad centre | in **binned** px |
| --- | --- | --- |
| green | `(0, 0)` — the two greens straddle the centre | `(0, 0)` |
| red | `(−0.5, −0.5)` sensor px | `(−0.25, −0.25)` |
| blue | `(+0.5, +0.5)` sensor px | `(+0.25, +0.25)` |

**Predicted displacement of blue relative to red: `(+0.5, +0.5)` binned px.**
Predicted displacement of green relative to red: `(+0.25, +0.25)` binned px.

The demosaiced render is the control. Malvar–He–Cutler estimates all three
channels *at every photosite*, so all three are co-sited by construction and
the constant term must collapse to zero there.

## The confound I must separate

Lateral chromatic aberration also displaces R against B, and this lens is a
100 mm macro with a 2× teleconverter — a stacked optical system with no reason
to be free of it. LCA cannot be assumed away.

It is separated by field signature. The binning defect is a **constant** vector
at every field position. LCA is **radial**: zero at the optical centre, growing
outward, directed along the radius. Fitting

```
d(x, y) = c + k · r̂(x, y)
```

over many field positions splits them. `c` is the binning defect; `k` is the
lens.

## Pre-registered bars

Let `c_bin` be the constant term fitted on the binned render and `c_demo` the
constant term on the demosaiced render of the **same frame**, both expressed in
binned pixels.

- **CONFIRMED** — the defect is real and is the predicted one — if
  `|c_bin − (+0.5, +0.5)| < 0.10` binned px **and** `|c_demo| < 0.10` binned px.
- **REFUTED** — there is no fixed misregistration — if `|c_bin| < 0.15` binned px.
- **CONFIRMED BUT NOT AS PREDICTED** if `|c_bin| > 0.25` px but it is not within
  0.10 px of `(+0.5, +0.5)`. This would mean something else in the path moves
  the channels and my geometric derivation is wrong.
- **INDETERMINATE** otherwise, or if any admissibility control below fails.

## Instrument admissibility (discipline 594)

A null is a claim about the world only if the instrument could have said
otherwise. The estimator is not admissible until all of these pass, and they
are run **before** the real measurement:

- **C1 — positive control.** Plant known shifts `0.0, ±0.25, ±0.50, ±0.75` px
  into a real crop with an exact frequency-domain phase ramp. The estimator must
  recover every one to within **0.03 px**.
- **C2 — null control.** A crop against itself must read `(0, 0)` to within
  **0.01 px**.
- **C3 — independent cross-check.** `skimage.registration.phase_cross_correlation`
  at `upsample_factor=100`, a completely different algorithm (upsampled
  correlation peak, not a phase fit), must agree within **0.05 px** on the same
  crops. If it does not, my estimator is not trustworthy and the arm stops.
- **C4 — power control (discipline 595).** The claim `c_demo ≈ 0` is an absence.
  It is only admissible if the *same instrument, same ROIs, same settings* reads
  the large value on the binned render. Reporting `c_demo ≈ 0` without that is
  forbidden.
- **C5 — stimulus validity.** The planted shift must be an exact translation, so
  it is applied as a phase ramp, never `scipy.ndimage.shift`. An interpolating
  shift blurs, which would entangle the planted displacement with the
  interpolator and mislabel the stimulus — the same failure mode that invalidated
  a truncated-Gaussian blur stimulus earlier in this milestone.

## What would falsify the whole arm

If `c_bin` is measured near zero on real data while C1–C4 pass, the geometric
derivation above is simply wrong and the binned path already co-sites its
channels somewhere I did not read. I would report that.

## Scope declared in advance

This arm measures **registration between colour channels**. It does not measure
luminance sharpness, and a fix for it is not a fix for softness in green. Green
is the channel carrying most of the luminance detail and it is already correctly
centred, so the expected visible benefit is on **coloured edge fringing and
chroma detail**, not on green MTF.
