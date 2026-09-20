# Slide2 source attribution: bounded null at source149

**MEASURED / independently VISUALLY REVIEWED.** The complete 299-frame observer-off/on pair is identical. Source149 (`DSC00150.ARW`) is insufficiently focused at the selected bar targets to establish a missing-source-detail defect. No quality gain, capture-resolution limit, or CA-cause conclusion follows. The independent photographic findings are in [slide2-source-review.md](C:/dev/blog/death-of-software/projects/strehl/experiments/quality-september20/slide2-source-review.md).

![Complete matched slide2 result — overview only](C:/dev/blog/death-of-software/projects/strehl/experiments/quality-september20/slide2-source-1/matched-overview-only.png)

The complete result is available as [native 6476×4316 PNG](C:/dev/blog/death-of-software/projects/strehl/experiments/quality-september20/slide2-source-1/matched-full.png), [observer-off RGB16 master](C:/dev/blog/death-of-software/projects/strehl/experiments/quality-september20/slide2-source-1/off/output/replay.tiff), and [observer-on RGB16 master](C:/dev/blog/death-of-software/projects/strehl/experiments/quality-september20/slide2-source-1/on/output/replay.tiff). The overview is for orientation, not native-detail assessment.

Root ran:

```text
python -I -B -X faulthandler experiments/quality-september20/slide2-source.py
```

The runner invoked retained `experiments/raw-affinity-support/build-1/cli-tests.exe` twice with `merge_cmd::matched_source_tests::matched_source_actual_consumer --exact --ignored --nocapture --test-threads=1`, using the separately retained `off/config.json` and `on/config.json` through `STREHL_MATCHED_SOURCE_CONFIG`. Each invocation, environment, process log and receipt is in `slide2-source-1/{off,on}`. This is a historical, source-bound executable, not a claim about the subsequently edited checkout. Both runs succeeded: 91.422s off and 101.969s on; these are observed job times, not a performance comparison.

Both consume all299 originals, the held map/reference149, seven-band native consumer, selected gear CA/WB/development and crop quads `[139,93,3238,2158]`. The explicit tone is black0.005475, white0.476094, contrast0.55. Complete TIFF SHA256 is `6d79e5996493afee9e3d7ba6edc6dc37c2d4983750efc0369ec880f810feb5ca` for both, with zero differing RGB16 samples and decoded-pixel SHA256 `cdd44d049ee569144f909ef38490a402572a21a8a3490130090d25d958d1b272`. All four merged crops equal the complete-image slices, including the additional interior check; the wrong x+2 lookup differs in every region. Original metadata remained unchanged; the preceding baseline's full original-content hash audit is retained rather than claimed to have been repeated.

The historical automatic baseline remains unchanged. It differs from this new explicit pair by at most2 RGB16 DN (12,927,488 samples differ), under a different binary and six-decimal pinned tone. That provenance difference is not image-quality evidence.

The four preselected 384px regions were medium-bars `[2592,1584]`, fine-bars `[3576,1710]`, lettering `[2772,2106]`, and pale-control `[792,600]`. Independent review found medium/fine bars and their numerals substantially blurred in149, while the merge separates them. Letter openings are present in149, but merged strokes and the thin rule are crisper; no resolved source stroke or separation was identified as lost. Pale-control is not a calibrated flat/noise reference. Raw views are source-centred/even-rounded without CA/warp; only gathered/merged views share pixel coordinates. This closes only the source149 attribution question and does not rule out useful information in other sources.
