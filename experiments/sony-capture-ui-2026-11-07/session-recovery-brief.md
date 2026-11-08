# Long capture browser pairing recovery

Allocation `sony-capture-ui-2026-11-08-session-recovery`, root, November 8 Pacific.
The owner reports "Pairing expired. Open a new link from the camera laptop."
mid-stack on both LAN and HTTPS. Source inspection finds no age-based expiration:
the key is immutable during each WebServer lifetime. The old client deletes it
on the first HTTP 401 and calls that expiration. Its storage is tab-scoped.
The particular rejection's cause is not established from this report alone.

Preserve the key until an explicit browser Forget or owner replacement. Remember
pairing across tabs/browser relaunch with graceful storage-denial fallback.
Retry read-only state/preview access after suspension or transient authorization
failure; retain last confirmed progress with commands disabled while offline.
Ignore stale responses from an earlier pairing attempt. Explicit server-side
revocation must continue rejecting old keys. Add a separate public server-session
identifier to distinguish restart/revocation from a transport response without
exposing keys or weakening authentication. Never retry a camera command.

Prior work: [web remote](web-remote-results.md), [away relay](away-relay-results.md).
Lookup commands: `python scripts/research.py search 'capture pairing session' --limit 3`
and `python experiments/ORCH-drift-check/prior_art.py 'pairing expired' 'sessionStorage'`.
No optical findings, RAW access, pipeline change or SYNTHESIS fold.

Commission the regression with the old client: one planted 401 must produce its
reported sign-out. Then exercise the same case with the new client, network loss,
stale rejection after re-pair, real wrong-key refusal, a changed public server ID,
tab close/reopen, Forget propagation and unavailable persistent storage. A browser
clock jump checks absence of client expiry logic; it is not an hours-long soak.
Exercise actual compiled embedded assets with a simulator and inspect mobile UI.
Test commands against only the simulator. The camera laptop and existing relay
must not be restarted, reconfigured, stopped or driven during this work.

References: [sessionStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage),
[localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage).
