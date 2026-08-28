# PREDICTION: `highly-angled-ruler-mm-cpl`, written before its master existed

Written 2026-08-28 01:32:43. At this moment `C:\dev\strehl-out\DELIVER-V6\masters\highly-angled-ruler-mm-cpl.tiff`
does not exist; 12 of 26 masters have rendered and the ruler is not among them.
The point of writing this now is that a prediction made after seeing the number
is not a prediction.

## What I have already measured (MEASURED)

On the OLD masters, all 11 scoreable subjects carry red displaced **outward**
(`ppmR_old` +178 to +470). The ruler is the exception ORCH named in advance: I
measured `ppmR_old = -207.1` (mad 107.6, n=68) during commissioning, i.e. red
displaced **inward** -- the opposite sign. That corroborates his description of
it as showing the lens's natural pattern rather than over-correction.

On the 11 scored subjects the new coefficient shifts red by a nearly uniform
`d_ppmR` of **-186.6 ppm median, range -237.3 .. -131.6**, at 7.2 to 59.8 sigma.
It is negative on 11 of 11.

## The prediction (falsifiable)

**P5.** If the change is a global coefficient rather than something
subject-adaptive, the ruler must receive the same negative shift. Its baseline
is already negative, so the shift moves it **away** from zero:

  predicted `d_ppmR`   : negative, in -237 .. -132 ppm (the observed range)
  predicted `ppmR_new` : about **-394**, in -444 .. -339
  predicted `ratio`    : about **1.9**, in roughly 1.6 .. 2.1  (i.e. ~2x WORSE)

**P6.** The ruler is therefore predicted to be the one subject where the fix
degrades the endpoint, and it should be the ONLY such subject.

## What would refute this

- `d_ppmR` near zero or positive on the ruler => the correction is not a global
  radial coefficient and my model of it is wrong. That is a finding, not a
  footnote, and I would have to withdraw the "global coefficient" reading.
- Any OTHER subject also showing ratio > 1 => P6 is wrong.
- `d_ppmR` outside -237 .. -132 by a wide margin => the shift is subject
  dependent even among the over-corrected subjects.

## Caveat carried forward

My commission of `vc_ca.py` **FAILED its BLUR-ONLY arm on this specific
subject** (paired -77.2 ppm at sigma=1.2, 7.3 sigma from zero) while passing
5/5 on `dry-erase-marker-head-cpl` (paired +0.0 ppm). So this subject is the one
where an equal-blur build difference could contaminate the reading. The bound:
the paired blur sensitivity is **exactly +0.0 ppm at sigma=0.3** on all four
subjects tested, and the largest edge-width change measured between old and new
masters so far is variance ratio 1.0239 (`flat-on-ruler-cpl`), equivalent to
roughly 0.23 px of added sigma. At that level the measured CA contamination is
0.0 ppm. A predicted effect of ~190 ppm therefore sits far above the confound,
but I will report the ruler's width_ratio explicitly and withdraw the row if it
is large.
