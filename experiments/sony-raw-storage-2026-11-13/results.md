# A7CR transfer headroom and compressed destination storage

2026-11-13. **VERIFIED / DEPLOYED:** the Windows receiver saves lossless
`.ARW.straw` archives by default. The installed setting is enabled. The actual
receiver UI saved both values and persisted On across a page reload. Existing
registered stacks retain their prior storage format. No old capture was converted
or deleted. The Pi service, camera settings, LAN authentication, receiver
destination and approved sign-in startup are unchanged.

## Measured transfer rate

**MEASURED:** one new A7CR four-shot group, 0.6 s, ISO 100, f/5.6, focus 37180,
EDUP 5 GHz to wired PC, existing four-worker CFA/Zstd sender. The camera and EDUP
enumerated on separate 5 Gbit/s USB roots. Pi pre-run load was 0.248/0.211/0.184,
available memory 3,867,072 KiB, swap zero, temperature 49.9 C, throttled 0x0.
No simultaneous build or benchmark was running during this group. This is an
author qualification of the present scene, not a controlled throughput campaign.

| Quantity | Observed |
| --- | ---: |
| Complete original group | 497,643,520 bytes |
| Stored compressed group | 149,896,988 bytes |
| Disk reduction | 69.879% |
| Original per RAW | approximately 124.4 MB |
| Stored per RAW | 37.46-37.49 MB |
| Per-file encode/upload/receiver acknowledgement | 0.597-0.777 s |
| Wire payload / that same interval | 48.2-62.8 MB/s |
| Original RAW bytes / that same interval | 160.1-208.4 MB/s |
| Camera/group call | 5.884 s |
| RAW-ready callbacks from that call's start | 2.111, 3.330, 4.424, 5.516 s |
| Subsequent RAW-ready spacing | 1.092-1.219 s |
| Upload queue peak / capacity | 1 / 4 |
| Buffer-full samples / pending at completion | 0 / 0 |
| Complete one-plane active run, including initial focus approach/setup and drain | 9.437 s |

MB means decimal million bytes. The effective RAW number is **not** radio speed.
The upload interval overlaps the camera's work; do not sum the four uploads onto
the group time. Likewise 5.884 s is not the whole one-plane run or the steady
multi-plane cadence. The earlier three-plane qualification had the same queue
peak of one and no buffer-full state; its camera calls were about 5.87-5.93 s.

**DERIVED / ARGUED:** delivery was faster than incoming RAW cadence, so there was
no observed network, codec or PC-write backpressure on this scene. The limiting
stage is upstream capture/readout/pixel shifting plus USB and controller protocol
work. That combined stage is measured; exposure, sensor readout, USB download and
polling are not individually instrumented. Four exposures total 2.4 s, but the
remaining 3.48 s must not all be attributed to either Sony or software. A better
radio alone would not remove all of that time. Less-compressible or noisier RAWs
can change the balance; the bounded queue then holds capture until space returns.

**DERIVED:** at this measured scene ratio, 900 four-shot planes would occupy
134.9 GB instead of 447.9 GB, excluding small journals. This is a size projection,
not a completed 900-plane test or a universal compression ratio.

## Implementation and compatibility

- `strehl-raw-codec` contains the existing byte-exact transport codec, moved
  without changing `STRHRAW1`. `strehl-capture::transport` reexports it. The
  `.straw` wrapper has a fixed 48-byte header with original length and SHA-256;
  full format/bounds are in the crate README. The receiver tees compressed
  input to its partial while decoding/hash-checking into a sink. No redundant
  compression pass or expanded destination ARW is needed.
- Original `bytes` and `sha256` acknowledgements retain their meaning. Receipts
  additionally report `logical_name`, `storage_encoding`, `storage_bytes` and
  the actual saved path. File flush, commit and durable receipt precede success.
  Retries validate both the stored archive and the full incoming stream. A bad
  existing archive cannot acknowledge and discard the Pi's last good original.
