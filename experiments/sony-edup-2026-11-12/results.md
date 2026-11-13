# EDUP qualification on the studio Pi

2026-11-12, author verification. **VERIFIED:** the EDUP is working with the
existing headless capture app. Its 5 GHz connection is preferred for PC delivery;
the onboard interface remains connected as a fallback. No production camera,
receiver or codec binary was changed for this qualification.

## Measured throughput

All MB are decimal. These are short Pi-to-wired-PC TCP tests at the existing
studio placement, not advertised link rates or a long-duration guarantee.

| Interface / band | TCP streams | Received Mbit/s | Received MB/s | Retransmits |
| --- | ---: | ---: | ---: | ---: |
| Onboard, before | 1 | 187.26 | 23.41 | 78 |
| EDUP, 5 GHz | 1 | 460.58 | 57.57 | 163 |
| EDUP, 6 GHz | 1 | 368.75 | 46.09 | 94 |
| EDUP, 6 GHz | 4 | 392.17 | 49.02 | 81 |
| EDUP, 5 GHz | 4 | 568.24 | 71.03 | 0 |
| EDUP, 5 GHz, repeat | 1 | 572.44 | 71.55 | 0 |
| Onboard, after | 1 | 204.39 | 25.55 | 64 |

**MEASURED:** 5 GHz delivered 58-72 MB/s, versus 23-26 MB/s onboard, roughly
2-3 times faster. At this placement, 6 GHz was slower at 46-49 MB/s. Its signal
was approximately -76 dBm, compared with -56 to -57 dBm on 5 GHz. Both bands
associated successfully; the final choice follows the measured results.

Each iperf3 run measured 12 seconds after a two-second omission. The Pi server
was bound to the selected address **and interface**; reverse-mode WSL Debian
clients received on the Windows PC's wired connection. Interface byte counters
confirmed the intended adapter carried each test, with the other below 10% of
test bytes. All actual deltas are retained. Pi load, temperature and station
information were sampled before/after each run. Concurrent Windows CPU load was
not logged, so these results do not isolate radio capacity from every host effect.

## Actual camera delivery

**VERIFIED:** two real A7C II Lossless L RAW exposures completed through the
unchanged production camera service and authenticated HTTP receiver. Both files
were saved in `D:\StrehlCaptures\stack-1794546666339-2273`, matched durable
receiver SHA-256 receipts on re-read, and decoded independently to 7028 x 4688
u16 CFA. The test used focus step 1 and the existing 500 ms settling interval.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| frame-000001.ARW | 33,169,408 | c0cf81c32b519f400e38e46a959cb10e038f65e5fc0ab4889c052d0dc453d643 |
| frame-000002.ARW | 33,165,312 | 062b634fd919315bc6b4b7b85d60f4ac7782a397feff6a4edfbb2c1ae861f9b2 |

**MEASURED:** the final file's app-reported upload took **0.517 seconds at
64.14 MB/s**. EDUP transmitted 69,521,479 interface bytes across the test;
onboard transmitted zero. The production queue peaked at one frame and finished
empty. Existing capture/upload overlap remained enabled.

This is transfer timing, not exposure cadence. Camera acquisition took 2.753
and 2.703 seconds, with the existing two-second exposure; consecutive
`capture_buffered` events were 3.576 seconds apart. Focus movement, settling,
readout and camera USB service still contribute. The scene was dark, so this is
a transport/functionality test and makes no optical-quality claim.

Focus returned to its initial position, 36802. Initial absent A/B marks and plan
settings were restored. The service finished ready with a fresh 1024 x 680 JPEG,
no failure and no pending RAWs. RAW staging was RAM-backed, with swap disabled;
the production staging directory was empty at final inspection.

## 61 MP RAW replay and compression

**MEASURED, prototype only:** the prior exact-byte transport codec was replayed
over EDUP with a genuine 122,968,064-byte A7R IV pixel-shift source ARW. This is
not an A7CR capture, pixel-shift camera sequencing test, or production HTTP codec
integration. Input provenance and codec design are in the
[prior report](../sony-raw-compression-2026-11-12/results.md).

Input: `DSC01472.ARW`, SHA-256
`453154311a136a0bb08efc4e3f0124e6d7fdc0116a5c413893a5c6b101f25c72`.

| Replay order | Encoding | Wire bytes | Seconds to durable PC file |
| ---: | --- | ---: | ---: |
| 1 | Identity | 122,968,587 | 2.388 |
| 2 | CFA prediction + Zstd | 54,525,214 | 1.836 |
| 3 | CFA prediction + Zstd | 54,525,214 | 1.612 |
| 4 | Identity | 122,968,587 | 3.022 |

Four encoder workers were configured. Timings include SSH process startup, Pi
encoding, transport, PC decoding, file flush/fsync and rename. A subsequent
complete file re-read independently verified the original SHA-256 in all four
cases; that verification re-read is outside the reported timer. The codec's
corruption/truncation controls ran before these replays. EDUP carried all replay
traffic. These figures demonstrate a useful path for larger RAWs, without
assuming that an A7CR stack will have the same compressibility or acquisition
rate. **This extra compression is not enabled in the production capture app.**

## Installed configuration and recovery

