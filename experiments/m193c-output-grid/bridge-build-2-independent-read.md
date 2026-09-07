# M193c build2 — independent actual-record read

2026-09-07. **VERIFIED BY RECORD/FILE INSPECTION, NO BUILD RERUN.** The
parent reports collecting actual build-controller exit 0 after about
27.30 seconds. That original OS wait is attributed to the parent. This
reviewer reopened the actual release/result, compiler and listing logs,
current bound source/input bytes and both executable files, without
launching either executable or reading any dependency implementation.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| bridge-build-release-2.json | 24151 | a3a7bd014e654026224f86f6fa733a76f3c806bf20c2d55d6aaff2a3d06b96cd |
| bridge-build-2/result.json | 48887 | 05154982aefcab418427c5311fb27ea499a42f1a1c6e9f714d9c46cb8e45c907 |
| bridge-build-2/compiler.log | 184893 | 92ccce5d3e3c1452f544ecb04a253204c6137f3a576202613781205a51558046 |
| bridge-build-2/test-list.log | 13769 | f8ae71f235181746a868f092f5490ade629a3ceb4d03ac50ebb239b7c922f3b0 |

The source/repair and fresh release were committed at `7b861935` before
this build. The actual original interpreter argv equals the release's
command after its single self-release-hash substitution. The actual Cargo
command uses `target/m193c-output-grid-build-2`, with `--no-run` and visible
compiler diagnostics. It does not reuse the failed build1 target.

The terminal result is `COMPLETE_COMPILED_TESTS_ONLY`, compiler exit 0,
`rebuilt_cli=true`, null error and empty finalization errors. All 119
recorded source bindings match current file SHA256/lengths and the recorded
after-map. The release has those same 119 bindings plus the separately
bound build driver: 120 total, not a contradictory source population.
Fieldwise SHA/length comparison matches all of them. All sixteen released
inputs and the driver, executable, listing, compiler-log and release refs
also match their actual bytes. These checks did not execute the build
driver's source enumerator again; its exact include scan was source-reviewed
and executed by the recorded build.

The compiler log visibly contains `Compiling strehl-cli`. Its actual test
artifact has `fresh=false`, the expected package/manifest/main path,
binary target `strehl` and `profile.test=true`. The original compiler
artifact and copied file are each 29488640 bytes and independently hash to
`8ecf5dfbb9270eef5ab99a9306bd1edb8cd0180e6128e86ad1bb18420b09b0e1`.
Their recorded paths are respectively:

- `target/m193c-output-grid-build-2/debug/deps/strehl-2cd1c0b56ad4ab1f.exe`
- `experiments/m193c-output-grid/bridge-build-2/output-grid-tests.exe`

The actual CLI build-script message occurs once for the expected package
and contains `STREHL_BUILD_ID=7b8619351f74`. The stored software context
`strehl 0.0.0 (7b8619351f74)` agrees with that message and the previously
reviewed owned software-string expression. It was not learned from a
subject image plan. Source/executable hashes remain the binding authority;
this is not a hermetic-toolchain or universal TIFF-stamp claim.

The actual copied-executable listing contains each of these four names
exactly once and no extra `m193c_` test names:

1. `merge_cmd::production_truth::m193c_output_grid::m193c_private_output_case`
2. `merge_cmd::production_truth::m193c_output_grid::precision_witness::m193c_private_precision_witness`
3. `merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_native`
4. `merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private`

Both compiler and listing observations have actual exit 0, terminal Job
accounting, zero active processes, null error and empty cleanup errors.
Their actual argv/log references match the declared compiler/listing
operations. The compiler used 1682968750 100-ns CPU ticks, a 26.234-second
helper wall observation and peak Job committed memory 5203607552 bytes;
these are below its 1800 CPU/wall-second and 8 GiB build limits. Listing
used 156250 CPU ticks, about 0.313 seconds and 2256896 peak committed bytes,
below its separate 30-second / 1 GiB limits. Log extents match actual bytes
and stay below their respective 64 MiB and 1 MiB caps. The result's
27.297-second wall field is a build-controller sample before its final
publication, not a more precise independent process-exit timer.

**Disposition:** the actual build2 result supports the source-bound compiled
and listed-test prerequisite. Build1 remains an uncommissioned compiler
failure; its record is not overwritten or pooled into this result. Listing
does not execute any of the four tests, so no private control, precision,
product TIFF, derivative or native RAW outcome is admitted here. The
encompassing private campaign and its independent readers still require
their frozen source/command release and actual complete results.
