# Independent native photographic review: full chip pair

**Verdict: a modest local photographic improvement, with substantial remaining colour artifacts.** The candidate retains the existing ladder structure while making the long near-vertical rail cores somewhat narrower and more continuous. Separation at the central rail/rung crossings is easier to follow. This is a qualified positive local result, not a dramatic cleanup, a full-image quality acceptance, or SOTA evidence.

The reviewer viewed all twelve native PNGs: baseline/candidate core, left/right/top/bottom transitions, and far control. There was no resize, sharpening, difference-image view, or gradient score used to judge quality. File identities and fixed crop coordinates are retained in `receipt.json`. Change counts were read as intervention information only and did not determine this verdict.

## Feature retention and colour cost

- **Core:** existing near-vertical rails and the two broad rows of small rungs remain recognizable in both arms. The candidate makes the rail cores and their intersections a little easier to distinguish. It does not visibly add an extra rail, rung, or repeated motif. The improvement is small enough that it should be described as improved local separation, not recovered fine-detail truth.
- **Colour/stipple:** bright cyan edging, magenta/blue speckling, and mottled bright boundaries remain conspicuous in both arms. I do not see a clear new overall speckle penalty in the candidate, but the persistence of these artifacts limits the benefit. These highly structured crops cannot establish unchanged sensor noise. Brighter or narrower false-colour edges can look sharper; the favorable judgment rests on following the existing dark rail/crossing geometry, not on increased edge sparkle.
- **Bottom crossing:** the broad horizontal junction remains mottled and is not transformed into a clean fine structure. Any program summary should preserve this limitation rather than implying the entire circuit patch became crisp.

## Boundary views

All four transition pairs were inspected independently of the core. I did not see an abrupt rectangular change, a broken rail, a displaced border, or an obvious new seam at the correction's fade. The left and top views show small local changes consistent with the core; the right view's dark strip and the bottom view's junction remain continuous. This is a visual result on the supplied frozen crops; it does not establish mathematical continuity everywhere in the full output.

## Distant control

The far-control baseline/candidate PNGs look indistinguishable at native display size. The region is **not byte-identical**. An independent reread of the two RGB16 far-control TIFFs reproduced the maximum absolute difference **33/65535**, about **0.05035%** of encoded range or **0.1284 of an 8-bit output step**. That figure describes this control crop, not the maximum over the whole image, and is not a quality score. The command used signed-int32 subtraction before taking absolute differences, avoiding unsigned wraparound.

Small distant changes are consistent with a changed global scalar probe and nonlocal pyramid processing; their magnitude alone does not prove that mechanism. Conversely, the correction rectangle is not a valid promise of byte identity outside itself when those shared downstream quantities are allowed to change. The correct reporting is therefore “no visible distant difference in this crop,” not “unchanged outside the patch.” Existing or supplemental generated controls must establish the intended propagation behavior separately.

The numeric check was run with Python 3.12 `-I -B -`, passing this body on standard input from the repository root (no RAW decoding):

```python
from pathlib import Path
import json
import numpy as np
import tifffile
p=Path('experiments/full-context-placement/comparison-1')
a=tifffile.imread(p/'far-control-baseline.tiff')
b=tifffile.imread(p/'far-control-candidate.tiff')
assert a.dtype==b.dtype==np.uint16 and a.shape==b.shape==(328,328,3)
d=np.abs(a.astype(np.int32)-b.astype(np.int32))
print(json.dumps(dict(max_abs_16bit=int(d.max()),different_rgb_samples=int(np.count_nonzero(d)),changed_pixels=int(np.any(d,axis=2).sum()),max_fraction_encoded_range=float(d.max()/65535),max_equivalent_8bit_steps=float(d.max()/257))))
```

## Acceptance scope

This independent photographic view supports continuing the fixed intervention to the second scene. It supports a limited claim of better local rail/crossing separation through the full-stack chip consumer. It does not establish ground-truth alignment, improved flat-region noise, resolved colour artifacts, a general-purpose local alignment algorithm, or comparable quality on other subjects. No code, configuration, RAW file, or runner was altered during this review.
