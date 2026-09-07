# Independent interval adapter source review

2026-09-07. **VERIFIED by source inspection only:** no blocking integration
defect found in the four files below. This does not admit numerical values or
predict that the complete component population will pass. No module import,
quadrature call or numerical control was executed by this review.

| File | SHA256 |
| --- | --- |
| independent-normalized-interval.py | 0db00d10d31af75818187542470b455be863b39d834cb0f95f8d2f2281c9df52 |
| independent-normalized-interval-controls.py | 58d232029bc6a79ed36625899fe8d5e952d96447894c2c37e0b2a5a24d81d27b |
| independent-reference.py | ae217b3b6587eb1b1db0cbf86060ae7f0bf3df34098af18eb4212c2b3d4981cc |
| independent-reference-components.py | 7512692df1be164b35edcb2b22e0ccbe0afc2c6c8fdae0fd494a175b9def78ad |

The governing amendment is the prospective `1477e677` revision, exact document
SHA `e80af8bc3d549ba021dba16cfea440dda080c542c4fe8cc5c807071b55220848`.
The earlier independent amendment review remains the mathematical design
review. This pass examines the actual implementation and downstream consumer.

`Normalizer.quad` maps the original interval onto [0,1] using the prescribed
nearest-endpoint binary64 operations, multiplies the callback by the width,
and passes the unchanged absolute request, zero relative request and limit128
to the captured dependency. It returns the integral/error pair without another
width multiplication. `installed` refuses nested installation on the same
module and restores the original dependency in `finally`; it does not suppress
the frozen caller's warning guard. These facts establish implementation
correspondence, not accurate integration of all tiny endpoint intervals.

`Engine.render` installs the adapter only around the frozen Cartesian render.
The separate factor quadrature remains outside that scope. It records the v2
row/engine method and closed normalization records, retaining the explicitly
named old Cartesian integrand method inside numerical receipts. Per-call
counter deltas are recorded separately from cumulative engine counters and
optional observer collection. The actual source map includes the adapter,
direct controls and amendment. The component controller loads the controls
from that checked map, invokes them with the existing cumulative budget and
refuses before the ordinary population if their complete status is absent.

The direct controls preserve 24 polynomial/interval pairs in each of
off/count/placebo modes. Direct callbacks charge the actual shared evaluation
budget; the adapter itself does not add a second resource tick to callbacks
already charged by the frozen render. Active scalar controls change the
Jacobian or interpolation, and restored calls must match original signatures.
Tolerance faults inspect the actual delegated request; polynomial accuracy is
explicitly insufficient to prove those faults occurred. Warning suppression,
the wrong dependency, wrapping both dependencies, callback/quad exceptions
and the original geometry004 refusal have specific witnesses and restored
companions. The eleven group names match the independent consumer contract.

Root identified a pre-execution fault-power weakness in an earlier draft:
generic numerical/delegation failure could stand in for the intended defect.
The reviewed version instead requires a finite value without an exception and
an actual rational scalar discrepancy above the fixed limit, or a bitwise
changed delegated request with callback/finite-value witnesses. This was a
static correction; it is not an observed failed numerical control.

The independent reader now interprets the actual 72 direct records and 12
fault records rather than relying on their booleans. Its polynomial oracle is
derived from the fixed endpoints and coefficients using rational arithmetic.
It rechecks fixed limits, actual delegation, callback accounting, count-mode
sample hashes and restored signatures. Ten additional private controls will
challenge this interpretation using externally pinned genuine reference
records; they do not fabricate successful optical authority. The final current
consumer source pins and expected193 private controls are recorded in
`independent-component-static-check-3.json` and
`independent-component-v2-implementation-notes.md`. Those are syntax-only and
prospective counts until the exact released commands run.

The fresh numerical batches were launched by root separately from these
unexecuted consumer edits. Their complete results still need externally pinned
independent reading. Earlier author-only success and the failed v1 reference
remain historical evidence, not a substitute for the new complete comparison.
