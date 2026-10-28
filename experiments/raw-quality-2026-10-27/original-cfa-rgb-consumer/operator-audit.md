# Once-RGB consumer: a boundary experiment, not a new joint inverse

SOURCE-VERIFIED / DERIVED, 2026-10-27. No RAW, image decoding, model inference,
build or numerical job. **No-go as a newly discovered joint-CFA reconstruction
method. Conditional go as one complete band-preserving boundary experiment:**
retain the existing MHC reconstruction prior, but stop throwing away two of its
three output colors and reconstructing them again. That is an actual operator
change; algebraically fusing its stencil is only an implementation choice.
There is no demonstrated photographic gain or compliant replacement ready now.

## Existing operator and actual prior evidence

`crates/strehl-cli/examples/build-demosaic-truth.rs::once_rgb` already evaluates
MHC RGB followed by the same full-native Catmull pull, retaining all RGB values.
Its comment correctly says it is not a drop-in for the mosaic-consuming merge.
The retained [actual log](../../BUILD-DEMOSAIC/out/03-truth.log) contains mixed
results, not a universal improvement: once versus fullres chroma error is
331.17 versus281.05DN on noisy flat, 464.08 versus447.66 on noiseless neutral,
520.73 versus595.28 on colored detail, and847.07 versus1259.49 on vivid color.
The one-source colored/vivid improvement is plausible motivation to remove
remosaicing; the flat/neutral regressions must travel with it. Those figures do
not establish a complete-stack improvement on today's capture rig.

The current path is directly visible in
`align_cmd.rs::warp_frame_fullres_coordinates_impl` and
`writeback_fullres_site`: source WB-scaled signed CFA -> MHC RGB -> Catmull
pull at reference Bayer sites -> inverse source WB plus black -> rounded/clamped
u16 remosaic. Extraction rectifies below-black values. `BandWorker` builds the
four phase pyramids and green guide, then `write_demosaiced_with_master` performs
MHC again before development. The previous
[native-contract note](../cfa-probe-cost-audit/native-contract-note.md) records the exact producing
path and the direct-plane, direct-CFA and continuous-boundary failures.

For frozen geometry let D be source-WB-aware MHC, W the color-specific geometric
pull, R reference remosaicing, Q its quantization/clamping, A/S pyramid analysis/
synthesis, and F the noise-gated band fold. Ignoring notation for WB conversion,
the old path is D_ref S F A Q R W D y. A once-RGB consumer is S F A W D y.
Writing each W D row directly against original sensels removes neither D's
cross-color assumptions nor W's interpolation bias. MHC also makes values at
unmeasured colors; those are estimates, not additional observations. Only a
different estimator that jointly uses original samples could exploit extra
sampling phases beyond this per-source reconstruction prior.

The changed consumer does preserve the full signed f32 W D result, eliminates
the intermediate integer/clamp boundary and R's discarded components, and
avoids D_ref acting across a spatially varying mixture of source coefficients.
These effects are coupled: removing the second MHC can expose noise and false
color which it previously attenuated. Rounding alone is not an evidenced cause
of the observed softness. M95's [actual summary](../../M95-demosaic/out/d9_summary.txt)
also shows why extra high-band power cannot decide this question: nearest was
louder while carrying less true detail; the unchanged MHC itself manufactured
part of the measured band energy.

## Smallest scale-compatible complete consumer

If root elects that *boundary experiment*, use the ordinary Laplacian consumer,
not the photographically rejected dual-tree recipe, and retain its band scales:

1. For each original u16 source, evaluate camera-RGB W D rows at all four
   reference Bayer offsets. Keep twelve temporary f32 planes, indexed
   `(reference phase, output color)`, on the existing quad grid. These are
   three full-native images in polyphase form, not twelve independent sensors.
   The source-specific WB conversion must match D; undo it per output color
   into a declared camera-DN basis before applying the fixed output WB later.
   Retain signed/headroom values and coverage explicitly.
2. Analyze all twelve planes with the existing actual sizes and Laplacian
   analysis/synthesis. Apply one shared noise-gated weight per source/band/site
   to all twelve coefficients, preserving ordinary coarse/base behavior and
   fallback. This retains the opportunity to take near fine and far coarse
   content. A single full-value source probability is **not** this experiment:
   native-pixel-fusion already demonstrated the coarse/fine loss it can cause.
3. Collapse the twelve planes and interleave each phase's RGB triple directly
   into one full-native camera-linear RGB image. Use matrix.develop and the
   existing direct RGB16/linear-TIFF helpers with pinned development; do not
   call the mosaic writer or binned writer, which would add another demosaic
   or co-siting interpolation. The direct-writer seam needs its own parity.

`BandMerge` already accepts a variable plane count and shares its weights across
those planes. Twelve instead of four preserves the existing quad-grid physical
band support; simply switching to three full-native planes with seven bands
would also change every physical band scale. This is why the twelve-plane
form is the smaller causal change. It does not remove all polyphase artifacts:
different phase sequences still undergo independent spatial filtering, and
their interleaving can reveal phase inconsistency that the final MHC concealed.

The guide can be the same physical green combination evaluated through the
continuous W D rows. It is still MHC-reconstructed focus evidence. Recompute
its floors through those exact rows and band filters using the one injected
original-sensor noise model; do not import the old remosaic-floor calibration.
The RGB rows share original sensels, so their cross-color and cross-phase noise
is correlated. Actual original-CFA probe draws through the complete rows retain
that dependence; treating twelve outputs as independent samples does not.
Data-dependent weights make fixed-weight propagation conditional, not a proof
of unconditional output variance. A scalar green guide remains weak on truly
independent color detail; this route does not solve that known limitation.

One source at a time is feasible without an aligned-source volume. Composed
row evaluation can avoid retaining dense source RGB, though it may repeat MHC
work; a transient reconstructed source image has the same mathematical bias.
Twelve-plane accumulators need about three times the current four-plane
coefficient storage, plus the final RGB output. This is a source-derived cost
warning, not a throughput claim; reuse of the ordinary parallel accumulator
does not establish a practical full299 time or memory bound.

## Contract and decision boundary

Call this **original-CFA-fed, once-per-source MHC/Catmull RGB band fusion**.
An implementation may gather its composed rows directly from u16 storage and
produce only one final RGB image. That satisfies the storage/no-volume aspect,
but it is algebraically reconstruction before source fusion, not a newly joint
measurement-domain solution. Do not market a fused kernel as proof that all
reconstruction and admission stayed unaltered in the native CFA domain. A
strictly native admission/reconstruction replacement remains unresolved.

The existing positive original-CFA kernels' full-chip failure, direct cubic/
quincunx neutral loss, and band-residual/deflation flat-chroma failures prevent
claiming that merely removing MHC is the safer alternative. They do not rule
out this explicitly different boundary comparison. Conversely, BUILD-DEMOSAIC
already answers the algebraic row-composition question; repeating its one-frame
test alone would add little.

The smallest useful next decision would therefore be a paired complete
photograph from this once-RGB band consumer, after actual signed single-source
and uniform-weight row/analysis/synthesis checks, flat-first colored/neutral
and mixed-depth guard reuse, and direct-writer parity. Numerical controls must
retain the known flat/color tradeoffs. No crop-power score or reduced R-B
difference can admit it as a quality improvement. Root must separately release
implementation and whole-photo execution; this report does neither.
