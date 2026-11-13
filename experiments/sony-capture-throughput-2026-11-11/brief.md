# Capture throughput attribution

Owner: root. Date: 2026-11-11. Engineering investigation requested by the owner,
not an optical-quality experiment or an A7CR hardware certification.

Question: why does each frame take longer than exposure, which costs can overlap
or shrink, and what changes for 61 MP ordinary RAW and four/sixteen-shot groups?

Prior work: `outputs/pi-capture-performance-2026-11-11/COMPLETION.md` measured
5.00 to 3.62 seconds per frame with capture/upload overlap; its journals already
separate focus, camera acquisition and remaining bookkeeping. The SDK/protocol
audit and `experiments/sony-capture-ui-2026-11-07/a7cr-sequencing.md` retain the
unverified A7CR backend boundary. The unified research and mechanical searches
are retained in this investigation's output directory.

Use the unchanged installed bridge/service for at most eight directly timed
captures and four two-frame app runs, with 500/100/100/500 ms settling. Keep
exposure, ISO, aperture, RAW compression and lighting unchanged. These timings
can justify latency attribution, not that 100 ms preserves optical sharpness.
Stop on uncertain capture, changed user plan, failed receipt or mismatched RAW.
Never retry a shutter. Preserve new RAWs on PC; existing corpora remain read-only.

For direct capture, isolate a small RAM-only probe directory, temporarily release
the app's camera session, use one SDK owner and restore its original settings.
Record USB bulk completion lengths/times without packet payloads. A captured
notification is not assumed to be physical exposure completion. USB intervals
cover actual bulk data and cannot explain all preceding sensor/firmware time.
The first four direct captures are a trace pilot. It showed background live-view
traffic and 16 MiB URBs, so completion timestamps alone cannot measure transfer
duration. The next four retain matched USB submissions/completions and compare
live view on/off/off/on. Compare commands with and without the trace; report trace
overhead uncertainty rather than claiming diagnostic non-perturbation by RAW
hash (physical exposures are not byte-identical controls).

Real file SHA-256/length and independent decode establish transport integrity.
Synthetic corruption/idempotence controls already passed in the preceding
qualification; no new integrity metric or sharpness score is introduced.
Compression probes must roundtrip to exactly the original bytes; any A7CR size
or speed forecast is DERIVED/UNVERIFIED and names its assumed file size.

Budget: one physical capture worker, at most 16 exposures, bounded RAM with a
completed file delivered before the next direct probe; no public deployment,
router configuration, SD-card writes, independent-review or multi-hour claim.
Leave the production capture default unchanged and the camera ready afterward.
