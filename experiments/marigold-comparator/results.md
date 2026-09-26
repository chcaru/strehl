# Complete marigold reference: no overall replacement

MEASURED / VISUALLY REVIEWED, 2026-09-26. All 488 originals were developed with
the native decoder and exact Current development, then stacked once with Helicon
B, radius 8 and smoothing 4. Both complete outputs and full-resolution masters
were shown to the owner. The independent reviewer and root inspected both whole
views and all three fixed native counterpart pairs. No overall B improvement is
established; it is not a clean target or presumed ground truth.

Some near hair tips appear better separated, while diffuse overlapping structure
remains. Bright petal interiors acquire large milky bands. In the upper folded
cup, those bands strongly weaken and interrupt a long fine strand visible in
Current; a lower portion remains. Darker/yellower bright-petal rendering does
not establish recovered texture. Current's defects remain open. See the separate
photographic-review.md for the precise observations and manual correspondence
limits. No parameter sweep or production promotion follows.

Both the existing independent u16/development golden and the complete Current
CFA-cache rewrite pass exactly in RGB16 and ICC before source development. The
ordered recipe matches the corrected cache's source-order hash. All prepared
TIFFs are content-hashed before and after vendor processing; original content
is checked during export and original metadata is unchanged afterward. No
original is written. Full vendor output is 7032x4688 RGB16; Current is 6268x4176.
There is no obvious trial overlay in the inspected complete views, which is not
an exhaustive pixel-level absence proof.

| Stage | Operational wall seconds | Peak Job committed bytes |
| --- | ---: | ---: |
| Fresh run-2 exporter build | 25.125 | 468,971,520 |
| Sequential 488-source development | 253.969 | 423,579,648 |
| One complete B process | 68.735 | 35,109,167,104 |

These are single bounded process readings, not controlled speed comparisons.
The vendor timing excludes preparation and wrapper input hashing. The first
build's successful compiler and failed immutable-document check remain in
run-1; first-build-refusal.md records why a fresh build was needed. No capture
was decoded from that refused build.

Executed from the workspace with Python 3.12 `-I -B -X faulthandler`:

```
experiments/marigold-comparator/run.py build --out experiments/marigold-comparator/run-2
experiments/marigold-comparator/run.py develop --out experiments/marigold-comparator/run-2
experiments/marigold-comparator/run.py b --out experiments/marigold-comparator/run-2
experiments/marigold-comparator/comparison-1/extract.py
```

Current TIFF SHA256:
19e657e419d52adf567ec86472f917ad9b9abfc9b0812131e9bba0eacbae462f

B TIFF SHA256:
30740f1c0c9cd9c5d24112121117b76da8444da0951ba26408dd5f365385cee5

B RGB16 SHA256:
4bc00a63663e49370b80d59ec4cc0db0c19918021a24ca8fd644c46aec3cfc42

Same decoder and development do not isolate fusion: prepared inputs are CA-off,
individually demosaiced and developed before vendor alignment/fusion. Current
gathers CA-corrected CFA and develops after merging. Other persisted vendor
settings remain unknown. The next independent registration pilot is motivated
by unresolved Current artifacts, not by a claimed vendor geometry advantage.
