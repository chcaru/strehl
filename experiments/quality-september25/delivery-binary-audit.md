# Which binary future user renders will run

2026-09-25, bounded read-only audit by pipeline_audit. No launcher, source, binary or output was changed.

VERIFIED by source and output receipts: the three scripts that created the nine recent user stacks explicitly pin `experiments/native-gpu-gather/build-native-6/strehl.exe` and SHA256 `2fd0a1615989e262fbba61e0a1587a9b8f20ff4913d3969510e967ce9d9219d7`:

| Script | Pin | Rerun behavior |
| --- | --- | --- |
| `outputs/flower-marigold-cpl/render.py` | EXE line11; hash assertion line23 | Skips stacks with completion.json. It also skips previously successful per-stage receipts. |
| `outputs/minerals-september24/render.py` | EXE line11; hash assertion line37 | Requires each per-stack output directory not to exist. Original folder layout in this old recipe also predates renamed mineral subfolders. |
| `outputs/peacock-ore/render.py` | EXE line11; hash assertion line37 | Requires each per-stack output directory not to exist. |

The actual invocation and render-process receipts under those three output directories agree. These are not a floating `target/release` selection. Compiling the fix cannot alter what they launch; replacing that retained executable in place would break their hash assertion and destroy historical provenance.

No application/UI launcher was found in the repository: its crates are CLI, core, plugin and RAW. README quickstart line650 builds a generic release binary, then invokes bare `strehl` from PATH. This audit did not inspect the user's global PATH or external shortcuts and therefore makes no claim about software launched outside the repository. Older generic scripts `scripts/render_all.ps1`, `gallery.ps1`, `gallery-ab.ps1`, `check-potency.py` and `measure-refusal-flags.ps1` have other historical/default executable paths; none pins this native build. They are not the provenance of the nine new outputs.

Three retained GPU experiment runners also explicitly choose build-native-6: `experiments/native-gpu-gather/run-device.py`, `run-device-native.py`, `run-device-coffee.py`. These are historical comparison programs; leave their receipts and selected old baseline intact.

The correction's immediate comparison route is already separate: `experiments/garnet-spatial-trace/run.py candidate --build <fresh-build> --recipe <held-recipe> --historical <old-full-receipt> --out <fresh-run>` executes the fresh bound CLI test binary, writes `candidate.tiff`, and checks unchanged source/gather/weight evidence plus historical cache replay. That route is intentionally limited to stacks with a complete historical bundle and is not a general future-stack launcher.

Recommended minimal operational handoff after full photographic review: retain the fixed release executable at a new versioned path with an explicit SHA, and add one current delivery runner accepting an explicit input/output directory (plus optional retained map/source manifest). Bind the executable path/hash in each new invocation, set the already reviewed native GPU fields, preserve automatic camera profile/WB/tone and held pyramid settings, and refuse an existing output directory. For rerenders, reuse the original ordered-source map and write a new versioned output directory; do not reuse completion files. The executable defaults should be centralized in one small current-version manifest or require explicit `--exe`/`--sha256`, rather than silently preserving three old hard-coded pins.

This is an operational correction proposal, not a claim that the new binary has yet passed its photographic gate or that other defects are resolved.
