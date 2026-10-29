# Original-CFA forward-model commissioning

Status: **SYNTHETIC ONLY; product admission false.** This is a bounded original-observation hypothesis producer, not an image renderer. No actual capture/cache pixels were read in this stage, no FocusEvidence peak/width was fabricated, and no production module was changed.

## Result and scope

**MEASURED:** The fixed cosine observer can retain same-PSF, ideal two-dimensional phase diversity above a single CFA's sampling band while the complete-cohort conjunction refuses the tested PSF, geometry, motion, illumination, duplicate-phase and missing-support foils. It is not yet a sufficiently powered certificate for the exact six-source bee cohort: the measured-trajectory synthetic positive has 76/450 patch-folds above the frozen prediction-variance cap. All such failures remain Unknown. It would be incorrect to replace this fact with the ideal-phase positive or to use an individual passing fold to admit the cohort.

**MEASURED:** Finite model approximation is material. At the fixed 24→8 sensor geometry, single off-grid tone transfer ranges from 0.9532 to 1.0730 across colors/patches/folds. A common scene can therefore be rejected because of the field model. `ForwardModelInconsistent` means rejection of this fixed hypothesis, not physical PSF disagreement. There is no real photographic/detail/noise benefit claim from this observer.

The public-research result is a three-state per-fold/color hypothesis, plus its exact model/source/geometry identities. Complete-cohort consistency is a conservative conjunction of all 18 fold/color results for one simulated noise seed. The six folds share training photons, so 144 rows are not 144 independent trials. Eight seeds are replications of one fixed family of spatial signals and phases, not a population guarantee. Flat/detail-Unknown does not prohibit ordinary conditional flat denoising.

## Preserved failed hypotheses

1. Open-clamped cubic v1: weak/unobservable boundary coefficients. Exact zero columns were considered only when identically zero in both training and held functionals; even removal did not cure the rank deficit. An independently balanced six-phase geometry also failed all 18 structural folds. The initial results and `repeat-forward-v1-source/` remain unchanged.
2. Natural-boundary spline v2: geometric viability improved, but the known identical-PSF high-frequency positive gave 88 Inconsistent and 56 Unknown of144, zero Consistent. Clean transfer ranged approximately0.777–1.114. This is a failed instrument, not evidence against the sources. `repeat-forward-v2-source/` preserves the exact source.
3. Cosine v3 is a separately frozen hypothesis class with fresh seeds208–215. Neither its basis nor its context is selected using real held residuals. Its protocol SHA256 is `4fd2bc0b686f8446c5b0ae8ceb4117312b9adce4e432cbed4461df5aa40aae69`.

## Actual operator and frozen controls

Twenty-five positions are parity00 of the original fixed5×5 cell positions, fit24sensor and scorecentral8. R/B use their original CFA sites; both green site sets observe one common green field but do not become extra independent acquisitions. The fixed full basis has18×18 tensor cosine modes; the restricted placebo has12×12. The pre-aperture field is integrated analytically over the inverse-transformed original unit sensor square. Unregularized f32 WLS uses the other five acquisitions and oracle original-site expected means for injected temporal variance. Known oracle variance is a mechanical control, not a measured-camera or noisy-guide calibration.

The actual implemented linear predictor B maps whitened training observations to held predictions. Covariance is computed from that actual f32 operator as B Bᵀ, with held original variance added before full residual whitening. The detail difference uses `(Bfull−Blow)(Bfull−Blow)ᵀ`; it does not pretend two fits have independent noise. No eigen truncation or ridge is hidden in the covariance. Fixed guards are scaled-Gram condition≤1e6, training samples≥coefficients+64 and maximum prediction variance/held variance≤4. All25 patches must be available; no survivor-only score.

Every ordinary high/negative case uses the balanced3×2 sensor-phase plant. Only `measured-high` uses the saved corrected RGB pulls for globals[3,4,20,23,12,28], fullquad[3516,2344], and the actual25 brow positions. All source phases and every model/cutoff are fixed before simulated photons. The current synthetic noise law is uniform across CFA sites; an actual caller must preserve separate R/G1/B/G2 sensor levels/noise and gain², even with a shared green field.

The bright/low flat controls ran first: all144 outcomes Unknown in each; mean whitened energy was1.00823 and1.02159. The latter retains known rounding/model discrepancy; neither noise nor thresholds were tuned to it. Weak and strong-common-lowpass controls also remain Unknown for detail. The ideal-phase high positive has per-color predicted-known-truth MSE/native-same-count-bilinear ratios0.0367/0.0152/0.0491. These are original held-sample mechanics against an intentionally lossy native interpolation foil, not an image-quality metric.

