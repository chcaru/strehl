# Source multiplicity: exact symmetry, different model

SOURCE-VERIFIED / DERIVED, 2026-10-27. Read the pinned MIT V3 inference source,
the actual [V-DILUTE report](../../../docs/research/V-DILUTE.md), and its
pre-registration. No numerical, GPU, image or RAW job; no bound source changed.
The complete V3 photograph has not been used to infer a softness cause here.

**Equal duplication is an exact real-arithmetic output symmetry of this fixed
model. Unequal duplication generally is not.** Neither statement says that its
current299-source photograph is being diluted, or that source removal helps.

## Through the actual attention and readout

The fixed model has no source-position embedding (`layer_pos=false`), source
mask, source-index regression or hard-argmax readout. LayerNorm acts on each
token's channels, not over source count. Spatial window attention treats each
source independently; its relative position bias is spatial. Spatial2x2 pooling,
bilinear updates and both inference scales are applied identically to sources.
The four cross-source attention blocks use ordinary scaled dot-product softmax,
with no dropout argument (the functional default is zero).

At a particular head/spatial group, write one attention row as

`o_i = sum_j exp(s_ij) v_j / sum_j exp(s_ij)`.

Duplicate every source m times, with identical pixels and geometry. Every copy
has the same query/key/value as its original. Each individual attention mass is
divided by m; summing its m equal values restores o_i. Residuals, per-token MLPs
and subsequent blocks therefore preserve each original state, by induction.
Final logits are merely repeated. Source softmax gives each copy p_i/m. The
two-scale probability average and channel-wise Gaussian smoothing are linear;
the final source renormalization preserves the grouped mass. Fusion sums m
identical RGB copies weighted p_i/m, giving the original RGB result.

This is not a bit-identity promise in f32. Changing N can change SDPA kernel
selection and reduction order; probability renormalization, NumPy summation and
rounding can differ slightly. Clipping the final rounded RGB to uint16 cannot
create a systematic real-arithmetic dependence, but can mask small differences.
Compare grouped probabilities and unrounded RGB, not only the saved uint16.
The model does not acquire more information or independent noise samples from
literal duplicates. The adapter's299-source bound is an operational limit,
not an N-dependent normalization inside the network.

For unequal integer multiplicities m_j, the *first* attention row instead is

`o_i(m) = sum_j m_j exp(s_ij) v_j / sum_j m_j exp(s_ij)`.

This is equivalent at that block to adding log(m_j) to each key's logit before
grouping. It is not a simple final-output effect: altered attention can change
every source's subsequent feature state and focus logit. At a later final
readout, the grouped mass is

`P_j(m) = m_j exp(l_j(m)) / sum_k m_k exp(l_k(m))`.

The dependence of l_j on multiplicity matters. Holding logits fixed would give
a simple increasing mass for a repeated blurred source, but that is only a
conditional readout calculation. The actual network may compensate, reinforce
or redistribute that change through its cross-source blocks. Thus the source
does **not** establish monotone sharpness loss when only a blurred source is
repeated. Spatial smoothing and two-scale averaging do not restore a general
unequal-duplication invariance. There is no calibrated noise gate that makes
blurred-source probabilities identically zero; finite softmax probabilities can
still be extremely small. Actual mass must be measured before calling it large.

## Why this does not reopen V-DILUTE

V-DILUTE examined the old native pyramid's noise-gated per-band normalized
weights on bee-3-cpl. It measured an effective fine-band competitor ratio near
0.36, approximate winner share0.92 and n_eff1.19 at299, and rejected the proposed
dilution mechanism. Its150-versus-duplicated300 null differed by at most1DN.
That result concerned actual gated coefficient weights and cannot be transferred
to learned cross-source attention followed by full-value RGB soft fusion.
Conversely, a V3 multiplicity effect would not overturn the old result. Equal
duplication symmetry belongs to many normalized estimators and is insufficient
to prove strong focus discrimination in any of them. The existing V3 all299
constant check is particularly weak on that question: equal RGB values fuse to
the same image under *any* normalized source probabilities.

## Small falsifier if root later releases a numerical question

Use one fixed small two-source structured input with distinct near/far focus
regions. Compare the actual default model on `[A,B]` and `[A,A,B,B]`; group the
duplicate probability channels and compare the entire unrounded RGB output
using the existing fidelity bars. A failure beyond floating tolerance falsifies
the claimed producing-path symmetry. Preserve source order, geometry, two
scales, padding and sigma; it is not a subset-quality comparison. Repetition
must copy existing arrays exactly, not draw new acquisition noise.

A separate tiny known-positive/flat-null commission can isolate readout
multiplicity without claiming focus truth. Use two constant RGB16 colors A and
B whose *actual uint16 OpenCV grayscale values are identical*. A fixed candidate
is A=(24576,24576,24576), B=(25600,24576,21890); require the actual grayscale
equality before interpreting the fixture, rather than assume coefficient
rounding. Then all grayscale inputs/states/logits are identical: `[A,B]` must
produce (A+B)/2, equal duplication must retain it, and `[A,B,B,B]` must produce
(A+3B)/4 before final rounding. This is a known changed color mixture, not a
softness or camera-color claim. It cannot show how the learned attention reacts
to real focused versus blurred images.

No temperature, multiplicity correction, source subset or parameter sweep is
recommended from these algebraic facts. The complete photograph and its source
evidence must first establish whether there is a visible defect worth testing.
