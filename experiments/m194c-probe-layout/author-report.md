# M194c author implementation and checks

The scoped repair assigns the existing probe RNG sequence to consumed photosites
in active-relative row order. Storage origin, stride, unused padding and discarded
odd trailing sensels no longer choose which random draws land in the image. The
analysis Crop does not change this source sequence: the helper receives the full
quad geometry used by both production gather implementations.

This is a deterministic storage correction, not a new noise model or a quality
tuning. Parent owns the fixed M194b matrix comparison and final report.

## Source and implementation

M194b committed source is `444eb759be0358cda25e97d4375f977a039efe6a`. Product
edits began only after that commit was confirmed. Before editing, the old
`fill_noise` function was copied verbatim into `legacy-fill-noise.rs` and bound
by `legacy-source.json`; the original gatefloor.rs SHA-256 is
`15a332afba5c7dd5e4a8696dbc6541c7a925e97e6e63bdba9d55ff1f3584f63e`.

The product diff is confined to gatefloor.rs:

- `Probe::run` calls `fill_probe_noise` with `self.domain.full`.
- The new private helper validates frame storage using M194's existing check,
  iterates the first `2*full.height` active rows, and supplies only their first
  `2*full.width` active samples to the RNG.
- `fill_noise` accepts a mutable destination iterator. Its SplitMix64 seed,
  uniform draws, Box-Muller spare/order, mean/sigma, rounding and u16 clamp are
  unchanged. The RNG body matches the frozen old text after normalizing only
  the destination loop expression.
- Two separate cfg(test) includes attach author and independent controls.

Both current gather implementations consume complete quads; an odd active tail
does not become a new input to either gather. The helper leaves padding and tails
untouched. Packed even geometry at origin0, stride=active width, preserves the
entire old sequence exactly. Padded images are expected to change probe realization
and may change rendered bytes across versions. No cross-version byte promise or
new real RAW run is made here.

WB/path/levels metadata, probe amplitude, analytic variance denominator, luma mean
removal, pooling margin, certified band count, NaN policy, floor scaling and all
merge arithmetic remain unchanged. The destination iterator adds no full-frame
array; this is source inspection, not a resource measurement.

## Preregistration corrections and failures retained

The author preregistration and test design preceded the product edit. Independent
review corrected one proposed test before execution: a tiny valid scene cannot
produce the desired measured-band NaN under existing level-size guards. It gives
an empty beta. A measured level has two descendants of extent at least8, implying
its own extent at least29 and at least529 pooled samples, above the256 minimum.
The preregistration now labels direct helper/fault injection separately. No
valid-scene NaN is claimed.

The first fresh-target compile failed at the independent test's digest formatting:
sha2 0.11's output does not implement LowerHex. The independent author corrected
only byte-to-hex formatting. The full error, source bindings and failed receipt
remain in `author-run-1`; no product or author-test compile error was reported.

The independent verifier's first fallback power fixture was inert; its measured
result and subsequent prospective fixture correction belong to the independent
report. The earlier M194b layout failure also remains a failure of that version,
not a result retroactively labelled passing.

The first full CLI run on independent source30cd7c19 also failed the additive
checkerboard power assertion:135 passed, one failed, two ignored, with visible
compilation and retained `unit-tests.log`. Inspection then identified the direct
test harness omitting `FrameWorkspace::next_frame()`, while the production fold
does call it. Reusing cached frame0 planes invalidated the intended component
power experiment; the initially suspected stimulus explanation was not tested
on a correctly advanced workspace. A separate API correction is also needed:
raw NaN beta is not promised to mean white fallback by `BandMerge::beta_for`;
the production caller filters the finite prefix before supplying it. Neither
finding calls for a product traversal change. Revised independent evidence is
reported separately; this failed full-suite run is retained unchanged.

## Author controls

`python -X utf8 experiments/m194c-probe-layout/run-controls.py --output
experiments/m194c-probe-layout/author-run-2` visibly compiled strehl-cli and passed
all four author controls in each of two isolated gather processes. Source hashes
were unchanged across build and execution. Full raw logs and structured records
are in that directory.

The author controls test two non-square extents, four seed indices and four
storage/tail layouts against packed storage and the frozen old function. Exact
sequence identity, untouched poison, legacy failure under relocated storage,
seed sensitivity and low/high u16 clamping are all asserted. Invalid storage is
refused before a sample changes.

The actual production `Probe::measure` controls cover whole and offset Crop
domains, band depths1/3/5/7, identity and a nonlinear scale track, both gather
modes and changed seeds. Corresponding layouts have bit-identical beta. Tests
assert finite and empty normal cases actually occur, plus a labelled direct
pooling refusal. Seed and warp changes are live. These are software controls;
they cannot validate a camera calibration shared with a synthetic producer.

## Final check closure

Final product gatefloor.rs SHA-256 is
`bcea35986c73011c20d872bddc9c0ef3ea9354101259bd3952c16976bb1c9496`.
The API-corrected independent test source is72accd15; full hashes are in the
build receipts. `author-run-5` visibly compiled the final source, passed all four
author tests in each gather, checked unchanged source bindings and copied the
exact original Cargo artifact. Its build receipt SHA-256 is
`8a4876025f515569b12baec9370513a2bcae779a199ce83cd790f4710faa68c0`.

`unit-tests-final.log` records136 passed, zero failed, two ignored after visible
`Compiling strehl-cli`. The independent original omitted-reset test is retained
as an expected-failure tripwire, not a passing demonstration of fallback power.
The final independently run five-test suites and48 actual TIFF readouts are
recorded in `independent-run-4`, separately from author execution.

`format-check.json` confirms that new gatefloor lines need no formatting changes.
It explicitly lists the three inherited full-file formatting differences, which
are preserved rather than rewritten. Final test sources are rustfmt formatted.

`author-run-3` repeated the author controls successfully after the first
independent fixture amendment: four passed in each gather, source hashes stable.
`clippy-final.json` records exit0 with `Checking strehl-cli` and no warning in
the scoped product/test files. `tests-format.json` records both authored test
files passing rustfmt; the frozen legacy function retains its original text.

After the final API-only test correction, unforced Clippy runs exited0 but
printed the build-script `Compiling` line. To obtain unambiguous final checking
proof, the lint-only process used explicit stamp
`STREHL_BUILD_ID=m194c-lint-only-bcea35986c73`, bypassing the Git-index restamp
trigger. `clippy-stamped-1.log` contains `Checking strehl-cli`, exits0 and reports
no warning in the scoped product/test files. This diagnostic stamp was never
used for an image artifact. Earlier lint logs remain preserved. Existing
unrelated warnings remain; strict whole-workspace lint cleanliness is not claimed.

## Scope and remaining source-only note

Rules1/3/7 are addressed by u16 storage, unchanged injected noise physics and
consumed active-site traversal. Rules8/11/20/24 use retained commands, old-traversal
failure, independent choices and live seed/warp controls. Rule12's independent
verification is performed by another agent and its preregistration timing is
disclosed separately. The independent stats-flag comparison is inert on Pyramid;
it is not evidence of active observer nonperturbation. M194c adds no diagnostic
observer; the earlier active confidence control belongs to M194b's source lineage.
The parent owns the fixed quality matrix and its regression disposition. Rule33 is enforced
with visible compilation/checking and pinned original/copied artifacts. No
capture writes, peer process interventions, Git mutations, calibration changes,
quality tuning or SOTA claim are part of this repair.

Existing debug code in `Probe::measure` indexes beta[0] even when a tiny valid
probe can return an empty beta. This is a source-only follow-up, not an observed
failure in these runs, and is intentionally outside the traversal repair.
