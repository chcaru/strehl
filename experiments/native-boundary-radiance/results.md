# Boundary radiance prototype: rejected

2026-09-09. **MEASURED, independently reviewed:** the fixed local affine two-layer reconstruction reduces flat noise but substantially worsens textured boundary fidelity. Do not promote it or tune its support, basis, threshold or geometry against this population. The default remains unchanged. This closes one optical reconstruction hypothesis, not the broader usefulness of RAW data.

The operator consumes original u16 CFA observations, subtracts the existing black level into f32, uses the injected noise model, and accumulates same-colour sufficient statistics. Its footprint moments share foreground visibility and background intersections along the same pupil ray. Accepted estimates enter the existing collapsed four-plane output before the current writer. The experiment supplies known M194g depths, pupil and geometry; it never supplies hidden radiance values or slopes to the estimator. Geometry estimation on a real macro stack is not implemented by this prototype.

## Actual result

The independent flat-first policy was committed before scoring at e86f9192917e661da4dfbb2a86c3bd8c608b38de. It reuses the existing admitted TIFF reader and M194g quality reductions. Metrics below use post-white-balance raw-DN units on the fixed native-coordinate boundary region.

| Observation | Baseline | Candidate | Disposition |
|---|---:|---:|---|
| Flat G temporal variance, DN² | 240.3911 | 42.3896 | Lower noise; insufficient for quality |
| Flat G noise-off ideal RMSE, DN | 0.04016 | 0.04016 | Unchanged |
| Textured R noise-off boundary RMSE, DN | 159.6262 | 293.6742 | Worse |
| Textured G noise-off boundary RMSE, DN | 160.5236 | 292.1555 | Worse |
| Textured B noise-off boundary RMSE, DN | 160.8547 | 304.3141 | Worse |

RMSE is DERIVED as the square root of the measured MSE in the saved scorer output. Variance can reward blur or bias, and MSE can reward smoothing: the fixed policy also requires local complex-wave fidelity and extreme-error preservation. Flat passes all20 checks. Textured fails30 of38 checks, including all12 window extreme-error checks and6 of12 complex-wave checks. The much larger boundary loss independently remains when the scored output changes from noise-off to the eight-repeat mean: boundary MSE increases3.27–3.60x across RGB. Rejection therefore does not depend on a tiny tolerance or one noise realization.

The displaced-boundary control changes the model offset by+4 native pixels while retaining the same treatment and scoring masks. It gives lower boundary MSE than the correct-geometry candidate in all three channels, but remains worse than baseline. The expected destroyer ordering therefore fails. It also accepts only2605 sites versus3447 with correct geometry in noise-off: fewer harmful replacements confound this comparison. It does not establish that the displaced geometry is more accurate. The residual diagnostic is not a quality score.

See [flat decision](score-flat-1/decision.json), [textured decision](score-textured-1/decision.json), [full texture readout](score-textured-1/result.json), [control readout](control-readout-1/result.json) and [independent review](independent-review.md).

## Controls and cost

Exactly39 primary TIFFs were produced:18 flat,18 textured,2 genuine-colour off/no-treatment,1 displaced. All18 fresh feature-off TIFFs are byte-identical to their saved HardFloor baselines. Every apply run exercises actual treatment. Each M194g render consumes the original five admitted CFA files exactly once; no aligned stack or extra decode is introduced.

The colour off/no-treatment pair is byte-identical and contains independently decoded, nonconstant chroma:60173 of60208 pixels have R different from G, and60171 have B different from G. This establishes live colour preservation for no treatment, not the quality of treating independently coloured depth layers.

The early operator controls cover independent affine recovery, constant layers, rank/variance refusals, both sides of the Schur-pivot threshold, bit-preserving abstention, analytical cell moments, and15 separately ray-integrated rows. Their image-quality scope is deliberately empty. The later production comparison supplies the missing actual consumer evidence.

The41 production test invocations (39 renders plus2 colour plan steps) consumed11.725s summed child wall and9.859375s owned CPU, with maximum recorded Job committed memory11632640 bytes. These are small320x240 or colour-fixture runs, one observation per output. They are experimental cost, not an admitted speed benchmark, and cannot predict native33MP overhead. The two release builds took91.828s and92.656s. Both recorded a fresh Compiling strehl-cli line.

## Reproduction and lineage

Commands actually run from the repository root with Python3.12; source and artifact bindings accompany each stage:

~~~text
python experiments/native-pyramid-profile/build.py --boundary-radiance --output-dir experiments/native-boundary-radiance/build-1
python experiments/native-boundary-radiance/run-controls.py
python experiments/native-pyramid-profile/build.py --boundary-radiance --output-dir experiments/native-boundary-radiance/build-2
python experiments/native-boundary-radiance/run-matrix.py --scene flat
python experiments/native-boundary-radiance/run-placebos.py --case color
python experiments/native-boundary-radiance/score.py --scene flat --input-dir experiments/native-boundary-radiance/run-flat-1 --output-dir experiments/native-boundary-radiance/score-flat-1
python experiments/native-boundary-radiance/run-matrix.py --scene textured
python experiments/native-boundary-radiance/run-placebos.py --case displaced
python experiments/native-boundary-radiance/score.py --scene textured --flat-decision experiments/native-boundary-radiance/score-flat-1/decision.json --input-dir experiments/native-boundary-radiance/run-textured-1 --output-dir experiments/native-boundary-radiance/score-textured-1
python experiments/native-boundary-radiance/read-controls.py
~~~

The actual executable was C:/Users/chris/AppData/Local/Programs/Python/Python312/python.exe with -I -B. Operator source68be9c37939104318e18ff3a547948260be2eacd; integrated source7ef4e4a6f6c265f45128cee08d71cec20ae2f695. Build2 test executable SHA256 facb0a0c4237c398cd1e0ee59e2c3476d99bd8e159eb995f0ecfb542a0b1e9ab. Fixed population/runner3511763b; placebo runner58a7a6a4; independent scorer e86f9192; supplemental reader9fe3a46e. Compiler logs, process receipts, immutable inputs, individual TIFF hashes and decisions are retained in this directory.

No original D:/personal/macro file was decoded or altered in this experiment. The prior native speed gains remain separate, measured results. Neither SOTA photographic quality nor competitive speed is established here.

