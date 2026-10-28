# Independent controls5 and cost16 audit

2026-10-27. **VERIFIED saved receipts/hashes; no numerical job by reviewer.**
Controls5 completed cleanly in17.187s, peak host Job commitment2,866,483,200B,
GPU allocated296,262,656B/reserved392,167,424B. All10 fixed cases and20 complete
native64x64 outputs are present, with one MHC stage per arm, identical held
development/executable, signed-CFA copies, camera/RGB16/linear masters and
successful readback/preservation. Controls pass; quality fails. These are
distinct recorded outcomes, not permission to call the reconstruction accurate.

Freshly rehashed367 unique controls/cost completion, dependency, native artifact
and prerequisite references totaling978,869,799B: no mismatch. Controls receipt
SHA`c747fc882838b755a65683681ea4f9b17b338bdb7b56e39d27ee67a891677010`;
cost receipt SHA`eb2426fc8f54da9386c7965673ae5b0286cbec3dd842d66bdc7486f97331a43a`.
Exact commands and environments are retained in their `invocation.json` files:
controls.py with --out, --renderer-binding and --development-receipt; stream.py
with --mode cost16 and --out. Both use `python -B -X faulthandler`,4 CPU/1 interop
threads, TF32/autocast off, and the prospectively fixed bounds. All processes
exited0 with no termination, active descendants or cleanup errors.

## Mechanical evidence

Constant CFA maximum error0.000732DN is below0.02. Independent f64 direct-Fourier
comparison maxima are approximately0,0.000154 and0.000200DN for identity,
fractional translation and affine queries, below0.06/0.01 max/RMS bars. The
physical-phase, square-green, omitted-cell and wrong-pitch foils all fail the
same scorer. The separate continuous-cell truth errors reach1.282DN; these
remain explicitly model/window/quantization differences, not silently accepted
by relaxing the operator oracle.

Propagated-floor normalized maximum difference8.45e-7 is below2e-4. The doubled
floor foil is about1.000001. Original-index probe mean-0.00243/variance0.99862
passes its fixed distribution check, with overlap/reflection identity retained.
Uniform OLA maximum error over all cases0.000858DN, conjugacy0.000488DN, and the
odd-edge/missing-patch controls pass. These verify the declared producer; the
conditional floor is not whole-estimator variance or optical calibration.

Scoped PTX evidence is identical in controls and cost: whole PTX SHA
`0d61a18e9e40511bab93dbad272a03290589c02ef69c0c4eae108e5c755c4fd1`.
ordered_x/y, spectral_weights and spectral_evaluate have zero fused floating
instructions and explicit rounded f32 mul/add; spectral_extract has20 reported
fma instructions. Unclassified count0, compiler flags retain --fmad=false,
--ftz=false and precise division/sqrt, NVRTC12.8/compute120. This is scoped
instruction evidence, not proven instruction-to-libdevice provenance. Runtime
source/DLL bindings remain unchanged.

## Retained quality failures

Constant and the two flat guards pass. Nevertheless candidate flat RGB errors
18.075/18.242DN exceed uniform16.019/16.175DN; chroma15.250/15.489 exceeds
13.562/13.905. Passing the fixed1.15x+0.5 tolerance is not noise improvement.
Neutral structure passes the lower-only recovery score despite RGB/chroma
errors exceeding uniform. That guard cannot certify absence of overenhancement.

All six structured failures remain decisive against default admission:

| Case | Specific retained failure |
| --- | --- |
| independent-colours | R/weak-G/B recovery0.650/0.766/0.650; false components26.53,39.44,42.27DN exceed their bars. |
| green-diamond | G recovery0.667; false R/B33.25/19.30DN exceed14. |
| shared-bin-conflict | R/G recovery0.270/0.492; false R/B at the G component47.26/20.06DN. |
| red-cancellation-diverse | One red component has negative recovery-0.698; false-color components exceed bars. Individual original-CFA aliases require rank-aware interpretation. |
| near-fine-far-coarse | G recovery0.829/0.897 improves uniform0.446/0.853, but false R20.36DN exceeds16. |
| crossed-glint-sign-inversion | One B component recovers0.779, while a G component reaches1.991; the lower-only guard does not penalize that overshoot. Chroma98.76DN exceeds uniform70.18. |

The headline component scores are computed from final MHC camera RGB with
WB/range undone. They do not by themselves locate the false-color error before
versus during MHC. Signed CFA and actual camera fields are retained, but no
causal attribution is made here. Root separately authorized a small saved-array
stage audit; it is not a new reconstruction or a reason to retune these guards.

## Cost scope

Cost16 completed in4.172s, peak host3,913,768,960B, GPU allocated835,384,832B /
reserved1,296,039,936B. Source149, all16 frozen patch indices, one signal plus
16 probes, admission/accumulation and finish are present. Runtime counts2
signal/32 probes include the separate one-patch warmup. Initialization0.277780s,
warmup0.450054s, measured16-patch batch0.2554155s and partial finish0.0051668s
are recorded separately. Cache bytes/metadata and original RAW metadata were
preserved; this worker did not rehash/decode RAWs. Cost numerical dependencies
exactly equal those of passing controls5.

The direct batch extrapolation is0.2554155*(7957/16)=127.023s per complete source,
plus finish/other work. Multiplying that alone by299 is about10.55 hours, not a
complete-workflow forecast or a full-stack release. The16-patch accumulator does
not commission full output memory or full OLA cost. A source149 checkpoint fits
the prospectively declared300s/12GiB-GPU test and can refine this estimate; its
complete image is a singleton interpolation diagnostic, not focus stacking.
No full299 timing or photographic quality claim follows from this audit.
