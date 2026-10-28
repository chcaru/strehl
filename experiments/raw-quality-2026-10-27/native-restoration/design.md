# Native CFA contrast hypothesis: author checkpoint

2026-10-27. DERIVED / SOURCE-REVIEWED only. No numerical execution, RAW read or build. The first proposed filter below is rejected before execution. No photographic improvement is claimed.

## Existing path and evidence boundary

Read `restore.rs`, the actual `write_merged_observed` restoration branch, M115-deconv-headroom, BUILD-SHARP's corrections, and M70's corrected introduction. M115 demonstrates old ringing/noise costs and an SNR null on its tested captures; BUILD-SHARP withdraws its optical attribution. Neither establishes a ceiling for this capture. M70's depth-mixture limitations remain relevant to any assumed global blur.

The current native gather performs full-resolution MHC, channel sampling, then remosaicing. The compact four CFA planes have two-native-pixel pitch, but that is not the current interpolation lattice. `RestorePlan::config(grid_factor=1)` and the old half-plane Catmull magnitude therefore do not identify this composite transfer. Changing that factor cannot remove color coupling, phase dependence or merge nonlinearity. The existing writer restores four already WB-normalized planes independently and uses a single-frame model variance at their mean. Its assertion that this overstates merged noise is not established after the current negative-tap gather/selection.

## Exact first proposal and rejection

For each signed black-subtracted phase plane, let `B` be the separable binomial kernel `[1,2,1]/4`, with taps two native pixels apart and reflected boundaries. Proposed one-pass correction:

```text
q = B x - B(B x)
x_candidate = x + 2 q
```

The same scalar, kernel and support apply to R, G1, G2 and B. No source election, per-color gate, resampling or optical PSF claim is involved. The interior transfer is `1 + 2 H(1-H)` with `H=cos^2(wx/2) cos^2(wy/2)` and therefore lies in `[1,1.5]`; DC and the CFA-lattice Nyquist are unchanged. The proposal used iteration/gain truncation as regularization. Amount zero would have been a literal copy, and amount eight a live excessive-correction foil.

This frequency bound is insufficient. For an edge constant in y, `B-B^2=[-1/16,0,1/8,0,-1/16]`. The proposed filter becomes `1.25*x[j] - .125*x[j-2] - .125*x[j+2]`, where j indexes same-color samples. A clean step acquires 12.5% undershoot/overshoot extending four native pixels. The independent reviewer found the same counterexample. This is a decisive sharp-step mismatch against the halo priority, so do not build or run this exact recipe.

A local support limiter is a changed nonlinear hypothesis, not a repair that makes this recipe pass. Even enforcing original per-phase local ranges does not prove absence of broad halos, and a common four-phase limiting gain can suppress independent colored structures.

## Root-frozen changed hypothesis

After the analytic rejection and before any execution, root authorized exactly:

```text
d = 2 * (B*x - B(B*x))
x_candidate = x + clamp(d, min3x3(x)-x, max3x3(x)-x)
```

Here the extrema are over the original same-phase 3x3 neighborhood, including the center, at two-native-pixel spacing. Each phase receives the identical operator independently at its actual physical CFA sites. There is no common-quad gain, cross-color election, noise threshold or parameter sweep. Reflected borders do not repeat the endpoint (`-1 -> 1`, `n -> n-2`). A final clamp to the same extrema only prevents the f32 addition from rounding just outside the stated support; nonfinite filter/correction intermediates fail closed before this cap can hide them. Signed values survive until the ordinary writer's existing normalization. Off is a literal copy; Unbounded retains the rejected amount-two formula as a commissioned adverse control only.

This nonlinear operation has no claimed global MTF bound. It preserves a sharp step in CFA space but can still change smooth shoulders, fine structures, mean/color relationships and final-MHC halos. The local range is an explicit algorithm choice, not a metric that certifies quality. The independent fixed screen checks noisy/colored constants first, clean and independently blurred steps, close lines, glints and independent color components through the actual MHC. Its known failures remain visible even if root separately runs a finite complete-image diagnostic. No synthetic result admits photographic improvement.

Implementation is in `implementation.rs`, and `writer-adapter.rs` replays the bound complete masters. Tests are `native_restoration::generated_controls`, `::replay_weevil`, and `::replay_flat`; all are ignored and root-scheduled. Strict `STREHL_NATIVE_RESTORATION_CONFIG` has only `schema:1`, fresh absolute `out_dir`, and `expected_test_executable_sha256`. Four CPU workers process one phase at a time; no GPU/RAW/gather job is required. Workspace is a few full-image f32 buffers, bounded below the root's 6 GiB job allocation by source reasoning, not measurement. Runtime is unmeasured.

## Noise and replay contract for a later root-selected correction

Use the one sidecar profile in DN units: gain 0.22893773 DN/e and read noise 4.2 e on each phase, black 512 and white 15360, ISO100, no PRNU. Evaluate its variance only as a single-frame reference; do not divide by299, infer an effective stack count, or describe it as a merged upper bound. For any fixed linear kernel L, `sum(L_i^2 variance_i)` is an independent-sample reference calculation, not the unknown actual postmerge covariance. A numerical noise control cannot by itself admit photographic utility.

The replay implementation boundary remains concrete and inexpensive: load the bound saved signed CFA master; split the RGGB phases without a second crop; apply exactly one root-selected correction; interleave; apply the ordinary writer's `max(0)*WB*exposure/range` expression in its existing order; and invoke `write_demosaiced_with_master` once with the original matrix and exact DisplayBaseline. Reuse the proven `green-phase-guide/full-adapter.rs` helpers rather than the old Wiener implementation. The no-op arm must reproduce the retained RGB16 and float pixel payloads, ICC and material metadata before the candidate is written/scored. Existing provenance Software may identify the new build honestly.

The original weevil input is the complete CA-off sensor master, 6896x4596 with reference-active origin[68,46]. It already contains its crop and CA choice. No RAW decode, warp, CA application, second crop, RGB source volume or retone belongs in this replay. Preserve complete sensor, RGB16 and linear candidate outputs and the unchanged baseline. The flat arm uses the bound `reconstruction-photo-full-1/output/baseline-sensor.f32le`, 6932x4620 with origin[50,34], its saved CA-on state and exact tone. Input hashes/stat checks cover the four retained sensor/sidecar/RGB/linear files per arm; they do not claim a fresh census of original camera files. Source counts describe saved-master lineage. Root owns registration and execution.
