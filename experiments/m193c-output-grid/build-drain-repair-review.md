# M193c source review of the build3 preparation

**SOURCE-REVIEWED ONLY.** This review does not execute the preparation script,
import the build/controller modules, run a process control, compile code, or
produce/read image pixels. The prospective build remains build-only. Actual
controller4 completion and independent readback are prerequisites, not assumed
results. Root will separately freeze the generated release and its exact command.

**Final disposition: source-ready, conditional on actual controller4 admission.**
The final preparation source identified below closes the initial findings. This
does not claim that the preparation script, controller4 or build3 has run.

## Build driver delta

`bridge-build.py` is 14,682 bytes, SHA256
`e0ab57c437af32b61f8f8ed6d7cfb0407789974f6db40151c2f49f302edfa255`.
The scoped source diff against the released build2 driver contains exactly two
replacements: `target/m193c-output-grid-build-2` becomes
`target/m193c-output-grid-build-3` in the exact cargo command assertion and in
the fresh-target assertion. There are no other driver changes in that diff.

The retained previous driver is SHA256
`f7690d009893698b6d9756d971ff0f3989e44a996b13fe5bd0d535add1cc29c7`.
The build2 release is 24,151 bytes, SHA256
`a3a7bd014e654026224f86f6fa733a76f3c806bf20c2d55d6aaff2a3d06b96cd`.
It contains 119 closure sources plus the driver and 16 historical inputs. A
read-only hash comparison during this review found changes in that 120-entry
map only for `bounded-process.py` and `bridge-build.py`. No Rust compiler input
was changed as part of this drain repair.

The actual build controller still discovers the tracked crate/workspace inputs
and explicit external Rust include forms, including the registered
`include_bytes!`/`include_str!` forms, before comparing its exact map with the
released map. This remains a scoped source collector, not a universal Rust
parser. It still requires a fresh output directory, fresh target directory,
visible rebuild evidence, the actual compiler artifact, identical original and
copied executable bytes, and the exact test listing. Nothing in the target
suffix change executes the four tests or admits a private image stage.

## Initial preparation source and findings

The first reviewed `work/prepare-build-3.py` is 2,651 bytes, SHA256
`000bef78414cb4b60ce95bd332da359313235e54acd1be5771c0b759709dc51a`.
It reads the build2 release, refreshes its source hashes, appends the amendment3,
review and actual controller4 dependencies, changes the two command suffixes,
checks historical inputs, and prepares the new release/archive list.

One concrete prerequisite gap was sent to root before preparation execution:
the initial script checks the PASS status and 14 true row booleans but only loops
over `control.sources_after`. An empty map or a mismatch with `sources_before`
could therefore pass this preparation condition. The required repair is the
actual controller schema, exact four registered source names, before/after
equality and actual current binding equality. Those four sources are
`controller-controls.py`, `controller-child.py`, `bounded-process.py`, and the
owned `experiments/m12-scorecard/m12-harness.py`.

Related bounded checks were proposed during the same review:

- Require the literal ordered 14 modes and indices rather than allowing any
  fourteen records with true booleans. This preserves the original eleven and
  requires the distinct finish/persistent/restored drain population.
- Preserve an explicit source refresh allowlist for the helper and driver, so
  an unrelated modified compiler input cannot silently become part of this
  narrowly reviewed release. The real build's exact source-set assertion remains
  necessary even when this preparation check passes.
- Form the controller4 FileRef and parse its actual result from the same bytes.
  The initial ref/separate-parse/final-rehash sequence unnecessarily separates
  the prerequisite value from the bytes admitted as the release input.
- Require the fresh build3 output directory as well as its fresh target and
  release file. The existing build controller already fails closed if the output
  exists; the preparation check simply catches that before publishing a release.

These are preparation/interface checks, not new numerical criteria or an extra
image population. Actual control4 launch/exit/log authority remains the subject
of its independent result read and the root-frozen input set; a JSON PASS label
is not itself an observed process result.

## Scope retained

Historical build1/build2 records, process controls and the failed private1
attempt must retain their original hashes and meanings. New control4 evidence
does not retroactively replace the helper used by those runs. The later build3
must bind the amended helper to its own new source revision. It must not inherit
build2's source authority while reading different process-helper bytes.

The build command remains `cargo test -p strehl-cli --bin strehl --target-dir
target/m193c-output-grid-build-3 --no-run --message-format=json-render-diagnostics`.
The interpreter command keeps the established arguments and actual release-SHA
substitution, changing only the intended build/release output suffixes. No image,
coordinate, CFA, noise, precision, quality, or calibration bar is altered.

At the first source read, controller4's actual result and independent review
were future dependencies. Their absence was not a measured failure. No
preparation execution or build pass is claimed here.

## Final preparation reread

The held replacement `work/prepare-build-3.py` is **4,152 bytes**, SHA256
`a417e142e1a365db7fc91e452d34bb08665ada07ae37edabcdcde5e2ace093c4`.
The build driver remains the 14,682-byte `e0ab57c4…` source above. This reviewer
read the actual replacement source and independently rehashed it, without
executing it or importing any subject module.

The preparer now requires that the changed source paths are exactly the helper
and build driver; every other historical source remains fixed. It requires the
actual `m193c-controller-controls-v1` schema, successful terminal status, exact
ordered fourteen modes, exact integer row indices, every passed flag genuinely
true, terminal Job accounting and zero active processes. It rejects errors or
secondary finalization errors. The exact four source keys must occur in both
equal before/after maps, and each binding must match the current file.

The parsed controller value now comes from the same `control_bytes` whose
SHA256/length is explicitly compared with the new release input FileRef. The
later complete input rehash remains in place. Fresh release, output and target
paths are all required before publication. The six appended inputs are the
amendment, actual `independent-controller-amendment-3-review.md`, actual control4
result, its independent read, this build source review and the retained build2
result. The sixteen original inputs are retained and rechecked; their values
are not regenerated to conceal changes. The release/archive preparation does
not itself run the controller or compiler.

No additional source blocker was found in this bounded reread. **Do not execute
this preparation until the actual control4 result and its independently written
read exist and pass.** Root must still inspect and commit the generated release
before the exact fresh build3 command runs. The actual controller OS exit/log
and control outcomes are not proven by these source assertions; their upcoming
independent read supplies that evidence. No scientific criterion changes or
additional image populations are introduced.
