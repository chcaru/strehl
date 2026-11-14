# A7CR four-shot capture on the Pi

Date: 2026-11-13. **VERIFIED:** the connected A7CR now captures real four-shot
pixel-shift groups at successively commanded focus positions through the Rust
PTP 3 backend. Each member is uploaded as soon as its USB download completes.
Six complete groups / 24 original ARWs decoded and matched durable PC receipts.
The three-plane run used normalized positions 37180, 37181 and 37182. This is
functional capture qualification, not an optical-resolution measurement.

The installation is ready at `http://10.0.0.178:8787/`, with the existing pairing
key and configurable receiver destination. Focus was returned to 37180, test
bounds cleared, preview verified fresh, and the RAW RAM mount checked empty.
The older onboard address did not answer during the final browser check; use the
EDUP address above. No cloud endpoint or receiver configuration was introduced.

## Implementation

- `crates/strehl-capture/src/ptp.rs` and the `strehl-sony-ptp` binary implement an
  original Linux USB client using Sony's supplied Camera Remote Command 2.02
  PTP 3 reference. The SDK is not used concurrently. Public libusb C ABI calls
  are loaded from the system library; no third-party camera implementation was
  consulted. The existing A7C II SDK backend remains available.
- The camera initially advertised pixel-shift count/interval as display-only
  while mode was Off. The owner enabled four shots on its menu. Subsequently,
  count 4, shortest interval and manual focus were writable and read back. Mode
  remained enabled over repeated session disconnect/reconnect. The controller
  gives explicit camera-menu instructions if it is Off; it does not force a
  disabled property or substitute four ordinary exposures.
- Capture checks MF, host-only destination, RAW, uncompressed format, count 4,
  shortest interval, single drive, fixed ISO and timed manual exposure. Focus is
  fixed throughout a group. Four complete objects plus camera and buffer idle
  are required before another focus move. Sony requires uncompressed RAW for
  pixel shift; the original files are preserved exactly by transport compression.
- The current focus comes from `0xE043`, not the target property `0xE042`. It
  must remain at the requested value for the selected settle duration, at least
  200 ms. Result event `0xC218` is checked when present. A successful command is
  not a claim that one normalized unit always moves the optics distinctly.
- `Native::capture_files` receives incremental `raw-ready` messages. `PcCamera`
  persists per-member bindings and queues each file immediately. Plane, group,
  member, focus and original filename accompany lengths and hashes. The final
  result validates a complete ordered four-member group. The journal and Sony
  PixelShiftInfo remain beside/in the original ARWs; no ARQ composite is made.
- The A7CR RAM mount is now 1 GiB, `tmpfs,noswap`, with swap disabled. Before a
  release the uploader requires four free slots, four 128 MiB member bounds and
  memory/headroom checks. Actual members were approximately 124.4 MB. One USB
  owner, one uploader and four compression workers are retained. A whole group
  fits even if Wi-Fi stalls; another release waits for queue capacity.
- Pause and stop finish the active group and pending deliveries. Browser counts
  distinguish planes from RAWs; estimated duration accounts for four exposures.
  Preview parses the documented offset and size, including valid JPEG padding.

