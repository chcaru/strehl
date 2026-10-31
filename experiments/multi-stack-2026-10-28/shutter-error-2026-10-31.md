# Tryout follow-up: hidden shutter-time incompatibility

The user reported failed desktop runs `strehl-1793474750997-32624-0` and
`strehl-1793474770086-32624-1` under Pictures/Strehl. Both retained logs end with:
`Error: combined passes have different shutter times; use HDR or aligned layers`.
Both immutable manifests use Combine, primary 0, and seven bug-3 passes in order
107/106/105/104/103/102/100. The first enables original-CFA reconstruction, the
second disables it; this does not affect the metadata eligibility refusal.

The recorded corpus census has 1.6 s for 103--107 and 2 s for 100/102. The known
same-exposure 106/107 pair is suitable for a first Combine/Repeat trial. Exposure
range permits shutter diversity subject to its compatibility checks; Layers
preserves appearances separately. Switching modes does not establish compatible
lighting/geometry for every selected pass.

The numerical eligibility guard is retained. The desktop previously discarded
the engine's actionable reason and showed only its exit status/log location.
The session worker now reads at most the final 64 KiB, extracts the last explicit
`Error:` reason, bounds it to 1,200 characters, uses the visible Exposure range
label in the shutter suggestion, and retains the full log path and exit status.
Unreadable logs or progress-only output preserve the generic failure message.
The mode guidance now explicitly includes shutter time alongside aperture/ISO.
No recipe is silently switched to another mode.

Fresh `cargo test --locked -p strehl-ui session -- --test-threads=2` passed 66
tests, including real log-file controls for the reported error, a later error in
a large log, progress-only/missing logs, malformed UTF-8 and bounded Unicode
diagnostics. UI formatting passes. Replacement package/build verification is
recorded below when completed. The original tryout stays intact because the user
may still have it running.
