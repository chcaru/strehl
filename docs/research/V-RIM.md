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

---

# Part two: ORCH's three follow-ups, 2026-08-28

*Sections 1-11 above stand except where section 14 revises them, and the
revisions are marked. Instruments added for this part:
`experiments/V-RIM/vr_ladder.py`, `vr_ladder2.py`, `vr_ladder3.py`,
`vr_score13.py`, `vr_shoulder.py`, `vr_ring.py`, `vr_ring2.py`,
`vr_ring_ship.py`, `vr_ring_lin.py`, `vr_ring_cmp.py`, `vr_ring_pics.py`.*

## 12. Closing the clamp: my own falsification 1, run

Section 3's read-across priced each master's rim-free pedestal by `np.interp`
on an Arm A ladder that stopped at shoulder sd **0.1957**. `coffee-bean`
(0.1992) and `leaf-2-cpl` (0.3015) are above that, so `np.interp` clamped and
their pedestals were extrapolated. ORCH called that the weakest joint in the
report. It was.

**Route 1 -- the ladder extended by direct measurement.** Same scene, same
roughener, same pipeline. The nominal roughness amplitude is not the achieved
shoulder sd, so the achieved sd is reported next to each rung:

| amp | achieved sd | corrected | med-then-max | n_sel | verdict |
|---|---|---|---|---|---|
| 0.000 | 0.0175 | +0.787% | +0.000% | 6003 | PASS |
| 0.012 | 0.0388 | +3.982% | +0.553% | 6170 | FAIL |
| 0.048 | 0.1187 | +16.370% | +4.574% | 6307 | FAIL |
| 0.090 | 0.1957 | +28.346% | +8.763% | 4433 | FAIL |
| 0.110 | 0.2279 | +32.999% | +9.909% | 3669 | FAIL |
| 0.130 | 0.2526 | +36.698% | +10.970% | 2994 | FAIL |
| 0.150 | 0.2672 | +39.254% | +11.163% | 2468 | FAIL |
| 0.170 | 0.2966 | +44.902% | +13.078% | 2036 | FAIL |
| 0.200 | 0.3342 | +48.659% | +13.115% | 1624 | FAIL |
| 0.240 | 0.3930 | +59.049% | +20.201% | 1109 | FAIL |

The ladder now spans **0.0175 to 0.3930**. Every one of the thirteen has a
shoulder sd inside it. Nothing in this report is extrapolated any more.

Re-pricing the headline read-across with no clamp anywhere:

| subject | sd | reads | rim-free at that sd | headline call |
|---|---|---|---|---|
| `bee-1-cpl` | 0.0795 | +3.13% | +10.29% | artifact |
| `couch-fibers-cpl` | 0.0584 | +3.50% | +7.02% | artifact |
| `lead-1-cpl` | 0.1333 | +3.36% | +18.64% | artifact |
| `flowers-cpl` | 0.0868 | +5.18% | +11.43% | artifact |
| `pencil-steep-angle-cpl` | 0.0780 | +6.77% | +10.05% | artifact |
| `wrapped-text-1` | 0.1088 | +7.48% | +14.83% | artifact |
| `lavendar-cpl` | 0.1035 | +8.01% | +14.01% | artifact |
| `wrapped-text-2` | 0.1199 | +10.93% | +16.55% | artifact |
| `flat-on-ruler-cpl` | 0.1557 | +14.84% | +22.12% | artifact |
| **`coffee-bean`** | 0.1992 | **+33.25%** | **+28.84%** | **ABOVE PEDESTAL** |
| `leaf-2-cpl` | 0.3015 | +37.07% | +45.39% | artifact |
| `112MSDCF` | 0.1440 | +12.62% | +20.30% | artifact |
| `113MSDCF` | 0.1644 | +17.28% | +23.47% | artifact |
| `109MSDCF` control | 0.0598 | -2.25% | +7.24% | artifact |

