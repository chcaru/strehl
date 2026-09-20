# Focused star-sand source attribution

One measurement replay, no new reconstruction or registration. Root runs after
independent review. The author does not execute RAW, build, or judge these views.

Inputs are all **259** originals DSC00016.ARW through DSC00274.ARW from
`D:/personal/macro/requests/misc-diagnostic/star-sand-cpl`. The selected source
ordinals are116/118/120, filenames DSC00132/DSC00134/DSC00136.ARW. Prior native
inspection establishes them as detail-bearing, not universally best across the
sloping surface. Global map reference stays129; the existing local-placement
experiment and its negative photographic result remain closed.

Use the fresh `through-focus-events/build-1/cli-tests.exe`, its executable receipt
and complete source manifest. The old build3 manifest is not asserted to match
current sources. The unchanged `matched-source-tests.rs` must retain SHA256
`093e25703bd86a303c95edbc557c253359365557d396364baa7dbdb9b6782111`
and appear in the fresh manifest. Any stale source binding refuses before the
RAW replay; do not bypass it or silently substitute another binary.

The sole invoked test is
`merge_cmd::matched_source_tests::matched_source_actual_consumer`.
Hold the old map SHA256
`6594d98255383218a3114fd783bfd0e2215b39b202777f1ee2e493f4b287a6a1`,
crop quads[77,52,3362,2240], rounded actual GPU MHC/Catmull consumer, existing
capture-resolved optical correction, native seven-band default, pinned tone
black0.01566/white0.51099/contrast0.55, WB and levels. Local correction is absent.
The complete image is **6724x4480**; the runner asserts that exact shape.

For each selected source, request native output ROI[472,1352,328,328]. The
existing hook exports raw-source, actual gathered and final merged CFA, camera
RGB and developed TIFF patches. Each has PAD4 and336x336 samples; remove exactly
four native pixels per side for the328x328 PNG. The TIFF ICC profile is retained
in every PNG and must match the complete baseline; if all are untagged, that
consistent status is recorded explicitly. No scaling or alternate colour
pipeline is introduced. Raw patches are source-centred/even-rounded without
geometric gathering or CA correction, so they provide context. Only gathered
and merged views have the same reference grid.

Require the complete current observer-on RGB16 array to equal the retained
observer-off baseline, including fixed little-endian pixel SHA256
`c6a5d6a68bc67950ebfc351ef3130ccd1b84b9bf33a7934f2d40cb1822022df9`.
TIFF container/build metadata may differ; record both file hashes without
spoofing metadata. This is an exact historical-baseline check, not a second
fresh observer-off replay. Earlier neutrality at125/129/133 covers the same
hook but does not replace this new check.

Every captured merged interior must equal the independent baseline slice at
the frozen coordinates. Also check the further16-native-pixel interior and
require a deliberately wrong x+2 lookup to differ. The three merged captures
are duplicates of one field, not independent evidence. A single failure stops
attribution; no discrepancy tolerance or alignment adjustment is authorized.

The Windows job caps the RAW replay at600 wall seconds,3600 CPU seconds,
16GiB committed memory and16MiB log output, with8 threads. Full-file SHA256
before/after covers the three selected originals; all259 originals have size
and modification-time checks. That is not a whole-corpus content guarantee.
Recheck map, executable, source manifest entries, helper/runner/plan and retained
references after execution. All new outputs remain in the new experiment folder.

The independent photographic question is whether a concrete pore rim or boundary
exists in the focused actual gathered source but is absent from the full merge.
If raw context appears better but gathering does not preserve the structure,
that is a different attribution. Different source-centred coordinates, colour
stipple, brightness changes and apparent sharpness alone cannot establish either
claim. If no specific structure is lost, do not infer an acquisition limit or
commission a parameter rescue.

Root command, not executed by the author:

```powershell
python -I -B -X faulthandler experiments/star-focused-attribution/run.py --out experiments/star-focused-attribution/replay-1
```
