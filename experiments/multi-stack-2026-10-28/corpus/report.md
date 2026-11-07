# Multi-stack corpus discovery

**VERIFIED census:** the eight requested roots contain **48 RAW directories,
8,299 RAW files and 308,651,499,520 bytes**. Metadata and full-file SHA256 were
read for the first, middle and last frame of each directory (144 representatives,
5,461,073,920 bytes). No representative hashes are equal. All 144 samples report
Sony ILCE-7CM2, ISO 100 and FE 100mm F2.8 Macro GM OSS + 2X Teleconverter.
Same model/lens is not proof of the same physical body.

**VERIFIED source handling:** only metadata, file bytes for hashes, and embedded
JPEG previews were read. No CFA decoder, stacker or aligner ran. The complete RAW
name/size/mtime census was unchanged after extraction. That is not a byte audit
of all 8,299 RAWs. No representative hash duplicates does not exclude unsampled
duplicates.

**Observed pose evidence:** all 90 extracted embedded previews (1616x1080) were
inspected via 12 contact sheets. The 480x320 thumbnails are orientation aids only;
they cannot establish detail retention, subpixel correspondence or quality gains.
Camera JPEG development differs with capture settings, so brightness/color
observations below are warnings, not linear-radiometry measurements.

## Recommended development pairs

| Priority and purpose | Source directories | Evidence and caveats |
| --- | --- | --- |
| 1: focus-matching pilot | slide tilted-sw10-cpl (b13, 92) + tilted-sw4-cpl (b14, 182) | Same chart, very similar pose and settings (f/5.6, 1s, ISO100). Different ladder density tests unequal lengths. Chart has unique QR/text features as well as periodic structure. Exact focus correspondence remains unproven. |
| 2: exposure-aware fusion | slide flat-sw4-cpl/flat-et1s-sw4-cpl (b10, 60), flat-et2.5s-sw4-cpl (b11, 61), flat-et6s-sw4-cpl (b12, 65) | Same chart composition; EXIF shutters are 1, 2.5, 6s, f/5.6, ISO100. Useful for registration, radiometric scaling and clipping controls. Exposure changes alone do not prove clipped RAW detail can be recovered; inspect sensor values before an HDR claim. |
| 3: full natural repeat result | insects bug-3/106MSDCF (b28, 299) + bug-3/107MSDCF (b29, 299) | Same full-body weevil pose and similar near/middle/far sweep, f/5.6, 1.6s, ISO100. Distinct acquisitions, Oct25 21:12-21:22 and 21:28-21:38. No commanded-focus manifest or proof of identical nodes/FPN independence. |
| 4: segmented-pass test | marigold stack2.1 + stack2.2 (b31+b32, 433); stack3.1 + stack3.2 (b33+b34, 339) | Preview focus progresses through each .1/.2 boundary, and times are close. Treat as likely continuation segments before considering these two grouped passes as repeats. Sampled shutters 1s, f/5.6, ISO100. Confirm grouping geometrically; suffixes do not prove ladder identity. |
| 5: small periodic-ambiguity challenge | grid calibration-grid-1-sw10-cpl (b06, 23) + calibration-grid-2-sw10-cpl (b08, 27), or sw4 b07 (55) + b09 (46) | Short, same target/settings. Repeating grid can yield a convincing wrong-period fit; require distinctive marks and held-out placement checks. These are development data, not the separate sealed 407-frame session. |
| 6: aperture-aware layers | fabric b03 f/5.6 (210), b04 f/8 (150), b00 f/11 (109), b01 f/14 (83), b02 f/18 (71) | Same woven subject, progressively different exposure/blur and focus span; shutter remains 1.3s. Do not average as equal-noise/equal-PSF repeats or treat aperture order as measured resolution order. |
| 7: stable aperture controls | ruler b40/b41/b39 (120/85/65), horizontal razor b46/b47/b45 (67/50/40), diagonal razor b43/b44/b42 (279/210/143) | Three apertures each, fixed shutter within family. Strong edges/marks aid alignment. Different optical blur/radiometry require per-pass treatment. Horizontal and diagonal razor poses are separate sessions. |
| 8: reflectance/layer challenge | insects bug-1/102MSDCF (b17) + 103MSDCF (b18) | Similar top view, but green iridescence changes visibly and shutter changes 5s to 3.2s. Scalar exposure correction need not remove directional reflectance changes. Preserve aligned layers rather than treating color differences as noise. |

