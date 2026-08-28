# V-RIM: the thirteen tight-scale rim failures are an instrument artifact

**VERDICT: THE RIM AXIS AS BUILT MEASURES SHOULDER ROUGHNESS, NOT RIM. Eleven of
the thirteen are instrument artifact outright. Two carry a coherent local
brightening that is real, invisible at print scale, and not what the convicting
number measures. The rim axis does not block a print-readiness claim, and it
must not be cited as supporting one either, because in its present form it
cannot distinguish a haloed print from a sharp one.**

*Lane V-RIM, second-claimant verification of SYNTHESIS fact 1881. Read-only on
`crates/`; nothing under `experiments/V-GATHER/`, `experiments/V-H2H2-RIMCLIP/`
or any master was modified. `rimaxis.py` and `rimv6.py` are imported unchanged
and called, never re-implemented. Scripts are in `experiments/V-RIM/`.*

**The exact sentence that is safe to say:**

> A rim-free image whose only property matched to the master is how rough its
> bright shoulder is reads AT OR ABOVE what the master reads, on eleven of the
> thirteen, inside the range where that comparison is interpolated rather than
> extrapolated. Two of three never-stacked single captures of `coffee-bean` FAIL
> the same axis, and so does Zerene Stacker PMax. The axis convicts on texture.

---

## 1. What was claimed, and what reproduces

`experiments/V-GATHER/printcert4.py`, run unmodified, partitions the rim axis
**9 PASS / 13 FAIL / 4 REFUSED = 26**. That reproduces. The thirteen are:

`112MSDCF`, `113MSDCF`, `bee-1-cpl`, `coffee-bean`, `couch-fibers-cpl`,
`flat-on-ruler-cpl`, `flowers-cpl`, `lavendar-cpl`, `lead-1-cpl`, `leaf-2-cpl`,
`pencil-steep-angle-cpl`, `wrapped-text-1`, `wrapped-text-2`.

My own harness reproduces every `corrected_bright` in `rim.json` to three
decimals, so what follows is scored on the same numbers, not a variant.

### 1.1 The thirteen were not measured on the deliverable

`rimaxis.py:52` pins `SEAL_DIR` to `C:\dev\strehl-out\acceptance\SHIP-V4`. Fact
1881 records that provenance and reads it as the shipping backend. It is the
shipping *backend*; it is **not the shipping bytes**. Measured:

| subject | SHIP-V4 vs `ORCH-FAITHFUL\faithful` |
|---|---|
| `112MSDCF` | 99.77% of samples differ, mean abs 398.9 DN, max 12995 DN |
| `leaf-2-cpl` | 99.73% differ, mean abs 931.2 DN, max 22764 DN |
| `coffee-bean` | 96.84% differ, mean abs 19.1 DN, max 1527 DN |

Only the `Software` and `StripOffsets` tags differ in the header; the pixels are
genuinely different renders. Re-running the whole axis against the deliverable
gives **9 PASS / 12 FAIL / 5 REFUSED**, not 13 FAIL: `112MSDCF` moves from FAIL
to REFUSED because its instrument floor rises past tolerance. Individual numbers
move a long way — `leaf-2-cpl` **+37.07% -> +12.92%**, a 24-point swing between
two renders of one scene that differ by about 1.4% RMS.

That instability is itself a finding. A statistic that moves 24 points when the
image moves 1.4% is not reporting a property of the image.

## 2. What the statistic actually is, worked out before measuring

For each selected edge `rimv6.measure` takes a 25-px profile `p` along the
gradient, `t = -12..+12`, sets `lo = mean(p[-12..-9])`, `hi = mean(p[+9..+12])`,
`step = hi - lo`, `q = (p - lo)/step`, and reports

```
ov   = max( q[t = +2..+7] ) - 1        per edge
bright = median( ov )                  over edges
```

Three consequences follow from the form alone, and I wrote them down before
running anything.

