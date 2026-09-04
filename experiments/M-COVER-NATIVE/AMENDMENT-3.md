# M-COVER-NATIVE Amendment 3 — overlap denominator

## Question

Scorecard section 1.5 says:

> Crops are fixed from the common-input overlap before outputs exist. Retained
> field of view must be `>=99.0%` of that overlap.

This amendment determines whether “that overlap” is:

- the spatial region jointly covered by the common input frames; or
- the original/native active-image array.

It also checks the already-recorded `109MSDCF` arithmetic and establishes why
that lane's `3516 x 2344` plane differs from this lane's `7032 x 4688` output.
No RAW, TIFF pixel payload, renderer, alignment solve, or border instrument is
run.

## Frozen source reading

The adjudication reads the current scorecard's complete common-input,
native-output, and geometry passages:

- lines 134–145: run freeze and output-independent site selection;
- lines 149–171: one common linear input;
- lines 173–179: native-size output and 1:1 visual crops;
- lines 223–235: geometry and exclusions.

It searches the whole scorecard for every use of `common-input overlap`,
`overlap`, `native active-image dimensions`, and `native-size`. A formal
definition elsewhere in the scorecard that supplies a reference gauge,
registration transform, support margin, or overlap-construction algorithm
falsifies the “operationally undefined” conclusion.

The arithmetic inputs are transcribed from the closed, read-only
`cover-default.md`:

- original binned plane: `3516 x 2344`;
- bare 109 Crop: `3470 x 2312`;
- post-256-px-inset rectangle: `2958 x 1800`.

The checker recomputes bare/original, inset/original, and inset/bare area
fractions directly from those integers. These are derived arithmetic, not new
measurements.

## Predeclared interpretation

1. Grammatically, “that overlap” takes the immediately preceding
   `common-input overlap` as its antecedent. The original array is not named as
   the denominator in section 1.5.
2. Section 1.2's native-size common TIFFs and section 1.3's native-size outputs
   are separate requirements. They do not silently redefine “overlap” as the
   original array.
3. A candidate's own alignment-dependent Crop rectangle cannot define both the
   denominator and numerator. That would not be common across methods, would
   not be fixed independently of the candidate output, and would recreate
   generator/checker cancellation.
4. If the scorecard does not specify how to obtain the common-input overlap
   rectangle, the grammatical denominator is Reading A but the formal
   per-stack result is `UNMEASURED_DENOMINATOR_UNDEFINED`, not PASS or FAIL.
5. Conditional arithmetic may still be reported:
   - if an independently frozen overlap equals bare Crop, bare retention is
     `100%`;
   - the 256 px inset retains `2958*1800/(3470*2312)` of that overlap;
   - using the original plane instead yields
     `3470*2312/(3516*2344)`, but that is not the scorecard denominator unless
     the registrar says so explicitly.

## Representation and stack dependence

The `3516 x 2344` plane is expected to be the default binned output: each
dimension is exactly half of `7032 x 4688`, and the COVER commands omit
`--demosaic`. `STREHL_FULLRES_GATHER=1` governs the warp source, not the output
sampling grid.

The emitted Crop fraction remains per-stack because its coverage rectangle is
derived from that stack's frozen alignment placements. No `109MSDCF` fraction
is transferred to the eight M1/M2 renders.
