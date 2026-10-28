# Fixed six-direction CFA consumer

2026-10-27. ARGUED / DERIVED, source preparation only. No implementation,
RAW read, numerical run, installation or quality claim. One fixed experiment,
not a filter/strength search. Root owns execution and release.

## Question and retained failures

Replace the real Laplacian synthesis with a genuine four-tree, six-complex-band
transform. The question is whether its directional and approximate shift
stability preserves photographed insect boundaries and detail. It does not
identify occlusion, restore unrecorded detail, calibrate an optical PSF, or make
energy a reliable glint discriminator.

The actual `band-weight-oracle/directional-prior.md` supersedes the older
`green-match-rgb/directional-route-review.md` absence finding. The completed
70-source separable complex H/V/D vitamin-C experiment broadened colored
highlights and was rejected. Its shared all-CFA energy is retained as a known
imperfect estimator; the changed question is the six-direction basis, not a new
claim for that estimator. Preserve the fractional weak-red failure and the
earlier coarse-detail failure. Seven AC levels, with an averaged terminal
lowpass, avoid repeating the previous twelve-level-to-DC depth confound on
the full photograph. Small generated canonical images still truncate at
MIN_LEVEL_EXTENT=8 while the candidate's reflected domain always supports
seven levels. Their reported dimensions and exponent bits expose this
confound: generated absolute failures are useful, but a generated relative
gain cannot isolate the basis. The complete weevil is seven versus seven.

Prior lookups: root ran unified and mechanical `dual tree complex wavelet`
searches recorded in the brief. This preparation read the two directional
audits above and the actual `parallel-cfa-wavelet/implementation.rs`,
`parallel-cfa-wavelet/full-stack.rs`, and `boundary-cfa-wavelet/probe.rs`.
No restricted toolbox implementation or coefficient asset was consulted.

## Published bank facts and exact indexing

