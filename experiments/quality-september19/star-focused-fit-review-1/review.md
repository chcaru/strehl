# Independent review: a local focus anchor in the original global gauge

VERIFIED by source inspection; MEASURED on a small generated CFA control.
No original RAW files were read. The production registrar, fitter wrapper,
global map and source receipts were not modified by this review.
Reviewed wrapper SHA256:
`d14192d8544b9e0491887765b0a88a8da42bafcff25d47fa42035f5cc4a76d6d`.
Generated control SHA256:
`72b669a6f01332af61200ef7bab92603f0510e5aed127dff9c6c8210a2411973`.

The wrapper maps each reference-grid coordinate through that frame's original
global129 transform. It samples the local anchor through the anchor's own
original transform at those same global reference coordinates. This correctly
preserves the original output gauge even when the local anchor is not frame
129 and its transform is not identity. No anchor inverse or global-map rebasing
is needed. The fitted translation is added to the **source-native** sampling
coordinate; the existing consumer later applies delta/2 to plane translation
before CA. The anchor's emitted correction is literal `[0.0,0.0]` and its
original map bits are retained.

The wrapper checks the bound map hash and compares each retained patch's
numeric transform with the values decoded from that map's original hexadecimal
words. Emitted configuration copies those original words directly. The copied
u16 patch hashes, geometry, origins, black/white levels and full search/filter
margin are checked before fitting. These guards are significant: an internally
consistent residual improvement does not establish a correct coordinate gauge.

The acceptance rule admits only a converged, off-bound, positive-gain fit with
lower right-side prediction error, except for the forced zero anchor. Both
before and after nuisance gain/bias are fitted only on the left and evaluated
unchanged on the right. Rejected frames retain their original map. At least one
neighbor must be admitted before a placement file is written. Nuisance gains
and offsets are diagnostic fit parameters and are not applied to image data.

## Generated control

Command run from the workspace root:

```powershell
$env:OPENBLAS_NUM_THREADS='1'
$env:OMP_NUM_THREADS='1'
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/quality-september19/star-focused-fit-review-1/controls.py
```

The control changes the anchor to scale/rotation `1.014 + 0.003i`, plane
translation `(1.8,-1.2)`, and an odd-parity source patch origin `(123,64)`.
The source has a different nonidentity map and origin `(121,67)`. Analytic
continuous radiance is sampled directly on each original CFA lattice and
quantized to u16. Unrelated red/blue values cannot become the green guide.
Different brightness nuisances and mild source blur are included. No image
resampler manufactures the source observations. The fixed error bar is 0.05
native pixels, with powered wrong-sign, doubled-shift and identity-anchor
placebos.

`result.json` records PASS. The known source-native translation `(0.61,-0.43)`
is recovered to 0.000122872 native px without extra blur and 0.000133138 px with
0.45-pixel blur. Blur alone produces 0.000227629 px apparent displacement.
The anchor remains exactly `[0.0,0.0]`. Search support stays disjoint by at
least 3.23 native pixels. The run exits zero and uses 0.546875 process CPU
seconds; this is small-control accounting, not a performance claim.

Correct same-focus validation RMSE is 0.000310303. Wrong sign gives 0.0245731,
doubled translation 0.0124795, and incorrectly treating the nonidentity anchor
as identity gives 0.0447262. All prescribed negative controls therefore have
power against the specific gauge/convention mistakes under review.

## Interpretation limit exposed by the controls

The identity-anchor placebo nevertheless reduces its **own** validation RMSE
from 0.0676487 to 0.0447262. It would satisfy the wrapper's generic improvement
gate while recovering the wrong correction. The map/receipt binding and correct
anchor sampling are therefore required evidence; the ratio alone cannot verify
them. The current inspected wrapper retains both.

Likewise, the blur-only null reduces validation RMSE very slightly and would
be admitted, although its correct displacement is zero. Admission is permission
for a paired photographic replay, not statistical proof of nonzero motion,
equal focus, geometric truth or improved image quality. These limits do not
invalidate the bounded replay, but its photograph still requires independent
review. This control does not calibrate the camera noise model or demonstrate
SOTA performance.