## Segment and geometry pitfalls

- **Likely continuation, not repeats:** bug-3 100MSDCF (299) followed by
  102MSDCF (247); bug-3 104MSDCF (299) followed by 105MSDCF (185).
  The next directory begins near the previous directory's far-focus end.
  The first pair is a much tighter view than the later full-body pairs.
- Bug-3 103MSDCF contains only 22 frames and looks like an incomplete
  full-body sweep. Useful for missing-focus-support tests, not automatically
  a complete repeat reference.
- Marigold .1/.2 groups are 433, 339 and 488 frames. The 488-frame offcenter
  group (b35+b36) changes composition, focus-step setting and shutter to 0.8s.
  It is a parallax/overlap negative against the centered 1s groups, not an
  ordinary repeat of the centered group.
- Bug-1 100MSDCF is an underside view; 102/103 are top views; 104 changes
  angle again. Same insect identity does not authorize one similarity model.
- Bug-2 102/103 show similar green wing composition but differ in brightness,
  focus coverage and shutter (1.6/2s). 100 shows substantially different
  coloration and placement at 2.5s. Check correspondence and photometry.
- The two peacock-ore directories (207/216 frames, f/5.6, 2s) show substantially
  different framing/surface appearance. Their previews do not establish a
  same-view repeat or valid calibrated mosaic. Keep as a geometry/reflectance
  challenge until overlap is actually measured.
- Flat, tilted and very-tilted chart families have different geometry. Only the
  two similarly tilted passes are initial same-pose candidates.

A **pass should support several source-directory segments** with separate
provenance and capture order. One-directory-equals-one-pass would misclassify
several useful supplied examples. Import should allow explicit grouping and
expose per-pass counts, settings and relationship (repeat, complementary focus,
exposure, separate layer). Automatically fusing a parent folder is unsafe.

## Focus metadata and limits

Queried ExifTool focus fields were absent on all samples. This says nothing
about the existing native Sony maker-note reader, which exposes additional
records; that reader was not executed here. Pairing cannot depend on these
ExifTool fields or filename equality. Directories reuse camera filenames, so
filenames alone are not source identities.

No candidate has a recorded exact focus-command ladder in this inventory.
M-FRC-VIABILITY distinguishes same-focus node identity from mere alignment and
warns about shared processing/FPN. FRC on ordinary repeated sweeps must therefore
be labelled reproducible detail and qualified by focus support, not certified
resolution.

No known lateral-stage displacement, entrance-pupil distance or calibrated
depth-varying mosaic fixture was found by this bounded inspection. That is a
limit of this inventory, not evidence of absence elsewhere.

## Prior work and access disclosure

Read capture-reference.md, applicable captures-needed.md sections,
M-FRC-VIABILITY.md, M-PHASE0-LCA.md, M171-aperture-reference.md, and
experiments/quality-october20/report.md. Searches used both research.py and the
mandatory prior_art.py helper.

The fabric 7-aperture-pairs set was historically marked HOLDOUT - QUALITY for
M171. The current owner explicitly supplied it for this new task, authorizing
this inventory and overriding that old lane restriction. Its sampled embedded
previews are now exposed for this task. Do not describe it as an unseen holdout
in later quality claims. The separate requested/sealed 407-frame session was
not accessed.

## Reproduction and artifacts

From the current worktree, with Python 3.12, Pillow and installed ExifTool:

    python -X faulthandler experiments/multi-stack-2026-10-28/corpus/inventory-captures.py
    python -X faulthandler experiments/multi-stack-2026-10-28/corpus/summarize-inventory.py

Both commands ran successfully. The first took 21.282s; this is an inventory
receipt, not an optimized engine benchmark. It used serial metadata/preview
extraction and streaming SHA256 reads; host load was not instrumented.

- inventory-table.md: all 48 directories and sampled exposure/time ranges.
- summary.json: identities, sampled metadata/hashes and census checks.
- inventory.json: full RAW filename/size/mtime census and sampled records.
- contact family JPGs: inspected overviews.
- previews/: untouched extracted camera JPEGs, hashes in the inventory.

Generated inventories and private previews remain local and are ignored by Git.
No product code or merge defaults were changed by this discovery lane.
