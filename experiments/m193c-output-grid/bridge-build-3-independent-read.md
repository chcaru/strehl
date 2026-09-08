# M193c build3 — independent actual-record read

2026-09-07. **VERIFIED BY RECORD/FILE INSPECTION, NO BUILD OR TEST RERUN.**
The actual build3 records support the compiled-and-listed prerequisite.
This reviewer reopened the release, result, compiler/listing logs, both
executable files and bound current source/input bytes. No subject module,
test executable, image stage or RAW decoder was invoked, and no dependency
implementation source was read.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| bridge-build-release-3.json | 25342 | 459c65edb12d6ebd4ac5d74f7d4ca9b664592425dbf7428c92927bf4316ade52 |
| bridge-build-3/result.json | 51621 | bfb951c8ccc0b2278802e69c3ca27fd9138bb817457b365caaea31d5b82a2977 |
| bridge-build-3/compiler.log | 184893 | cc88f9ee15209c37f8d89215c340536fcdc0104fc4291a639bccfbe5cb4ad981 |
| bridge-build-3/test-list.log | 13769 | f8ae71f235181746a868f092f5490ade629a3ceb4d03ac50ebb239b7c922f3b0 |
| work/bridge-build-3-outer.json | 869 | 1dff1aaa5df2813b33739c1fdb9c1372001d18c01d39481e414db9b87a6f9582 |

The parent collected OS exit 0. Its retained outer observation records
26.6325101 seconds and the exact interpreter argv; this is an attributed
parent observation, not a second OS wait performed by this reviewer. The
211-byte console record reports `COMPLETE_COMPILED_TESTS_ONLY`, null error
and empty finalization errors, and the three-byte exit file contains
`0\r\n`. Their actual SHA256 values are respectively
`ed28e8f3b023613677e53dc871d882f7d2a73b29cf6464de2a850c39834ba519`
and `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354`.

The source/release checkpoint is
`43a72446c2c73718c285681170bdb3d4784afbb5`. The recorded original argv and
outer command match the released command after its sole self-release-SHA
substitution. It uses Python 3.12 with `-B -X utf8 -X faulthandler`, the
absolute build driver/release/output paths, and the external release hash
above. The actual compiler command is:

```text
cargo test -p strehl-cli --bin strehl --target-dir target/m193c-output-grid-build-3 --no-run --message-format=json-render-diagnostics
```

The terminal result has compiler exit 0, `rebuilt_cli=true`, null error and
empty finalization errors. All 119 recorded source bindings match their
recorded after-map and current file SHA256/lengths. The release contains
those same 119 entries plus the separately recorded 14682-byte build driver
(`e0ab57c437af32b61f8f8ed6d7cfb0407789974f6db40151c2f49f302edfa255`):
120 entries total. All 22 release input bindings and the six result
FileRefs checked here match actual files. A scoped Git comparison of all
released source/input paths against the checkpoint found no content diff.
The Git line-ending warning for the owned hook was not a source change.
This inspection did not re-execute the driver's include scanner; its
source-closure implementation was previously reviewed and the recorded
build ran it.

The added inputs explicitly include amendment3, its independent review,
the actual 14-control result and independent read, the build-drain source
review, and the retained build2 result. The actual controls4 result is
71176 bytes with SHA256
`6598085965a18d0165073a0ebcfcbdc44ed543008af64f569182965eddea8b80`.
The current 12664-byte process helper is bound at
`47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b`.
This keeps the drain repair and its prior process-only controls explicit;
it does not retroactively change private-campaign1's failed observation.

The actual compiler log contains `Compiling strehl-cli` and a terminal
finished-test-profile line. Exactly one own CLI test artifact message
matches the expected owned package, manifest, main source, binary target
`strehl`, `profile.test=true`, `fresh=false` and target3 executable path.
Both the compiler artifact and copied executable independently hash to
`fa03b12fe177608851d6758517c9bda050998cdc4d777195fab8e3dc1e0813a3`
at 29488640 bytes each. Their distinct recorded paths are:

- `target/m193c-output-grid-build-3/debug/deps/strehl-2cd1c0b56ad4ab1f.exe`
- `experiments/m193c-output-grid/bridge-build-3/output-grid-tests.exe`

Exactly one actual CLI `build-script-executed` message names the same
package and `STREHL_BUILD_ID=43a72446c2c7`. The result's recorded message
matches that log record, and `strehl 0.0.0 (43a72446c2c7)` agrees with the
compiler package version and build stamp. This checks the independently
obtained software context; no subject plan or TIFF supplied the stamp.
The source/executable hashes remain the binding evidence, without a claim
of a hermetic toolchain.

The actual copied-executable `--list` output contains each of the four
released names exactly once and no additional `m193c_` name:

1. `merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case`
2. `merge_cmd::production_truth::m193c_output_grid::precision_witness::m193c_private_precision_witness`
3. `merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private`
4. `merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native`

The compiler and listing observations each record exit 0, direct-child
exit and pipe EOF, null error, empty cleanup errors, terminal Job
accounting and zero active processes. Their commands and actual log
identities match the corresponding operations. For each, the ordinary
drain's first and last active counts are zero, it completes after one
observation, and `termination.attempted=false`. The absence of a forced
termination is read from that explicit field, not inferred from the
different `total_terminated_processes` counter. These two ordinary exits
do not replace controls4's delayed/persistent-descendant witnesses.

| Recorded observation | Compiler | Listing |
| --- | ---: | ---: |
| Job user + kernel CPU, seconds | 158.640625 | 0.015625 |
| Helper wall, seconds | 25.297 | 0.297 |
| Peak Job committed bytes | 5235146752 | 2252800 |
| Actual log bytes | 184893 | 13769 |
| CPU / wall limits, seconds | 1800 / 1800 | 30 / 30 |
| Committed-memory limit, bytes | 8589934592 | 1073741824 |
| Log limit, bytes | 67108864 | 1048576 |

Both actual observations remain below their original limits. The CPU
totals are terminal Job user-plus-kernel accounting, and memory is Job
committed memory, not RSS. The result's 26.344-second wall sample precedes
final publication; the parent's 26.6325101-second outer observation has a
different scope. None is a performance comparison or an image-stage
budget measurement.

**Disposition:** no blocking inconsistency was found in the actual build3
compiled/listed prerequisite. This result preserves the earlier compiler
and campaign failures as separate history. `--no-run` plus `--list` does
not execute the four tests: no private-grid controls, precision samples,
derivative controls, TIFF population or RAW outcome is admitted here.
Private-campaign2 still requires its fresh release and complete actual
producer/independent-reader evidence.
