# Production lossless RAW transport integration

2026-11-12. **VERIFIED / DEPLOYED:** the Pi sender and PC receiver now negotiate
exact RAW transport compression automatically. The PC reconstructs the complete
original ARW, including metadata, inactive pixels and original camera compression.
Normal capture uses the new path; source RAM is released only after the existing
durable, matching-length, original-SHA-256 acknowledgement. Camera acquisition,
focus settings, LAN authentication, destination selection and sign-in startup
remain in place.

This integrates the [compression experiment](../sony-raw-compression-2026-11-12/results.md)
after [EDUP qualification](../sony-edup-2026-11-12/results.md). This is author
engineering qualification, not an optical-quality claim or independent research
review. No A7CR camera or pixel-shift sequencing was tested.

## Implementation

- `transport.rs` implements a checked Rust codec, without the experimental C ABI
  or Python runtime. It recognizes bounded little-endian TIFF scalar layouts
  containing a single uncompressed 16-bit storage plane and applies the tested
  reversible CFA predictor. Unsupported layouts, including camera-compressed
  A7C II files, receive generic Zstd. Each chunk retains original bytes if coding
  would enlarge it. No frame depends on another frame.
- One immutable original byte body is shared with four encoder workers. At most
  four jobs plus the current packet are retained; each decoded chunk is at most
  4 MiB. Encoding overlaps HTTP transmission. Receiver decoding and file writes
  run on a blocking worker with a demand-driven HTTP reader, rather than buffering
  a full compressed body or blocking the async executor.
- Protocol 1 status advertises `raw_encodings`; new senders use `strehl-raw-v1`
  only when advertised. Original length and checksum are independent of wire
  size. The binary stream uses a separate `STRHRAW1` magic, not the experimental
  Python protocol. Bounds cover original size (256 MiB), wire size, chunk count
  (1024), payload sizes, dimensions and decompression output.
- Old clients can still send identity bodies; an old receiver without the new
  capability receives identity. Retries rebuild the stream, recheck capabilities
  after connection errors and handle an explicit encoding refusal. A truncated
  or corrupt duplicate must be fully rejected even when the correct final file
  already exists. Different RAWs cannot overwrite existing destinations.
- The Pi retains its four-frame queue limit and tmpfs capacity reservation. A
  new Linux memory gate additionally reserves two maximum-sized RAWs, 96 MiB for
  encoder workspace and 64 MiB headroom before another exposure. The measured
  replay process used substantially less than that conservative reservation.
- The browser reports restored **RAW MB/s**, and separately reports the transfer
  byte reduction. This speed includes encoding/upload/receiver processing for
  the successful attempt; it is not radio throughput or capture cadence. The
  configurable PC destination continues to hold original-size `.ARW` files.

## Production HTTP measurements

**MEASURED:** the actual Rust `Sink` and installed receiver were exercised over
EDUP 5 GHz, with the PC on wired Ethernet. Both file classes used identity,
compressed, compressed, identity order. All eight files were independently
re-read on the PC and matched the source SHA-256. Interface counters confirmed
EDUP carried these replay transfers. Pi load/temperature, Windows CPU load,
process peak RSS, expanded commands and input hashes are retained in the receipts.

| Input / mode | Original bytes | Wire bytes | Complete transfer call, seconds | Upload portion, seconds | Peak sender RSS, MiB |
| --- | ---: | ---: | --- | --- | --- |
| 61 MP reference, identity | 122,968,064 | 122,968,064 | 1.992 / 2.252 | 1.847 / 2.107 | 120.1 |
| 61 MP reference, CFA + Zstd | 122,968,064 | 54,525,034 | 1.181 / 1.512 | 1.025 / 1.368 | 146.1 / 146.8 |
| A7C II test RAW, identity | 33,169,408 | 33,169,408 | 0.986 / 0.646 | 0.942 / 0.598 | 34.6 |
| A7C II test RAW, generic Zstd | 33,169,408 | 18,482,450 | 0.644 / 0.429 | 0.586 / 0.383 | 54.9 / 52.8 |