**`leaf-2-cpl` is acquitted by direct measurement**: its rim-free pedestal is
+45.39% against a reading of +37.07%. **`coffee-bean` is not.** It reads 4.4
points above its own rim-free pedestal. Section 8 called it an artifact on the
strength of the pixels and the never-stacked captures, not on this comparison,
and that is still the argument -- but the read-across no longer supports it and
I am recording that it does not.

**Route 2 -- the pedestal measured on the master itself, no synthetic scene.**
`rimv6.measure` returns the `(n_edges x 25)` array of normalised profiles. Split
it as `P = m + R`, `m` the median profile and `R` the per-edge residual. A rim
is a coherent non-monotone excursion in `m`; roughness lives in `R` and is
incoherent across edges. Replace `m` by its isotonic non-decreasing projection
and re-read. Every edge keeps its residual row bit-exact, so shoulder sd and
t-to-t correlation are unchanged, and the only thing removed is the coherent
bump.

The operation's matched control, on a planted rim at fixed roughness:

| planted rim / step | raw | isotonic pedestal | coherent excursion |
|---|---|---|---|
| 0.000 | +3.312% | +3.155% | +0.370% |
| 0.020 | +4.335% | +3.909% | +1.021% |
| 0.080 | +8.059% | +6.166% | +3.795% |

The pedestal follows about 63% of a planted rim, so it is a weak, conservative
control -- but the **coherent excursion** column tracks the plant cleanly and is
the usable statistic. Both PASS controls, `109MSDCF` and `119MSDCF`, read
coherent excursion **0.000%**: their median profiles are already monotone, so
the projection is the identity and the operation correctly does nothing.

## 13. The rim-free floor for the coherent excursion

The coherent excursion of a median over `n` rough edges is not zero when no rim
exists. Measured on the rim-free synthetic across the whole sd range, and on the
planted-rim series for the other end of the scale
(`z = coherent * sqrt(n) / sd`):

| rim-free sd | 0.0175 | 0.0388 | 0.1187 | 0.1957 | 0.2526 | 0.2966 | 0.3342 | 0.3930 |
|---|---|---|---|---|---|---|---|---|
| coherent | 0.000% | 0.370% | 2.698% | 5.260% | 6.751% | 7.999% | 8.501% | 12.623% |
| z | 0.0 | 7.5 | 18.1 | 17.9 | 14.6 | 12.1 | 10.2 | 10.6 |

| planted rim / step | 0.000 | 0.010 | 0.020 | 0.040 | 0.080 | 0.160 |
|---|---|---|---|---|---|---|
| z | 7.5 | 12.0 | 20.5 | 36.6 | 62.6 | 98.2 |

The thirteen, scored on `z` against the rim-free floor at their own sd. `z_free`
is interpolated, never extrapolated:

| subject | n edges | sd | coherent | z | rim-free z | call |
|---|---|---|---|---|---|---|
| `bee-1-cpl` | 2970 | 0.0795 | 0.380% | 2.6 | 12.9 | artifact |
| `couch-fibers-cpl` | 1679 | 0.0584 | 0.549% | 3.9 | 10.1 | artifact |
| `lead-1-cpl` | 1284 | 0.1333 | 0.849% | 2.3 | 18.0 | artifact |
| `flowers-cpl` | 2411 | 0.0868 | 0.961% | 5.4 | 13.8 | artifact |
| **`pencil-steep-angle-cpl`** | 2034 | 0.0780 | 2.319% | **13.4** | 12.7 | **above floor** |
| `wrapped-text-1` | 1861 | 0.1088 | 1.515% | 6.0 | 16.7 | artifact |
| `lavendar-cpl` | 1159 | 0.1035 | 1.492% | 4.9 | 16.0 | artifact |
| `wrapped-text-2` | 1432 | 0.1199 | 2.404% | 7.6 | 18.0 | artifact |
| `flat-on-ruler-cpl` | 244 | 0.1557 | 6.386% | 6.4 | 18.0 | artifact |
| `coffee-bean` | 334 | 0.1992 | 9.578% | 8.8 | 17.7 | artifact |
| `leaf-2-cpl` | 109 | 0.3015 | 5.416% | 1.9 | 11.9 | artifact |
| `112MSDCF` | 97 | 0.1440 | 5.009% | 3.4 | 18.0 | artifact |
| `113MSDCF` | 72 | 0.1644 | 7.584% | 3.9 | 18.0 | artifact |
| `109MSDCF` control | 2371 | 0.0598 | 0.000% | 0.0 | 10.3 | artifact |

