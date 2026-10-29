# Complete reconstruction and regression checkpoint16

MEASURED/VERIFIED, with photographic outcome still open. Both retained chart
arms completed all126 originals and7197 tiles. The older14c arm was allowed to
finish; it was not terminated or replaced by the faster run.

| Arm | End-to-end seconds | Reconstruction seconds | Sampled private peak | Coherent replacement pixels |
| --- | --- | --- | --- | --- |
|14c, prior single-tile-sized original cache and green appearance gate|4678.898|4355.290|9,770,020,864 bytes|150455|
|15, session-sized bounded original cache and all-color gate|1078.010|749.379|11,736,682,496 bytes|149759|

Both used16 workers and48GiB requested budget, the same saved native14c map,
precision weights, contribution maps and original-CFA option. They ran alongside
different owned work, so this is observed completion/resource evidence rather
than an isolated speed ratio. The separately frozen69/127/127/69-slot ABBA
establishes the cache-preparation change with exact original-observation hashes;
its timings are preparation only. See production-integration-15.md.

The complete7197-record comparison preserves every source/guide selection,
skip, graph witness, geometry certificate and consuming-pull bit.5002 tiles
carry witnesses;1086 pass geometry in both arms. Exclusions are elapsed seconds,
region-sampler peak memory and intentionally changed replacement counts. There
are no remaining geometry differences. Receipt:
outputs/multi-stack/completion/sr-registration-comparison-15-complete.json.

Both complete6928x4620 photograph/master pairs are finite, all map/record hashes
and counts reconcile, and every unsupported native RGB triple is bit-identical.
The14c arm changes150330 pixels;15 changes149636. Exact readback receipts are
sr-chart-full-readback-14c.json and sr-chart-full-readback-15.json. The independent
whole-photo plus13 frozen native-witness reviews find no obvious reviewed seam
or hole, but no established recognizable-detail improvement. More support or
lower runtime does not close the intended photographic outcome.

## Bounded insect revisit

The actual corrected global estimator was revisited on the preselected insect
ROI0 and ROI1 under the frozen insect-global-plan.md. The legacy16b replay
matches all20 original array/TIFF pixel artifacts exactly. The exact product RGB
appearance helper is then used at both saved/corrected pulls. Both ROIs have
zero coherent replacement, and their entire output remains exact native. ROI0
accepted graph edges are7/0/8RGB; ROI1 has0/4/0. Both lack cycles. Eighteen
original cache payloads per arm are verified, with zero RAW decodes.

The three bounded runs took2.698/3.587/2.565s and approximately1.202GB private
under concurrent work. Binary SHA is1236c3eb249708bcae830579210eb6496701bb6fb47615418791efcf7dd33d72;
build16b binds all current reconstruction/motion sources and exact product16
support libraries. sr-insect-global-summary-16b.json records commands, hashes,
all artifact comparisons and fixed plan identity. These are geometry-negative
pilots; zero held-prediction support supplies no image-quality comparison.

An independent audit distinguishes missing held-patch coverage from retained
vectors that contradict the placement bar. The new diagnostic census records
every predefined seed/fitted probe after the ordinary estimator completes.
Additional probes never feed fits, admission or certificates. Flat/clipping
controls passed before the18-test registration module rerun; exact unchanged
evidence/footprints and information decisions are checked for textured and
one-axis originals. The initial test compilation error was a missing closure
type annotation, retained in sr-patch-diagnostics-flat-01. Successful receipts
are sr-patch-diagnostics-flat-02 and sr-patch-diagnostics-all-01. Real diagnostic
replay is separate from these controls.

## Ordinary pipeline and desktop

Fresh product16 ordinary299-source regression retains every7032x4688 photograph,
linear-master and sensor-master pixel bit. Actual GPU16 verifies independent-view
zoom/reopen and strict SR import/support inspection. See
../review/broad-validation-02.md and ../review/ui16-actual-gpu-review.md.

Commands actually run are retained in the named run receipts. In addition:

```powershell
python experiments/multi-stack-2026-10-28/completion/sr/verify-full-reconstruction.py outputs/multi-stack/completion/sr-chart-native-14c outputs/multi-stack/completion/sr-chart-full-14c outputs/multi-stack/completion/sr-chart-full-readback-14c.json
python experiments/multi-stack-2026-10-28/completion/sr/compare-reconstruction-registration.py outputs/multi-stack/completion/sr-chart-full-14c/reconstruction/tiles.json outputs/multi-stack/completion/sr-chart-full-15/reconstruction/tiles.json outputs/multi-stack/completion/sr-registration-comparison-15-complete.json --count 7197
python experiments/multi-stack-2026-10-28/completion/sr/run-insect-global.py --binary outputs/multi-stack/completion/sr-insect-roi-build-16b/roi-pilot.exe --tag 16b
```
