# Independent photographic proxy pilot closure

MEASURED / INDEPENDENTLY REVIEWED, 2026-09-26. **Stop this fixed intervention.** All eight pairs pass both directional consistency judges, but none reaches the independently frozen minimum activity of 0.5 source-native pixels. The largest norm is **0.4898698162927117**, at ordinal116, from vector (-0.32337512539823055,0.36796870137055643). It remains below the bar; rounding it to0.5 would reverse the decision improperly.

The generated controls passed as described separately in `independent-results.md`. They licensed this proxy observation, not a native bridge. The real result is `FIXED_PILOT_REFUSED`, with `all_eight_admitted=true`, activity=false and eligibility=false. No hook configuration, native render or image-quality admission was emitted.

| Source ordinal, direct from112 | Proposed source-native translation norm |
| --- | --- |
| 108 | 0.297230 |
| 109 | 0.188987 |
| 110 | 0.175182 |
| 111 | 0.170095 |
| 113 | 0.078770 |
| 114 | 0.077478 |
| 115 | 0.291723 |
| 116 | 0.489870 |

These norms were independently calculated from the saved two-component source-native reductions using `sqrt(dx*dx+dy*dy)`. They are not a sharpness ranking or a reason to select only some sources. All eight prescribed sources remain in the decision; anchor112 remains literal zero.

I inspected the actual result, plan, runtime and completed-process receipts. They record all nine TIFF ordinals108–116, original reference244 and the pinned map SHA, exact run2 developer receipt, fresh selected-TIFF content hashes, and sixteen fixed checkpoint calls. All call input-array hashes are unchanged. The runtime still records safe strict loading, float32 execution, twelve updates and the original full checkpoint hash. The process exits0 with clean accounting in8.344s. This includes source staging/model work and is not a controlled speed result. The pre-run review still hashes exactly `77cdb6182705580a51838c73b4bab5913d709b73084a5a6fe61a3de87af33590`.

Consistency is not accuracy: small, spatially smooth, mutually compatible flow estimates may still be wrong, especially for defocus and the CA-off developed proxy. Nor does falling short by0.01013 pixels prove the true displacement is below0.5. The bar was chosen prospectively to avoid building an intervention smaller than the commissioned accuracy criterion. There is no measured uncertainty interval making that narrow gap physically significant; it is a decision rule, and it must remain fixed after seeing this result.

This therefore closes this checkpoint/scale/interior/source interval as an insufficiently active correction. It does not exonerate the existing alignment, reject learned flow generally, or establish that native subpixel errors cannot matter. The AREA/remap/native-consumer gap remains explicit. No threshold change, larger context, extra source interval, native warp or photographic test follows from these receipts.

Root command:

```text
python experiments/marigold-raft-translation/run.py pilot --upstream experiments/marigold-raft-translation/upstream-2 --controls experiments/marigold-raft-translation/controls-1 --out experiments/marigold-raft-translation/pilot-1
```

Pilot receipt SHA256: `32e32b9a589a70d1dd55ddcefbd573b35289aaf11740d172ea977d72e6ee7a2f`. Plan SHA256: `2553803eaa1509cefd40816e066a75fa2a3636da6b9e4c79bc83f3c1124a3b56`. Runtime SHA256: `6051aff18ee1ca2b272159c16466006cc547d6f4aba10452879e65125f73f798`. Checkpoint SHA256: `ff5fadd56d26b40647388883af1547351ea17868b765c05b27231e72dd16a322`.
