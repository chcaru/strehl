# First-control failure: test workspace cache lifecycle

MEASURED: build1 freshly compiled core and CLI (148.515s child wall). The first
control job exited101 after0.297s: geometry passed, but the all-ones image/clamp
assertion failed. No photograph was run. Failed receipts remain in controls-1.

Root isolated the original fixture against the same compiled core rlib with a
small Rust executable. The first direct link failed because the release rlib
contains LTO objects; adding `-C lto=thin` compiled successfully. This is a
diagnostic, not a replacement for a fresh final CLI build and full controls.

```
rustc --edition=2021 -O -C lto=thin experiments/donor-consistency/controls-1/diagnose.rs --extern strehl_core=target/native-pyramid-profile/release/deps/libstrehl_core-60ead7b714ba5262.rlib -L dependency=target/native-pyramid-profile/release/deps -o experiments/donor-consistency/controls-1/diagnose.exe
experiments/donor-consistency/controls-1/diagnose.exe
rustc --edition=2021 -O -C lto=thin experiments/donor-consistency/controls-1/diagnose-fixed.rs --extern strehl_core=target/native-pyramid-profile/release/deps/libstrehl_core-60ead7b714ba5262.rlib -L dependency=target/native-pyramid-profile/release/deps -o experiments/donor-consistency/controls-1/diagnose-fixed.exe
experiments/donor-consistency/controls-1/diagnose-fixed.exe
```

Both diagnose sources are extracted from the independently authored fixture,
using the actual experimental core consumer. The second adds only
`ws.next_frame()` before each source in the fixture's merge loop.

| Observation | Original fixture loop | Cache-reset loop |
| --- | --- | --- |
| Maximum returned-image disagreement |0 DN in all four planes|0 DN in all four planes|
| Pre-hull excursions |1 (roundoff-sized pin)|4|
| Pre-hull pin values |1800,1940,2080.0002,2220|2396.8613,2547.7573,2674.7856,2818.2969|
| Final pin values |1800,1940,2080,2220|1800,1940,2080,2220|

The test helper reused FrameWorkspace without invalidating its memoized colour
pyramids. It therefore merged first-source coefficients repeatedly even though
the supplied raw planes changed. Actual BandWorker already calls next_frame;
the production renderer was not changed. The independent author fixes the
test lifecycle and adds a base-equals-all-source-mean witness with distinct
source bases, preserving the original fixture and excursion threshold.

The corrected entire independent control suite then passed through the lean
harness, which includes the exact control file and verbatim geometry functions,
and links the hash-bound unchanged core. Command:

```
python -I -B experiments/donor-consistency/lean-controls.py --out experiments/donor-consistency/lean-1
```

Compile3.782s and controls0.125s child wall; these are operational receipts,
not a repeated comparative benchmark. Both tests pass; independent three-source
mean base is bit-exact, original all-ones excursions4, explicit second clamp
excursions4, largest image comparison discrepancy0.00024414DN. Invalid-input
panics are deliberately caught refusal controls. The final fresh CLI build and
its controls remain required before full rendering. This lean route avoids a
full CLI link for each diagnostic print while preserving the actual core path.
