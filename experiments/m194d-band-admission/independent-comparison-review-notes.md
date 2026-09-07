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

## Sparse component commissioning

**VERIFIED, pure component scope.** The final `sparse-error.py` at SHA-256
`cdceca7a9232489223dc9395f2131d02642d365b111850d7caa4addb742169cd`
passes ten numerical, null and power checks plus sixteen malformed-input
refusals. `independent-sparse-controls.json` records all 26 results and
unchanged subject bytes. Exact command, from the repository root:

```powershell
python -B experiments/m194d-band-admission/independent-sparse-controls.py > experiments/m194d-band-admission/independent-sparse-controls.log 2>&1
```

The independent script chooses a 4-by-7 RGB array with eight irregularly
masked sites, nonconstant truth, signed residuals and ties. Decreasing native
x coordinates distinguish first row-major tie handling from choosing the
smallest coordinate. Fraction-based interpolation of manually sorted lists
checks the declared linear quantiles without calling NumPy's quantile as its
oracle. The red p99.9 is 22.916 DN by linear interpolation and 23 DN by the
separately declared nearest-rank description. This is the expected convention
difference, not an instrument failure.

The live choices also distinguish movement from harm: a 60 DN movement from
signed error +30 to -30 has exactly zero absolute-error change; moving one
20 DN isolated error to another site leaves the marginal error distribution
unchanged but exposes the new harmed site. The same-output companion is
exactly zero. All-improving and all-worsening arms preserve the signed meaning
of their extrema. Values and coordinates outside the mask are deliberately
inert; the inputs remain unchanged.

The initial helper passed all ten ordinary-domain checks but silently
accepted complex RGB, complex coordinates, an integer-valued coordinate
outside int64, finite inputs whose residual overflowed, and finite paired
residuals whose output movement overflowed. The first run contained fifteen
malformed cases; the paired-overflow companion was added before the final
sixteen-case rerun. Both failed receipts and logs are retained as
`independent-sparse-controls-first.*` and
`independent-sparse-controls-before-hardening.*`, with the original helper
saved in `independent-sparse-subject-first.py`. Its SHA-256 is
`1da7c8835f43d407243adccb60f23914b2052c36fb5d0e112bc291d0e8d3a749`.
These five findings concern malformed values outside the bounded u16 image
and small canonical-coordinate domain; they do not refute an image result.
Root repaired refusal checks before any scored image output, preserving the
normal arithmetic, quantile and tie conventions. The final sixteen cases all
refuse. No product code or threshold was changed by this review.

## Concrete outer controller review

**VERIFIED source contracts; runtime execution remains pending.** The final
pre-build review finds no additional design blocker in `run-experiment.py`
and `compare-experiment.py`. The inexpensive source-set read is retained in
`independent-adapter-source-review.json`, including the six actual adapter
hashes reviewed. Calling `fixed_sources()`, `frozen_artifacts()` and
`validate_external_includes(consumer.sources())` succeeds against the current
tree. The latter resolves explicit includes using the including crate root
and requires the reached external Rust set to match the attested set. It is
an explicit-form check for this source tree, not a general Rust dependency
parser.

The controller now pins prospective documents to commit
`5f55c9ee7dc15d47e04ded53cd11eea929e28fc2`, fixed M194b artifacts to
`444eb759`, and reused M194c comparison/controller functions to `04128e`.
Both mode indices must reference the same build and original producer
artifacts. The complete current source map and archived snapshots are checked;
source checks surround each child invocation. The comparator reopens bound
indices, replays each actual-TIFF score, checks the exact five outer child
commands and their terminal logs, and requires all forty explicit hard-floor
TIFFs and decoded pixel arrays to equal the committed M194c outputs before it
returns candidate comparisons.

The versioned score reader calls the unchanged M194b numerical functions and
adds `SP.summarize` only after actual TIFF, manifest, plan, crop and output
interpretation validation. `SP.compare` receives actual candidate and baseline
pixels under the same target and mask. Its signed error change is candidate
minus baseline absolute truth error; paired temporal statistics use the
unchanged `S.paired_error` with an explicit across-mode direction. Neither
the added summaries nor a mode label substitutes for actual output
verification. The build-backed mode/schema/environment/source refusals and
the planned 120 actual TIFF reads remain pending; no image-quality or default
claim follows from this source review.

## Bounded runtime mode verification

**VERIFIED, first execution:** `independent-mode-controls.py` passes 46 checks
across 29 subprocesses. It generates three actual TIFFs and exercises 22
refusal cases. Command:

```powershell
python -B experiments/m194d-band-admission/independent-mode-controls.py --build-record experiments/m194d-band-admission/author-run-2/versioned-cli-build.json --build-sha256 973a0fb48edb88d52b9a6e1037e0fc75e58c495af1aa0e1e9f8e74ca8f2005b0 --out experiments/m194d-band-admission/independent-mode-run-1 > experiments/m194d-band-admission/independent-mode-run-1.log 2>&1
```

The independently chosen case is the existing `flat/seed-709/full9`. Both
actual admission modes produce the expected versioned plan and receipt. The
explicit hard-floor TIFF matches its committed M194c counterpart byte for
byte, and a second hard-floor render is the exact byte null. The candidate
changes 151,028 image components, with maximum movement 530 TIFF LSB. This is
positive evidence that the mode reaches the delivered pixels, not a finding
that those changes improve truth error.

The valid direct-child plan matches the driver's plan. A valid driver plan
also remains identical when its parent environment contains the opposite
admission value and an unrelated gate override: the driver clears them and
sets its declared values. Exact child argv, environment, build digest,
terminal log, manifest and plan bindings are checked for the successful
driver calls. Independent TIFF decoding verifies u16 RGB dimensions and
pixel hashes, while receipts report the nine original input indices and one
decode each.

All 22 negative cases refuse without producing their target output. They
cover missing/invalid admission, missing/wrong required settings, an
unexpected gate setting, the forbidden white-floor diagnostic, a valid
off-plan used by the on-mode, and rehashed plan edits to schema, admission,
formula, type, unknown field, gate and coherently shifted crop/offset. A
duplicate schema key also refuses. Private rehashed build records omitting
the core operator or the included independent consumer test refuse; a
record pointing at the real historical executable cannot satisfy the new
test execution. The latter is a functional driver refusal, not an assertion
that a digest authenticates arbitrarily forged compiler history.

The final result is `independent-mode-run-1/result.json`, SHA-256
`fa91ecc03f506bd25eaf2c0d113e00bc17331c5f4dd6e7c6744b26f5dc5418b4`.
It records the script SHA-256
`f5b4e9e9779ff5add9d7a26f2a7e15c2508ef6fdcf9e6c8ba6b6a54d55a6c873`
and the copied executable SHA-256
`8fe0f83b263424338c704388dfe20219a6ae77ac607ad1e12300d5d4a3bbe46c`.
The compiler artifact matched that copy, and its bound log contains
`Compiling strehl-cli`. All 106 compiler-input bindings and the ten input
files (nine CFA files plus manifest) remain unchanged. Raw child logs and
every private mutant are retained. No test assumption or product change was
needed after the first runtime execution.

These checks clear the mode plumbing for the fixed complete experiment.
They do not replace the forty off-mode identity checks, the paired quality
comparison, or the downstream receipt/index admission controls. Those still
await the complete outer package. Ordinary default-call coverage is Curie's
separate responsibility; explicit hard-floor execution alone is not that
claim.