`pencil-steep-angle-cpl` is the only subject above the floor, at `z` 13.4
against 12.7, implying a rim of **1.2% of the local edge step**. The planted
ladder does not resolve 1% of step from nothing (`z` 12.0 against a floor of
7.5-18.0), so that is inside the instrument's own noise.

**The two routes disagree about which subject is the exception, and no subject
fails both.** Route 1 leaves `coffee-bean`; route 2 leaves
`pencil-steep-angle-cpl`. That is what a null looks like when two estimators
each keep one different subject at the margin.

I tested the obvious explanation for `coffee-bean`'s 4.4-point excess -- that
bean crystal is heavy-tailed where the synthetic roughener is Gaussian, and a
max over six samples is exactly what a heavy tail inflates. **It is not.**
Excess kurtosis of the shoulder residual: `coffee-bean` **-1.60**, synthetic at
matched sd **-1.58**. The 99.9th percentile: 1.98 against 1.93. That hypothesis
is dead and `coffee-bean`'s excess is unexplained.

## 14. Revisions to sections 3 and 8

- **`leaf-2-cpl`** -- was artifact on an extrapolated pedestal; **now artifact
  on a directly measured one**. Strengthened.
- **`112MSDCF` and `113MSDCF`** -- were *real but below visibility* on the
  strength of the tangent-averaged stack. Their coherent excursion is 5.009%
  and 7.584% against a rim-free floor of 3.538% and 4.217%, but on `z`, which
  accounts for their very small edge counts (97 and 72 against the ladder's
  1082-6307), they read 3.4 and 3.9 against a floor of 18.0. **On this
  evidence they move to instrument artifact.** The stack excursion in
  section 5 is real and I still cannot say whether it is scene or merge; what
  has changed is that it is no longer above what 97 rough edges produce by
  chance.
- **`pencil-steep-angle-cpl`** -- was artifact; **now the one subject marginally
  above the coherent floor**, at an implied rim of 1.2% of the edge step, which
  is below what the planted ladder can resolve. Call it *real but unresolvable*
  and note that this is a downgrade in confidence, not an upgrade to defect.
- **`coffee-bean`** -- was artifact; the read-across no longer supports that and
  the heavy-tail explanation is refuted. Its acquittal now rests on the pixels
  and on the two never-stacked captures of the same subject that FAIL the same
  axis. **Recorded as artifact-on-external-evidence-only.**

Revised score: **13 instrument artifact / 0 real but below visibility / 0 real
defect**, with `coffee-bean` and `pencil-steep-angle-cpl` flagged as the two
whose acquittals are one-legged. The verdict in section 9 is unchanged and is
slightly strengthened.

## 15. The mid-scale ring axis, adjudicated

`docs/research/V-RIM-verification.md` and `experiments/V-RIM/logs/summarise.log`
report a 0-140 px ring window with a 170-300 px null and **RING on 5 of 14**.
Different scale, different estimator; section 9 does not reach it. Four tests.

**INPUT PATH -- the worst defect on this axis.** `experiments/V-RIM/src/render_all.ps1`
line 3 renders the axis's own inputs to `C:\dev\strehl-out\V-RIM\lin` with
`$exe = C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe`, `--demosaic`,
no `--srgb`. **That is neither the deliverable nor `acceptance/SHIP-V4`.** All
three of `C:\dev\strehl-out\V-RIM`, its `lin` and `json2` subtrees, and the
pinned binary are **gone**; `summarise.py` hardcodes `JS = C:\dev\strehl-out\V-RIM\json2`
and cannot run. The published mid-scale result is **not reproducible from its
own artifacts by anyone**.