First stage: the four columns of Table 1 in [Bal 2012, DOI
10.1364/BOE.3.003231](https://pmc.ncbi.nlm.nih.gov/articles/PMC3521299/), read in
the [primary article PDF mirror](https://pdfs.semanticscholar.org/cf9e/8b662ce7319bf901993f9acd31fb588880f3.pdf).
Only published numerical filter facts are used. The first-stage table is
distinct from the later-stage table; no denoising implementation is adapted.
Store the following decimals directly as f32, with tap indices 0 through 9:

| n | a low | a high | b low | b high |
|---|---:|---:|---:|---:|
| 0 | 0 | 0 | .01122679 | 0 |
| 1 | -.08838834 | -.01122679 | .01122679 | 0 |
| 2 | .08838834 | .01122679 | -.08838834 | -.08838834 |
| 3 | .69587998 | .08838834 | .08838834 | -.08838834 |
| 4 | .69587998 | .08838834 | .69587998 | .69587998 |
| 5 | .08838834 | -.69587998 | .69587998 | -.69587998 |
| 6 | -.08838834 | .69587998 | .08838834 | .08838834 |
| 7 | .01122679 | -.08838834 | -.08838834 | .08838834 |
| 8 | .01122679 | -.08838834 | 0 | .01122679 |
| 9 | 0 | 0 | 0 | -.01122679 |

Stages 2 through 7: the 14-tap prototype in Table 2 of [Kingsbury 2001,
DOI 10.1006/acha.2000.0343](https://staff.washington.edu/dbp/s530/PDFs/2014/ACHA-Kingsbury.pdf).
For `HL(z)=sum_n h[n] z^-n`, indices -6 through 7 are:

```text
 .00325314 -.00388321  .03466035 -.03887280
-.11720389  .27529538  .75614564  .56881042
 .01186609 -.10671180  .02382538  .01702522
-.00543948 -.00455690
```

Use this local convention, matching the a/b and highpass signs of Bal's
later-stage table: `a_low[n]=h[n]`, `a_high[n]=(-1)^n h[1-n]`,
`b_low[n]=h[1-n]`, `b_high[n]=-(-1)^n h[n]`. It swaps the a/b labels and
negates both highpasses relative to Kingsbury's equations after Fig. 7; it
does not change the bank. This explicit convention prevents silently mixing
two publications' tree labels. No tap normalization or fitted coefficient
repair is permitted. Published decimal truncation and f32 arithmetic mean
numerical reconstruction, not a bit-exact mathematical inverse.

Analysis is `y[m]=sum_n filter[n]*x[(2*m-n) mod N]`, low and high at the
same even decimation origin. Synthesis is its transpose: scatter each
coefficient through the same tap and index expression. This specifies delay
and reversal without relying on a library's convolution convention.

## Two dimensions, physical CFA and finite image

Run four separable real trees AA, AB, BA, BB, first letter for x and second for
y. Each tree recursively analyzes only LL. At each level and each real
LH/HL/HH group, pack:

```text
z+ = ((AA-BB) + i*(AB+BA)) / sqrt(2)
z- = ((AA+BB) + i*(AB-BA)) / sqrt(2)
AA=(Re(z+)+Re(z-))/sqrt(2); BB=(Re(z-)-Re(z+))/sqrt(2)
AB=(Im(z+)+Im(z-))/sqrt(2); BA=(Im(z+)-Im(z-))/sqrt(2)
```

After unpacking and four real inverse trees, average their images by 1/4.
Do not average magnitudes or independently elect real/imaginary donors. Six
angular responses, nominally +/-15, +/-45 and +/-75 degrees, must be
commissioned with the actual signs and axes before assigning angle labels.
Correct roundtrip alone does not establish directionality.

Apply the same bank to R, G1, G2, B planes at their actual 2-native-pixel pitch.
Offsets from a Bayer-cell origin remain (0,0), (1,0), (0,1), (1,1). No phase
plane is translated or interpolated to pretend the colors were colocated.
The common guide aggregates this physical Bayer neighborhood; it is not a
per-sensel chromatic-registration or covariance-whitening claim.

For an input phase extent W,H, endpoint-repeating reflection extends right
and bottom to M=128*ceil(W/128), N=128*ceil(H/128). Mirror that core once in
each axis, producing 2M by 2N, and use periodic filtering throughout the bank.
Reflection uses period 2L: r=t mod 2L, index=r if r<L else 2L-1-r. Inverse
crops exactly [0,0,W,H], with no further sensor crop. This fixed boundary
convention handles odd input sizes and does not invent independent noise at
reflected samples. Altered coefficients near natural boundaries remain a
quality risk even when untouched inversion works.

## One fixed shared weight and actual noise propagation

Hold the actual current full-native CPU MHC/Catmull/remosaic gather, exact map,
source order, crop, CA-off weevil arm, first-source WB, matrix and display
baseline. Originals remain u16; gather/transform/accumulation are f32. No
RGB-stack volume. Final demosaic/development uses the ordinary writer once.

For source i, level k and one of six bands, let z_ip be its complex coefficient
for CFA phase p. With fixed WB amplitude gains g_p, define
`E=S5(sum_p g_p^2*|z_ip|^2)` and `V=S5(sum_p g_p^2*v_ip)`.
S5 is the existing separable [1,4,6,4,1]/16 energy smoother, including its
clamped coefficient-grid boundary. Its radius is two coefficients at that
level, not two native pixels. Both fields use identical support. Use the
existing `soft_weight(max(E-2*V,0),2*V,exponent_at(k,7))`, whose exponent
ladder is [8,8,7.6832,5.488,3.92,2.8,2]. Preserve the producing helper's
finite floor and exponential cap; do not substitute a private formula.

Obtain v_ip using exactly eight independent original-source noise pairs,
sixteen draws, as in `boundary-cfa-wavelet/probe.rs`: supplied NoiseModel at
actual sensels, fixed `probe_seed(source_id,draw)`, original-u16 perturbation
and rounding, actual gather, the same reflection and new transform. Then
`v_ip=sum_pair |z_a-z_b|^2/16`. Refuse clipped/nonfinite probe construction.
This preserves MHC/resampler/cross-tree covariance in the propagated marginal
complex power. It is a finite conditional probe estimate, not an exact noise
law or independent degrees-of-freedom count. No white-wavelet gain shortcut,
private residual variance, or division by stack count is allowed.

One nonnegative weight multiplies Re and Im of all four phases. Each
orientation/scale has its own field; there is no directional median, phase
veto, hard donor or source-membership smoothing. Use the tested common
running-max-scaled weighted numerator/denominator to avoid exp(80)*DN
overflow. Shared weights can still erase depth/color components or favor
defocused glare: these are binding photographic risks.

Maintain the gathered spatial mean in source order. Analyze that mean once
at finish: use its four terminal LL arrays and any coefficient whose total
weight is zero. This avoids a second full complex fallback accumulator. It
is mathematically the coefficient mean, with separately disclosed f32
association differences. Invert and apply the existing actual gathered
InputRange hull per physical phase; report its changed-site fraction. Do not
use the hull or exact-copy shortcut to conceal a broken transform null.

## Minimal implementation and resource decision

First implementation is independent Rust FIR code, not a third-party wavelet
package. `Plan::new(W,H)`, `forward_phase`, `inverse_phase`, and
`Accumulator::add_source` form the small seam specified in api.md. Generated comparison
uses the existing actual-gather adapter and ordinary camera_rgb writer.
Use one source at a time and one phase's four real trees in parallel; keep
row/column scratch bounded and drop it by stage. The pre-execution buffer
amendment retains pair A's four-phase coefficient map and streams pair B by
phase, releasing each A phase after subtraction. Only one gathered probe
exists at once. Signal energy is analyzed before probes and the signal is
analyzed again for weighted folding afterward: exactly two signal analyses
and sixteen probe analyses per phase/source. Accumulate weighted phase/pair
power divided by16 directly into the common V field in f32, then smooth.
This is the declared accumulation order of the same marginal-power sum.
Never retain sixteen coefficient sets or aligned capture sources, and never
hide repeated gathers in the timing.

For weevil W=3448,H=2298, the extended phase is 6912x4608. Four phase
transforms have about 510 million f32 values: 2.04 GB decimal (1.90 GiB),
and the four-phase complex numerator adds another 2.04 GB. A shared band
scalar field is about 0.255 GB. Signal, numerator, denominator, scale, E/V,
the full pair-A map plus one-phase probe scratch, gathered planes, mean and
hull imply roughly 6-10 GiB host peak before allocator and canonical-worker
overhead, not merely 4x redundancy. Signal coefficients are released before
the probe pair maps and recomputed afterward.
This is DERIVED, not a measured memory commitment. No four-source parallel
execution is allowed for this route.

Root first runs one actual full-size source plus all sixteen probe gathers,
fold, inverse and writer, recording each stage and peak commit. Project
299-source cost from the complete per-source workload and add finalization;
root must accept that projection before a complete run. Bare FIR throughput
cannot qualify it. Initial checkpoint: four CPU workers and a 14 GiB host
ceiling, 300 s wall; this is a cost test, not a promise that CPU execution is
competitive. CPU full299 additionally requires the root's fixed
`299*source_seconds + finish_seconds + 120 <= 1200` gate.
If the projection is impractical, stop before 299 and port the same literal
separable FIR/packing operations to a persistent Torch CUDA worker, with a
bounded one-phase buffer protocol and CPU/GPU parity; do not drop probes or
change the bank to rescue timing. That port needs a separate root allocation.

## Mechanical nulls and photographic decision

Keep separate: exact canonical/off bypass; actual single-source
analysis/packing/unpacking/inverse before hull; and uniform-weight transform
fusion versus the mean of the same actual gathers. Prospective f32 mechanics
bound on signed DN fixtures is max absolute 0.05 DN and RMS 0.01 DN; preserve
failure rather than tuning taps or relaxing the bound. Test impulses at all
phases, fractional gather, constants, odd dimensions, natural edges and
modified coefficients at reflected boundaries. The one-sided sign/orientation
foil must fail; a consistent relabel of both forward and inverse is not a
destroyer. Flat-first and complete known-truth controls belong to the
independent plan. The bank's angular energy responses must actually separate
six directions, including noncardinal detail.

Finite mechanically valid output may proceed to the authorized complete
weevil observation despite retained generated quality failures. Save the
whole CFA, RGB16 master and linear master, exact canonical companion,
complete identical-display previews and existing vendor comparison.
Numerical nulls, local crops and synthetic scores cannot admit the recipe.
No photographic improvement or SOTA progress is claimed by this design.
