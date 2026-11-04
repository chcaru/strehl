# Precision weighting under fixed native repeat membership

**MEASURED:** the existing precision mean fixes the unequal-variance regression in this mechanical fixture when supplied exact expected signal and an unchanged equal-observation focus reference. It does not fix mismatched PSFs or guarantee a chosen primary's appearance. No engine source or default changed.

## Frozen operator and reproducibility

`repeat-proposal-precision-controls.rs` copies the source/photon/PSF equations from root's `repeat-proposal-consumer-controls.rs` SHA256 `eb1935044226cff9345381d7ba8cec358fca02e918dcd41700e84f6f654d6748`. Eight original-u16 sources form four fixed cross-pass groups [0,4],[1,5],[2,6],[3,7]. All arms regenerate identical photons from seed/source IDs, gather through actual NativeSampler and invoke PreparedSource/GroupWorkspace/SessionMerge. No aligned volume, RAW reads or privately fitted noise model.

Twelve arms cover equal proposed, oracle precision with EqualObservation, precision with Delivered focus, missing-guide precision, all-single, partial legacy, equal/precision with primaryA/B, and each single pass. Oracle predictions are deterministic source-specific latent means in original black-subtracted DN with separate acquisition IDs. They are not reconstructed target photons and do not commission a real noisy guide. This is the key limitation. The normal configuration remains7bands/gate2/exponent2/sharpen1.4/agreement4; bands0 is an internal flat estimator control only.

Build `np-precision-b01` executable SHA256 `680bf21001c936c0d5d99e32813c57367f3d33d9e07b6ab27c38dbb09cd56017` binds product16 support libraries and every recursively included source with unchanged pre/post hashes, archived before root's release17 build. Commands actually run:

```powershell
python experiments/multi-stack-2026-10-28/completion/sr/build-roi.py --fingerprint target/release/.fingerprint/strehl-cli-63ce8e1d9f947ed6/lib-strehl_cli.json --out outputs/multi-stack/completion/np-precision-b01 --source experiments/multi-stack-2026-10-28/completion/review/repeat-proposal-precision-controls.rs --build-id product16-repeat-proposal-precision
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/repeat-proposal-precision-flat-run-01 --cwd . --env RAYON_NUM_THREADS=4 -- outputs/multi-stack/completion/np-precision-b01/repeat-proposal-precision-controls.exe outputs/multi-stack/completion/repeat-proposal-precision-flat-01.json flat
python experiments/multi-stack-2026-10-28/completion/review/analyze-repeat-proposal-precision.py outputs/multi-stack/completion/repeat-proposal-precision-flat-01.json outputs/multi-stack/completion/repeat-proposal-precision-flat-analysis-01.json
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/repeat-proposal-precision-full-run-01 --cwd . --env RAYON_NUM_THREADS=4 -- outputs/multi-stack/completion/np-precision-b01/repeat-proposal-precision-controls.exe outputs/multi-stack/completion/repeat-proposal-precision-full-01.json full
python experiments/multi-stack-2026-10-28/completion/review/analyze-repeat-proposal-precision.py outputs/multi-stack/completion/repeat-proposal-precision-full-01.json outputs/multi-stack/completion/repeat-proposal-precision-full-analysis-01.json
python experiments/multi-stack-2026-10-28/completion/review/verify-repeat-proposal-baseline.py outputs/multi-stack/completion/repeat-proposal-precision-full-01.json outputs/multi-stack/completion/repeat-proposal-precision-baseline-equivalence-01.json outputs/multi-stack/completion/repeat-proposal-consumer-original-02.json outputs/multi-stack/completion/repeat-proposal-consumer-psf-02.json
```

Four workers, eight seeds160..167. Flat run10.164s/29,110,272sampled private bytes; full run44.393s/40,828,928bytes. These are operational receipts under concurrent root debug/release work, not comparative performance claims.

**VERIFIED:** all270shared original-case and216shared PSF-case saved numerical summaries and original diagnostic counters exactly reproduce root's existing equal-weight fixtures. The old harness did not retain complete arrays, so this is not a whole-output bit-identity claim. Missing-guide equality is stronger: the new executable compared every output float bit in36flat plus90full cases; the analyzer independently verified every ordinary averaged/single/fallback counter. Precision and missing-prediction counters are intentionally different and excluded from that invariance claim.

## Flat commissioning first

Before result inspection, criteria were fixed: bands0 observed temporal variance within5% of the injected inverse-variance prediction with the Gaussian-u16 rounding approximation1/12; lower variance than equal at20/1200DN; clean DC shift<=0.002DN. Normal7band flats require lower variance and unchanged clean DC, without treating bands0 theory as their model.

All16component/level/band cases passed. Bands0 variance differs by at most1.40% from the prediction. All clean DC differences are exactly zero in retained summaries. The normal7band precision/equal temporal variance ratio is0.408-0.639. Input noise is deliberately unequal (gain0.2 versus0.8DN/electron, read noise5electrons), with no noise parameter fitted from output.

