# M8 comparative controlled execution preregistration

Frozen before generating any synthetic outcome, decoding any subject frame,
running the comparator, or evaluating M8-O.

## Status and subject

This is an unlicensed, candidate instrument-commissioning arm. It is not a
scorecard row and can never become one.

The registrar granted exactly:

```text
subject: tilted-sw10-cpl
source:  D:\personal\macro\requests\misc-diagnostic\
         high-res-calibration-slide-cpl\tilted-sw10-cpl
N:       92
session: complete 2026-09-02 calibration-slide session, burned development
```

Every `*.ARW` directly in that directory is selected, in case-sensitive
filename order. No sibling is selected. In particular, `tilted-sw4-cpl` and
every `flat-*` stack are forbidden. `D:\personal\macro` and
`D:\edited\macro` are strictly read-only.

The names and sizes are frozen in
`source-inventory-preregistered.json`, SHA-256
`8163077E1EE511C9F7136F45FCF5294906BBEFD879AD0568B76C008ACFD324BF`.
It contains 92 entries, recomputes stack digest `3c8796d7fd1acf46`,
and puts `DSC00062.ARW` at registered reference index 46.

## Frozen artifacts

| artifact | SHA-256 |
| --- | --- |
| frozen RAW decoder, `D:\strehl-out\cover-default\target\release\strehl.exe` | `1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F` |
| placement sidecar, `tilted-sw10.warpmap.txt` | `DB982BEDAE1172EB51D5787F4C6746C1FD552E33077CCAFAD5469BC96D6B10D1` |
| comparator, `C:\dev\macro\focus-stack\dist\focus-stack.exe` | `0ABA0CF0936AF8B1CACE2681CA43D49729D253E8ED1F786F2A8960B7974CA45D` |
| unchanged M8 checker copied as `checker.py` | `B66C9465D5F644D66646A14722475987F187E32B02ED3B687997C18CE1670B89` |

Any mismatch is `UNMEASURED`.

## Prepared-input boundary

Each RAW is copied one at a time into scratch and decoded with the frozen
binary:

```text
strehl.exe stack --limit 1 --merge estimator --photometric off
  --linear-srgb --out <decoded.tif> <one-file-directory>
STREHL_ALIGN=0
```

The expected decode is `3516 x 2344 x 3`, uint16, linear sRGB/BT.709
primaries at D65 with no transfer curve.

The exact registered reference-to-frame f64 placements are read from the
frozen sidecar. They are applied as pulls with OpenCV `INTER_LINEAR`, float32
coordinate maps, centre `(1758,1172)`, and no inversion. The crop is frozen
from the already-commissioned COVER result:

```text
x=62, y=41, width=3392, height=2262
```

This crop must have valid bilinear support in all 92 frames. Failure is
`UNMEASURED`; no crop may be fitted after seeing pixels.

Before warping, decoded linear sRGB is transformed to linear Rec.2020 by:

```text
0.6274038959346991   0.3292830383778841   0.04331306568741707
0.06909728935823203  0.9195403950754587   0.01136231556630915
0.01639143887515027  0.08801330787722583  0.8955952532476241
```

Every prepared sample is rounded once to uint16. A value below zero or above
one before quantisation is a stop, not a clipping invitation. Files are
uncompressed TIFF, Orientation 1, with a deterministic matrix/shaper ICC:
ITU-R BT.2020 D65 primaries, Bradford D65-to-D50 adaptation, and identity
TRCs. Its bytes and SHA-256 are outcomes of the preregistered generator, not
selected after inspection.

The materialized, hashed prepared TIFF arrays are the M8 source boundary.
Interpolation used to create them is upstream of that boundary. Placement
inside the audited comparator invocation is identity.

## Controls before subject decode

`controls.py` must pass in full before `prepare.py prepare` will run.

1. Generate one full-size `3392 x 2262` aperiodic coordinate image containing
   eight frozen asymmetric impulses, four coded borders, whole-frame
   coordinate values, and three constant RGB patches.
2. Give the comparator 92 byte-identical hard-linked copies through the exact
   subject invocation and output path.
3. Test only the registered identity map. Every marker and sampled border must
   be within 4 DN, every constant-patch median within 4 DN, and at least
   `0.999` of output coordinates must be within 4 DN of the registered input
   coordinate. Dimensions, uint16 type, Orientation 1, and ICC must match.
4. RED plants `+0.25 px` translation, scale `1.001`, 90-degree orientation,
   one-pixel crop then resize, gamma encoding, channel swap, and wrong ICC
   must each reject.
5. Restoring the untouched identity output must pass.
6. The ICC must parse through LittleCMS/Pillow as
   `M8 Linear Rec.2020 D65`.
7. Commission the RGB-to-checker adapter on three small frames: a hull
   respecting output must read zero; one lower and one upper two-DN plant must
   read exactly 2 total, 1 per sign; restoring the null must return to zero.

Any failure stops the subject as `UNMEASURED`. Thresholds are not adjusted.

## Comparator invocation

Pass the 92 prepared files explicitly in manifest order:

```text
focus-stack.exe
  --no-align --no-transform --no-whitebalance --no-contrast --nocrop
  --input-colorspace=linear-rec2020
  --internal-colorspace=linear
  --output-colorspace=linear-rec2020
  --output-bitdepth=16 --hdr-preserve=off --threads=6
  --output=<fresh-direct.tif>
  <000.tif> ... <091.tif>
```

Retain binary/help hashes, exact argv, working directory, stdout, stderr,
direct output, and metadata-only canonical output. If the direct output omits
the ICC, attach the frozen ICC while writing an uncompressed canonical TIFF
and require canonical pixel-array identity before and after.

Admission occurs before visual inspection or M8. It requires all prepared file
and pixel hashes, same build/help as controls, exact dimensions and sample
type, Orientation 1, canonical uncompressed encoding, frozen ICC, and the
same-N full-size identity witness.

## Reusing the commissioned checker

No second hull verdict is implemented. For each prepared RGB channel the
adapter repeats every sample into a `2 x 2` cell and emits a version-2
bilinear `.m8site` block. The unchanged checker independently samples at phase
`(0.5,0.5)`. All four reconstructed support values are therefore equal to the
single prepared sample, making its hull exactly the one-sample identity hull.
Blocks are consumed and deleted one at a time.

The unchanged checker alone declares violations using its existing
`8 ULP + 0.5/65535` tolerance. The summarizer only describes those declared
rows.

## Frozen outputs and interpretation

Report:

* all-output and valid-hull denominators;
* lower, upper and total violations and rates;
* signed extrema;
* median, p99 and maximum excess in linear units and DN;
* median, p99 and maximum excess divided by positive hull span;
* sign balance, zero-span counts, rail occupancy;
* the unchanged checker's file containing every violating coordinate.

The result is candidate-only. **M8-O can establish invention after the
declared prepared-input boundary. It cannot name the inventor.**

This is a **controlled merge audit, not a default-settings product
benchmark**. Disabling the comparator's normal alignment deliberately removes
one part of its product.

