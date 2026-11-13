# A7C II timing and A7CR throughput plan

Date: 2026-11-11. Author-run engineering qualification; no independent review,
optical-quality conclusion, A7CR hardware test or multi-hour guarantee. The
production driver and its 500 ms settling default were not changed.

## Adapter and network

**VERIFIED:** the matching Amazon product is
[ALFA AWUS036AXML, ASIN B0BY8GMW32](https://www.amazon.com/dp/B0BY8GMW32).
The fetched Amazon title matches the model. Price, delivery and seller were not
qualified. [ALFA's specification](https://www.alfa.com.tw/products/awus036axml)
lists MT7921AUN, USB 3, 2x2 operation, 80 MHz channel width and up to 1200 Mbit/s
on either 5 or 6 GHz. AXE3000 aggregates band rates; it is not one 3 Gbit/s link.

The owner identified the router as Technicolor XB8 2.0.
[Xfinity's specification](https://www.xfinity.com/support/articles/broadband-gateways-userguides)
lists XB8 as tri-band Wi-Fi 6E with 6 GHz support. This establishes compatibility
in principle, not that the current SSID/security configuration will connect on
6 GHz. Compare 5 and 6 GHz after the adapter arrives; do not assume the higher
band wins through walls. The preceding on-Pi check found `mt7921u` and its
firmware installed. The adapter itself has not been physically tested here.

The preceding network test measured 235.7 Mbit/s single stream and 238.5 Mbit/s
four streams. The PC has 1 Gbit/s Ethernet, which will eventually impose a
roughly 100-115 MB/s practical transfer ceiling even if the wireless link improves.
75 MB/s below is a planning scenario, not a measured adapter result or guarantee.

## Where 3.62 seconds goes

**MEASURED:** the six-frame overlap journal, followed by a fresh two-frame app
run, used 2-second exposures, ISO 100, f/5.6, Lossless Compressed RAW L, host-only
saving, focus step 1, approach 128 and 500 ms settling. The earlier five steady
intervals average 3.616 seconds; the new interval is 3.623 seconds.

| Component | Mean seconds per frame | Interpretation |
| --- | ---: | --- |
| Programmed exposure | 2.000 | Decoded SDK shutter value 20/10 seconds |
| Additional camera acquisition | 0.753 | Readout/processing/USB/SDK completion; not all USB |
| Deliberate focus settling | 0.500 | Existing configured wait after focus-completion notification |
| Remaining focus call | 0.271 | Command, result event, property operations and polling |
| Capture bookkeeping | 0.063 | Hash, pending intent, queue and journal work, plus boundary timing |
| Status checks before capture | 0.010 | Readback and exposure guard |
| Preview and loop boundary | 0.019 | Between completed acquisition and next focus intent |
| Total | 3.616 | Wi-Fi upload already overlaps this work |

The exposure is only one part of the capture cycle. Native in-camera bracketing
can schedule focus, exposure and buffering internally; our external path waits
for the whole RAW in Pi RAM before the next focus operation. A native bracket
was not timed with matching settings in this investigation, so no numerical
native-versus-external speed ratio is claimed. Native card recording and this
host-only delivery path are also different workloads.

## Camera USB and live-view controls

**MEASURED:** four refined direct SDK probes kept the same exposure/file settings
and used live view on/off/off/on. Capture-to-completed-RAM times were 2.703,
2.703, 2.703 and 2.753 seconds. This tiny sample does not establish a meaningful
benefit from disabling live view; 50 ms completion polling also limits resolution.

The trace retained only USB request metadata, never payload bytes. Matched
submissions/completions for the large RAW transfers covered approximately
35.67 MB in 0.171, 0.142, 0.157 and 0.157 seconds: about 208-251 MB/s across
those service windows. These are host-controller request times, including
inter-request gaps/waits, not a direct electrical-bus measurement. Small initial
chunks are excluded (about 3 KB per file); this is not a complete USB wire-byte
accounting. See the [kernel usbmon reference](https://docs.kernel.org/usb/usbmon.html).

**DERIVED:** roughly 0.55-0.60 seconds of the capture call beyond exposure is
outside that large-data window. Camera processing, command scheduling and SDK
notification/polling remain combined. No exposed callback here independently
timestamps the end of physical exposure, so it would be incorrect to assign the
whole remainder to sensor readout or to start moving focus on an ambiguous event.

The first four pilot captures recorded completions alone. Live-view traffic and
large 16 MiB requests made their reported whole-trace span unsuitable as a RAW
transfer duration. The refined trace fixes that measurement. Traced/untraced
pilot capture times overlap the refined range, but zero diagnostic overhead is
not proven. Pi load before the refined probe was 0.16/0.12/0.09; one SDK owner,
one lightweight trace reader, no competing camera app session.

## The shorter-settle result is a rejection

**MEASURED:** the app's 500 ms control run passed. Its following 100 ms run failed
the approach-focus readback before any exposure. The series stopped there; no
successful 100 ms stack cadence is claimed. Recovery restored 500 ms, released
the test marks and returned the camera to Ready with a fresh preview.

Two direct diagnostic probes also returned requested 36804/readback 36802 after
100 ms, despite a focus-success notification. Their next focus calls read the
previous target as 36804. This is consistent with delayed readback or incomplete
settling; it does not distinguish those causes. The native bridge returns the
readback separately, while the production Rust owner rejects a mismatch. The
initial diagnostic harness did not enforce that extra Rust guard. Those two
files remain valid transport samples but are not verified focus planes. The
retained harness now refuses an exposure on mismatch; its measured earlier
source snapshot is retained separately. Production guards were not weakened.

**ARGUED next change:** await both the focus-success event and the requested
readback, then apply a separately qualified optical settling floor. A fixed
100 ms wait is not a validated replacement. Benchmark this readiness scheme
before changing the default; readback correctness alone does not prove sharpness.

## Lossless transport compression

**MEASURED on the Pi:** two approximately 35.7 MB Lossless Compressed ARWs were
compressed with system `libzstd`. Level 1 produced approximately 29.3 MB, saving
18%, in 0.112-0.117 seconds (306-319 MB/s input). Level 3 saved about 18.2% but
took 0.134 seconds. Every decompression matched the original bytes exactly.
These are two nearby frames of the same illuminated, relatively dark subject;
other scenes/noise levels can compress differently. No A7CR compression ratio
is measured.

**DERIVED:** at 25 MB/s, level 1 changes a serialized compress-plus-send estimate
from 1.43 to 1.29 seconds. For this sample, sequential compression stops helping
above about 55 MB/s because CPU time exceeds network time saved. At 75 MB/s,
compression should be skipped for this ratio or overlapped with transmission of
another file. A future adaptive codec should use measured size/time benefit,
bounded memory and exact original-byte hash verification on the PC. It must
reconstruct the original ARW, not replace it with a different RAW format.

Compression is currently a measured prototype, not an installed transport feature.

## A7CR capacity model

**VERIFIED:** Sony lists 61 MP effective pixels and a 5 Gbit/s USB interface.
[A7CR specifications](https://www.sony.com/electronics/support/e-mount-body-ilce-7c-series/ilce-7cr/specifications).
Its [pixel-shift help guide](https://helpguide.sony.net/ilc/2370/v1/en/contents/0414M_pixel_shift_shooting.html)
locks pixel-shift recording to uncompressed RAW and disallows setting changes
inside a group. Ordinary Lossless Compressed L and pixel-shift therefore have
different transfer budgets.

**DERIVED planning examples:** use 75 MB for one ordinary 61 MP lossless file
(budget roughly 65-95 MB until actual samples exist) and 125 MB per uncompressed
member (approximately 61 million 16-bit storage values plus container overhead).
Actual ARW lengths depend on the camera format/metadata/scene. Group sizes below
are original ARWs before any optional transport compression, not combined ARQs.

| One focus plane | Assumed data | At measured-class 25 MB/s | At hypothetical 75 MB/s | 900 planes |
| --- | ---: | ---: | ---: | ---: |
| A7CR ordinary lossless example | 75 MB | 3.0 s | 1.0 s | 67.5 GB |
| A7CR four-shot group | 500 MB | 20.0 s | 6.7 s | 450 GB |
| A7CR sixteen-shot group | 2,000 MB | 80.0 s | 26.7 s | 1.8 TB |

At the end of this investigation, D: had approximately 283 GB free.
The four-shot 900-plane example would require a different destination or more
free space. The future group backend should preflight whole-stack PC capacity
as well as atomic-group RAM admission.

These are network-only service times. With a sufficiently buffered pipeline,
exposure and transfer overlap; do not add them as fully serial costs. Conversely,
a buffer cannot compensate indefinitely for a slower consumer. At 2 seconds per
exposure, 900 four-shot planes already require 2 hours of exposure alone; sixteen
shots require 8 hours, before motion, readout, gaps and final drain.

The current backend is A7C II/single-exposure/Lossless L only. Four/sixteen shots
cannot be enabled merely by raising a frame count. The existing SDK helper
rejects extra downloads and an uncompressed format. The separate public PTP 3
four-shot design is documented in the earlier A7CR sequencing report; its full
host-only alternating sequence remains unverified on that camera. Public
sixteen-shot mode selection remains unresolved.

For an atomic four-shot implementation, admit the complete group's worst-case
bytes before release. The current 512 MiB tmpfs is too tight as a robust group
budget even if four typical files approximately fit. A 1 GiB bounded spool is a
reasonable four-shot design target on the 4 GB Pi, subject to measured total
memory use and explicit per-member limits. Sixteen shots need a different memory
budget or verified camera-side backpressure; do not rely on Wi-Fi always draining
while an uninterruptible group is being generated. Retain per-file original-byte
receipts and group/member IDs, and commit focus advancement only at group end.

## Prioritized improvements

1. **External adapter:** test both 5 and 6 GHz with the XB8, place its antennas
   clear of the Pi's metal case, retain the PC's wired route. Target 60-90 MB/s
   for qualification; no promised throughput. More TCP streams did not help the
   present onboard radio. No second computer, cloud relay or faster USB cable is
   indicated by these measurements.
2. **Adaptive transport compression:** especially investigate uncompressed
   pixel-shift ARWs. Pipeline compression and upload where worthwhile; skip it
   when predicted CPU cost exceeds bytes saved. This preserves full RAW data.
3. **Focus readiness and exposure/download overlap:** separate completed exposure
   from completed file delivery only with authoritative supported camera status.
   Then move focus while the previous RAW downloads, retaining bounded queues
   and never retrying an uncertain shutter. The current conservative boundary
   is deliberate; this is a proposed backend redesign, not yet implemented.
4. **Camera-native bursts where applicable:** ordinary native brackets, or
   interleaved native brackets with calibrated starting offsets, might amortize
   remote focus commands. Exact fine-plane coverage and host-only support must
   be verified. Native focus bracketing is not a ready substitute for pixel-shift
   alternation, and three offset passes do not automatically prove 900 unique
   equally spaced optical planes.
5. **Alternative network path:** an Ethernet-to-Wi-Fi client bridge beside the
   Pi can use its Ethernet port and a separate stronger radio; GL.iNet documents
   this [connection pattern](https://docs.gl-inet.com/router/en/4/faq/produce_a_wired_connection/).
   If studio coax is available, [MoCA](https://www.trendnet.com/store/products/coax-to-ethernet-adapter/2.5gbps-ethernet-over-coax-adapters-2-pack-TMO-313C2K-v1)
   is another way to avoid running new Ethernet. Neither alternative was tested
   here or is necessary to buy alongside the adapter now.

More illumination at unchanged ISO/aperture can shorten exposure while preserving
photon count, but faster shooting then needs proportionately more transfer
bandwidth. The existing CPL/cross-polarization need not be removed. Processing
on the PC as frames arrive can reduce the final wait for Strehl, but does not
reduce the original RAW traffic that the owner wants retained.

## Evidence, commands and limits

Commands actually run from the repository root:

```powershell
python scripts/research.py search sony capture
python experiments/ORCH-drift-check/prior_art.py sony capture
python -X faulthandler experiments/sony-capture-throughput-2026-11-11/run-probe.py
python -X faulthandler experiments/sony-capture-throughput-2026-11-11/bench-settle.py
python experiments/sony-capture-throughput-2026-11-11/analyze.py
```

The probe ran twice with the successful camera capture paths: pilot then refined
USB tracing. An initial tab-delimiter harness error took no exposures. Eight
direct diagnostic frames and two app frames passed PC receipt/hash/length checks
and independent `rawpy 0.27.0` full active-array decode (7028x4688). The 100 ms app
arm took zero images; the intended later arms were not run. Recovery used the
existing API, without app restart or shutter replay. Focus, 500 ms setting and
cleared test marks were verified on the final ready session.

Evidence lives in `outputs/sony-capture-throughput-2026-11-11/`: the original
and refined `direct-probe*.json`, `direct-raw-verification*.json`,
`settle-comparison.json`, `settle-fault*.json`, `final-ready.json`,
`existing-cadence-attribution.json`, `summary.json`, measured harness snapshots
and hashes. The native bridge SHA-256 is
`73abfba37853ac0c0315e1ce21dac4300c3ab1db7a374fad45d93f31ad5b3551`;
the installed headless SHA-256 remains
`219d707946c9e0a55db217d1f0e596e6a8a55ffa0300fed7fe1a5fb160d37076`.

No sharpness metric or optical-quality gate was introduced, so flat-ROI and
photographic superiority controls do not apply to these transport/timing claims.
Byte verification is not focus verification. USB tracing, live-view controls
and compression roundtrips are author-run evidence, not independent research
validation or measurements of a future A7CR. The temporary USB monitor was
stopped and its module unloaded. No production source, router setting, camera
SD content, capture corpus or existing RAW was modified.
