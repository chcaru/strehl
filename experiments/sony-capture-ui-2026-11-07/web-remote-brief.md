# Browser capture remote

Allocation: `sony-capture-ui-2026-11-07-web-remote`, root, 2026-11-07 Pacific.
The owner requests browser control from phone/another computer, including while
away. Continue the existing SD-only USB capture application. LAN HTTP plus a
private Tailscale connection provides access without a public camera endpoint.
Tailscale is not installed on this development machine; authentication and
installation on the actual laptop/phone remain owner setup, not a simulated fact.

Prior lookup commands: `python scripts/research.py search 'capture remote' --limit 5`
and `python experiments/ORCH-drift-check/prior_art.py 'web remote' 'camera session'`.
Read the existing capture reports, desktop-control contract and SYNTHESIS scope.
No reconstruction change or image-quality claim is part of this continuation.

Keep one camera worker and shared desktop/browser plan, marks and ROI. Network
requests must not wait on desktop painting. A disconnected browser must not
stop or restart an accepted sequence. Queue admission must reject overlapping
or stale mutations; request identifiers must prevent repeat shutter sequences.
Pause/stop target the current sequence identity, not a stale progress revision.

Remote access is explicitly enabled in the desktop. Use an OS-random session
key, QR/copy links, bearer-authenticated API and no-store previews. Disable/enable
rotates the key. Embedded assets only; no filesystem browse, RAW transfer,
arbitrary output-path API, telemetry or third-party QR service. Refuse foreign
browser origins and public peer addresses; document local HTTP and private VPN
scope, and a narrow firewall setup if Windows blocks inbound access.

The web page needs responsive live view, zoom/pan, marks/jogging, step/settle/
approach/timeout settings, camera magnification where advertised, bounded preview
survey, start/pause/resume/stop, card/battery status and the existing countdown.
Manual marks remain usable when preview fails. Run controls with an explicit
simulator: unauthorized/wrong-origin requests, stale state, duplicate commands,
multiple clients, disconnect/reconnect and completion. Exercise the actual
browser at phone/desktop sizes and the exact packaged executable. Keep all
camera capture verification simulated; preserve unrelated work and old receipts.

Primary references checked: [Tailscale quickstart](https://tailscale.com/docs/how-to/quickstart),
[Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli), and
[axum 0.8.9](https://docs.rs/axum/0.8.9/axum/). Browser UI follows the Sites skill's
local-only workflow; hosting is inside the existing Rust application.
