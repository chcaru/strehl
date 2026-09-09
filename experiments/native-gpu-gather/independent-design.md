# GPU gather: fixed first equivalence allocation
Prospective source-only design;18 tiny CPU/GPU comparisons, no timing or RAW reads.
This tests current arithmetic/storage, not camera calibration or photographic quality.

## Oracle and domain
CPU oracle is align_cmd::warp_frame_fullres_with_sink: current demosaic_row,
OpticalProfile::compose, Resampler::sample_checked and writeback_fullres_site.
A test-only explicit-CA argument at the existing resolution seam is permitted;
retain the ordinary gear guard. Do not use the GPU descriptor builder as oracle.
Capture the existing CPU per-site cover flags beside its actual written u16 codes.
The GPU may receive CPU f64-derived integer bases/f32 fractions and coverage;
give it the SAME host-computed f32 inverse-WB values, not another GPU division.
Use finite transforms/CA, positive finite WB, black512 or512.25 and u16 inputs.
White15360 is ordinary fixture metadata; the fullrange control uses65535.
RGGB only: four phases means R,G1,G2,B sites, not other unsupported CFA patterns.

## Fixed inputs
Reuse m194c-probe-layout/independent-tests.rs make_frame/warp conventions.
Consumed native size70x50, sourcek=1; its existing independent phase offsets,
two sinusoids and integer texture are the nonconstant/nonneutral witness.
L0: origin0,0,stride70,height50. L1: origin5,7,stride88,bufferheight68.
L2: origin2,9,stride101,bufferheight75,active71x51 but consumed70x50.
Poison padding and the odd trailing row/column; compare them outside consumption.
Ordinary WB=[1.15,1,1.65]; unity WB is explicitly named below.
T1=M194c warp(1),including off-centre scale/rotation/translation; F=plane translation(.185,-.115).

Six RGB cases:
0. L0, existing colour field,identity,unityWB,black512,CAoff.
1. L1,same field,T1,ordinaryWB,black512,CAoff.
2. L2,identical CONSUMED field to1,T1,ordinaryWB,black512,CAoff.
3. Case1 with synthetic CA epsR=.012,epsB=-.009,translation(.13,-.09)plane;
   green remains unmodified; these are test inputs, not measured lens coefficients.
4. L1,code=4096+x at every native site,translation(.25,0),unityWB,black512.25;
   covered interior half-integer outputs exercise Rust ties-away rounding.
5. L1,code=0 left of x35 and65535 otherwise; set(16,16)=65535,(52,34)=0;
   F,unityWB,black512,white65535; require actual unclipped gather excursions
   and final saturation so overshoot/clamp coverage cannot pass vacuously.
Nine additional RGB cases use case0 field/L1/unityWB/black512.25 and translation
(c/2,0), where native c is each of1.5,4,67.5 plus each of[-2^-40,0,+2^-40].
At output-native x0 these independently pin lower coverage,integer floor and
upper coverage; f32 coordinates alone cannot distinguish their neighbouring cases.
Catmull support is[1.5,w-2.5], then its internal clamp/floor/f32 fraction rules.
Case15 is native2x2,L0,distinct four phase codes[1000,2100,3300,4700],identity,
ordinaryWB,black512.25: all coverage false and every RGB output roundedblack512.
Cases16/17 replay1/5 in GREEN_ONLY mode; retain every original R/B code exactly.

## Admission and rejecting inputs
Require exact equality of EVERY consumed u16 and per-site coverage bit/count;
Outside storage stays unchanged; reuse one GPU object for different existing inputs.
Check packed halves, odd-stride row crossings, partial groups and all phase totals.
Mirror-extension must retain CFA parity; uncovered output is rounded/clamped
black, never zero. Only consumed greens are replaced in GREEN_ONLY mode.
Use independent literal coordinate checks at the three boundaries and a nonzero
CA direction check; CPU/GPU agreement alone cannot establish shared map semantics.
Wrong source base+1,swapped G1/G2 destination phase,and flipped coverage at an
informative covered site must each change output or coverage and fail admission.
Round/clamp literal controls reuse the existing table plus half ties' adjacent f32s;
require case4 actual half ties and case5 actual excursions, not just table checks.
Report first differing coordinate/phase,CPU/GPU codes and coverage plus counts; any
mismatch is CONTROL_FAILED. No tolerance/fixture retuning or new apparatus.
