# Source localization, fixed before the scan

Use only the existing 70 unaligned native RGB16 exports. No RAW decode, render,
colour adjustment or diagnostic crop resampling. The held warp map locates each
384-square reference window's centre in original active coordinates; round the
source crop origin once to integer pixels. Keep the full native pixel array.

Windows are the previously frozen facet-edges and dark-inclusion rectangles.
The conspicuous glint locators are fixed from the frozen baseline: facet-edges
local centre (128,222), dark-inclusion (46,326), each 80 square. Scan all70 using
mean squared green gradient after a fixed 3x3 box smoothing, solely to nominate
a source index to inspect. This quantity rises on both genuine structure and
noise, can prefer a clipped/bright edge, and is NOT quality or clipping evidence.
Run flat/noise controls first: constant input must score zero; sufficiently
noisy constant input must outscore an independently specified low-contrast wave.
These demonstrate the locator's known failure, not validation of a quality bar.

For each window inspect the nominated index and its neighbours at -3/+3 frames
(clamped to the70-frame extent), plus the unchanged native baseline. A spike at
an endpoint is a boundary nomination, never an optimum. Record every source
index, original filename, transform bits, mapped centre, rounded crop origin,
locator value and source receipt identity. Display by rounded division by257,
as in the frozen diagnostics; preserve RGB16 crops as well.

Interpretation is limited to whether similar chromatic spokes are already
present in these developed single frames. Source exports already include MHC,
matrix/tone/gamut/highlight development, omit lateral CA correction and have
tone before any external merge. Baseline has CA gather and tone after its CFA
merge. Display white is not a measurement of RAW sensor pinning. These source
views cannot separate optical structure from source demosaic/developer effects,
or quantify the merge's causal contribution.
