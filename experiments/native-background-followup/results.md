# Upper-right background inspection — outcome

VISUALLY REVIEWED: a compact dark mark near native sensor position (6404,238)
persists in original coffee-bean frames 0 and 104, in both green phases.
It is visible in the common fixed-DN display, before the optional stretch.
This supports sensor-coordinate persistence. It does not establish physical dust
or prove this mark's contribution to the delivered diagonal streak.

VERIFIED: the embedded, locally measured camera map already contains exactly
`d 3202 119 1.036653`, corresponding to native top-left sensel (6404,238).
The map was built from 160 flat fields; it is not Sony vendor metadata.
The earlier custom left-mark sidecar replaces this embedded map, so that
photograph did not apply these existing nominations. No new detector is needed
to nominate this site. Existing per-stack validation is still required.

The original fixed diagnostic STOPPED before viewing: all 720,896 sensels and
eight phase-pair hashes match between independent decoders, but 22,437 codes
in frame 0 meet the product's 15360 white threshold (frame 104: zero).
That is not a physical-saturation count; LibRaw declares 16383. The original
failure is preserved, along with the independently acknowledged scope error:
a whole-support white check was unnecessarily strict for descriptive viewing.

The separately committed display amendment reads the retained full ROIs, without
another decode, resampling, changed crop or per-panel stretch. Its separate
15360/16383 masks expose display clipping. Within the unchanged sensor target,
frame 0 has four codes >=15360; its mapped target bounding box has two.
Frame 104 has none; all four target boxes have zero codes >=16383.
These local counts do not qualify the failed whole-ROI gate. Mapped boxes
have unequal areas, and the pooled stretch clips spot cores to black.

SOURCE-VERIFIED: the current production RAW loader and full-resolution gather
retain values above 15360. The u16 writeback bound is 65535, and output
normalization retains values above 1. M54 already measured coffee-bean's
histogram smooth through 15360 and piled up at 16383. This lookup identifies
no new RAW-ingest clipping defect or justified white-level calibration change.

The only product-source edit is a comment correction in stack.rs: V-MOTE
adjudicated the former 17x disagreement. Default-off behavior is unchanged.
Current gain-to-variance propagation remains incomplete; the rejected local
approximation does not become acceptable because another visible mark exists.
Independent review confirmed all 2,215 non-doc-comment lines unchanged.
The initial comment write hit Windows encoding and temporarily emptied the
previously clean file; root restored it from clean 4c4a733, applied UTF-8
atomically, and refreshed its mtime. No build was running; no source was lost.

Execution sources: diagnostic 7f5b746c99da9b49e954965cdfb899b964155045;
display 4c4a733db072eef8fec7946abc75ee28739639b9.

Commands actually run:

```powershell
python -I -B experiments/native-background-followup/run.py
python -I -B experiments/native-background-followup/display.py
```

The second command was launched once through the existing bounded Job helper;
its exact argv and terminal accounting are retained in display-invocation.json
and display-process.json. The first run used five bounded children.
MEASURED: diagnostic 1.953125 CPU / 2.015 summed child-wall seconds;
display 0.296875 CPU / 0.391 wall seconds. Combined 2.25 CPU seconds.
Peak diagnostic Job commit 125,128,704 B; display 72,101,888 B.
No new build, alignment fit, whole-stack render or original RAW write.
All children ended; the failure was an assertion, with no resource intervention.

Decision: close this inspection. Do not fit another custom mark or repeat RAW
decoding to rediscover an existing nomination. The previous corrected photograph
remains the only new photographic intervention in this branch. General
alignment/detail quality and a fair complete-workflow comparison remain the
program priorities; no SOTA claim follows from this inspection.

Independent evidence: independent-results.md and independent-display.md.
Retained views: view-2/fixed-dn.png, pooled-inspection-only.png and
white-threshold-masks.png. Raw arrays remain local, bound by saved receipts.
