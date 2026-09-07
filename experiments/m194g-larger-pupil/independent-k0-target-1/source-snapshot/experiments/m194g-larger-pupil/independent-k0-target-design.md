# Independent K=0 target verification design

2026-09-07. Root-authorized source/design preparation, before any quadrature,
array read or private control execution. The target interface is
`next-quality-target-interface.md` and its fixed ten native centres are
(142,0),(142,1),(143,7),(150,53),(151,64),(152,64),(159,117),(160,117),
(169,179),(178,239). No cell may be dropped or replaced after seeing results.

The comparison is max absolute discrepancy<=0.004 electrons and
RMS<=0.0008 electrons across all ten actual target-array entries. This verifies
the target's K=0 cell integration at those sites; it does not independently
integrate the whole76800-cell array or admit production quality. The actual
array is read completely for bounded storage, exact dtype/shape/hash and
finite/nonnegative values. Original target data are never replaced by these
independent values.

## Different integration choice

Use only the explicit fixture field coefficients, not polygon, moment,
Fourier-polygon, hybrid, pupil or author-target helpers. The fixed primary
geometry is the identity native grid and foreground half-plane
`x-.15*y>=142`. At each y within the unit sensor cell, the foreground interval
starts at the clipped crossing `x=142+.15*y`; the background is its complement.
Integrate each field in x analytically. An affine field contributes interval
width times its value at the interval midpoint. Each actual cosine wave
contributes
`A*width*sinc(pi*fx*width)*cos(2*pi*(fx*midpoint+fy*y)+phase)`.
The zero-frequency sinc limit is1. Sum the two separately restricted field
integrals, never their independently averaged alpha/colour.

Then use independent `scipy.integrate.quad` over y, splitting at every interior
y where the boundary crosses either x edge of the cell. Allocate a total
absolute request1e-7 electrons per cell equally over the resulting positive
length intervals; epsrel0, limit128. Inspect the actual full-output status,
finite value/nonnegative error indicator, per-interval request and summed
indicator. Any warning, extra failure message, exception or indicator above
its allocation refuses. Every callback checks the shared stage budget; actual
callback counts and reported neval are retained. This is an adaptive numerical
indicator, not a rigorous enclosure of floating arithmetic error.

## Independent private oracles and live faults

Before target comparison, evaluate these re-chosen literal cases at centre(0,0):

- Fully foreground constant30 and fully background affine10+4x give30 and10.
- Foreground30, background10+4x, vertical visibility x>=.1 give17.52 exactly.
  Reversing the background slope gives18.48. This rechooses the mask from the
  producer's .125 vertical witness.
- Foreground30, background10+4x, diagonal visibility x+y>=0 give59/3. The
  excluded foreground triangle's x moment is1/12.
- A fully visible wave `100+7*cos(2*pi*(.125*x+.0625*y)+.3)` is compared with
  the direct rectangular-cell transfer using the two scalar sinc factors.
  A second wave has x frequency1.5, powering the negative sinc lobe; a zero
  x-frequency companion powers that branch. These check this verifier's
  interval formula rather than reuse the producer's polygon integral.

Constant/affine discrepancies must be<=1e-8 electrons; Fourier controls<=1e-7.
The same actual integration function executes named faults: shift native x by1
on the nonconstant fully visible wave; select the whole-cell layer using only
the centre mask (vertical witness returns10); omit alpha weighting (vertical
witness returns40); separately average alpha and complete-layer radiance
(vertical witness returns18). Each active result must be finite, warning-free
and differ from the correct baseline by>0.004 electrons. The restored call
must recover the exact f64 baseline bytes. An unrelated exception or a failed
indicator does not count as fault power.

Retain per-interval records for every baseline, fault and restored call. The
diagonal/vertical witnesses check actual branch occurrence; at least one fixed
scene comparison must exercise an interior y split. The test cannot infer
that property solely from a mask label.

There are eight literal oracles and four active/restored fault groups, using
20 actual cell integrations before the ten target cells. Each attempted call
and interval is attached to the result before invoking quadrature, so a warning
or exception preserves completed pieces, callback counts and the original error.

## Reader, release and resource boundaries

The new `independent-k0-target.py` accepts externally pinned target.json and
full-float authority, plus an exact execution release with scope
`independent-k0-target`, schema `m194g-numerical-execution-release-v1`.
Only the already commissioned independent file/NPY
and resource utilities are reused, loaded from exact source bytes after the
external release gate. No producer or optical module is imported. The target
receipt must match the accepted interface, genuine complete float/fixture
association, geometry, actual scalar ref and complete unchanged source maps.
All released supplemental inputs remain in the same live read ledger through
terminal persistence. Output references are repository-relative.

The target's separate `m194g-quality-execution-release-v1` has scope `target`.
Reopen its complete sources, original source snapshots and released inputs;
require the fixed fixture/full-float refs in that input list. Its actual
orig_argv must match its released command, argv must be the actual script
suffix, and its release, full-float and output arguments must identify the
receipt being checked. Check the exact 16 ordered local control IDs and typed
work/runtime fields from the accepted target interface. These recorded local
checks remain producer evidence, separate from this verifier's private oracles.
The exact five Python dependencies are target, quality-io, quality-metrics,
software-noise-authority and the frozen M194e independent-model; protocol
documents are release inputs, not executable source-map entries. Require the
target interface/preregister and full-float schema among those released inputs.
The first static adapter draft put two protocol documents in the source-map
requirement; Curie's metadata review caught that mismatch before any import or
execution. The original AST-only record is retained and the corrected source
has a separate AST-only record. No mathematical stimulus or bar changed.

One non-resetting120 CPU/240 wall-second budget begins before imports and
includes private controls, source snapshots, target reading, all ten values
and finalization. Named live ndarray backing storage<=32MiB, total output
<=16MiB. No full image is generated by this verifier. Refusals preserve the
original exception and any secondary source/persistence failure. An actual
failed target or private control leaves status UNCOMMISSIONED_K0_TARGET.
The live ndarray ledger also registers the actual QUADPACK information arrays;
this named-array scope is not process RSS or a general SciPy allocation profiler.

Source and exact original interpreter argv are committed before execution;
there are no unknown future-output placeholders apart from the existing
external release's own SHA substitution. The actual target path/hash will be
supplied when the target exists. Independent result status
PASS_TEN_CELL_K0_TARGET names this limited comparison, not a quality pass.

## Concrete command and result

The command is `independent-k0-target.py --target PATH --target-sha256 SHA
--float-commission PATH --float-commission-sha256 SHA --execution-release PATH
--execution-release-sha256 SHA --output NEWDIR`, under root's exact frozen
interpreter argv and fresh cache prefix. No command has been run at this source
preparation stage.

`result.json` has schema `m194g-independent-k0-target-verification-v1` and exact
fields schema/status/method/scope/invocation/target/float_commission/scalar/
execution_release/source_before/source_after/input_bindings/controls/cells/
maximum_error_e/rms_error_e/runtime/work/error/finalization_errors. Target,
float_commission and execution_release are repository FileRefs; scalar is the
original target's repository ArrayRef. Every cell row has native_xy, target_e,
independent and signed_error_e. The independent receipt retains evaluated_xy,
fault, value_e, indicator_e, absolute_request_e, y_breaks, every piece,
callback_calls and branch_calls. A failed attempt can retain null scalar values
and partial pieces; only complete success has all ten finite signed errors and
the two fixed comparison bars. Work is the commissioned reader Budget receipt,
with final checks after persistence; it is not a process-exit measurement.
