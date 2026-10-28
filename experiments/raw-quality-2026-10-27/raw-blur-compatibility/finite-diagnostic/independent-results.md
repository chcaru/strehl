# Coloured-flat diagnostic: ambiguous blur, no observed image failure

2026-10-27. **VERIFIED finite diagnostic stopped on unsupported calibration variances, not failed image/prediction guards.** The compatible-detail fit was skipped. This does not establish physical-model failure on a constant field, convergence, selective mismatch rejection or photographic usefulness.

Root executed:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/raw-blur-compatibility/finite-diagnostic/controls.py --out outputs/raw-quality-2026-10-27/raw-blur-finite-1/output
```

Exit0 in7.359s, peak job3,545,792,512bytes, terminal accounting complete, no error/cleanup failure. Original generated observations reproduce run2 exactly; the parent operator commission passes unchanged. These are bounded diagnostic costs, not a stacking benchmark. No captured RAW or native comparison was used.

The coloured-flat returned image is finite. RGB/chroma RMSE4.11758/5.78615DN improves on the explicitly labelled same-data flat mean8.01512/10.73163DN and passes the original flat bars. Held RMS.99807/.99253sigma passes both global and local guards. I viewed the complete unresized96x96 [truth](../../../../outputs/raw-quality-2026-10-27/raw-blur-finite-1/output/flat-colour/truth-complete.png), [returned field](../../../../outputs/raw-quality-2026-10-27/raw-blur-finite-1/output/flat-colour/fit-complete.png), [initial field](../../../../outputs/raw-quality-2026-10-27/raw-blur-finite-1/output/flat-colour/initial-complete.png) and [mean reference](../../../../outputs/raw-quality-2026-10-27/raw-blur-finite-1/output/flat-colour/same-data-flat-mean-complete.png), all under the same fixed display. They look broadly uniform; no conspicuous colored lattice or contour appears. The [full float fields](../../../../outputs/raw-quality-2026-10-27/raw-blur-finite-1/output/flat-colour/fit/fields.npz) are retained. This flat contains no detailed structure that could validate preservation.

Both calibrated variances select256, triggering `calibration_variance_ceiling:5/6`. Neither selected value lies inside its final localized interval. Their sampled NLL ranges are only.02612/.02531; a blurred smooth field can explain constant observations over a broad parameter range. The values therefore are not measured optical blur or evidence that a Gaussian family is physically inconsistent. The prescribed unsupported-status stop remains in force; it was not silently exempted after seeing results.

Joint optimization also remains `FIT_ITERATION_LIMIT`:64iterations,70evaluations, final maxgradient.000743994 against1e-6. That unchanged numerical failure is retained independently of the passing image diagnostics. `image_only_diagnostic_pass=false` combines the unsupported-status guard with image/prediction tests; it must not be described as measured image degradation.

The compatible case did not run, and all adverse fits and spatial anchor-order questions remain untouched. `all_pass`, admission and full-design qualification remain false. A separately authorized isolated compatible observation would ask the untested detail question using the same fixed model; it must preserve these refusal records rather than reclassify this run. This reviewer changed no implementation, threshold, seed or solver and performed no numerical fit.
