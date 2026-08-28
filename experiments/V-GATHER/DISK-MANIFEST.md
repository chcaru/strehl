# V-GATHER disk manifest

Banked 2026-08-28 before deleting this lane's scratch, per ORCH's reclaim
instruction. Everything below is the regeneration recipe for bytes that no
longer exist on disk. Nothing in `docs/research/V-GATHER.md` cites a path under
`C:\dev\strehl-out\V-GATHER`; every number it quotes is banked in tracked
JSON in this directory (24 JSON files, 203 tracked files total, 0 untracked).

## The two pinned binaries, deleted

Both were deleted. Both are rebuildable from committed sources, so no published
result becomes unreproducible.

| pin | sha256 | bytes | built |
| --- | --- | --- | --- |
| `strehl-pinned.exe` | `F663B703AA6851292B6E37ED3202E53CF56A042019414D692309C0BED4E9704C` | 9568768 | 2026-08-27 07:23:15Z |
| `hull/bin/blend-render-pin.exe` | `37A1B1D49E11713E216E6893CF932B6570869F1197774EDDE77386AFA5F1F037` | 7011328 | 2026-08-28 02:24:44Z |

**`strehl-pinned.exe`** was the alignment/merge pin, commit **`9b05d0b7`**
("V-H2H2: correct three numbers against the persisted logs"), which is reachable
in this repository. Rebuild:

    git checkout 9b05d0b7
    cargo build --release -p strehl-cli
    copy target\release\strehl.exe <dest>\strehl-pinned.exe

Twelve scripts in this directory hardcode its old path (`ab.py`, `election.py`,
`election2.py`, `esfrender.py`, `ncount.py`, `ruler2.py`, `splitrender.py`,
`threads.py`, `timing.py` and others). **They will fail with a missing-file
error, not silently**, because each invokes it via `subprocess` on an absolute
path. Repoint `EXE` before re-running any of them.

**`blend-render-pin.exe`** was the hull-ladder pin. Its source is committed at
`crates/strehl-cli/examples/blend-render.rs`. Rebuild:

    cargo build --release -p strehl-cli --example blend-render

`hul_run.py:22` hardcodes the deleted path. The hull modes are only reachable
through this example, not through `strehl stack`, which is why a separate pin
existed at all. **The hull-ladder numbers are already banked** in tracked
`hull-render.json` and `hull.json`, so the finding that `hull_lambda` shipped
wired and inert (2 -> 4 moved 0.008% of samples) survives the deletion intact.

## What else was deleted

Two passes. Earlier tonight, 119.59 GB of full-resolution per-frame TIFF dumps
under `sharp/`, deleted only after confirming `sharp.json` was populated from
them and tracked. Then 210 files at wind-down: warp caches
(`*.warpmap.txt`), gate-floor logs (`gatefloor/g0-*.log`), sweep JSONs, and
per-subject `cert/*/cache/` intermediates. All are regenerable from the
committed scripts in this directory plus the read-only originals in
`D:\personal\macro`, which were never written to.

## What was NOT measured

No measurement was abandoned to free disk. The open gaps in
`docs/research/V-GATHER.md` Part 17 are gaps of scope, not of deleted evidence:
per-subject band qualification at 0.1093 cyc/px was never run on any of the six
subjects, and the timing hypothesis from the original charter was never measured
by this lane. Neither would have been recoverable from scratch that existed.
