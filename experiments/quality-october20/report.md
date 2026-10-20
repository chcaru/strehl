# October 20 quality, repair and reconstruction work

This is a scoped product change and review record, not a new SOTA milestone.
Original captured RAW files were read only. No global merge, noise, resampling,
highlight or alignment default was changed.

## Decisions from existing photographic evidence

The requested tilted calibration slide contains 197 RAW files. The four mineral
collections contain 183 garnet, 423 peacock-ore (two brackets of 207 and 216),
155 opal and 228 rutile-on-hematite files.

Before selecting a change, the existing September mineral diagnosis and complete
photographic reviews were read: `quality-september25/minerals/diagnosis.md`,
`garnet-numeric-fix-photographic-review.md`, the garnet/ore
`highlight-rendering/photographic-review-*.md`, and the opal headroom factorial
and stage reports. They already reject using a shoulder/rolloff parameter as a
general glare cure. The garnet rectangular color failure was a separate,
previously repaired nonfinite-accumulator defect. A lower white-pixel count does
not establish recovered detail, and a physical reflection present in a focused
source is not necessarily a merge artifact.

The current investigation also read the existing clamp-default decision,
M54 clipping-mask rejection, V-REVIEW-halo rendering warning and relevant
SYNTHESIS/AGENTS constraints. A blanket bright-region blur, clipped-source
rejection, default clamp switch or another shoulder sweep was not justified.

`inspect-existing.py` creates complete BOX-filtered overviews of five existing
TIFFs, records their source hashes and run settings, and retains ICC profiles.
`native-regions.py` uses three frozen native-size regions chosen from the complete
baseline photograph before inspecting variants. Existing slide runs distinguish
the default, clamped Catmull, and gate 8/exponent 8/sharpen 2 settings; they are not
treated as interchangeable baselines. Broad gray edge shoulders remain in the QR
region in those three runs. This is a visible observation, not an isolated
mechanism or a quantitative ranking.

Three original slide sources, zero-based indices 49, 98, 147, were decoded one at a
time. Copies of the active CFA and color layout were made while the rawpy context
was alive. Source 49 supplies the relatively focused QR witness; the later sources
show that area defocused. None of those three active areas reached nominal white
or the container ceiling. Their maximum codes were 7865, 8184, 8508. LibRaw's active
width is 7028 versus Strehl's 7032; those raw previews are therefore descriptive
witnesses, not pixel-matched resampling truth. Source hashes remained unchanged.

## Explicit source-region repair

`--region-recipe` now consumes enabled normalized regions with inclusive,
zero-based source ranges. Each region is reconstructed in a separate CFA
accumulator using the original output gauge, crop, noise model, configuration,
resampler, correction policy and canonical chunk boundaries. Only permitted,
placed donors are decoded in that pass. Its fallback, base residual and
reconstruction hull cannot silently reintroduce excluded donors. The reconstructed
CFA result is feathered before demosaic and color development; later overlapping
repairs apply after earlier ones.

This is an explicit manual correction tool. It does not infer the correct donor
or claim automatic occlusion-halo or reflection removal. It costs another pass
over the selected donors for each active region, plus the current reconstructed
CFA planes retained during that pass. Sources are not rewritten. Missing placed
donors, out-of-range spans, empty sample support, and uncovered alignment are
refused before reconstruction. Covered scale/crop output is required for aligned
repairs. A successful float master records the actual applied recipe; merely
pending annotations are not recorded as baked source repairs.

The existing admission telemetry describes the original merge. It must not be
presented as final source ownership inside repaired areas. The new source-repair
progress reports actual extra-pass region and frame counts. Confidence, when
requested, compares the repaired result with the full source stack; it remains a
centrality diagnostic, not a quality probability.

**VERIFIED generated-path controls:** fresh compilation and
`cargo test -p strehl-cli --lib source_repair -- --test-threads=1 --nocapture`
passed 6 tests. They exercise the actual `BandWorker` and final TIFF writer:

- Disabled/source-free recipe produces the same entire TIFF hash and decode count.
- Two different full-region, single-source constraints each equal a separately
  stacked donor's entire output; the fixture asserts they really differ from the
  unconstrained image.
- Forced mean-fallback control crosses canonical chunk boundaries, decodes no
  excluded donor, preserves every exterior CFA bit and exercises interior and
  feather pixels.
- Invalid spans, all-refused donors, uncovered alignment and a subpixel region
  with no sample centers fail.
- A cropped registered output retains exact geometry/CFA phase and whole-image
  equality with the corresponding single donor. Applied recipe metadata survives
  master reload; tone changes remain allowed, changed source constraints fail.
