# Independent green-phase screen review

2026-10-27. **ARGUED decision: the completed generated screen supports one bounded complete-weevil observational trial, subject to the separate full-source cost and baseline-identity checks.** It does not demonstrate a substantial quality improvement. The intended moderate diagonal gain is absent, low-frequency fidelity regresses, and existing glint streaks remain. Preserve these limits when judging the photograph; do not retune the generated screen.

## Integrity and display

**VERIFIED:** the executed binary hashes to `b1eb8fdc62c2a0ef3b0a6583db583c3cf2fc9b389ee3303896826bf0e5b16f45`. Screen SHA-256 is `03660b8acd0c9ad33bc4b1edccf14222a2d1929884597e47b86874214338b63d`. All56 complete generated float files (45 arm outputs, nine truths, two foils) match their recorded hashes. Current implementation, independent controls and inherited fixtures match build3's source manifest. The current full adapter differs from that manifest; this screen exercises the generated comparison path and does not validate subsequent full-adapter edits. Root confirms the intentional change repairs a full-size TIFF readback allocation limit after the first cost run, without changing reconstruction. A fresh build/screen/cost is being prepared; this report remains bound to build3/screen3.

[Invocation](../../../outputs/raw-quality-2026-10-26/green-phase-screen-3/invocation.json) records the exact command:

```powershell
outputs/raw-quality-2026-10-26/green-phase-build-3/cli-tests.exe merge_cmd::green_phase_guide::independent_controls::fixed_green_phase_actual_consumer_screen --ignored --exact --nocapture --test-threads=1
```

Two Rayon/pyramid workers, alignment/fullres enabled, GPU rounded gather, green probes, CA/defect/fine-support off. [Process receipt](../../../outputs/raw-quality-2026-10-26/green-phase-screen-3/process.json): exit0, one selected test,3.422s wall,400,125,952 bytes peak job commitment; no termination. These are operational observations, not a full-photograph benchmark.

I viewed all nine complete truth/canonical/matched-mean/candidate panels and the two complete thin foils at native290x250 per image. [Preview receipt](independent-previews-2/receipt.json) binds inputs and conversion. Unit gain, fixed sRGB transfer on diagnostic camera-RGB channels, display-only clipping0..1, no resizing or calibrated-color claim. The float masters retain out-of-display-range values. The initial converter stopped after one panel on a null optional field; only null handling was repaired, then all panels were staged in a fresh directory. No fit, RAW decode or measurement rerun occurred.

## Outcomes that matter

**MEASURED, known-truth generated fixtures only:**

| Case | Canonical RGB RMSE | Candidate RGB RMSE | Interpretation |
| --- | --- | --- | --- |
| Flat | 0.001127 | 0.001095 | Slightly lower than canonical; still above uniform0.000989. |
| Horizontal neutral | 0.004088 | 0.003674 | About10.1% lower error; reduces existing amplitude overshoot. |
| Moderate diagonal | 0.007308 | 0.007316 | Essentially unchanged/slightly worse; no intended diagonal benefit. |
| Low-frequency diagonal | 0.003779 | 0.004769 | About26.2% higher error; matched-mean is0.004086. |
| Thin far / near | 0.002504 /0.003188 | 0.002514 /0.003025 | Both depths retained; small far regression and near improvement. |
| Colored rays | 0.002692 | 0.002458 | About8.7% lower error; no erased ray. |
| Glint outside / adjacent | 0.011124 /0.015526 | 0.011141 /0.015529 | Essentially unchanged; colored streaks and surrounding error persist. |

The low-frequency recovery falls from approximately0.944–0.946 to0.927–0.929. This is a real regression despite passing the prospectively looser severe-loss guard; it is not catastrophic structure removal. The complete panels show largely similar outputs, with no convincing new moderate-diagonal detail. No aggregate score conceals this failure.

Cofocused color RGB error falls about1.2%, while green error rises about2.8%. Different-source color remains weak: red recovery0.571→0.589, blue0.426→0.418. The blue loss is small relative to canonical but about13% relative to matched-mean0.481. It must remain visible as a color tradeoff, not be described as universal color preservation. Unlike the previous RGB-guide screen, this run does not show severe additional loss of one recoverable color.

The [complete glint panel](independent-previews-2/clipped-glint-adjacent-detail.png) is especially important: all reconstructed arms retain conspicuous colored streaks absent from truth. Candidate outside-core green recovery is1.555 versus canonical1.563. Passing a relative guard does not repair this inherited defect or establish that the gathered-input hull is physically sound.

