# Developer build, held-CFA replay and first controls startup

2026-10-27. **VERIFIED retained commands, receipts and file hashes.** No build,
CUDA job, RAW read or reconstruction was run by this reviewer. Freshly rehashed
1444 unique build/runtime/input/output references totaling2,898,217,360 bytes;
all matched. This includes the build-bound Rust/Cargo sources, frozen executable,
null configuration and every referenced null artifact and held parity input.

The recorded build command was `cargo build --locked --offline --release -p
strehl-cli --example native-cfa-develop --features native-direct-planes,native-correction-variance,native-gpu-gather --jobs 4
--message-format=json-render-diagnostics`; the environment is retained in
`native-spectral-build-1/invocation.json`. Cargo reported fresh
compilation, `fresh:false`, build-finished success and28.56s. The original owned
job was **not clean**: after direct Cargo exit0 and pipe EOF, one descendant
remained at the420s boundary; explicit TerminateJobObject succeeded. A zero
final total-terminated counter does not override that explicit record. The
narrow cached recovery then exited0 cleanly in0.891s, with `fresh:true`, the
same executable, no termination attempt or active descendants. Completion
honestly retains `compilation_job_clean:false` and `cached_recovery_used:true`.

The copied native developer is SHA
`174d3fd5221d4406140d6dcc5932f88139c03ae5fd8fcb0ac81f6b72efc856ff`.
Null command: this executable plus the absolute
`native-spectral-null-1/config.json`. It exited0 cleanly in4.063s, peak Job
commitment764,645,376 bytes, four workers, no termination or cleanup error.
It developed the complete6896x4596 CFA at native origin68,46, using exactly one
MHC stage/4596 row calls, no source demosaic, remosaic or RAW read.

The signed CFA copied exactly at SHA`1a442c16...`; actual normalized camera RGB
SHA`42429be1...` matches the retained baseline camera artifact. RGB16 pixel hash
`f98cb4d9...` and linear pixel hash`ee2b711b...`, complete material metadata and
held development all pass exact replay. The linear container is also identical;
RGB16 container SHA`abfcc458...` differs because this developer has its own
Software provenance. Pixel/material exactness is the intended null. Full
receipt SHA`458827b438de30d231880c16a37957ab333eccb0c79d7309498f2a9ad3c7e280`.
This commissions final development of a known field, not spectral fusion or
photographic improvement.

Controls1 exited1 cleanly after2.454s, peak Job commitment1,479,667,712 bytes.
Its saved receipt is `INCOMPLETE_NATIVE_SPECTRAL_CONTROLS`, complete:false,
mechanics:{}, cases:[], with all pass/quality/admission flags false. The traceback
ends in NVRTC compilation of the two C++14-incompatible `0x1p-24f` literals,
before a SpectralConsumer was constructed or any case measurement occurred.
No control, quality or timing-projection result can be inferred from this run.
Failure receipt SHA`6fa3e95c30a4512c684906f1e830464a8139534f5537a9cedb563c4f87b5e58d`.

Independently compared the preserved executed producer47b34c89... with repaired
producer`5bd9b9407a0f60504b1942435d85f6df4ba7ca296a541026dfb6e9626bf1b2dd`:
the complete bytes differ only by the two exact replacements with
`0.000000059604644775390625f` (2^-24). Inputs, guards, control population, RNG
formula and operations are unchanged. Root may rerun the unchanged controls
in a fresh directory. No outcome has yet qualified the spectral operator or
authorized a full photograph through this review.

## Second startup refusal

Controls2 also exited1 cleanly,2.469s and1,481,023,488-byte peak Job commitment,
with mechanics:{}, cases:[] and no acceptance. Compilation reached PTX, but
the inherited ordered-FIR whole-module no-FMA guard rejected it before module
load or case kernels. This likewise supplies no numerical control evidence.

The blanket guard was appropriate to the former serial FIR identity experiment;
the appended extractor also contains Gaussian transcendental math, while Torch
FFT already has its own arithmetic. A narrow private adaptation is defensible:
retain the old loader bytes/compiler options, require explicit rounded f32
multiply/add and no fused floating operations in ordered_x/y and the actual
spectral interpolation-weight/evaluation entries, and record any permitted
extractor fused operations in complete PTX metadata. Unclassified fused helper
code must remain a refusal until identified. Counts/location alone are not proof
of libdevice provenance. The author is preparing this source-only adaptation;
no numerical guard, fixture, RNG distribution or quality threshold change is
requested. Its exact diff and subsequent execution still require review.

The completed private guard was subsequently reviewed at producer SHA
`e7419571b90b67723ed3dfb1a812975b8b92a97cda28d1f1d5fd93ba7ef28a0b`.
AST/source comparison proves the CUDA literal is byte-identical to controls2;
all existing scientific methods are unchanged. Only constructor/metadata and
the added guard differ. It masks comments while preserving offsets, parses
balanced function bodies, requires all five named entries, and rejects every
floating fma/mad outside spectral_extract. Four protected entries also require
explicit rounded f32 mul/add. Per-body hashes, counts and instruction lines,
whole PTX and adapted-loader hashes are retained without claiming instruction
provenance. The loader change replaces exactly one assertion in a private copy;
the old loader and compiler flags remain unchanged. **No source blocker to
unchanged controls3 was found; numerical results remain pending.**

Root runner SHA`2f4aa0423414735bf7e31952605d30a0db308d0931c87c0fde5bd13a899899b5`
now saves the numerical dependency set before each job, requires cost to match
the passing controls' exact set, source149 to match both controls and measured
cost, and rehashes all at completion. This closes the stale-controls inheritance
gap raised in source review. No shared Rust, frozen controls or predecessor file
was modified by the reviewer.

## Tensor API repairs before complete scientific results

Controls3 reached the new PTX guard but failed on Tensor subtraction of a Python
Boolean in source-lattice coordinate construction; clean exit1,2.765s. Exact
comparison to its preserved producer shows only `(kind!=0)` and `(kind==2)`
changed to their integer0/1 casts. Producer SHA
`378e42c1e13065cd90cf0ecc5468e4a8c41ab5c1fcf41c5397e90ea0392c36a2`.
The intended numerical phase offsets, physical geometry and gates are unchanged.

Controls4 then executed the first constant prepared source, but the diagnostic
`view_as_real` refused a lazy conjugated Tensor; clean exit1,3.203s. Its producer
did run kernels, so this is not a pre-kernel failure. Exact control-source diff
adds only `opposite.resolve_conj()` before reading its real representation.
Control SHA`08f01bd367c3194375d1ded022b718915d382cb9f459ec549f6623a750eeb07e`.
Resolving the conjugate does not alter its mathematical values or the scorer.
Both attempts retain incomplete receipts with no completed cases or mechanics;
neither provides an accepted scientific result. The independent reviewer made
no edits to these bound sources. Complete controls5 results remain pending.
