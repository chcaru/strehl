# Source-consistency priority after the Helicon comparison

**ARGUED decision: prioritize one source-consistency intervention on the known
photographic defect before extending wavelet covariance to full photographs.**
Covariance remains a correctness requirement if the wavelet route continues;
it is not currently the strongest explanation for these fans.

I inspected the retained native `photo-comparison-1` dark-inclusion and
facet-edges boards. Helicon B has substantially shorter coloured extensions
around the glints, while recognizable facet boundaries remain. C retains much
more spread. This agrees with the retained source witnesses: compact glints
near28/33, extended coloured fans in52/69. The actual Strehl ancestry at the
dark fan strongly selects69 even in the finest band; its late detail is real
source structure being used in the wrong composite context, not simply a
small signal near the injected noise floor.

This is a workflow observation, not identification of Helicon's algorithm.
Its public B/C descriptions and comparison limitations are already bound in
`comparison-plan.md`. The external workflow includes premerge development and
its own alignment; B's success does not prove depth-map smoothing alone causes
the difference. No proprietary implementation was inspected.

Mechanical prior-art searches used separate terms for `depth map`, `depth-map`,
`focus curve`, `unimodal`; `whole colour`, `source consistency`,
`regularization`, `graph cut`, `whole-color`; and `election`, `regularised`,
`regularizer`, `consistency`. Targeted report/source reads found these limits:

- **BUILD-ELECT, especially sections11–16:** ordinary hard whole-image election
  produced smooth, confident wrong-depth collars and hard composite boundaries.
  Replacing the focus statistic by high-pass or maximum-gradient variants did
  not fix the ring. BUILD-BLEND removed that particular low-frequency selection
  mechanism. Its corrected linear comparison, not the withdrawn0.37% toned
  headline, is the relevant precedent. Do not reinstate a global hard argmax.
- **M13 and the new radius32 candidate:** generic spatial borrowing can cross
  depth and erase the very compact feature being protected. The current
  generated candidate loses roughly58–59% of truth-capped glint-core recovery;
  actual nearby structure prefers25 and visibly softens in35. A wider window
  or smoother label map is not the missing evidence.
- **M63:** a second focus-curve peak often belongs to one spreading edge, not
  a second surface. **M96** explicitly retires spatial label coherence as
  evidence of correctness: regularization manufactures it even on arbitrary
  elections. A decisive or unimodal curve can still describe defocused rays.
- **M65:** a large change in elected labels need not materially change the
  admitted source set. Any new field must actually control the colour consumer.
  **BUILD-HALO section33** gates a veil envelope by election coherence; it is
  not a demonstrated whole-colour depth reconstruction and has its own transfer
  limits. M93's motion-discrepancy gate addresses another mechanism.
- Existing graph-cut/guided-map references are proposals/surveys; this targeted
  search found no native actual-consumer quality test of a source-witness
  anchored, spatially connected whole-colour donor assignment. That absence is
  not evidence such an estimator will succeed.

**One minimal untried test:** a fixed local donor-consistency counterfactual,
before designing an automatic depth solver. Use the two already frozen384-native
windows and retained, independently inspected donors28/33. Its implementable
contract, supplied to root before any new output, is:

| Fixed support, output-native pixel centres | Donor index |
| --- | --- |
| Capsule from facet core(2624,2906) to fan(2602,2945) |28|
| Capsule from dark core(3080,2150) to fan(3102,2203) |33|
| Disk centred at nearby structure(3240,2070) |25|

Use one radial mask rule everywhere:1 through distance16native, then
`1-smoothstep((distance-16)/8)` to0 at24native, zero beyond. Distance is to
the closed capsule segment or disk centre. These are fixed geometric supports,
not masks found by scoring the new output. The competing structure is included
specifically because borrowing the glint's donor there already has a visible
counterexample. Index25 is independently witnessed as sharper than35 there.

Build each finest mask at local output-quad centre
`(2*qx+0.5,2*qy+0.5)`; convert coordinates consistently if the implementation
starts from full reference-active coordinates, whose frozen output origin is
(56,38). Reduce masks to every existing Laplacian level with the actual pyramid
Gaussian reduction and its exact phase. The three finest supports are disjoint;
positive reduction preserves summed masks<=1 even when their coarse supports
overlap. Preserve that invariant rather than picking a new winning mask.

For actual normalized baseline coefficient `C_l` and actual gathered donor
coefficients, apply after per-band weight/fallback normalization and before
collapse/InputRange limiting, identically to all four original colour planes:

`C'_l = (1 - sum_r m_l,r) * C_l + sum_r m_l,r * C_l,donor(r)`.

Keep the mandatory terminal mean base exactly baseline. This is coherent
replacement of detail coefficients, not replacement of illumination/DC or an
output RGB blur. It reuses the actual native gather, CA, WB/levels and same
pyramid domain; only the current prescribed donor coefficients need streaming
accumulation, not an aligned-frame collection. Preserve exact baseline values
when every mask is zero. All donor indices and masks are external diagnostic
inputs, not camera constants. The current full consumer output is6920x4612
native pixels; do not reset pyramid context to the diagnostic384x384 windows.

Compare unchanged baseline, this fixed counterfactual and an identical-mask
late69 donor destroyer. This normalized coefficient prescription avoids mixing
arbitrary units of existing soft weights with a unit donor weight. Simply
zeroing forbidden weighted terms would be different: its zero-weight fallback
can silently restore all70 sources and defeat the test. No source-score fitting,
mask enlargement or donor sweep is part of this contract.

The question is whether coherent donor use can simultaneously remove the
source-supported tails, retain compact cores and the different-depth nearby
detail, and avoid the old hard-boundary defect. Seeing only a compact source
again is not a pass. Explicitly inspect the complete window, the donor boundary
and the nearby25 witness; retain the flat-noise cost of selection. This is a
diagnostic with externally supplied labels, not automatic depth estimation or
a shippable selector. A positive result would justify one bounded automatic
label-assignment test; a failure would identify which reconstruction or boundary
constraint blocks that route before committing to a graph solver.

No RAW read, image-generation run, build or production edit was performed in
this audit. Only prior-art search, saved-image inspection and this note changed
the program record. No SOTA or new photographic improvement is claimed.