- Older configurations default **new** runs to compression. Legacy run-index
  paths migrate as plain ARW. A run pins folder and format across settings
  changes/restarts. JSON remains plain; identity-only clients are compressed
  on the PC using bounded memory. Off produces byte-identical plain ARWs.
- Updated `strehl-raw` and CLI/session discovery read archives directly, restoring
  one file in RAM before decoding/metadata reads. They refuse an ARW beside its
  matching archive to avoid counting an exposure twice. Plain files retain their
  normal mapped/seekable reads. Archive metadata reads currently expand and verify
  the whole file, which adds transient memory/CPU on import; no import-speed claim
  is made. No pixel-shift fusion or optical/noise calibration was changed.
- Installed `%LOCALAPPDATA%\StrehlCaptureReceiver\Restore RAWs.cmd` opens source
  and destination folder pickers and invokes `strehl-raw-archive.exe`. Its CLI was
  tested for exact restoration and overwrite refusal. The interactive picker
  itself was not exercised. Sources are retained. Other photo apps and existing
  older Strehl executables need these restored ARWs; the stacking desktop was not
  replaced in this task. Direct import was exercised through the updated CLI.
- Capture-only packaging now copies/resolves the shared codec without adopting
  `rawler` or the stacking engine. The generated package dependency manifest was
  checked; no new complete Windows desktop distribution was produced.

## Verification and commands

**VERIFIED:** complete real A7CR reference ARW -> archive -> byte-identical ARW;
the actual receiver retained exactly the supplied compressed stream, plus 48
header bytes. Full Strehl decode compared all 61,209,600 stored CFA samples,
geometry, levels, white balance, colour matrix and identity with the original.
The specialized hidden focus/optical readers still refuse unsupported A7CR
layouts exactly as for the original file; their A7C II assumptions were not
extended. The linked decoder's 9600-wide declared active area differs from
RawPy's 9564-wide visible crop, also unchanged by archival storage.

**VERIFIED:** all four newly captured files matched original SHA-256/length in
both PC receipts and Pi per-member journals. Python framing plus the earlier
research predictor and imagecodecs decoded the retained archive, cross-checked
against an original reference before use. RawPy fully decoded each live image
as 6376 x 9564 u16, copying inside its context. ExifTool confirmed one Sony group
and members 1/4 through 4/4, ISO/shutter/aperture and model. This is author
cross-implementation checking, not independent research review.

Commands executed from the repository root (logs under
`outputs/sony-raw-storage-2026-11-13`):

```powershell
cargo test --locked -p strehl-raw-codec -p strehl-capture --no-default-features
cargo test --locked -p strehl-capture
cargo test --locked -p strehl-raw --lib --test archive
$env:STREHL_ARCHIVE_RAW = 'D:\StrehlCaptures\stack-1794612335049-9932\frame-000001.ARW'
$env:STREHL_ARCHIVE_PACKED = Join-Path (Get-Location) 'outputs/sony-raw-storage-2026-11-13/reference/frame-000001.ARW.straw'
cargo test --locked --release -p strehl-raw --test archive -- --ignored --nocapture
cargo test --locked -p strehl-cli --lib session_discover::tests
cargo test --locked -p strehl-cli --lib session_input::tests
cargo run --locked -p strehl-cli --bin strehl -- probe 'D:\StrehlCaptures\stack-1794614074886-9932' --limit 1
cargo clippy --locked -p strehl-raw-codec -p strehl-raw -p strehl-capture --all-targets --no-deps -- -D warnings
cargo clippy --locked -p strehl-raw-codec -p strehl-raw -p strehl-capture --no-default-features --all-targets --no-deps -- -D warnings
wsl.exe -u root -- bash /mnt/c/dev/blog/death-of-software/projects/strehl/experiments/sony-a7cr-2026-11-13/lint-arm.sh
cargo fmt -p strehl-capture -p strehl-raw-codec -p strehl-raw -- --check
rustfmt --edition 2024 --config skip_children=true,reorder_modules=false --check crates/strehl-cli/src/lib.rs crates/strehl-cli/src/align_cmd.rs crates/strehl-cli/src/session-discover.rs crates/strehl-cli/src/session-input.rs
cargo build --locked --release -p strehl-capture --no-default-features --bin strehl-capture-receiver -p strehl-raw-codec --bin strehl-raw-archive
python -X utf8 experiments/sony-raw-storage-2026-11-13/qualify-http.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/sony-raw-storage-2026-11-13/install-receiver.ps1
python -X utf8 -X faulthandler experiments/sony-raw-storage-2026-11-13/verify-live.py
python -X utf8 experiments/sony-raw-storage-2026-11-13/verify-ui.py
```