**DERIVED:** for bands0, scalar weights use the injected green-luma variance ratio, not a separately optimal weight per color. For color c, the predicted final four-pair variance is `[w0^2*(v0c+1/12)+w1^2*(v1c+1/12)]/4`. The1/12 term describes this synthetic rounding plant only. It does not change camera calibration or the actual precision weights.

## Signal and appearance tradeoffs

Risk below is MSE to each pass's actual clean noise-gated consumer, separately; no argmax reference. Ranges cover all four CFA components, averaging the eight predeclared realizations. Full per-seed and component rows remain in the result. Transfer is centered AC projection of the clean candidate onto each clean pass reference.

| Case | Precision/equal risk to passA | Precision/equal risk to passB | Clean transfer to passA | Clean transfer to passB |
| --- | --- | --- | --- | --- |
| unequal-variance | 0.6020-0.6395 | 0.6020-0.6395 | 1.000000-1.000000 | 1.000000-1.000000 |
| stationary | 1.0000-1.0000 | 1.0000-1.0000 | 1.000000-1.000000 | 1.000000-1.000000 |
| psf-blur | 0.9990-0.9991 | 1.0008-1.0010 | 0.941098-0.941098 | 1.064129-1.064129 |
| psf-blue-blur | 1.0000-1.0000 | 1.0000-1.0000 | 0.941051-1.000000 | 1.000000-1.064078 |
| psf-fine-focus-offset | 1.0000-1.0000 | 1.0000-1.0000 | 0.998991-0.998991 | 0.995153-0.995153 |
| unequal-psf-blur | 0.5032-0.5528 | 1.0251-1.1839 | 0.976657-0.976657 | 1.102782-1.102782 |
| unequal-psf-fine-focus-offset | 0.6251-0.6394 | 0.6357-0.6530 | 0.999802-0.999802 | 0.993232-0.993232 |
| brightness | 1.0000-1.0000 | 1.0000-1.0000 | 1.000000-1.000000 | 1.000000-1.000000 |
| shift | 0.9999-0.9999 | 1.0005-1.0006 | 0.983302-0.983302 | 0.985837-0.985837 |
| clipped | 1.0000-1.0000 | 1.0000-1.0000 | 1.000000-1.000000 | -0.000627--0.000472 |

For equal latent structure with unequal variance, fixed-focus precision achieves0.602-0.640times equal risk and0.816-0.862times all-single risk, preserving clean transfer1.000000. Delivered-focus feedback lowers risk further on this fixture, but is a distinct arm; it cannot explain the fixed-focus improvement. Equal-noise stationary precision is effectively null, as expected.

The PSF adverse control remains adverse: equal-noise differential Gaussian blur leaves about5.89% attenuation against the sharper pass. With unequal noise, precision improves the sharper target but worsens the blurred target by2.5-18.4% relative to equal. The same mismatch is not eliminated by choosing the blurred pass as primary because primary currently applies on disagreement fallback, not every accepted mean. Clean unequal-PSF transfer is0.976657 against sharp and1.102782 against blurred. This is an appearance tradeoff, not a blanket quality improvement.

| Case | Precision/equal own-target risk with primaryA | Precision/equal own-target risk with primaryB |
| --- | --- | --- |
| unequal-variance | 0.6021-0.6395 | 0.6020-0.6395 |
| psf-blur | 0.9989-0.9991 | 1.0008-1.0010 |
| unequal-psf-blur | 0.5032-0.5529 | 1.0251-1.1838 |
| psf-fine-focus-offset | 1.0000-1.0000 | 1.0000-1.0000 |
| unequal-psf-fine-focus-offset | 0.6251-0.6394 | 0.6357-0.6529 |
| brightness | 1.0001-1.0001 | 0.9999-1.0000 |
| shift | 0.9996-0.9997 | 1.0004-1.0005 |

The20DN brightness difference is handled by actual primary fallback: clean primaryA/B mean error to its own target is below3e-7DN, while no-primary output lies10DN between states. This useful specific control does not override the PSF limitation. The clipped-source foil remains valid but its clipped pass is not an optical clean-truth target; retain the raw rows without interpreting its AC projection as fidelity.

## Boundary and next use

This establishes an existing operator capability with an oracle noise guide and fixed membership. It does not validate a real guide, new geometry proposals, global compatibility, RGB SNR, optical detail or a photograph. Shared noisy guides, geometry errors, photo appearance changes, and the actual membership selector still require their own evidence. Partial-guide Gaussian/pyramid-halo refusal is not exercised by this harness: all-false guide support and clipped original support are separate controls, and must not be mislabeled. Root's existing guide-support tests remain separate evidence.

Independent review checked the oracle gauge against NativeSampler's crop and the causal EqualObservation arm. Review requested own-target primary risks and retention of the PSF tradeoff; both are present. No threshold was changed and no adverse rows were dropped.
