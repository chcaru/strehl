# Independent source-witness review

2026-09-19. Read-only review of source-witness.rs at
`94d21d6cdead1c357d05fdad4f7ae51fb12dd2c84281b0d7eaece39e78f685af`.
**No source-level blocker for the four-source measurement export.** This is
not a runtime verification; root owns the fresh build and original reads.

The test binds retained configuration, map, full receipt and witness before
decoding; fixes original indices25/28/33/69 and complete70-file identity;
requires the held full active geometry, levels, normalized WB, matrix, optical
profile, crop and rounded GPU/MHC/probe route. Each source goes through the
actual full-domain BandWorker.fold. The patches are extracted only afterwards,
with unchanged output-quad coordinates and explicit reference-active offsets.
Even quad origins preserve decimation phase. No local patch gather substitutes
for the original consumer and no image development is applied.

The strongest identity checks are substantive: active-u16 hash matches the
retained frame; all four complete gathered planes, guide, variance and beta
match retained actual-consumer evidence. The old192-square known4 patch must
also match byte-for-byte inside each wider512-square field. Output fields are
finite, planar f32 little-endian with explicit[R,G1,G2,B] order. Frame and full
known4 hashes are checked again after extraction. Only the current frame and
worker are retained; no collection of aligned frames or pyramids is created.

Two interpretation limits remain. The exported variance is the actual green
guide variance, not four-plane or cross-pixel covariance for a blur-fit
likelihood. Also this export does not carry original CFA clipping/support
authority. Gathered high DN cannot independently certify which original
stencil samples clipped. Any clipping state absent from retained evidence
must be marked unknown, especially around glints; do not manufacture a
physical saturation test from these MHC/Catmull outputs. These limits permit
the proposed descriptive residual inspection and prohibit calibrated
compatibility, source ownership or PSF claims.
