# Independent attribution source review

VERIFIED by source inspection: no blocker in the immutable observer. Frozen
SHA256 bindings reviewed:

| File | SHA256 |
| --- | --- |
| core-attribution.rs | 34a2209debf47b4c97225b034d487fc6d6f319a9fc6790a877110b08468941ed |
| attribution.rs | 82e2ca350cb97cf36048d6ea59e8379d2dbe1ba30f70f46900a343da6b84b976 |
| core-bridge.rs | 549bee46241c4986ed0b520260bd073fd611ad418ea0d268c66230203dfef2e2 |
| full-stack.rs | b530cea2a0f406430b705ba171fd7ebaa2f00c374d7b93b154ba0939f2358fc0 |

The core resolves the actual normalized baseline coefficients and prescribed
donor coefficients. It multiplies masks before full-context collapse, clears
each isolated band, and extracts windows only afterwards. Terminal base and
original sample hull are shared. Negative terms and hull corrections remain
signed. No expanded mask is interpreted as an output-pixel ownership weight.
Memory is fixed with respect to frame count; there is no aligned source volume.

The writer stores planar R/G1/G2/B little-endian f32, checks append lengths,
uses separate arm/region/field/level files, and hashes completed arrays.
Candidate and late PostHull windows must match delivered f32 planes bitwise.
The absent environment variable returns before observer computation. The
full-stack diff adds only observer construction and calls after the respective
TIFF writes; baseline, donor accumulation and development arithmetic are intact.

MEASURED by root, independently inspected here: `controls-3/process.log` and
`controls-3/output/screen.json` record all three tests passing. The new signed
observer control reaches 14,910 opposed-sign cancellations, four actual clamps
(largest 607.757324DN), 0.000122071DN maximum field error and 0.000761629DN
reconstruction error. Odd-domain crop extraction and observer output neutrality
are exact. These are operator tests, not photographic quality measurements.

`full-on-2/neutrality.json` records exact decoded RGB16 equality for baseline,
candidate and late arms across off/on/original runs; off/on TIFF files are also
byte-identical. Commands and environment are retained in `controls-3`,
`full-off-2` and `full-on-2` invocation.json files. This reviewer authored the
independent controls but performed no builds, execution or RAW reads.

The signed source-DN fields support accounting of this reconstruction only.
Cancellation, original hull limiting, later MHC, WB and tone prevent treating
their absolute values or positive fractions as source ownership or quality.
