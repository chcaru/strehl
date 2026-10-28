# Supplied training blur restores projections, not overall fidelity

2026-10-27. **VERIFIED conditional image refusal.** Supplying the true five training variances removes most attenuation of the measured genuine components. It does not make this fixed-work reconstruction faithful overall: RGB and chroma errors still exceed the unchanged bars, slightly worsening relative to the counted joint fit. Close this fixed radiance/prior/optimizer recipe under the brief; no full-photo adapter, solver repair or parameter campaign follows. This is not rejection of original-CFA inverse methods in general.

Root executed:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/known-variance/controls.py --out outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output
```

Exit0, 8.703s, peak job3,560,591,360bytes, complete terminal accounting and no cleanup errors. Both requested cases completed; neither was skipped. These are diagnostic costs, not full-workflow performance. Frozen model SHA`c95d3c0fdfd237a6192c6167181929ae03450ecec78a45330f85af873a33a88c` consumed training IDs0..4 at f32 values corresponding to `[0,.35,.8,1.6,3]`. Only radiance `z` was optimized; no joint variance parameter remained. The wrong extra held-ID mapping was rejected. Held truth was never supplied; their disjoint calibration procedure stayed unchanged. I independently verified all139 source bindings, all14 original-u16 identities, completion report hashes and both saved master/prediction hashes.

## Complete image review

I viewed complete unresized96x96 [truth](../../../../outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output/compatible/truth-complete.png), [supplied-blur fit](../../../../outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output/compatible/fit-complete.png), [initialization](../../../../outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output/compatible/initial-complete.png), and [counted joint fit](../../../../outputs/raw-quality-2026-10-27/raw-blur-counted-1/output/compatible/fit-complete.png) at the unchanged fixed display. The modulation is stronger in the supplied-blur result, but the complete pattern remains less clean than truth; the change is modest at native display scale. Full float masters are retained for [compatible](../../../../outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output/compatible/fit/fields.npz) and [neutral flat](../../../../outputs/raw-quality-2026-10-27/raw-blur-known-variance-1/output/flat-neutral/fit/fields.npz). These small generated images are not photographic stacks.

| Quantity | Counted joint fit | Supplied training blur |
| --- | --- | --- |
| Near-fine recovery | .9070 | .9823 |
| Blue-diagonal recovery | .9470 | .9917 |
| Weak-green crossing recovery | .9177 | .9809 |
| Third red harmonic recovery | .8581 | .9605 |
| RGB RMSE, DN | 52.5561 | 53.7711 |
| Chroma RMSE, DN | 58.3049 | 60.9789 |

All eight component recovery and per-channel amplitude guards now pass, including coarse detail. Nevertheless RGB/chroma bars remain45.8054/37.8277DN, so `known_detail_pass` correctly remains false. A collection of truthful projections does not constrain all residual image structure. Both held predictions pass all original global, phase and cell guards, RMS1.14776/1.04288sigma. Successful prediction also does not establish a faithful delivered image.

**MEASURED descriptive check, no new gate:** reading only saved float arrays, `e=(output_rgb_dn-truth_cell_rgb)` has full-image quadrant RMS53.11/52.62/58.90/56.08DN. Central64x64 channel RMS is62.81/31.30/61.23DN; channel means are−.14/−.23/−.73DN. Thus substantial error remains throughout the image, including its scored interior, and cannot be summarized as a constant color offset. This does not identify its cause or separate prior, optimizer, interpolation and inference effects. No model import, fit, RAW read, crop search or retone was performed for this review.

The complete neutral-flat fit appears uniform at the same display. RGB/chroma errors7.68595/10.74503DN pass the unchanged mean-reference guard; held RMS.98927/1.00850sigma passes. Flat blur remains unidentifiable despite localized scalar searches. Both radiance fits retain `FIT_ITERATION_LIMIT`:64iterations, flat72/compatible69evaluations, gradients2.02e-5/.00257651 versus1e-6. There are no unsupported or hard-failure flags, but numerical refusal remains.

`all_pass`, `image_only_all_pass`, photographic admission and full-design qualification remain false. Adverse-model discrimination, spatial anchor-order reversal, native baseline equivalence, production memory and complete-photo quality remain untested. The supplied-blur intervention supports restored component amplitudes under this model; it does not justify promoting the image or blaming one remaining mechanism.