**P1 — the max of six samples is positive without a rim.** `ov` is a maximum
over six samples of a quantity whose expectation is 1. Any zero-mean shoulder
fluctuation — sensor noise, resolved texture, nearest-neighbour sampling jitter
along a diagonal normal — makes `E[max] > 1`. The instrument's floor arm cannot
remove this, because the floor is measured on the same image Gaussian-smoothed
at sigma 3.0, where that fluctuation has been destroyed by construction. **The
floor subtracts a bias measured on an image that does not have the bias.**

**P2 — the bias scales with shoulder roughness over step.** Therefore rough or
low-contrast subjects should read high with no rim present.

**P3 — the reference is inside the profile, so wide rims are under-read.** `hi`
is taken at `t = +9..+12`. A rim extending past `t = +9` inflates `hi`, inflates
`step`, and deflates `q` at its own peak. The axis is a band-pass for rims that
peak in `+2..+7` and have vanished by `+9`. It is therefore not the same
measurand as `halo_profile.py`, and neither result can impeach the other —
which is what fact 1881 already says, and it survives.

**P4 — the false-positive rate has never been measured.** `rimcommission.py`
has a sensitivity ladder and two arms it calls controls. Arm `FLOOR` tests the
sigma-3 smoothed base. Arm `NOTALWAYS` tests the unmodified master — the very
thing under test, so if the master carries a false positive that arm asserts it
away. **Neither arm is a sharp image known to be rim-free.** Confirmed by
reading: `rimcommission.py` passes 11 of 11 and not one arm is a specificity
arm.

## 3. The specificity arm that was never run

`experiments/V-RIM/vr_specificity.py`. A synthetic scene of 28 straight steps
convolved with a Gaussian. A blurred step is monotone, so **no rim exists
anywhere in this image, by construction**. Adding a zero-mean band-limited field
to the shoulders adds roughness, not a rim. Everything the axis reads here is a
false positive. The full `rimaxis` pipeline runs on it unchanged.

### Arm A — sweep roughness, no rim

| shoulder field / step | `corrected_bright` | median-then-max | verdict |
|---|---|---|---|
| 0.00 | +0.787% | +0.000% | PASS |
| 0.01 | +1.497% | +0.067% | PASS |
| **0.02** | **+2.304%** | +0.183% | **FAIL** |
| 0.04 | +3.982% | +0.553% | FAIL |
| 0.08 | +7.927% | +1.558% | FAIL |
| 0.16 | +16.370% | +4.574% | FAIL |
| 0.30 | +28.346% | +8.763% | FAIL |

**`rimv6` FAILs a monotone, rim-free image once its bright shoulder carries 2%
of the edge step in zero-mean roughness.** That is below the noise floor of any
real photograph. `RIM_MAX` is 2.0% and the reading with no rim at all and
nothing but ordinary roughness is already 2.3%.

### Arm B — sensitivity, the arm that does work

Roughness held at 0.04 of step; a rim of known amplitude planted at `t = +3 px`,
width 1.5 px, windowed so it cannot reach the normalising reference.

| planted rim / step | `corrected_bright` | median-then-max |
|---|---|---|
| 0.00 | +3.982% | +0.553% |
| 0.01 | +4.362% | +0.947% |
| 0.02 | +4.778% | +1.563% |
| 0.04 | +5.527% | +2.889% |
| 0.08 | +7.676% | +5.750% |
| 0.16 | +12.954% | +12.480% |

The axis is **not inert** — it does respond to a real rim, monotonically. Its
problem is not sensitivity; it is that its zero point is set by roughness. Note
also that `median-then-max` tracks the planted amplitude at gain 0.75 while
`corrected_bright` tracks it at gain 0.56 on a pedestal of +4.0%. Swapping the
two reductions is most of the fix.

### Arm C — the read-across, and the decisive table

Set the synthetic's roughness to each master's own measured shoulder sd, with
**no rim**, and compare against what that master reads.

