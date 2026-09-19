# Independent full-adapter source review

**Decision: no remaining source blocker; admit the bounded full pair after the
same executable passes the two frozen generated controls.** This is a read-only
integration review, not runtime verification or photographic acceptance. No
build, source image, RAW decode or numerical test was executed by this reviewer.

Reviewed frozen SHA256:

- `full-stack.rs`: `8b167e4f02d7da316d7c2c5b2ef3bc2c457bc3d3a7424509a9f0e68071d8480f`.
- `implementation.rs`: `0638ac4cbacf3b366b699f5c9b2d50adbd3f7c1f4cf7463be06010cdc27841c5`.
- `full-run.py`: `d6dd7cf5b2f79eb14807ea60a0c1d4ff2bb11f47e297d22619e8389f56e2eb20`.
- `full-plan.md`: `0aaaf69d0858f387ed1ef803d65e29729aa4d3f720f7f8e9526bd6e5316247d4`.

One concrete in-flight mismatch was found and corrected before execution: the
strict Rust configuration requires `max_extra_inset_quads=0`; an intermediate
wrapper instead emitted `expected_baseline_sha256`. The reviewed final wrapper
matches Rust. Rust already hard-pins and checks the complete baseline TIFF hash
before starting the colour replay, and the wrapper checks it again afterward.

**Baseline and geometry.** `chunk_plan` is the existing four-plane, full-geometry
planning formula, explicitly asserted to give four chunks of at most18 frames.
The first accumulator move, subsequent left absorption and between-chunk resets
match `run_pyramid_prepared`. All70 source names, placements and successful folds
are required. Crop, seven-band defaults, WB bits, matrix, tone and CA profile are
held. The second decode checks active u16 hashes against the first; this is
repeatability of the same decoder, not an independent decoder implementation.

**Acceptance arithmetic.** Comparing the frozen generated implementation with
the new file shows only the maximum size bound and full-adapter include changed.
Target remains `0.5*(collapsed G1+G2)` in black-subtracted source DN. Replay uses
actual `load_frame` and `luma_variance`; both arrays must hash-match the baseline
for every frame. No beta or WB multiplier enters the squared-intensity acceptance
test. One mask/count applies to all twelve colour/site values. Source ordering,
uniform f32 summation, division and zero-count fallback are the screened helpers.

**Colour and exact fallback.** The four actual consumer planes are moved into
the packed array; CPU gather supplies only slots4..11. It cannot substitute CPU
known-site values for GPU values. All twelve composed CA pulls receive the
existing full-source support guard before processing, with no extra inset;
missing-colour gathering also refuses any unsupported/nonfinite sample.
`camera_rgb(12)` interleaves directly and adds no MHC. `camera_rgb(4)` and
`write_planes(4)` use identical `max(0,value)*gain*1/range` normalization and the
same Malvar row kernel; directional mode is refused. The existing phase-packed
writer control already exercises their equality. The shared fallback copies
all three RGB bits at each of the four correct native quad addresses, then the
candidate uses the same held `develop_pixel`. No additional spatial operation
can contaminate those fallback pixels.

**Scope and receipts.** Original inputs have no write path; sizes/times are
checked before and after both passes. Workspace output is new-only. Streaming
sums/counts plus one current source are retained, not an aligned-frame volume.
The source count map and histogram preserve fallback versus single/multiple
source participation. The bounded runner cleans experimental environment,
binds source/executable/control receipts and enforces the stated resource caps.
Runtime, baseline byte identity and photographic benefit remain root-run gates.

## Baseline container guard correction

**Decision: admit the guard-only correction.** The first full run stopped at
the baseline file-hash assertion before colour replay, after30.859 seconds.
Root's independently decoded `full-1/baseline-container-check.json` records
zero differing samples across all95,745,120 RGB16 values. The only differing
TIFF tag was305, Software: the truthful build identifier changed from
`ed20dc3be490-dirty` to `93c08ce7655d-dirty`. Thus the earlier whole-file guard
was stricter than the intended image-content identity requirement.

Reviewed replacement `full-stack.rs` SHA256 is
`2511ae67eb151e196ce40830754faddb65de89ca682b603fbd3204bb9e22bc5d`;
runner SHA256 is
`36c1f7ec9c60f933ec1b42bc459b9a48d22425906c3e988323ffddd519c97596`.
Comparison against `full-first-freeze/full-stack.rs` shows only the decoded
baseline guard and receipt additions; candidate/rendering arithmetic is
unchanged. `implementation.rs` retains its previously reviewed0638ac4c hash.

The new guard opens the written TIFF, requires6920x4612 RGB(16), exactly
95,745,120 u16 samples and one page, packs every decoded sample explicitly in
little-endian order, and requires the independently obtained hash
`2a19cd9b7236a13bf90e81b87e85b1058e071aa19f4a5af82b97f453687d0dda`.
It runs before colour replay. A pixel change, channel/extent change or missing
sample can fail this guard. Actual file hash and Software tag remain recorded;
neither is rewritten to impersonate the historical build. The wrapper separately
checks `np.array_equal` against the historical file bound by its original
`c0d8faca...` hash after the pair. This supersedes only the whole-file-equality
requirement above. Review read code/receipts only and performed no decode/run.
