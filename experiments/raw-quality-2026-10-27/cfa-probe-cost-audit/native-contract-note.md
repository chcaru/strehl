# Actual RAW boundary and the demosaic-once contract

2026-10-27. **VERIFIED by source inspection:** the current dual-tree photograph
does not satisfy a literal demosaic-once reconstruction contract. Original
storage is u16 CFA and there is no aligned-frame volume, but those facts alone
do not make its intervening reconstruction entirely original-CFA based. The
Device256 recommendation preserves this existing boundary; it does not repair
the contract gap. No code, RAW or numerical work was performed for this note.

## Exact producing path

`dual-tree-cfa/full-adapter.rs::full_gather` calls the ordinary CPU full-resolution
warp, with Malvar, Catmull, CA off and direct planes off. In
`align_cmd.rs::warp_frame_fullres_coordinates_impl`, each source undergoes:

1. Original active sensels become f32 `(code-black)*source_WB` on their Bayer
   sites, initially retaining negative values.
2. MHC reconstructs full native-resolution R, G and B planes. These contain
   both measured sites and cross-color estimates at missing sites.
3. Catmull interpolates the appropriate reconstructed channel at each warped
   reference CFA phase. The source phase offsets and actual runtime transform
   matter; this is not independent interpolation of each original CFA plane.
4. `writeback_fullres_site` computes `sample*inverse_WB+black`, rounds, clamps to
   `[0,65535]`, and stores u16. Uncovered sites become rounded black.
5. `extract_planes` reads that remosaic and supplies `max(code-black,0)` as four
   f32 phase planes to the candidate. Its sixteen original-u16 noise draws pass
   through this same complete boundary before coefficient variance estimation.

After coefficient fusion/inversion and the source hull, `write_result` assembles
an f32 CFA mosaic, applies the fixed output WB/range and existing nonnegative
writer boundary, then calls `write_demosaiced_with_master`. That writer performs
MHC again before the color matrix, linear master and display rendering.

Thus this is **RAW-fed, four-plane fusion after per-source MHC/Catmull/remosaic**,
followed by final demosaicing. It is neither RGB-stack fusion nor reconstruction
that only ever consumes measured same-color CFA samples. The first MHC stage
has not become harmless simply because its output is packed back into Bayer.

## What the comparison can establish

Both canonical and candidate share this front end. Their paired complete-output
comparison still isolates the changed merge/reconstruction choice *conditional
on that front end*: an extra per-source demosaic was not introduced in only one
arm. However, absolute fidelity and the candidate's color/detail behavior are
coupled to the already mixed channel estimates, interpolation covariance,
requantization and below-black rectification. The propagated probe captures
noise through that operator; it does not restore lost signal or prove the
operator physically correct. Do not call a resulting gain proof of the
demosaic-once RAW-native architecture, or attribute a loss solely to source
weights without an upstream comparison.

For finite covered unsaturated samples, rounding alone changes the continuous
sensor-domain value by at most0.5DN before subsequent operations. This does not
bound nonlinear fusion error. Conversely, it supplies no evidence that rounding
causes the visible softness. Identity at actual measured phase sites can remain
exact; the retained source149 green identity is compatible with this chain and
does not validate every nonidentity source pull.

## Prior results constrain the next test

- [Direct-plane results](../../native-direct-planes/results.md): Rounded is an
  exact storage shortcut. Float removes integer rounding but retains per-source
  MHC, WB/pedestal arithmetic and both clamps. Its fixed flat experiment missed
  the required benefit, with small changes rather than demonstrated visible
  harm; float detail renders were withheld. Neither mode is an original-CFA
  sampler, and this result does not reject a different direct-CFA architecture.
- [October direct-CFA results](../../raw-quality-2026-10-26/results.md) and the
  [unchanged-green falsifier](../../raw-quality-2026-10-26/cfa-residual/results.md):
  original-color cubic R/B and quincunx green preserve measured-site identity
  but lose fine neutral structure. Green RMSE35.0053 became67.0887DN in the
  fixed witness; even perfect R/B could not repair it. Removing requantization
  is not evidence that this bandwidth/phase defect disappears. Four independent
  half-resolution planes are an even different green-sampling choice.
- The [continuous shared-pupil boundary population](../../../docs/research/M194g-larger-pupil.md)
  was independently commissioned, yet its textured noise-off output retained
  about62-63DN window error despite favorable flat noise changes. The separate
  [native boundary-radiance trial](../../native-boundary-radiance/results.md)
  consumed original CFA with known geometry and reduced noise while substantially
  worsening textured boundaries. Original-CFA input or supplied geometry alone
  is not a fidelity guarantee.
- The retained full-chip `native-cfa-kernel/results.md` in the original checkout
  also rejects both positive-kernel original-CFA reconstructions for softened
  rails/contacts/scratches. Its particular kernel/focus model is not a family
  prohibition, but repeating that reconstruction is not a new route.

## Smallest honest contract-correct follow-on

There is no currently demonstrated drop-in replacement satisfying both the
contract and photographic quality. The smallest *boundary test* is a separately
named original-CFA f32 callback: immutable u16 source, the existing actual
phase/channel geometry, direct original-color samples, signed black-subtracted
f32 output, no per-source RGB reconstruction, no remosaic/u16 store, and one
final demosaic after the unchanged four-plane consumer. Apply exactly the same
callback to all sixteen original-source probe draws; recompute its floors and
hull rather than importing MHC-path statistics. An on-demand algebraic rewrite
of the MHC stencil is not evidence that the cross-color reconstruction vanished.

Reuse the already implemented fixed direct-CFA sampler only as a clearly named
challenged arm, not as an accepted quality repair. Commission actual consumed
phase identity/offsets, signed headroom, covariance, flat noise and the existing
neutral/color adverse fixtures before any complete observation. Preserve its
known failures and compare the same dual-tree consumer against the held MHC
boundary; do not change filter banks, gate or tone simultaneously. A full-photo
observation would need an explicit root decision and complete output review.
If the known neutral loss remains, the unresolved work is a better original-CFA
reconstruction operator, not justification for relabeling the current pipeline.
