# Proposed numerical implementation release after complete cost admission

2026-09-07, root. **Design only; cost admission has not occurred.** This resolves
the remaining author resource and payload choices before implementation. It
does not authorize radiance execution, a full expected-image run or a consumer.

Retain the150 literal cases in next-component-population.json at
4344d04234e3d0849c4cccdc5cf0af4347dec5f2133c680e145f0288bff82a45 and the
independent reference plan at685d1b5b7d7780c7dc7e9469b4be472b66c9d0ca4716c27de5579e0a303d2151.
Accept the proposed author component batch allowance:16million actual point
calls,2.4billion angular nodes,600CPU/1200wall seconds and32MiB tracked arrays,
including cache setup, all enabled/disabled/mutated/restored component calls and
the observer population below. This is one global batch allowance, not one per
case. Keep angular depth10, cell depth6 and32768 simultaneous node pairs.
The independent component batch keeps its separately proposed30million actual
integrand calls/600CPU/1200wall limit. Those budgets are engineering choices,
not guarantees that the commissioning workload completes.

## Small observer and traversal population

Fix one9×6 native grid with the independent private counter geometry:
depths(1,2), normal(1,.25), offset2, scale2/rotation0/centre(.5,-.5)/
translation(1.25,-.75), K2, indices0..4 and foci(.5,.75,1,1.25,1.5).
Use the two textured fields from the intended M194g fixture, explicitly
replacing the geometry-only private counter's unused constants. This is a
separately declared numerical-control input, not the same optical scene as
that geometry-only record. Run all three arms; require actual foreground,
background, numerical branches, signed/zero defocus and nonzero wave-transfer
work to be reached. No sensor/noise/CFA conversion is performed.

Use four fixed executions under the same global author component budget:
off row-major, count row-major, placebo row-major, and count reverse-row-major.
Reverse the complete cell sequence, not only rows. Require each one's full
scalar, branch and sorted fallback diagnostic payloads to be byte-identical.
Mode-dependent counters, hook receipts, timing and ordered traversal digest
are separate. Count/placebo hooks must execute, with actual collection only
in count. Use one actual scalar change and one omitted/duplicated coordinate
as powered failures of the consuming equality/coverage checks. These are
instrument controls, not a timing sweep or a full-image quality comparison.

## Successful-frame payload

Use a new M194g schema, not an M194e certificate. Keep one current scalar
frame and bounded scratch. A complete frame has:

- scalar little-endian f64[height,width], all finite and covered;
- branch u8[height,width] with explicit foreground/background/numerical codes;
- sorted unique native linear indices little-endian u32[N], exactly the sites
  whose branch is numerical;
- finite fallback diagnostics little-endian f64[N,4], ordered as
  value_error_indicator_e, cell_indicator_e, weighted_high_pupil_indicator_e,
  cell_quadrature_delta_e from the actual unchanged fallback receipt.

Analytic sites have no fallback diagnostic row and no fictitious zero adaptive
indicator. Their method/finite-arithmetic scope is recorded separately, and
every analytic scalar still faces the external whole-image comparison. Sort
sparse diagnostics by native index before writing so traversal order does not
change the payload. Mandatory numerical payloads exist in every observer mode.
Incomplete frames retain explicit partial state and cannot satisfy these
success requirements. Shape, dtype, all indices/branches and finite masks are
checked by the actual consumer, with live value/coverage/source mutations.

Freeze one JSON-normalized input representation before both persistence and
comparison. Constructor tuples may remain implementation details; comparing a
serialized JSON list directly with a live tuple repeats the stopped profile's
defect. Require a literal re-opened valid companion and a changed-field refusal
on the actual boundary before trusting intended manifests.

The author may use SciPy j1 for the full-disc branch, with canonical-radian
frequency transformed by M transpose and both native square factors. The
independent reference uses its spatial integral and different conservative
selector, never that j1 primitive or the author's cached factors. Keep the
frozen M194e numerical fallback/source and global-error allocation unchanged.
No numerical sharing removes the independent component and complete-array
comparisons. Retain a failed or inert destroyer without retuning its input.

After complete cost admission, independently review and commit this resolved
specification plus the literal component catalog before author/reference
implementation. Commit both implementations and exact component commands before
running their batch. Only complete independent component/observer/reader passes
release the separately committed all15 author images and both five-frame
reference arms under the original fixed bars and per-arm resources. An apparent
constant/interior success cannot admit missing boundary work.