**RE-RUN.** The instrument imported unchanged from `experiments/V-RIM/src` and
pointed at every render that survives:

| subject | published (1cacb61, linear) | deliverable | SHIP-V4 | deliverable, curve undone |
|---|---|---|---|---|
| `bee-3-cpl` | +4.48% @29 RING | +0.06% @89 no ring | +0.07% @96 no ring | +0.40% @21 no ring |
| `flower-bud-alone-cpl` | +3.18% @22 RING | +0.04% @98 no ring | +0.04% @113 no ring | +0.13% @109 no ring |
| `flower-bud-with-background-fern-cpl` | +9.76% @21 RING | +0.12% @116 no ring | +0.09% @115 no ring | +0.28% @127 no ring |
| `lavendar-cpl` | +2.93% @22 RING | +0.80% @77 no ring | +0.63% @67 no ring | +0.76% @87 no ring |
| `coffee-bean` | +7.13% @34 RING | +1.82% @84 no ring | +1.76% @83 no ring | +0.06% @132 no ring |

Fifteen measurements, **zero RING**. Two independently produced current renders
agree with each other to within 15% and disagree with the published table by
25x to 80x.

**COLOUR SPACE, the matched control that arm needed.** `acceptance/SHIP-V4`'s
own provenance file states

> `colour space  : sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY`

and `ORCH-FAITHFUL/faithful` matches it to **0.02%** on the green channel over
515k samples, so the deliverable is in that same encoded space. The published
run measured camera-linear. Undoing the curve and re-running is the fourth
column above: it moves `bee-3-cpl` from +0.06% to +0.40% and puts its peak back
at t=21 px, where the published run found t=29 -- so a small feature is in the
same place -- but it is still **11x short** of the published amplitude and still
no ring.

**SPECIFICITY.** Build a curve with no ring in it: the subject's own far-field
fluctuation (t=150-300, linearly detrended) transplanted over the whole grid on
a monotone rise, so ring window and null window are treated identically.

| subject | real | rim-free | detections |
|---|---|---|---|
| `bee-3-cpl` | +0.06% | +0.15% | 0/48 |
| `flower-bud-alone-cpl` | +0.04% | +0.14% | 0/48 |
| `flower-bud-with-background-fern-cpl` | +0.12% | +0.13% | 0/48 |
| `lavendar-cpl` | +0.80% | +1.10% | 0/48 |
| `coffee-bean` | +1.82% | +4.77% | 0/48 |
| `bee-1-cpl` | +0.78% | +1.06% | 0/48 |
| `bee-2-cpl` | +0.96% | +0.77% | 0/48 |
| `109MSDCF` | +5.72% | +6.60% | 0/48 |
| `119MSDCF` | +0.19% | +1.56% | 0/48 |

**The ratio rule is sound** -- 0 of 432 false detections -- and this is where
the mid-scale axis differs from the tight-scale one. But **8 of 9 subjects read
at or below what their own backdrop fluctuation produces with no ring present**,
so on the deliverable there is nothing there to detect and the detector
correctly says so.

I predicted before running that `ringstat.dip`'s recovery gate would favour the
ring window, because `tail = med[b:]` runs to the end of the grid rather than
the end of the window, giving a ring-window pair a 160-point tail and a
null-window pair as few as none. **That prediction is refuted.** On correlated
noise with no ring the ring/null ratio is 1.01x to 1.21x and the 3x rule fires
0/200, 0/200, 1/200 and 13/200 at correlation lengths 1, 2, 4 and 8 px.

**A DEFECT IN MY OWN FIRST SPECIFICITY ARM, withdrawn.** The first version put
the transplanted fluctuation inside the ring window only, leaving the null
window perfectly smooth, and duly printed 24/24 detections. Those detection
rates were an artifact of my construction and are withdrawn; the corrected arm
is the table above. The ring amplitudes from that first run were unaffected and
agree with the corrected ones to 0.15 points.

