# Tiny learned band guide

Preparation for one fixed generated feasibility experiment, not a product or
photographic claim. Source storage remains original u16 CFA. The learned object
is a shared local source score, never RGB, coefficients, geometry, or a depth
label. Native reconstruction remains the current four linear CFA pyramids,
terminal mean, source input hull and final MHC. No canonical-weight multiplier
or veto is applied.

Fixed network: replicate-border 3x3 convolution10->8, tanh, 1x1 convolution8->1;
737 f32 parameters shared across all sources and AC levels. The five source
features are log1p(E/max(F,1)), log1p(F), GaussianG/range,
Gaussian(R-G)/range and Gaussian(B-G)/range; E/F are the actual canonical
decision fields using the injected noise model and actual probe. Append the
five source-set means at that location. There is no ordinal/index feature.
Weights are exp(logit-max_over_sources); normalized weighting happens inside
the existing native accumulator. The zero final layer produces exactly unit
weights. No-learning and uniform are intentionally the same mathematical
control, with their byte identity checked rather than counted as corroboration.
Different frequency bands can retain different source support.

Root freezes 1024 Adam steps, learning rate0.001, seed137, f32 deterministic
CUDA with TF32 disabled, final step only and a300-second training cap. A cap
failure yields no model. No scheduler, early-best selection, model download,
architecture/feature/seed/strength sweep, or second training attempt based on
quality is authorized. The loss is equal-case mean squared error of the full
native camera-RGB image after exact finite pyramid expansion, held terminal
mean, original input hull, WB/range normalization and MHC. This does not
calibrate noise or establish physically correct depth/visibility.

Independent fixtures own12 training cases and7 cases in6 held families, including
flat N=5/N=9 cases; training uses only paths in the training manifest. Entire texture,
occlusion and pupil families are held out, not only noise seeds. Before training,
the independent baseline-only screen must show a live positive and protectable
detail, and admit perfect truth. Flat/noise, genuine bright detail, both depth
components, weak colour and clipping guard against a smooth or noisy shortcut.
Permutation and duplicate-source controls test the set-based model. There is no
488-source transfer claim. The features omit signed coefficient phase and cannot
be assumed to identify occlusion.

A future whole-image implementation would need a first source pass for the
set-mean features and later source passes for logit maxima and weighted
accumulation (or a separately commissioned stable online rescaling). This
prototype does not claim one-pass speed and does not authorize retaining an
N-source full-image feature volume. Permutation/duplicate commissioning holds
the feature/coefficient tensors fixed: the unchanged canonical noise probe is
ordinal-seeded, so raw-end-to-end source-order invariance is not established.

`implementation.rs` exports bounded actual source coefficients/features,
canonical and uniform outputs, truth supplied by the independent fixture, and
an independent-of-model prescribed spatial weight pattern. Artifacts are f32
little-endian blobs with shapes/hashes in case.json. Export/replay is restricted
to80x72 CFA-quads, three AC levels and2..17 generated sources. No N full-size
aligned-image volume is created. `train.py commission` must match Rust uniform
and prescribed reconstructions including input hull/MHC boundaries before
`train`; `infer` creates frozen-checkpoint replay expectations. Root executes
the jobs and the actual Rust replay; the author does not judge quality.

Prior boundaries: R24's twin-trained adaptivity/A5 ordinal prior were deferred,
not implemented. FocusDeep's missing licensed ready checkpoint and learnedRGB
route do not supply this consumer. StackMFF V4's categorical source-copy seams
remain rejected. `shared-source-field` and `cross-scale-source-prior` lose depth
information when finest/full-AC source ownership is imposed; this is neither
that field nor a multiplier on canonical support. M67's monotone ideal-PSF
admission is an upper bound, not a training label; M70's useful off-peak band
information and M69's texture-dependent response uncertainty remain constraints.
The failed layered inverse is reused only as a documented forward equation by
the independent fixture author, never as the learned reconstruction.

Root adds only a test CLI include `learned_band_guide` under
native-direct-planes/native-correction-variance/native-gpu-gather. Existing
BandWorker, rb-own-guide core bridge and phase-packed-rgb helper remain unchanged.
