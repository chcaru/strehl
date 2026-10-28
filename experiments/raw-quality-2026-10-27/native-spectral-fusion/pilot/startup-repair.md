# NVRTC literal portability repair

2026-10-27. Root's controls1 process failed during NVRTC compilation, before
any controls or CUDA kernels ran. The retained compiler log reports four parse
errors on the two `0x1p-24f` literals in the newly added probe kernel. This is
a startup/compiler compatibility failure, not a measured control result.
The actual pinned compiler language option is `--std=c++11`.

The only producer change replaces those two literals by
`0.000000059604644775390625f`, exactly2^-24 and exactly representable in f32.
No operation, probe hash, rounding rule, input, control, threshold or numerical
algorithm changed. No Rust/Cargo or predecessor source was edited.

The executed source is preserved at
[controls1 snapshot](../../../../outputs/raw-quality-2026-10-27/native-spectral-controls-1/spectral-operator-executed.py),
SHA256 `47b34c89b2e45f4ddc1b9d61a41dab987179d6e22c9e135cd29e3da181a0de0b`.
The [compiler log](../../../../outputs/raw-quality-2026-10-27/native-spectral-controls-1/process.log)
remains unchanged. A byte comparison against that snapshot verified that the
new source is exactly the two literal substitutions; Python AST parsing passed.
Repaired producer SHA256:
`5bd9b9407a0f60504b1942435d85f6df4ba7ca296a541026dfb6e9626bf1b2dd`.
Neither check imports the producer or performs numerical work. Root alone will
rerun the unchanged controls in a fresh output directory.

## Controls2: scope the inherited PTX guard

Controls2 compiled the CUDA module, then stopped at the predecessor loader's
whole-module floating-FMA ban before any case or kernel execution. Its executed
producer remains preserved under controls2; this is again a startup failure.

The new private adaptation leaves the pinned predecessor file unchanged and
replaces only that global assertion in the in-memory loader source. A PTX
body parser requires `ordered_x`, `ordered_y`, `spectral_weights` and
`spectral_evaluate` to contain separate rounded f32 multiplication/addition and
no floating fused instructions. Fused operations are permitted only within the
named `spectral_extract` entry, which contains the f32 Gaussian Box-Muller
transcendentals; unknown or unclassified fused helper paths still refuse.
This is an explicit entry-scoped permission, not a claim that instruction
location alone proves its libdevice origin.

Runtime metadata records the whole PTX hash, every parsed body's hash, fused
instruction counts and actual instruction lines, protected-entry results and
the exact privately adapted loader hash. The compiler flags remain unchanged,
including `--fmad=false`, `--ftz=false`, precise division/square root and C++11.
An AST literal comparison proves the appended `CUDA_SOURCE` is byte-identical
to controls2: no signal operation, Gaussian distribution, probe key, guard
threshold or control changed. AST parsing passed without importing the module.
The predecessor loader SHA remains16688f2b. Root alone performs the next run.
