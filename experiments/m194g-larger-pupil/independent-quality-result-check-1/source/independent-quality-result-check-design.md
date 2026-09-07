# Independent actual quality-result check

2026-09-07. Prospective bounded verification of the completed fixed38 output
matrix and scorer result, after their reported values exist. The input choices
below are frozen before this verifier decodes or calculates anything. They add
no quality acceptance threshold and select no new ROI. Root commits source,
design and exact command before execution. No producer, old TIFF parser,
quality metric/reducer, or optical helper is imported.

Input is the externally pinned actual scorer result
`7477f1553ac53dc87d554cee04117c536f7e5d3476b97ce9fde8f5d3b42b95df`.
Its original matrix,38 entry records, two readouts, scalar target, fixture,
source snapshots and observed input bindings are reopened and hashed. The
fixed source/command release uses m194g-numerical-execution-release-v1, scope
independent-quality-result-check. Source bindings contain the new verifier;
inputs include this design and the scorer result. Actual sys.orig_argv must
match its exact command after the sole release-hash substitution. Additional
released inputs remain in the final recheck. This produces a scoped independent
comparison result, not another authority/gate or recursive certificate system.

## Different deciding choices

- Implement a separate small classic TIFF decoder with struct and NumPy only.
  Inspect the same bounded byte buffer: byte order,42 magic, one IFD, unique
  tags, unsigned16 RGB, uncompressed/chunky/top-left/no prediction, valid strip
  extents/counts, no overlaps with metadata and no ICC/extra channels. Dimensions
  are bounded320x240 and files1MiB before array allocation. Reconstruct native
  little-endian pixel bytes and compare all38 actual file/pixel identities with
  both checked-entry and render-receipt records. No author TIFF implementation
  is called. Harmless TIFF metadata/padding is permitted; payload interpretation
  is independently checked.
- Flat scene first, then textured; all eight literal seeds701,709,719,727,733,
  739,743,751 and both modes. Temporal variance uses first-repeat-centered batch
  sums of deviations and squared deviations, denominator7, not Welford or
  spatial variation. Independently compute all original seven region means and
  mode ratios, with whole/W as the primary requested variance readout.
- Per-seed MSE differences use independent dot products and math.fsum across
  the eight named repeats. Retain the values, sample SD and SD/sqrt(8).
  Jackknife variance removes each whole repeat from these batch statistics;
  paired deletions retain pairing. Do not use pixel independence for SE.
- Independently verify every individual bias/MSE/RMSE/site record, including
  noise-off and all eight noisy seeds, both modes and all channels. Preserve
  exact ordered keys: seed, channel, fixed reference, region, then mode.
  There are378 flat and486 textured rows (seven ideal regions plus the two
  separately admissible endpoint references for textured). Use already loaded
  pairs, so this adds no TIFF read. Equal common errors cannot hide by cancelling
  in the paired MSE difference. The same numerical agreement tolerances apply.
- Keep ideal, each endpoint observation, and each mode's own noise-off image
  separate. Ideal uses the original admitted K=0 array for textured and12000e
  for flat, represented f32 WB and CFA factors, with no second black subtraction.
  Endpoint0/background and endpoint4/foreground retain their original strict
  masks. The own-noise-off comparison is a noise-dependent nuisance reference,
  not fidelity truth. No best-reference selection, splice or new boundary mask.
- Check every individual noise-off/seed pair and the two eight-repeat means:
  whole and W, each channel, both absolute-error maxima/p999, signed values at
  both worst sites and maximum absolute-error worsening, all native coordinates,
  and >10DN improvement/worsening counts. Native(y,x) order breaks exact ties.
  Only an alternate floating summation may move a mean-image tie: any different
  reported coordinate must independently attain the same maximum within1e-8DN
  and is explicitly reported as a numerical tie, never silently treated as an
  exact coordinate match. Individual u16-derived output pairs require exact
  coordinates; no tie allowance is applied there. Non-tied displacement refuses.
- Noise-off textured waves use a directly constructed canonical-coordinate
  five-column matrix and independent NumPy least squares on each original
  surface mask. Compare both modes/channels, target coefficients, amplitudes,
  phases, intercepts and residuals; retain full-signal error. No target fitting,
  gain correction or phase correction changes the fidelity reference.

Agreement tolerances are numerical verification tolerances, not new quality
bars: absolute1e-7DN2 plus relative1e-10 for variance/MSE/uncertainty;1e-8DN
for sparse magnitudes/site values;1e-7DN for wave coefficients/amplitudes/
residuals and1e-9 radians for defined wrapped phase. Integer counts, file/pixel
hashes, populations and non-tied coordinates are exact. Retain actual differences
and all failures, including an earlier successful subset.

## Private power before actual output calculations

The separate TIFF decoder gets two-endian/multiple-strip integer-ramp valid
companions and wrong sample format, overlap, truncation, wrong external digest,
oversized dimensions and one changed green-code faults. Decoder refusals must
be the named boundary, not an unrelated exception. Constant/spatially structured
but temporally constant arrays must have zero temporal variance. Eight fixed
offsets[-7,-5,-3,-1,1,3,5,7] give variance24; half offsets give6 and ratio.25.
Their paired MSE differences are -.75 times offset squared, mean-15.75 and
SEsqrt(27). Build the actual offset/half-offset arrays and compute both errors
through the same independent helper used for the genuine individual rows;
verify literal signed bias, squared error, RMSE and population before the
paired uncertainty. Supplying the expected differences directly is insufficient.
A deliberately spatial-axis estimator must disagree on that actual
fixture. Restore inputs and recover the original values.

A single64DN red spike and tied positive/negative errors exercise the sparse
maximum/count/native-location code; one spike outside W must remain visible in
whole-output diagnostics. A constant3000DN and fixed two-wave private signal
exercise the actual least-squares function. Halved amplitude and a dropped
native coordinate offset must produce finite changed coefficients/common-target
error; restored inputs recover. These controls do not draw random noise.

One120CPU/240wall clock starts before NumPy import;32MiB of live named ndarray
backings and32MiB cumulative output apply to private and genuine work together.
No eight-repeat image volume is stored. Use one scene and current pair at a
time, retaining only noise-off/endpoint references, two anchors and batch
statistics. Reread noisy pairs for delete-one statistics; successful scope is38
distinct actual TIFFs, normally70 genuine decodes plus bounded private decodes,
at most96 total. The finite private population has21 checks and exactly9 parser
attempts: two valid endian companions, four malformed headers/extents, wrong
external hash, legal changed-green bytes and restored bytes. The legal green
change must decode to the independently expected changed site/value and changed
pixel hash; a parser rejection cannot pass it. Thus successful complete work
has70 genuine plus9 private parser attempts =79, with rejected attempts counted.
Every read is hashed. Output/source/input rechecks and final
persistence share the same clock. This is not a process-RSS or throughput claim.

Command form (actual absolute paths/interpreter/cache/output frozen by root):
`python -X pycache_prefix=NEWCACHE -X faulthandler independent-quality-result-check.py --release RELEASE --release-sha256 ACTUAL_EXECUTION_RELEASE_SHA256 --score SCORE --score-sha256 7477f1553ac53dc87d554cee04117c536f7e5d3476b97ce9fde8f5d3b42b95df --output NEWDIR`.
