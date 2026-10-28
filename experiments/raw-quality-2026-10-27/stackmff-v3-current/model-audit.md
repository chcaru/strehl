# Pinned current StackMFF V3: bounded consumer audit

SOURCE-VERIFIED / DERIVED, 2026-10-27. No model import, inference, RAW read,
installation or numerical job was run by this author. Root owns execution.
This is a developed-image external comparator, not native-CFA reconstruction.
The old September three-source hard V4 pilot is not this model or this workflow;
its [seams and rejection](../../stackmff-v4-evaluation/results.md) remain valid
for that pilot. The [current brief](brief.md) fixes the changed question.

## Source, weights and exact defaults

The official MIT repository is pinned to commit
`6e1d7211f7634f60245706ebe3b839b320df9d00`. Read only the permitted inference
sources. Root's `outputs/raw-quality-2026-10-27/stackmff-v3-upstream-2/`
contains LICENSE, THIRD_PARTY_NOTICES.md, README.md, fuse.py,
stackmff_v3/{__init__,model_io,network}.py and weights/stackmff_v3_final.pth.
Its download receipt records exact Git blob identities, sizes and SHA256s.
The checkpoint is 658587 bytes, SHA256
`39b2ea3738e8fea1676c379238d6be81a87988fc9952dbd6ac3825d5d7249f46`.
[The source adapter](model-adapter.py) independently pins every downloaded file,
uses only `torch.load(..., weights_only=True)`, requires the released architecture
arguments, and loads the state strictly. There is no unsafe-load or download
fallback. No restricted third-party implementation was read.

The live defaults are StackMFFLoop, C1=48, C2=96, heads=(3,6), window=8,
inter_pool=2, mlp_ratio=2, single_scale=true, fine_head=false, no layer-position
embedding, distinct u4a/u4b, k_eval=1. Thus the active backbone has two
AttentionRounds at one-quarter resolution: four intra-image window attentions
and four pooled cross-source attentions. The unused one-eighth loop is absent.
The two *inference* scales are independently fixed to (1,0.75). All parameters
and arithmetic are f32; TF32 and autocast are disabled. No hard selection is used.

Official fuse.py consumes BGR uint8/u16 developed images. It converts each to
uint16 OpenCV BGR2GRAY first, then f32 divided by65535; so using floating RGB
luminance would change the input. It pads the grayscale bottom/right to64,
computes probabilities at both scales, crops to the original image, and only
then applies sigma0.5 separable Gaussian probability smoothing and renormalizes.
One resulting source probability weights all RGB channels. Its final f32
weighted sum is rounded with NumPy round, clipped and converted to uint16.
The adapter accepts RGB16 and explicitly reverses channels for the same grayscale
conversion; `fuse_rgb16` is the actual shared composer used by both routes.

`predict_full` calls the pinned upstream `fuse.probabilities` unchanged on small
complete inputs. It is the independent whole-input reference for the bounded
route, not a Python approximation of the network. The model itself is unmodified.

## Derived plugin halo and global phase

LayerNorm is per token over channels. Cross-source attention is spatially local;
it attends to *all* N sources at each pooled position. There is no global spatial
normalization or spatial source-index embedding. The stem is4x4/stride4, the
head is pointwise plus4x pixel shuffle. Each intra block covers an8-token window,
alternating global origins0 and4. Each inter block averages2x2 then bilinearly
upsamples its update with align_corners=false.

For a one-axis token interval[a,b], one backward inter dependency is
`[2*floor((a-1)/2), 2*floor((b+1)/2)+1]`. A backward intra dependency expands
to complete8-token windows on its declared origin. The reverse sequence is
inter, shifted-window, inter, regular-window, repeated twice. For output-token
residues0..7 the left/right extents are respectively
(16,15), (17,14), (18,13), (19,20), (20,19), (13,18), (14,17), (15,16).
Including the stem cell, no ordinary one-scale dependency is farther than83
native input pixels along either axis. The0.75 path expands this by1/0.75;
bilinear output interpolation, finite antialiased input resize and the final
radius2 Gaussian still fit conservatively inside128 native pixels. The shifted
mask uses upstream finite -100 rather than mathematical minus infinity;
numerical equivalence is therefore tested, not claimed as a bitwise theorem.

