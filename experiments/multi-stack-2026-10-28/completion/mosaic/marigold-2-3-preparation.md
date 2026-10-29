# Full-density marigold2/3 geometry preparation

This root-authorized second real mosaic candidate contains 772 RAW captures:
marigold2 has 289+144 ordered acquisitions; marigold3 has 299+40. All source
directories remain read-only. The previous 827-capture marigold3/off-center
failure remains a separate preserved result. Preview evidence (246 reciprocal
matches,110 FIT inliers,4.49 preview-pixel heldout p90) only nominates this pair.

The preparation harness invokes the frozen product15 public alignment, focus
evidence and diagnostic guide consumers. It exits before cross-view fitting or
photograph rendering. Each compact guide is serialized directly from the actual
production buffers and checked against the production guide hash; it is not a
stacked photograph. Full source hashes, pass ranges, focus ordinal-to-global
source mapping and guide/map bindings are retained. The source census and full
hashes must still match at completion.

The explicit geometry resampler is **bilinear**. This differs from the product
CLI default of catmull-rom and must remain explicit in a later matching product
invocation (`--resampler bilinear`). Each alignment envelope binds this choice.
No default-equivalence or cross-kernel quality claim is made. The source cache
is shared with the earlier campaign; the actual15 decoder cache identity found
339 existing entries and433 originals needing decoding. The standard cache
consumer still verifies every entry before use.

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/mosaic-marigold-2-3-preparation-run-01 --cwd . --env RAYON_NUM_THREADS=8 -- outputs/multi-stack/completion/mosaic-preparation-build-02/prepare-geometry.exe outputs/multi-stack/completion/mosaic-marigold-2-3-inputs/manifest.json outputs/multi-stack/completion/mosaic-source-cache outputs/multi-stack/completion/mosaic-marigold-2-3-prepared-01 8 16
```

Eight workers and a16GiB total reservation are fixed for this arm. Source-cache
prepopulation reserves3.74GiB, then releases that phase before alignment/focus.
The resident original-CFA cache is2GiB. Native pair work and focus evidence each
use their actual production resource planners; no aligned frame volume exists.
The command receipt contains host-memory samples and the exact executable hash;
the build receipt records the product15 library and included-source hashes.
Concurrent full SR work means elapsed time is not an isolated performance result.

Acceptance after preparation still requires useful spatially independent FIT
and heldout original-image matches, qualified local geometry, positive meshes,
measured loops and actual extended supported coverage. A successful preparation,
connected coarse graph or expanded bounding rectangle does not meet that bar.
The final original-CFA mosaic, masters, coverage output and independent full-image
review remain required.

**MEASURED:** preparation completed with exit0 in2461.30s under concurrent host
work, with14,358,405,120 sampled peak private bytes. Prepopulation decoded433
new originals; the subsequent actual alignment/focus/guide consumers decoded
zero and recorded3,860 verified disk-cache loads. Both end-of-run source census
and full-content identity checks passed.

Marigold2 places433/433 frames with2,522 native edges and2,090 anchor-component
cycles. Marigold3 places339/339 with1,841 native edges and1,503 cycles. Its339
serialized pose rows exactly match the prior16-worker/48GiB run, while the stored
resampler differs explicitly. `mosaic-marigold-3-placement-repeat-01.json` binds
both alignment-envelope hashes and states that this is parameter reproducibility,
not final-pixel or speed equivalence.

The direct compact guides retain499,100 covered pixels each, with22,310 and
47,361 usable focus pixels respectively. They are bound by the completed compact
receipt hash `1428bdd8a3d5383f1e839a281e1324efeb56c093715bd6a68f8d339d121aaade`
and complete source-identity hash
`b19e693713ea5a4f41be3889497dcb982f3e4014758174b4a125f7333911477f`.
The following cached-only native discovery/refinement is a separate experiment;
these complete preparations do not certify cross-view placement.
