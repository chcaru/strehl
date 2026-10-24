# Capture and reference-rig notes

Moved from `AGENTS.md` on 2026-10-24. Paths in code spans are repository-relative
unless absolute. Treat the values below as reference-capture observations, not
universal sensor constants; obtain actual active bounds, levels and metadata
from the input and its applicable profile. In particular, the historical white
level below is not a universal clip point (see SYNTHESIS fact 681 and
`docs/research/M54-clip-mask-measured.md`).

Keep capture corpora read-only. Count hidden and system files with
`Get-ChildItem -Force` when checking integrity. Original rule
[14](engineering-ledger.md#rule-14) records the measured `C:\dev\macro` inventory
and the byte-identical 119MSDCF mirrors; a mirror is not a second stack.
Check [captures needed](../captures-needed.md) and the relevant request in
`docs/capture-requests/` before asking for new data. Review existing owner
questions and actions for the particular request, checking their dates.

## Reference rig

Sony A7C II (`ILCE-7CM2`) + Sony FE 100mm F2.8 Macro GM OSS (`SEL100M28GM`).
Pixel pitch 5.12 um. RGGB. Black level 512, white level 15360, active area
7032x4688. Confirmed by measurement, not by documentation.

**v1 targets in-camera focus bracketing only** — camera fixed, focus moves, so
frames differ by magnification and occlusion never changes.

Focus rails translate the camera, producing genuine parallax and occlusion. Rail
support is **deferred**: no rail hardware is available to test against, and an
untested geometry model would violate rule 8. The `CaptureMode` enum and mode
detection stay in place because that is the one seam the rail case genuinely
needs. Never silently apply the breathing model to rail data — detect from EXIF
plus fitted residual signature, and warn. Never trust a user flag alone.
