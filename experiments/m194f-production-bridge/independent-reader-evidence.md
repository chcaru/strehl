# Independent delivered-file instrument

2026-09-07, Zeno. `independent-reader-controls-1/result.json` is
**PASS_READER_INSTRUMENT_ONLY, 59/59**; SHA256
`f61e7b7990559e6368a676b70b16d1174c26a8b969fc9f56ad9403a5ffe9efc4`.
This run preceded this lane's first M194f product-TIFF read. It grants no
integration or model authority. Source snapshots and all synthetic TIFFs,
including malformed files, are retained under that run directory.

The bounded direct classic-TIFF parser is `independent-reader.py`, SHA256
`3fbaf526776fc85042861e1e7a90c06664c43519cef20d12310a67efd8eaff2d`.
The independent commissioning driver is `independent-reader-controls.py`,
SHA256 `9e1a065d2dd193b14996591304f2c21a8ead0a0046d97b635c644ce95aee0256`.
Its prospective design SHA256 is
`4828397cb0e5af0ed7477b8ca1406f610663a71a4172ae9a4d35f76cd3c9ab2a`.
All four recorded sources, including the root's clarified preregistration,
were unchanged through the run. No failed first run was hidden: the first
instrument run completed all cases successfully.

Exact original invocation, from the repository root in PowerShell:

```powershell
$env:OMP_NUM_THREADS='2'
$env:OPENBLAS_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -X utf8 -X pycache_prefix=experiments/m194f-production-bridge/work/cache-reader-controls-1 experiments/m194f-production-bridge/independent-reader-controls.py --out experiments/m194f-production-bridge/independent-reader-controls-1
```

Runtime: Python3.12.10 AMD64, NumPy2.4.4, tifffile2026.5.2, Windows11
10.0.26200. One Python process; library thread limits2. Recorded measured
body wall0.1462024s and process CPU0.09375s are execution accounting, not
performance claims. `orig_argv`, executable and xoptions include the actual
fresh-cache prefix, not merely `sys.argv`.

Constant passed first, max0.102357DN; affine max0.111464DN on all80 fixed
sites with represented f32 WB, below the unchanged .25DN bar. These are
synthetic quantizer/parser controls, not product interpolation results.
Both endian representations and single/multiple strips agree exactly with
tifffile's separately decoded samples. Twenty-five malformed/tag/hash/shape
controls reject through the actual reader. Twelve mapping, parity, channel,
WB and black-subtraction destroyers fail the actual value oracle. The smallest
of those maxima exceeds40DN, so the tolerance is not marginally powered.
A correctly rehashed, structurally valid TIFF with one changed red sample
passes parsing but fails the value oracle at22.56298DN.

The synthetic +64DN green companion gives63.89160DN after quantization;
the exact null and saturation controls refuse. The strict-less counts and
rank codes match their independently enumerated declared rows. Wrong ties,
red/blue luma, dropped duplicate200, wrong scaling, absent/moved sentinel,
and a corrupted reached-zero companion refuse. These rank controls pass
arrays to the actual final `rank_check`, which is distinct from TIFF parsing;
the valid Gray files pass both stages. The separately re-chosen synthetic
sentinel is linear index53, while actual intended component output must keep
root's preregistered index0 and reached-zero index1. No exact rank is inferred
from a genuine demosaiced RGB image.

The mathematical oracle does not fit a surface to samples or import the
production MHC stencil. Affine preservation is the declared bounded API
assumption that actual product outputs will still have to satisfy. This
instrument can reject a coordinate/value or writer error but cannot establish
optical fidelity, real-noise calibration, or the accuracy of a confidence score.