| subject | reads | shoulder sd | rim-FREE image at that sd reads | median-then-max |
|---|---|---|---|---|
| `lead-1-cpl` | +3.36% | 0.1333 | **+18.64%** | +1.54% |
| `bee-1-cpl` | +3.13% | 0.0795 | **+10.04%** | +0.58% |
| `couch-fibers-cpl` | +3.50% | 0.0584 | **+6.78%** | +0.94% |
| `flowers-cpl` | +5.18% | 0.0868 | **+11.22%** | +1.77% |
| `pencil-steep-angle-cpl` | +6.77% | 0.0780 | **+9.79%** | +4.01% |
| `wrapped-text-1` | +7.48% | 0.1088 | **+14.76%** | +2.30% |
| `lavendar-cpl` | +8.01% | 0.1035 | **+13.91%** | +2.34% |
| `wrapped-text-2` | +10.93% | 0.1199 | **+16.55%** | +3.92% |
| `112MSDCF` | +12.62% | 0.1440 | **+20.30%** | +8.02% |
| `flat-on-ruler-cpl` | +14.84% | 0.1557 | **+22.12%** | +9.05% |
| `113MSDCF` | +17.28% | 0.1644 | **+23.47%** | +11.12% |
| `coffee-bean` | +33.25% | 0.1992 | >= +28.35% (extrapolated) | +13.48% |
| `leaf-2-cpl` | +37.07% | 0.3015 | >= +28.35% (extrapolated) | +8.07% |

**For eleven of the thirteen, inside the range where the read-across is
interpolated and not extrapolated, a rim-free image at the master's own shoulder
roughness reads MORE than the master does.** The masters' readings are entirely
accounted for by roughness with no rim required. The last two sit above the top
of the swept grid (sd 0.1957) and are stated as extrapolated, not claimed;
the Arm A curve is near-linear in sd, and linear extrapolation puts
`leaf-2-cpl`'s rim-free pedestal near +44% against its +37.07%.

## 4. The control that is not ours

`experiments/V-RIM/vr_external.py` and `vr_sourceframe.py`. Same instrument,
same thresholds, producers that are not strehl.

| arm | what it is | `corrected_bright` | verdict |
|---|---|---|---|
| **Zerene Stacker PMax** | commercial stacker, 63-frame `test2` set | **+7.455%** | **FAIL** |
| strehl `stack_test2_rec2020` | same 63 frames | -1.994% | PASS |
| `test2` frame 30 | one Lightroom-developed capture, never stacked | +1.621% | PASS |
| `test2` frame 45 | one capture, never stacked | **+3.862%** | **FAIL** |
| `coffee-bean` frame 30 | one capture of a FAILING SUBJECT, never stacked | **+6.741%** | **FAIL** |
| `coffee-bean` frame 60 | ditto | +1.938% | PASS |
| `coffee-bean` frame 90 | ditto | **+7.579%** | **FAIL** |

Read the last three rows again. **Two of three individual, never-stacked
captures of `coffee-bean` — a subject on the list of thirteen — FAIL the rim
axis.** A single capture has been through no merge, no pyramid and no election;
it cannot carry a rim this project put there. And the spread across three frames
of one scene is 1.9% to 7.6%, nearly three times the entire FAIL threshold.

Zerene, a commercial product, reads +7.455% — level with `wrapped-text-1`
(+7.48%) and `pencil-steep-angle-cpl` (+6.77%). Whatever this axis convicts,
it convicts the commercial comparator too.

*Stated rather than buried:* the source frames are Lightroom-developed and
Lightroom applies capture sharpening, so a 1-2 px overshoot may be present that
a strehl master does not have. The axis measures at `t = +2..+7 px`, outside
that radius, and the synthetic arm of section 3 has no develop step at all and
reaches the same conclusion. This arm alone would not be enough; it is not
alone. The provenance of `stack_test2_rec2020.tif` as a strehl render is taken
from `experiments/V-HEADTOHEAD` and was not independently verified by me; the
never-stacked rows carry the argument and do not depend on it.

## 5. The pixels

`experiments/V-RIM/vr_crops.py` cuts 1:1 sRGB crops centred on the individual
edges the instrument itself ranked worst, plus two at the subject's median
reading as a matched control, and separately builds a 25x41 edge-aligned stack —
every selected edge rotated so bright is to the right and medianed together, so
that texture, which is incoherent along an edge, averages away while a rim,
which is coherent, survives.

Written to `D:\strehl-out\V-RIM\pics` and looked at. What is there:

- **`coffee-bean`** worst four sites (`ov` +278%, +277%, +216%, +205%): the
  crystalline surface of a coffee bean. No occluding edge in frame at all.
- **`113MSDCF`** and **`112MSDCF`** worst sites (+254%, +223%): a thicket of
  bright filaments a pixel or two wide on a grey ground. The "edge" the selector
  found on the sigma-3 smoothed reference is the *boundary of a textured
  region*, not a contour.
- **`leaf-2-cpl`** worst four sites (+2986%, +1089%, +408%, +406%): **flat,
  featureless out-of-focus background.** There is no edge there. Its fifth site,
  at the subject's median reading, is a real leaf edge and carries no halo.
- **`wrapped-text-2`** (+240%): printed dots on foam. The surround is uniform
  white granular texture with **no brightening ring**.
- **`lavendar-cpl`**, **`pencil-steep-angle-cpl`**, **`couch-fibers-cpl`**,
  **`bee-1-cpl`**, **`flat-on-ruler-cpl`**: crystal, graphite sparkle, synthetic
  fibre, bee setae, paper grain. Texture in every case.
- Control: **`flower-inner-edge-cpl`**, which PASSES at -0.06%, has a worst-edge
  `ov` of **+102.9%**. Per-edge overshoots above 100% are present on subjects the
  axis acquits, so a per-edge value carries no information.

The edge-aligned stack, rendered at the master's own print gain, shows **a smooth
monotone ramp with no visible band on every one of the thirteen.** Only when the
stack is stretched so that +/-6% of the step fills the panel does anything appear,
and what appears is mottled and irregular rather than a stripe running along the
edge.

Maximum of the stacked median profile over `t = +2..+7`, which is the coherent
part of the reading:

| coherent excursion | subjects |
|---|---|
| none (<= +1.1%) | `wrapped-text-1`, `wrapped-text-2`, `lavendar-cpl`, `flowers-cpl`, `bee-1-cpl`, `couch-fibers-cpl`, `lead-1-cpl` |
| marginal (+2.5%) | `pencil-steep-angle-cpl`, at `t = +7`, the last sample in the window |
| present (+5.8% to +12.3%) | `leaf-2-cpl` +5.8%, `113MSDCF` +9.0%, `112MSDCF` +12.3% |
| stack not usable | `coffee-bean`, `flat-on-ruler-cpl` -- edge curvature smears the tangent average, the stacked profile never reaches 1.0, and no coherent statement can be made from it |

Seven of the thirteen have **no coherent bright excursion at all** in the
measurement window. Their entire reading is the max-of-six pedestal.

## 6. What number would a real rim have to be

`experiments/V-RIM/vr_calibrate.py` runs `rimcommission.py`'s own ladder --
same `usm`, same amounts, radius 2.0 -- on failing subjects and on the passing
control, on the identical 2048px crop.

```
109MSDCF  PASS control   usm 0.00 -> -2.11%   usm 2.00 -> +1.23%   usm 4.00 -> +10.22%
wrapped-text-2           usm 0.00 -> +12.67%  usm 1.00 -> +28.33%  usm 4.00 -> +71.16%
113MSDCF                 usm 0.00 -> +11.89%  usm 1.00 -> +23.37%  usm 4.00 -> +54.03%
coffee-bean              usm 0.00 -> +8.36%   usm 2.00 -> +23.61%  usm 3.00 -> REFUSED
```

On the only subject whose zero is near zero, an unsharp mask at **amount 4.0,
radius 2.0** is needed to reach +10.2%. `wrapped-text-2` reads +10.93% and
`coffee-bean` +33.25% on the full frame. Taken at face value the axis is
asserting that these masters carry a rim stronger than a 4x unsharp mask. That
is a defect nobody could miss at 1:1, and section 5 shows it is not there.

Note also the crop dependence: `coffee-bean` reads **+33.25%** whole-frame and
**+8.36%** on a 2048px crop of itself. Twenty-five points, same image.

## 7. Two defects in `rimaxis.py` proper