Sources: owner's local PTP 3 reference pp. 43–49, 110–120, 460–463, 567–568,
645–646 and 691; [Sony A7CR pixel-shift guide](https://helpguide.sony.net/ilc/2370/v1/en/contents/0414M_pixel_shift_shooting.html);
[libusb synchronous transfer API](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html).
The [earlier feasibility analysis](../sony-capture-ui-2026-11-07/a7cr-sequencing.md)
was hardware-unverified at its publication date. This qualification establishes
the four-shot path for the owner's actual connected camera/lens combination.

## Physical evidence

Compact identities, group timings, checksums, dimensions, camera tags and build
hashes: [qualification.json](evidence/qualification.json). Installation-private
logs, complete state histories and screenshots are retained under ignored
`outputs/sony-a7cr-2026-11-13/`.

| Run | Completed planes | Verified RAWs | Control exercised |
| --- | ---: | ---: | --- |
| complete-group | 1 | 4 | One complete four-shot group |
| three-planes-pause | 3 | 12 | Step 1; pause during member delivery, complete group, resume |
| browser-stop | 1 of 3 planned | 4 | Phone-sized browser Start/Stop; no next group |
| final-build-group | 1 | 4 | Final installed build; fresh decode/hash verification |

**VERIFIED:** all 24 files are Sony `ILCE-7CR`, uncompressed, with consistent
Sony group IDs and member tags 1/4 through 4/4. LibRaw via RawPy decoded the full
visible 9564 × 6376 u16 CFA in every file; the EXIF width includes additional
sensor columns. Original bytes match the PC receiver's SHA-256 receipts and the
per-plane journal bindings. No capture-corpus file was modified.

**MEASURED, diagnostic:** with the existing 0.6 s, f/5.6, ISO 100 exposure,
the final group's USB member completions were 2.093, 3.327, 4.448 and 5.560 s
after starting its capture command; the group call finished at 5.905 s. This
excludes the preceding focus/approach operation and the final uploader drain.
The first member was saved while the group remained active, as recorded by
controller-state polling. Delivery is member-by-member, not deferred to the
end of the four-shot group. Camera operation still uses serialized USB commands.

**MEASURED:** final-group original bytes totaled 497,745,920; wire bytes totaled
151,350,071 (69.59% less). Approximately 124 MB per member became 38 MB in this
scene. Original-size ARWs are stored on PC. This scene is relatively dark and
compressible: the ratio is not a guarantee for other scenes or ISO settings.

Environment: Pi 5 4 GB, kernel `6.18.50+rpt-rpi-2712`, EDUP on `wlan1`, USB 3
A7CR and adapter, wired PC receiver, four encoder workers. The final run's
pre-load averages were 0.108/0.178/0.142, with 3,874,192 kB available and zero
swap. Post-load was 0.224/0.199/0.150; temperature 47.95 C and throttling flags
`0x0`. The initial unprivileged firmware-temperature query was denied; the
post-run root query succeeded. Earlier group timings had uncontrolled background
load and are retained as diagnostics, not a comparative throughput benchmark.

## Failures retained and corrected

The first group stopped after two members because the new event reader treated
a libusb timeout with arrived bytes as an empty/failed event. Both received RAWs
were saved. After releasing that session, the camera reported an empty buffer;
members 3/4 and 4/4 were not recovered. That run remains explicitly **incomplete**
in `stack-1794611465892-9543`, and was never counted as a completed plane. No
shutter was automatically retried. Later tests started distinct new groups.

The reader now retains transferred event bytes on timeout and parses complete
containers, including multiple events in one read. A regression test exercises
the timeout-with-focus-result case, genuinely truncated data and disconnect.
The initial live-view implementation also wrongly required JPEG EOI at the
last payload byte: the camera supplied 106 padding bytes after EOI. The native
JPEG decoder and the UI now accept the valid bounded image body.

The browser test successfully captured/stopped and reconnected before a final
string-based Playwright wait hit the page CSP. It was replaced with DOM-property
assertions, preserving the CSP. Only the remaining display checks were rerun.
The old onboard-IP timeout was handled by testing both layouts on the working
EDUP address. Phone-sized Edge and desktop Edge passed with no page errors;
this is not a claim of a new test on the owner's physical Android device.

## Commands and checks

Commands actually run from the repository root (WSL scripts use the existing
Debian cross-toolchain; Rust 1.98, two build workers):

```text
python scripts/research.py search "Sony A7CR pixel shift capture"
python experiments/ORCH-drift-check/prior_art.py "A7CR"
cargo test --locked -p strehl-capture
cargo test --locked -p strehl-capture --no-default-features
cargo clippy --locked -p strehl-capture --all-targets --no-deps -- -D warnings
cargo fmt -p strehl-capture -- --check
wsl -d Debian -u root -- bash /mnt/c/dev/blog/death-of-software/projects/strehl/experiments/sony-a7cr-2026-11-13/build-arm.sh
wsl -d Debian -u root -- bash /mnt/c/dev/blog/death-of-software/projects/strehl/experiments/sony-a7cr-2026-11-13/lint-arm.sh
python experiments/sony-a7cr-2026-11-13/deploy.py
python experiments/sony-a7cr-2026-11-13/qualify.py --planes 1 --label complete-group
python experiments/sony-a7cr-2026-11-13/qualify.py --planes 3 --label three-planes-pause --control pause
python experiments/sony-a7cr-2026-11-13/verify-ui.py
python experiments/sony-a7cr-2026-11-13/verify-ui.py --finish-only --stopped-run D:\StrehlCaptures\stack-1794611876360-9758
python experiments/sony-a7cr-2026-11-13/qualify.py --planes 1 --label final-build-group
python experiments/sony-a7cr-2026-11-13/verify-raws.py
```

Both feature builds passed **35 tests**; Windows and ARM64 Clippy and formatting
passed. New controls reject wrong transaction IDs, oversized/truncated datasets,
bad JPEG bounds, incomplete/mixed/duplicated group members, wrong format and
non-idle completion. Existing transfer corruption, lost acknowledgement, queue
backpressure and recovery tests still pass. Edits rebuilt the affected crate.
The unrelated `experiments/ca-before-mhc/gpu.rs` content matches its pre-edit
SHA-256 snapshot. Work was not committed or pushed as part of this request.

Final installed SHA-256:

- Headless: `6909e62edc8f4c0abc76000993c45b26f05f2dbe2bcacecc71ba083b9b4b3758`
- PTP backend: `26b2364596190e85d9846a5b61916888b7eafcb0740aed0cfcfce63c98b49105`

Original SDK bridge and receiver are unchanged. Before-install binary, private
configuration and RAM-mount rollback copies are in `/root/strehl-a7cr-20261113/`.
Never restore/restart during an active group or while unacknowledged RAWs remain.

**UNVERIFIED:** hours-long unattended capture, power-loss recovery, a new camera
power cycle, every lens setting, 16-shot automation, independent research review,
and group-aware Strehl reconstruction quality. This implementation delivers
original pixel-shift data and provenance; it does not establish optical gains
or change the stacking engine's merge defaults.