Fixed cores are at most256x256, their origins lie on a128-pixel lattice, and
normal contexts are512x512 with128 plugin halo. Context origins are also
multiples128: after0.75 scaling they are multiples96, preserving the scaled
32-pixel window lattice. Context sizes512 scale to384, a multiple64, so no
spurious scaled local pad is introduced. The true weevil extent6896x4596 pads
globally to6912x4608, each divisible256; its scaled padded extent is5184x3456.
The full486-core traversal therefore fits this exact supported geometry.

At real boundaries a512 context is shifted inward to end at the global padded
edge, never shortened to an arbitrary extent. The bridge gathers only physical
RGB pixels; the adapter constructs the *global* grayscale reflect padding from
those pixels. It then removes that true outer padding before smoothing
probabilities, as the official whole call does. Artificial context boundaries
are outside the retained core's dependency. Small axes use their entire padded
extent; large padded axes not divisible256 are explicitly unsupported here.
There is no generic arbitrary-size approximation or automatic smaller halo.

Controls use one full760x756 input (globally padded to768 square), an interior256
core with512 context, and true-edge coverage. The zero-halo diagnostic uses the same predictor
and composer with a256 context and is explicitly marked diagnostic-only.
Agreement tolerances and this foil are fixed in
[the independent protocol](comparison-protocol.md). Floating backend kernels may change accumulation
order with tensor size, so actual reference agreement is mandatory.

## Practical all299 route and limits

All299 sources remain joint in every cross-source attention and softmax.
Splitting the source axis into subsets would change the model and is forbidden.
Only spatial input contexts are gathered. The complete RGB16 source volume at
7032x4688 is about59GB decimal before any model activations; official fuse.py
also stacks color inputs and grayscale. Its direct full-image CLI is not a
practical route here.

A512-square299-source context uses about470MB RGB16,314MB grayscale f32 and
941MB stem features. A materialized pooled attention matrix at full scale is
4096 spatial groups x3 heads x299x299, about4.39GB f32, before temporary copies.
These are derived sizes, not a memory or speed measurement. The unchanged
Torch attention backend may require multiple matrices. Root's explicit24GiB
Torch/host bounds and all299 cost tile decide feasibility; no fit is promised.
The adapter records process GPU allocated/reserved high-water and synchronized
per-call seconds without resetting the caller's peaks.

Root's cost core(1792,512,256,256) reads(1664,384,512,512). A whole-image timing
projection must account for486 consumer cores, overlap, both scales, source
gather and output. Small controls or published12-33-source benchmarks cannot
establish competitive full-stack speed. If the unchanged512 context fails cost,
the faithful possible next adaptation is spatial-group batching inside attention,
whose groups are independent; that is not implemented or authorized by this file.

The input TIFFs already underwent MHC, fixed white balance, matrix, tone and
sRGB encoding before fusion. Their cubic RGB gathering has the held coordinate
gauge but a different interpolation kernel from native Catmull. These workflow
differences must accompany every complete comparison. Model mechanics or a
successful full render makes no photographic improvement or SOTA claim.

## Source-preparation checks

Read pinned local source plus its download receipt. Ran only Python standard-
library `ast.parse` on model-adapter.py and SHA256 hashing; no NumPy, Torch or
upstream imports. Root will bind the final adapter/source versions and execute
the prospective controls and cost. API: load_model; tile_spec;
predict_tile; predict_full; fuse_rgb16. Returns uint16 RGB, normalized f32 RGB,
optional source probabilities and JSON metadata. Outputs retain actual source
order and shared RGB probabilities.
