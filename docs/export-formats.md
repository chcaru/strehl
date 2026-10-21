# Image export

Export settings are independent of the photograph's development recipe. The
default is AVIF, HDR, Rec.2020, quality 100. HDR requires the retained scene-linear
master; an imported SDR photograph can be exported as SDR but cannot acquire
missing highlight detail by changing a file tag.

| Format | Stored samples | Delivery | Color description |
| --- | --- | --- | --- |
| AVIF | 10-bit, 4:4:4, full range | PQ HDR or SDR | Matching AV1 sequence header and AVIF `nclx` |
| TIFF | 16-bit RGB | SDR | Embedded ICC matrix/TRC profile |
| PNG | 16-bit RGB | SDR | Embedded ICC matrix/TRC profile |
| JPEG | 8-bit RGB | SDR | Embedded ICC profile; lossy |

All four formats offer sRGB/BT.709, Display P3 (D65), and Rec.2020 primaries.
HDR export converts developed linear BT.709 into the selected RGB primaries,
applies the recipe's reference-white and peak luminance, and encodes ST 2084 PQ.
The selected primaries therefore change the pixel values as well as the tags.
P3 and sRGB use a signaled BT.709 YCbCr transport matrix; Rec.2020 uses BT.2020
nonconstant luminance. P3 PQ is not the SDR Display P3 transfer curve.

SDR export preserves the existing SDR preview appearance and converts those
display colors into the chosen output space using the sRGB transfer curve.
A wider output container does not create colors missing from that SDR rendering.
Strehl recognizes its own generated wide-gamut TIFF profiles when reopening them
and converts their samples back into the linear working space. Arbitrary foreign
ICC profiles remain unsupported and are refused rather than silently relabeled.

AVIF quality 100 selects rav1e's lowest supported lossy quantizer, 1. It does
**not** mean lossless RGB storage. Encoder speed is a separate effort tradeoff
and can change both coding error and file size. The default speed remains 6;
faster settings are not presented as quality-neutral. These semantics follow
[rav1e's encoder configuration](https://docs.rs/rav1e/0.8.1/rav1e/struct.EncoderConfig.html).
The color signaling follows the
[AV1 specification](https://aomediacodec.github.io/av1-spec/#color-config-semantics)
and [AVIF specification](https://aomediacodec.github.io/av1-avif/latest-approved.html).

Exports publish a complete, synced file under a new name. They never overwrite
an existing destination, including one created by another process during
encoding. Cancellation is checked during pixel preparation and before
publication; a running codec call finishes before its cancelled result is
discarded. PNG/JPEG/AVIF encoding runs in the export worker, not the UI thread.

CLI examples:

```text
strehl develop master.tiff --out photograph.avif --hdr --color-space rec2020 --quality 100
strehl develop master.tiff --out photograph-p3.avif --hdr --color-space display-p3
strehl develop result.tiff --out photograph.png --color-space srgb
strehl develop result.tiff --out photograph-p3.jpg --color-space display-p3 --quality 100
```

## Verification and limits

**VERIFIED, October 21, 2026:** the editing crate's 52 tests cover format
validation, color conversion, profile round trips, cancellation and atomic
publication alongside development controls. An independent review decoded the
exports using FFmpeg and tifffile, with target matrices derived independently
from primary chromaticities. It re-chose the input patches and reference
luminance (110-nit white, 600-nit peak), including negative, colored and
above-white samples. Incorrect reference white and omitted wide-gamut
conversion were explicit failing alternatives. AV1 elementary-stream color
signaling was inspected separately from the AVIF container: both describe the
same primaries, PQ transfer, matrix, full range and 10-bit 4:4:4 samples.

The independent flat-patch check passed its three-code bound with less than
0.5 code of native YUV error. This establishes color/encoding behavior on that
fixture, not photographic losslessness or a universal error bound. An earlier
author check on a different, textured fixture **failed** its proposed 15-nit
maximum RGB-error bound (21.9 nits observed). Its subsequent inspection reported
up to two native YUV codes of error; inverse PQ and YUV mixing amplify bright
RGB errors. The failed bound was not reclassified as passed. Speed 6, 8 and 10
also changed decoded error and file size, supporting the exposed effort
tradeoff rather than a claim of quality-neutral maximum speed.
LittleCMS was also used for an author inspection of the SDR ICC outputs; that
inspection is separate from the independent color gate above.

Commands run for the local review:

```powershell
cargo test --locked -p strehl-edit
$env:CARGO_BUILD_JOBS = '4'
$env:CARGO_TARGET_DIR = 'target/progressive-photo'
cargo build --release -p strehl-edit --example export-review --example adaptive-review --offline
& 'target/progressive-photo/release/examples/export-review.exe' 'outputs/export-review/fixture-v1'
python outputs/export-review/check-decodes.py outputs/export-review/fixture-v1
python outputs/export-review/check-decodes.py outputs/export-review/fixture-v1 --inspect
python outputs/export-review/independent-color-review.py
```

The Python review tools and generated images/receipts are local investigation
artifacts under ignored `outputs/`; the Rust fixture generator and regression
tests are included in the repository. These checks do not calibrate a physical
HDR display or establish a subjective image-quality advantage.
