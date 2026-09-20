# Independent colour-error scale attribution

Root executes only saved-array arithmetic; no model forward, fitting, RAW
decode, rendered image modification or quality promotion:

```text
colour-error-controls.py commission --out <run/commission>
colour-error-decomposition.py --out <run/decomposed>
colour-error-controls.py score --candidate <run/decomposed> --out <run/scored>
```

Use exactly the supported native64×64 domain `[16:80,16:80]` from the full96×96
flat and layered images, for retained visibility1, shot-prior1 and Cauchy1.
First cast saved image and truth to f64, then subtract, then form the two
coordinates `delta_R-delta_G` and `delta_B-delta_G`. This is the unchanged frozen
scalar chroma score's arithmetic. It is analysis of saved f32 output, not a new
candidate image-arithmetic path.

For nested orthogonal block-average projections P2 and P4, partition error E
into E-P2(E), P2(E)-P4(E), and P4(E). The three mean-square energies must sum
to the original per-coordinate total. Separately split P4 into its global
signed mean and zero-mean remainder. Report both signed mean and squared DC;
never add the already included DC energy a second time. Overall chroma RMSE
is sqrt of the mean of the two coordinate total energies.

Repeat for basis origins `[x,y]=[0,0],[1,0],[0,1],[1,1]`, equivalent to circular
roll by `[-y,-x]`. All original pixels remain and every phase must have the
same total. **Wrap groups join opposite domain edges artificially.** The phase
values are sensitivity checks, not independent replicates or four different
images. Do not trim to improve a conservation or comparison result.

The independent oracle enumerates coordinate groups modulo64 and assigns each
group's mean back to original coordinates. It does not use the author's roll,
reshape or repeated-pooling implementation. Commission four fixed error fields:

- Constant signed colour error `[-7,13]` must reside entirely in DC, retaining
  its signs. Absolute means or a missing bias term fail this case.
- Alternating native checker `[5,-9]*(-1)^(x+y)` must have within2 energies
  `[25,81]`, with zero coarser projection. This checks Bayer-phase-scale routing;
  it is not evidence that real checker error is an optical null mode.
- Aligned4×4 constant blocks with alternating `[4,-6]` must reside in common4
  at phase00; shifted bases must exercise nonzero within2 energy while keeping
  the original pixels and total. An invariant-subband implementation fails.
- Weak fixed smooth sines must exercise all three non-DC components and agree
  with the independent coordinate oracle at all phases. A deliberately wrong
  decomposition using E-P4 plus P2-P4 double-counts middle-scale energy and
  must show positive excess. This proves the conservation check can reject an
  overlapping decomposition rather than merely confirming a tautological sum.

Array input immutability is asserted. Arithmetic comparisons use f64 roundoff
tolerances (absolute1e-10 plus relative2e-12), not image-quality thresholds.

Actual scoring verifies all six expected case/arm bindings, source and truth
hashes, fixed support, every component against the independent grouping oracle,
and total chroma against the existing frozen `scored/result.json` for that arm.
It preserves only compact decompositions and scalar-score hashes, not optimizer
histories. Inputs remain unchanged. Existing rejected quality decisions remain
rejected.

The result can locate error energy by this particular block basis and expose
phase sensitivity. It cannot identify an optical nullspace, a demosaicing cause,
a photon-noise mechanism or a better prior. Low common4 error could coexist with
bad phase error, and low total error could coexist with lost true fine detail;
neither component energy is a new quality acceptance criterion.
