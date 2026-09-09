# Independent native saved-reader and decoder design

Source-only companion to independent-protocol.md. No decoder, simulation,
operator, control or candidate has executed. This specifies the intended
independent entry point for root/peer source review; it is not another process
framework or permission to open RAW. The producer owns actual fold/observation
code. The independent reader owns only decode ownership, independently written
stencils, statistics and interpretation. It cannot verify its own source choices;
sampler_result_review and root review the concrete implementation before release.

## Closed work population and interface

Use existing reviewed owned-process/capture helpers and exact source/input
FileRefs. A root-authenticated release binds the27 originals, nine paired native
invocations/eighteen f32 outputs AND eighteen existing write_merged TIFFs,
source/binary/config/feature identities, all actual
outer/child/terminal records and this protocol/design. It also binds the one
independent27-original decoder stage. Reuse established same-file source/receipt
interfaces; no directory discovery, generic recovery engine, new imported-runtime
capture, broad dependency inventory or changed old200-source map.

The independently authored reader must run in this order:
1. authenticate bounded metadata, source/schema/argv/counters and actual process
   dispositions, preserving refusal prefixes;
2. execute the synthetic/helper portions of the20 fixed result groups once,
   retaining variants/restorations before the independent RAW decode. Groups17/18
   remain pending for their actual saved-native output/exercise portions;20 checks
   metadata authority before scientific reads. No successful portion is rerun;
3. independently decode each of27 original snapshots once, copy the one fixed
   ROI during its live decoder lifetime, and compare every source/row hash;
4. read only fixed saved current consumer arrays,18 output buffers and18 native
   writer TIFFs; complete
   the actual portions of17/18 with their fixed byte/bit faults/restoration; verify
   complete associations, independently reproduce deterministic stages and
   perform the declared temporal/prediction/nuisance calculations;
5. publish detached bounded per-block/route results and compact final references,
   with source and complete external interval/exit retained by root.

If the controls and independent decoder are separate released processes, controls
are not repeated by every file. A true refusal stops its dependent claim and
retains visited/unvisited identities. Existing original metadata/read ledgers
remain charged. Stage allocations and exact CLI are root release prerequisites,
not invented here. The source-only64MiB/4MiB/60CPU/120wall lane does not authorize
77 real original decodes or private numerical controls.

## Independent arrays and bit arithmetic

Raw array serialization is uint16 little-endian interleaved native sensor rows,
256x256=131072 bytes. Deinterleave by literal four parity offsets. Four-plane
serialization and output are planar R,G1,G2,B, each128x128, float32 little-endian,
262144 bytes total. Each existing-writer TIFF is256x256 RGB16 in the declared
camera-native linear measurement path, Exposure::None/restore None/demosaic true
and actual levels/WB. Require original write_merged call/source/setting association
and exact whole-byte equality across the SAME f32 witness groups; the two byte
checks are both mandatory. Use the existing admitted TIFF metadata reader if
needed for shape/settings, with no new quality metric or alternate writer oracle.
Producer preregistration must bound the18 output extents and writer calls; they
add no fold or original decode. Luma/variance each65536 bytes. Actual Laplacian level lengths
are16384,4096,1024,256 (21760 total), base64. The bound is based on these fixed
shapes, not array headers trusted from a receipt. Per-band saved field labels
must distinguish actual L/E/V/weights from a DERIVED floor/threshold-side value.

For raw codes, extraction, clamp, luma, supplied variance, reduce, expand,
Gaussian variance reduction and smoothed square energy, use an independent
binary32 evaluation of the actual scalar operation order. R32 means correctly
rounded ties-to-even binary32 after EACH elementary add/subtract/multiply/divide
or square root; it can be implemented via an explicit pack/unpack or reviewed
array primitive that demonstrably preserves this order. Do not fuse multiply-add
or replace sqrt-then-square with its algebraic simplification. All inputs and
stencil coefficients are literal/source-bound; no producer function is imported.

Admission for those operations is EXACT IEEE bit equality for every retained
finite scalar. Signed zero may not be silently normalized in the byte equality.
A mismatch is an implementation-association refusal, not a physical sensor result.
Source review must confirm the native compile flags do not enable reassociation/
fast-math that changes the stated order. If it cannot, resolve that source-level
contract BEFORE execution rather than widening a tolerance after output appears.

Real-arithmetic Hdiag(q)H' predictions are separately computed in binary64 from
independent sparse one-dimensional stencils. A 2D Laplacian is the difference of
two separable Gaussian products. Coalesce equal original indices at the crop
boundary. Use the resulting rational/dyadic weights; no Monte Carlo white-field
measurement supplies the expected edge variance. E-scale prediction is the
literal five-tap smoothing of the band variance. The native beta*Gaussian(V)
approximation remains a separate actual consumer comparator.

If linear-prediction algorithms use two mathematically equivalent evaluation
orders, their private controls require |a-b| <= 2^-38*max(1,|a|,|b|), independently
of sensor output. This is a fixed binary64 numerical agreement bound, not a model
accuracy bar. Every result must be finite and diagonal predictions nonnegative;
a tiny negative due to cancellation is refused, not silently clipped. Failure
before RAW is a valid source/control outcome requiring a prospective revision.

## Actual weights, floor and exercise

Root approved preserving the existing scalar closure. Derive F=R32(R32(gate*beta)
*max(V,0)) and X=R32(E-F), excess=max(X,0), directly from observed operands.
These are DERIVED quantities. Do not claim the logger observed a private scalar
it did not read. Preserve actual weights, actual E/V, beta source and config.

