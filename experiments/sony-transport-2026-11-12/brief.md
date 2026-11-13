# Production exact RAW transport compression

Owner root, 2026-11-12. The owner requests production integration of the measured
compression experiment. Prior work: sony-raw-compression-2026-11-12 established
exact independent-frame CFA/Zstd coding; sony-edup-2026-11-12 verified the adapter
and replayed the prototype. Neither deployed a production codec. Unified search
and mechanical prior-art search precede this allocation.

Own the capture crate's transport, receiver, transfer diagnostics, minimal browser
status wording, Pi runbook, this qualification and the corresponding ledger row.
Preserve existing dirty source and installed binaries/configuration before edits
or deployment. Do not alter camera USB behavior, exposure settings, focus settling,
LAN/authentication boundaries, existing RAWs or destination configuration.

Implement bounded streaming Rust encoding and decoding with explicit capability
negotiation. Preserve the original file length and SHA-256, including inactive
sensor borders and metadata. Unsupported TIFF layouts use generic compression;
incompressible chunks use identity. Old receivers remain compatible. Keep original
Pi RAM files until durable verified PC acknowledgement, including interrupted,
malformed and duplicate uploads. No temporal frame dependencies, lossy signal
processing, SD spool or compressed archival format.

Acceptance: deliberate corruption, truncation, bad dimensions/lengths/versions,
expansion bombs, trailing data and failed acknowledgements must fail before the
positive throughput claims. Exercise real HTTP retry/overwrite paths, full source
byte identity on real 61 MP and A7C II files, and a short physical capture with
focus/marks restored. Identity transfer is the causal baseline. Measure complete
production HTTP delivery, bounded memory and encoder workers; keep USB/exposure
cadence separate. Deployment must find the camera idle with no pending RAWs and
retain rollback binaries. Author operational qualification only; no optical-quality
or A7CR hardware claim. No multi-hour soak is implied by short tests.
