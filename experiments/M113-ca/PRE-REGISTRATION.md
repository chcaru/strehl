# M113-ca -- pre-registered bars

Written BEFORE any measurement was run (AGENTS.md rule 20). Target: ORCH's
lateral-CA gain claim, SYNTHESIS facts 1511-1514.

## What I am testing

ORCH claims the shipped lateral-CA correction has correct radial SHAPE and a
scalar gain of 1.444 (over-corrects ~44 %), implying a red-coefficient fix of
x0.692, and that this refutes ORCH's own fact 1501 (extrapolation past the
r = 0.788 fit support).

## The gap I identified before running anything

`ca_shift.py`'s positive control plants **integer** pixel rolls only
(-2, -1, 0, +1, +2). Every reported quantity is **sub-pixel**: R_off peak
0.155 px, residual 0.047 px, tangential floor 0.033-0.051 px, applied ~0.22 px.
The parabolic sub-pixel peak fit -- the only part of the estimator that produces
those numbers -- contributes approximately nothing at an exact integer shift,
because the correlation peak already lands on a grid point. **The control
therefore cannot exercise the machinery every reported number depends on.**

Separately: `optics.rs` advertises 2.977 output px of red-green misregistration
at the corner (eps_R = -704.5e-6 x 2112.9 plane px x 2). At r = 0.45 that is
1.340 output px. ORCH measured needed = 0.155 px and applied = ~0.224 px there.
That is a factor of ~6-9 unexplained. A UNIFORM estimator attenuation cancels in
the ratio applied/needed and would leave 1.444 intact; a NON-UNIFORM one does
not. B1 decides which.

## Bars

- **B1 sub-pixel linearity of ORCH's estimator.** Plant band-limited Fourier
  shifts into red, run ORCH's `shift_of` unmodified. PASS if slope of recovered
  vs planted over |d| <= 0.5 px is in [0.90, 1.10] AND max |residual| <= 0.05 px.
- **B2 my estimator on the same plants.** PASS if slope in [0.95, 1.05] and max
  |residual| <= 0.03 px over |d| <= 0.5 px. If B2 fails my instrument is not fit
  to judge ORCH's and I report that instead.
- **B3 gain agreement.** My median gain AGREES if within +/-0.15 of 1.444
  (1.294 .. 1.594). Outside that is a material difference and is the finding.
- **B4 second stack transferability.** Gain on a second capture must be within
  +/-0.20 of the bee gain. Otherwise the x0.692 scalar must not ship.
- **B5 fact 1501 refutation power.** The refutation is SUPPORTED only if there
  are >= 2 independent rings beyond r = 0.788 whose |needed| >= 3x the noise
  floor, AND the inside-vs-outside gain difference is smaller than the
  ring-to-ring spread WITHIN the inside group. Otherwise UNDER-POWERED.
- **B6 radial-scale plant.** Plant a radial magnification (not a uniform roll),
  resampling R and G identically so no sharpness difference is introduced. PASS
  if the recovered eps is within 10 % of planted. This is the control ORCH lacks.
- **B7 centre null.** At r ~ 0.045 the radial displacement must not exceed the
  tangential floor. Above it means scene structure is being read as CA.
- **B8 closure against the source model.** applied_measured / (2.977 * r) must
  lie in [0.8, 1.25] for the measurement and the shipped coefficient to describe
  the same world. Outside that, one of them is wrong and the gain's
  INTERPRETATION is unsettled even if its arithmetic is right.

## Chosen before looking at results

Rings: the same radii ORCH used, plus r = 0.88 and r = 0.93 explicitly retained
so the outside-support group is not n = 1. Window size 128 px, matching ORCH, so
a difference cannot be attributed to windowing. Optical centre = image centre,
as ORCH assumed; B7 tests that assumption.