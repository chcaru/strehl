# Camera website relay and Android access

Allocation `sony-capture-ui-2026-11-07-away-relay`, root, 2026-11-07 Pacific.
Author verification only. [Brief](away-relay-brief.md).
This changes access to the existing r5 camera website. There is no change to
the Rust app, Sony bridge, capture settings, reconstruction or optical findings.
No SYNTHESIS fold or photographic-quality claim is involved.

## Result and scope

**VERIFIED by owner report:** Android Chrome can now open the camera laptop's
local page. The phone showed `ERR_TOO_MANY_RETRIES` on HTTP while the wired PC
could load the same server. Granting Chrome **Nearby devices** permission fixed
the phone. The owner replied, "It loads now." No router, firewall or server
change was needed for this symptom. This is consistent with Android's documented
[local-network permission group](https://developer.android.com/privacy-and-security/local-network-permission);
the phone's exact Android/Chrome versions were not collected.

**VERIFIED by deployment checks:** a portable Cloudflare connector on the
personal wired PC relays the existing laptop website to a temporary HTTPS URL.
The generic page returns HTTP 200, the camera API refuses missing/incorrect
keys with 401, and a foreign browser origin gets 403. A separate invocation
confirmed the owned connector was still running and HTTPS remained reachable
after startup returned. No actual camera commands or authenticated camera API
requests were issued by this setup; the operator retains the pairing key.

**VERIFIED by owner report:** the phone loaded the actual camera preview with
Wi-Fi off through this HTTPS route. The owner replied, "Preview loads on
cellular." This closes the requested away-preview field check; it does not
establish that a physical capture or focus command was exercised over cellular.

The owner prefers a laptop-only arrangement but accepted the personal-PC relay
fallback, then explicitly approved Cloudflare carrying preview/control traffic.
Automatic approval review refused the first proposed live start until that
destination consent was obtained; no live tunnel was started before consent.
Both PCs must remain awake and the laptop must keep Strehl Capture running.
Nothing was installed on the corporate laptop, and no corporate policy, router
setting or firewall setting was altered. The preferred laptop-only arrangement
still needs an outbound remote-access method permitted on that laptop.

**VERIFIED in source and the existing r5 checks:** RAWs remain on the camera SD
card. The new relay carries the existing preview/control web traffic, with its
per-session pairing key. The hop from relay PC to laptop still uses LAN HTTP;
the public endpoint uses HTTPS. There is no new RAW download, filesystem browser,
shell or metadata-export API. Loss of the browser/relay leaves the laptop's
sequence worker running. This report does not claim an independent audit of
Cloudflare or the operating systems.

## Verification and controls

The connector is pinned to the official
[2026.10.7 release](https://github.com/cloudflare/cloudflared/releases/tag/2026.10.7).
Its 55,390,512-byte executable matched the release asset digest:
`2493dbc168923bb3e59e5e7716f71deced92992eea9acd6e9d74f84ac7751343`.
The helper verifies that digest before execution. This private helper ZIP does
not redistribute the vendor executable: it downloads directly from that release.

**VERIFIED:** the actual HTTPS route was exercised with the explicit r5 camera
simulator in Edge/Playwright at 390 x 844 CSS pixels. A browser authenticated,
decoded a 960-pixel-wide JPEG, marked both focus bounds, jogged one command unit
and completed a two-plane simulated stack. No browser errors remained. The
complete phone screenshot was inspected. The simulator and test connector were
retired; only the separately authorized live relay remains running.

The first browser harness run failed because its string-evaluated wait conflicted
with the page's content policy. Replacing that wait with Playwright's DOM property
assertion allowed the same protected page to pass; the policy was not weakened.
The successful transport receipt identifies the app and connector hashes. The
app is the previously verified r5 binary, SHA-256
`d25a59160b213b76a76c5f73e4f9910f6113590f0d551948059be8578d5d7288`.

**VERIFIED:** the helper gate exercise rejected eight invalid target URL forms.
A local HTTP fixture presenting an unprotected API or the wrong page could not
start the connector. A modified connector was refused before launch. A child
process with deliberately mismatched creation time could not be stopped; the
exact owned child could. All eight ZIP entries were accounted for, manifest
sizes/hashes matched, and the bundled helper matched the working source.
These negative controls test refusal paths, not just successful setup.

The first authorized live attempt reached Cloudflare but failed its 50-second
page-readiness deadline; the helper stopped that owned process. The root cause
of that attempt was not established. A retry with the same helper/binary passed
all gates; a brief initial DNS-resolution failure on the retry recovered.
The final coexistence test initially reproduced a narrower transient DNS failure
between a successful page request and the following authentication check. The
helper now retries transport errors across the entire bounded readiness check,
while immediately refusing responses that fail pairing or origin checks. An
inert-child regression plants that DNS failure and exercises all three fatal
response cases. A subsequent full simulator run passed with the revised helper.
The final read-only check is retained without a public hostname, PID, camera key
or user filesystem path in the committed receipt.

Commands and artifacts from the work, run at repository root:

```powershell
python tools/sony-control/package-away-relay.py --out outputs/sony-capture-ui/strehl-away-relay-2026-11-07-r2 --camera-url http://10.0.0.7:8787
python experiments/sony-capture-ui-2026-11-07/verify-away-relay.py --exe outputs/sony-capture-ui/strehl-capture-win-x64-2026-11-07-r5/Strehl-Capture.exe --connector outputs/sony-capture-ui/away-relay-2026-11-07/cloudflared.exe --out outputs/sony-capture-ui/away-relay-test-04
python experiments/sony-capture-ui-2026-11-07/verify-away-relay-helper.py --connector outputs/sony-capture-ui/strehl-away-relay-2026-11-07/cloudflared.exe --zip outputs/sony-capture-ui/strehl-away-relay-2026-11-07-r2.zip --out outputs/sony-capture-ui/away-relay-helper-check-03
python outputs/sony-capture-ui/strehl-away-relay-2026-11-07/away-relay.py start --connector outputs/sony-capture-ui/strehl-away-relay-2026-11-07/cloudflared.exe --download-connector --state-dir outputs/sony-capture-ui/strehl-away-relay-2026-11-07/state --camera-url http://10.0.0.7:8787
```

The last command first returned exit 1 during the readiness timeout. The
successful retry imported the same packaged `start` function with the same
paths/target, wrapping `fetch` only to print read-only response codes and
readiness errors; it returned exit 0. After updating the helper files in the
live folder, the exact Start command above returned 0 and reused the original
PID and URL. No working relay restart was needed. The package, simulator and
helper verification commands also returned 0.
Python was 3.12.10, Windows x64; the browser was Edge under Playwright. One demo
session/connector ran at a time; the final test also ran alongside the live relay
to check that test cleanup preserved the live process. This is functional
verification, not a latency or uptime benchmark. The Rust code was unchanged,
so its earlier r5 compilation
and test evidence remains in the [browser report](web-remote-results.md).

**VERIFIED:** targeted documentation checks passed for four changed Markdown
files, nine local links and all 314 table rows in those files; each file has one
final newline. The four Python sources parsed and matched the receipt hashes.
`git diff --check` passed for the tracked documentation changes. The broader
`python scripts/corpus_lint.py` returned 1 with 16 violations confined to
unchanged research documents (seven table-width errors, the same seven unescaped
code-span bars, and two missing final newlines). The sandbox denied its Git EOL
lookup, so its Git-dependent line-ending checks were skipped. This is not a
claim that the whole documentation corpus passes; those unrelated files were
left untouched. See the local `away-relay-corpus-lint.log` for complete output.

## Delivery and verification limits

- Helper ZIP: `strehl-away-relay-2026-11-07-r2.zip`, 12,604 bytes, eight entries.
- ZIP SHA-256: `466089d5710f31ce48658611fc0bc0024f619ded2e74ff160fc6ae79804f9c43`.
- Included source and MIT/Apache notices; start, stop and status launchers.
- [Transport receipt](evidence/away-relay-transport.json).
- [Helper/refusal receipt](evidence/away-relay-helper.json).
- [Deployment/source receipt](evidence/away-relay-deployment.json).

The live relay folder contains an HTTPS shortcut and an ownership record.
Start reuses the owned running connector; Stop checks executable path and
Windows process creation time before terminating it. Stop affects only the
relay. Starting after it stops creates a new hostname. Users must stop it before
moving its folder. Python must be available as `python` on this personal PC.

**UNVERIFIED:** physical-camera focus/capture commands through the public route,
long unattended uptime and automatic restart after a PC reboot. The owner
confirmed actual live preview over cellular; the broader controls passed the
simulator transport test. The relay is a portable owned process, not an installed
auto-start service. These checks do not establish corporate policy approval for
any different deployment on the managed laptop.
[Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)
have no uptime guarantee and are not a permanent hosting arrangement.
