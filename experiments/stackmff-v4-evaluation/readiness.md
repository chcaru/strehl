# StackMFF V4: deterministic inference readiness

2026-09-25. Source inspection only; no model execution, installation or checkpoint
download by the author. Root separately authorizes the fixed three-source pilot
in `decision.md`. This is a conventional developed-image comparator, not a
CFA-native improvement or a complete-stack quality result.

**Pin and licence.** Official GMFF commit
`d104b3f51fc3933c7dbb2da27a21816b574914f3`; its actual Git tree is
`4e9332ab8a7700ba791bbcda1efb2bf500a75977`. The previous readiness memo called
the commit identifier a tree identifier; this corrects that wording. The
[pinned README](https://github.com/Xinzhe99/GMFF/blob/d104b3f51fc3933c7dbb2da27a21816b574914f3/README.md)
explicitly declares MIT. Root accepted this declaration for research inspection.
The earlier absence of a separate LICENSE file remains recorded, without
overriding that authorization. No GPL code, diffusion or training code was read.

**Exact consumer.** The official
[stage-one script](https://github.com/Xinzhe99/GMFF/blob/d104b3f51fc3933c7dbb2da27a21816b574914f3/inference_stage1.py)
imports only one project module:
[`stackmffv4/network.py`](https://github.com/Xinzhe99/GMFF/blob/d104b3f51fc3933c7dbb2da27a21816b574914f3/stackmffv4/network.py).
`StackMFF_V4().eval()` receives float32 `[B,N,H,W]` grayscale in [0,1], N>=2.
It returns fused grayscale `[B,1,H,W]` and integer source indices `[B,H,W]`.
Softmax then argmax chooses one input layer; `torch.gather` copies its grayscale
value. The script copies the corresponding original RGB pixel using that index.
There is no radiance synthesis, source averaging, RAW/noise model, registration,
white balance or exposure fit. Hard selection can amplify grain and create seams.

The official loader converts decoded 8-bit BGR images to grayscale /255; its
model API does not require quantized input. The authorized pilot instead converts
the existing RGB16 donors to float32 /65535, then uses OpenCV RGB-to-gray with the
same channel convention. This precision-preserving input adaptation is explicit;
it is not an exact replay of the official 8-bit file loader. No extra tone or
normalization is allowed. The official script resizes spatial dimensions upward
to multiples of32; our384-square is unchanged and also divisible by128. It loads
all sources at once and has no tiling/context API. Its exported index PNG is
unsafe for large N: uint8 indices multiplied by `255//(N-1)` become all zero at
N=488. The pilot must preserve the actual int64 index array instead.

**Resource limits (DERIVED, not measured).** Features occupy O(8NHW). Four
depth-attention layers use full N-by-N attention at spatial quarter resolution;
`MultiheadAttention` is called with its default returned attention weights.
At384-square,N=3, one float32 eight-channel field is14,155,776 bytes and a
four-head score tensor is1,327,104 bytes. At the same spatial size,N=488,
these become2,302,672,896 and35,115,761,664 bytes respectively, before other
activations. Thus variable N is an API property, not a demonstrated practical
488-source path. Whole-image inference would also materialize full aligned RGB
and gray volumes, prohibited here. Spatial convolution, adaptive pooling and
size-dependent interpolation mean naive tiled calls are not proven equivalent.

**Minimal fetched research files.** Pin and verify Git blob identities before
execution: `network.py` (`f59f61dd549caa9c7e34505a8e58ded8e397641c`,25,187 bytes),
`weights/stackmffv4.pth` (`a452536a934e8cb4c72270f8738db060556a72d5`,3,972,415 bytes).
Retain README (`051077c2fb839fbac640b3c60591f5a4a091e4ac`,10,384 bytes) and stage-one
script (`ced133fe8a8e4cac0f972efb7bd633a0fd6786ee`,10,888 bytes) as provenance;
do not import the latter. No utils, dataloader, diffusion or training modules are
needed. Runtime imports are torch, torchvision, numpy, OpenCV, plus local TIFF
and image I/O. Existing packages only. Load the checkpoint with
`torch.load(weights_only=True)` and strict full state loading; never fall back to
pickle. Official construction requests pretrained MobileNet weights before this
load; bypassing that discarded initialization needs an explicit receipt and
complete strict-load check, not an unrecorded extra model download.

**First falsifiable observation.** Fixed donor order112,152,320, crop
[3230,3000,384,384] in the existing6268x4176 marigold output/ref244 gauge. Use
the existing identically developed donor TIFFs and current baseline. The outer
two RGB pixels can see the old MHC blend ring; judge the fixed inner380-square,
retain the entire384-square result, and make no full-context equivalence claim.
Near shorter/brighter fan tips must coexist with far long/slanted strands.
Source320 is the existing hair-loss destroyer, not an invalid background donor.
Run actual-model duplicate/constant fidelity and index validity, plus independent
mixed-label source reconstruction and permutation reporting. These commission
execution, not quality. No sharpness scalar, label histogram or reversal can
qualify it. Root bound:120s wall/300s CPU/8GiB host/eight CPU threads, float32 CUDA
with synchronized timings and peak allocation recorded. Only root executes.

**Conditional full-stack route.** A useful pilot first earns an independently
reviewed bounded all488-source region test; it does not earn production
integration. Unchanged upstream full-frame execution is ineligible for our
memory/storage contract. Any later implementation must stream native gather into
bounded spatial context, retain all-source attention semantics, verify context
and numerical equivalence, and avoid a full aligned frame volume. Feature/spatial
attention batching is a separate engineering decision, not part of this pilot.
Only after that passes could one whole488 output be judged against the current
complete stack, with the full-resolution image shown to the owner. No additional
sources, model tuning or context sweep is authorized here.
