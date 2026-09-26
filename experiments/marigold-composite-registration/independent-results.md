# Independent composite-registration result

MEASURED / INDEPENDENTLY REVIEWED, 2026-09-26. **Close this fixed constant-translation proposal.** The generated contamination screen passes, but every real source112/152/320 pair fails both directional judges. Activity is true and eligibility is false. No native configuration, render, threshold change, survivor subset or dense-field substitution follows.

The generated test has power and was exercised: local corruption RGB RMS0.015597, maximum0.103668,4.7179% of interior pixels changed by at least0.01, and41.7206% of the interior context remains exactly unchanged. It is not an unidentifiable global duplicate. Both clean directions are admitted with truth errors0.014297/0.234246 native; both contaminated directions are admitted with errors0.026380/0.250953, below the unchanged0.5 bar. This passes by accurate recovery, not refusal or absent corruption. The actual integer-area/channel/constant controls also pass. This single localized corruption does not establish robustness to arbitrary photographic composite defects or commission real noninteger resampling/native CFA gathering.

The real result is different:

| Fixed source | Proposed source-native delta | Norm | Forward/reverse spatial p90 spread | Median closure | Forward/reverse cycle p90 |
| --- | --- | --- | --- | --- | --- |
| 112 | (-1.78333,-3.03381) | 3.51913 | 0.24961 / 1.12837 | 1.00658 | 1.96990 / 1.96441 |
| 152 | (-0.52150,-0.16347) | 0.54653 | 0.70138 / 1.36663 | 0.66759 | 1.61523 / 1.61084 |
| 320 | (-4.63814,-0.12586) | 4.63984 | 14.52815 / 6.28156 | 7.96665 | 14.01030 / 14.21861 |

Spread/cycle limits are0.75 native and median closure0.5. All pairs also fail quadrant consistency; source320 additionally exceeds the strict4-pixel source-translation limit. The relatively smooth forward field at112 is therefore insufficient: its reverse field and cycle disagree. Source152 crossing the minimum activity threshold cannot overrule its failures. Selecting either of those forward estimates alone would discard the checks that actually reject this proposal.

I inspected the actual controls, staging, pilot, runtime and completion receipts. They retain the prescribed three ordinals, corrected Current whole hash, original reference244 map/development bindings, unchanged checkpoint/operator/prior controls and exact four generated plus six real calls. Current is resized directly in its existing cropped gauge, while source transforms alone supply the source mappings; the reverse destination map is identity. The process/source records pass, original RAW reads and native-hook output remain false. Controls and pilot wall readings are6.766s and5.891s, including initialization/staging; these are not controlled algorithm-speed claims.

This refusal concerns reducing the fixed learned fields to one local translation per selected source. It is not a test of every possible dense-flow consumer, nor permission to switch to one after failure. The inconsistency is observable; physical warp truth is not. Defocus, absent shared detail, Current's existing artifacts, preparation differences and model error remain confounded. The CA-on composite versus CA-off individually developed sources particularly prevents treating these vectors as exact CFA-placement corrections. The earlier near-reference activity refusal remains unchanged.

Root commands:

```text
python -I -B -X faulthandler experiments/marigold-composite-registration/run.py controls --out experiments/marigold-composite-registration/controls-1
python -I -B -X faulthandler experiments/marigold-composite-registration/run.py pilot --controls experiments/marigold-composite-registration/controls-1 --out experiments/marigold-composite-registration/pilot-1
```

Controls receipt SHA256: `3564f929695d1e830d73e7e0fc3378b44eccb4dafee5eda1fa9f30111fce9fbb`. Pilot receipt SHA256: `1153c920eaa5ea083c75631746abc47d25b66e6245f4b679088cbf44311a7953`. Checkpoint SHA256: `ff5fadd56d26b40647388883af1547351ea17868b765c05b27231e72dd16a322`. No frozen source was edited for this interpretation.
