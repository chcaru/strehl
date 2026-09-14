# Printer quadratic alignment — independent photographic verdict

**VISUALLY OBSERVED: no demonstrated image-quality improvement.** Baseline and quadratic alignment output look indistinguishable for the specific defects checked in the matched native crops. This is a bounded photographic verdict, not proof of equivalence everywhere or a claim that the changed alignment method is ineffective on other captures.

Both render completion records were available before inspection. I opened all ten native PNGs in `comparison-1` with `view_image`: baseline and candidate versions of junction, letter-edge, fibre, surface, and dark-cavity. `comparison-1/comparison.json` records identical native output origins `(96,64)`, frame-52 reference coordinates, crop rectangles, and the direct 16-bit to 8-bit display conversion. No new RAW files were decoded, and no spatial or colour matching was applied.

The rejection criteria were a broken or doubled edge becoming continuous, two features becoming clearly separable, or retained fine structure becoming visibly more resolved without an accompanying increase in texture in the dark-cavity control. Conversely, loss of those features or extra flat-region texture would reject the candidate. No quantitative sharpness score was used; gradient increases alone could reward noise or manufactured detail. The cavity is a visual low-texture control, not a calibrated noise target or temporal-noise measurement.

| Region | Independent visual finding |
| --- | --- |
| Junction | No clear change in edge separation, doubling, or continuity. Cyan/magenta fringes persist around the bottom bright points. |
| Letter-edge | No clearly resolved additional separation or improvement in the jagged outline. |
| Fibre | The narrow winding strand follows the same visible path; no obvious repaired break or reduced doubling. |
| Surface | Fine ridges and small bright points look substantially unchanged at native display size. |
| Dark cavity | No obvious new texture, and no obvious smoothing that could account for a false sharpness impression elsewhere. |

The image-derived tone parameters changed slightly: black `0.00856 → 0.00858`, white `0.35904 → 0.35776`, contrast unchanged at `0.55`. Consequently, small brightness differences cannot be assigned to recovered detail. This review does not use transform differences or a held-out alignment score as photographic evidence.

**Decision:** retain the quadratic method as an experimental option if its other checks justify that, but do not advertise this printer run as a visible quality gain. The earlier source review remains intact: the permitted middle original was defocused at several regions and did not establish a best-focus reference or fusion-only origin for coloured bright points.
