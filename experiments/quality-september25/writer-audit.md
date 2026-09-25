# Writer audit: tone, gamut and an economical replay boundary

Read-only source review; no code change, build, RAW decode or candidate image.
This follows the pipeline audit and is independent of the current generated
coherent-estimator author. Root's generated build may proceed unchanged.

## Verified live path

`merge_cmd.rs::write_merged` (currently near line 7715) reads the compact
collapsed four CFA planes through `Merged::Bands::value`, clamps negative DN to
zero at that boundary, applies first-frame white balance and normalization,
interleaves the full mosaic, then calls `image_out::write_demosaiced`.
`image_out.rs` resolves tone from a mosaic quad sample, demosaics full rows, and
calls `develop_pixel` (1236). That function calls `color::Render::develop`,
which already performs sensor-highlight clipping, sensor-domain chroma
roll-off, and the camera-to-sRGB matrix in that order (`color.rs` 345–373).
Thus the production pyramid skips its *merge clipping census*, but does not
skip all highlight rendering. Those are distinct mechanisms.

Tone uses luminance p0.1, multiplied by 0.85, for the black point; p99.9 is
placed at 0.90. `Tone::gain` (image_out 1130) applies one luminance-derived gain
to all three channels, with a soft shadow toe. It has **no highlight shoulder**.
The exposure gain follows this placement. `gamut_map` (1181) then projects an
out-of-range triple toward neutral at its clamped BT.709 luminance, taking the
smallest blend that enters the RGB cube. Finally, sRGB encoding and the
per-channel display-space S curve (contrast 0.55) precede RGB16 quantization.

**DERIVED directly from these operations:** when upper-gamut violation binds,
at least one channel lands on exactly 1.0 even if the other channels still
contain useful differences. If the post-tone luminance reaches or exceeds 1,
the neutral endpoint is [1,1,1]; a channel above 1 requires full projection,
which can collapse the complete triple to white. Neither condition implies
RAW clipping. A bound on luminance does not bound maximum channel value.

The retained build used for the new outputs has the same writer mathematics.
`git diff 36b91f0e5ced HEAD -- crates/strehl-cli/src/image_out.rs
crates/strehl-core/src/color.rs crates/strehl-core/src/highlight.rs` shows only
`develop_pixel` visibility and a test-only pinned-tone hook in image_out; no
changes to color.rs/highlight.rs. This read does not independently qualify
all other current gather/merge differences against the retained executable.

## Existing evidence that must not be repeated as a discovery

`docs/research/BUILD-OUTPUT.md` section 2 explicitly separates all-three-channel
white from one-channel gamut-wall hits. SYNTHESIS fact 1894 records the same
correction: a clip-count gate had failed a master with zero all-channel blown
highlights. The near-100% red ceiling in a marigold crop therefore cannot
alone support “lost RAW highlights” or “glare recovered.”

The same report's section 2.2 found a sensor-domain chroma roll-off benefit on
the old marker capture. Section 2.3 found the roll-off completely inert on
old flowers-cpl at knees 0.60, 0.45 and 0.30: its gamut limit arose downstream
of the sensor-domain operation. Repeating that knee sweep is not justified by
the new red-ceiling count. A post-tone shoulder/gamut strategy is a distinct
untested question in the inspected records, not disproved by that null sweep.

The old automatic-exposure double-application regression is separately fixed.
SYNTHESIS facts 1816–1819 expressly prohibit offering it as the explanation for
the user's historical quality rejection. The new invocations contain no
`--auto-exposure`; their negative exposure variants already reach the current
writer's explicit post-tone gain. Do not reopen the old bug without new proof.

## Minimal complete intermediate export

The economical boundary is the **one merged output**, not every aligned frame:
save the four collapsed f32 planes after `merge.finish` and before
`write_merged`. The actual call site already exists at merge_cmd around 6490:
`source.observe_direct_collapsed(&planes)` under the test/direct-plane guard.
`RawPyramidSource` routes it to `matched_source_tests::observe_planes(None,…)`.
The existing observer in
`experiments/quality-september14/matched-source-tests.rs` supports only <=400
pixel patches and at most eight regions; it must not be disguised as a full
image export or have those limits silently removed.

Recommended separate diagnostic adapter, after the current source freeze:

1. Stream each already-existing collapsed plane to new little-endian f32 files
   in [R,G1,G2,B] order, retaining signed values exactly. Store full-plane and
   crop geometry, reference index, levels, first-frame WB and camera matrix,
   actual f32 bit patterns, input-order/map/source hashes, merge settings and
   each plane hash. The buffer already exists; no N-frame image volume is
   created. A channel-major raw f32 payload plus JSON is sufficient.
2. Replay through the **existing** `write_merged(Merged::Bands{…})` and existing
   MHC/writer. First replay must match the complete freshly rendered baseline
   RGB16 pixels and ICC. Also compare to the retained user-output baseline
   before interpreting any candidate. Do not invert a clipped TIFF to create
   the intermediate.
3. Add writer-only candidate variants on that same merged object. Preserve a
   bit-exact current arm. Freeze the original tone anchors where the scientific
   question is a shoulder/gamut change, so remeasured percentiles do not mix
   into the intervention. Retain the requested exposure of the delivered
   comparison, and record whether a candidate intentionally changes it.
4. Prove the new export does not change output by on/off output hashes, including
   its placebo path, per rule 26. Since the observation point is after the merge,
   this can be designed around one frozen collapsed result and repeated writer
   calls; it need not rerun N RAW sources for every rendering variant. Exact
   retained whole-baseline comparison remains an additional requirement.

**DERIVED storage:** marigold 1's four planes occupy
`3114*2076*4*4 = 103,434,624` bytes (about 98.6 MiB). The largest current
mineral crop occupies `3396*2264*4*4 = 123,016,704` bytes. A full materialized
marigold RGB f32 image would instead use 310,303,872 bytes and is unnecessary
for ordinary writer replay. These are arithmetic estimates, not runtime
measurements. The existing writer processes rows and keeps RGB16 output, so
the repeat cost is full-image development/write, not RAW decode/align/merge.

`--linear-srgb` RGB16 is not a substitute for this cache: it already clamps
out-of-gamut values in develop_pixel. Preserve the pre-development f32 planes
if the purpose is to examine precisely that information.

## Bounded next question and failure conditions

One fixed shoulder/gamut candidate can be assessed independently of the merge
work using full marigold and one mineral outputs. A useful result must retain
petal and colored-facet texture, avoid bleaching saturated real colors, keep
diffuse surfaces/shadows usable, and preserve whole-image brightness intent.
It must fail if it merely hides glare by globally darkening or deleting
highlight structure. A neutral highlight ramp, a saturated yellow/red ramp,
an in-gamut identity control and a dark colored control can cheaply expose
different regressions before full replay. Include unclamped intermediate
stage counters, distinguishing sensor-domain clipping, post-tone luminance
overflow and a single-channel gamut boundary.

No display-only change can establish a repaired doubled hair, spatially
misregistered contour, or eliminated defocus occlusion halo. Those still
require the independent geometry/merge work. Every user-facing improvement
must show the complete before/after output and its full-resolution masters.

Commands were targeted `Get-Content` source/report slices, `rg` searches in
image_out.rs, merge_cmd.rs, color.rs, highlight.rs, the matched observer,
BUILD-OUTPUT/BUILD-HIGHLIGHT and SYNTHESIS, plus the targeted revision diff
above. No source binding was edited during the review.
