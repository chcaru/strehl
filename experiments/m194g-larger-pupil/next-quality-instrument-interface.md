# Private quality readout and TIFF instrument interface

Source preparation only. The exact69-check command is
`independent-quality-instruments.py --release PATH --release-sha256 SHA --output NEWDIR`.
Its release uses `m194g-quality-execution-release-v1`, scope `instruments`,
with the same closed release/actual orig_argv/input/source rules as the target.
Required source closure is exactly this runner, independent-quality-io.py,
independent-quality-metrics.py, independent-rgb-tiff.py and the immutable
M194f independent-reader.py. Required input files are fixture.json,
next-quality-reader-preregister.md and next-rgb-tiff-reader-design.md.
This interface is also to be recorded as a release input before execution.

The result has exact keys schema/status/checks/sources_before/sources_after/
runtime/work/error/finalization_errors/execution_release/invocation/fixture/
artifacts. Schema is `m194g-quality-instruments-v1`; success status is
`PASS_QUALITY_INSTRUMENTS_ONLY`, with null error, empty finalization_errors,
identical nonempty source maps, and69 actual passing checks. Failures retain
the started check rows and use `UNCOMMISSIONED_QUALITY_STAGE`. Check rows have
exactly id/passed/details with unique string IDs, genuine boolean passed,
finite JSON details. This file is a test of readout/TIFF instruments, not a
candidate-quality result, complete matrix association check or target authority.

There are46 metric controls and23 TIFF controls. The first controls within
each surface's actual wave-fit population use a constant flat field. The
original registered masks/frequencies, amplitude/phase/extra-wave faults,
temporal offsets, sparse defects and legal/malformed TIFF choices are fixed
in the preregistration and literal source. Total actual TIFF entry calls is23
(22 larger-reader calls plus one frozen128-pixel rejection); target calls is0.
The69 count is asserted, never inferred from an absent exception.

Source maps, source snapshots, runtime, invocation and FileRefs follow the
target interface. Artifacts is the list of actual retained private TIFF
FileRefs, relative to this result's directory; fixture and release are
repository-relative. All private TIFFs are written through the same budgeted
store and rehashed before finalization. Work uses the same exact keys as the
target, stage `instruments`;120CPU/240wall,32MiB named live ndarray storage,
64MiB output,128 TIFF calls and76928 maximum target calls (actual0). No random
draw, optical integration or genuine output decode occurs in this command.

The upcoming matrix/plan/receipt association adapter has a separate private
commission and source freeze. It must run before candidate scoring and must
not inherit admission from this69-control result. Root will bind both actual
completed results in the final instrument authority consumed by the38 matrix.
No fixture-only receipt can replace either result.
