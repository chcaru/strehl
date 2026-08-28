# V-MOTE: adjudicating the dust-mote dispute

Status: complete. Agent: V-MOTE, an independent third party to the disagreement
between BUILD-DEFECT and the DELIVER-V5 dust arm. Neither disputant can
adjudicate itself, which is why this lane exists.

Subject: sensor dust "mote 2", the defect that ships visibly in the delivered
masters, and the three coordinate pairs in circulation for it: `(3434, 2305)`,
`(7008, 4450)` and `6776_4322`.

I edited nothing under `crates/`. This report and `experiments/V-MOTE/` are the
only files I wrote. `D:\personal\macro\` was read only. Scratch went to
`C:\dev\strehl-out\V-MOTE\` and has since been purged to a 1.68 MB exhibit.

Every claim below is labelled **MEASURED** (I ran a command and read its
output), **DERIVED** (arithmetic on measured quantities), or **ARGUED**
(reasoning that no single command settles).

## 0. Bottom line

**The 17x disagreement does not exist.** The two lanes agree to 0.6 percentage
points on the subject in dispute. The advertised contradiction compares a
minimum-over-search statistic on one subject against a fixed-point statistic on
a different subject, and neither of the two lanes measured the mote.

**One of the three coordinates is not a coordinate.** `6776_4322` is the clamped
top-left origin of a 256 px crop.

**The mote is at CFA quad `(3434, 2305)`**, photosite `(6868, 4610)`, and its
true depth is **-2.94% +/- 0.06%** on the flats, **-3.4% to -5.7%** on delivered
masters.

**`STREHL_DEFECT=on` is safe to make the default**, and the reason is not the
doc comment, it is a render: a map handed deliberately wrong coordinates
produced a file byte-identical to the corrector-off arm.

**The doc comment above `defect_request_from_env` in
`crates/strehl-cli/src/stack.rs` (approx. lines 822-834) is wrong in three
places**, and it is the stated reason the corrector ships off.

## 1. Provenance: one pinned build, because absolutes here are timestamps

Roughly 16 lanes edit this crate concurrently. Source was copied to
`C:\dev\strehl-src-vmote` at `2026-08-28T01:42:54-07:00`, built with a private
`--target-dir C:\dev\strehl-tgt-vmote`, and the executables copied aside.

```
PS> Get-FileHash C:\dev\strehl-pin-vmote\*.exe -Algorithm SHA256
A23969DA3FD80A4EF92F5C178C00DD227B08F3CD790D36AD019A8C07167482BC  defect-cpl-split.exe
761CD006E3BFAF47DB2FBB3F90E159BA2062A056A0A5A718F9E4A8DA85328309  defect-flat-census.exe
0F4ACD7E2D592FE3F8980BA6077100BCBF253879CE53A42F0AC81EFFFA3CFCDA  strehl.exe

