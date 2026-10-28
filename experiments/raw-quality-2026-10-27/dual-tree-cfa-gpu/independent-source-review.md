# Literal CUDA continuation source review

2026-10-27. SOURCE-REVIEWED / DERIVED, no numerical execution. This reviewer authored `bridge.rs` and independently audited the producer's CUDA server, root runner and independent control wiring. Bridge checks are therefore an author cross-check; the root and control author separately reviewed that source. No source changed after root announced build1.

## Frozen checkpoint

| Source | SHA-256 |
| --- | --- |
| `bridge.rs` | `3329927579e4a12fd8e34667b74dbed24222b69b69151c3719d69231527adb81` |
| `gpu-server.py` | `b17820bd8924d1ace1a76ae17dbc10465ccebe2782c0ffbae586d02d90c07fca` |
| `controls.rs` | `e7d5d23607847ac235d4f21e13375368f551eb03720b00215ac4f733e3026785` |
| `run.py` | `71e024406465fdd5e57c1063db102411823d74261931822e94cb130a9123783f` |

No remaining source blocker found. Rust formatting/source parsing and the author's Python AST parsing do not establish compilation, CUDA availability, parity, cost or quality.

## Literal operator and transport

The grouped horizontal channels are tree x {L,H}; the subsequent vertical channels are {LL,LH,HL,HH} for each tree. Reversed correlation taps with periodic extension indices from `-maximum` through `N-minimum-1` implement the CPU sample address `2m-n`. The transpose convolution followed by fixed-order periodic folding maps extended coordinate j to `(j-maximum) mod N`, including coarse axes shorter than the filter. Packing, unpacking and four-tree averaging match the declared CPU algebra. The GPU uses the same published decimal/f32 filters, first-stage versus Q14 distinction, reflection composition and seven levels. No third-party DTCWT implementation is used.

S5 remains horizontal then vertical, clamped independently per coefficient plane. The eight pair differences accumulate WB-scaled complex power divided by16; the floor remains twice its smoothed field. The SNR64 weight, exact exponent bits, exp clamp, common running weight scale, mean fallback, terminal lowpasses and actual input hull match the CPU recipe. Conv/FMA reduction and device log/exp arithmetic can differ; source agreement is not numerical identity.

Original u16 noise construction and all sixteen actual four-phase CPU remosaic/extraction calls stay in Rust. The signal is passed directly from canonical gathered samples, with no alternate source interpolation or aligned capture volume. Source ordinal149 remains149. Python receives one field per request, retains only the current source signal and bounded coefficient/accumulator state, and performs both signal analyses. The bridge independently counts its actual callback loop and verifies returned source/probe census.

Protocol operations and payload lengths agree. Signal/probe messages echo index/draw; small stage arrays are energy, floor, raw weights and phase0 signal AC+LL in declared order. The bridge unwraps `source_evidence` and final `evidence` into the CPU-compatible receipt shape, preserving fallback counts. Final payload is delivered, pre-hull, uniform and spatial-mean arms, each four phases. The frozen full adapter is included unchanged, retaining whole baseline CFA/RGB16/linear/material-metadata parity and individual pre-hull max0.05DN/RMS0.01DN nulls.

## Independent controls and failure recording

Inherited fixtures/guards resolve to local GPU wrappers; every CPU reference explicitly names the frozen CPU module. The eight quality cases and two singleton cases retain original source hashes, noise, geometry and truth. Canonical pixels must remain exact and CPU generated RGB hashes must reproduce the held screen. Independently replayed CPU energy/floor/weight bands must first match their actual CPU consumer hashes before comparison with saved GPU arrays. Structured cases additionally require positive selected coefficients, so successful fallback alone is insufficient.

The wrong-bank, one-sided phase/orientation/scale and actual floor times 2 producing-path foils retain their failure checks. All four pre/post-hull output phases are compared. Declared cross-backend tolerances differ from individual reconstruction bounds; they are fixed before execution and do not qualify photography. Final controls preserve a floor-foil error in the report rather than losing earlier observations. Historical independent-colour/glint quality failures must remain visible.

## Runner, ownership and practical limits

The runner selects the exact ignored GPU-module test with one test thread, builds the library test target, requires fresh compilation and binds Rust/Cargo plus local Python sources. It binds interpreter/server/config, helper sources and successful worker receipts before dependent stages. Device0 is pinned, allocator/TF32 overrides are removed, and the read-only preflight requires RTX5090 with26GiB free. Host job caps are8GiB for generated controls and14GiB for cost/full; the worker's24GiB limit and peaks describe the Torch allocator, not whole-device memory.

Children are ordinary non-detached processes with no breakaway flag; parent and child job membership are queried before protocol work. Normal completion requires child exit0, no trailing payload, unchanged interpreter/script/config, exact source census and complete server/bridge receipts. Error cleanup only terminates this bridge's child. The root's bounded Windows job remains the wall/CPU/host-memory authority.

The generated120s budget includes ten paired comparisons, all-source CPU stage replay, debug exports and several CUDA-worker startups. A timeout would establish incomplete qualification, not disprove the method. Full-source cost still includes sixteen CPU gathers, wire/copy/CUDA work, synthesis and writer; full299 remains forbidden unless `299*source_phase_seconds+finish_seconds+120<=1200`. No bound extension, fewer probes, filter rescue or implicit CPU fallback is authorized here.

This is an execution continuation of a quality-unqualified recipe. Complete identical-display photographs and full-resolution masters remain the decisive next evidence after mechanics and cost pass; no photographic improvement or SOTA claim follows from this audit.