Complete transfer calls include readiness/registration, input reading/hashing,
encoding, HTTP, PC decoding and durable acknowledgement. Upload portions begin
before constructing the encoder. Subsequent independent PC hash readbacks are
outside these timers. MB are decimal; RSS uses MiB. These short measurements
include Wi-Fi variability and do not establish sustained stack throughput.

The 61 MP input is the genuine A7R IV `DSC01472.ARW` used by the prior experiment,
SHA-256 `453154311a136a0bb08efc4e3f0124e6d7fdc0116a5c413893a5c6b101f25c72`.
It is not an A7CR capture. The A7C II input is today's retained **dark** transport
test frame, SHA-256
`c0cf81c32b519f400e38e46a959cb10e038f65e5fc0ab4889c052d0dc453d643`.
Its roughly 44% wire reduction must not be generalized to illuminated scenes or
different noise/exposure settings. The 61 MP file's reduction is about 56%.

Compression starts after the SDK finishes each RAW in RAM. It does not shorten
camera exposure, readout, USB transmission or focus settling, and does not alter
whether a future camera releases pixel-shift files individually or in a group.

## Real capture and browser qualification

**VERIFIED:** three new A7C II Lossless L RAWs completed through the deployed
compressed pipeline at step 1 and 500 ms settling. They are retained in
`D:\StrehlCaptures\stack-1794549760762-7547` with journals and receipts. Each
independently decoded to a 7028 x 4688 u16 visible CFA, matched its full-file
SHA-256 and durable receipt, and explicitly used `strehl-raw-v1`.

| Frame | Original bytes | Wire bytes |
| --- | ---: | ---: |
| 000001 | 33,177,600 | 18,552,726 |
| 000002 | 33,185,792 | 18,496,321 |
| 000003 | 33,173,504 | 18,518,847 |

Focus was returned to 36802, test marks cleared and plan settings preserved.
The final service state was ready, connected and free of pending transfers.
The scene remained dark; these are transport/function tests. The three files'
hashes and full receiver receipts are in [evidence/summary.json](evidence/summary.json).

Deployed Edge browser checks at phone and desktop viewport sizes verified live
1024 x 680 preview, enabled A/B controls, Start disabled without marks, visible
compression savings and the configurable receiver folder. No browser errors
occurred. Complete screenshots were inspected. This was not a new physical
Android-device test.

## Refusal controls and issues found

**VERIFIED:** all 31 Rust tests passed in both default/desktop and headless builds.
Codec controls cover generic/CFA reconstruction, all u16 values and wrapping
boundaries, a calculated predictor vector, invalid TIFF fallback, bad versions,
truncation, trailing data, oversized declarations and a decompression bomb.
Receiver tests exercise partial cleanup, bad checksums, duplicate validation and
overwrite refusal. Real HTTP queue tests cover blocked delivery, a lost response
after durable commit, full-stream retry, retained source until acknowledgement,
legacy negotiation and receiver rollback. LAN/authentication tests also passed.

The installed HTTP receiver additionally passed nine deliberately failing
controls before the successful real-file comparisons: truncation, trailing data,
wrong checksum, unsupported encoding, oversized original length, invalid CFA
dimensions, wrong version, expansion bomb and a TCP connection closed mid-body.
No failed control committed a final or retained partial file. A valid fixture
then passed exact comparison, duplicate acknowledgement, truncated-duplicate
refusal and different-content overwrite refusal. This fixture is not counted as
a photographic RAW.

Qualification exposed and resolved the following:

- Socket tests initially failed with sandbox error 10013; the same tests passed
  with loopback access. This was an environment restriction.
- A real rollback test found that an early HTTP refusal can close the request
  body before its response status is delivered. The sender now renegotiates on
  retry. This was a production fix, followed by passing tests and rebuilds.
- Windows briefly retained the stopped receiver executable. The installer
  restored the old binary, then a bounded file-release retry installed the new
  one. Credentials, destination and sign-in launcher were preserved.