- Pi 5, kernel `6.18.50+rpt-rpi-2712`; EDUP USB `0e8d:7961`, native `mt7921u`
  driver. EDUP and Sony camera each negotiated USB 3 at 5000 Mbit/s, on separate
  root controllers. The wired PC link is 1 Gbit/s; access point is the owner's
  Comcast/Technicolor XB8.
- `Strehl EDUP 5 GHz`: wlan1, permanent hardware address, automatic connection
  priority 100, route metric 100, power saving disabled. Final association:
  channel 157, 5785 MHz, 80 MHz HE, two spatial streams.
- `Strehl home`: wlan0, automatic connection, route metric 600. The 6 GHz profile
  remains saved for manual testing with automatic connection disabled.
- Final PC route: `10.0.0.109 dev wlan1 src 10.0.0.178`. The existing camera
  address `http://10.0.0.187:8787/` still works; EDUP also serves
  `http://10.0.0.178:8787/`. Existing authenticated LAN-only configuration remains.
- Preferred routing was changed with a timed rollback armed, then verified from
  both camera addresses before cancelling rollback. An **idle-only** fallback
  test deactivated EDUP, observed the PC route switch to onboard, and restored
  EDUP while the camera remained connected. Active-stack failover and reboot
  behavior were not tested.
- The prior camera fault initially could not recover because the PC receiver
  was stopped. After restarting it, normal recovery exposed a missing registered
  folder for an older **zero-exposure** aborted test. Its retained journal was
  checked for no capture or exposure intent before recreating that exact empty
  folder and allowing metadata resynchronization. Normal recovery then worked;
  no prior RAW was changed or discarded.
- Following explicit owner approval, a per-user Startup shortcut now launches
  the existing RAW receiver hidden **at Windows sign-in**. Re-running the launcher
  while the receiver was active preserved one process. A new sign-in/reboot was
  not performed. The existing receiver settings retain the configurable PC
  destination, currently `D:\StrehlCaptures`.
- Browser checks exercised the deployed camera UI at phone and desktop viewport
  sizes and the receiver settings UI: preview decoded, A/B buttons enabled,
  Start correctly disabled without marks, no browser errors. These were Edge
  automation checks, not a new test on the owner's physical Android phone.

The original network profiles were backed up under root-only
`/root/strehl-edup-20261112/network-before/`. Wi-Fi credentials were entered in a
local form and sent directly to NetworkManager without printing or saving the
plaintext passphrase on the PC. A derived WPA2 key alone was insufficient for the
SAE profile; NetworkManager documents the distinct PSK/passphrase requirements
in its [wireless security settings](https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/nm-settings-nmcli.html).

Final inspection: service active, `throttled=0x0`, approximately 49 C, no swap,
no RAW pending, no test server listener and no active rollback timer. Only the
hash-verified temporary replay RAW on Pi RAM was removed; source and received
PC RAWs remain available.

## Commands, evidence and limits

Run from the repository root. Setup helpers are installation-specific and use
existing private credentials from ignored outputs; they must not be packaged
with those credentials. Network tests require an idle camera. The capture check
deliberately takes two pictures and expects no existing A/B marks.

```powershell
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label onboard-before --interface wlan0 --address 10.0.0.187
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label edup-5-single --interface wlan1 --address 10.0.0.178
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label edup-6-single --interface wlan1 --address 10.0.0.178
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label edup-6-four --interface wlan1 --address 10.0.0.178 --streams 4
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label edup-5-four --interface wlan1 --address 10.0.0.178 --streams 4
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label edup-5-repeat --interface wlan1 --address 10.0.0.178
python -X faulthandler experiments/sony-edup-2026-11-12/bench-network.py --label onboard-after --interface wlan0 --address 10.0.0.187
python -X faulthandler experiments/sony-edup-2026-11-12/replay-raw.py
python -X faulthandler experiments/sony-edup-2026-11-12/qualify-camera.py
python -X faulthandler experiments/sony-edup-2026-11-12/verify-ui.py
```

The adapter was connected to each named band before its test; the individual
receipts retain exact expanded iperf commands, station state and counter deltas.
Do not re-run labels over existing evidence. `replay-raw.py` refuses to overwrite
its existing output directory. Full machine-local evidence and screenshots are
under `outputs/sony-edup-2026-11-12/`; the compact, credential-free
[evidence summary](evidence/summary.json) records measurements and source hashes.

The checkout was already dirty at base commit
`122ed990e95e8d4a671ee68ce6bf45a7ac6bdd89`; a Git commit alone does not identify
the deployed build. Observed binary SHA-256 identities were:

| Binary | SHA-256 |
| --- | --- |
| Pi headless service | 219d707946c9e0a55db217d1f0e596e6a8a55ffa0300fed7fe1a5fb160d37076 |
| Pi Sony bridge | 73abfba37853ac0c0315e1ce21dac4300c3ab1db7a374fad45d93f31ad5b3551 |
| PC receiver | dbb449045a995f7246957008f64a07a84fb4c71b92270089534e174781305201 |

**UNVERIFIED:** hours-long throughput, actual reboot/startup recovery, active
capture during adapter loss, A7CR USB/pixel-shift behavior and production codec
integration. This is author operational qualification, not independently reviewed
research or a SYNTHESIS fold.
