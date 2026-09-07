# K=0 quality-target interface

Source/design preparation only. This narrow receipt does not admit production
quality. The model/controls are in `next-quality-reader-preregister.md`.

The target command writes `target.json` with exact keys
schema/status/ref_root/upstream_ref_root/fixture/float_commission/scalar/
geometry/method/controls/sources_before/sources_after/runtime/work/error/
finalization_errors/execution_release/invocation.

Schema is `m194g-quality-target-v1`, status
`COMPLETE_K0_TARGET_UNCOMMISSIONED` only after all target-stage work completes;
otherwise `UNCOMMISSIONED_QUALITY_TARGET`. Success has error null, empty
finalization_errors and unchanged source maps. `ref_root` is `target-parent`;
`upstream_ref_root` is `repository`. FileRefs have exactly path/sha256/bytes;
ArrayRef adds dtype/shape. Lengths/indices/dimensions are genuine integers,
hashes lowercase SHA256 and paths canonical contained POSIX-relative names.

Fixture and float_commission are repository-relative FileRefs to the exact
M194g fixture and genuine complete float authority. Scalar is the target-parent
relative `scalar.npy`, C-order NPY `<f8`, shape[240,320], all finite/nonnegative
expected electrons before CFA factors or quantization. Controls is a
target-parent relative FileRef to the completed local analytic/control result;
it is not the later independent target verification. No scalar copies or
independent values are substituted into the target array.

Geometry has exactly width320/height240/native_origin[0,0]/
cell`integer-centre-unit-square`/units`expected-electrons`/K0.0/
forward_similarity equal to the fixture's identity record. Method is
`m194g-k0-clipped-cell-v1`. The target uses the fixture's exact scene fields.
There is no target-specific fitted gain, phase, focus selection or amplitude.

Source maps use repository-relative names to sha256/bytes. Each bound source is
copied under `sources/<repository-relative-path>` inside the new target directory;
the copy must have the same bytes as the source binding. No executable source
is substituted from an unrecorded import location.

Runtime has exactly `python,numpy,scipy,thread_environment,executable,cwd`.
Version values and executable/cwd are strings. Thread environment has exactly
OMP_NUM_THREADS/OPENBLAS_NUM_THREADS/MKL_NUM_THREADS/NUMEXPR_NUM_THREADS, all
the string `2`, set before NumPy/SciPy import. Invocation has exactly
`orig_argv,argv,xoptions`; the first two are actual string lists and xoptions
is the actual interpreter option map. Execution_release is a repository FileRef
whose externally supplied hash is checked before helper imports. The release
schema is `m194g-quality-execution-release-v1`, exact fields
`schema,scope,source_bindings,inputs,commands`, scope `target`. Inputs are
repository FileRefs and commands are full orig_argv lists with the sole digest
placeholder `ACTUAL_EXECUTION_RELEASE_SHA256` replaced by the supplied digest.
The release includes this interface/preregister, fixture and full-float authority.
It does not authorize the later instruments or candidate scoring.

Work has exactly `stage,limits,cpu_seconds,wall_seconds,live_array_bytes,
output_bytes,tiff_decodes,target_cells,peak_live_array_bytes,tracked_scope`.
Stage is `target`; limits has exactly cpu_seconds120.0/wall_seconds240.0/
live_array_bytes33554432/output_bytes67108864/tiff_decodes128/target_cells76928.
Counters/byte values are nonnegative genuine integers; elapsed values are finite
nonnegative numbers. All stay within their limits, peak>=live. Tracked_scope is
`unique live backing ndarrays; not process RSS`. Target_cells counts76800 full
cells plus the actual local calls, at most128 additional; TIFF decodes is0.
Output bytes includes retained sources, controls, NPY and receipts. The work
receipt is the last recorded accounting point, followed by a final actual check
after its last successful write. It is not a process-exit timing measurement.

The controls child has exactly `schema,status,checks,error`, schema
`m194g-quality-target-controls-v1`; success status
`PASS_LOCAL_K0_CONTROLS_ONLY` and error null. Its16 ordered checks each have
exactly `id,passed,details`, genuine boolean passed=true, and details is a
finite JSON object. IDs are constant-full-foreground, constant-full-background,
constant-mixed, vertical-affine, oblique-affine, centre-mask-live,
separate-alpha-live, coupled-restored, fourier-zero, fourier-full-x,
fourier-negative-sinc, fourier-two-dimensional, translated-phase-live,
translated-phase-restored, nonfinite-refuses, empty-normal-refuses.
An incomplete child uses `UNCOMMISSIONED_LOCAL_K0_CONTROLS`, retains all started
rows and the original error. The external verifier checks this actual child;
these local controls cannot supply its independent ten-cell values.

These metadata cannot substitute for actual input/array checks.
The explicit external target path/hash is the independent verifier's
entry pin. It reopens this receipt, fixture, genuine float authority and scalar
with bounded same-buffer NPY header/dtype/shape/extent/hash checks. Its10 cells
are `(142,0),(142,1),(143,7),(150,53),(151,64),(152,64),(159,117),(160,117),
(169,179),(178,239)`, interpreted as native integer cell centres. It computes
its own analytic-x/y-quadrature values from the fixture. The comparison bars
are max0.004e and RMS0.0008e across all10 cells, with no omitted cell.

That separately source-bound verification result, not this producer's local
controls, is required by the later quality scorer. It must identify the exact
target receipt and array it checked. Root freezes its closed result/command
and the complete quality index association before38 output scoring. The
current interface grants no permission to execute a target or optical helper.
