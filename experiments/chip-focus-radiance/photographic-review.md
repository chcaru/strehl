# Independent complete-chip photographic verdict

VISUALLY REVIEWED, 2026-09-25: **reject this fixed candidate as an overall
quality improvement.** The complete image has visibly less broad coloured
spread, particularly around the upper-left contacts and large compartment
edges. That is a real visible change worth recording. At native scale it also
softens or removes protected internal structure, thin subdivisions, stipple and
fine scratch branches. The smoother complete view does not satisfy the detail
protections. No production promotion, cross-scene transfer or width tuning is
supported by this observation.

I inspected both complete overviews in their common orientation, then all
25 fixed unresampled native pairs (50 PNGs), without selecting new crops or
changing display processing. The seven regions below enumerate all inspected
tiles; coordinates are the saved delivered-native top-lefts, not recentered
points. Rail is 384 square; all other tiles are 256 square.

| Region and inspected top-lefts | Independent visible finding |
| --- | --- |
| Rail crossing: (1098,958) | Broad pale/coloured spread across the yellow interiors is reduced. Main long rails remain, but horizontal crossbars and their internal alternating divisions are appreciably softer; fine scratches are weaker. Cleanup with detail loss. |
| Upper colour: (1036,196), (1292,196), (1036,452), (1292,452) | Rectangles remain recognizable, but narrow horizontal subdivisions and fine dotted interiors lose separation. The two lower tiles have less bright coloured spill, yet their repeated lines blur together. Darkening or reduced granularity cannot rescue the lost structure. |
| Central stipple: (2976,1306), (3232,1306), (2976,1562), (3232,1562) | Large compartment boundaries are quieter. Narrow edge stripes and triangular lined facets soften; the lower-left coloured stipple is visibly smeared, and lower-right repeated internal bars lose fine texture. The protected fine pattern does not survive intact. |
| Lower array: (566,2796), (822,2796), (566,3052), (822,3052) | Cell positions and gaps remain, but cyan boundaries and bright joints broaden; dark-cell texture is less resolved. The right-hand divider appears cleaner in colour while its fine scratch definition weakens. This is not improved native contact separation. |
| Lower colour: (4666,3016), (4922,3016), (4666,3272), (4922,3272) | The first tile's broad green spread retreats markedly. Across the other three, fine horizontal contact patterns, small dots and striped triangular facets soften or disappear. The new smoother dark surroundings coexist with loss of supported detail. |
| Surface scratches: (4856,1256), (5112,1256), (4856,1512), (5112,1512) | Main long scratches remain visible, but their fine branches, small marks and local edge definition are substantially suppressed. The large olive areas become smoother. These views alone cannot establish sensor-noise reduction; they contain scene structure. |
| Upper-left contact grid: (48,336), (304,336), (48,592), (304,592) | Strong yellow/green/white spread between repeated contacts is greatly reduced, a conspicuous complete-image benefit. Individual contact boundaries, tiny connectors and interior texture become broader/softer in every tile. This border control therefore fails retention despite its attractive overview cleanup. |

MEASURED identity and scope: the saved successful receipt covers all 299
sources in one canonical pass at reference149, crop [133,89,3250,2166], native
6500x4332. The comparator's RGB16 and ICC match current production; the pinned
baseline rewrite is whole-file identical. Model SHA remains
`9aa704e4cbea5f9193aa98e8d63c5abec3a983202a48c84e8d6a6da75a39c8fd`.
Candidate total mass is finite and positive (15.686945 to 19.014545), and the
whole-field latent front ranges 0.217839 to 0.869267. Those ranges validate
arithmetic support; they do not prove focus correctness in extrapolated borders.
Source metadata and captured compiled-source bindings remained unchanged.

Tone settings, WB, matrix and writer are pinned, but the changed radiance can
change their per-pixel response. The candidate changes DC and all frequency
content together. This pair cannot isolate whether the cleanup comes from
removing the mean base, enforcing coherent source weights, the fitted front,
or their combination. Nor does it distinguish bandwidth blur, focus prediction
error or actual gathering/placement mismatch as the cause of detail loss.
The prior two-band proxy admission remains false; no physical glare diagnosis or
new general failure claim follows from this single photograph.

The full observation completed successfully (root job 131.813 s; receipt
internal elapsed 131.645 s). This includes the baseline and candidate workflow
and is not a standalone candidate-speed or SOTA-speed claim. Root commands:

```text
python experiments/chip-focus-radiance/run.py full --build experiments/chip-focus-radiance/build-3 --controls experiments/chip-focus-radiance/controls-2 --out experiments/chip-focus-radiance/full-1
python experiments/chip-focus-radiance/run.py views --run experiments/chip-focus-radiance/full-1 --out experiments/chip-focus-radiance/views-1
```

Complete outputs, suitable for showing the owner the entire comparison:
`full-1/output/{baseline,candidate}.tiff` and
`views-1/{baseline,candidate}-full.jpg`. Both complete overviews and all native
tiles are retained in `views-1`; no crop substitutes for the full output.
Receipt SHA256:
`2dd0919cbf4a8f29fa4aec091197447d3c2371bb03b9487b85e6991cc302b958`.
Views manifest SHA256:
`4e2f35f6b0f23315cbd8b2c60aec6787e25e45b2df602b0672ae65397df530ec`.
Candidate RGB16 SHA256:
`9215e7b6f01ed9153b1bf56b45aa7102fa47b1be5a9364e914cbf8617eef978f`.