**PIXELS.** `D:\strehl-out\V-RIM\pics\midscale-*.png`. At a stretch of +/-2% of
the far field, the published +3% to +10% band at 21-34 px would be saturated
white. There is nothing there on any of the three renders. The boundary crops
show the backdrop next to the silhouette is **darker** than the far field, not
brighter -- a moat, the opposite sign to a halo -- recovering over 60-90 px.

**VERDICT ON THE MID-SCALE AXIS.** It does not convict the deliverable, and its
published conviction of five subjects cannot be reproduced on any render that
exists. What I cannot rule out is that the vanished 1cacb61 render genuinely
carried a ring that the shipping render does not; the binary and the images are
both deleted and that hypothesis is now untestable. Either way it is **not a
print blocker for the deliverable**.

## 16. A third defect in the tight-scale axis

`rimaxis.py:52` sets `SEAL_DIR` to `acceptance/SHIP-V4`. That directory's own
provenance files say `colour space : sRGB, TONE CURVE APPLIED -- DO NOT MEASURE
NUMERICALLY`, and every subject there was rendered with `--auto-exposure`, so
each master sits at a different place on that curve. The thirteen were produced
by measuring, numerically, a set of images whose own provenance record forbids
it in capital letters.

The direction of the error is not the one that would rescue the thirteen. The
sRGB curve is concave, so the encoded edge step grows faster than the encoded
shoulder texture and the normalised shoulder sd is **compressed** by the
encoding. Measured in linear light the max-of-six pedestal would be larger, not
smaller, and the false FAILs would be worse. This is stated as a direction from
the shape of the curve; I did not re-run the tight-scale axis in linear light,
and it belongs on the list of things I could not measure.

## 17. What part two could not measure

- **`coffee-bean`'s 4.4-point excess over its rim-free pedestal.** Measured, not
  explained. The heavy-tail hypothesis is refuted. Its acquittal rests on the
  pixels and the never-stacked captures alone.
- **The tight-scale axis in linear light.** Section 16 argues the direction from
  the shape of the curve, not from a measurement.
- **Whether the vanished 1cacb61 render carried a real mid-scale ring.** Binary
  and images both deleted. Untestable now, and it is the one hypothesis that
  would make the published mid-scale result correct as written.
- **The dark arm as a symmetry control.** `dark/bright` runs 0.11 to 1.75 across
  the thirteen against 1.04 on the rim-free synthetic, which looks like strong
  bright-side asymmetry -- but the subjects with the smallest ratios are exactly
  the ones whose edges are so wide that the dark window `t = -7..-2` is still on
  the rising edge (`q` already 0.12 to 0.26 at `t = -2`). Window placement
  explains it mechanically. **Inconclusive, reported as such.**
- **The four REFUSED subjects, on either axis.**

## 18. What would falsify part two

- **A rim-free sharp image at shoulder sd 0.19-0.21 reading below +29%.** That
  would put `coffee-bean` back above its pedestal by more than 4.4 points and
  make it a candidate defect rather than a one-legged acquittal.
- **A visible band in the LEFT (unstretched) panel of `ship-112MSDCF-stack.png`
  or `ship-113MSDCF-stack.png`.** Section 14 downgraded both to artifact on a
  statistical argument; a human seeing the band overturns that immediately.
- **A bright band at 21-34 px in any `midscale-*-profile.png` strip.**
- **Any re-render at commit `1cacb61` reproducing +9.76% on
  `flower-bud-with-background-fern-cpl`.** That would establish the published
  mid-scale result and turn section 15 into a claim about a regression that was
  fixed rather than a result that was wrong.
- **A demonstration that `np.maximum.accumulate` is the wrong monotone baseline
  in the mid-scale specificity arm.** It is a valid non-decreasing curve, but it
  is not the least-squares one, and a different choice could move the rim-free
  numbers.
