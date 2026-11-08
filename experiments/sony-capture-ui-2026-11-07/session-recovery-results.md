# Long-stack browser pairing recovery

Allocation `sony-capture-ui-2026-11-08-session-recovery`, November 8 Pacific.
Root, author verification only. [Brief](session-recovery-brief.md).
Delivered together with [camera fault recovery](fault-recovery-results.md).

**VERIFIED:** the old server had no elapsed-time or inactivity expiry. The old
browser deleted its tab-stored key on any single HTTP 401 and displayed
"Pairing expired. Open a new link from the camera laptop." The regression
exercise planted one 401 against r5: the browser erased its key while a direct
request with that same key still returned 200. This establishes the misleading
sign-out behavior, not the cause of the owner's original 401.

**UNVERIFIED:** why the owner's original request was rejected. The original
pairing link was unavailable. The report occurred on both LAN and HTTPS; it
does not identify Cloudflare as the cause. No live pairing key was collected and
no camera command, laptop restart or relay restart was performed for this fix.

## Resulting behavior

**VERIFIED in source and the actual packaged browser:** pairing persists across
browser processes using local storage, with tab storage and memory fallbacks.
The old tab key migrates. A temporary rejection or lost connection preserves the
key and last confirmed progress, disables camera commands, and retries read-only
status requests with bounded backoff. Wake/online events prompt another read.
There is no age-based key expiry. Explicit Forget clears this browser's stored
pairing and its other open tabs. Server revocation still refuses the old key.
LAN and HTTPS origins remember pairing separately.

A separate random public server-session identifier distinguishes an identified
server restart/revocation from a transient response. It is independent of the
192-bit pairing key. Repeated rejection offers Retry saved pairing and a field
for a replacement link. Authentication, origin and peer-address restrictions
remain enforced. Late state, preview and command replies from an older pairing
attempt cannot overwrite a newer one. Camera commands are never retried.

Opening a replacement `#key=` link in an already open tab now applies its key,
then removes the fragment. The first r6 browser exercise exposed the missing
same-document hash-change handler; that failed artifact was retained locally.
Wrong keys are still rejected by the server, including control requests.

## Verification

Commands ran from the repository root. Final browser tests used the r10 Windows
package, Edge/Playwright and explicit simulator servers. The source/build
identity and common native checks are in the [fault recovery report](fault-recovery-results.md).
The [browser receipt](evidence/session-recovery-verification.json) contains the
old/new executable hashes, all ten exercised cases, capture count and zero
unexpected browser errors.

```powershell
python experiments/sony-capture-ui-2026-11-07/verify-web-session.py --exe outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-08-r10/Strehl-Capture.exe --baseline outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r5/Strehl-Capture.exe --out outputs/sony-capture-ui/session-recovery-browser-r10
```

**VERIFIED:** one 401 during capture, network loss, a lost Start reply, browser
process closure/relaunch without a URL fragment, a stale 401 after re-pair,
changed server-session identity, same-tab replacement links, wrong-key refusal,
cross-tab Forget and storage denial all follow the intended recovery paths.
The same simulated sequence continued; exactly one Start request was sent.
The server's real HTTP unit check also rotates the key/session identifier and
rejects the prior key after an actual server restart.

**VERIFIED, bounded check:** advancing the browser clock by 24 hours does not
expire pairing. **UNVERIFIED:** a real hours-long soak on the owner's Android,
corporate laptop or Cloudflare connection. A clock jump is not that soak.
Complete mobile offline/re-pair and desktop recovered screenshots were inspected;
offline progress is explicitly labelled last confirmed and controls are disabled.

References: MDN's [session storage](https://developer.mozilla.org/en-US/docs/Web/API/Window/sessionStorage)
and [local storage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage),
and Playwright's [clock control](https://playwright.dev/python/docs/clock).
These explain storage lifetime/test mechanics; the executable exercises establish
the application behavior. No optical-quality claim or SYNTHESIS fold.

## Install

After capture finishes, close the old laptop app, extract the entire new ZIP,
run its executable, enable Web remote and pair each browser with its current
link. Refresh existing browser pages to load the embedded updated assets.
The existing personal-PC relay can keep its camera target if the laptop address
and port remain unchanged. Restarting the app creates a new pairing key.
