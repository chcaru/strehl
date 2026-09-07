# Independent review of the prospective normalized-interval amendment

2026-09-07. **DERIVED / source-reviewed: no blocking design defect found.**
Reviewed `reference-interval-amendment-1.md` at SHA256
`e80af8bc3d549ba021dba16cfea440dda080c542c4fe8cc5c807071b55220848`.
This review calls no numerical helper and grants no numerical admission.

The change of variables is dimensionally consistent. With `w=b-a>0`, the
weighted callback `w*f(a+w*u)` integrates over `[0,1]` in the original
integral's units. Keeping the original absolute request and returning both
integral and indicator unchanged therefore preserves the specified tolerance
convention. The piecewise nearer-endpoint expressions describe the same affine
map in real arithmetic. The prescribed binary64 ordering, explicit endpoint
branches and out-of-domain refusal make the floating-point implementation
reviewable. Repeated represented coordinates can still occur; normalization
does not prove that their integrand samples approximate a continuous model
accurately. The complete independent comparisons remain necessary.

The direct controls have power at the stated choices. Interval B has width
one half, so an omitted or repeated Jacobian changes the nonzero constant
integral. On interval C, the affine integrand changes under a left-half map;
the quadratic distinguishes a midpoint replacement from integration. Constant
and affine integrands alone cannot reject that midpoint replacement, which the
amendment now explicitly acknowledges. Exact rational endpoint/monomial
oracles avoid deriving truth from the new map. Both endpoint slivers and the
signed integrand remain software integration controls, not radiance scenes.

The actual delegated-kwargs check is essential: polynomial accuracy cannot
reliably establish correct `epsabs` scaling. On the unequal widths B and C,
`e/w` and `e*w` differ from the released request and must fail that consumer
contract independently of scalar accuracy. Warning propagation is checked
through the frozen refusal guard, with the sentinel warning and restoration
named explicitly. The original geometry-004 refusal remains a required
historical control rather than a silently removed case.

The dependency-isolation fault is also powered by the existing source.
`independent-reference.py::integrate_factor('disc',...)` uses `[0,pi/2]`;
accidentally wrapping it with the Cartesian adapter must refuse its domain.
The correctly scoped installation leaves that actual factor call unchanged.
Both dependency identities must be restored even on exceptional paths.

The v2 method and closed normalization object give the consumer concrete
checks. Returned numerical/point intervals must match the frozen receipt and
engine difference; callback counts must match both the engine difference and
actual chord-evaluation work. Analytic rows retain zero normalization/chord
deltas while permitting factor work. Refusals may retain partial work and must
not claim a completed receipt. These are mandatory accounting counters,
distinct from optional observer hooks and collection. Boolean/float counter
aliases, false targets, stale v1 identifiers, missing/unknown fields and
coherently changed deltas will be exercised in the existing private driver.

The final shared-budget clarification closes a real implementation pitfall:
direct test callbacks must charge the common budget, whereas frozen Cartesian
callbacks already do so and must not be charged again. The per-engine
normalization counters may restart with a new engine; the component resource
budget may not. The new adapter and amendment must be in the exercised source
map and snapshots as well as the root release. A release's broad source union
does not replace checking actual dependencies.

The integration plan is appropriately bounded: preserve the catalog and all
numerical bars, run both complete numerical batches from the final shared
source snapshot, refresh the 145 existing private checks plus the narrow v2
metadata controls, and then execute the complete reader on externally pinned
fresh results. Previously chosen metadata companions remain geometry-060 in
both arms, transfer-small-full primary and joint-relative-sign-point refined.
No source, input, method, limit or result was modified by this review. The
original 28 refusals and diagnostic are historical evidence; a successful new
method would not retroactively pass them or establish physical optics, image
quality or full-array admission.

The reviewed sources were the amendment, the diagnostic review, frozen
`independent-model.py::render` (split construction, `quad` call and final
division/indicator gate), `independent-reference.py::Engine`,
`integrate_factor`, `Budget` and `source_map`, and the current strict reader's
`reference_row`, `source_closure` and `verify_controls`. Reads used
`Get-Content`, `rg` and `Get-FileHash`; no runtime imports or quadrature ran.