PS> git --no-pager log -1 --format='%H %ci %s' c9f557f6
c9f557f61e6fb315dc11c8049e1c5891144dd3a7 2026-08-28 01:41:50 -0700 V-ENVSURF: ledger of all 46 STREHL_* env vars on the shipping pyramid path
```

At copy time `crates/strehl-cli/src/merge_cmd.rs` was dirty in the shared tree
from another lane. HEAD had moved to `952115c4` by the time I finished.
**MEASURED.** Every number in this report comes from `0F4ACD7E...FCDA` or its
two example binaries. No arm of any comparison crosses builds.

## 2. Part 1 — the three coordinates reconcile to two, and one is not a coordinate

### 2.1 What each one actually is

| pair | space | status | transform to the others |
| --- | --- | --- | --- |
| `(3434, 2305)` | CFA quad, active-area origin `(0,0)`, pre-warp | **CORRECT** | times 2 gives photosite `(6868, 4610)` |
| `(7008, 4450)` | rendered-master pixels | **WRONG**, empty background | the mote in master space is at roughly `(6879, 4617)` on `flower-bud-alone-cpl` |
| `6776_4322` | **not a coordinate** | a clamped crop origin | add back the logged `disc@(232,128)` to recover `(7008, 4450)` |

### 2.2 How `6776_4322` was established as a crop origin — MEASURED

`experiments/DELIVER-V5/dust_patch.py` sets `CX, CY = 7008, 4450` and
`PATCH = 256`, then computes `x0 = max(0, min(w-PATCH, CX-PATCH//2))`. Its
output filename is `sensor-dust_mote2_%d_%d_NOT-REPRODUCED.png % (x0, y0)`.
Running that clamp:

```
w=7032  CX,CY=7008,4450  PATCH=256 -> x0=6776 y0=4322  disc@(232,128)
w=7040  CX,CY=7008,4450  PATCH=256 -> x0=6784 y0=4322  disc@(224,128)
```

`experiments/DELIVER-V5/logs/dust-patch.txt` records `disc@(232,128)` and both
filenames. `6776 + 232 = 7008` and `4322 + 128 = 4450`. **The log carries two
different values of this "coordinate", 6776 and 6784, because the corpus has two
frame widths. No physical mote can have two x coordinates in one body.**
**MEASURED**, then **DERIVED**.

### 2.3 Why quad `(3434, 2305)` is the correct space — MEASURED

`crates/strehl-core/src/defect_map.rs` line 321 documents `DustQuad::px` as
"Quad column, i.e. sensor column `2 * px`", and `quad_mean` (approx. line 2246)
indexes `photosite = ax + 2*qx`. The embedded map header declares its space:

```
strehl-defect-map 2
camera ILCE-7CM2
sensor 7032 4688
covered 7028 4688
coords active
aperture 5.6
```

My own flat-field centroid lands at quad `(3432.7, 2305.3)`, so the stored map
coordinate is 1.3 quads off in x and 0.3 in y. **MEASURED.**

### 2.4 The "opposite signs" that supposedly ruled out a translation

The stack.rs doc comment observes that `3434*2 = 6868` is 140 short of 7008
while `2305*2 = 4610` is 160 past 4450, and argues the opposite signs rule out a
pure origin translation. They do. **They are the per-stack alignment warp**,
which I measured per subject as `(+10,+10)`, `(+15,-5)`, `(+25,+15)`,
`(+70,+55)`, `(+70,+50)`, `(+5,+15)`, `(+10,-25)`. On `flower-bud-alone-cpl` the
A/B difference clusters localise the warp directly at `(+11,+7)` for mote 2 and
`(+9,-7)` for mote 1. **MEASURED**, then **ARGUED** that warp is the mechanism.

## 3. Part 2 — the depth, measured independently on the flats

I reused `crates/strehl-cli/examples/defect-flat-census.rs` rather than writing
a census from scratch, per the brief: its frame selection
(`EXPOSURE_WINDOW (0.06, 0.90)`, per-frame median normalisation,
`BLOCK2_FIRST = DSC00263`) and its `quad_mean`. I replaced its truncated box-64
high-pass with a quadratic fitted to an annulus, because the box is truncated at
the frame edge where this mote lives.

### 3.1 Annulus sweep on the real site — MEASURED

```
annulus 25- 37 quads  -2.390%     annulus 55- 90  -2.936%
annulus 30- 45        -2.982%     annulus 60-110  -2.999%
annulus 40- 60        -2.878%     annulus 90-140  -3.044%
annulus 45- 80        -2.945%     annulus100-170  -2.910%
```

### 3.2 Where the +/- 0.06% comes from — DERIVED

The quoted uncertainty is the **spread of the estimator across its own free
parameter**, not a photon-noise standard error. Excluding the 25-37 annulus,
which arm A4 shows is invalid for this feature size, the seven remaining
annuli span **-2.878% to -3.044%**, a half-range of 0.083% about a midpoint of
-2.961%. The two independent data splits agree far more tightly than that:
odd versus even frames read **-2.946 / -2.944** and capture block 1 versus
block 2 read **-2.937 / -2.952**. I quote **-2.94% +/- 0.06%** as the
root-mean-square of the annulus spread and the split disagreement, which is the
dominant term. **DERIVED from MEASURED inputs.**

### 3.3 Commissioning arms — MEASURED

- **A0 CLEAN**, 240 edge-matched control sites: mean `+0.014%` sd `0.039`
  (annulus 25-37); mean `+0.024%` sd `0.052` (annulus 45-80); max deviation
  `0.20%`. **The frame edge does not fabricate a mote.** This was the named
  failure mode and it is retired.
- **A4 WIDE PLANT**: the 25-37 annulus fails for planted features of radius
  greater than or equal to 35 quads, inverting sign to `+4.433%` on a -4%
  radius-35 plant. This is why the 25-37 row above reads shallow and is
  excluded.
- Radial profile: median `-3.0%` to `-3.2%` for r under 15 quads, `-0.58%` at
  r 20-25, `-0.12%` beyond r 30.
- Equivalent radius 20.3 quads, that is **41 photosites, about 81 px across**.

### 3.4 CPL split — MEASURED

Dust on the sensor stack cannot know whether a polariser is fitted, so a
candidate present in only one block is not sensor dust.
`defect-cpl-split.exe` from my pinned build:

```
mote 2: block1 -3.480%  block2 -3.486%  DELTA -0.006 pp  p 0.4487 -> Common
        edge-matched null bounds any filter-borne share at <= 1.50%
```

All four commissioning arms G0 to G3 PASS. **Against my own supporting
evidence**: arm `C1`, which tests which block wears the CPL, **FAILED**. The
per-step level ratio ranges 4.593x to 1.050x, a spread of 2.130 stops, more
consistent with cloud drift than a fixed filter transmission. **The block labels
are therefore unverified and this is a valid reproducibility split but a weaker
filter test than its docstring claims.**

## 4. Part 3 — the mechanism of the 17x, and it is not a disagreement about a mote

### 4.1 The two lanes agree — MEASURED

`experiments/DELIVER-V5/logs/dust-patch.txt` line 18 reads
`highly-angled-ruler-mm-cpl` at **-13.88%**. That is the same subject the other
lane read at **-13.28%**, at the same point `(7008, 4450)`. **Agreement to 0.6
percentage points.** The advertised 17x compares that -13.28% against
DELIVER-V5's **-0.78%**, which was measured on `pencil-flatter-angle-cpl`, a
**different subject**.

### 4.2 The -13.28% is a search artifact — MEASURED

It is the **minimum over a plus-or-minus 170 px search** on a texture-saturated
ruler surface. `ARM S` runs the identical search at 20 edge-matched control
anchors in the same master:

```
mean -16.14%  median -8.03%  min -60.16%  max -5.16%
=> the site is -0.11 sd of that null, rank 4 of 21
local annulus roughness there is 4.23%; a -13.9% read is about 3.3 sd of it
```

`11-MARKED-master-highly-angled-ruler-mm-cpl.png` showed the search coordinate
sitting on a **dark shadowed groove in the ruler**. Scene content, not dust.

### 4.3 The -0.78% is a fixed point 215 px from the mote — MEASURED

`ARM L`, a plus-or-minus 70 px search against a fixed-point edge-matched null:

```
pencil-flatter-angle-cpl : DELIVER-V5 read -0.78%; mote at (6938,4665) at -3.41%, -15.74 sd (null sd 0.22%)
pencil-steep-angle-cpl   : DELIVER-V5 read -0.26%; mote at (6938,4660) at -5.66%, -20.14 sd
```

Running DELIVER-V5's own statistic at BUILD-DEFECT's coordinate instead shows
the mote plainly: `109MSDCF -3.44%`, `flower-bud-alone-cpl -3.02%`,
`couch-fibers-cpl -3.41%`, `119MSDCF -1.69%`, `bee-1-cpl -1.07%`.

DELIVER-V5 also **excluded `highly-angled-ruler-mm-cpl` from its adjudication
set** because its background sd of 11.5 exceeded its 8 DN flatness bar, so its
"worst of 14 flat-and-bright masters" never saw its own -13.88% row.

`ARM E`, a fast-versus-slow equality assertion on the estimator, returned delta
`0.00e+00` on every one of the 14 subjects. The statistic is not the problem.

### 4.4 The verdict on the dispute — ARGUED from the above

**Neither number is wrong and neither lane measured the mote.** A
minimum-over-six-hundred-samples statistic and a single fixed-point statistic
are not comparable quantities; quoting a ratio between them manufactures a
contradiction out of two correct measurements. The `NOT-REPRODUCED` verdict is
**correct about `(7008, 4450)` and wrong about the mote**.

## 5. Part 4 — the A/B render, the knob, and the guards

### 5.1 The knob is live, not another silently-ignored env var — MEASURED

```
PS> foreach($v in @('banana','1','ON','On','off','on')){ $env:STREHL_DEFECT=$v; strehl stack D:\personal\macro\119MSDCF --limit 2 ... }
"banana" rc=1  Error: STREHL_DEFECT="banana" is not a setting; it is "on" or "off". Refusing rather than assuming, because a misspelled "on" that silently means "off" leaves an image uncorrected while the caller believes it was corrected
"1"      rc=1  (same error form)
"ON"     rc=1  (same error form)
"On"     rc=1  (same error form)
"off"    rc=0  defect map      : off (STREHL_DEFECT=off)
"on"     rc=0  defect map      : 0 hot, 652 dust quads, arms dust (floor 8.0 e-, gain 0.22894 DN/e-)
```

It validates its input and rejects even the capitalised spelling of a valid
value, which distinguishes it from the env vars on this path that accept
garbage at rc 0. An exit code is not a measurement of the knob you set; the
matched control in 5.2 is.

### 5.2 The A/B render — MEASURED

One pinned exe `0F4ACD7E...FCDA`, subject `flower-bud-alone-cpl`, **205 frames**,
`--srgb`, separate cache directories per arm.

`STREHL_DEFECT=on` banner:

```
--- defect self-validation (MEASURED) ---
sites           : 2/2 sites confirmed from 8 frames (not significant 0, too shallow 0, not stationary 0, unmeasurable 0)
site ( 3202,  119): depth -3.963% (map -3.606%), p 0.0025, present 1.00 -> CORRECT at scale 1.101
site ( 3434, 2305): depth -9.432% (map -8.236%), p 0.0025, present 1.00 -> CORRECT at scale 1.153
defect map      : 0 hot, 1135 dust quads, arms dust (floor 8.0 e-, gain 0.22894 DN/e-)
dust            : examined 232675, corrected 232675, clipped 0, outside 0, no change 0
samples changed : 930700 over 205 frame loads (4540.0 per frame)
```

Default arm banner: `defect map      : off (STREHL_DEFECT=off)`.

```
B649F0BCE653569A345DAAD5E518773DD4B5F838FF6E41C83D309535141701B3  flower-bud-alone-cpl_OFF.tiff
1451B7B545E58F0C88F3092966AE1FDD585FE9A91579B168E4F37543EBF4C743  flower-bud-alone-cpl_ON.tiff
B649F0BCE653569A345DAAD5E518773DD4B5F838FF6E41C83D309535141701B3  flower-bud-alone-cpl_WRONGMAP.tiff
```

Whole-image difference OFF versus ON: **915,135 of 99,010,560 samples differ
(0.9243%), max absolute delta 4744 DN16.**

### 5.3 Depth at the site, same statistic, both arms — MEASURED

| site | OFF | ON |
| --- | --- | --- |
| BUILD-DEFECT `(6868,4610)` | **-3.717%** | **+0.033%** |
| mote centre `(6878,4620)` | **-4.644%** | **+0.019%** |
| the other lane `(7008,4450)` | -0.051% | -0.046% |

The third row is the control that settles the location question: the disputed
coordinate does not move when the mote is corrected, because there is nothing
there.

### 5.4 Residual after correction — MEASURED

Radial profile about `(6878,4620)`, background a quadratic on 180 to 320 px:

```
   r(px)      OFF%       ON%
     0- 10    -4.358    +0.080
    10- 20    -4.196    +0.178
    20- 30    -1.219    +0.093
    30- 40    +0.328    +0.256
    40- 50    +0.187    +0.194
```

Worst 10 px annulus after correction is `0.256%` against a surrounding
background that itself reads `+0.13%` to `+0.19%`. Net over-correction is about
`+0.06` to `+0.12` percentage points, **roughly 40x smaller than the mote it
replaced**. A faint ring outline is visible at aggressive stretch at the 0.1 to
0.25% level.

### 5.5 Where the difference actually lands — MEASURED

```
ring r(px)           n px  n changed frac changed    max |d|
0-50                 7825       7825    100.0000%       4744
50-100              20258      20258    100.0000%         95
100-200             55770      55654     99.7920%         19
200-400            142357     121983     85.6881%          7
400-800            469566     126895     27.0239%          1
800-1600          1691611       7068      0.4178%          1
1600-3200         6398474          0      0.0000%          0
3200-99999       24217659     111588      0.4608%       1761
changed-pixel |d| percentiles: p50 1  p90 6  p99 543  p99.9 2719  max 4744

pixels with |d|>100 DN16 : 6836
cluster A (upper, y<2000)  n=  2861  bbox x 6379..6444  y  201.. 263  centroid (6413,  231)
cluster B (lower, y>=2000) n=  3975  bbox x 6832..6916  y 4571..4655  centroid (6879, 4617)
map site 1 quad (3202, 119) -> photosite (6404,  238)
map site 2 quad (3434,2305) -> photosite (6868, 4610)
pixels with 0<|d|<=2 DN16 : 335734   bbox x 5555..7039 y 0..4687  (1.0173% of frame, <= 0.003% full scale)
```

The material change is confined to two discs of 65 by 63 px and 85 by 85 px,
centred within 11 px of the two map sites. The alarming-looking bounding box
`x 5555..7039, y 0..4687` is **entirely the 2 DN16 or smaller halo**, under
0.003% of full scale. **MEASURED.** That the halo is Laplacian-pyramid band
spread is **ARGUED**, not proven.

### 5.6 The guards, verified by execution rather than by doc comment

**`check_geometry` refuses a map that does not belong to the body — MEASURED.**
`MAX_ACTIVE_MISMATCH_FRAC` is `0.01`, confirmed by case-sensitive grep. A
sidecar declaring `sensor 9560 6376`:

```
Error: the defect map does not belong to D:\personal\macro\119MSDCF\DSC00024.ARW; set STREHL_DEFECT=off to render without it
Caused by:
    defect map was measured on a 9560x6376 active area but is being applied to a 7032x4688 one, a 26.5% difference; the tolerated difference is 1.0%. A sensor-coordinate map applied to a different READOUT MODE indexes different photosites, because the crop moves where (0, 0) sits on the sensor
EXIT=1
```

A sidecar with out-of-range records is refused earlier still, at load:
`defect map dust record at (3202, 106) is outside the 2320x1548 area the map declares it measured`, EXIT=1.

**`SiteValidator` reduces a wrong coordinate to nothing — MEASURED.** This is
the arm that answers the brief's third question. I relocated **both** motes,
483 plus 652 quads, 1000 quads into clean silicon and ran the full 205-frame
render:

```
sites           : 0/2 sites confirmed from 8 frames (not significant 2, too shallow 0, not stationary 0, unmeasurable 0)
site ( 2202, 1119): depth  -4.651% (map -3.606%), p 0.4239, present 0.75 -> skip: not significant here
site ( 2434, 1305): depth -18.661% (map -8.236%), p 0.1796, present 0.88 -> skip: not significant here
defect map      : nothing confirmed in these frames; correcting nothing
EXIT=0 elapsed=00:02:43.9430167
```

Note that the naive depth statistic reported **-18.661%** at a fabricated site.
The gate refused it on **stationarity across frames**, `p 0.1796` against a bar
of `0.0025`, not on depth. The output was byte-identical to the corrector-off
arm.

The gate also bites on real data: on `119MSDCF --limit 2` it confirmed 1 of 2,
skipping mote 1 at `p 0.0324`, and the map shrank from 1135 to **652** quads.
On the flats the validator reads `-3.235%` where plain division reads `-3.483%`,
a ratio of 0.93, so it does not over-read; it returns `NotSignificant` at
`p 0.0150` there and would skip, which is the conservative direction.

## 6. What the byte-identity result does and does not prove

This distinction matters and must not blur. **ARGUED**, from the measurements in
5.2 and 5.6.

**It proves:** handing the corrector a map whose coordinates are wrong cannot
damage a good render. The empirical presence gate is a real bound on the damage
from a disputed coordinate, not a claim in a doc comment. Enabling the
correction is therefore not a gamble on the coordinate being right.

**It does NOT prove that the corrector does anything useful.** A map that
changes nothing is also a map whose effect nothing has demonstrated; a
do-nothing implementation would pass that arm identically. The evidence that the
corrector *works* is a different measurement entirely: section 5.3, where the
mote moves from **-4.644% to +0.019%** at its centre, and section 5.4, where the
residual is about 40x smaller than the feature removed. The two arms are
independent and **both** are required. Byte-identity bounds the downside;
the A/B pair demonstrates the upside. Neither substitutes for the other.

A further limit on the byte-identity arm: it was run on **one subject**. It
shows the gate refusing two fabricated sites on `flower-bud-alone-cpl`. It does
not establish the gate's false-positive rate across the corpus.

## 7. Facts proposed for the fold

Numbered locally per rule 28. The orchestrator allocates absolute numbers; I did
not edit the synthesis.

| # | Class | Fact |
| --- | --- | --- |
| F1 | CORRECTED | The 17x dust disagreement does not exist. The DELIVER-V5 log reads `highly-angled-ruler-mm-cpl` at **-13.88%**, the same subject the other lane read at **-13.28%**, at the same point. The advertised ratio compares that against -0.78% measured on a **different** subject. A minimum-over-search statistic and a fixed-point statistic are not comparable quantities. |
| F2 | CORRECTED | `6776_4322` is not a coordinate. It is the clamped top-left origin of a 256 px crop, `max(0, min(w-256, 7008-128))`, and the log carries **6776 and 6784** for the corpus's two frame widths. A filename is not a measurement. |
| F3 | MEASURED | Mote 2 is at CFA quad `(3434, 2305)`, photosite `(6868, 4610)`; the measured flat-field centroid is quad `(3432.7, 2305.3)`, 1.3 quads away. `(7008, 4450)` is a rendered-master point about 215 px from the mote that reads -0.051% with the corrector off and -0.046% with it on. |
| F4 | MEASURED | Mote 2 is **-2.94% +/- 0.06%** on the flats and **-3.4% to -5.7%** on delivered masters, diameter about 81 px. A 240-site edge-matched control null reads mean +0.014% sd 0.039, retiring the fear that the frame edge fabricates a mote. It is common to both CPL blocks, delta -0.006 pp at p 0.4487, bounding any filter-borne share at 1.50%. |
| F5 | CORRECTED | The map's stored depth for mote 2, -8.236%, is **2.8x** the measured truth. Harmless as shipped because the validator refits amplitude from the frames, `CORRECT at scale 1.153`, but it must never be quoted as an attenuation. |
| F6 | CORRECTED | The shipping flat census's box-64 background over-reads this mote by about **0.54 pp** because the box is truncated 38 quads from the frame edge. The edge does not create a defect but it does bias a real one deep. |
| F7 | MEASURED | The self-validation gate reduces a wrong coordinate to **zero bytes**. Both map sites relocated 1000 quads, full 205-frame render: the naive statistic read -18.661%, the stationarity gate refused at p 0.1796 against a bar of 0.0025, and the output was byte-identical to the corrector-off arm, SHA256 `B649F0BC...01B3`. `check_geometry` independently hard-errors at rc 1 on a 26.5% geometry mismatch against a 1.0% bar. |
| F8 | ARGUED | Byte-identity under a wrong map bounds the **downside** of enabling a corrector; it says nothing about the **upside**, because a do-nothing implementation passes it identically. The two must be measured separately and both were. |
| F9 | MEASURED | `STREHL_DEFECT` is a live knob and a validating one: 915,135 of 99,010,560 samples differ between arms with max delta 4744 DN16, and it hard-errors at rc 1 on `banana`, `1`, `ON` and `On`, rejecting even the capitalised spelling of a valid value. |
| F10 | MEASURED | Enabling the corrector changes material pixels only inside two discs of 65 by 63 and 85 by 85 px centred within 11 px of the two map sites. The remaining 1.02% of the frame moves by 2 DN16 or less, under 0.003% of full scale. |
| F11 | CORRECTED | The claim that nothing at or above 1 percent reaches the delivered masters is false. The delivered `flower-bud-alone-cpl` carries the mote at **-3.717%** at the map coordinate and **-4.644%** at its centre. |
| F12 | CORRECTED | The doc comment above `defect_request_from_env` in `crates/strehl-cli/src/stack.rs` is wrong in three places, and it is the stated reason the corrector ships off: the lanes do not disagree by 17x, the three coordinate pairs do reconcile, and the location is not disputed. |
| F13 | MEASURED | Against my own supporting evidence: the CPL split's arm `C1`, which identifies which block wears the polariser, **failed**. The per-step level ratio ranges 4.593x to 1.050x, a 2.130-stop spread, more consistent with cloud drift than a fixed filter transmission. The split remains a valid reproducibility partition but is a weaker filter test than its docstring claims. |

## 8. Verified versus assumed

Every claim in this report is partitioned. Nothing is here because it looks
right.

### 8.1 Verified — I ran a command and read its output

- The pinned executables' SHA256 values and the commit they were built from.
- The clamp arithmetic producing `6776` and `6784`, and the `disc@(232,128)`
  offset that recovers `(7008, 4450)` from it.
- The DELIVER-V5 log line reading `highly-angled-ruler-mm-cpl` at -13.88%.
- The quad-to-photosite mapping in `quad_mean` and the `DustQuad::px` doc.
- The flat-field depth, the annulus sweep, the 240-site control null, the
  odd/even and block1/block2 splits, the radial profile, the centroid.
- The CPL commonality result and all four G-arms passing.
- `ARM E` fast-versus-slow estimator equality, delta `0.00e+00` on 14 subjects.
- `ARM S` and `ARM L` nulls on all 14 admissible subjects.
- `STREHL_DEFECT` liveness, the sample-difference count, and the four rejected
  input values.
- The A/B render banners, the three file hashes, the per-site depths, the
  residual profile, and the difference localisation.
- `check_geometry` refusal at rc 1, and the load-time out-of-range refusal.
- The wrong-map render producing a byte-identical file.
- Run-to-run determinism of the pinned exe: the OFF and WRONGMAP arms were two
  separate 2m44s runs with separate cache directories and produced identical
  SHA256 values.
- `corpus_lint` clean before every commit I made.

### 8.2 Assumed, or measured but not by me

- **Whether the render cache key includes the defect setting.** I sidestepped it
  with separate cache directories and never tested it. If the key does not
  include `STREHL_DEFECT`, a warm shared cache could serve a stale result across
  a toggle. **This should be checked before default-on ships.** NOT VERIFIED.
- **BUILD-DEFECT's corpus sweep tally** of 26 examined, 17 corrected, 9 skipped,
  0 failed. I verified the *mechanism* on two subjects. I did not replicate the
  sweep. NOT VERIFIED.
- **Which capture block wears the CPL.** Arm C1 failed, see F13. NOT VERIFIED.
- **That the 2 DN16 halo is Laplacian-pyramid band spread.** The halo is
  localised and bounded by measurement; the causal explanation is ARGUED.
- **`ARM L`'s search boundary.** The plus-or-minus 70 px window was hit on
  `lead-1-cpl`, `pencil-steep-angle-cpl` and others, at offsets `(+70,+55)`,
  `(+70,+50)`, `(-70,-5)`, so the true warp displacement on those subjects may
  exceed 70 px and my per-subject mote locations there are lower bounds on the
  displacement.
- **Mote 1.** Its map coordinate `(3202, 119)` is about 22 quads from its
  flat-derived blob at `(3201, 141)` and it reads only -0.74% to -0.91% on the
  flats. It corrects at scale 1.101 and is bounded by the same gate, so it is
  not a blocker, but the coordinate is loose and this remains an open question
  belonging to BUILD-DEFECT.
- **Generality of the byte-identity arm.** One subject. It does not establish the
  gate's false-positive rate across the corpus. See section 6.
- **`flower-bud-with-background-fern-cpl`** shows the mote at only -0.34%,
  -0.10 sd. The defect does not reach every master, so default-on is not
  uniformly beneficial, merely never harmful within what I measured.

## 9. Recommendation

**Yes. Switch `STREHL_DEFECT=on` by default.** ARGUED, from F4, F7, F9, F10 and
F11.

The evidence: the defect is real, it is on the sensor, and it reaches the
delivered masters at -3.4% to -5.7% on flat, bright subjects, which is plainly
visible at print size and is fixed in sensor coordinates so it lands in the same
place every time. Correction removes it to within about 0.1 percentage point.
The blast radius is two small discs. A wrong coordinate costs exactly zero
bytes, and a foreign body is a hard error rather than a silent mis-correction.

Carry these caveats with the change:

1. The amplitude is refit from the frames, not read from the map. That is
   already the design and it is why the map's 2.8x-too-deep stored value is not
   dangerous. Do not "fix" the map's depth by making the corrector trust it.
2. Mote 1's coordinate is loose, see 8.2.
3. Check the cache key first, see 8.2.
4. The doc comment that currently justifies the default must be replaced, not
   merely edited around, because all three of its factual claims are wrong.

## 10. Reproduction

Everything in this report regenerates from the owner's read-only source captures
plus a rebuild. No deleted artifact is load-bearing.

**Build.** Rebuild commit `c9f557f6` into a private target directory. Do not use
the shared one and do not run `cargo clean`.

```
git worktree or source copy at c9f557f61e6fb315dc11c8049e1c5891144dd3a7
cargo build --release --target-dir <private>
cargo build --release --target-dir <private> --example defect-flat-census
cargo build --release --target-dir <private> --example defect-cpl-split
```

**The A/B pair**, about 2m44s per arm:

```
$env:STREHL_CACHE_DIR='<scratch>\cache-off'
Remove-Item Env:\STREHL_DEFECT -ErrorAction SilentlyContinue
strehl stack D:\personal\macro\flower-bud-alone-cpl -o <out>\flower-bud-alone-cpl_OFF.tiff --srgb

$env:STREHL_CACHE_DIR='<scratch>\cache-on'
$env:STREHL_DEFECT='on'
strehl stack D:\personal\macro\flower-bud-alone-cpl -o <out>\flower-bud-alone-cpl_ON.tiff --srgb
```

Separate `STREHL_CACHE_DIR` per arm is deliberate, because I did not verify that
the cache key includes the defect setting. Expected: 205 frames, OFF hashes
`B649F0BC...01B3`, ON hashes `1451B7B5...C743`.

**The wrong-map arm.** Copy `crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt`
to scratch, translate every `d <x> <y> <gain>` record with `y > 2000` by
`(-1000, -1000)` and the rest by `(-1000, +1000)`, point `STREHL_DEFECT_MAP` at
it with `STREHL_DEFECT=on`, and render. Expected: `0/2 sites confirmed` and a
file byte-identical to the OFF arm.

**The scripts.** `experiments/V-MOTE/` holds nine scripts, committed at
`5a18f2f131d8375e499a0479d71fb409ea48f3d0`, each with a docstring naming its
inputs:

| script | what it does |
| --- | --- |
| `vm_accum.py` | accumulates flat-field quad means from the 360 ARWs into npy caches, reusing the census's frame selection |
| `vm_depth.py` | the first-principles depth statistic and commissioning arms A0 CLEAN, A1 PLANT-, A2 PLANT+, A3 DIVIDE |
| `vm_profile.py` | radial profile, arm A4 WIDE PLANT, and the annulus sweep |
| `vm_crops.py` | 1:1 crops of the flats and the delivered masters |
| `vm_master.py` | three statistics over all 26 masters, including DELIVER-V5's transcribed one |
| `vm_verdict.py` | ARM S search-bias null, ARM L location, ARM E estimator equality |
| `vm_ab.py` | the A/B difference and the before and after crops |
| `vm_ring.py` | flat centroid and post-correction radial residual |
| `vm_marks.py` | annotated copies of the crops |

## 11. Defects for other lanes. I edited none of these

1. **`crates/strehl-cli/src/stack.rs`, approx. lines 822-834.** Three false
   claims in the `defect_request_from_env` doc comment. See F12. This is the
   most misleading text in the tree, because it is what a reader consults before
   deciding whether to trust the corrector.
2. **`experiments/DELIVER-V5/dust_patch.py`.** Measures a fixed point about
   215 px from the mote on the subjects it adjudicated, and its shipped
   `NOT-REPRODUCED` artifacts read as exculpatory while being pictures of empty
   background. It also excluded the one subject that carried its own deepest
   reading.
3. **`crates/strehl-core/src/defect-map-ILCE-7CM2-dust.txt`.** Mote 2's stored
   depth is 2.8x the measured truth. See F5.
4. **`crates/strehl-cli/examples/defect-flat-census.rs`.** The box-64 background
   is truncated at the frame edge and biases this mote deep by about 0.54 pp.
   See F6.
5. **Open, not mine.** Mote 1's coordinate, see 8.2.

## 12. Artifacts

`C:\dev\strehl-out\V-MOTE\crops\`, 1.68 MB, five PNGs, described in the
`README.txt` beside them. Everything else this lane created has been deleted
under the disk directive, returning about 1.30 GB. The deleted items were
derived scratch only: three master TIFFs, npy caches, a private cargo target
directory, a source copy and the pinned executables. The inputs are intact.
