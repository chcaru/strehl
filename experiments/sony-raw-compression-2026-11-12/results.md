# Exact RAW transport compression on Pi 5

2026-11-12. Author-run experiment; no independent research review or SYNTHESIS
fold. Source and compact receipts are in this directory. Original inputs and
larger artifacts remain under `outputs/sony-raw-compression-2026-11-12/`.

## Result and scope

**MEASURED:** a 122.97 MB uncompressed 61 MP Sony ARW became a 54.53 MB transport
stream. On the owner's existing Pi Wi-Fi, complete delivery through SSH, PC
decoding, file synchronization and rename took 2.38-2.65 seconds, versus
4.85-4.99 seconds for the original bytes. All resulting ARWs have the original
SHA-256. This is about 56% fewer transport bytes and twice the effective RAW
delivery rate. It does not change image quality, bit depth, metadata or noise.

**MEASURED:** the Rust predictor plus Zstd took 0.403-0.409 seconds on the Pi's
four cores in the separate encoding benchmark. The actual bounded streaming
sender peaked at 177.8 MiB process RSS, plus the separate input file in tmpfs.
The larger exploratory benchmark retained several whole arrays and peaked at
1,057.9 MiB; that is not the streaming implementation's memory requirement.

**MEASURED:** temporal prediction does exploit real pixel-shift redundancy, but
the best tested temporal payload saves only 0.27% in the four-shot group and
0.98% in the sixteen-shot group beyond an independent CFA-aware JPEG-LS baseline.
Against the faster independent Rust/Zstd predictor, it saves 3.22% and 3.98%.
Those small gains do not establish a worthwhile Pi implementation once reference
generation, dependencies and recovery are included. These are not universal
limits or a proof of optimal compression.

**VERIFIED:** three existing camera-compressed A7C II ARWs also support a generic
byte-stream fallback: approximately 35.68 MB becomes 29.27 MB, an additional 18%
reduction without changing the camera's compression. One was transmitted through
the Pi and restored exactly. No camera settings were changed and no new
photographs were taken in this experiment.

**UNVERIFIED:** A7CR capture/USB timing, availability of each pixel-shift member
during its group, A7CR recognition by this TIFF fast path, the EDUP adapter's
throughput, and compressed transfer through the production HTTP receiver.
The running capture application has not been modified or redeployed.

## Inputs and independent decode

The source is Mathieu Gasquet's [Sony A7R IV sample gallery](https://mirrorlesscomparison.com/galleries/sony-a7r-iv-sample-photos/),
which offers genuine four-shot and sixteen-shot pixel-shift RAW groups for
download. All twenty originals were used: DSC01472-DSC01475 and
DSC01476-DSC01491. Their exact names, lengths, public download IDs and hashes are
in [the input manifest](evidence/input-manifest.json). Originals are not included
in the experiment package or redistributed in the repository.

Both groups show the same indoor scene at ISO 100, 1/5 second, f/5.6 and 55 mm.
They are two acquisition modes, not twenty independent scenes or noise regimes.
The complete embedded previews were inspected to establish that these are
normally exposed photographs with detail, bright areas and shadows, rather than
black frames. No photographic sharpness or reconstruction-quality claim is made.

Each file contains a 9600 by 6376 uncompressed, little-endian u16 sensor array
with 14-bit values: 122,419,200 sensor bytes. Metadata, embedded previews, inactive
borders and trailing bytes are retained. File sizes are about 122.97 MB. The
sensor strip begins at different offsets in different files; it is parsed, not
assumed. Every PC load compares this entire sensor array against an independent
RawPy/LibRaw decode copied inside the RawPy context. All comparisons passed.

