# Security reporting

Strehl is experimental software and has no published security-support window or
guaranteed response time. Use a current reviewed build; old research binaries
are retained for provenance, not maintained as supported releases.

For a suspected vulnerability, use this repository's private vulnerability
reporting channel if it is enabled. If no private reporting channel is
available, open an issue asking for a secure contact method without including
exploit details, credentials or private files. Do not assume a public issue or
an image attachment is confidential.

Include the build identity, operating system, affected command or interaction,
expected impact and a minimal reproduction. Share only files you are authorized
to disclose. RAW images, embedded previews, saved projects and logs may contain
paths, camera identifiers or location metadata; review them before sharing.

The desktop processes RAW files and saved activity locally and starts an owned
engine child process. That process separation supports cancellation and memory
isolation; it is not a security sandbox. Treat malformed or untrusted image and
project inputs with the same care as other native file-processing applications.

Maintainers should establish and verify a private reporting route before a
public release. The [release checklist](docs/public-release.md) tracks that work.
