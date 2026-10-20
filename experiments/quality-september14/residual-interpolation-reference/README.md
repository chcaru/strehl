# Published RI reference and local adaptation

> **Archived dependencies: do not install `source/requirements.txt`.**
> Its original pins include vulnerable NumPy 1.19.0 and OpenCV Python 4.3.0.38.
> They are preserved as upstream research evidence, not a supported environment.
> See the NumPy advisories
> [GHSA-6p56-wp2h-9hxr](https://github.com/advisories/GHSA-6p56-wp2h-9hxr) and
> [GHSA-fpfv-jqm9-f5jm](https://github.com/advisories/GHSA-fpfv-jqm9-f5jm), and the
> OpenCV/libwebp advisory
> [GHSA-qr4w-53vh-m672](https://github.com/advisories/GHSA-qr4w-53vh-m672).

For `v0.1.0-alpha.4`, this reference and these Python dependencies are excluded
from the application and delivered source/relink kit; CI does not install this
manifest. The historical pins remain vulnerable. Any future reference work
needs a separately maintained and tested environment; changing that environment
does not retroactively validate the recorded research results.

Source: [IPOL 2021/358](https://www.ipol.im/pub/art/2021/358/), Jin, Guo,
Morel and Facciolo, *A Mathematical Analysis and Implementation of Residual
Interpolation Demosaicking Algorithms*. The official ZIP was downloaded on
2026-09-14. Its SHA256 is
`1b50cc7855bdf1f06254145007fd4716249daa74f29db08d3b6aa07a2c547269`.

The archive's BSD-2-Clause `LICENSE.txt` was read before any implementation.
`source/` retains the original Python/text files; the photograph bundled in the
archive was not extracted. No external demo was run or photograph uploaded.
The licence is retained in both `source/` and `float32-ri/`.

`adapt-float32.py` generated the separate `float32-ri/` dependency path.
`float32-adaptation.diff` records every edit, and `float32-adaptation.json`
binds original and adapted files. Constructors and Gaussian kernels explicitly
use f32; the fixed variance floor uses f32 arithmetic. All reference `[0,255]`
clips are explicitly disabled to retain WB-applied RAW headroom. The callable
adapter exposes RI only, although upstream shared modules retain other branches.

`../residual-interpolation.py::ri(cfa)` scales normalized WB RGGB by255 and
divides the result by255. RI's spatial Gaussian sigma remains1, guided epsilon0,
and its published window sizes are unchanged. No sensor noise is estimated.
Measured samples are algebraic identities of the residual update; an explicit
16*f32-epsilon*max(1,absolute input/output) roundoff guard precedes restoring
the original normalized sample bits. `LAST_DIAGNOSTIC` records those corrections.
Correlations replicate boundaries; box sums use zero boundaries. Trim32 is the
conservative interior comparison; trim12 can contain boundary effects.

The first saved-chip call exposed a separate boundary defect: the reference's
replicated border duplicates a sparse R/B residual in the final3x3 interpolation,
breaking measured-sample identity on the outermost row/column. The recorded
diagnosis is `../ri-guard-diagnosis-1.json`. The adapter now reflect-pads32 in
native coordinates before RI and crops32 afterwards. Whole-sample reflection
and the even padding preserve CFA phase. Every returned pixel still faces the
same known-sample guard; neither its tolerance nor its domain was relaxed.
`../ri-boundary-controls.py` retains the unpadded failure as a negative control
and checks exact measured samples across the full padded-adapter output.

Available runtime: numpy2.4.4 and OpenCV4.13.0. No dependency was installed.
Source preparation alone establishes no quality result; independent controls
and actual product rendering are separate steps.