**7.1 `MIN_ISOLATED` is dead.** `rimaxis.py:57` defines `MIN_ISOLATED = 0.20`
and the module docstring says *"A subject whose isolated fraction is too low is
REFUSED on this axis, never passed."* The name appears exactly once in the
repository — at its own definition. It is never read. `wrapped-text-1`
(isolated 16.2%) and `wrapped-text-2` (12.1%) are both below it and both were
convicted FAIL. **Two of the thirteen are convicted in violation of the
instrument's own written refusal rule.**

**7.2 the gate is one-sided.** `printcert4.rim_verdict` convicts on
`corrected_bright` only. `flower-bud-alone-cpl` reads `corrected_dark` +4.51%
with bright -0.04% and is recorded PASS; `flower-bud-with-background-fern-cpl`
reads dark +3.88% and is recorded PASS. Under a planted unsharp mask the two
axes move together (`dark/bright` reaches 1.04 at amount 4.0, measured), so a
gate that can only convict on one of them is not measuring ringing.

## 8. Scoring the thirteen

Rubric. **instrument artifact** = a rim-free image at this subject's roughness
reads at or above it, AND the tangent-averaged stack shows no coherent
excursion, AND the 1:1 pixels show no rim. **real but below visibility** = a
coherent excursion is present in the stack but is not visible at 1:1 or at
print gain. **real defect** = visible.

| # | subject | reads | call | why |
|---|---|---|---|---|
| 1 | `bee-1-cpl` | +3.13% | **instrument artifact** | rim-free at its sd reads +10.04%; stack peak +0.4%; worst site `ov` +5198% on bee setae |
| 2 | `couch-fibers-cpl` | +3.50% | **instrument artifact** | rim-free +6.78%; stack peak +1.1%; sites are soft fibre crossings |
| 3 | `lead-1-cpl` | +3.36% | **instrument artifact** | rim-free +18.64%, 5.5x its reading; stack peak +1.1% |
| 4 | `flowers-cpl` | +5.18% | **instrument artifact** | rim-free +11.22%; stack peak -1.4%; worst site is 19 px from the frame border |
| 5 | `pencil-steep-angle-cpl` | +6.77% | **instrument artifact** | rim-free +9.79%; only excursion is +2.5% at `t=+7`, the last sample; sites are graphite sparkle; `dark/bright` = -0.014, no ringing |
| 6 | `wrapped-text-1` | +7.48% | **instrument artifact** | rim-free +14.76%; stack monotone, no excursion; also below `MIN_ISOLATED` and should have been REFUSED |
| 7 | `lavendar-cpl` | +8.01% | **instrument artifact** | rim-free +13.91%; stack monotone; sites are crystal texture |
| 8 | `wrapped-text-2` | +10.93% | **instrument artifact** | rim-free +16.55%; stack monotone; printed dots with no ring at 1:1; below `MIN_ISOLATED` |
| 9 | `flat-on-ruler-cpl` | +14.84% | **instrument artifact** | rim-free +22.12%; sites are wood/paper grain and specks, no occluding edge |
| 10 | `coffee-bean` | +33.25% | **instrument artifact** | worst four sites are bean surface crystal with no edge in frame; two of three never-stacked captures of this same subject FAIL the same axis at +6.7% and +7.6% |
| 11 | `leaf-2-cpl` | +37.07% | **instrument artifact** | worst four sites are FLAT OUT-OF-FOCUS BACKGROUND with no edge; reading collapses to +12.92% on the deliverable render of the same scene |
| 12 | `112MSDCF` | +12.62% | **real but below visibility** | stack carries a coherent +12.3% at `t=+6`; it is the first filaments inside a filament thicket, invisible at 1:1 and at print gain; rim-free at its sd reads +20.3%, so the convicting number is not a measure of it. REFUSED, not FAILED, on the deliverable |
| 13 | `113MSDCF` | +17.28% | **real but below visibility** | stack carries a coherent +9.0% at `t=+4`, same filament-thicket geometry; rim-free at its sd reads +23.5% |

**11 instrument artifact / 2 real but below visibility / 0 real defect.**

## 9. Does the rim axis block print readiness

**No, and it does not clear it either.**

It does not block, because the FAIL verdicts are not evidence of a rim: a
rim-free image at the same roughness reads higher, a never-stacked capture of a
failing subject reads FAIL, and the commercial comparator reads FAIL. No claim
of a visible rim on the shipping masters survives.