- Progress off/on/disabled-placebo produces identical complete TIFFs:
  SHA256 `9c86d4fc9bbb4a271c46c6b6a72d13d4ab28c66400ad2fe16adbf74f4e1197ac`
  in the recorded run. Captured events assert actual accepted/completed counts.

Commands used `CARGO_TARGET_DIR=outputs/quality-october20-target` and
`CARGO_BUILD_JOBS=4`. Complete logs are in `repair-tests.log`; generated artifacts
are in the existing production-truth test workspace. These are behavior controls,
not photographic quality proof.

`run-slide-pair.py` freezes the real comparison: two complete 197-frame renders,
the existing alignment copied to isolated override paths, four execution
workers, identical ordinary merge settings. The repair is a single fixed QR
rectangle, x 4650..5290/y 400..1040 in 7032×4688 output, inner feather 0.2, source 49.
Its output includes a float master. The receipt stores complete commands,
environment, executable/map/recipe hashes, source inventories and source 49 hashes.
No parameter sweep or alignment re-fit is licensed by this comparison.

The reproducible entry point is
`python experiments/quality-october20/run-slide-pair.py "<read-only-slide-bracket>"`.
The exact two expanded command lines, environment and original private source path
remain in the local `outputs/quality-october20-slide/receipt.json`. That receipt
and both run logs are retained locally, not published. The runner refuses to
reuse its existing output directory, so a future investigation must choose a
new isolated directory rather than overwrite this evidence.

**MEASURED complete real runs:** both exited 0, producing 7032×4688 TIFFs.
Baseline wall time 158.609 s and repair+master 157.344 s are single-run observations
on a shared machine, not a timing comparison. The repair extra pass folded only
source 49. The unchanged original alignment hash is
`133aad1446f50f570cafc9df636661318a6688a7c1b8c2d5f2a9ec9bd2cdebec`.
Baseline TIFF SHA256:
`4b1973afac3bc10c204d9877797fb61593c9718816853f8594c5d4c64f78c256`;
repaired TIFF:
`5e4f49af88bb070cc7cc244993ef1ca94b0cb8b60e83cc3cceeeffe9b3005ea6`.
The source inventory and source 49 hash were unchanged.

`review-slide-pair.py` generates complete BOX overviews and the same frozen
native-size crops. **Author photographic observation:** the repair suppresses
broad gray shoulders but softens the QR
edges and makes purple edge fringes more visible. This one selected donor is
not accepted as an overall photographic improvement. It is evidence that the
manual region/source intervention works and that selecting a relatively focused
witness is not enough to establish the best replacement.

The complete TIFF comparison finds 0 changed exterior RGB pixels out of 32,546,112
outside the repair rectangle plus four pixels of final demosaic support.
410,324 region RGB pixels change. This is a locality check, not a quality score.
The unmodified centre-text and gray-ramp native crops are negative controls.
No further donor sweep or full RAW replay followed this result.

**Independent root review:** both complete photographs were inspected before both
native QR crops. The whole composition stayed stable without obvious exterior
damage. The reviewer independently observed reduced gray shoulders, softer white
boundaries and stronger purple/magenta fringes, and rejected this replacement as
an overall quality improvement. Retain the explicit manual tool; a better source
and region choice is required for a useful repair on this photograph.

No second donor/span is justified by the inspected witnesses: sources 98 and 147
were visibly more defocused at this region than 49. The RAW witnesses were not
registered pixel-matched evidence. A further attempt needs registered per-source
inspection that separates focus, chromatic fringe and resampling effects; no
additional RAW replay or unsupported nearby-span guess was performed.

## Reconstruction storage optimization

The collapse operation alternates two full-size buffers instead of allocating
and copying each expanded pyramid level. Expand/add/bound order and f32 arithmetic
are unchanged. Both buffers retain a caller's maximum workspace extent.

**VERIFIED** frozen pre-change implementations compare every output f32 bit
across odd/even sizes, repeated dirty scratch, signed values, impulses, ramps,
zero signs, source immutability and active upper/lower per-level bounds. An
independent root review found the important larger→smaller→larger workspace
sequence: an odd number of swaps originally shrank reusable scratch. The added
adversary failed with 49601→12513 samples before the maximum-extent fix and passes
after it. The fixture asserts that an odd number of swaps actually occurs.
Fresh `cargo test -p strehl-core --lib collapse_tests -- --test-threads=1` passes
four controls, with the manual benchmark ignored.

