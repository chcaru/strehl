# Compatible-detail observation: image and held prediction fail

2026-10-27. **VERIFIED rejection of the fixed returned reconstruction.** Unlike the flat observations, this compatible-detail case fails image-preservation and held-prediction guards in addition to numerical convergence. No complete-photo adapter or further iteration campaign is justified by this result. It does not establish impossibility of original-CFA blur reconstruction or rejection of all Gaussian models.

Root ran the separately authorized compatible-only dispatcher, which changes only the finite driver's requested case order. The entire original generator sequence still runs, retaining the exact original seed and CFA observations:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/finite-diagnostic/compatible-only.py --out outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output
```

Process exit0 in7.125s, peak job3,544,018,944bytes, terminal accounting complete and no error/cleanup failure. Model SHA remains`659da66d343908564b16262482dc55e3220dd15f8318bf49623a7b2d8d8106cc`; no prior, initializer,64iteration/160evaluation budget, noise, split or guard changed. This is a small generated diagnostic cost, not stacking speed.

I inspected the complete unresized96x96 [truth](../../../../outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/compatible/truth-complete.png), [returned output](../../../../outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/compatible/fit-complete.png) and [initialization](../../../../outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/compatible/initial-complete.png) under the identical fixed display. The crossed pattern remains recognizable, but the finer colored modulation is weaker and softer than truth. The result does not display a new fine structure that compensates for that loss. [Complete float fields](../../../../outputs/raw-quality-2026-10-27/raw-blur-compatible-1/output/compatible/fit/fields.npz) retain the240x240latent and96x96delivered/initial RGB arrays.

RGB/chroma RMSE is64.2118/65.8278DN against the unchanged45.8054/37.8277DN bars. Genuine near-fine recovery is.8374, blue diagonal.8715, weak-green crossing.8288, and the second/third red-line harmonics.8500/.7238. Their per-channel amplitude guards also fail. Neutral coarse.9742 and far coarse.9919 survive. Thus this is selective fine/color loss, not complete destruction or mere cosmetic contrast judgment. Weak-green crossing failure predominantly loses its red/blue components; its small green amplitude error alone does not indicate false-green contamination.

Held view5 fails at1.33036sigma, including R/B phase RMS1.45248/1.38672 and maximum cell RMS1.88194. View6 passes at1.13422sigma. Calibration parameters are numerically localized for both views, without a global-optimum or identification claim. Unlike the coloured flat, no unsupported variance-ceiling status causes this rejection.

The returned solution remains nonstationary:64iterations,69evaluations, final parameter-gradient maximum.0120859 versus1e-6. Objective reduction19.5879→8.8008 does not override the failed image or prediction evidence. Fitted training variances.00431/.47710/1.20066/2.61991 underestimate supplied.35/.8/1.6/3; held estimates.31108/1.91620 likewise fall below.6/2.3. Underestimated relative blur and softened latent detail co-occur. That is consistent with a blur/radiance tradeoff but does not isolate its cause or distinguish optimizer, prior and representation contributions. No causal intervention was performed.

I verified the source bindings, both saved-field hashes and all seven original-u16 identities. Observation SHA256`beb9bccb224b2c0effb1adad84a8c86e4b18ea6a08ac2686a75b77d959bdbe20`; fields SHA256`a813072b86b64786332e752d42ce1066b4460c34422fc0a883eed3b8c0802dee`. No original RAW, numerical rerun or display adjustment was used in this review. All adverse unknown fits, spatial anchor-order validation, actual native comparison and photographic evaluation remain unperformed. The flat diagnostics retain their passing image results; this structured rejection must not rewrite them as failures.