The physical group was invoked through an inline import of the existing
`qualify.py`, assigning the new OUT and `--planes 1 --label storage-group`, with
the preceding SSH health snapshot. `qualify-camera.py` preserves those exact
operations as a reusable entry point and refuses an existing evidence name;
it was not rerun to take another group. `verify-live.py` is read-only.

Results: 33 capture tests in each feature build; four codec tests; 53 RAW unit
tests plus the discovery test passed (two unrelated private RAW tests and the
separately invoked real-archive test are normally ignored). Four folder discovery
and seven session-input tests passed. Windows and ARM64 clippy passed. The final
scoped format checks passed. Broad CLI formatting remains nonclean in unrelated
existing files/module ordering; it was reported, not swept into this change.
CLI lib tests retain 13 unrelated unused/dead-code warnings; no blanket workspace
test or photographic-quality campaign is claimed.

Refusal controls ran before measurements: wrong checksum, truncated/trailing
payload, oversized header, unknown version, actual TCP interruption, corrupt
stored duplicate, truncated retry, cross-format conflict, restore overwrite.
Identity sender, Off/plain storage, migration and pinned policy were checked.
Early rejection of a large malformed body can reset TCP before an HTTP error is
read; the harness verifies that the receiver remains alive and writes nothing.
An initial harness expected an A7C II-only reader to accept A7CR; it was corrected
to compare the original/archive result including refusal, without relaxing that
reader. Sandbox loopback restrictions required running HTTP tests outside the
sandbox. Initial package-manifest checking omitted the lockfile; copying the
same lockfile used by the actual packaging workflow resolved its offline lookup.

The receiver UI was rendered/inspected at 1280 x 900 and 390 x 844; local settings
were exercised, LAN settings remained read-only, and no browser errors or mobile
horizontal overflow were found. Camera preview was 1024 x 680, both focus marks
enabled, Start disabled with bounds unset. These are browser viewport tests,
not an actual new Android-device test. Camera ended ready at focus 37180, no
pending transfer, with test marks cleared. Compression remains enabled.

## Build identity, preservation and limits

Base: `15ed6df237db7f8abaf3b817de597dfd59b5beb2`, plus the preserved uncommitted
A7CR implementation and this storage change. Installed receiver SHA-256:
`c5b073378e8e0881f82ca95fe4a19bd862c9bae35192e4ddb7a26d5d0cc949ab`.
Archive tool: `cf5639e358b096285a5ac388908f008f3ed488eff1886a93a3d72ee2b640d6a6`.
Pi binaries were not replaced. Source hashes, installed receipt, before snapshot,
full test logs and redacted compact evidence are retained. The unrelated dirty
`experiments/ca-before-mhc/gpu.rs` SHA remained unchanged.

Rollback binary is `outputs/sony-raw-storage-2026-11-13/receiver-before.exe`.
After new runs have been registered, old software cannot read the new run-index
objects: prefer turning compression Off, not downgrading. Never replace/delete
the run index or archives merely to make an old receiver start. Restore ARWs
using the independent archive utility if needed.

**UNVERIFIED:** multi-hour soak, power-loss durability under hardware failure,
compression ratios for every subject/ISO, steady A7CR 900-plane cadence, sixteen-
shot sequencing, and reconstructed pixel-shift image quality. Existing captures
remain original-size; only new stacks use the selected storage policy.
