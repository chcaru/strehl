# GPU full-size singleton cost and independent audit

MEASURED by root on 2026-10-27; independently VERIFIED from saved receipts and source. No additional job, RAW decode or image computation was run for this audit.

Exact root command, from the repository root:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-27/dual-tree-cfa-gpu/run.py cost 2 --screen-iteration 2
```

This is build2, cost iteration1. [The process receipt](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-cost-1/process.json) records exit0, exactly one passing `weevil_source149_cost` test, 22.968 seconds wall, clean pipe/job termination, zero remaining processes and no kill. Four CPU workers, the frozen CA-off CPU gather, seven dual-tree levels and sixteen actual original-u16 noise probes were retained. The [scientific receipt](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-cost-1/output/receipt.json) and [completion](../../../outputs/raw-quality-2026-10-27/dual-tree-cfa-gpu-cost-1/completion.json) bind the result.

## Identity and scope

| Item | SHA256 |
| --- | --- |
| Frozen executable | `84b8a52c6027179fd7808f70ceceed721437d26ec3e670146e2beacc9b7ae8a7` |
| CUDA server | `b40bead68adb6359ddf103b5cbba53bac97b9c4a9c4fc364b82dc61147dd1a4f` |
| Ordered-FIR helper | `16688f2bf6b555c2fe5c90e4d141415ddc0b59d0d7574f847f55a13bbd715dce` |
| Scientific receipt | `278e89d319c661483db58053650e5a288feb2b8ecf8516b207d6e70a50794891` |
| Completion receipt | `efdcef2bf1f28831b5145f255f2923095e70dafd64056e33101e453b386b9b40` |
| Process receipt | `e4aa954c0c43d7f7694b01b9239878b7fc686ce950dba549ad99605afea42ea8` |
| Prerequisite screen2 | `44627a41fc04b1e7362f13c087790da2c3b1a27609e9638cb543a9a3ec974c09` |

The only decoded source was original ordinal149, `D:\personal\macro\insects\bug-3\107MSDCF\DSC00150.ARW`, SHA256 `e85572179c8a98f5a2de2be5c81cd0b1bdeae67999aa00e585c6dde35f531154`. The held map is `4a76cd0c56c3a525e70f5bf72b965adb706131618c5bf49d0ae853fbf341c225`; input-order manifest is `0235564cf5131e7eb5e4ea251c16ea9272f6a55a9d8cc6efc717970615a30d6f`. Reference149 and crop `[34,23,3448,2298]` produce6896x4596 native pixels.

All sixteen completion-bound references were independently rehashed. The sole worker reports source IDs `[149]`, sixteen probe draws, unchanged helper/CUDA-library bindings, the same compiled PTX as screen2 and clean child exit under the parent job. Source149 content and all299 original metadata are preserved. The receipt explicitly says all299 contents were not reread. Output sizes were checked; this audit did not redundantly rehash all large TIFF payloads.

## Mechanical result and cost

VERIFIED: actual four-phase callback equals canonical gathering; singleton hull and mean equal the gather, and baseline/candidate CFA/RGB16/linear pixels and material metadata agree. Actual pre-hull reconstruction and uniform-transform nulls pass on every phase: worst maximum0.00390625DN, worst RMS0.000149778DN. All three full-size single-source masters exist. This is not a complete299-stack baseline comparison; `baseline_pixel_golden_exact` remains null for cost mode.

MEASURED source phase12.3356226s; finish6.0113382s. Candidate processing is10.9728468s, including8.5464554s CPU probe preparation/gather and2.1586134s wire plus synchronized CUDA; the worker's probe computation is0.890s within that path. The source timer includes first decode, canonical fold, sixteen probes, source checks and chunk absorption. Finish includes synthesis, three master writers/readbacks and final preservation checks. Startup outside these timers was4.3899951s; the declared projection adds a fixed120s margin.

DERIVED unchanged projection: `299 * 12.3356226 + 6.0113382 + 120 = 3814.3624956s`, or63.57minutes. The original1200s practical-speed gate **fails**. One source and one placement do not guarantee299-source timing, file I/O or finish cost; this is not measured full-workflow performance.

MEASURED peak host job commitment14,253,887,488bytes, leaving778,498,048bytes (about0.73GiB) below the14GiB cap. Full combined/current canonical state across75-frame chunk transitions was not exercised. Torch peak allocated/reserved memory was7,519,746,048/9,527,361,536bytes under24GiB; driver module storage is separate. These are guarded observations, not proof of full-run peak memory.

The separately allocated [photographic observation](photographic-observation/brief.md) is ongoing at this report's publication. It preserves the speed failure and generated colour/glint failures while testing complete-image usefulness under its own finite budget. No photographic improvement, competitive speed or production admission is established here.
