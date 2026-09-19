# Star-sand baseline inspection and frozen local-placement check

**MEASURED:** the fixed green-guide correction reduced the held-out residual for all eight nonreference neighbours of frame 129 at the porous-grain ROI. The ratios range from **0.8700 to 0.9460**, with no search-bound hits. This is evidence that the chip's local-placement diagnostic can transfer to a second subject. **It is not evidence of a photographic improvement:** no corrected star image has been reconstructed or rendered in this task.

## Frozen photographic targets

The full-stack baseline is `../star-baseline-1/star.tiff`, SHA-256 `0111ed93166e775f87d50399ce75b5e2b039d74ff956208c50ca6d29bcd7e459`, **6724 × 4480 RGB16**. The reference is stack ordinal **129**, filename **DSC00145.ARW**; the file sequence begins at DSC00016, so ordinal plus one is not a valid filename rule here. The output's native sensor crop origin is **(154,104)**, derived from logged plane origin (77,52). All coordinates below use native sensor/output pixels, not CFA plane pixels.

The render log reports tone black **0.01566**, white **0.51099**, contrast **0.55**. These are rounded printed values, not exact renderer bits suitable for a pixel-identical matched-source developer.

The ROIs were frozen from subject location in the orientation overview before viewing their native crops:

| Name | Output `(x,y,width,height)` | Reference-sensor `(x,y,width,height)` |
| --- | --- | --- |
| ridged-shell | (1360,1136,392,392) | (1514,1240,392,392) |
| porous-grain | (440,1320,392,392) | (594,1424,392,392) |

`receipt.json` retains the source and native-crop hashes. The native TIFF crops preserve the original 16-bit samples; their PNG companions use only `uint16 * 255 // 65535`, with no resampling or enhancement. `overview-orientation.png` and `overview-roi-locations.png` are resized orientation aids and must not support a detail-quality claim.

**VISUAL OBSERVATIONS, cause unverified:** the ridged shell has continuous broad curved bands, but the trough boundaries look soft at native scale. Its bright surface carries small cyan/pink points and mottling. The porous grain shows rounded, low-contrast pores with similarly coloured bright points; many pore boundaries are not crisply separated. These appearances alone do not distinguish scene sparkle, sensor noise, demosaic artifacts, focus error, or stacking artifacts. A matching source-RAW development is needed before attributing a defect to the merge.

**ARGUED target selection:** the porous-grain ROI is preferable for the immediate 2-D placement check because its pores furnish structure in both directions. The shell's bands are useful for a later ridge-continuity comparison but are directional and repeated, which can make translation less well constrained. Both features were recognisable near the middle embedded preview, but no claim that frame 129 is their sharpest RAW frame has been made. Neither ROI is a verified flat noise-control region.

## One bounded RAW check

Commands actually run from repository root, using the installed Python 3.12 executable with `-I -B`:

```powershell
python -I -B experiments/quality-september19/star-inspection-1/inspect-star.py
python -I -B experiments/quality-september19/star-local-green-translation.py
python -I -B -X faulthandler experiments/quality-september19/star-porous-translation-run.py
```

The second command only prepares mapped patch coordinates for both frozen ROIs; it decodes no RAW. The third command was explicitly authorised for **porous-grain only**, ordinals **125 through 133**, and performs exactly one extraction and fixed fit. Detailed executable paths and bounded-child command are recorded in `../star-porous-translation-1/process.json`; hashes and fixed limits are in its `preregistration.json`.

The adapter reuses the unchanged September 14 registrar, SHA-256 `5b64f7e612fd94cd8a22515bffb67addcee71021f6338f10a249c63864420196`. The star warpmap hash is `6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1`. Original CFA stays **u16**, copied while inside each RawPy context. No aligned frame or demosaiced frame is materialised.

For reference-sensor coordinate `z`, source sampling uses `C + a*(z-C) + 2*b_plane + delta_source_native`, with `C = 3516 + 2344i`. True green sites alone form a normalized Gaussian guide with sigma **1.5 native pixels** and radius **6**; exact 16383 sensels are excluded. The correction is bounded at **±4 native pixels**. The unchanged left fit/right validation split has 32-pixel outer margins, stride 2, and a 12-pixel guard on each side of the middle. Gain and offset are fitted on the left only and transferred to the right; before and after each have their own left nuisance fit. These gains are diagnostics, **not corrections to the RAW values**.

The existing positive-shift, wrong-sign, and blur-only controls ran before fitting photographic patches. They are falsifiable: known shifts must recover within 0.05 native pixels, and wrong-sign shifts must worsen held-out prediction. A photographic correction fails the prospective residual criterion if its held-out RMSE does not decrease; a boundary solution is not accepted. Residuals can still be fooled by matching blur or scene-dependent photometry, so a reduction does not prove geometric truth or preserved sharp detail.

**MEASURED**, from `../star-porous-translation-1/fit/result.json`:

| Ordinal | Source delta x, y (native px) | Held-out RMSE after / before | Converged | Bound hit |
| ---: | --- | ---: | --- | --- |
| 125 | +0.2322, +0.4127 | 0.943065 | yes | no |
| 126 | +0.2236, +0.3032 | 0.945986 | yes | no |
| 127 | +0.1647, +0.2172 | 0.945445 | yes | no |
| 128 | -0.1065, +0.1381 | 0.943902 | yes | no |
| 129 reference | 0.0000, 0.0000 | 1.000000 | yes | no |
| 130 | +0.0453, -0.2927 | 0.879079 | yes | no |
| 131 | -0.0209, -0.5553 | 0.869999 | yes | no |
| 132 | -0.0396, -0.6190 | 0.917127 | yes | no |
| 133 | +0.2379, -1.0964 | 0.883125 | yes | no |

All fitted gains were positive, ranging from 0.929939 to 1.067988. The reference's residual is numerical roundoff (about 2.14e-15), so its ratio is an identity check, not independent evidence. The worst retained support separation is **3.916479 native pixels**, after accounting for filter, displacement, numerical-derivative, and sampling support.

The central **408 × 408 original-u16 patch**, source origin **(586,1416)**, matched a second independent rawler decode with **zero differing sensels**. The other eight patches were not second-decoded; this limited validation scope is explicit in the staging receipt. Every patch has its own u16 SHA-256. File size and last-write time remained unchanged for all nine input RAWs. This is not a full source-file content-hash guarantee.

The bounded child tree finished using **6.171875 CPU seconds**, **7.875 wall seconds**, and **148,234,240 bytes** peak committed job memory. The local fit's own process-time reading was 0.84375 seconds. These are single operational observations, not comparative speed measurements. Limits were 90 CPU seconds, 120 wall seconds, and 2 GiB committed memory; all child processes exited and terminal accounting was collected.

There was no parameter sweep, reconstruction, corrected TIFF, source-side sidecar change, production edit, or default promotion. The next photographic test can apply these fixed geometric deltas to original CFA gathers while leaving intensities and all other processing fixed.
