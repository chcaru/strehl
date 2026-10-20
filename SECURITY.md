# Security reporting

Report suspected vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/chcaru/strehl/security/advisories/new).
Do not post exploit details, credentials, or private photographs in public issues.
If the private route is unavailable, open an issue asking for a secure contact
method without disclosing those details.

Include the build identity, operating system, affected command or interaction,
expected impact, and a minimal reproduction. Share only files you are authorized
to disclose. RAW images, embedded previews, saved projects, and logs may contain
paths, camera identifiers, or location metadata; review them before sharing.

Strehl is experimental software and has no guaranteed response time or formal
security-support window. Use a current reviewed build. Historical research
results are not maintained releases.

The [archived residual-interpolation reference](experiments/quality-september14/residual-interpolation-reference/README.md)
retains upstream dependency pins affected by
[GHSA-6p56-wp2h-9hxr](https://github.com/advisories/GHSA-6p56-wp2h-9hxr),
[GHSA-fpfv-jqm9-f5jm](https://github.com/advisories/GHSA-fpfv-jqm9-f5jm), and
[GHSA-qr4w-53vh-m672](https://github.com/advisories/GHSA-qr4w-53vh-m672).
Do not install its historical `source/requirements.txt`. These dependencies are
excluded from the `v0.1.0-alpha.5` application and delivered source/relink kit,
and CI does not install that manifest. This scope assessment does not fix the
archived pins or establish that other dependencies are vulnerability-free.

The desktop processes photographs and saved activity locally and starts an
owned engine child process. That separation supports cancellation and memory
isolation; it is not a security sandbox. Treat malformed or untrusted image and
project inputs with the same care as other native file-processing applications.

Release signatures authenticate published bytes and their build workflow.
They do not establish that the application is free of vulnerabilities.