**MEASURED reconstruction kernel only**, including the workspace-extent guard:
one release binary, frozen old implementation and new implementation,
warmups and ten alternating old/new pairs at each setting. At 3516×2344, minimum
old/new times were 11.9469/8.8295 ms with one thread and 8.9817/5.2786 ms with four.
This does not establish a full-stack speedup. The exact benchmark command was:

```
cargo test --release -p strehl-core --lib collapse_tests -- --test-threads=1 --include-ignored --nocapture
```

## Executable size

**MEASURED binary transformation, not a rebuilt whole application comparison:**
`measure-linux-strip.py` extracts the official alpha.5 AppImage's Strehl ELF,
copies it and applies GNU strip 2.42. Size changes 31,717,040→26,267,488 bytes,
5,449,552 bytes smaller (17.2%). Every allocated ELF section's name, address, size,
flags and SHA256 stays equal; engine `--version` and `--help` bytes stay equal.
The original AppImage remains unchanged.

This justifies the approved release `strip="symbols"` setting. It does not
measure compressed AppImage savings, Windows size, or the final net size after
adding HDR/editing. No GUI/RAW execution claim is made from help/version checks.
Detailed hashes and invocation are in `linux-strip/receipt.json`.

**MEASURED net Windows executable size:** the locally extracted official alpha.5
`Strehl.exe` is 25,138,688 bytes; the new release build with HDR/editing/agent features
is 28,310,528 bytes (+3,171,840 bytes, 12.6%). These are different feature sets, not a
controlled stripping comparison. This release does not claim a smaller Windows
executable.

## Independent HDR/editing review

Independent controls are in `crates/strehl-edit/tests/quality-review.rs`.
An off-center crop preserves a concave polygon's original image coordinates,
including a known outside notch; reversed vertex order produces the same result.
Persisted source-repair matching rejects changed order, shape, feather and
enabled state while permitting names and tone controls to change. Negative and
above-white samples survive the master round trip.

Review found two defects and the HDR author corrected them:

1. Foreign embedded RGB ICC profiles previously entered the sRGB decoder
   silently. The initial supported policy now refuses unknown embedded profiles;
   a syntactically intact changed-primary ICC is the negative control.
2. Full-range 10-bit chroma was centered at 511.5 rather than 512. Quantization now
   follows the integer origin in H.273 equations 30–31. The independent inverse
   also uses `(code-512)/1023`.

Fresh normal-account test execution passes all three independent controls.
The Windows sandbox's temporary-folder ACL rejects atomic publication; the same
tests pass with normal account permissions. Product publication semantics were
not weakened to accommodate that sandbox.

`quality-color-fixture` plus `verify-color-hdr.py` uses eight saturated, mixed,
negative-component and above-white patches, reference white 250 nits, and an
independently xy-derived BT.709→BT.2020 matrix. The verifier decodes raw
10-bit 4:4:4 YUV with FFmpeg, then applies the inverse transfer. Corrected output
passes the 3%/0.75 nit per-channel bound with 1.5051 nits maximum absolute error on
targets up to 673.4264 nits. Swapped chroma is rejected. CICP container and AV1
tags agree; MaxCLL 674 and frame-average 155 match the independent calculation.
This is a numerical encoding check, not verification of a physical HDR display
or real-scene quality.

**VERIFIED real-file workflow:** the repaired 7032×4688 RGB32 master was reopened
through the CLI and exported with its baked source recipe to 10-bit 4:4:4 BT.2020/PQ
AVIF, quality 85/speed 10. The 1,764,113-byte output was decoded in full by FFmpeg,
and ffprobe confirmed size, bit depth, full range and color tags. MaxCLL 200 nits
and frame-average 59 nits match the encoder report. This particular capture stays
below reference white; the alternate colored fixture is the explicit headroom
control. The full decoded SDR proxy was visually inspected and retains the
photograph's structure. It is not an HDR-display test.

The independent root reviewer also inspected the complete decoded proxy and
found the photograph consistent, without a conspicuous color cast or global
geometry damage. This supports decode/render plausibility only, not HDR-monitor
verification or acceptance of the rejected QR replacement.

The real HDR output SHA256 is
`077a8c7038ea230eb62a793562e067b17600cdf61040e521dcd89cbdbd336624`.
Full invocation, current executable, master, recipe and output hashes are in
`outputs/quality-october20-slide/repair/hdr-smoke-receipt.json`.

Primary specifications consulted:
[ITU colorimetry](https://www.itu.int/dms_pub/itu-r/opb/rep/R-REP-BT.2380-1-2017-PDF-E.pdf),
[H.273 full-range encoding](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-H.273-202107-S%21%21PDF-E&lang=e&type=items),
[AV1 container color agreement](https://aomediacodec.github.io/av1-isobmff/).
