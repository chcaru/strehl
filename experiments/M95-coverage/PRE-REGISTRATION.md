# M95 arm 5 — pre-registration: does removing the coverage scale recover sharpness?

Written **before** running `x7_scale.py`, `x8_fix.py` or `x9_endtoend.py`.
Only `w0_warpstats.py` has run, and it reports input geometry, not sharpness.

## The claim under test

The orchestrator measured `resample_budget.py` and concluded:

> One gather at k = 0.9315 costs +0.2392 dex — 64.2% of the entire measured
> deficit. … The sub-pixel warp offset is NOT the problem — the SCALE is.
> Emit the cropped region at its native sampling: 6550 × 4367, zero
> interpolation on the coverage axis.

Call this **the magnitude model**: the cost of the gather is a function of how
big the enlargement is, so shrinking the enlargement to zero removes the cost.

I hold a different model, from arm 4. Call it **the phase model**: a Catmull-Rom
gather costs nothing at integer phase and ~0.52 dex at half-pixel phase, and
*any* geometry that sweeps the output across a full cycle of fractional phase
pays the phase-average of that curve. A scale sweeps phase; so does a warp
translation with a non-integer part. The magnitude of the scale sets how *fast*
phase is swept, not how much is lost per pixel. Under this model, removing the
coverage scale while keeping the per-frame warp recovers approximately nothing.

The two models make opposite predictions and this document fixes them in advance.

## What is already on the table (not re-derived here, re-measured in B4)

- Arm 4, committed `56e4cfa`: `B0 → B1` = **−0.2851 dex**. B1 is a *one-frame*
  stack whose warp sidecar is the identity and whose coverage came out
  k = 0.9974 — a 0.26% enlargement, zero translation.
- The orchestrator's R1: k = 0.9315, a 7.35% enlargement, **+0.2392 dex**.

The magnitude model must explain why a 0.26% enlargement costs *more* than a
7.35% one. The phase model predicts they cost the same, because both sweep many
full phase cycles (18.3 and 517.1 across the output width, from `w0_warpstats`).

## Pre-registered bars

### B1 — the discriminating ladder (the decisive test)

Pure Catmull-Rom scale gather, no translation, on real strehl-decoded tiles,
at k ∈ {1.0, 0.9999, 0.9995, 0.999, 0.997, 0.99, 0.97, 0.9315, 0.85, 0.70},
each integrated over a band scaled by its own k.

- **Magnitude model predicts** cost rises with |1−k| across the whole ladder;
  in particular cost(k=0.9974-equivalent) ≲ 0.01 dex, ~28× below cost(0.9315).
- **Phase model predicts** cost is *flat* for every k that sweeps at least one
  full phase cycle across a 256 px tile — that is |1−k| ≳ 1/256 = 0.0039 —
  and falls toward 0 only for k closer to 1 than that.

**I conclude the scale magnitude matters, and the orchestrator's fix has real
value, if** cost(k=0.997) < ⅓ × cost(k=0.9315).

**I conclude the scale magnitude is irrelevant, and the fix is dead, if**
cost(k) varies by less than ±0.04 dex across k ∈ {0.997 … 0.70}, a 100× range
of enlargement.

### B2 — the fix, priced directly

Two arms on the same tiles, using the **real** per-frame warps from
`D:\personal\macro\bee-3-cpl\warpmap.txt`:

- **NOW** — per-frame warp with the coverage scale folded in, sampled at the
  shipped output grid. This is what `fit_to_cover` + `merge_cmd.rs` do today.
- **FIX** — the same per-frame warp with the coverage scale removed, emitted at
  native 0.9315 sampling. This is exactly what the orchestrator proposes.

Both compared to the unresampled base, band-matched.

- **The fix ships if** cost(FIX) < cost(NOW) − 0.10 dex.
- **The fix is dead if** cost(FIX) > cost(NOW) − 0.03 dex.
- Anything between is a partial win and I report it as such.

### B3 — how much of +0.2392 is a units artifact

The orchestrator's script integrates every arm over a **fixed** 0.30–0.48 cyc/px
band. But an arm magnified by 1/k carries the scene's Nyquist at 0.5·k cyc/px,
so for k = 0.9315 its spectrum is empty above **0.4657** cyc/px by construction
while the unresampled baseline has real content up to 0.5. Their band's top
0.4657–0.48 therefore compares real content against a guaranteed hole.

I will run their R1 arm both ways — their fixed band, and band-matched — and
report the difference. No pass/fail; this is a quantification of a bias, and it
is only meaningful if my own controls K1–K5 pass.

### B4 — end-to-end on the shipped binary, re-printed this session

Re-measure `B0 → B1` from the actual TIFFs on disk.

- **Magnitude model predicts** ≲ 0.01 dex (a 0.26% enlargement).
- **Phase model predicts** 0.25–0.30 dex.

This bar is the one that cannot be blamed on my synthetic kernel, because both
images came out of the shipped `strehl` binary.

## Controls — all must pass or I report no arm numbers

- **K1 NULL.** Scale exactly 1.0, offset exactly 0: |cost| < 0.005 dex.
  If the harness blurs while doing nothing, every number is void.
- **K2 DOSE.** Offset ladder 0 / 0.125 / 0.25 / 0.5 px at scale 1.0 must be
  strictly monotone increasing. Catmull-Rom is exact at integer phase and worst
  at the half-pixel; a non-monotone ladder means the kernel is wrong.
- **K3 POSITIVE (discipline 594).** A planted Gaussian blur of σ = 0.30 px,
  applied as the exact transfer function `exp(−2π²σ²f²)` — *not* a sampled
  kernel, which truncates to a delta at small σ and silently reads ≈ 0 — must
  register ≥ 0.15 dex. The instrument must be shown saying otherwise before any
  null it produces is a claim about the world.
- **K4 INTEGER SHIFT.** A pure shift of exactly 1.0 px must cost < 0.005 dex.
  Catmull-Rom at integer phase is a copy; if this reads non-zero the gather has
  an indexing error.
- **K5 BAND-MATCH LEGITIMACY (the control that can void B1).** Resample the base
  by k = 0.9315 with a near-ideal kernel (Lanczos-8), then band-match. This must
  read < 0.05 dex. Band-matching is the step that lets me compare images with
  different sampling densities, and if band-matching *itself* manufactures a
  null then the flat ladder in B1 is an artifact of my correction rather than a
  fact about the kernel. This control is what makes B1 admissible.

## What would falsify my conclusion

If B1's ladder turns out to rise with |1−k|, or K5 fails, or B4 comes back near
zero, the phase model is wrong and the orchestrator's fix should ship. I would
rather find that than defend arm 4.

## Scope declared in advance

This arm prices **geometry** — scale versus translation phase — for one fixed
kernel. It does not revisit which kernel to use (arm 4, `56e4cfa`), it does not
touch election quality, and it cannot speak to anything outside 0.30–0.48 cyc/px
scaled by each image's own coverage.
