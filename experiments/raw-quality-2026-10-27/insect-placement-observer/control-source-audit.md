# Independent control source audit

2026-10-27. SOURCE / MATH REVIEW only. The core observer author reviewed the
separately authored controls; no test, numerical job or RAW read was executed
by this reviewer. No remaining source blocker found for the frozen bounded
commissioning run. Passing results have not been observed or assumed.

Bindings reviewed:

- `core-controls.rs`:
  `b7b92dd66a99c9b9079d0732d0c6c01f9c9dbf774f612b4762fb2d1402c5f4e9`
- `controls.rs`:
  `2af53e14c82ceb52a31fc68db105ad122b03cc5df832acdac71bde84c3b91f82`
- `controls-protocol.md`:
  `ccf784230cfc5b0534fa2fd6b9c4bbd1c5806310fbb41c019105b8e83337883b`

## Geometry and noise

The source renderer evaluates fixed continuous Fourier components directly,
rather than interpolating a photograph. Its inverse affine coordinate map
gives the stated reference-to-moving displacement at the aligner's literal
fitting centres. Gaussian attenuation uses the transformed source-coordinate
frequencies. A separately seeded fixed guide-noise draw is added after that
attenuation, so defocus does not artificially smooth acquisition noise. This
is a synthetic guide model, not a calibrated Sony sensor model.

The geometry score uses all 35 predeclared first-pass sites, including eventual
MAD outliers, and refuses a missing correlation. On this symmetric rectangular
grid, the declared anisotropic template has zero translation/rotation inner
product. Its removed scalar term also makes its inner product with isotropic
scale zero. Projecting measured vectors onto it therefore does not mistake an
arbitrary fitted similarity component for this planted non-similarity mode.
That statement depends on the fixed population; it would not transfer to a
survivor-only or asymmetric field population.

The nulls gate that one signed mode and mean displacement, not every possible
defocus bias or residual field. The protocol correctly retains scatter and
limits the interpretation. No straight-line deep track is substituted for
measured breathing curvature; this is explicitly a pair-only commission.

## Producing-path checks and pre-run repairs

Three narrow issues raised during review were resolved before execution:

1. The factor-two foil now alters copied measured displacements and traverses
   the same geometry scorer. It no longer merely multiplies the reported
   amplitude afterwards.
2. The fixed boundary case exercises the actual public iterated pair path.
   At origin x=350, a 32-wide template translated by +2 reaches the width384
   boundary but fits. The subsequent seed-warped full radius4 search support
   extends beyond it. The test requires actual pass1 refusal, at least two
   OOB tiles, selected pass0, and unchanged ordinary/observed results. It does
   not fabricate a failed trace. Whether the exact matcher reaches those
   conditions remains a run result, not a source-review assertion.
3. The wrong-phase fixture now copies R/B values into synthetic green slots
   and calls the actual `green_luma` consumer. It no longer substitutes an
   independently calculated alternate expression. A G1/G2 swap would have
   been ineffective because the producing guide averages them.

The flat stage, coarse refusal, fixed local outlier and later-failure cases
retain masks/censuses and distinguish unavailable values from rejected ones.
The CLI test calls the real measurement helper with and without collection,
checks all ten requested pairs and returned edge bits/order, then sends both
edge sets through the actual shared `finish_measured_map`. It compares complete
map text and all placement bits, including the two refused frames. The three
identical texture guides establish static observer parity, not independent
acquisition information or physical alignment accuracy.

Input bit/hash checks and selected-pass/result correspondence are explicit.
The current five-guide fixture does not exercise an unavailable pyramid/plane;
those branches were source-reviewed separately, so no runtime coverage claim
is made for them. Likewise, these controls do not establish the original
photographs' common field/focus support. The complete observation still needs
the planned support review before any signed-vector interpretation or proposed
placement correction. No extra sweep or research branch is requested.
