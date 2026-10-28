# Complete weevil B4: no substantial gain over B8

**VERIFIED visual observation:** reducing Helicon B radius8→4, with smoothing4 fixed, does not produce a substantial improvement on this complete299-frame weevil. Some fine texture and points look slightly firmer, but no decisive new hair, scale gap or contour is established. Rounded scales, soft thorax features, bright glints and pale wing/occlusion rims persist. No conspicuous new widespread background traces or major B4 regression is established in the frozen witnesses either. Retain both comparisons; neither is a SOTA result or a native improvement.

The reviewer viewed native CA-off, B8 and B4 complete JPEGs first, then all ten frozen native384 witnesses for all three arms. Root independently reviewed the same complete outputs and30 witnesses. No additional crop search, retone or optimization followed the result.

| Complete workflow | Full JPEG | Full-resolution RGB16 master |
| --- | --- | --- |
| Native CA-off,6896x4596 | [Complete photograph](../../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-26/weevil-107-ca-off/stack-master.tiff) |
| Helicon B8/S4,7020x4676 | [Complete photograph](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-26/weevil-107-comparator/b/stack-master.tiff) |
| Helicon B4/S4,7020x4676 | [Complete photograph](../../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-full.jpg) | [Master](../../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/stack-master.tiff) |

## All ten retained witnesses

Coordinates are top-left native pixels in the respective delivered master; each rectangle is384x384. Exact PNG/TIFF pairs are retained under `native-ca-off/`, `b8/` and `b4/` and bound in the [crop receipt](crop-export-receipt.json).

| Witness | Native / B8 / B4 origins | Observation |
| --- | --- | --- |
| Background black |3800,500 /3865,495 /3866,495 | All remain visually dark at the fixed display. Sparse native specks persist; B4 shows no conspicuous new long trace relative to B8. This is not a calibrated noise measurement. |
| Dark elytron |2750,2120 /2795,2147 /2795,2147 | B4 slightly emphasizes fine surface texture; no clearly new structure. Dark grooves and rounded glint-bearing scales remain similar. |
| Turquoise scales |2120,1340 /2152,1352 /2152,1353 | The same rounded scale field and dark gaps persist. B4 does not restore distinct finer contours missing from B8. |
| Elytron seam |2950,1960 /2998,1984 /2998,1984 | Broad diagonal seam and nearby depths remain. Glints and soft edges persist; no convincing seam cleanup. |
| Bright wing rim |4050,1810 /4118,1831 /4118,1831 | The long pale lower contour and bright scattered glints remain. B4 is very close to B8; no broad halo removal or meaningful glare reduction. |
| Thorax texture |4520,2560 /4597,2596 /4598,2596 | Slight local firmness does not resolve the rounded spot-like features into additional genuine shapes. All three remain soft here. |
| Upper-leg hairs |1820,640 /1845,638 /1845,638 | Both B arms give some lower hairs more contrast/separation than native, with workflow/scale caveats. B4 adds no decisive extra strand or consistently cleaner continuity over B8; curled upper contours and soft material remain. |
| Blue joint |2680,850 /2722,853 /2722,853 | Blue surface texture, irregular dark features and the pale green lower junction remain. B4 does not fix the soft junction or bright color/glint fringe. |
| Upper occlusion |3850,1300 /3915,1312 /3915,1311 | Persistent pale/green contour around the blue limb and bright point near its foot. Small highlight changes do not remove the extended contour. |
| Eye and antenna region |5350,2920 /5447,2964 /5448,2964 | Similar bright structures above/below the dark gap; fine scattered points and glints remain. No decisive new depth structure or edge cleanup. |

## Mapping and workflow limits

**VERIFIED:** [mapped-witnesses.json](mapped-witnesses.json) was saved after the three complete views and before any new crop export. The exact retained SIFT locator was reused, with fixed seed/thresholds and its100px wrong-translation control. B8 and B4 were independently located against the current CA-off native master; old artifacts were not edited. Similarity scales are1.019849 and1.019979, with local inlier-median translations used only to locate centers. Native crop pixels were never warped or resized. These fits are not measurements of pipeline placement accuracy, equal physical footprint or resolved detail. The background has no nearby feature inliers, so its location relies on the global locator.

Native retains reference149 crop active-origin(68,46), its original CA-off RGB16 and automatic tone. B8/B4 consume exactly the same299 predeveloped native TIFFs with fixed WB/tone; radius is their only intended processing-setting change. Native develops after RAW reconstruction, while the vendor develops before alignment/fusion; the native original tone is not replaced by the earlier manual common-gain display. Therefore B4 versus B8 isolates the setting comparison more cleanly than either vendor versus native. No merger-only or new-resolution claim follows from brighter glints or apparent contrast.

**VERIFIED export:** `python -B -X faulthandler experiments/raw-quality-2026-10-27/weevil-fine-comparator/photo-review/export-corresponding.py --whole-images-reviewed` exited0; helper time4.813s. All30 lossless RGB16 crops and PNG `(value+128)//257` readbacks are exact, ICC is unchanged, all input hashes/metadata are unchanged, and RAW reads are0. Original complete images/masters remain linked rather than being retouched for comparison.

**MEASURED operationally / receipt reviewed:** the [B4 completion](../../../../outputs/raw-quality-2026-10-27/weevil-107-fine-comparator/b-r4-desktop-2/completion.json) records all299 unchanged inputs and the fresh methodB/radius4/smoothing4 output. Master SHA256 is `d24e944825fe5e8405dbf26a7339e7d69af4f70dea6607db1af81ea809a274ff`. Root's application audit accounts for598 forward/reverse source rows. Vendor child45.344s and wrapper117.485s exclude the prior TIFF-development cost from a fresh RAW workflow; they are not a clean competitive speed ranking. The earlier preflight refusal is preserved and supplied no photograph. Missing `saved-outputs.txt` remains disclosed in the successful receipt.

The proposed next source-support observation is separate: fixed complete developed-source indices0,74,149,224,298, followed by at most two whole-view nominees and the existing scale/thorax/hair witnesses. It requires root allocation. A negative five-source sample cannot establish an optical ceiling or an oracle best source. No new source reading was performed for this report.
