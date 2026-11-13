# Exact RAW transport compression

Owner: root. Requested 2026-11-12. Identifier: sony-raw-compression-2026-11-12.

Question: can per-image and inter-image coding reduce A7CR pixel-shift network
traffic enough to justify encoding on a 4 GB Pi 5? Compare size, CPU latency,
throughput, memory and recovery dependencies, retaining every original ARW byte.
No A7CR is available. Distinguish real camera samples, decoded-CFA surrogates,
and explicitly simulated pixel-shift groups; none certifies A7CR transfer timing.

Prior work: the 2026-11-11 Sony throughput investigation measured Zstd levels
1/3 on two already lossless-compressed A7C II files (about 18 percent saving).
The A7CR sequencing report leaves combined capture/transfer unverified. Unified
research search and the mechanical prior-art check were run before allocation;
the latter located M61's discussion of lossless capture, not a transport codec.
Consult published predictive compression methods (JPEG-LS, JPEG XL, CCSDS-123,
byte/bit shuffle and temporal residual coding). Do not read prohibited sources.

Consumer: PC receiver reconstructing the exact original ARW before durable save
and acknowledgement. Compression does not alter CFA values, metadata, previews,
padding, noise or bit depth. Original SHA-256 and length are mandatory. This is
an integer reversible transport transform, not a change to Strehl's f32 image
processing. Original captures remain read-only.

Arms: raw-byte Zstd; reversible byte/bit packing and CFA spatial predictors;
lossless JPEG/JPEG XL baselines if available; temporal residuals with Bayer-aware
spatial prediction, running references and tile-level spatial/temporal choice.
All selector metadata and reference costs count. Independent frames remain the
recovery baseline. All transformations must have actual inverse implementations.

Controls before real timings: exact constants/ramp and duplicated frames as
positive controls; independent random noise, wrong reference, wrong Bayer phase,
changed exposure/texture, truncated/corrupted payload as negative controls. SHA
failure must reject output. Duplicate-frame wins are not photographic evidence:
fresh photon/read noise must remain in realistic repeat/simulated arms. Assess
cross-frame advantage against the strongest independent-frame baseline, not only
against uncompressed or plain Zstd bytes. Camera compression cannot be compared
as identical exposures; preserve that limitation.

Bounded work: one physical camera owner, only if idle with no pending delivery;
at most 16 diagnostic exposures, no lens movement, host RAM-only RAW destination,
restore camera settings and reconnect afterward. Abort on uncertain capture.
No production service or capture-default changes without complete transport
verification. PC experiments use bounded samples from existing read-only files.
Pi benchmarks use isolated RAM, one benchmark at a time, bounded memory and record
temperature/throttling/load. Do not disturb a user's stack. No purchase or router
changes. Preserve artifacts and source/build identities. No quality alteration
claim: bit-exact full-file reconstruction is the acceptance metric. Independent
research review is not yet commissioned; author-run checks will be labelled.

Completed scope: twenty public genuine A7R IV pixel-shift ARWs, existing A7C II
RAWs, synthetic noise/failure controls, native Pi timings and full LAN replays.
No physical exposures or camera-setting changes were needed. Tile selectors,
trained entropy models, new temporal transforms, production HTTP integration,
and A7CR hardware support remain outside the completed prototype. See results.md
for measured gains and limits. The working wire path uses independent frames.
