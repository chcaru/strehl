# Fixed-focus repeat reconstruction evidence

The completed32-source bee sequence has a fixed focus setting, but the sweep
focus observer qualifies only393/4137 pixels in its two passes. It must not
fabricate a peak, width or depth for a plateau. A distinct repeat-compatible
state requires original-image PSF/appearance evidence; metadata only nominates.
The matching compatibility work is responsible for that shared evidence.
Flat regions alone cannot certify PSF or new detail, and a stable defocused
plateau may be useful for averaging without being called sharp.

First use only the frozen Q/V acquisition identities, not the reserved R/M
assay observations. Global IDs are0,3,4,7,8,11,12,15,16,19,20,23,24,27,28,31.
Chronological first/last Q/V (global0/15, ordinals0/31) are disjoint guides;
the other14 are targets in chronological order. No candidate image selected
them. Preserve the same nine384-pixel witnesses from the independent full
photo review; the central192 areas are `origin_full_sensor + [96,96]`.
The existing joint geometry used all32 acquisitions and is explicitly
conditional, not independent of the eventual scored photons.

The read-only `bee-phase-opportunity.py` first rejects duplicate phases and
accepts a known complete phase lattice. On the saved geometry it finds100/100
potential RGB sites in each of the nine fixed areas with the unchanged positive
Gaussian0.35sensor taper and condition limit20. It reads no original pixels.
This is sampling feasibility only: no clipping, measured local geometry,
appearance, focus/PSF, optical bandwidth or photographic result follows.
Commands and exact identities are in `sr-bee-phase-opportunity-run-01` and
`sr-bee-phase-opportunity-01.json` under outputs/multi-stack/completion.

Next run cache-only original-CFA geometry at all nine fixed central192 areas,
four workers, two-GiB checked limit,14target and two guide handles. Fixed
192quad original context,46quad patches,3-by-3 grid, sigma1.2quad, unchanged
0.15sensor held bound and all original train/held footprints/global triangles.
`--geometry-without-focus` requires `--registration-only`: every source's
focus admission is false, no focus field is claimed/exported, and execution
returns before reconstruction. This diagnoses geometry without interpreting
missing sweep focus as a repeat certificate. Render/prediction combinations
are forbidden by argument controls. Retain all nine failures or successes.

Only after actual compatibility controls may repeat-plateau eligibility enter
the reconstruction consumer. Required negatives include fine focus changes
with nearly equal scales, channel-only blur, periodic wrong placement, local
motion, lighting/drift and low-power UNKNOWN. Signal transfer is per channel;
a lower noise/error statistic caused by blur is not a useful result. Mainline
focus-sweep semantics remain unchanged. No full SR photograph is released yet.

## Geometry-only outcome

**MEASURED:** all nine fixed regions were evaluated by the17g original-CFA
producer, with16 cache hits and zero RAW decodes per region. The actual runs,
commands and resource receipts are `sr-bee-run-17g-geometry-roi0` through8;
`sr-bee-17g-geometry-summary.json` collects their outcomes. Each source retains
zero focus-admitted pixels; no candidate photograph or focus map was generated.

The brow-hairs region at sensor origin[3687,1858] has6 of14 sources with coherent
RGB geometry under the unchanged0.15sensor held/loop bound: global IDs
[3,4,20,23,12,28]. Its RGB graphs have17/25/19 passed edges and cycle ranks5/12/7.
The other eight regions have no all-RGB admitted source. Chin has some supported
edges but no qualifying anchor-triangle intersection; that distinction is kept.

**DERIVED conditional sampling opportunity:**
`sr-bee-registered-phase-run-01` runs the actual phase operator on every one of
those nine saved geometry reports after the duplicate-phase negative and known
phase-lattice positive. `sr-bee-registered-phase-01.json` binds each complete
report hash and checks original identities, gauge and zero focus admission.
All100 predeclared brow positions retain RGB phase condition<=20 using only the
six qualified corrected placements. R/G/B condition ranges are5.373–13.789,
2.159–2.673 and4.226–11.247. The other regions have zero qualified phase sites.
No original samples are read by this calculation; it neither establishes repeat
compatibility nor clipping, actual heteroscedastic precision, optical bandwidth
or visible resolution gain. Equal-mean native-band compatibility also cannot be
assumed to characterize every useful phase-dependent alias for reconstruction.
