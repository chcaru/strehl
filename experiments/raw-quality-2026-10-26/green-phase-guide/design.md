# Fixed green-phase evidence at the ordinary finest two bands

**SOURCE-PREPARED / UNVERIFIED numerically.** Root owns builds and execution. This is one candidate, with complete-photo admission decided separately. The refused bristle transfer model supplies no blur estimate motivating it.

`implementation.rs` retains the actual gathered G1 and G2 planes through the ordinary Laplacian operator. For bands0 and1 only, it computes `E=0.5*(energy(L_G1)+energy(L_G2))` and `V=0.5*(V_G1+V_G2)`, then passes `E` and `gate*V` to the existing `fields_from_energy`. One resulting field enters one four-plane `add_fields` call. The canonical coarse energy, floor and weights are copied and checked bit-for-bit; base, input hull, mean fallback, original coefficient pyramids and MHC are unchanged. No independent R/B decision or phase-specific reconstruction weight is introduced.

The mean-green comparator uses the same16 source-space draws and actual gather, but computes ordinary Laplacian energy after `0.5*(G1+G2)`. G1/G2 are spatial samples, not independent repeats. Their covariance is retained in the mean-green probe; averaging their separate expected energies needs no independence assumption. No variance is inferred from their signal difference. The estimator reuses the injected model, content-derived seeds, `noisy_source`, actual rounded GPU gather and eight-pair `NoiseEnergy`. Its triple slots now mean G1/mean-G/G2. Only `sizes[..3]` is needed to compute the first two ordinary AC bands; unnecessary coarse guide/probe storage is omitted.

In exact linear arithmetic, separate-phase energy adds a quarter of the energy of the Laplacian phase difference to mean-green energy, with its corresponding noise price. This is an algebraic hypothesis about focus evidence, not proof of photographed cancellation or extra recoverable resolution. Finite probes, phase-dependent texture and the unchanged selector may still worsen noise or source admission.

## Difference from rejected work

[Native-green-cue](../../native-green-cue/design.md) substituted a special original-green difference high-pass cue, transported its energy before the consumer and replaced band0. Its [actual result](../../native-green-cue/results.md) lost noisy mixed and low-frequency fidelity despite high-frequency headroom. This experiment retains the ordinary Laplacian bands and current gathered grid. It does not resurrect that high-pass filter or interpret G1-G2 as a private noise estimator. The rejected [insect-color](../insect-color/independent-results.md) combined R/mean-G/B SNR and lost a true different-source blue component; this candidate uses only green evidence and keeps one shared four-plane decision. The failed full wavelet photograph remains a warning that different sampling evidence alone does not establish image quality.

## Generated API and control ownership

The independent reviewer owns `independent-controls.rs` and its plan. `compare_generated(...)` preserves the previous comparison shape: canonical, exact canonical replay, matched_green, joint (this phase-energy candidate), and uniform. It allows1..16 generated sources. `compare_generated_with_foil(...)` additionally accepts `GuideFoil::None`, `NextSource`, or `ShiftG2OneQuad`. The latter deliberately shifts only guide/probe G2 by one quad with row wrap; original reconstruction planes and canonical coarse fields remain unchanged. Merely exchanging G1/G2 cannot destroy their symmetric mean and is not used as a foil.

Diagnostic receipts record original/known-plane hashes,16 seeds, fine variance fields, per-band energy/floor/weight hashes, coarse exactness, and one shared field for four planes. Disabling diagnostics changes no estimator calculation. The generated screen uses four bands with exponent ladder `[5.488,3.92,2.8,2]`; complete photos use seven bands `[8,8,7.6832,5.488,3.92,2.8,2]`. The tiny screen does not validate the full fine-band exponent behavior.

## Complete source route, ready before admission

`full-adapter.rs` provides separate ignored tests:

- `merge_cmd::green_phase_guide::full::weevil_source149_full_cost`
- `merge_cmd::green_phase_guide::full::weevil299_complete_observation`

Both explicitly require CA-off, actual rounded direct-plane GPU gather, the same injected profile, four execution threads, complete6896x4596 crop and frozen299-source order/map. The cost test decodes only source149; the complete test decodes each original sequentially and retains no aligned-frame volume. The complete fold reuses the actual canonical chunk planner and left-to-right absorb helper, requiring75/75/75/74 source chunks. It prepares baseline, matched-mean and phase-energy complete CFA float captures, RGB16 masters and linear RGB32 masters, all with the exact fixed display baseline read from the held CA-off linear TIFF metadata. It does not choose separate automatic tone per arm.

One-source outputs must equal the actual gathered source under the existing input hull, and all three delivered outputs must agree. Complete baseline signed-CFA payload, decoded RGB16 pixels and decoded linear RGB32 pixels must equal the existing CA-off observer/master; a changed GPU/direct-plane route is not assumed equivalent merely because prior fixtures passed. Failure preserves files and an identity receipt but blocks comparison admission. The original full TIFF and sidecar hashes bind the saved CFA payload hash, avoiding a generic decoder's unsupported CFA photometric interpretation. All299 original names/statistics are checked in both tests; the cost test rereads original149 content before/after, while the full test rereads all299 contents before/after. Frozen executable, map, order and baseline identities are also checked.

Config pointed to by `STREHL_GREEN_PHASE_GUIDE_CONFIG` has exactly:

```json
{
  "schema": 1,
  "out_dir": "C:/Users/chris/.codex/worktrees/raw-quality-october26/strehl/outputs/raw-quality-2026-10-26/<fresh-run>",
  "baseline_linear_sha256": "8f3d9ec977f06d8fd44e070f27ab97e398611436cef17271fa6b889067ea1960",
  "expected_test_executable_sha256": "<root-frozen-test-executable-sha256>"
}
```

Required execution environment includes `STREHL_FIX_CA=off`, `STREHL_FULLRES_GATHER=1`, `STREHL_DIRECT_PLANES=rounded`, `STREHL_GPU_GATHER=on`, `RAYON_NUM_THREADS=4`, `STREHL_PYRAMID_WORKERS=4`; keep the root runner's cleared competing controls, defect/temporal/spatial treatment off, gatefloor enabled and Malvar default. Root registers one test-only `green_phase_guide` include of `implementation.rs`, guarded by native-direct-planes/native-correction-variance/native-gpu-gather; the implementation includes the independent controls and full adapter. Build and runtime receipts, not this document, establish resolved flags.

**DERIVED cost limit:**16 noisy source gathers per original means4,784 probe gathers for299 frames, plus canonical processing. Fine-only guides reduce pyramid work but not this gather count. The cost receipt reports first decode, processing, finish and299-source projection; root must review actual speed before dispatch. Three arms with retained plus scratch accumulators can reach six `BandMerge` instances after the first chunk, roughly3.8GB of accumulator arrays at this geometry before workspaces, probes, source storage and GPU scratch. One-source cost can understate that later peak. Budget the complete run explicitly; no practical-memory or speed claim is established by source preparation.

Only `rustfmt --edition 2024 --config skip_children=true` has parsed the producer sources, exit0. No child build, RAW read, numerical fit or photographic execution occurred. Complete masters, identical display, the frozen ten photographic guards and independent whole-image comparison remain required; a generated benefit or cost pass is not promotion.