It does not clear, because an axis whose zero point is set by texture cannot
certify the absence of a rim either. Its `median-then-max` figure is the part
that tracks a planted rim nearly one-for-one, and on the thirteen that figure
runs +0.6% to +13.5% with a rim-free pedestal underneath it that I have priced
only on a synthetic scene.

The honest status of the deliverable on this axis is **rim-unconvicted at tight
scale**, which is stronger than fact 1881's *rim-unexamined* and weaker than
*rim-clean*.

### What would have to change to unblock it as a gate

1. **Report `max(median_over_edges(q))`, not `median_over_edges(max(q))`.** Same
   pixels, same selection, one line. Arm B measures its gain at 0.75 against
   0.56, on a pedestal of +0.55% against +3.98%.
2. **Set the threshold from a measured false-positive curve, not from the floor
   tolerance.** `RIM_MAX = FLOOR_MAX_FWD = 0.02` is derived, but it is derived
   from a floor measured on a smoothed image, and a rim-free sharp image reads
   +2.30% at 2% roughness.
3. **Add a specificity arm to `rimcommission.py`** — a sharp image that is
   rim-free by construction — and require it to PASS.
4. **Wire up `MIN_ISOLATED`,** or delete it and stop claiming the refusal in the
   docstring.
5. **Point `SEAL_DIR` at the deliverable,** or state in every result that
   SHIP-V4 is a different render from `ORCH-FAITHFUL\faithful`.

Items 1-3 are what turn this from a texture meter into a rim gauge. Until then
no print-readiness claim should rest on this axis in either direction — and
that is a narrower statement than fact 1881's, which reads the thirteen as a
possible defect in the product.

## 10. What I could not measure

- **Whether the coherent excursion on `112MSDCF` and `113MSDCF` is scene or
  merge.** There are no developed source frames for those two subjects under
  `D:\edited\macro`, only raw captures, and rendering one would have needed the
  binary that BUILD-SOFTGATE is rebuilding. The 1:1 pixels say the excursion sits
  where the first filaments of a thicket are, and the excursion moves from +11.1%
  to +15.3% between two strehl renders of the same scene, both of which point at
  scene structure; neither proves it.
- **The rim-free pedestal above shoulder sd 0.196.** `coffee-bean` (0.199) and
  `leaf-2-cpl` (0.302) sit above the top rung of Arm A. Both are marked
  extrapolated in section 3 and neither is claimed as interpolated.
- **`coffee-bubbles`, `foam`, `tweezers-cpl`, `highly-angled-ruler-mm-cpl`** are
  REFUSED on this axis and I did not adjudicate them; they were not among the
  thirteen. `highly-angled-ruler-mm-cpl` reads +2.001% against a 2.0% threshold,
  which is a coin toss, and is REFUSED only because its bootstrap interval
  straddles the line.
- **Whether any rim exists at scales the axis cannot see.** P3 shows this
  instrument is blind to rims wider than about 9 px, and `halo_profile.py` never
  measured 120-400 px. Between them there is still a band nobody has walked.
  I did not open it; it is not this lane's question.

## 11. What would falsify me

- A rim-free sharp image — synthetic or real — that reads **near zero** at
  shoulder sd 0.10-0.20 through the unmodified `rimaxis` pipeline. My Arm A
  would then be measuring something other than the max-of-six pedestal, and the
  read-across table in section 3 collapses.
- A 1:1 crop from any of the thirteen, at a site the instrument ranked worst,
  showing a bright band along an occluding edge at print gain. I looked at the
  worst four sites on ten of the thirteen and found texture; a site I did not
  cut that shows a band would refute the pixel arm.
- A demonstration that `D:\edited\macro\coffee-bean\DSC000*.tif` are not
  single captures of `coffee-bean` but something already merged. The
  never-stacked arm in section 4 depends on that identification.
- Any run of `experiments/V-RIM/vr_specificity.py` in which Arm B does **not**
  rise monotonically. That would mean my harness cannot see a rim either, and
  nothing above would be admissible.
