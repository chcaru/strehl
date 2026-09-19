# Preserve reconstructed colour through the merge

September 19, after the focused star placement null. Experimental and off by
default. The owner requires complete stack images whenever an improvement is
shown; native crops are additional diagnostic evidence only.

Question: does moving the missing-colour reconstruction before the current
merge, while keeping its actual focus decisions fixed, preserve more real
colour/detail than remosaicing followed by final MHC? Keep the original four
CFA planes first, bit for bit, and gather the other eight colour/site planes
using the existing MHC/Catmull arithmetic. Fold all twelve on the existing quad
grid with the existing shared G1/G2 guide, injected variance, measured probe,
band count and weights. Interleave complete native RGB after collapse. Original
storage remains u16; arithmetic remains f32; no collection of aligned frames.

This is not a new inverse solver, focus metric, denoiser or fitted optical model.
It does not reopen the rejected September 14 single-frame demosaicers, native
green cue, or iterative CFA inverse. The first implementation is test-only and
uses the actual BandMerge. No full-RAW render until the small screen is reviewed.

Prior art search: `quality-september19/chroma-prior-art.txt`, plus the author's
RGB-merge search. Read BUILD-DEMOSAIC, V-GATHER, M95-chroma-cositing,
BUILD-CHROMA and V-LINEAR2. BUILD-DEMOSAIC's once arm already establishes a
mixed single-frame tradeoff: better coloured/vivid truth, worse flat-noise and
achromatic truth. Its oracle improvement is not the once-arm gain. In particular
this is NOT an established cure for isolated magenta pixels. V-GATHER requires
the probe to follow the guide; keeping the four original planes fixes that
consumer rather than changing focus resolution under the experiment.

Primary external context, read September 19:
[Wronski et al. 2019](https://sites.google.com/view/handheld-super-res/) shows why
multi-frame RAW colour reconstruction can matter but assumes burst-like scene
agreement; it does not validate this proposal or focus-stack super-resolution.
[Superpixel Bayer fusion, 2015](https://doi.org/10.1016/j.ijleo.2015.08.023)
is prior art for joint RAW fusion/demosaicing; no implementation was read/copied.

Author: full_context_placement. Independent stimulus, coordinate and numerical
review: placement_controls. Root builds/runs and makes photographic decisions.
Author must expose the actual small consumer to the independent tests rather
than reimplementing a favourable scorer. Reuse existing process/build tools.

The screen must include flat noise FIRST, neutral and truly coloured structure,
fractional geometry, unequal defocus/spatially varying focus, and wrong-phase
or wrong-channel destroyers. Confirm the varying selection actually occurs.
Known four-plane, guide and band-gain equality isolate the intervention. Truth
error can reward smoothing: pair it with recovery of known scene components.
Chroma high-pass can reward correlated error and is not an acceptance score.
Noise must be measured against the same flat truth, not scene spatial SD.

One fixed screen; no threshold/iteration/interpolation sweep. The independently
chosen acceptance decision must be fixed before execution. A material loss of
real neutral or coloured detail, or a clearly worse flat-noise tradeoff without
compensating measured signal recovery, closes this candidate. A useful tradeoff
may proceed to the retained chip RAW samples and then complete stack images.
Any such step needs full-resolution photographs, including an independent
review and a complete before/after pair. No SOTA claim from synthetic scores.

Bounds: first build at most 600 wall seconds, 3600 CPU seconds, 16 GiB job commit.
Small generated screen at most 120 wall/300 CPU seconds and 4 GiB. Saved-patch
diagnostic at most 120 wall/300 CPU seconds and 4 GiB. Root records full argv,
environment, source and executable hashes beside runs. Full-stack work, if
justified, will use existing bounded render machinery and explicit maps under
the workspace. Originals remain read-only; no source-directory sidecars.
