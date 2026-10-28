# Native restoration: moderate acutance, unresolved defects

2026-10-27. **VERIFIED photographic mixed result, no default promotion.** Root inspected both complete images before all ten weevil and eight flat native384 pairs, under identical development. Existing scale and hair contours and chart boundaries become firmer. Dark insect texture becomes coarser, glints harder and some contours visibly stepped. The weevil's soft/doubled hair remnants, pale occlusion rims and glare persist. The flat radial convergence region and finest unresolved bars remain unresolved. This is a real contrast effect, not demonstrated newly resolved structure or state-of-the-art stacking. Seven of eight generated quality guards fail; those results are retained.

## Complete evidence

| Dataset | Previous complete view / master | Experimental complete view / master |
| --- | --- | --- |
| Weevil299,6896x4596 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/baseline/complete-stack.jpg), [RGB16](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/baseline-master.tiff) | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1/candidate/complete-stack.jpg), [RGB16](../../../outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output/candidate-master.tiff) |
| Flat60,6932x4620 | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/baseline/complete-stack.jpg), [RGB16](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/baseline-master.tiff) | [JPEG](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-views-1/candidate/complete-stack.jpg), [RGB16](../../../outputs/raw-quality-2026-10-27/native-restoration-flat-1/output/candidate-master.tiff) |

Both pairs were shown to the user with full-resolution masters. Each output directory also retains both signed sensor f32le masters, sidecars and float RGB TIFFs. Each view directory retains the full JPEG, orientation overview, all frozen unresampled384px PNG/RGB16 witnesses and display receipt. Root initially attempted too many images per tool call and received truncation; those did not count as inspection. All eighteen native pairs were subsequently viewed in batches of two pairs. Frozen coordinates are bound by the display receipts; no new favorable crops were selected.

Full-frame source lineage is the existing complete299-source107MSDCF weevil and60-source flat-et1s-sw4-cpl. These runs change only the saved merged-CFA reconstruction before the actual final writer. Original RAW reads=0. Weevil retains its CA-off preparation, reference149, native origin[68,46]; flat retains its CA-on preparation, reference30, origin[50,34]. Exact saved WB, color matrix, display baseline and material metadata are preserved per dataset. Previous source-merge and alignment costs remain required. This is not a new end-to-end RAW performance measurement.

## Fixed recipe and controls

The [brief](brief.md) freezes the same-phase binomial correction with a local3x3 range constraint before execution. Four CFA phases use identical f32 operators independently, with2native-pixel phase spacing. No tone fitting, model-derived PSF, source selection or additional demosaic. The unbounded1.5-maximum-frequency-gain foil is retained: it produces12.5% sharp-step excursions. The bounded operator removes those excursions but is not a proof against halos, noise or color errors.

All eight controls and deliberate destroyers completed through the actual final MHC helper. Hard validity, input preservation, off identity and local-range checks pass. Only the sharp-step quality case passes. Neutral/colored flat chroma RMS increases17.95→20.76 and18.52→21.48DN. Glint green error41.44→61.67DN and RGB56.18→74.25DN fail. Independent-color green error137.16→157.47DN fails despite improved selected amplitudes. Near/far fine amplitude0.840→1.123 overboosts; coarse1.002→1.013 remains. The generated superposition is not an occlusion oracle. The synthetic unequal-phase noise model is a stress model, not newly measured Sony calibration or the merged-image covariance.

Finite complete diagnostic rendering was explicitly authorized in advance despite generated quality failures; all admission flags remain false. These are not silently relaxed gates. See [independent design review](independent-design-review.md), [independent full receipt audit](independent-photo-receipt-review.md), [independent photographic review](independent-results.md) and [generated visual harms](generated-visual-review.md). The old restore.rs transfer model was not adopted as an exact inverse of the modern MHC/gather/remosaic/band-merge/final-MHC pipeline.

## Execution and identity

**MEASURED**, from the worktree, Python3.12,4Rust workers, pinned test-only feature set and exact tests. The runner records full environment, source bindings, command, limits and host load. All following commands actually ran with exit0 and terminal job accounting:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run.py build 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run.py screen 1 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run-views.py generated --input outputs/raw-quality-2026-10-27/native-restoration-screen-1/output --out outputs/raw-quality-2026-10-27/native-restoration-generated-views-1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run.py weevil 1 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run.py flat 1 --iteration 1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run-views.py weevil --input outputs/raw-quality-2026-10-27/native-restoration-weevil-1/output --out outputs/raw-quality-2026-10-27/native-restoration-weevil-views-1
python -B -X faulthandler experiments/raw-quality-2026-10-27/native-restoration/run-views.py flat --input outputs/raw-quality-2026-10-27/native-restoration-flat-1/output --out outputs/raw-quality-2026-10-27/native-restoration-flat-views-1
```

Fresh Compiling build238.422s; binary SHA256`339efc0ac1652501b2a834ab9305cc7c6ede792316c42d20f7dfdbc32d32714d`. Operator`983bef507afa85de503ec68517ea988e81f5c0010aaa94fe4fccacfc2dd1cccb`; writer`ed03928f9676382ff4780c6b5e558c2394e4ea69476f27faba1395b4cf3cfaea`; controls`4b4e30c35b4c8b4651447d8432a76a15813c7c26e8ebcd1fc624bdc33d22f78a`. Build uses locked offline release CLI library tests with native-direct-planes,native-correction-variance,native-gpu-gather features; actual reconstruction is CPU-only. Existing104 warnings are retained.

| Job | Wall seconds | Peak committed job bytes |
| --- | --- | --- |
| Eight generated cases | 0.859 | 7,815,168 |
| Complete weevil reconstruction/writer | 4.547 | 766,038,016 |
| Complete flat reconstruction/writer | 4.640 | 774,049,792 |
| Weevil display export | 4.719 | 981,835,776 |
| Flat display export | 4.593 | 991,748,096 |

Exact complete no-op RGB16/float pixels, signed-CFA off values and material metadata passed before either candidate. Independent audit rehashed119 bindings totaling4.35GB and verified complete masters, source preservation and zero RAW reads. RGB16 provenance Software differs from held originals; actual pixels/material match. Candidate master SHA256: weevil`d31e93271d77a85bfb1ba1bae7ca8d672252d17590af844f528044c5aae218ea`; flat`9bf8939e26470500beb64d4d9c033557eafab94f7b0351037c20f5f8e967eb4a`.

Existing Helicon8.3.11 B8/B4/C full workflows remain the competitive context, including their unresolved defects and differing predevelopment/gauge. A post-merge4.55s replay does not establish a faster complete workflow or a photographic win over those outputs. No GPU timing claim follows. No production default or SYNTHESIS fold is made. Continue upstream source-support diagnosis, retaining this mixed photographic result rather than tuning it against isolated crops.