These are A7R IV files, not A7CR captures. They provide real 61 MP Bayer samples,
real shifted exposure groups and independent exposure noise. They establish
compression feasibility, not support for the future camera's SDK operations.
Sony documents the A7CR's uncompressed RAW pixel-shift format in its
[pixel-shift guide](https://helpguide.sony.net/ilc/2370/v1/en/contents/0414M_pixel_shift_shooting.html).

## Methods and exactness

`predict.rs` implements reversible same-CFA-phase spatial predictors, temporal
predictors and blends. The selected fast predictor averages four previously
decoded same-phase neighbors (left, above, upper-left and upper-right), with
causal boundary handling. Prediction errors use an exact wrapping u16 signed
mapping, zigzag and byte-plane separation, followed by Zstd level 1. It handles
the full 0-65535 range; it does not discard low bits or assume clean borders.

The transport's integer arithmetic is separate from Strehl's f32 image pipeline.
It never demosaics, registers or denoises the captured signal. Filtered/aligned
temporal references affect only prediction: the complete error, including all
photon/read noise, is encoded and restored. Existing compressed or unsupported
ARWs fall back to generic Zstd; an incompressible chunk is sent literally.

Comparisons included plain Zstd, byte and bit shuffle, median and average spatial
predictors, low-bit splitting, lossless JPEG, JPEG-LS, lossless JPEG XL, FFV1,
CCSDS adaptive entropy coding, previous-frame residuals, CFA-aware reference
alignment, filtered references and running averages. Published baselines:
[Zstd](https://meta.github.io/zstd/), [JPEG XL](https://jpeg.org/jpegxl/),
[FFV1 RFC 9043](https://www.rfc-editor.org/rfc/rfc9043.html) and
[libaec](https://gitlab.dkrz.de/dkrz-sw/libaec).
FFV1 is an intra-frame codec; testing it is not a claim to have tested a temporal
video codec. The custom temporal arms provide the inter-frame comparison.

The entropy experiment uses libaec's adaptive coder on our predictor residuals;
it is not an implementation of the CCSDS-123 predictive image standard. Its
required block padding is explicitly zeroed, counted and checked on decode.

Forty native predictor cases cover zero, maximum, ramp and arbitrary full-width
u16 data. Forty low-bit packing cases cover odd lengths and all split widths.
Wrong references, corruption and truncation fail the exactness checks. The wire
protocol has three generic and eight CFA full-file roundtrips, plus 68 malformed
payload refusals. CFA controls include final two-row stripes and random full
16-bit data that forces literal fallback. Full-bit-depth FFV1 and six AEC
boundary controls also passed. See [control receipts](evidence/extra-controls.jsonl).

The real network path reconstructs and hashes the whole original ARW before
finalizing it; each saved file was also re-read and hashed. Exploratory temporal,
AEC and FFV1 arms verify the entire sensor and every side byte separately, with
the original strip layout retained. Their descriptor allowance is a budget,
not a serialized production group protocol. Cross-platform reconstruction of
the floating-point reference filters has not been implemented or verified.

## Compression comparisons

All MB below are decimal. Group totals include the first independent keyframe;
no free reference frame is assumed. JPEG-LS figures include a 256-byte descriptor
budget per file; custom temporal/AEC figures use 512 bytes. This discrepancy is
less than 0.005 MB for a sixteen-shot group. Prefix/suffix compression is counted.

| Method | Four-shot group MB | Sixteen-shot group MB |
| --- | ---: | ---: |
| Original ARWs | 491.87 | 1,967.53 |
| Fast independent CFA predictor + Zstd | 218.02 | 877.50 |
| Previous frame + Zstd | 221.28 | 890.33 |
| Aligned previous frame + Zstd | 214.48 | 857.51 |
| Filtered aligned previous frame + Zstd | 213.38 | 852.26 |
| Running previous-frame average + Zstd | 218.61 | 858.75 |
| Independent CFA predictor + AEC | 213.49 | 858.98 |
| Independent CFA-plane JPEG-LS | 211.56 | 850.88 |
| Filtered previous frame + AEC | 210.99 | 842.56 |

Temporal alignment searches +/-2 sensor pixels on a fixed central 1024-square
ROI; interpolation is within each color phase. AEC's filtered temporal arm uses
the previous frame with a 3-by-3 same-phase mean and no alignment search.
Search/filtering time is not hidden in a Pi throughput claim: these advanced
arms ran on the PC, and their Pi preparation cost remains unmeasured.

For the first four-shot file, ordinary Zstd gives 97.40 MB. Byte shuffling gives
68.64 MB; CFA prediction gives 54.48 MB; independent JPEG-LS gives 52.87 MB.
JPEG XL with the four phases as four channels gives 53.79 MB at effort 3,
but takes 2.26 seconds on one PC worker. Effort 7 was both slower (about 29
seconds) and slightly larger; there is no presumed monotonic quality/effort win.
Low-bit splitting worsened the Zstd result. Four-worker FFV1 produced 53.10 MB,
taking 0.92 seconds to encode and 2.82 seconds to decode on the PC, including
process startup and phase rearrangement. It was not benchmarked on the Pi.

### Why temporal redundancy is limited here

**ARGUED:** modern video's familiar extreme compression ratios usually include
quantization and discarding information. Exact RAW delivery must retain the
independent shot/read noise in every exposure. Subtracting two independently
noisy frames retains the noise from both, so identical subject content does not
imply a near-zero lossless residual. Good spatial prediction already removes
much of the predictable scene signal. Filtering the reference can improve
prediction without filtering the restored image, which explains the modest
measured temporal improvement.

**MEASURED control:** for a synthetic 524,288-byte CFA image, an exactly duplicated
reference gives a 34-byte temporal residual. With fresh Poisson/read noise the
temporal result grows to 282,570 bytes, versus 269,325 for spatial coding; a
filtered reference improves it to 257,719 bytes. A wrong Bayer phase and changed
exposure make prediction worse; unrelated random full-width noise is not
compressible. These are causal controls, not camera compression estimates. They
were added as follow-up controls after the first real-data sweep; native
exactness/refusal controls preceded that sweep.

More elaborate tile selection, trained entropy models or reversible temporal
transforms remain possible. The tested results do not justify promising a
dramatic extra group-level saving or a general information-theoretic limit.

## Pi and complete network measurements

Pi 5, 4 GB, ARM64 Linux 6.18.50+rpt-rpi-2712, Zstd 1.5.7. Four-worker encoding
uses independent 256-row strips in `pi-bench.py`; the actual wire uses 128-row
strips to overlap production with transmission. No entire pixel-shift group is
buffered. Three repeats per worker-count/predictor setting; all 42 roundtrips
passed. Representative four-worker encoding ranges:

| Method | Encoded MB | Encode seconds |
| --- | ---: | ---: |
| Generic byte Zstd | 97.40 | 0.242-0.276 |
| Median CFA predictor | 56.05 | 0.374-0.396 |
| Two-neighbor average | 54.96 | 0.372-0.388 |
| Four-neighbor average, selected | 54.49 | 0.403-0.409 |
| Wider spatial average | 54.55 | 0.421-0.437 |

Temperature peaked at 57.85 C. Load, temperature, build hash, input hash and
per-repeat process RSS are in [the Pi receipts](evidence/pi-bench-v3.jsonl).
PC: Windows 11 build 26200, 32 logical CPUs, AMD64 Family 26 Model 68, Python
3.12.10; native predictor Rust 1.98.0. Dependency versions and executable hashes
are frozen in [the build receipt](evidence/measured-build.json).
PC codec timings are exploratory shared-host measurements, not isolated CPU
comparisons. Historical PC load was not sampled for every codec run.

The LAN replay order was identity, Zstd, CFA, CFA, Zstd, identity. This is SSH
over the existing Pi Wi-Fi to the wired PC, not a camera exposure or HTTP upload.
Each measurement includes SSH/Python startup, encoding, transfer, PC decoding,
file flush/fsync and rename. Files were re-read and SHA-256 checked afterward.

| Transport | Actual wire MB | Seconds to finalized file | Mean +/- SE, two repeats |
| --- | ---: | ---: | ---: |
| Original bytes | 122.969 | 4.85-4.99 | 4.919 +/- 0.066 |
| Generic Zstd | 97.401 | 4.00-4.03 | 4.015 +/- 0.019 |
| Chunked CFA + Zstd | 54.525 | 2.38-2.65 | 2.516 +/- 0.133 |

The two-repeat SE is descriptive and not a reliable population confidence
interval. A third, instrumented CFA replay took 2.634 seconds with 177.8 MiB
sender RSS and identical bytes. No headline depends on excluding it. The
instrumented A7C II fallback replay took 1.427 seconds for 35.68 MB restored
from 29.27 MB on the wire; no paired A7C II network-speed claim is made.

One early Pi run used the first RAW's strip offset for its reference even though
the reference had a different offset. That owned process was stopped, all its
timings discarded, and the complete 42-case run repeated with correct offsets.
The aborted receipts remain explicitly named as invalid in ignored outputs.
The initial AEC odd-length control rejected inadequate padding; the corrected
block-padded roundtrip was commissioned before the full AEC sweep.

## Integration into Strehl

**ARGUED implementation choice:** use independent per-file compression first.
It offers almost all the tested saving, supports immediate processing of each
completed RAW, and makes retry/recovery independent of other frames. Keep
temporal compression experimental until it wins a full Pi-to-PC comparison.

The prototype `wire.py` uses the Rust predictor, four bounded worker jobs,
128-row stripes, a versioned header, original length/SHA-256 and bounded chunks.
It sends literal data if a compressed chunk expands. Unsupported TIFF layouts
and already-compressed ARWs use ordinary byte compression. It does not require
the whole pixel-shift group, write a compressed spool to SD, or create a new
camera RAW format. The PC restores the identical original ARW before saving it.

Production integration belongs at `Sink::put_bytes` in `transfer.rs` and
`receive_file` in `receiver.rs`, after checking `/api/status` capabilities.
The current protocol is version 1 and expects the original length and hash.
A new negotiated body encoding must distinguish wire length from decoded length,
bound both, and retain the original SHA and existing durable acknowledgement.
The receiver must decode to its partial file and only finalize/acknowledge after
validation and synchronization. Existing-file retries must still consume and
verify the complete incoming decoded body. Disconnects, corrupted chunks and
unsupported versions need end-to-end tests through the actual HTTP path.

The sender must retain the source RAM file until that acknowledgement, rebuild
a stream on retry, and account for worker buffers in the existing upload queue's
memory reservation. Keep the current LAN allowlist, authentication and
configurable destination. The prototype's C ABI and Python assertions are local
research interfaces, not a release-ready network decoder. Port them to checked
Rust slices/results before production. No new capture or UI behavior is needed
to establish this transport optimization.

This cannot shorten camera readout, exposure, lens settling, or transmission of
the original uncompressed bytes over USB. It starts after the SDK supplies a
complete RAW. If Sony releases the files only after completing a pixel-shift
group, compression does not change that. Combined A7CR sequencing remains a
separate hardware/protocol question.

**DERIVED adapter model:** at a genuinely sustained 75 MB/s application link,
123 MB takes 1.64 seconds of network time and 54.5 MB takes 0.73 seconds.
Encoding can overlap transmission by stripe, but startup, PC decoding, USB and
capture remain. These are network-only calculations, not a measured EDUP or
whole-stack forecast. Re-run the identical replay after the adapter arrives.

For scale, the tested fast payloads total about 218 MB per four-shot group and
878 MB per sixteen-shot group. Across 900 planes those are about 196 GB and
790 GB of transport payload, versus 443 GB and 1.77 TB of original ARWs for
this scene. **Destination disk usage remains the original size** because this
design restores ARWs on the PC. Compressed archival storage would be a separate
format/reader feature. A 16-shot capture remains roughly four times the payload
of a four-shot capture; lossless coding does not erase that cost.

## Reproduction and status

See [README](README.md) for commands, fresh output labels, and source-inclusive
packaging. [summary.json](evidence/summary.json) is recomputed from the receipts
by `summarize.py`, which re-hashes all twenty input files. Code, source snapshots,
builds and receipts are retained. No production source was changed; no running
capture service was replaced. Research controls and full-file equality establish
transport exactness, not an independently reviewed optimum or A7CR compatibility.

Final scoped checks passed: Python compilation, native/transport controls, new
Markdown links, final newlines, and preservation of all 317 previous ledger
table rows. The five preserved production source/configuration build inputs
remain byte-identical. The complete `python scripts/corpus_lint.py` check exits
1 with 17 findings in eight untouched documents (seven table-width, seven
unescaped-bar and three missing-newline findings); it reports none on the new
ledger row. Those unrelated files were not edited to make this experiment green.

The camera service remained active, connected and ready. The deployed headless
and current native helper hashes match the recorded production builds. Final
Pi throttling status was `0x0`, swap was disabled, and the three hash-verified
temporary experiment RAW copies were removed from Pi RAM. PC originals and all
measurement evidence remain intact. See [environment](evidence/final-environment.json),
[scoped validation](evidence/final-validation.json) and
[temporary-copy cleanup](evidence/ram-cleanup.json).
