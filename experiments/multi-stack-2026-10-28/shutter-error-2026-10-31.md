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

## User-directed product correction

The user then clarified that choosing modes/removing mismatched passes is not the
desired workflow: Strehl should handle the differences together and intelligently
merge whatever information improves the best supported result. The automatic
analysis/planning and composable local fusion requirement is now the first
priority in `docs/multi-stack-handoff.md`. It supersedes treating the current
global-mode eligibility restriction as the intended end state. This small error
reporting patch does not implement that planner or fulfill that larger objective.

## Verified replacement

Strict UI clippy passed with four Cargo workers and incremental compilation off.
The fresh source-inclusive replacement is
`outputs/strehl-multi-stack-2026-10-31-fix-1/Strehl.exe`, build
`desktop-96be5fd0a5b4e6c3`, built from committed
`bbdf45a0ddd1b7c419c48787a7d9d6ef8a17c280`. All package and copied-source hashes
verify. Build elapsed 184.270 s; sampled peak private memory 3,405,971,456 bytes.
The matching source/relink ZIP and notices remain alongside the executables.

The actual packaged desktop was exercised with the exact seven folders in the
reported order, Combine, primary 0 and 48 GiB, using an isolated catalog/output
and the local control API. It scanned the same 1,650 originals and the actual
owned engine refused the incompatible settings. The application snapshot now
reports the different-shutter reason and visible Exposure range/Aligned layers
suggestion, with exit status and full log location. No completed photograph was
published; the headless process saved and exited 0 after shutdown. Command:

```powershell
python -X faulthandler experiments/multi-stack-2026-10-28/verify-shutter-error-ui.py --binary outputs/strehl-multi-stack-2026-10-31-fix-1/Strehl.exe
```

Compact receipts are in `shutter-error-2026-10-31/` beside this report; full local
commands/logs/snapshots are under `outputs/multi-stack/shutter-error-fix/`.
This verifies the immediate error-reporting repair, not automatic merging or
compatibility of the mixed inputs. The latter remains the new product priority.
