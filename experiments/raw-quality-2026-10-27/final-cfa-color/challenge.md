# Independent challenge: one final spectral color completion

**SOURCE / DERIVATION REVIEW, 2026-10-27.** No implementation, numerical job,
RAW read or render. The spectral full299 photograph is still running and its
bound sources remain untouched.

**Decision:** the exact operator in [design.md](design.md) is implementable and
worth one bounded, same-CFA completion diagnostic after root release. It has a
clear changed question and an inexpensive path relative to another stack run.
It is not a general demosaic recommendation or an identified cure for weevil
softness. Its strongest risk is a deliberate sampling-prior tradeoff, not a
missing implementation detail.

## Algebra and producing contract

I independently checked the finite sampling argument. With even periods
`2(W-1), 2(H-1)`, half-period FFT shifts exist as integer indices. Each square
axis has `s(f)+s(f+1/2)=2`, giving the R/B quartet sum 4. The checkerboard shift
maps green diamond interior to exterior; boundary weights sum `1+1=2`.
Physical phase factors cancel upon restriction to the corresponding measured
lattice. Reflection about the first/last sample and the periodic seam preserve
parity. These statements support the pre-restoration sample null; they do not
establish arbitrary missing-color values.

The proposal correctly combines both physical green phases, interpolates the
already cell-integrated field without an aperture inverse, and changes no
geometry or source selection. Applying the same max-zero/WB/range preparation
as held MHC isolates this completion change. Preserve the original signed CFA
as well as that actual normalized input. No additional candidate-only clamp,
tone or RGB-to-CFA round trip belongs in the comparison.

Exact restoration of known sites is insufficient commissioning. The old
[CDIFF2 result](../../../docs/research/M95-cdiff.md#43-k11-is-itself-blind-to-the-green-refinement)
showed a broken refinement can preserve every known sample. Require the stated
pre-restoration null and actual missing-site values. For an exact missing-site
oracle, use a small independent direct DFT of the declared extension, or modes
compatible with its finite reflected period. Arbitrary-phase continuous
sinusoids and affine ramps also contain the operator's real boundary mismatch;
their whole-field error must remain visible, without mislabeling it a transform
bug or hiding it with an interior-only score. Impulses at center/edge, physical
phase permutations and the green-square foil exercise different errors.

## The chromatic/neutral ambiguity is unavoidable

A neutral native `(0.30,0)` cosine has the same CFA samples as an alternative
with R at `(0.20,0)`, G at `(0.30,0)` and B at `(0.20,0)` with opposite sign,
after matching the unit-cell sinc amplitudes. R's even x and B's odd x supply
the respective alias signs. Add a sufficiently large positive constant to make
both scenes physically nonnegative. All original measured values, and therefore
their conditional shot/read distributions, coincide. Both interpretations
cannot be recovered by one deterministic final-CFA operator.

This design explicitly chooses independent within-lattice color bands. It can
preserve the current in-band chromatic positives while converting neutral
supra-R/B detail into colored aliases. The two-truth/same-input adverse should
show this tradeoff, not become an impossible requirement to pass both truths.
The complete photograph decides whether that prior helps colored scales at an
unacceptable cost to neutral hairs, glints or fine texture. No noise threshold
or known-site identity can certify the correct interpretation in this example.

## Evidence, noise and boundaries

The [stage audit](../native-spectral-fusion/pilot/analysis/stage-audit-results.md)
is materially stronger evidence for this question than a band-power ranking:
known sites agree within 0.00033004 DN while several identified components
deteriorate at newly inferred sites. It also retains pre-MHC flat penalties,
shared-bin conflict and red alias error. Independent color completion will not
repair those causes. The earlier [M95](../../../docs/research/M95-demosaic.md),
[CDIFF](../../../docs/research/M95-cdiff.md),
[directional actual-photo](../../../docs/research/BUILD-SHARP.md#327-hamilton-adams-already-rejected-before-the-report-arrived-and-v-demosaics-data-strengthens-the-rejection)
and [M104b](../../../docs/research/M104b-demosaic-lever.md#6-verdict) negatives
constrain claims; neither a historical optical cutoff nor one failed recipe
rules out this distinct operator.

The hard frequency mask has global signed tails. Neutral step/glint ringing,
edge-reflection contamination and missing-site noise remain substantive risks.
Known-site restoration must not conceal these. Reuse all saved controls,
including the weak 8-DN green and mixed-depth cases, and retain signed absolute
amplitudes, false components and full RGB error. A lower-only recovery bar can
reward overshoot; quiet chroma can reward erased real color.

There is no justified independent-noise model for the nonlinear fused CFA.
Neither the original source variance nor source variance/299 is its covariance.
The fixed completion is linear conditional on its input, but the input already
carries selection and overlap correlations. The saved noisy-flat comparisons
are empirical effects of this complete fixed recipe, not a calibrated universal
variance guarantee.

## Bounded photographic decision

The memory estimate covers arrays, not the exact FFT workspace. The unusual
13790-by-9190 extension can incur planning/workspace costs that a small fixture
does not predict. One full-field cost must include all three colors, native
writers and peak allocations under the stated budget; a budget refusal must
not silently change extension, precision or masks.

After the active job completes, hold both candidate and uniform CFA masters
byte-identical, reproduce their MHC outputs, then deliver this completion with
the same development. Inspect all complete outputs and all ten fixed witnesses
under the [photographic protocol](prior-photo-constraints.md). This needs no
repeat of 299 source fusions. A null or visibly worse result closes this fixed
recipe; a useful result still needs the separately specified flat and second
insect transfer before a general claim. This review releases no execution and
does not predetermine that photographic verdict.