| Plant | Consistent | Unknown | Inconsistent | All18 consistent seeds |
| --- | ---: | ---: | ---: | ---: |
| flat-bright | 0 | 144 | 0 | 0/8 |
| flat-low | 0 | 144 | 0 | 0/8 |
| high | 133 | 11 | 0 | 3/8 |
| weak | 0 | 144 | 0 | 0/8 |
| common-lowpass | 0 | 144 | 0 | 0/8 |
| unequal-psf | 9 | 45 | 90 | 0/8 |
| blue-blur | 92 | 20 | 32 | 0/8 |
| wrong-geometry | 22 | 31 | 91 | 0/8 |
| wrong-blue-phase | 99 | 5 | 40 | 0/8 |
| motion | 8 | 55 | 81 | 0/8 |
| blue-motion | 91 | 30 | 23 | 0/8 |
| drift | 0 | 48 | 96 | 0/8 |
| phase-drift | 43 | 5 | 96 | 0/8 |
| blue-illumination | 105 | 31 | 8 | 0/8 |
| opposite | 0 | 8 | 136 | 0/8 |
| clipped | 0 | 144 | 0 | 0/8 |
| duplicate-phase | 0 | 144 | 0 | 0/8 |
| one-axis | 48 | 96 | 0 | 0/8 |
| measured-high | 109 | 35 | 0 | 0/8 |
| curved | 135 | 9 | 0 | 3/8 |
| edge | 133 | 11 | 0 | 3/8 |

The same-PSF positive, curved and edge cases each have only3/8 complete-cohort successes. The power limit is retained. Individual passing folds in the adverse plants never authorize source removal, favorable subset choice or RGB admission. X-only phases do support the shared green lattice in this particular plant, but R/B remain unidentifiable; the RGB outcome is unavailable.

**VERIFIED:** The absolute-sensor aperture oracle passed18 checks including nonidentity rotation/scale, all CFA sites and high cosine modes, maximum error<5e−6 against independent32×32 aperture quadrature. The actual patch producer held-photon poison control passed all three colors: finite and clipped changes to acquisition28 leave that fold's operator and every prediction bit identical, while the finite held residual changes and the clipped held score is refused. The same poison changes predictions in folds where that source is training, proving the poison reaches the numerical path. This does not establish independence of a future noisy-guide caller.

## Approximation-bias census

All five predeclared [fitSide,scoreSide,fullAxis,restrictedAxis] contexts were retained: [16,8,12,8], [24,4,18,12], [24,8,18,12], [24,12,18,12], [32,8,24,16]. Each has all25positions×6folds×3colors. Three separate off-grid tones, a quadratic field plus mixed tones, and a smooth nonperiodic edge plus mixed tones were independently integrated over the sensor square. No random photons are used for this bias table; injected oracle variance only fixes the estimator weights. No context is selected for a real patch.

The saved summary contains every per-tone/color range. Some24→4 R/B samples have zero AC support, so transfer is unavailable rather than silently replaced with one. Larger context often reduces mean squared bias but does not monotonically eliminate phase/edge transfer errors. Changing score size also changes the measured AC domain; it is not a causal optical bandwidth comparison.

| Fit / score sensor side | Known field | Color | Mean squared bias DN² | Clean AC transfer range |
| --- | --- | --- | ---: | --- |
| 16 / 8 | curved | R | 21.352 | 1.0033–1.0357 |
| 16 / 8 | curved | G | 34.519 | 0.9990–1.0751 |
| 16 / 8 | curved | B | 36.081 | 1.0082–1.0578 |
| 16 / 8 | edge | R | 22.856 | 1.0034–1.0597 |
| 16 / 8 | edge | G | 35.659 | 0.9991–1.0746 |
| 16 / 8 | edge | B | 38.067 | 1.0093–1.0671 |
| 24 / 4 | curved | R | 3.958 | 0.6628–1.1809 |
| 24 / 4 | curved | G | 15.032 | 0.9304–1.1044 |
| 24 / 4 | curved | B | 11.881 | 0.8504–1.8483 |
| 24 / 4 | edge | R | 3.838 | 0.7275–1.1226 |
| 24 / 4 | edge | G | 14.833 | 0.9285–1.1006 |
| 24 / 4 | edge | B | 11.086 | 0.7428–1.3105 |
| 24 / 8 | curved | R | 5.547 | 0.9775–1.0000 |
| 24 / 8 | curved | G | 15.236 | 0.9619–1.0240 |
| 24 / 8 | curved | B | 10.304 | 0.9666–1.0009 |
| 24 / 8 | edge | R | 5.973 | 0.9796–1.0125 |
| 24 / 8 | edge | G | 15.963 | 0.9619–1.0290 |
| 24 / 8 | edge | B | 10.476 | 0.9662–1.0027 |
| 24 / 12 | curved | R | 4.917 | 0.9918–1.0045 |
| 24 / 12 | curved | G | 16.109 | 0.9816–1.0145 |
| 24 / 12 | curved | B | 11.838 | 0.9916–1.0081 |
| 24 / 12 | edge | R | 5.741 | 0.9911–1.0051 |
| 24 / 12 | edge | G | 17.040 | 0.9817–1.0158 |
| 24 / 12 | edge | B | 12.609 | 0.9908–1.0089 |
| 32 / 8 | curved | R | 2.419 | 0.9951–1.0079 |
| 32 / 8 | curved | G | 6.915 | 0.9744–1.0013 |
| 32 / 8 | curved | B | 4.754 | 0.9943–1.0189 |
| 32 / 8 | edge | R | 3.822 | 0.9903–1.0368 |
| 32 / 8 | edge | G | 7.573 | 0.9713–1.0013 |
| 32 / 8 | edge | B | 6.383 | 0.9917–1.0265 |

