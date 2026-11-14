# A7CR four-shot capture qualification

The owner has connected an A7CR and requested working four-shot pixel-shift
capture on the existing Pi. This reopens the hardware-unverified question in
`sony-capture-ui-2026-11-07/a7cr-sequencing.md`, using the supplied Sony Camera
Remote Command 2.02 PTP 3 specification. Prior searches ran `research.py search
"Sony A7CR pixel shift capture"` and `prior_art.py "A7CR"`.

Scope: one exclusive camera session, capability/readback-checked four-shot mode,
absolute focus between complete groups, actual JPEG preview, bounded original
RAW delivery through the existing exact transport to the configured PC folder.
No camera-card or persistent Pi RAW storage. No optical quality or reconstruction
claim. Preserve original settings, pre-test focus, unrelated work and receipts.

Fail closed for missing/extra members, unsupported settings, wrong focus,
incomplete USB transfers, unexpected RAW layouts, and unacknowledged PC delivery.
Never replay a shutter following an uncertain result. Exercise malformed protocol
and incomplete group controls before interpreting physical captures. Verify
camera-generated pixel-shift metadata, complete RAW decode and PC hashes, then
exercise preview and phone-sized browser controls. Bounded short stacks only;
an hours-long soak remains separate. Pause/stop must finish the active group.

Resources: one camera owner, one uploader, four encoder workers; build workers 2.
Evidence and private installation data live under ignored
`outputs/sony-a7cr-2026-11-13/`; only redacted compact receipts enter source.