- The first replay invocation completed all four 61 MP cases, then found that
  an older illuminated A7C II test file had been removed. Those successful
  receipts were retained; a separate labeled comparison used the existing dark
  frame. No missing input is counted as tested.
- The copied capture harness initially requested an unsupported two-unit jog;
  the API refused it before any exposure. Two supported one-unit jogs fixed the
  harness. After the three successful captures, its old interface-counter gate
  compared network bytes with **original** rather than **wire** bytes. That gate
  was invalid for compression and was corrected. Its unsaved counter snapshots
  are not reported as evidence: physical-capture `tx_deltas` is explicitly null.
  The already completed three RAWs were re-verified without additional exposure;
  replay interface-counter evidence is unaffected.
- One immediate post-reconnect preview fetch was not decodable. Subsequent
  fresh JPEG requests and actual browser checks passed. The harness now waits
  for a decodable preview; the native preview driver was not modified and no
  cause of that transient response is claimed.

## Deployment, reproduction and remaining limits

The camera was idle with an empty RAW queue before replacement. The receiver was
updated first, then the Pi headless executable; the existing Sony SDK bridge was
retained. Configuration hashes/values and binary installation checks are recorded.
Only two hash-verified experiment copies were removed from Pi tmpfs. All PC
originals and received evidence remain. Final Pi checks: service active,
`throttled=0x0`, no swap, no experiment or production RAW left pending, route to
PC through wlan1/EDUP.

| Installed binary | SHA-256 |
| --- | --- |
| Pi headless | 1fcbbf09fcb6cd7470c18553f5301168d4288087972a1b40bd77bb117ce550d9 |
| Windows receiver | 8acfeb7305332e7ca75a56f9a759913731406e970c547086991c6f5b3bcd92dc |

Rollback copies are `/root/strehl-transport-20261112/headless-before` on Pi and
`outputs/sony-transport-2026-11-12/receiver-before.exe` on PC. Restore executables
only while the camera is idle with no pending RAW. An advanced diagnostic setting
`"transport_compression": false` in the Pi transfer configuration disables the
optimization; absent settings default to automatic negotiated compression. Do
not restart an active stack just to change this setting.

Commands actually exercised, from the repository root:

```powershell
cargo test --locked -p strehl-capture
cargo test --locked -p strehl-capture --no-default-features
cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-capture -- --check
cargo build --locked -p strehl-capture --no-default-features --release --bins --example transfer-probe -j 2
wsl -d Debian -u root -- bash /mnt/c/dev/blog/death-of-software/projects/strehl/experiments/sony-transport-2026-11-12/build-arm.sh
python -X faulthandler experiments/sony-transport-2026-11-12/qualify-http.py
python -X faulthandler experiments/sony-transport-2026-11-12/replay-pi.py
python -X faulthandler experiments/sony-transport-2026-11-12/replay-pi.py --case a7c2 --label production-a7c2
python -X faulthandler experiments/sony-transport-2026-11-12/qualify-camera.py
python -X faulthandler experiments/sony-transport-2026-11-12/qualify-camera.py --finish-existing
python -X faulthandler experiments/sony-transport-2026-11-12/qualify-camera.py --verify-restored
python -X faulthandler experiments/sony-transport-2026-11-12/verify-ui.py
python -X faulthandler experiments/sony-transport-2026-11-12/cleanup.py
```

The unsuccessful harness stages are described above; only final verified
artifacts support the claims. Replays now require fresh output labels. Helpers
are installation-specific; they use existing private configuration rather than
command-line credentials. Do not package or commit those private files. Build
workers were limited to two per platform; the codec uses four. Runtime source
and log hashes, input identities and compact receipts accompany this report.
Clippy exited zero; the compiler emitted incremental-cache hard-link fallback
warnings, not a failing lint. No engine/optical campaign was run.

**UNVERIFIED:** hours-long soak, power-loss recovery of unacknowledged RAM-only
images, a new Windows sign-in/reboot, A7CR camera/USB/pixel-shift sequencing and
compression ratios beyond the tested input classes. The original storage tradeoff
remains: Pi power loss before durable PC acknowledgement can lose that exposure.
