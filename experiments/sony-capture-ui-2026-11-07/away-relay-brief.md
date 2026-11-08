# Corporate camera laptop: access continuation

Allocation `sony-capture-ui-2026-11-07-away-relay`, root, 2026-11-07 Pacific.
The owner reports that the camera laptop cannot install Tailscale. The wired
personal PC can reach the camera server at `10.0.0.7:8787`; the Android phone at
`10.0.0.13` initially could not. HTTP 200 and matching HTML/JS/CSS were checked
from the wired PC. The phone screenshot showed Chrome ERR_TOO_MANY_RETRIES on
HTTP. The owner confirmed that granting Chrome's Nearby devices permission fixed
local access. Do not change router/firewall policy based on that resolved symptom.

The owner prefers only the camera laptop to stay on, but authorizes the personal
wired PC as a relay if needed. Provide the immediately usable fallback here;
do not attempt installations or policy changes on the corporate laptop. Relay
only the existing camera web server, preserving its pairing/authentication and
single camera owner. No real camera commands or RAW transfers are part of setup.

Use the official portable Cloudflare connector on the personal PC, pinned to
2026.10.7 with the GitHub release asset SHA-256 verified before execution. This
creates a temporary HTTPS URL, not a permanent hosted site. Every API request
still needs the original Strehl pairing key. Never put that key in the target
URL, connector arguments/logs, relay receipts or source. Keep the old app/ZIP
unchanged. The relay must fail to start if the origin API is unauthenticated.
The owner explicitly approved routing camera preview and control traffic through
Cloudflare after the initial automatic approval review required destination
consent. That consent covers starting this relay on the personal wired PC.

Check the new HTTPS transport with an explicit demo session first. Verify actual
pairing, same/foreign-origin handling and JPEG transport without a physical
camera. After that, start the authorized personal-PC relay to the existing live
server and make only unauthenticated/read-only reachability checks. Stop only
owned test processes, matching Windows process creation time and executable
path for a persistent relay. Retain a user-visible start/stop route for the live
relay. Both PCs must remain awake for this fallback; the URL changes on restart.
Cloudflare documents Quick Tunnels as development facilities with no uptime SLA.

Prior lookup: `python scripts/research.py search 'capture relay' --limit 3` and
`python experiments/ORCH-drift-check/prior_art.py 'web relay' 'nearby devices'`.
Owning prior: [browser remote report](web-remote-results.md). No reconstruction
or image-quality claim, no new optical experiment, and no SYNTHESIS fold.

Primary references: [Android local network permission](https://developer.android.com/privacy-and-security/local-network-permission),
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/),
[official release](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.7).
