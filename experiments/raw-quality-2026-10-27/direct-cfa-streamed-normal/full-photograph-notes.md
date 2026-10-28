# Complete299-source worker

2026-10-27. **Source preparation, no author execution.** Root separately releases
and schedules the bounded run after the controls. `full-photograph.py` calls the
frozen paired measurement, source-grid bands, normal operator, fixed64 solver
and final reference-cell delivery. It adds input bindings, streaming loaders,
progress and output orchestration; it changes none of their arithmetic.

## Invocation and bound inputs

```text
python -B -X faulthandler experiments/raw-quality-2026-10-27/direct-cfa-streamed-normal/full-photograph.py --out <fresh-workspace-output> --renderer-binding <delivery-build-4/executable.json> --development-receipt <delivery-controls-2/output/held-development.json>
```

Root's wrapper supplies7200s wall,28800CPU-seconds,16GiB committed host memory
and8GiB CUDA allocation/reservation limits. The worker requests four CPU
workers/one interop worker, f32, no autocast/TF32 and a precise QPC clock.
Those are research observation limits, not competitive-speed acceptance.

The worker pins the complete native-u16 export receipt SHA057b50d7… and precise
geometry SHAa48f5970…, together with the held order/map and all producing
sources. It checks every one of the299 cache headers, byte counts and complete
SHA256 hashes before and after execution. Each file is original7032x4688 u16,
16-byte `[y0,x0,h,w]=[0,0,4688,7032]` header, row stride7032, physical RGGB origin
zero. The exact original filename/ordinal/SHA provenance must match the held
input order. Native source0/149/298 overlap verification and the native-only
four-column limitation remain in the bound export receipt.

No original ARW is opened for content or decoded here. Original file size and
mtime are checked against the export and again afterward. Original-byte
identity comes from the already verified export; the worker explicitly does
not claim a new ARW content rehash. Cache/source contents and metadata are
rehash-verified at the two boundaries, with no hidden mid-solve scans.

Every loader invocation creates a read-only memmap of only the requested
original-u16 cache. `prepare_source` copies that current observation to CUDA
f32 before any black subtraction. No list of299 open pixel arrays, source RGB
images or aligned frames is retained. Path/identity records and loader counters
remain small. Each pass visits original ordinal0..298 without a subset.

The global latent field is4743x7109 HWC, reference origin(-34,-22), held
reference149 and native map center(3516,2344). All299 literal affine f64 bit
patterns and the uncoerced reference transform are verified. No patch inverse
or separate tile gauge is introduced. Original profile gain/read variance are
reconstructed from the export's exact f32 bit fields; black512, white15360,
physical phase order and no-PRNU/no-private-noise semantics are checked.

## Telemetry without a recurrence change

A pass-through `ObservedProblem` subclass wraps only method boundaries. Every
numerical result comes from the unchanged `super()` method, exactly once.
`current_source` reports source preparation, `_adjoint` reports completed source
folds, `normal` reports its recurrence call number, `_rhs_pass` distinguishes
RHS construction, and `evaluate` distinguishes constant-only reference from
restored-final checks. The latter both occur where the frozen solver places
them, after the recurrence. There is no additional normal/residual/objective
calculation and no modified cap, direction, admission or mask.

JSON lines are appended to `telemetry.ndjson` and flushed to stdout with QPC
timestamps. Normal-call numbers are progress, not unreported true residuals.
Actual recursive history, final normal/objective diagnostics and convergence
status come from the saved frozen solver result. Constructor and final-audit
passes remain visible in its counters. The root wrapper records host load and
job memory independently. Lack of an immediate line is not a kill criterion;
only the prospective owned-job limits apply.

## Complete output even when numerically refused

After the fixed64 solve, both complete global X and correction z must be
finite and correctly shaped. The frozen result writes `fit/latent.f32le`,
`fit/correction-z.f32le` and `fit/result.json`, retaining its status/history.
`latent-metadata.json` binds geometry, original export, source count/order,
units, reference origin and numerical status. A finite refused result continues
to complete-image delivery; it is never relabeled converged and no earlier
baseline is substituted. Nonfinite or incomplete fields stop delivery.

After saving, recurrence/problem scratch is released. The same X is integrated
with the commissioned `ReferenceDelivery` over(68,46,6896,4596), producing the
complete signed black-subtracted camera-DN RGB master
`delivery/camera-rgb-dn.f32le` and its provenance/runtime receipt. This is the
actual reference-cell result, not a crop of interpolation coefficients.

The pinned build4 native renderer then receives that exact file/receipt and
the already commissioned development-bit receipt. Its metadata WB, matrix and
levels must also match the original export; tone and exposure come from the
held development receipt. It writes `native/rgb16-master.tiff` and its native
pixel-readback/ICC receipt, with no remosaic, MHC, retone or extra sharpening.
The renderer's final source SHA0e2ca203… supersedes the initial preparation
hash; root's completed build repairs and delivery controls bind that version.

The worker emits terminal `COMPLETE_DIRECT_CFA_FULL_PHOTOGRAPH` only after both
masters exist and all final input checks pass. It records `complete:true`,
`source_count:299`, actual `numeric_converged` (also its descriptive alias),
solver status, iteration count, operator/loader counters, complete dimensions,
QPC times and allocation peaks. `quality_claim`, `photographic_admission` and
production-speed acceptance remain false. It preserves the old generated
flat/noise failure regardless of numerical status.

This worker supplies complete TIFF/f32 masters and the native full pixel
readback. Root's subsequent independent presentation stage creates the
full-size display JPEG, overview and the same ten frozen384px witnesses, checks
the complete outputs, and compares with native CA-off and Helicon B4 in their
declared gauges. A finished TIFF alone does not establish improvement or finish
the user's cross-corpus quality objective.

On an exception, an incomplete receipt and existing finite artifacts/logs are
retained. No partial run is promoted to complete. Author checks are limited to
stdlib AST parsing and read-only interface/source review; no NumPy/Torch import,
CUDA compilation, cache pixel read, solver, renderer or RAW decode was run by
the author.
