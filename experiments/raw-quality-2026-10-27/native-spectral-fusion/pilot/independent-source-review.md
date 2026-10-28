# Independent source review before the fixed pilot

2026-10-27. **SOURCE-REVIEWED, not numerically verified.** No concrete blocker
was found in the producing operator, streamer, native developer or presentation
joins. This permits the allocated bounded controls and subsequent root-controlled
cost decision; it is not release of a complete299 run or a quality claim. The
reviewer authored the independent controls, while the producer independently
cross-read those controls. No operator import, CUDA compilation, RAW access,
reconstruction or build was performed by this reviewer.

Reviewed checkpoints:

| File | SHA256 |
| --- | --- |
| spectral-operator.py | 47b34c89b2e45f4ddc1b9d61a41dab987179d6e22c9e135cd29e3da181a0de0b |
| stream.py | 5835e6249fb613b606f2e4e899c287817266a29535f859b1647c6f6553f7f728 |
| native-cfa-develop.rs | 57ff4d8c2f33547337b4953e3344617b61b557d2560dc59cf09ab25eb7d47eab |
| run.py | e15477db98af91b9f82b267c2baf64f043740be129f7127c74971eb55ed6315a |
| views.py | 91da211a061be5681ebab1e904c21200cdb89e0f4b4d571abf9d8c7fc555d69e |
| controls.py | 1afdf349ec675c6bd6cc7a0c8c2dbbd5e389e8cea4a42f3efcabf92edb0a1d33 |
| controls-protocol.md | 17246e84dbeff3663bfaa70e21ba8e00185f0cd53d8841c84dee0fc58199339a |

The R/B square and green quincunx mappings preserve their declared physical
phase positions. The green inverse is x=u+v+1,y=u-v; the two output greens query
one interpolant at distinct native positions. Source patch centers use the
declared63.5-native center and nearest-ties-even lattice origin. Held map pulls
in stream.py are reference-to-source, with center3516,2344 and twice the stored
quad translation; the stored149 transform is not silently replaced by identity.
Source/window support is checked before interpolation, without adaptive recentering.

Reflection is about integer0/dimension-1 and preserves CFA parity. Signal and
noise read the same reflected original indices. The counter key includes source,
draw and reflected index, so overlap and repeated reflection do not manufacture
independent probe values. All16 draws pass through the actual source taper,
cell-response ratio, interpolation and output analysis; eight pair differences
divided by16 estimate coefficient variance. This is conditional propagation of
the supplied noise model, not a measured optical PSF or a guarantee for the
data-dependent output selector. Marginal variance normalization does not whiten
cross-phase or cross-frequency covariance.

The unitary FFT, symmetric even-Nyquist split, aperture ratio evaluated before
padding,4x inverse amplitude factor and separable degree15 evaluation are
internally consistent with the declared source interpolant. Ordered CUDA
arguments match their scalar/pointer types; tensors are contiguous and tracked
on the current Torch stream. The unchanged ordered-FIR loader is hash-bound and
privately composed. Its strict PTX no-FMA assertion may refuse startup if
Box-Muller libdevice code emits an explicit FMA: that would be a preserved
mechanical failure, not justification to change controls silently.

Uniform fusion is synthesized through the actual coefficients and OLA. Negative
half-window origins provide intended outer-corner coverage; full execution
requires every delivered pixel to have positive coverage. Source IDs and patch
counts are checked during accumulation and at finish. The cost16 branch uses
the frozen16 grid indices and explicitly marks its partial image incomplete.
Its timing includes geometry plus signal/all16 probes/accumulation, with finish
and whole-path warmup separately recorded. Full-size accumulator and allocation
pressure are not commissioned by the small batch; the separate source149 stage
remains necessary if the extrapolation is practical.

The streamer verifies consumed cache bytes and metadata before/after, and all299
original RAW metadata against the frozen export. It does not reread original RAW
bytes; the export's independent four-column coverage limitation remains explicit.
It holds one original u16 source and bounded patch intermediates, plus output
coefficient accumulators, rather than a source-aligned image volume. No per-source
RGB is generated. The final developer retains signed CFA, uses the held exact
WB/range/matrix/tone and one actual MHC stage per delivered arm, and saves its
actual camera field. Its held-CFA no-op must reproduce both full pixel payloads
and material metadata before the controls rely on it.

The root build/null wrapper preserves fresh build identity, terminal process
accounting and its narrow successful-compiler/owned-descendant recovery path.
The null binds the known CFA hash and historical RGB16/linear masters. It does
not infer scientific success from compilation. The presentation helper binds
each arm's own full master, the same executable/development, exact null, complete
dimensions/ICC and ten native PNG subarrays. It explicitly leaves source-census
and process qualification to the root producing wrapper.

Remaining scientific limits are material: a finite tapered source interpolant
is not true continuous radiance; source lattice aliases remain; shared weights
cannot independently select conflicting colors/depths in one quad-frequency
pair; the noisy estimated variance can affect selection; reflected boundaries
are not extra observations. The fixed lower-only component recovery score can
pass overenhancement and is not an absence-of-halo test. Controls preserve those
quality failures. Passing mechanical controls only permits a cost decision and,
if practical and separately released, the complete candidate/uniform photograph.
No additional source changes or broader campaign are requested by this review.
