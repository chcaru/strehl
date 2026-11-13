# EDUP Wi-Fi qualification

Owner root, 2026-11-12. User has plugged the ordered EDUP into the Pi and asks
to configure and test it. Scope: native driver/USB negotiation, existing home
SSID on 5/6 GHz, measured Pi-to-wired-PC throughput, RAW replay with exact-byte
receipts, persistent preferred routing with onboard fallback, camera recovery
and short physical capture through the existing LAN receiver.

Prior work: sony-capture-throughput-2026-11-11 measured approximately 236 Mbit/s
onboard Wi-Fi and separated USB/exposure overhead. sony-raw-compression-2026-11-12
measured 123 MB to 54.5 MB exact compression and 2.38-2.65-second SSH-carried
delivery. Those are baselines, not measurements of the new adapter. Unified
research search and mechanical prior-art search ran before allocation.

Preserve the existing profile, credentials and source. Never print secrets.
Retain onboard management access during connection tests; use a timed rollback
for routing changes. Benchmark only with no active stack or pending upload.
No router changes, firmware flash, custom kernel, cloud access or production
codec deployment is needed. RAW fixtures remain read-only on PC and in tmpfs on
Pi. Keep every original byte, prove hashes, preserve temporary-file receipts.

Compare measured bands rather than choosing by advertised PHY speed. Bind
network tests to the intended adapter; record routes, station counters, USB
speed, signal, link rate, load, temperature, exact commands and repetitions.
Keep raw network measurements distinct from compressed effective RAW rate and
actual exposure cadence. A bad hash must fail before making a delivery claim.

Physical capture: at most three frames through the existing owner/API, no
unverified focus settling change, preserve any user marks, return the lens and
plan afterward. The initial app has an existing focus-information fault, with
no uncertain exposure, active stack or pending RAW. Use normal recovery first.
Report any remaining camera problem separately from network qualification.

Author verification only; no independent research or optical-quality claim.
