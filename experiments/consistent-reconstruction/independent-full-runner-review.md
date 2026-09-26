# Independent full-runner source review

2026-09-25. Reviewer: `opal_headroom`, independent of the root-authored
`full-run.py`. This reviewer authored the numerical operator, so this note
does **not** verify that operator or accept its results. Scope is runner,
data-binding, cache and refusal handling only. No builds, tests, RAW reads or
renders were executed by this reviewer.

**Found and fixed before execution:** the initial validator expected seven
stored levels per plane and 28 coefficient-cache rows. The fixed production
configuration has seven AC bands **plus** the terminal Gaussian base: eight
levels and 32 rows. For crop 3250x2166 the last two sizes are 51x34 and 26x17.
The initial validator would have rejected a valid completed full observation.
Root corrected the target lengths, size loop, row count and `divmod` stride to
eight. A subsequent source read confirmed all four changes and the added
`cleanup_errors` checks before root's build-2.

No further concrete source-level blocker was found in the reviewed contract:

- The immutable generated runner is extended with explicit required full-run
  dependencies before compilation. Sources and executable are rechecked;
  fresh controls must retain the historical screen byte-for-byte. Failed
  general preservation and photographic admission remain false. Full execution
  requires the separate explicit observation flag.
- The recipe binds all 299 ordered inputs, map, reference, crop and retained
  production baseline. The adapter validates original file hashes before RAW
  work and metadata stamps afterward. Baseline RGB16 and ICC must equal the
  current production delivery; the baseline's actual tone is pinned for the
  candidate and a literal baseline rewrite.
- Cache filenames are fixed. Coefficient layout, offsets, extents, total file
  size, whole-file and per-level hashes, and finite f32 values are checked
  against actual bytes. Plane caches receive equivalent size/hash/finite checks.
- Each plane's solve receipt persists. Candidate output requires all four
  solves to be admitted under the unchanged numerical contract. Refusal keeps
  the diagnostics, requires null candidate delivery fields, and requires the
  candidate TIFF and caches to be absent; no partial or placeholder candidate
  is rendered. The validator permits missing/null numeric diagnostics on
  refused solves rather than coercing them into accepted values.
- Actual canonical state/target/hull identities, complete observer on/off TIFF
  identity, pinned rewrite RGB16/ICC and candidate ICC are checked. Output
  directories remain inside the experiment workspace and are created fresh.

This is an inspection of specific control flow, not an executed corruption
commission or a broad security/correctness guarantee. Build-2 and its controls
were pending at review completion. Numerical convergence and photographic
quality require their separately assigned independent reviews. The known
generated glint and far-coarse-detail harms are not waived by this note.
