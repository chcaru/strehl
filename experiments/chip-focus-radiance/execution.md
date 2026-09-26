# Native observation execution record

Root execution, 2026-09-25. The source and decision checkpoint is
26ee776ac82bd1fd858c0cd833807a8717993ab1; the new experiment-only Rust files
and CLI includes are bound individually in each build receipt. No production
default changes. All commands use the installed Python3.12 with
`-I -B -X faulthandler`, from the repository root.

`run.py build --out experiments/chip-focus-radiance/build-1` failed in18.828s
with one E0689 error in an independent control's floating literal before
`.powi(2)`. The reviewer annotated0.41 asf64; no formula, stimulus or criterion
changed. No generated tests or RAW photographs ran on build1. Its complete
failure log and process record are retained.

Before build2, independent runner review identified two validation omissions:
the full route had not rebound the four completed control JSONs/process, and
cache validation lacked semantic arm/crop/reference/map/tone checks. Those
checks were added directly, along with explicit absence of a refused candidate
CFA blob. The reviewer re-read the changes and found those gaps closed. No
supplemental verifier or new framework was created. These are pre-execution
instrument repairs, not rescues of image results.

`run.py build --out experiments/chip-focus-radiance/build-2` is the fresh build
for the unchanged operator and corrected controls. Subsequent measurements
must cite their completed job receipts; this paragraph alone claims none.

Build2 completed187.875s with fresh `Compiling strehl-cli`. The command
`run.py controls --build experiments/chip-focus-radiance/build-2 --out
experiments/chip-focus-radiance/controls-1` finished0.359s with three tests
passing and the address destroyer failing. Its first original point has exact
cancellation: the missing-factor formula and correct mapping both give0.45.
The original second point distinguishes them,0.585 versus0.72. The reviewer
repairs the detector to check both already-fixed points, records the first
degeneracy explicitly and retains the0.01 separation requirement at at least
one point. The operator author independently checked that repair. No operator,
coordinate fixture, bandwidth, source population or image-quality bar changed.
No original RAW was read. All three completed control records remain intact.

Build3 is required for the repaired control; the old test binary is not treated
as if it contains the new test. Runtime/quality claims await completed receipts.
