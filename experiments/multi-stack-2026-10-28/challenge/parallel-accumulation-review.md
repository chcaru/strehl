# Independent review of parallel session accumulation

VERIFIED by source comparison on 2026-10-28; no Cargo or RAW execution in this
review lane. The reviewed current source SHA256 is c26fbb21762575ec24d1a0ebf36775924cd79915361c39c51e22a52558ec6d6a; the serial
session-fusion.rs in candidate-2/owned-source.zip is c9b35df90afd37fbfaa3079addf0b0320127e289908fa52b92de01e82391787f.
This report reviews the optimization delta, not a new photographic conclusion.

## Conclusion and exactness boundary

No correctness blocker found in the changed code. The delta parallelizes
independent coefficients within one source call and preserves source and group
call order. Rayon for_each joins before the call returns. There is no parallel
floating-point reduction, source reordering, new image-sized allocation, unsafe
aliasing or shared mutable coefficient. Each pixel executes the same scalar
operations in the same order as the archived serial implementation.

- channel_chunks_mut zips four private vectors constructed from one LevelSize.
  Contribution and Group chunks likewise share those lengths. There is no
  externally supplied unequal vector that could silently truncate the zip.
  The partial last chunk uses its actual count length; begin=block*4096 plus
  local index addresses the corresponding original coefficient.
- ContributionChunk.add preserves denominator/count, numerator division and
  multiplication order, and plain-sum arithmetic exactly. Welford mean/M2 and
  luma/color variance updates retain their original per-source operation order.
- Optional primary chunks are populated only when the source bracket is the
  configured primary. Nonprimary calls cannot mutate them. Group clear still
  resets every mean, M2, variance, count and contribution; it retains the same
  immutable policy and dimensions.
- Coverage fallback preserves the early skip for missing coverage or an already
  preferred primary. The first covering primary clears prior ordinary sums
  before adding itself. Later nonprimary sources cannot affect that coefficient.
  Source registration and duplicate rejection remain serial and unchanged.
- Hull updates preserve the first-uncensored transition, reset to infinities,
  and later exclusion of censored values. The original source ordering still
  determines that transition, regardless of pixel worker scheduling.
- A singleton Repeat group has coefficient count at most one. The new bypass
  skips residual/variance smoothing, but all downstream guarded/scratch reads
  are short-circuited by count>=2. Wholly censored singletons still contribute
  coverage-only fallback, with no statistical gain claim. Stale scratch from a
  prior group therefore cannot change a singleton result.

## Memory, overflow and controls

The pixel-buffer memory estimate remains valid: the parallel adapters hold
slice references and scalar closure state, not new pixel arrays. Existing
estimates explicitly exclude allocator, collection and thread-pool overhead;
caller safety margins still need to cover those. block*4096 cannot overflow for
a valid allocated slice, as its value is at most the beginning of that slice's
last chunk. Existing checked dimension/workspace calculations and the u32 group
member limit are unchanged. This delta adds no source/group counter arithmetic.

The added one-versus-sixteen-worker control exercises 193x177 odd dimensions,
full and partial chunks at multiple levels, both modes, both primary policies,
paired/singleton/reused groups, ordinary and primary disagreement, clipping,
true absent coverage with NaN poison, output floats/validity and all diagnostic
histograms. It asserts that averaging, primary fallback, saturation fallback,
valid and invalid output were actually reached. Existing controls separately
exercise source order, hull censorship, duplicate identity and memory overflow.

UNVERIFIED here: compilation, test execution, speedup and archived-serial output
identity. The new worker-count control compares two executions of the new code;
it cannot alone rule out a schedule-independent regression from the old code.
Root should compare the frozen candidate-2 and optimized binaries on the same
retained ten-source manifest: all sensor/linear/display pixels and non-timing
merge diagnostics must match exactly. The ten-source pilot has incomplete focus
coverage and is only a mechanical/performance control, not photographic proof.

## Commands actually used

Read-only Python zipfile/difflib comparison extracted the archived source in
memory and printed a unified diff against the current source. Read-only rg and
Get-Content inspected constructors, reset, source registration, fold decisions,
finish, memory preflight and the new test. No product source was edited.

## Completed independent archived-serial comparison

VERIFIED after root completed candidate3. Command actually run:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/verify-parallel-pilot.py

Exit0; Python3.12.10, NumPy2.4.4, tifffile2026.5.2. Both complete4672x7008
RGB outputs were compared channel-bit by channel-bit. The float32master has
zero bit differences and identical whole-file SHA256
0bbd7984c2a1413b67104b6ef1cd1631b5f88984690fa3ba087687fb78f6cb50.
The uint16photograph has zero pixel differences; only TIFF Software tag305
changes its candidate-build label. Every non-build/non-timing render field,
source-identity/calibration file and geometry warpmap matches. Exact excluded
fields, hashes and command are recorded in
outputs/multi-stack/pilot-3/independent-optimization-equality.json.

All ten groups in this pilot are singletons. This verifies ordinary/singleton
optimization mechanics on actual data; it does not validate repeat-group quality
or establish photographic gain from incomplete focus coverage.
