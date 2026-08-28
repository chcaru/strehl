import io, os

DOC = r"""# Closing the halo instrument's blind spot

`experiments\ORCH-drift-check\halo_profile.py`, run over the 26 delivered
masters at `C:\dev\strehl-out\ORCH-FAITHFUL\faithful\`.

**Before: 7 clean, 4 HALO, 15 skipped. After: 15 clean, 4 HALO, 7 UNMEASURABLE.**
Measured subjects 11 -> 19 of 26. Every number below is MEASURED unless labelled.

---

## 0. What you most need to know

Three findings outrank the coverage number.

1. **Both regime guards were inert on the exact subjects they were written
   for.** Guard 1 was written to catch `tweezers-cpl` and does not fire on it.
   Guard 2 was written to catch `flat-on-ruler-cpl` and cannot apply to it. A
   guard that cannot apply reads exactly like a guard that passed.
2. **The 200 DN threshold is not the detection floor.** Commissioning with
   planted rims puts the real floor at **400-12,800 DN depending on subject and
   radius**, i.e. 2x to 64x the threshold. The instrument is far less sensitive
   than its threshold implies, and nobody had measured this.
3. **Two of your eleven gate subjects changed verdict**, and I believe both
   changes are corrections rather than regressions. Evidence in section 6. You
   should decide, not me.

---

## 1. The skip taxonomy (MEASURED)

I evaluated every guard independently for all 26 rather than reporting only the
first to fire, because the first can mask the others -- `coffee-bubbles` fires
three guards and `foam` two, so "fix the component guard" would have bought
nothing on either. The 15 skips were four causes, not one:

| class | n | subjects | real cause |
| --- | ---: | --- | --- |
| **A. multi-component** | 9 | `109MSDCF` `119MSDCF` `couch-fibers-cpl` `flower-bud-with-background-fern-cpl` `flowers-cpl` `lead-1-cpl` `leaf-2-cpl` `wrapped-text-1/2` | see A1-A3 |
| **B. far field unreachable** | 2 | `112MSDCF` `113MSDCF` | background exists but never >181 px from subject |
| **C. no usable background** | 3 | `coffee-bubbles` `foam` `highly-angled-ruler-mm-cpl` | see C1/C2 |
| **D. background not uniform** | 1 | `coffee-bean` | far annuli differ 3563 DN |

Class A splits three ways, and the component COUNT is a symptom that hides it.
`leaf-2-cpl` has 574 components but only **4** hold >=1% of subject mass and the
speckle (parts under 0.5% each) is **5%** of mass:

- **A1 dominant blob plus satellites** (`leaf-2-cpl` largest 69%, `lead-1-cpl`
  67%, `119MSDCF` 70%, `flower-bud-with-background-fern-cpl` 70%). Two of these
  miss the 70% bar by rounding.
- **A2 genuinely fragmented** (`couch-fibers-cpl` 38% / 9 major,
  `flowers-cpl` 53%, `109MSDCF` 48%).
- **A3 no silhouette at all** (`wrapped-text-1` largest part 8% of subject mass
  across 37 major parts, `wrapped-text-2` 13%). Text on a page has no
  silhouette to walk outward from, and no fix should invent one.

Class C splits too: `coffee-bubbles` and `foam` fail the DIRECT tests (far field
0 px) and are genuinely unmeasurable, but `highly-angled-ruler-mm-cpl` failed
**only the `MAX_SUBJ` proxy** while holding 106,153 far-field px and 7 populated
near bands.

---

## 2. What changed, and why

**(a) The component guard is replaced by a Voronoi restriction, not loosened.**
Its stated concern is that walking outward from a union of parts crosses the
gaps between them. That is answered directly by restricting the walk to the
**dominant part's own Voronoi cell** -- background whose nearest subject pixel
belongs to the dominant part. Inside that cell the walk cannot cross into
another part's territory, so the confound is prevented by construction instead
of by refusing to measure. This is what lets 862-component `couch-fibers-cpl`
be measured.

**(b) Guard 2 now splits the far field at its own MEDIAN distance.** It
previously required both halves of a FIXED 400-650/650-900 split to hold >200
px. `flat-on-ruler-cpl` reaches only 599 px, so its outer half was empty and
the guard silently did not apply. **It was inert on 7 of 26 subjects.** The
median split is populated whenever the far field is.

**(c) `MAX_SUBJ` retired.** It was a proxy for "no usable background", which is
already tested directly and better by the backdrop fraction, far-field
population and near-band population. The direct tests still exclude
`coffee-bubbles` and `foam`.

**(d) Cell-pinch truncation** -- see section 4, this one came out of an
artifact I created and then caught.

---

## 3. An adaptive far field was TESTED AND REJECTED, with the calibration

`112MSDCF`/`113MSDCF` have 24% of frame as background that never lies more than
167/181 px from the subject, so the fixed 400-900 px window is unreachable. The
obvious fix is a nearer far field. I calibrated it on the 17 subjects where
**both** windows exist, measuring overshoot at 400-900 and again at 130-180:

| | |
| --- | --- |
| median absolute error | **3,318 DN** |
| worst | **13,023 DN** (`flower-inner-edge-cpl`) |
| threshold it must serve | 200 DN |

It is not small and **not one-signed** -- it flips verdicts in both directions:
`dry-erase-marker-head-cpl` +236.7 -> -535.1 (HALO would become clean) and
`119MSDCF` -284.1 -> +240.5 (clean would become HALO). A far field inside the
penumbra is not a far field. **Rejected**, and those two subjects are reported
UNMEASURABLE with that reason.

---

## 4. Two defects I introduced and caught by measuring

Recorded because they are the reason to not trust an uncommissioned instrument.

**(i) I restricted the far field to the Voronoi cell as well as the walk.**
That starved the reference: `lead-1-cpl` reaches 1766 px yet got **0** far-field
px inside the cell, so the subjects the restriction existed to rescue became
unmeasurable for a new reason. It also moved every already-passing subject,
because moving the reference moves all seven bands together (`bee-2-cpl`
-4273.0 -> -2477.0). Fixed: the far field is a **global reference level**; only
the walk is restricted. `bee-2-cpl` returned to -4306.9 against its -4273.0
baseline.

**(ii) The Voronoi restriction manufactured two HALO verdicts.** `leaf-2-cpl`
read +5721.4 / bump 10245.4 and `lead-1-cpl` +4446.8 / bump 9508.3. The profile
showed why: a clean monotone ramp to d=32-50, then a **single-band** spike at
50-80 and a fall at 80-120, while band population collapsed 42,924 -> 7,994. The
cell had narrowed to a directional sliver and its median was no longer the
background level at that distance.

The discriminator is **density, not population** -- the bands are 4,6,8,12,18,30
and 40 px wide, so raw counts are not comparable. Per-unit-width density
normalised to the innermost band, measured on all 26: well-formed cells hold
0.15-0.64, the pinching ones fall to 0.019. The walk now **stops** at the first
band below 10% rather than the subject being skipped, and requires >=3 usable
bands. Both subjects now read clean with monotone profiles.

I set that bar from all 26 subjects, not from the two that showed the artifact:
`pencil-flatter-angle-cpl` is a known-clean subject that collapses to 0.023,
as low as `leaf-2-cpl`, so density alone does not separate artifact from clean
and only truncation -- never a skip -- is licensed by it.

---

## 5. Commissioning, and the detection floor (MEASURED)

`experiments\V-REVIEW\vh_commission.py`. Every plant is verified to have landed
and hard-errors if not, so a "not detected" cannot come from a plant that
silently failed to apply.

**Null arm: 3 subjects, plant nothing. 0 of 3 moved** -- overshoot and bump
identical to the digit. Without this the floors below would be worthless,
because a detector that fires on everything would score perfectly.

**Planted arm: smallest amplitude caught, in DN, by radius.**

| subject | r=8 | r=15 | r=30 | r=60 | r=100 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `bee-2-cpl` | 12800 | 12800 | 6400 | 3200 | 12800 |
| `flower-bud-alone-cpl` | 6400 | 3200 | 1600 | 1600 | 1600 |
| `109MSDCF` | 6400 | 3200 | 3200 | 400 | 800 |

**STATED DETECTION FLOOR: 400 DN at best, 12,800 DN at worst, median 3,200 DN,
for a rim of sigma=8 px.** Against a nominal threshold of 200 DN.

Two mechanisms, both already half-documented in the file's own commission notes:
the subject's penumbra rises thousands of DN per band close in, so a rim there
rides a gradient larger than itself; and the **median** -- chosen precisely so
wisps and dust cannot fake a halo -- also makes a narrow rim invisible when the
band is 30-40 px wide. **The robustness that makes this instrument trustworthy
is the same property that makes it insensitive.** That trade is now measured
rather than assumed.

The floor is worst-case for a NARROW rim; a broad halo is caught lower. It is
not a bound on broad defects.

---

## 6. Regression on your 11 gate subjects: 9 hold, 2 change

| subject | fact 1841 | now | verdict |
| --- | --- | --- | --- |
| `flat-on-ruler-cpl` | +4481.8 (bump 227.0) | **+5680.4** (bump 0.0) | HALO **held** |
| `tweezers-cpl` | bump 1542.3, over -15502.0 | bump **1567.0**, over **-15519.0** | HALO **held** |
| `lavendar-cpl` | +527.3 | **+350.9** | HALO **held** |
| `dry-erase-marker-head-cpl` | +236.7 | **-1014.3** | **CHANGED -> clean** |
| `bee-1-cpl` | -3666.5 bump 0.0 | -3441.0 bump 0.0 | clean held |
| `bee-2-cpl` | -4273.0 bump 0.0 | -4306.9 bump 0.0 | clean held |
| `bee-3-cpl` | -4212.3 bump 0.0 | -4186.6 bump 0.0 | clean held |
| `flower-bud-alone-cpl` | -431.7 | -471.0 | clean held |
| `flower-inner-edge-cpl` | clean | **UNMEASURABLE** | **CHANGED** |
| `pencil-flatter-angle-cpl` | clean | -7002.4 clean | clean held |
| `pencil-steep-angle-cpl` | clean | -11901.8 clean | clean held |

**`dry-erase-marker-head-cpl` HALO -> clean.** Its profile is now a textbook
monotone ramp with bump 0.0: -10218.5, -6861.4, -5706.0, -4282.0, -2920.0,
-1653.2, -1014.3. The old +236.7 cleared a 200 DN bar by 37 DN and came from
background owned by other components -- the gap-crossing confound. **Checked at
1:1** (`--mode halo`, six sites, no per-crop autoscale): the boundaries show a
soft penumbra and **no bright rim**. The eye agrees with the new verdict.

**`flower-inner-edge-cpl` clean -> UNMEASURABLE.** Its background fails
uniformity at **3147 DN** against a 3000 limit. It measured 2828 under the old
fixed split, so it is a borderline subject either way and the side it lands on
depends on how the annuli are cut. Its overshoot was -16604, nowhere near a
halo verdict, so **nothing is being hidden** -- but I did not special-case it,
because a guard with an exception for the subject that trips it is the defect I
was sent to fix.

**I did not tune anything to make these hold.** Both are consequences of fixing
guard inertness, and I would rather hand you two honest changes than a green
table.

---

## 7. The true 26-subject halo status (MEASURED)

**15 clean, 4 HALO, 7 UNMEASURABLE.**

| verdict | subjects |
| --- | --- |
| **HALO (4)** | `flat-on-ruler-cpl` +5680.4 - `tweezers-cpl` bump 1567.0 - `119MSDCF` +820.5 - `lavendar-cpl` +350.9 |
| **clean (15)** | `109MSDCF` `bee-1/2/3-cpl` `couch-fibers-cpl` `dry-erase-marker-head-cpl` `flower-bud-alone-cpl` `flower-bud-with-background-fern-cpl` `flowers-cpl` `highly-angled-ruler-mm-cpl` `lead-1-cpl` `leaf-2-cpl` `pencil-flatter-angle-cpl` `pencil-steep-angle-cpl` `wrapped-text-2` |
| **UNMEASURABLE (7)** | see below |

`119MSDCF` is the one new HALO. Its profile rises monotonically to +820.5 at the
OUTERMOST band with bump 0.0, so it is a **broad elevation, not a narrow rim**.
At 1:1 there is a visibly brighter zone hugging the strokes. I flag it, with the
caveat in section 8.

### The 7 unmeasurable, each with its reason and what would fix it

| subject | reason | what would make it measurable |
| --- | --- | --- |
| `112MSDCF` | background never >167 px from subject | **a capture with more clearance**, not a better statistic |
| `113MSDCF` | never >181 px | same |
| `foam` | subject 97% of frame, far field 0 px | full-frame texture: needs a different statistic entirely |
| `coffee-bubbles` | backdrop 1.5% of frame | same |
| `wrapped-text-1` | largest of 79 parts is 1.7% of frame | no silhouette exists; not a defect of the instrument |
| `coffee-bean` | background non-uniform, 3659 DN | re-shoot with even illumination |
| `flower-inner-edge-cpl` | background non-uniform, 3147 DN | borderline; see section 6 |

**Four of these seven are properties of the capture, not of the instrument.** For
`foam` and `coffee-bubbles` a rim statistic is undefined in principle -- there is
no background. Measuring those needs a different statistic (a local
contrast-inversion measure), which I have not built and am not claiming.

---

## 8. Gaps -- what I did NOT establish

- **The profile has an unmeasured hole between 120 px and 400 px.** The near
  bands stop at 120 and the far field starts at 400. `bump` therefore cannot
  see a local maximum peaking in that range, and `119MSDCF`'s +820.5 sits
  exactly at the edge of it. **I cannot presently distinguish a broad halo from
  a broad illumination gradient in that window** on that subject, and its HALO
  verdict should be read with that caveat.
- **The detection floor is measured on 3 subjects, not 26**, and for one rim
  shape (Gaussian, sigma=8 px). Other shapes are unmeasured.
- **`flat-on-ruler-cpl`'s HALO may still be the illumination confound the file's
  own notes describe.** Guard 2 now applies to it and passes it at 234 DN, so
  the guard does not consider its background sloped -- but its notes say the
  card brightens to 120 px and is darker by 400-900, which is what a +5680
  overshoot with bump 0.0 looks like. **Unresolved**, and it is one of your four
  HALOs.
- I did not re-verify `tweezers-cpl` visually; its bump 1567.0 survives, but the
  file's own notes record that inspecting it at 1:1 showed a clean boundary.
  **Two of the four HALO verdicts therefore carry a documented suspicion of
  being confounds**, and neither is resolved by this work.
"""

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "HALO-coverage.md")
with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(DOC.lstrip("\n"))
b = open(path, "rb").read()
print("wrote", path, len(b), "bytes; last", hex(b[-1]), "CRs", b.count(b"\r"))