## Controls and decision limits

Canonical replay, one-source hull identity, immutable sources, shared four-plane routing, coarse fields, terminal mean and diagnostics placebo passed. The literal opposed-phase arithmetic kept energy16/floor4 versus mean-green energy0/floor1. This proves the intended operator is live, not that its extra energy represents useful photographic detail.

Wrong-source weights visibly weaken both thin components: far/near RGB errors rise about3.05/4.57 times the candidate and recovery falls to roughly0.66–0.72. The one-quad wrong-G2 foil is live but only slightly worse; it is not a strong phase-calibration discriminator. Near/far deletion and color/noise metric destroyers also pass their explicit checks.

All severe flags are false, but this is one ISO100 realization with synthetic known geometry. Four-band fine exponents are5.488/3.92; the complete seven-band path uses8/8. The full photograph may therefore behave differently. Nothing here calibrates optical blur, establishes SOTA, or warrants a default change. Given intact depths, no flat-noise blowup and no severe new color loss, one complete observational photograph is proportionate; require a visible benefit there to continue this direction. Bug2/flat transfer remains necessary if that photograph improves.

Complete evidence: [screen and all float-master paths](../../../outputs/raw-quality-2026-10-26/green-phase-screen-3/output/screen.json), [all preview panels](independent-previews-2/receipt.json), [moderate diagonal](independent-previews-2/diagonal-moderate.png), [low frequency](independent-previews-2/diagonal-low.png), [both depths](independent-previews-2/crossed-thin-depths.png), [thin foils](independent-previews-2/thin-foils.png), [different-source color](independent-previews-2/different-source-colour-adverse.png).

## Build4 replay and full-size cost release

**VERIFIED independent comparison:** all56 complete float payloads from [screen4](../../../outputs/raw-quality-2026-10-26/green-phase-screen-4/output/screen.json) are byte-for-byte equal to screen3, with both sets also matching their recorded hashes. Every scientific JSON value is identical after normalizing only output path basenames and removing per-probe `seconds`; metrics, flags, source hashes, output hashes, coefficients and exponents remain in the comparison. The existing complete previews therefore also represent screen4. [Replay receipt](build4-replay-review.json) records the comparison and manifest difference.

Build3/build4 source manifests differ in exactly `full-adapter.rs`: `7168dbde1e3fd5df9b70e2ecf9edf8849de6dc73074a309c5f86a9ca1bcc76c9` → `0499fbff388117e1c9ab64be076de45bddc1e7a4f5516952cb7d6980186f328d`. Reversing only the explicit TIFF decoding-buffer limit block in memory reproduces the entire old-file hash exactly. Thus the change is restricted to bounded float-image readback; no estimator or reconstruction edit is concealed in that difference. Build4 executable binding is `d89b20091cd425ea546da3234657ed3c99de85781cc4d0cdad19132c68ec67f6`; screen4 hash is `08c552fcff5c504b0f4bad4b31cfa71742c1b859ebcd3b45d35cd665540a1047`.

**VERIFIED receipt review:** [cost2](../../../outputs/raw-quality-2026-10-26/green-phase-cost-job-2/output/cost.json) reports `SOURCE149_COST_COMPLETE`, exit0 and terminal owned-job accounting. Actual source149 plus16 propagated-noise draws completes in8.008s; total job wall time including full output writing/readback is15.031s. Peak job committed memory is6,567,747,584 bytes. All three complete one-source CFA payloads have the same recorded hash, as do their decoded RGB16 and RGB32 pixels. Coarse fields and terminal mean remain exact. I inspected these receipts; I did not reread/decode the multi-gigabyte cost images or RAW original.

Processed source149 content and all299 source metadata remain unchanged. This cost run explicitly did **not** reread all299 source contents. Its one-source identity is the actual-gather hull identity, not proof that the complete299 canonical reconstruction reproduces the previous photograph. That stronger check remains inside the full adapter and must pass before photographic attribution.

**ARGUED final release:** no remaining screen or cost blocker was found for one complete299-source observational run. The2475s (about41.3min) estimate is an extrapolation from one source, not a measured full-stack time or a competitive-speed claim. It is a costly research candidate with modest generated evidence; do not repeat this expenditure without a useful complete-photograph result. Keep the low-frequency regression and unresolved glint artifacts prominent. Release is for this observation only; no quality, optical-calibration or product-default claim follows. Root alone schedules the run.
