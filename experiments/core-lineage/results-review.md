# Independent results review

**MEASURED decision: refuse photographic replay of this fixed rule.** The generated test completed successfully, but its recorded quality admission is false. No rerun, parameter change, or RAW execution was performed for this review.

## Evidence and useful coverage

The fresh build log contains `Compiling strehl-cli` and a completed release build. Root's exact test completed in 3.516 seconds, exit 0, one test passed, with peak job committed memory 395,698,176 bytes. I checked all 83 bound source hashes and the executable hash: no mismatch. Mechanical test completion is not quality admission.

Every through-focus scene has **zero active quads out of 18,125**: glint/depth step, its no-glint twin, true coloured radial detail, and crossed thin features. No track is eligible in these scenes. Flat also has zero activation. Consequently their candidate is exact fallback, with all reported RGB/chroma error ratios 1.0. Passing detail-preservation rows therefore provide no evidence that the proposed memberships preserve those details when active.

The required glint fan has baseline RGB RMSE 0.002749244 versus flat 0.001109891, so the scene contains the required error above the flat control. It fails the frozen 5% improvement and live-coverage requirements. The forced source-4 consumer is a useful destroyer: fan RMSE rises to 0.003888004 (about 1.414 times baseline), and core truth-template recovery falls to 0.0367–0.0400. Thus the image test can reject a harmful source choice; the automatic rule simply never supplies a useful choice here.

Only the same-focused-world, independent-noise scene activates: one track, 13 quads (about 0.072% of the output), with a three-cell persistent core. It passes the frozen nonregression bars; core RMSE changes only from 0.005034502 to 0.005031930. This is not useful through-focus recovery. Constant, colour-only, hot-site, clipped-core, and disabled cases retain exact fallback. The unequal-checker-subset arithmetic witness also passes, including fixed-input reversal and no support expansion.

## Reversal and limits of interpretation

Actual glint reversal has exact zero alpha and q in both orders. Candidate and baseline each change by the same maximum normalized RGB amount, 0.004320100. Per-original u16, gathered known4, guide, input variance, and energy hashes agree. Beta bits and resulting floors differ for original sources 0, 1, 3, and 4; the middle source 2 agrees. This is the anticipated changed-probe-input confound. The recorded reversal check is invalid for attributing a lineage-order defect, not a passed invariance test. Tolerances remain unchanged. The supplied-weight arithmetic reversal is valid but cannot substitute for an exercised image-level ordering test.

The glint case records 1,238 tracks, of which 1,237 are short. Its sole three-node track has no persistent core and is weak. Refusal reasons overlap: counts are not independent causes or ownership percentages. No glint track carries a clipping refusal, so the generated failure cannot be blamed on the real capture's clipping. All-track support contests are likewise not established as the cause: no track survives eligibility before contested cells are removed. The observations establish failure of this fixed topology/core/eligibility combination on the declared scenes; they do not isolate one threshold, prove that geometric tracking is impossible, or authorize relaxing safeguards. The sparse persistent-core definition and changing branch topology remain plausible limitations, not measured causal decompositions.

Preserve and close this candidate without a full photograph or threshold sweep. It has not demonstrated automatic support recovery, image-quality improvement, or a path to SOTA.

## Bound receipts

- Screen: `controls-1/output/screen.json`, SHA256 `e971fac5fd32836ae5d54d6c1bc38b60872b699f9172ae69ffddbebef238936d`.
- Process: `controls-1/process.json`, SHA256 `b63c336f47fd07267e4c94a354f6089edb8d20f739c090713dc1b47d0d0ac512`.
- Completion: `controls-1/completion.json`, SHA256 `17adfa94b5fdfe0d2b25ebdf5bd20991f1e499139c7a5c9d429b96eea469f049`.
- Bindings: `controls-1/bindings.json`, SHA256 `880b605caa7e0de0dbf6c0f18c1c1b5b98fd24d9eb041e6bf68358d877cb9d6d`.
- Executed binary: `build-1/cli-tests.exe`, SHA256 `619899300ad0846ac6fdae6ae4267876f88020b568142864b4786cf75eeffb2e`.