The noisy curved/edge controls use `repeat-forward-cosine-nonbasis.py`, which binds and installs the independent aperture-integrated truth from `repeat-forward-cosine-bias.py`. The older point-evaluated curved/edge branches in the general harness were **not run** and are not commissioned exact-aperture controls. Both the wrapper and override source hashes are recorded in those result files.

## Commands and identities

Working directory for every command: `C:/Users/chris/.codex/worktrees/multi-stack/strehl`. Python/NumPy version and recursive model source hashes are in each result; command, exit status, host memory/load and worker environment are in each corresponding fresh `*-run-01/receipt.json`. Maximum observed private memory for the largest bias census was491,249,664bytes, below the4GiB lane cap. Runs shared the machine with other authorized lanes; these are resource receipts, not isolated speed claims.

Actual ordinary case command template, instantiated for every listed case except curved/edge:

```powershell
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/repeat-forward-cosine-CASE-run-01 --cwd . --env RAYON_NUM_THREADS=4 -- python experiments/multi-stack-2026-10-28/completion/sr/repeat-forward-cosine-controls.py outputs/multi-stack/completion/repeat-forward-cosine-CASE-01.json CASE --workers 4
```

For curved/edge the producer filename is `repeat-forward-cosine-nonbasis.py`; the receipts retain the exact instantiated commands. Other exact commands:

```powershell
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/repeat-forward-cosine-bias-run-01 --cwd . --env RAYON_NUM_THREADS=4 -- python experiments/multi-stack-2026-10-28/completion/sr/repeat-forward-cosine-bias.py outputs/multi-stack/completion/repeat-forward-cosine-bias-01.json
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/repeat-forward-cosine-isolation-run-01 --cwd . --env RAYON_NUM_THREADS=1 -- python experiments/multi-stack-2026-10-28/completion/sr/repeat-forward-cosine-isolation.py outputs/multi-stack/completion/repeat-forward-cosine-isolation-01.json
python experiments/multi-stack-2026-10-28/completion/sr/repeat-forward-cosine-analyze.py outputs/multi-stack/completion outputs/multi-stack/completion/repeat-forward-cosine-summary-01.json
```

The complete saved summary binds all21 noisy case files and the known-field census by SHA256. `repeat-forward-v3-source/receipt.json` freezes the recursive source checkpoint. No original reads, RAW decode, product build or full render were performed in this stage.

## Explicit next boundary

**ARGUED:** This supports a research hypothesis record distinct from sweep focus: `OriginalForwardHypothesis { model_identity, original_identities, guide_identities, consuming_geometry_identity, physical_domain, per_fold_color_results, support_and_condition_refusals, original_and_guide_footprints, covariance_scope, product_admission:false }`. It does not yet justify a product `RepeatCompatible` or sharp/detail eligibility variant. Stable common blur can remain a common field; the tested strong blur becomes detail-Unknown, not unsafe for ordinary denoising.

Before any new real-source diagnostic, preserve original content identities and source-cache binding, exact four-site levels/noise, per-original frozen guide prediction/variance/support including negative interpolation taps, and all guide dependencies. Q0/Q15 are disjoint from held acquisitions but were previously observed and their noise creates a random plug-in variance model. All-source registration ancestry remains conditional. A diagnostic could retain per-fold field consistency with admissionfalse; the present six-source complete-cohort prediction-variance refusals must remain visible. It must not switch basis, drop difficult sources or lower the cap after reading held values. Parent authorization is still required for that next actual-pixel lane.
