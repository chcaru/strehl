# Bug2 transfer baseline frozen before candidate inspection

**VERIFIED — baseline observations only.** The complete 299-frame output was
inspected before choosing ten native384 witnesses. Its 6566 × 4376 JPEG was
displayed at 1920 × 1280 for orientation. A common-display complete RGB16 master,
JPEG and ten exact TIFF/PNG crops were then produced and inspected. No CA-off
photograph or CA-off linear master was read during this phase.

The frozen display uses gain4.993 from the baseline log's exposure suggestion,
clamp0..1, standard sRGB transfer and RGB16 rounding. The same transform must be
used for the candidate, with no separately fitted automatic tone. Native gauge
is the delivered master, offset `(234,156)` in reference-native coordinates.
`frozen-witnesses.json` pins the master, runtime map, executable, source order,
gain and coordinates before any candidate view. `baseline/receipt.json` pins
the common master and every native crop, with original ICC retained.

The reflective orange network is visibly soft/hazy at native scale, with bright
flecks on it. Green surfaces carry fine grain, dark marks and soft bright ovals.
Surface junctions and seams have pale/colored edges and coarse dark contours.
Fine white fibres are visibly present on opposite sides of the field, though
many are soft or have colored/double-looking surrounds. Without source witnesses,
their division between real reflection/iridescence, defocus, occlusion and
reconstruction artifacts is not established.

| Frozen witness | Native origin | Baseline guard |
| --- | --- | --- |
| dark-background | 6180,40 | Nearly black field with fine colored grain and diagonal faint streaks; not a certified flat-noise target. |
| green-fine-texture | 380,720 | Small green/dark surface marks and a chain of soft white flecks. |
| left-green-rim | 100,2970 | Far-left green curved rim, thin colored outline, dark surround and lower white fibres. |
| junction-white-strands | 990,2040 | Pale curled strand at a junction, small glints and broad dark separation. |
| orange-network-upper | 2820,430 | Upper orange branches and nodes; diffuse boundaries and fine underlying texture. |
| orange-network-lower | 1530,3460 | Lower-left orange network and faint internal grain; several isolated colored glints. |
| central-green-orange-rim | 2790,2160 | Bright diagonal edge crossing green material, short strands, cyan/purple surroundings. |
| central-seam | 4250,2970 | Long diagonal dark seam with bright flecks and a thin blue/purple edge. |
| right-reflective-orange | 5560,2560 | Right-side orange branches under a broad pale reflective haze; fine surface texture remains visible. |
| right-outer-fibres | 5960,900 | Far-right fibre web with bright masses, dark gaps and colored surrounds. |

Acceptance requires a complete paired image view and all ten fixed sites under
this common transform. Check opposite field directions, white fibres and color
boundaries, orange-network continuity and fine grain. Removing a genuine color
variation, smoothing the haze/texture, or changing brightness cannot by itself
count as a gain. A visibly narrower edge is not proof of improved placement or
correct color. No new original-source decode is authorized for this phase.

Executed command, exit0:

```powershell
python -B -X faulthandler experiments/raw-quality-2026-10-26/photo-review/bug2-transfer/prepare-display.py baseline
```
