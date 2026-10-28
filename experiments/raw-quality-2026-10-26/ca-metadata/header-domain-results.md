# Current calibration-selection header domain

2026-10-27. Independent receipt review; no additional original-file reads, pixel decoding or fitting by this reviewer.

**MEASURED:** the current 24-source selection replay from each of six calibration stacks contains neither weevil149's coarse focus code86 nor its exact 32-value CA table. Bug2-149's exact joint `(code58, table)` occurs in four stacks; only tweezers also matches the complete recorded identity stratum. This supports a difference in sampled metadata states. It establishes neither physical chromatic geometry nor correction applicability.

## Execution and independent checks

Root ran the following command from the worktree, inside the bounded owned job recorded in [invocation.json](../../../outputs/raw-quality-2026-10-26/ca-header-domain-job-1/invocation.json):

```powershell
C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe -I -B -X faulthandler C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\experiments\raw-quality-2026-10-26\ca-metadata\header-domain.py --out C:\Users\chris\.codex\worktrees\raw-quality-october26\strehl\outputs\raw-quality-2026-10-26\ca-header-domain-1
```

**VERIFIED:** [receipt.json](../../../outputs/raw-quality-2026-10-26/ca-header-domain-1/receipt.json) contains 144 distinct source records, 24 per stack, with successful native header inspections and matching before/after source SHA-256, byte length and mtime. I independently checked every generated header's hash, source path, coarse code, full table and CA setting against its receipt, then recomputed all twelve reference/stack overlap comparisons; no discrepancy occurred. Retained exact-source checks for bee-3 indices0 and298 agree on code, table and setting. The runner also verifies final directory inventories and executable/reference bindings. This review verifies recorded source-preservation evidence without rereading the originals.

The source SHA is `58fc57ba316354988be4c9cfc79801c6d2e6cb1822cc4a9c41ef3da242328534`; executable SHA is `89a0d92aad1628cfdfe75f39d2627ed3679990c5b3381d8839f6cce61b7f2388` (native header reports `0.1.0-alpha.6 (4813e46bdc9a-dirty)`). The reference SHA is `d9fb0f7a3f08620786c26577b50f08d881063b7353891857a958f3ec75327006`.

[Process receipt](../../../outputs/raw-quality-2026-10-26/ca-header-domain-job-1/process.json): exit0, 12.078s wall, 24,727,552 bytes peak job committed memory, no termination or surviving child. Python3.12.10, one worker and one native thread (`RAYON_NUM_THREADS=1`); limits120s/4GiB. These are operational costs, not a host-load-controlled benchmark. Full original bytes were read for hashes; image pixels were not decoded.

## Observed overlap

Every row contains 24 headers. “Matched identity” means camera, firmware, lens/TC, focal length, aperture, ISO and CA setting all equal the references; each stack has one such recorded identity. All six lack both the weevil code and table.

| Current stack | Observed codes | Bug2 joint match | Identity-matched headers | Bug2 joint match within identity |
| --- | --- | --- | --- | --- |
| tweezers-cpl | 56–59 | Yes | 24 | Yes |
| bee-3-cpl | 58–66 | No | 24 | No |
| coffee-bean | 57–60 | No | 0 | No |
| lavendar-cpl | 56–64 | Yes | 0 | No |
| couch-fibers-cpl | 56–64 | Yes | 0 | No |
| bee-2-cpl | 58–66 | Yes | 0 | No |

Lavendar uses ISO200; couch and bee2 use ISO400, versus reference ISO100. Coffee uses ISO50/f8 versus ISO100/f5.6. All stacks contain code58, illustrating why code equality alone does not establish full-table equality.

**ARGUED limits:** this replays the historical selection recipe on today's directory inventories; missing historical coefficient/source bindings remain missing. It is neither a census of unsampled frames nor recovery of the calibration-fit identities. Raw code ranges have no established physical-distance meaning; table equality does not establish units, freshness, PSF behavior or photographic utility. No correction coefficient, automatic policy or quality gain follows. Effective registration still needs held photographic validation, including complete weevil and bug2 outputs. This bounded header observation is closed; the softness defect remains unresolved.
