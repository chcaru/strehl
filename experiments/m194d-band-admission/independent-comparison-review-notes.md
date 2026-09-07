# M194d pre-freeze comparison-adapter review

2026-09-07, `roadmap_audit`. Read-only review of root's comparison
preregistration, `consumer-run.py`, `run-matrix.py`, `adapter-lineage.json`, and
the initial `score-benchmark.py` as it became available. No build, image
execution, measurement or independent control implementation was performed.
This is a design/source review, not commissioning or acceptance of outputs.

## Necessary corrections found and their disposition

1. **Overbroad Python source freeze, corrected before output.** Initial
   `run-matrix.py` inserted every `HERE.glob("*.py")` member into the frozen
   source map. That needlessly included independent review/control code and
   would prevent its normal development during the campaign. The corrected
   code names exactly `consumer-run.py`, `run-matrix.py`, `score-benchmark.py`,
   `run-experiment.py`, `compare-experiment.py` and `sparse-error.py`. Required
   production/test sources remain bound separately. I read the corrected list;
   no controller/source-control run has yet exercised it.

2. **Every-invocation provenance claim lacked its guard, corrected before
   output.** The preregistration requires frozen source bytes around each
   invocation. Initially the matrix checked the full map only at start/end,
   while the child driver checked compiled inputs only before launching the
   native process. The corrected `run-matrix.py::invoke` calls `check_sources`
   immediately before the child and after recording its terminal result.
   This covers compiled, producer and explicit adapter map members, and retains
   the child record if the post-check fails. I read those actual calls.

Both findings preceded candidate output. They should remain recorded as
pre-freeze corrections rather than failed imaging results. The full eighty
output controller still needs to bind the same source/build settings across
both separately sealed forty-output mode indices.

## Coherent parts and lineage check

The proposed runtime enum and required mode string are explicit. The child
driver starts from a cleared STREHL environment, adds
`STREHL_M194D_ADMISSION`, and records that actual environment and new child
entrypoint in its command witness. Reusing the existing `STREHL_M194B_*`
input/plan/action variable names does not hide the new operator: the new
admission variable and M194d schema are separately required. The original
M194b entry remains a distinct interface.

The matrix preserves the fixed twenty cases and two frame-subset arms per
case. All twenty plans precede that mode's first output. Every invocation uses
one bound build and the exact mode argument. Failed native commands retain
their logs and make the mode index failed. These are appropriate local
properties; they do not alone establish same-binary identity across both mode
runs or off-mode identity with committed M194c.

The initial M194d reader imports the unchanged numerical `score.py` from its
original M194b path. It constructs a full exact configuration for each mode,
including `admission` and `admission_formula`, and a full exact environment.
Those values are checked against the parsed plan, indexed mode, parent argv
and actual child witness. Its required source set adds the new child and
core `pyramid.rs`; its build argv, child entry, plan/receipt/index/result
schemas and source paths explicitly identify M194d. The actual CFA/TIFF reads,
crop/gauge checks, target construction and numerical reductions are retained.
This is an honest versioned adapter rather than a candidate projected into a
false legacy record.

Static lineage replay used the three original source byte streams, normalized
CRLF to LF for text editing, and applied each listed replacement only after
checking its declared occurrence count. For consumer, matrix and initial
reader, all source SHA-256 values, replacement counts and recorded
`initial_destination_sha256` values matched. At that inspection the current
consumer/reader were their initial versions; the matrix had the two disclosed
follow-up repairs above. The `initial_*` names correctly describe origin,
not a final source freeze. The final source map must additionally bind the
actual final files and the lineage record. Do not rewrite initial hashes to
pretend those later edits occurred in the initial copy.

## Quantile conventions and independent choice

Root explicitly chooses NumPy's linear p99/p99.9 quantiles; my independent
design preregisters nearest-rank p99.9. Both are legitimate descriptive
statistics, with different behavior on sparse tails. This is not a numerical
contradiction or an added quality bar. Once root's sparse module is available,
I will check its linear interpolation against manually chosen small sorted
lists and retain nearest-rank as an explicitly separate independent read.
The expected convention difference must not be labelled a reader failure.

Root's signed extrema, maximum absolute error, paired absolute-error increase/
decrease, and largest movement with its signed truth-error change correctly
separate movement from harm. The independent fixed >10 DN adverse/improved
counts and the historical site trace supplement these diagnostics; they do
not replace the full fixed-ROI read or tune an acceptance cutoff.

## Concrete remaining checks after freeze

- The final Rust child must produce the exact new schemas/configuration/mode
  witnessed here; missing/malformed mode and mode/plan/receipt disagreement
  must refuse even with recomputed outer hashes. These bindings cannot be
  commissioned from Python source alone.
- Freeze the complete exact source set, including untracked core/CLI additions
  and actually included external tests. Resolve an include's
  `CARGO_MANIFEST_DIR` from its own crate; M194c's CLI-only resolver must not
  silently resolve a core include as a CLI file. An explicit known set is
  sufficient; no new general dependency framework is needed.
- The outer experiment record must bind both mode indices to the same actual
  compiled/copied binary, original producer/commission references and source
  freeze, then require all forty off-mode TIFFs to match the archived M194c
  forty outputs before interpreting candidate quality. Parsed plans may differ
  only in declared mode/configuration/schema/build context; image input,
  geometry, noise, output interpretation and score masks stay fixed.
- Keep the distinction between explicit hard-floor execution and a default
  call. Curie's direct default-resolution tests plus complete off-mode image
  identity cover the intended default claim; a JSON label alone does not.
- Commission only the changed source/mode/schema boundaries and new sparse
  arithmetic. Reuse the unchanged TIFF/geometry/numerical commissioning where
  its contracts apply. A genuine bad candidate output remains an observed
  product failure even if the strict reader refuses to issue a normal score;
  it must not become a refutation caused by an unrelated instrument failure.

No additional pre-freeze design blocker was found in these initial adapter
interfaces after the two corrections. This statement does not assert the
unfinished joint controller or future Rust implementation has passed tests.
