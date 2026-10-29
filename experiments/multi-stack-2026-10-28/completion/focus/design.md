# Shared focus evidence

Reuse the existing FocusField two scales, regularized FocusStats anchor and
ThroughFocus sufficient statistics; do not invent a second focus selector or
retain an aligned frame volume. A regularized anchor selects the neighbourhood
for a diagnostic fit, not an output pixel. Output values still require
noise-gated averaging/direct-sample reconstruction.

Per-pass evidence lives in that pass anchor green-quad gauge. Coordinate is
fractional acquisition ordinal, not physical depth or a calibrated posterior.
Expose local log-Gaussian width, prominence in the existing fine-response noise
units, untruncated regularized perplexity, fine/regularized disagreement,
boundary status, coverage versus usable-focus masks, and original global IDs.
Mask unsupported response values before either fold and verify the same ordered
acquisition census in both passes. Require a complete local triple, significant
focus variation, and no strong distant competing mode for a usable focus fit.
A local width is a shape diagnostic, not a confidence interval.

Primary literature read: Nayar and Nakagawa, Shape from Focus (PAMI1994),
https://cave.cs.columbia.edu/Statics/publications/pdfs/Nayar_PAMI94.pdf . It models
local through-focus variation for textured surfaces and does not justify dense
depth in textureless regions. Existing ThroughFocus implements the repository's
measured distinction between position and height interpolation; retain it.
Hasinoff et al.2016, https://people.csail.mit.edu/hasinoff/pubs/HasinoffEtAl16-hdrplus.pdf ,
uses constant-exposure RAW bursts and robust alignment/merging. Its results do
not transfer automatically to unequal-focus or exposure-varied passes.

Controls: flat response first (no depth evidence), known Gaussian centres and
widths, reversed/unequal track identity, separated comparable peaks, boundary
peak, missing footprint, duplicate/mismatched second pass and undersized budget.
A synthetic Gaussian validates the diagnostic arithmetic, not a physical camera
focus calibration. Real held-out geometry and edge witnesses remain required.
