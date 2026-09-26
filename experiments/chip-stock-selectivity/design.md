# One complete native chip ramp ablation

Prepared for root execution only. No render, build or RAW decode has been run
by this author. This experiment does not modify Rust or any production default.

The current seven-band selection ramp is capped at8; its coarse-to-fine
exponents are approximately2,2.8,3.92,5.488,7.6832,8,8. This single ablation
uses existing CLI controls to flatten them to2. It is conditional on root's
interpretation of the pending source trace, or separately motivated by the
independently observed complete chip/Helicon-B boundary-quality gap. That
comparison does not establish matched native noise/detail superiority and is
not evidence that the competitor internally uses a flat exponent.

Historical closures remain adverse evidence: BUILD-BLEND's80-frame visual
subsamples found ramp1 softer; BUILD-HULL§14.5 found changing ramp did not
eliminate reconstruction excursions; BUILD-OUTPUT§12 rejected a default
flat1 trade on26 historical subjects. This fixed flat2 observation on the new
complete native chip is not a rediscovery of those tests. See the separate
`real-source-contributions/stock-selectivity-audit.md` for the prior-work audit.

The baseline is the corrected production delivery
`outputs/quality-september25/chip-fixed`: all299 original ARW files, held map
SHA256ce8534c9e65c5c761373bad87df5352c1c46319b7eaf7f7c91477ea61b4f4922,
reference149, native crop[133,89,3250,2166] and6500×4332 RGB16 output.
The driver copies its exact invocation and environment, with the same corrected
production executable SHA256bec4c357836ad1383800a6c933460ee7ef072c525b5957a6f5deb5194b203314.
Only two argv values may differ: `--pyramid-sharpen 1.4` becomes `1.0`, and
`--out` names a fresh file. Both changes are explicitly asserted and recorded.
The actual candidate banner must report all seven exponents2, ramp1.0, unchanged
camera/geometry settings, plain mean base and299 placed sources.

No exposure tweak, new alignment, parameter search, local mask or treatment is
added. All original file hashes, order and mtimes are checked before and after.
The retained map, baseline, executable and source dependencies are rechecked.
Output directories must be fresh and inside this experiment folder. Existing
masters and original captures are never overwritten.

The normal production writer automatically fits tone independently per arm.
The driver records both actual rounded tone log lines and explicitly sets
`tone_anchors_exactly_pinned=false`. These logs do not provide exact shared f32
anchors. A darker image, histogram change or stronger apparent contrast alone
is not evidence of better structure. Do not call this a fixed-tone comparison.

The independent reviewer freezes the existing seven chip regions in
`targets.json`, translated from the older manual inset into the current common
crop. No new region search is allowed. The384-pixel rail view remains native;
each512-pixel region is covered by four unresampled256-pixel tiles. Baseline and
candidate use the same RGB16-to8bit conversion and ICC. Full-resolution TIFF,
full JPEG and complete overview accompany every comparison; native regions
support detailed inspection but never replace the full stack shown to the user.

Photographic acceptance requires cleaner contact separation or compactness at
the complained-about boundaries while preserving real tracks, scratches,
contact interiors and colours across all seven controls. A smoother surface
paid for by lost lines/texture fails. No gradient, clipping count, estimated
noise or reduced colour stipple score can admit the image. These natural
controls are not calibrated flat fields, so no noise-neutrality claim follows.
A null or visible damage closes this one arm without a sweep or default change.
A useful result would still require an independent complete marigold transfer
protecting both source-supported hair depths.

The render child is bounded to300 wall seconds,1500 CPU seconds,8GiB committed
memory and8MiB log output. The retained baseline used109.25 operational seconds
and about3.2GB Job commit; this is a resource margin, not a speed comparison.
Original-hash audits and JPEG/native-view preparation are outside render-child
timing; total wrapper time is recorded separately. Completion leaves the visual
verdict unset for independent review.

Root command, prepared but not run:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B -X faulthandler experiments/chip-stock-selectivity/run.py --out experiments/chip-stock-selectivity/run-1
```
