# V-HEADTOHEAD3 — 113 cover-border profile amendment

**Frozen before rendering or opening either new two-band arm.**

## Question, prior, and bias

The completed cover arm compared the same 63-frame `113MSDCF` stack under
shipping `cover=scale` and `--cover crop`, but its 256-pixel ROI clearance came
from prior BUILD-CROP evidence rather than a profile on these exact renders.
This amendment measures whether the 113 crop's seven-band pyramid carries a
border-local effect beyond that clearance.  It cannot reinterpret ordinal
power as resolution.

Bias is toward finding that the existing 256-pixel clearance is sufficient,
which would preserve the published geometry/band-power observation.  Contrary
prior evidence is explicit: independently commissioned COVER profiling
(`c40a965e`, final report `66e79043`) found a 256-pixel safe inset on
`109MSDCF`, while a second subject defeated specificity and licensed no finite
all-stack inset.

## Frozen inputs and renders

Existing seven-band inputs:

* scale:
  `113-cover-scale-control.tiff`,
  SHA-256
  `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`;
* crop:
  `113-cover-crop.tiff`,
  SHA-256
  `5B5F863AB2602EA18DB995FEA6361D4AB86B8FF24ECBCB9D2A470E637091F18B`;
* executable:
  `C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`,
  SHA-256
  `2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`;
* source manifest:
  63 ARWs plus 63 XMPs, digest
  `A6275BE83552AC1BE4E23381A42BF1024FB33C217A9529DCDCC018BB4992AC5D`;
* cached warp map:
  63 frames, 63 placed, reference 31, SHA-256
  `A5DF650CCE1224A7B6F54B5570B0BC1E643F1728B030D2496BD2BC13E462623E`.

The independently commissioned geometry port reads the serialized map as
`k=0.9808883167827137`, hence `1/k-1=1.9484056329646338%`, and crop rectangle
`(x=34,y=23,w=3448,h=2298)`.  This exact value, not the earlier scorecard's
between-render disagreement, is the coverage resample magnitude.

Two new two-band controls use the same executable, capture, private cache,
alignment, colour path and output encoding:

```text
strehl.exe stack D:\personal\macro\113MSDCF
  -o <scale-b2> --srgb --pyramid-bands 2

strehl.exe stack D:\personal\macro\113MSDCF
  -o <crop-b2> --srgb --pyramid-bands 2 --cover crop
```

All inherited `STREHL_*` variables are cleared except the same private
`STREHL_CACHE_DIR`; Rayon and numerical libraries are capped at 8.  Each log
must report 63/63 placed, zero refused, the same four-place `k=0.9809`, and
the crop must repeat the exact rectangle and unity-scale statement.

## Fixed profile and interpretation

For each mode, compare green-channel seven-band and two-band renders on their
identical native grid.  In fixed distance-to-emitted-border annuli

```text
0,2,4,8,16,32,64,96,128,160,192,256,320,384,448,512,640,768
```

compute

```text
E(d) = (mean_G(bands7,d) / mean_G(bands2,d)) / R_deep - 1,
```

where `R_deep` uses pixels at least 768 pixels from every edge.  The safe inset
is the smallest registered boundary at or beyond 8 pixels for which
`abs(E)<=0.001` in that and every deeper annulus.

The profile is specific only if the scale control's safe inset is 8 pixels.
If specific and crop's safe inset is at most 256, the existing frozen ROIs
(minimum crop clearance 256) pass.  If crop exceeds 256, the old band-power
observation is retained only after filtering the already frozen sites to the
measured inset, without replacement, and satisfying the original minimum
counts.  If the scale control exceeds 8, no finite 113 black-fill reach is
claimed and the prior 256 clearance is not relabelled as newly validated.

This is a geometry and absolute band-depth profile, not sharpness, resolution,
MTF, or proof that a profile difference comes only from black fill.

## Commissioning

Before real pixels:

1. a known 2% outer 16-pixel ring must read `E=0.02` and safe inset 16;
2. improving it to 0.05% must reduce the safe inset to 8;
3. an unplanted gradient null must remain at 8;
4. swapping bands, omitting deep normalisation, changing the 0.1% threshold,
   or changing an annulus edge must go RED;
5. exact hashes, command arguments, frame count, `k`, crop rectangle and
   source manifest must be fail-closed.