With this frozen HardFloor/significance0 configuration, mean_coarse bypass must
be false for k0..3; base remains Mean. excess<=0 requires an exact zero weight.
For positive excess form r=R32(R32(excess/max(F,1))/64). The finite actual
configuration has p2 and noninteger p; p1 is not an admitted real-config value.
At p=2 evaluate R32(r*r), which CAN underflow to zero despite positive excess.
Require EXACT binary32 bits, including zero; no absolute tolerance applies.
Retain that zero-underflow class separately from threshold rejection. Do not
infer positive weight from positive excess without this branch check.
For a separately labelled source-branch p1 witness, the result is r itself,
which can also be zero after rounding and requires exact binary32 bits; it
cannot change the real-config population.
At other p the actual source takes
exp(clamp(p*ln(r),-80,80)); independently evaluate that real function in binary64,
using the actual recorded f32 p/r and the source's intermediate R32 placement.
If rounded r is zero, ln(r)=-infinity and the clamp gives-80 exactly; handle
that source branch explicitly instead of calling a domain-erroring log(0).
ONLY for this log/exp branch, because independent libm need not reproduce its
bits, require
|w-w_ref| <= 2^-14*|w_ref| + 8*2^-149, fixed before execution. No absolute1e-6
floor may swallow a physically tiny but positive weight. This does not authorize
a threshold or output tolerance; observer output remains byte-exact.

Finite private witnesses inside group18 are fixed as follows, without claiming
that every witness is physically reachable on this sensor: E=F=1,p2 (threshold
zero); E=65,F=1,p2 (positive r1,w1); E=65,F=1,p3.92 (positive); E=2^-74,F=0,p2
(r2^-80,w underflow0); E=2^-149,F=0,p3.92 (r rounds0, clippedexp(-80)>0);
E=2^100,F=0,p3.92 (upper exponent clamp); and E=2^-149,F=0,p1 (source-branch
witness outside the real p population, r/w round0). Require all named branches
actually visited. Change the w1 positive witness to4 through the SAME weight
predicate and require rejection/restoration. Do not use multiplying a zero
weight as power. Also replace the correct p2-underflow zero with the minimum
positive subnormal bit pattern; the exact-bit predicate MUST reject and restore.
These seven branch witnesses and two mutation/restoration pairs remain declared
variants inside group18, not additional result groups. Flipping threshold-side metadata
without changing observed E/V also rejects that group's association. If actual
paper/dark fail to exercise a class, retain NOT_EXERCISED and no claim about that
class; synthetic power does not fabricate real gate use.

## Conditional scalar uncertainty implementation

No new scipy/runtime closure is needed solely for chi-square quantiles. The
finite df population is2,4,11,21. Define chi-square CDF via the regularized lower
gamma at x/2. For integer shape use P(1,z)=1-exp(-z); for half-integer shape use
P(1/2,z)=erf(sqrt(z)); advance with
P(a+1,z)=P(a,z)-exp(a*log(z)-z-lgamma(a+1)). z=0 is exactly0.
Use ordinary binary64 math functions, finite checks, and the increasing CDF
branch. Determine p=.025,.975 quantiles by exactly64 bisections of [0,128],
requiring the bracket's CDFs enclose p. Do not fit a quantile to simulation.

The df2 reference is independently analytic q_p=-2*log1p(-p); compare computed
quantiles within1e-10 absolute. Independently bind df4/11/21 to the primary
[NIST chi-square table](https://www.itl.nist.gov/div898/handbook/eda/section3/eda3674.htm),
read2026-09-09. At CDF probabilities(.025,.975), the listed pairs are
df4=(0.484,11.143), df11=(3.816,21.920), df21=(10.283,35.479).
Require absolute error<=0.0005001 against EACH table cell: the published table
has three decimals, not1e-10 precision. Within group19 omit the final subtraction
term from each df11/21 CDF recurrence; the resulting quantiles must fail the SAME
NIST-reference predicate, then restore. Route df4 to the wrong half-integer start;
it must fail its NIST pair and restore. Record all expected/actual values and
reached faults. No simulation-fitted quantile or derivative table is used.

Also require positive ordered quantiles, CDF inverse residual<=1e-10 for every
fixed df/p and reject unsupported df. That inverse residual is numerical
consistency only, not corroboration of the CDF. Wrong spatially inflated df
belongs to group19. These controls do not establish that the real quantized/
clamped samples are Gaussian or independent. No interval for E/clamped data.

The noisy frame4 prediction uncertainty is labelled separately from the temporal
variance interval. Do not combine them into an unsupported exact coverage claim.
All nuisance screen score operands,32x32 block statistics and pair contributions
remain available even if the conditional interval is uninformative.

## Final truth labels and read bounds

The final report separates directly observed producer values, independent raw
observations, exact arithmetic associations, source-derived floor/support rules,
model-conditional predictions/uncertainty and unresolved physical premises.
A completed diagnostic is not an unconditional calibration PASS. Both f32 and TIFF identities are required in the first2dark witness; this is
not a22dark output hash experiment. A nominal identity map
is not proof of per-channel sample identity.

Before execution, the concrete reader must give exact source pins, bounded array/
metadata/output populations, final publication slots and the existing root wrapper
interface. All20 groups/variants must be represented with specific error checks,
restoration and actual visitation. The current document requests no additional
capture, spatial window, RAW/image population, compiler run or metric selection.

Methodology source hold: concrete producer patch/adapter and independent reader
implementation remain subject to full independent source review, build/control
release and actual-data authority. Holding this design does not close any of
those remaining stages or authorize a candidate import/execution.
