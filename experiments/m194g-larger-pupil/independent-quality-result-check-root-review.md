# Root review of the final independent result checker

2026-09-07. Source review only; no independent numerical execution yet.
Reviewed verifier SHA256
`6c69efa777efccca740901edac9e633deb9a16f3dbe539d66c4e6337994e8539`
(50,432 bytes), design
`0a6efc5a3266f4c0b1cd9b3f35ea7927a7106ec5dd3dc6abdc9dcf2878ff1b2e`,
and preparation record
`c7b952414059d215ce0a77b7b90556880dc5007382cbf593f1e054a4952baa4f`.
The independent author is Socrates; the original quality scorer was Curie's.

Source inspection covered the full parser, file/source binding and finalization,
private controls, batch statistics, reference and population choices, sparse
native coordinates, wave fitting, error comparison and command entry point.
The exact original first `individual_errors` row was opened to check the actual
saved schema, rather than relying on the proposed interface.

The deciding choices are independently implemented: classic TIFF parsing,
first-repeat-centered batch variance instead of the original online reduction,
dot-product errors, matched whole-repeat deletions, and a fresh native-coordinate
least-squares wave design. It retains the fixed published input population and
references; changing those would answer a different question. Private failures
exercise erroneous TIFF interpretation, spatial-versus-temporal variation,
individual errors before paired cancellation, missing sparse outliers and lost
wave amplitude/native phase. Flat controls precede the textured private fit.

Root's earlier static findings and their corrections are preserved in the
preparation record. The final amendment checks all 864 individual-error rows,
including noise-off values, and supplies actual arrays through the same error
helper in the paired uncertainty control. Defined phase comparisons remove the
raw phase from generic comparisons before checking the wrapped difference.
Mean-image coordinate alternatives require the originally reported site to
attain the same maximum within the fixed numerical tolerance; individual output
coordinates remain exact.

Scope and failure directions remain explicit. This can reject a decoder,
statistical calculation, population or reference inconsistency with the fixed
diagnostics. It cannot validate physical noise calibration, representativeness,
the optical target beyond its existing independently checked scope, an absolute
quality threshold, or a SOTA claim. The decomposition identity is arithmetic;
own-noise-off is a nuisance reference. An unchanged fixed-input bias may survive
both implementations. These are limits, not reasons to move the registered bars.

The 32 MiB memory ceiling is for registered live ndarray backing allocations,
not total NumPy temporaries or process RSS. All actual images are bounded before
the independent parser allocates, and no repeat-image volume is retained. One
clock includes private controls, genuine calculations and finalization. The
source/input/output closures are checked again at publication. Any first actual
failure must be preserved in its fresh output directory and diagnosed before an
amendment. This review permits only the committed fresh-command execution of
the checker; it does not promote the candidate or change product defaults.
