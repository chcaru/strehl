# V-bestframe: does any input frame carry detail the merge lost?

**Verdict: H1.** `flowers-cpl` is capture-limited, not software-limited. Measured
with an instrument that shares no code with `strehl`, the best single input frame
holds detail above that subject's own fixed-pattern floor in **48 of 352 tiles
(13.6%)**, against **222 of 352 (63.1%)** for the calibration subject
`bee-1-cpl`. On the tiles that do hold frame detail the merge is **at or above
the best single frame in 83.3%** of them, median amplitude ratio **1.414**. The
merge is not losing detail the frames contain; the frames largely do not contain
it. At the six lowest-detail tiles the band energy is flat across all 36 sampled
frames, with no frame spiking anywhere in the stack.

The qualification, stated up front because it is real: in **2 of 352 tiles** the
merge is measurably softer (ratio 0.705 and 0.709) than frame `k=0`, the
least-warped frame in the stack. That is discussed in section 7 and it is not
subject-specific.

The 26-subject survey in section 11 sharpens this rather than merely extending
it. `flowers-cpl` is **not** the worst subject on the roster: four rank below it
and `109MSDCF` loses in 95.5% of its detail tiles. But those subjects have 193 to
246 detail tiles where `flowers-cpl` has 48, so `flowers-cpl` is not a member of
that class. The survey also found a real defect on **other** subjects with a
mechanism in the merge's own log, and two defects in my own instrument that
appeared only when it was extended past the two headline subjects. Both are
reported in section 11.

**Section 12 answers a separate question and carries a ship blocker.** Re-run on
`SHIP-V1`, the deficits of section 11 **do not vanish**: `109MSDCF` holds at
4.5%, `119MSDCF` at 23.1%, and the count of tiles below 0.8 summed across the 24
ranked subjects moves **299 -> 338**, the wrong way. It also establishes that the
comparison could not have tested the backend flip, because
`GALLERY-FIXED-SRGB` was **already** a pyramid render.

**Section 13 answers BUILD-SHARP 21.6 and concedes half of it.** This
instrument's reference arm IS the unwarped original, so the merge does pay
resamples the frame does not, exactly as alleged. But the FINE band peaks at
f = 0.153 cyc/px, below BUILD-SHARP's lowest tabulated row. Measured at the
gather's **real half-resolution CFA plane geometry** the handicap is
**1.06x-1.16x**, not 1.43x. It moves `109MSDCF` from 4.5% to **22.8%** and the
pooled rate from 84.7% to 91.8%. **The deficit survives the correction**, and
the decisive reason is that the handicap does not track it:
`Spearman = +0.096, p = 0.821`, with three subjects reading 100.0% while paying
a **larger** handicap than `109MSDCF` pays.

---

## 1. What was asked and what would answer it

H1 said the bracket does not span the subject's depth, so those regions are out
of focus in every frame and the merge cannot invent them. H2 said some frame does
resolve them and the merge lost it. The discriminator is direct: **does any input
frame carry detail where the merge does not?**

An instrument that shares code with the thing it audits cannot find a fault in
that shared code, so the frame side is built in Python against `rawpy 0.27.0`,
decoding the ARWs directly. Nothing routes through `strehl` or `blend-render`.
The merge side is necessarily the rendered TIFF, read with `tifffile` and an
immediate `uint16` assert.

## 2. The first answer was wrong, and catching it is the main result

The obvious statistic — per-tile band-pass RMS of the merge against the maximum
over sampled frames — returned **merge below best frame in 88.64% of tiles** on
`flowers-cpl`, median ratio 0.200. That reads as a flat H2 and it is false.

Two facts killed it:

1. In the mush tiles the frame achieving the maximum was `k=175`, `k=155`,
   `k=145` — the **most defocused frames in the stack**. A maximally out-of-focus
   frame cannot hold the most detail. The statistic was ranking noise.
2. In the tiles that do have detail the same statistic put the merge **above**
   the best frame (348.87 against 289.15 DN, 399.84 against 291.22 DN).

A single frame's band-pass energy is dominated by sensor noise, and the merge
averages it away. Comparing the two raw hands every empty tile to the frames. The
number was measuring the noise advantage of averaging, backwards.

## 3. The instrument that replaced it

Two frames adjacent in the stack carry the same scene one focus step apart and
**independent** sensor noise. Per tile, after an integer-only shift alignment:

```
signal power  ~  Cov(b_k, b_k+1)      independent noise has zero expectation
noise power   ~  Var(b_k) - Cov
```

Alignment is integer-only on purpose. Sub-pixel resampling would add blur to the
exact quantity being measured, and only to the frame arm.

Tiles are a **uniform 22 x 16 grid over the whole frame**, 352 tiles, chosen
before any measurement and never feature-selected in either direction.

Neither arm is ever resampled for measurement. `blend-render` shrinks the field
so every frame covers every output pixel, so the merge is magnified by `1/s`
relative to a frame, and focus breathing makes `s` a function of frame index
(measured on `flowers-cpl`: 0.9925 at `k=0` falling to 0.9000 at `k=175`).
Instead of warping either image, the frame-side band radii are multiplied by
`s_k` so both arms probe the same **physical** scale on their own native grid.

## 4. Commissioning: the instrument was made to fail before it was believed

| check | what it plants | result | verdict |
| --- | --- | --- | --- |
| C1 identity | a frame against itself | `Cov/Var` median, min and max all `1.000000`; shift 0 in 352 of 352 tiles | PASS |
| C2 known split | signal plus noise of equal amplitude, truth 0.500 | recovered **0.4986** | PASS |
| C3 pure-noise null | two independent noise fields, no signal at all | `Cov/Var` **0.00995**; at zero shift `+0.00026` | PASS |
| C4 sub-pixel cost | one arm shifted by half a pixel | `Cov/Var` **0.8126** | quantified |
| C5 fixed pattern | frames 60 apart, scene displaced, read at **zero shift** | **18.58 DN** (flowers), **16.26 DN** (bee-1) | see below |

**C3 is the check that matters most**: the estimator returns essentially zero
when there is nothing there, so the best-of-441-shifts pick buys only 1% of
variance. C4 says the frame-arm numbers are a **lower bound** loose by at most
19%, which biases against the frame and therefore toward H1; it is divided out,
inflating the frame arm, which is the conservative direction for this verdict.

**C5 found a real defect in my own first estimator.** Two adjacent exposures
share more than scene: they share sensor fixed-pattern noise — PRNU, dark-signal
non-uniformity, hot pixels, and the demosaic maze keyed to the Bayer grid. All of
it sits in **sensor** coordinates and is identical between exposures, so
covariance counts it as signal. Taking frames 60 apart displaces the scene by a
median of 86 px through focus breathing while the fixed pattern stays put:

| subject | scene displacement | cov at **zero shift** | cov at best shift | median &#124;shift&#124; |
| --- | --- | --- | --- | --- |
| flowers-cpl | 20 to 170 px | **18.58 DN** | 18.62 DN | 0.0 px |
| bee-1-cpl | 20 to 189 px | **16.26 DN** | 17.06 DN | 0.0 px |

The floor survives an 86 px scene displacement and stays pinned at zero shift. It
is sensor-locked, it is not scene detail, and it is measured **per tile** so it
can be subtracted per tile.

### The plant

| plant | tiles with detail to lose | detected | false positives | verdict |
| --- | --- | --- | --- | --- |
| bee-1, sigma 2.0, tiles [4:10, 6:14] | 47 | **47** | 1 of 203 = 0.5% | PASS |
| bee-1, sigma 0.8, same tiles | 47 | **0** | 1 of 203 = 0.5% | **FAIL** |
| flowers, sigma 2.0, same tiles | **2** | **2** | 0 of 47 = 0.0% | PASS |

The sigma 0.8 row is reported because it failed. Median ratio inside the plant
moved 2.362 to 2.024, a 14% response, below the 30% flag. **The instrument's
detection limit lies between sigma 0.8 and sigma 2.0**, so a softening gentler
than that would not be caught, and nothing here should be read as excluding one.

The flowers row is itself evidence for H1: in the region called mush, **46 of the
48 planted tiles had no detail to lose**. A heavy blur planted there is
unmeasurable because there is nothing there to blur.

## 5. The measurement

Frames read, labelled as the bounds they are: **20 of 176** for `flowers-cpl` and
**20 of 299** for `bee-1-cpl` (10 adjacent pairs each), reducing to 12 each under
the registration gate of section 6. A separate 36-frame sweep per subject
supplied the per-frame diagnostic in section 8.

Both subjects, binned by how much detail the best frame actually holds, in units
of that subject's own measured fixed-pattern floor:

| best-frame SNR | bee-1 n | bee-1 merge/frame | flowers n | flowers merge/frame |
| --- | --- | --- | --- | --- |
| 0.50 to 0.75 | 22 | 0.297 | 1 | 0.480 |
| 0.75 to 1.00 | 28 | 0.271 | 22 | 0.576 |
| 1.00 to 1.50 | 21 | 0.173 | 135 | 0.549 |
| 1.50 to 2.00 | 16 | 0.230 | 118 | 0.426 |
| 2.00 to 3.00 | 13 | **4.021** | 27 | 0.419 |
| 3.00 to 5.00 | 32 | 3.403 | 14 | **1.847** |
| 5.00 to 8.00 | 30 | 3.263 | 22 | 1.475 |
| 8.00 and above | 188 | 2.210 | 13 | 1.195 |

**The two curves have the same shape.** Below a crossover at SNR 2 to 3 both
subjects read merge/frame around 0.2 to 0.6; above it both read 1.2 to 4.0. In
the low-SNR regime the control subject — the one that is excellent, that resolves
individual ommatidia — reads **0.17 to 0.30**, *worse* than flowers' 0.43 to
0.58. That regime is two different noise floors being compared, in both subjects.
It is an instrument artifact and not a defect in either.

What actually separates the subjects is **how many tiles sit above the
crossover**, which is a property of the capture:

| | frames on disk | frames read | detail tiles (SNR >= 3) | merge >= best frame | median ratio | H2 candidates |
| --- | --- | --- | --- | --- | --- | --- |
| bee-1-cpl, ungated | 299 | 20 | 250 of 352 = 71.0% | 98.8% | 2.370 | 2 (0.8%) |
| bee-1-cpl, gated | 299 | 12 | 222 of 352 = 63.1% | **99.5%** | 2.719 | **0** |
| flowers-cpl, ungated | 176 | 20 | 49 of 352 = 13.9% | 81.6% | 1.379 | 3 (6.1%) |
| flowers-cpl, gated | 176 | 12 | 48 of 352 = **13.6%** | **83.3%** | 1.414 | 2 (4.2%) |

### The deficit in absolute terms, and its distribution

A mean would hide exactly the localised failure this was sent to find, so the
shortfall is given as percentiles over tiles in DN of fine-band amplitude.
Negative means the merge is **ahead**.

| | detail tiles | merge behind | frame minus merge, p05 | p50 | p95 | worst single tile |
| --- | --- | --- | --- | --- | --- | --- |
| bee-1-cpl, gated | 222 | 1 (0.5%) | -1025.9 DN | **-433.3 DN** | -67.3 DN | 6.2 DN behind |
| flowers-cpl, gated | 48 | 8 (16.7%) | -171.7 DN | **-53.7 DN** | +28.3 DN | **43.0 DN behind** |

On `flowers-cpl` the median detail tile has the merge **ahead by 53.7 DN**. Among
the 8 tiles where it is behind, the median shortfall is 12.7 DN and the worst
anywhere in the subject is 43.0 DN against a frame detail of 139 DN there — the
30% softening of section 7. `flowers-cpl` does carry a larger worst-case
shortfall than the control (43.0 DN against 6.2 DN), and that is stated rather
than averaged away; it amounts to 8 of 352 tiles, or 2.3% of the image.
## 6. The registration gate, and why it is not selection on the arm under test

Every residual false positive in **both** subjects traced to the same cause.
bee-1's two candidates came from `k=264` (phase-correlation peak 0.759) and
`k=297` (peak 0.660), the worst-registered frames in its stack; flowers' worst
came from `k=155` (peak 0.642). A frame that cannot be registered is contributing
a **different patch of scene** than the merge tile, so the comparison measures
misregistration. Gating pairs at peak 0.80 is a statement about the instrument,
not about detail, and it is applied identically to both arms of both subjects.
**Every number above is reported gated and ungated and the verdict does not turn
on it.**

## 7. The qualification: a real, bounded softening

After gating, `flowers-cpl` retains **2 of 352 tiles** where the merge is
genuinely softer than the best frame: tile (15,1) at ratio 0.705 and tile (11,2)
at ratio 0.709. Both name **frame `k=0`**, at `s=0.9925` — the least-warped frame
in the stack. Inspected at native pixel scale, the same structures are present in
both arms; the merge is modestly lower in fine-scale contrast, not missing
content.

That is what interpolation loss in the alignment warp predicts, and the merge is
resampled while my frame arm is not. **This is a confound I could not remove**,
only bound: it is worth up to roughly 30% of fine-band amplitude in the worst 2
tiles, it points the same way in `bee-1-cpl`, and it is not specific to
`flowers-cpl`. It does not support H2, because H2 requires the merge to have lost
content some frame held, and the content is present in both.

## 8. The frame-side evidence, independent of any ratio

At the six lowest-SNR tiles on `flowers-cpl`, the FINE band RMS of **every one of
36 sampled frames**, against a fixed-pattern floor of 18.6 DN:

| tile | merge | k000 | k020 | k040 | k060 | k080 | k100 | k120 | k140 | k160 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (9,21) | 10.3 | 75 | 76 | 76 | 77 | 77 | 76 | 72 | 51 | 52 |
| (15,19) | 12.1 | 76 | 81 | 83 | 88 | 86 | 83 | 85 | 98 | 96 |
| (15,21) | 13.5 | 75 | 74 | 75 | 76 | 75 | 76 | 76 | 81 | 80 |
| (8,19) | 16.3 | 66 | 68 | 72 | 74 | 74 | 78 | 78 | 82 | 79 |
| (13,14) | 8.6 | 73 | 75 | 73 | 75 | 78 | 85 | 79 | 71 | 80 |
| (6,18) | 16.9 | 67 | 67 | 70 | 73 | 74 | 72 | 67 | 69 | 56 |

**Flat.** Under H2 some frame must spike as focus sweeps through. None does. The
66 to 98 DN is the frame's total band energy, of which the covariance measurement
says roughly 94% is noise: across `flowers-cpl` the median per-frame signal
fraction is **0.058 to 0.070**, and only the first frame `k=0` has a p95 signal
fraction (**0.536**) far above the rest. The bracket starts in focus and runs
monotonically out of it.

Looked at directly, the adversarial tile confirms it. Of the three ungated H2
candidates, tile (2,14) — the single worst, the best case H2 has on this subject
— shows a merge that is a smooth gradient and a "winning" frame that is
**visibly pure sensor noise** with no structure at all.

## 9. Confounds checked, and the direction each one pushes

| confound | checked how | direction | resolved |
| --- | --- | --- | --- |
| 16-bit truncation by PIL | every pixel read is `tifffile` or `rawpy` with `assert dtype == np.uint16` on the next line; PIL is used to write JPEGs only | would destroy absolutes | yes |
| single-frame noise inflating the frame arm | replaced RMS with pair covariance; C2 and C3 | was creating a false H2 | yes |
| fixed-pattern noise counted as signal | C5, zero-shift covariance with the scene displaced 86 px | inflates frame arm | yes, subtracted per tile |
| order statistic over frames | frame arm is a max over 10 pairs; C3 bounds the pick bias at 1% of variance | inflates frame arm | bounded |
| magnification and focus breathing | band radii scaled by per-frame `s`; neither arm resampled | would confound scale | yes |
| tone and exposure mismatch | empirical monotone transfer per frame, 48 quantile bins, linear extrapolation past the end bins so highlights are not flattened | either way | yes |
| rawpy encoding curve | measured, not asserted: `output ~ linear**0.6403`, i.e. 1/1.562, over midtones | absorbed by the empirical transfer | yes |
| measurement windows chosen using an arm | uniform 22 x 16 grid fixed before measurement | would be fatal | yes, never feature-selected |
| detection threshold chosen on the subject under test | crossover calibrated on **both** subjects; gate calibrated on the control's known-empty backdrop | would be circular | yes |
| misregistration masquerading as lost detail | section 6 gate, reported both ways | inflates frame arm | yes |
| **merge is resampled, frame arm is not** | section 7 | **favours the frame arm, i.e. toward H2** | **no — bounded, not removed** |
| demosaic mismatch (rawpy AHD vs Malvar-He-Cutler) | not tested | unknown sign at the finest scale | **no** |
| sensitivity below sigma 0.8 blur | plant failed at sigma 0.8 | cannot detect gentle softening | **no** |

Three confounds are unresolved and all three are named above. The first two push
**toward** H2, so they cannot manufacture the H1 verdict; the third means a
softening gentler than the detection limit would be invisible.

## 10. What would have to be true for this verdict to be wrong

The verdict rests on 20 frames of 176. It would be overturned if detail existed
in frames between the sampled anchors and nowhere near them, which focus
continuity makes implausible but which was not measured. It would also be
overturned if the merge and the frames were being compared at different scene
locations, which section 6 addresses but only for pairs that registered well.

It would **not** be overturned by the section 7 softening, which is present on
the control subject too.

---

## 11. Ranked survey: is flowers-cpl alone?

All 26 renders in `GALLERY-FIXED-SRGB` were measured at 6 adjacent pairs, so 12
frames, except the two subjects called out by name and the two headline subjects,
measured at 10 pairs, so 20 frames. **A bound from 12 frames is a bound from 12
frames.** It can only ever say that no sampled frame beat the merge.

### Two defects in my own instrument, found by extending it

Neither affects sections 1 to 10, which rest on `flowers-cpl` and `bee-1-cpl`
alone, but both would have corrupted this table.

**The registration gate was inert.** PowerShell's `*>>` writes UTF-16LE with a
BOM. `peaks.py` read its logs with `read_text(errors="ignore")`, which decoded
that as UTF-8 and produced NUL-interleaved text matching no regex. Every pair
returned a `nan` peak, `keep` was all-true, and the gate removed nothing on all
24 survey subjects while the table header said `peak gate 0.80`. **A gate that
silently passes everything prints exactly like a gate that found nothing to
remove.** Caught because `pkMed` was `nan` for 24 subjects and 0.889 and 0.948
for the two whose logs were written by a different route. Fixed by detecting the
BOM.

**The merge floor was estimated from real signal.** `arms()` sets the merge noise
floor `Fm` to the median of empty tiles, or, if there are fewer than 8, to the
5th percentile of merge band energy. On a subject with detail everywhere that
percentile is not a noise floor, it is the quietest real tile, and subtracting it
removes real signal from the merge arm. It returned a merge floor of 571.8 DN
against a single-frame floor of 20.3 DN on `flat-on-ruler-cpl`. **An average of
79 frames cannot be noisier than one frame**, so that is impossible on its face.
It held on 13 of the 24 measured subjects. The column below labelled `capped`
replaces `Fm` with `min(Fm, F)` per tile, which removes the impossible
over-subtraction but makes the merge arm as strong as physics permits, so
**`capped` is an upper bound on merge performance, not a best estimate.** Both
columns are shown.

### The table

`detail` counts tiles where the best frame holds signal at SNR >= 3 above that
subject's own fixed-pattern floor. It is computed from the frame arm and the
floor alone, the merge never enters it, so it is a property of the capture and is
immune to the merge-floor defect above. `avgFine` is the merge's own reported
fraction of finest-band coefficients where no frame cleared the `--gate 4` noise
gate and it averaged instead of selecting.

| subject | frames | read | detail | capped >= frame | med ratio | tiles < 0.8 | strict >= frame | avgFine |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 109MSDCF | 22 | 12 | 246/352 | 4.5% | 0.86 | 84 | 4.5% | 91.3% |
| 119MSDCF | 33 | 12 | 221/352 | 22.6% | 0.91 | 55 | 22.2% | 84.7% |
| flower-bud-alone-cpl | 205 | 12 | 193/352 | 46.6% | 0.93 | 50 | 43.5% | 86.0% |
| flower-bud-with-background-fern-cpl | 299 | 12 | 202/352 | 68.8% | 1.84 | 52 | 68.3% | 66.1% |
| **flowers-cpl** | 176 | 12 | **48/352** | **83.3%** | 1.41 | 2 | 83.3% | 94.5% |
| flat-on-ruler-cpl | 79 | 12 | 352/352 | 86.4% | 2.09 | 0 | invalid | 0.1% |
| dry-erase-marker-head-cpl | 299 | 10 | 143/352 | 86.7% | 3.01 | 16 | invalid | 54.8% |
| wrapped-text-2 | 120 | 12 | 271/352 | 87.1% | 2.49 | 13 | invalid | 32.3% |
| tweezers-cpl | 100 | 12 | 204/352 | 89.7% | 3.25 | 2 | 89.7% | 47.9% |
| pencil-steep-angle-cpl | 299 | 8 | 75/352 | 90.7% | 2.38 | 6 | 90.7% | 64.2% |
| coffee-bubbles | 19 | 12 | 352/352 | 92.0% | 1.28 | 2 | invalid | 82.7% |
| leaf-2-cpl | 182 | 10 | 195/352 | 93.3% | 2.24 | 4 | invalid | 76.0% |
| lavendar-cpl | 299 | 8 | 105/352 | 95.2% | 4.14 | 5 | 95.2% | 67.9% |
| pencil-flatter-angle-cpl | 299 | 8 | 72/352 | 95.8% | 2.84 | 3 | 93.1% | 62.2% |
| **lead-1-cpl** | 123 | 20 | 329/352 | **97.0%** | 1.80 | **0** | invalid | 72.4% |
| 113MSDCF | 63 | 12 | 351/352 | 97.7% | 1.52 | 0 | invalid | 47.9% |
| wrapped-text-1 | 130 | 12 | 285/352 | 97.9% | 3.71 | 0 | invalid | 7.6% |
| bee-2-cpl | 299 | 8 | 194/352 | 97.9% | 3.48 | 3 | invalid | 49.7% |
| bee-3-cpl | 299 | 8 | 210/352 | 98.1% | 3.55 | 2 | invalid | 36.3% |
| coffee-bean | 105 | 12 | 227/352 | 98.7% | 2.17 | 0 | 98.7% | 38.5% |
| flower-inner-edge-cpl | 299 | 6 | 168/352 | 99.4% | 3.25 | 0 | invalid | 58.6% |
| **bee-1-cpl** | 299 | 12 | 222/352 | **99.5%** | 2.72 | **0** | 99.5% | 41.5% |
| 112MSDCF | 79 | 12 | 348/352 | 100.0% | 1.61 | 0 | invalid | 61.2% |
| couch-fibers-cpl | 299 | 8 | 177/352 | 100.0% | 2.82 | 0 | invalid | 49.8% |

Partition, so that a skipped subject cannot read as a passing one:

| outcome | n |
| --- | ---: |
| rendered on disk | 26 |
| measured and ranked above | 24 |
| NOT MEASURABLE | 2 |
| **partition sums to** | **26** |

The two that are not measurable are named, with the reason, in the next section.
Neither is reported as passing.

### flowers-cpl is not the worst subject, and that sharpens the verdict

Four subjects rank below `flowers-cpl` and one of them, `109MSDCF`, is worse by
an order of magnitude: the merge loses in 95.5% of its detail tiles at a median
ratio of 0.86. So `flowers-cpl` is not the visible member of a class of merge
failures. **It is not in that class at all.**

What separates it is the merge-independent column. `flowers-cpl` has **48 of 352
detail tiles**. The next lowest among ranked subjects is 72, and every subject
that ranks below it has 193 to 246. Its frames contain roughly a quarter as much
resolvable detail as the nearest subject and a fifth as much as its neighbours in
the ranking. **That is H1 stated in a quantity the merge never touches.**

### A real defect, on other subjects, with a mechanism

The three subjects below `flowers-cpl` show the signature `flowers-cpl` lacks:
plentiful frame detail and a merge that loses on it. The adversarial render for
`109MSDCF` is `images/FIG4-109MSDCF-all-H2-candidates.jpg`. Unlike the
`flowers-cpl` candidate in section 7, whose winning frame was visibly sensor
noise, these frames show directional filamentary texture that **correlates with
the merge's own large-scale structure** -- the dark comma in tile (2,5) is
present in both arms -- so it is scene content, not noise. Display gain between
the two panels is 1.015, so the comparison is not a stretch artefact.

The mechanism is in the merge's own log. Ranking subjects by `avgFine`:

| group | n | median merge >= frame |
| --- | ---: | ---: |
| avgFine >= 80% | 5 | 46.6% |
| avgFine < 80% | 19 | 97.0% |

Spearman rank correlation between `avgFine` and the merge-beats-frame rate is
**rho = -0.486, p = 0.016** across 24 subjects. Against `detail` it is
rho = -0.334, p = 0.110, not significant, so this is not merely poor subjects
averaging more: **the averaging fraction predicts merge loss beyond what capture
quality explains.** Where the `--gate 4` noise gate finds no frame above the
floor, the merge averages, and averaging a scene that focus breathing displaces
blurs the fine band.

`flowers-cpl` is the outlier above this trend, and consistently so. It has the
**highest** averaging fraction on the roster at 94.5% and still ranks mid-pack,
because it has almost no detail for the mechanism to destroy. **It is maximally
exposed to this defect and largely unharmed by it only because its capture is
poor.** That is worth saying plainly: fixing the gate would not fix
`flowers-cpl`.

This is a new finding, it is outside the H1/H2 question I was asked, and I have
not verified it to the standard of sections 1 to 10. It rests on 12 frames per
subject, one adversarial render, and a rank correlation over 24 points. **It
should be treated as a flagged candidate for its own milestone, not as a
result.**

### The two subjects called out by name

**`highly-angled-ruler-mm-cpl` -- NOT MEASURABLE, and the reason is a finding.**
Its render log has no `coverage` line because it has no warp map: `alignment :
REFUSED -- a tilted subject; a global similarity cannot describe it (M86).
Merging unregistered.` The gallery therefore contains one merge built from
unregistered frames. My C5 control derives scene displacement from the
registration solution, which is degenerate here, so predicted displacement is
identically 0.0 px across all 352 tiles, no tile reaches the 20 px threshold, and
the fixed-pattern floor is undefined. Independently, 8 of its 10 pairs register
below 0.80 with a maximum peak of 0.814, the worst on the roster. **Two
independent signals agree that a frame cannot be put into correspondence with
this merge.** It is not passing and it is not failing; this instrument cannot
speak about it.

**`lead-1-cpl` -- measured, and healthy.** 20 frames read, minimum registration
peak 0.936, 329 of 352 detail tiles, merge at or above the best frame in 97.0% of
them at a median ratio of 1.80, and **zero tiles below 0.8**. Its strict column is
invalid for the merge-floor reason above, but the capped bound and the zero count
of deficient tiles both say the thumbnail-scale worry is not borne out.

**`foam` -- NOT MEASURABLE.** Its fixed-pattern floor reads 0.09 DN against a
7.54 to 30.74 DN family across every other subject, at two separate control gaps
of 60 and 30 frames, so it is not a gap artefact. A floor near zero makes SNR
diverge and every tile read as detail. Cause not established.

### What this section does not establish

The survey does not measure any subject at the depth of sections 1 to 10. It
reads 12 frames of up to 299, it inspects one adversarial render on one subject,
and 13 of its 24 ranked subjects carry only an upper bound on the merge arm. It
is a screen for where to look next, not a verdict on any subject other than
`flowers-cpl`.

---

## 12. SHIP-V1: the deficits do not vanish, and the backend was never the variable

**Verdict on the acceptance invariant: `SHIP-V1` does NOT satisfy "merge >= best
single frame" on detail tiles. The deficits persist essentially unchanged. This
is a ship blocker.**

### First, the premise of the comparison is false

I was asked to test whether the section 11 deficits are an **estimator** defect
that the **pyramid** backend already fixes. They cannot be, because
`GALLERY-FIXED-SRGB` was already rendered by the pyramid backend.

Its driver, `experiments/ORCH-drift-check/galleryfixed.ps1`, carries the comment
`# Arm is the pyramid merge with the hull clamp (verified in ORCH-veiling 32)`,
invokes `blend-render.exe ... --gate 4 --base-mean --chunks 5`, and prints into
every per-subject log `merge : pyramid, hull clamp ON, gate 4, base-mean, sRGB`.
The log header reads `strehl BUILD-BLEND -- LAPLACIAN MULTI-BAND MERGE`.

So this comparison is **pyramid gate 4.0 against pyramid gate 4.5**, plus
lateral-CA correction and `--auto-exposure` in the `SHIP-V1` arm. It does not
test estimator against pyramid in either direction. **The near-identity of the
two tables is what that predicts, and it is not evidence that the backend flip
does nothing, because the backend never changed.**

### Instrument comparability, since the previous numbers predate two fixes

The `GALLERY-FIXED-SRGB` numbers in section 11 were **already** produced with
both fixes in place. The registration-gate fix is visible in that table's `gt`
column, which is non-zero on 11 subjects; under the UTF-16 defect it was zero on
all 24. The merge-floor defect is handled by the `capped` column, which both
sections use. So the two runs are like-for-like and no re-run was required.

To point the instrument at a second gallery I added a `VBF_GAL` / `VBF_OUT`
environment override defaulting to the existing literals. **That change was
commissioned rather than assumed inert**: `ctrl_patch.py` re-measured `109MSDCF`
from `GALLERY-FIXED-SRGB` with the patched code and compared every array in the
output against the pre-patch file.

| array | shape | result |
| --- | --- | --- |
| `S` | (6, 16, 22) | identical |
| `N` | (6, 16, 22) | identical |
| `merge_tiles` | (16, 22, 3) | identical |
| `anchors`, `band`, `n_on_disk`, `ye`, `xe` | -- | identical |
| **arrays differing** | | **0** |

Both galleries are then read through the **same** `curve.arms`, reloaded under a
swapped environment, so they cannot be measured by different code. Depths and
control gaps were matched subject by subject.

One change to a reporting gate was forced by the data. `SHIP-V1` uses
`--auto-exposure` with per-subject gains from 0.807x to 13.548x, so an absolute
floor band in DN is not comparable across galleries. The band is now taken
relative to each gallery's own median floor. Those medians came out at
**17.65 DN** and **17.62 DN**, so in practice the gate did not move.

### A third silent fallback, found while doing this

`arms()` abandons the registration gate when fewer than 2 pairs would survive,
leaving `ngate = 0`. **That prints identically to "the gate found nothing to
remove."** `flower-bud-with-background-fern-cpl` has 5 of its 6 pairs below the
0.80 threshold and reported `gt = 0` in section 11. It is now printed as `SKIP5`
and counted on its own line in both tables. It is the only subject affected, in
either gallery.

### B. SHIP-V1, worst first

| subject | frames | read | floor | detail | merge >= frame | med ratio | p05 | tiles < 0.8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **109MSDCF** | 22 | 12 | 18.22 | 245/352 | **4.5%** | 0.86 | 0.436 | **84** |
| **119MSDCF** | 33 | 12 | 16.88 | 221/352 | **23.1%** | 0.91 | 0.476 | **55** |
| **flower-bud-alone-cpl** | 205 | 12 | 10.94 | 193/352 | **43.5%** | 0.82 | 0.609 | **91** |
| flower-bud-with-background-fern-cpl | 299 | 12 | 13.77 | 202/352 | 70.3% | 1.90 | 0.321 | 52 |
| **flowers-cpl** | 176 | 12 | 18.57 | 48/352 | 83.3% | 1.44 | 0.841 | 2 |
| dry-erase-marker-head-cpl | 299 | 10 | 11.02 | 144/352 | 86.8% | 3.25 | 0.354 | 16 |
| flat-on-ruler-cpl | 79 | 12 | 20.20 | 352/352 | 86.9% | 2.13 | 0.945 | 0 |
| wrapped-text-2 | 120 | 12 | 20.06 | 272/352 | 88.2% | 2.52 | 0.833 | 11 |
| pencil-steep-angle-cpl | 299 | 8 | 17.31 | 75/352 | 90.7% | 2.38 | 0.423 | 7 |
| coffee-bubbles | 19 | 12 | 7.51 | 352/352 | 91.5% | 1.28 | 0.962 | 2 |
| leaf-2-cpl | 182 | 10 | 28.79 | 195/352 | 91.8% | 2.31 | 0.947 | 4 |
| tweezers-cpl | 100 | 12 | 18.86 | 204/352 | 92.2% | 3.26 | 0.945 | 1 |
| lavendar-cpl | 299 | 8 | 20.48 | 105/352 | 95.2% | 4.14 | 1.342 | 5 |
| **lead-1-cpl** | 123 | 20 | 20.77 | 329/352 | 95.7% | 1.75 | 1.033 | **0** |
| pencil-flatter-angle-cpl | 299 | 8 | 17.62 | 72/352 | 95.8% | 2.86 | 1.018 | 3 |
| wrapped-text-1 | 130 | 12 | 15.92 | 285/352 | 97.9% | 3.79 | 1.106 | 0 |
| bee-2-cpl | 299 | 8 | 18.21 | 194/352 | 97.9% | 3.44 | 1.509 | 3 |
| bee-3-cpl | 299 | 8 | 14.05 | 211/352 | 98.1% | 3.57 | 1.459 | 2 |
| 113MSDCF | 63 | 12 | 20.63 | 351/352 | 98.9% | 1.54 | 1.095 | 0 |
| flower-inner-edge-cpl | 299 | 6 | 10.73 | 168/352 | 99.4% | 3.20 | 1.474 | 0 |
| 112MSDCF | 79 | 12 | 30.84 | 348/352 | 99.4% | 1.62 | 1.107 | 0 |
| **bee-1-cpl** | 299 | 12 | 16.25 | 222/352 | 99.5% | 2.76 | 1.310 | 0 |
| coffee-bean | 105 | 12 | 13.56 | 227/352 | 99.6% | 2.23 | 1.144 | 0 |
| couch-fibers-cpl | 299 | 8 | 25.24 | 179/352 | 100.0% | 2.81 | 1.397 | 0 |

Partition, identical in both galleries:

| outcome | n |
| --- | ---: |
| rendered on disk | 26 |
| measured and ranked | 24 |
| NOT MEASURABLE | 2 |
| **partition sums to** | **26** |

### C. Paired diff, the three worst rows first

| subject | >= frame G | >= frame S | delta | med G | med S | < 0.8 G | < 0.8 S |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **109MSDCF** | 4.5% | 4.5% | **+0.0** | 0.86 | 0.86 | 84 | 84 |
| **119MSDCF** | 22.6% | 23.1% | **+0.5** | 0.91 | 0.91 | 55 | 55 |
| **flower-bud-alone-cpl** | 46.6% | 43.5% | **-3.1** | 0.93 | 0.82 | 50 | **91** |
| flower-bud-with-background-fern-cpl | 68.8% | 70.3% | +1.5 | 1.84 | 1.90 | 52 | 52 |
| flowers-cpl | 83.3% | 83.3% | +0.0 | 1.41 | 1.44 | 2 | 2 |
| tweezers-cpl | 89.7% | 92.2% | +2.5 | 3.25 | 3.26 | 2 | 1 |
| leaf-2-cpl | 93.3% | 91.8% | -1.5 | 2.24 | 2.31 | 4 | 4 |
| lead-1-cpl | 97.0% | 95.7% | -1.2 | 1.80 | 1.75 | 0 | 0 |
| bee-1-cpl | 99.5% | 99.5% | +0.0 | 2.72 | 2.76 | 0 | 0 |
| couch-fibers-cpl | 100.0% | 100.0% | +0.0 | 2.82 | 2.81 | 0 | 0 |

Across all 24 subjects ranked in both:

| quantity | value |
| --- | --- |
| median delta in merge >= frame | **+0.0 pp** |
| range of delta | -3.1 pp to +2.5 pp |
| subjects improved | 10 of 24 |
| subjects worsened | 5 of 24 |
| subjects unchanged | 9 of 24 |
| **tiles below 0.8, summed** | **299 -> 338** |

**The total count of deficient tiles got worse, not better**, driven by
`flower-bud-alone-cpl` going from 50 to 91. No subject that failed the invariant
in `GALLERY-FIXED-SRGB` passes it in `SHIP-V1`.

### The evidence, since the deficits persist

`V-BESTFRAME-SHIP/images/FIG4-109MSDCF-all-H2-candidates.jpg` is the 100%
side-by-side on `SHIP-V1`, merge against the frame that beat it, identical tile
coordinates, display gain matched at 1.015. It selects the **same** tiles as the
`GALLERY-FIXED-SRGB` render and the **same** frame.

| tile | ratio | SNR | winning frame |
| --- | ---: | ---: | --- |
| (1,5) | 0.000 | 3.31 | `k=8` `DSC00017.ARW` |
| (2,5) | 0.000 | 3.15 | `k=8` `DSC00017.ARW` |
| (3,6) | 0.053 | 3.07 | `k=8` `DSC00017.ARW` |
| (2,6) | 0.079 | 3.53 | `k=8` `DSC00017.ARW` |

The merge panels are smooth gradients. The frame panels carry directional
filamentary texture that **correlates with the merge's own large-scale
structure**, so it is scene content and not sensor noise: the dark comma in tile
(2,5) is present in both arms.

### The two kept explicitly visible

**`highly-angled-ruler-mm-cpl` -- still NOT MEASURABLE in `SHIP-V1`.** Predicted
scene displacement is again identically 0.0 px across all 352 tiles, which
reproduces the signature of an unregistered merge. `SHIP-V1` ships one merge
built from unregistered frames.

**`foam` -- still NOT MEASURABLE in `SHIP-V1`**, and slightly further out: its
fixed-pattern floor reads 0.00 DN against a gallery median of 17.62 DN. Cause
still not established.

### What I did not test, and what must not be claimed

**The backend flip is untested.** Nothing in this section compares estimator
against pyramid, because neither directory contains an estimator render. **The
sentence "the backend flip is the fix" is not supported by anything measured
here**, and the persistence of every deficit across a gate, CA and exposure
change makes it less likely rather than more. Testing it requires an estimator
arm rendered on the same subjects.

Three things also remain untested: whether the deficit survives at more than 12
frames per subject; whether it is present on `109MSDCF` at a finer tile grid; and
whether the section 11 mechanism, the finest-band averaging fraction, explains it
in `SHIP-V1`, because the `SHIP-V1` render log records only exposure and does not
report `averaged`, `coverage` or `alignment` per subject. **That missing
per-subject provenance is itself worth fixing before ship.**

## 13. The path-boundary objection: correct in kind, twenty times too small

BUILD-SHARP 21.6 asks one question of this instrument and it is the right one.
I answer it first, without hedging.

### 13.1 The reference arm is UNWARPED. The objection's premise is CORRECT.

`bestframe.py` says so itself, in capitals, in its own module docstring:

> NEITHER SIDE IS EVER RESAMPLED FOR MEASUREMENT. Resampling destroys exactly
> the high-frequency content under test. Instead the band radii on the frame
> side are multiplied by s_k, so both sides probe the same PHYSICAL scale on
> their own grid.

The mechanism is in `paircov.py`. `band_of` decodes the ARW with `rawpy` and
never resamples it; `pair_tiles` maps each merge tile into the frame's own grid
with `int(round(s0 * ye[i] + t0[1]))`, an integer crop. The only
`map_coordinates` call on the frame side is inside `bestframe.fit_tone`, and it
runs on an 8x boxdown for the tone fit alone, never on the measured band.

So the merge arm pays the alignment gather and the chroma co-site, and the frame
arm pays neither. **The two arms do sit on opposite sides of a path boundary.**
That is the same error class BUILD-SHARP found in the ESF instrument, I did not
price it, and the objection is well founded.

What does not follow is the magnitude.

### 13.2 The quoted figure is for a band this instrument does not measure

BUILD-SHARP prices f = 0.25, 0.35 and 0.50 cyc/px. The FINE band here is
`DoG(1.0, 2.0)`, whose amplitude response peaks at

    f = 0.1530 cyc/px      (closed form sqrt(ln(s2^2/s1^2) / (2 pi^2 (s2^2 - s1^2))))
    power-weighted f10 / f50 / f90 = 0.1164 / 0.1877 / 0.2799 cyc/px

The band's power-weighted **median** sits below BUILD-SHARP's **lowest**
tabulated row. Catmull-Rom is very flat down there, and the loss is steeply
frequency dependent, so carrying the f = 0.35 figure across is not conservative:
it overstates the handicap by more than an order of magnitude. `1.43x` is a real
number about a real band, and it is not this band.

### 13.3 Identifying the kernel before pricing it

Pricing the wrong interpolator would waste the whole exercise, so the kernel is
identified by reproducing BUILD-SHARP 20.4's plant numbers rather than by
reading the source. `resample_price.py`, phi = 0.5 on both axes:

| f | Catmull-Rom (2-D) | bilinear (2-D) | BUILD-SHARP 20.4 | |
| ---: | ---: | ---: | ---: | --- |
| 0.25 | 0.781250 | 0.500000 | 0.781250 | CR **MATCH** |
| 0.35 | 0.402210 | 0.206107 | 0.402210 | CR **MATCH** |
| 0.50 | 0.000000 | 0.000000 | 0.000000 | CR **MATCH** |

Exact to six decimals on all three, and bilinear is excluded. This also pins
down the convention: BUILD-SHARP's "2-D" column is amplitude **squared**, the
product of the two separable axes. Phase-averaged over uniform phase I get
0.88405 / 0.67426 / 0.39063 against their 0.88986 / 0.69055 / 0.42096; mine are
uniformly **lower**, consistent with their measured histogram having a pile-up
near integers that a flat uniform does not.

### 13.4 Is the modelled gather harsh enough? Yes, harsher than the real one

Retention is monotone in distance-to-integer, so under-sweeping the phase would
under-price the handicap, which is the direction that would let a false deficit
survive. `phasecheck.py` measures the phase my synthetic warp actually produces:

| | mean | p90 | p99 | >0.2 from integer |
| --- | ---: | ---: | ---: | ---: |
| modelled, n = 4688 | **0.2554** | 0.4530 | 0.4950 | 61.3% |
| modelled, n = 7032 | **0.2489** | 0.4490 | 0.4950 | 59.7% |
| real warpmap (BUILD-SHARP 20.2) | 0.2369 | 0.4470 | 0.4942 | 57.3% |

**The model is harsher than the thing it models on every column.** Everything
below therefore over-prices the handicap.

### 13.5 My first attempt priced the wrong geometry. Retracting it.

The version of this section committed as `5f6c7c0` reported a handicap of
**1.02x-1.04x**. **That number is wrong and I withdraw it.** `boundary.py`
applied Catmull-Rom at **full-resolution** pixel spacing to demosaiced luma. The
gather does not run there. `align_cmd.rs` deinterleaves the CFA first:

```rust
for dy in 0..2usize { for dx in 0..2usize {
    let row = (ay + 2 * py + dy) * stride + ax + dx;
    *o = frame.data[row + 2 * px] as f32;          // stride 2: HALF resolution
    ...
    gather_checked(src, t_site, geom, resampler, &mut scratch.dst, ...)
```

Each plane is a single CFA site at half resolution in both axes, so the
interpolator's taps are **2 output pixels apart**, and a structure at `f` cyc/px
in the render sits at `2f` cyc/plane-px, where Catmull-Rom is far weaker. Pricing
it at full-res spacing evaluates the kernel at half the frequency it actually
sees.

Corroborated from the artefact rather than from the code, per ORCH's rule:
BUILD-SHARP 20.2's warpmap geometry is **3516x2344**, exactly half of the
**7032x4688** the gallery writes. The warp is stored in plane units.

| | R (alpha=0) | R (alpha=2) | handicap |
| --- | ---: | ---: | ---: |
| full-res spacing (what I did, **withdrawn**) | 0.9727 | 0.9875 | 1.013x-1.028x |
| **plane spacing (what the code does)** | **0.8267** | **0.9000** | **1.111x-1.210x** |

The same reading confirms ORCH's retraction independently:
`cfa_site_channel(dx, dy)` returns a `Channel` (`optics.rs:449`), not an offset,
and the comment records that with `ca == None`, `t_site` is exactly `t`. **There
is no chroma co-site on this path**, so the align-only column is the right one
and my earlier align+co-site column overstated the chain by a stage.

### 13.6 Measuring it at the right geometry

`cfawarp.py` deinterleaves the real CFA, Catmull-Rom warps each half-res plane at
the swept phase, writes it back into `rawpy`'s own buffer and lets `rawpy`
demosaic. The unwarped arm is the same decode without the warp, so the demosaic
is common-mode and cancels; what remains is the gather alone.

| subject | **R (gather)** | handicap | two serial gathers | predicted R^2 |
| --- | ---: | ---: | ---: | ---: |
| flowers-cpl | 0.8615 | **1.161x** | 0.7846 | 0.7422 |
| flower-bud-alone-cpl | 0.8669 | 1.154x | 0.7979 | 0.7515 |
| couch-fibers-cpl | 0.8773 | 1.140x | 0.8049 | 0.7696 |
| bee-1-cpl | 0.8838 | 1.131x | 0.8140 | 0.7810 |
| 109MSDCF | 0.9188 | 1.088x | 0.8708 | 0.8442 |
| 119MSDCF | 0.9264 | 1.079x | 0.8833 | 0.8582 |
| 112MSDCF | 0.9316 | 1.073x | 0.8912 | 0.8678 |
| flat-on-ruler-cpl | 0.9463 | **1.057x** | 0.9105 | 0.8954 |

**Measured handicap: 1.06x to 1.16x**, median R = 0.9013. Three to four times my
withdrawn figure, and still well below BUILD-SHARP's 1.43x.

**CONTROL, null, 8 of 8.** An identity warp through the identical deinterleave,
gather and reinterleave path: `median 1.000000000  min 1.000000000  max
1.000000000` on all 352 tiles of all eight subjects. Exactly one, not approximately.

**CONTROL, potency, 8 of 8 -- and the first version of this control was inert.**
In `5f6c7c0` the plant was an added constant phase of 0.5. That is useless here:
the base warp already sweeps phase uniformly, and a uniform distribution plus a
constant is still uniform. It moved `109MSDCF` from 0.9188 to only 0.9157 and I
would have been reporting a control that could not fail. Replaced with a
**second serial gather**, which must cost about `R^2`:

    109MSDCF     predicted 0.8442  measured 0.8708  ratio 1.0314  PASS
    flowers-cpl  predicted 0.7422  measured 0.7846  ratio 1.0570  PASS
    (all eight subjects: ratios 1.0169 to 1.0618, all PASS)

All eight land slightly **above** `R^2`, which is the correct sign: the second
gather acts on an already-depleted spectrum. The instrument responds to a
resample and reports the right size.

### 13.7 The demosaic asymmetry, now bounded rather than open

Section 13.8 of `5f6c7c0` listed this as un-ruled-out. It is now measured.
The frame arm decodes with AHD; the gallery log says `blend-render` used
Malvar-He-Cutler. LibRaw does not offer MHC, so `demosaic_spread.py` measures the
spread across the family it does offer, on `109MSDCF`, band amplitude against AHD:

| algorithm | median | p05 | p95 |
| --- | ---: | ---: | ---: |
| LINEAR | 0.9462 | 0.8958 | 0.9945 |
| VNG | 0.9718 | 0.9169 | 1.0223 |
| PPG | 0.9850 | 0.9712 | 0.9979 |
| DCB | 0.9957 | 0.9726 | 1.0162 |
| AAHD | not measured | | |

**5 of 6 attempted, 1 failed:** AAHD raised
`rawpy._rawpy.LibRawUnsufficientMemoryError`. It is not counted as a pass.

MHC is bilinear plus a gradient-correction term, so it cannot sit below LINEAR.
**R_demosaic >= 0.946 is the worst case for the merge**, and every measured
alternative is closer to 1 than that.

### 13.8 Inverting the question, with the corrected numbers

`corrected.py`, capped arm, `GALLERY-FIXED-SRGB`. The last two columns apply each
subject's **own measured** gather retention, and then that times the worst-case
demosaic bound:

| subject | nDet | R=1.000 | R=0.930 | R=0.870 | R=0.800 | **own R** | **own R x demosaic** |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 109MSDCF | 246 | 4.5 | 15.4 | 45.5 | 65.9 | **22.8** | **45.9** |
| 119MSDCF | 221 | 22.6 | 41.6 | 62.9 | 75.1 | **43.0** | **61.5** |
| flower-bud-alone-cpl | 193 | 46.6 | 50.8 | 56.5 | 74.1 | 57.0 | 71.0 |
| flowers-cpl | 48 | 83.3 | 89.6 | 91.7 | 95.8 | 91.7 | 95.8 |
| flat-on-ruler-cpl | 352 | 86.4 | 95.5 | 99.7 | 100.0 | 92.3 | 97.4 |
| bee-1-cpl | 222 | 99.5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 112MSDCF | 348 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| couch-fibers-cpl | 177 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| **POOLED** | **5190** | **84.7** | **88.2** | **91.8** | **94.2** | | |

`SHIP-V1` pooled behaves the same: 84.8 / 88.2 / 91.5 / 93.5.

**The correction matters and it is not decisive.** `109MSDCF` moves from 4.5% to
22.8%, and to 45.9% only if MHC is as soft as bilinear. It still fails. Half its
detail tiles breaking even needs R = 0.863; 95% needs R = 0.456.

### 13.9 Why it cannot be the explanation: the handicap does not track the deficit

This is the decisive test and it needs no assumed value of R at all. If the
deficit were a path-boundary artefact, the subjects with the **largest** measured
handicap would fail **hardest**. Measured, `anticorr.py`:

    Spearman(R_gather, merge>=frame %) = +0.096, p = 0.821   (n = 8)

No relationship, and at the halves it runs the wrong way:

| | R range | median merge>=frame |
| --- | --- | ---: |
| worst-handicap half | 0.8615-0.8838 | **91.4%** |
| gentlest-handicap half | 0.9188-0.9463 | **54.5%** |

`couch-fibers-cpl` carries the third-largest handicap measured (1.140x) and reads
**100.0%**. `109MSDCF` carries the second-**smallest** (1.088x) and reads
**4.5%**. R varies by a factor of 1.098 across these subjects; the pass rate
varies from 4.5% to 100.0%. **A quantity spanning 10% cannot produce a spread
spanning 95 points**, and it does not even order them.

### 13.10 Verdict on the objection

**Correct in kind, and it accounts for part of the effect but not the effect.**
The arms do sit on opposite sides of a path boundary; I did not price it, then
priced it at the wrong geometry, and the corrected handicap of 1.06x-1.16x is
real and should be carried on every number in sections 11 and 12. It lifts the
pooled rate from 84.7% to 91.8% and `109MSDCF` from 4.5% to 22.8%.

It cannot carry the deficit, because the deficit is not distributed the way a
handicap is distributed. Three subjects read 100.0% **while already paying a
larger handicap than `109MSDCF` pays**.

### 13.11 What I still cannot rule out

**Whether MHC is softer than every LibRaw algorithm.** Bounded but not measured:
if MHC were softer than LINEAR the bound in 13.7 breaks. I judge this unlikely
because MHC is bilinear plus a correction, but I have not run MHC.

**The gather's phase on the real warpmaps of these specific subjects.** I use
BUILD-SHARP's `coffee-bean-20` distribution as a stand-in and verified my sweep
is harsher (mean distance-to-integer 0.2489-0.2554 against 0.2369). A subject
whose real warp is nearly integer everywhere would have a smaller handicap than I
assign it, which would make its corrected pass rate lower, not higher.

**Whether `blend-render` gathers exactly as `align_cmd.rs` does.** I read the
deinterleave loop in `align_cmd.rs`. I did not trace `merge_cmd.rs`'s own call
path to the same loop, so "the shipped render uses this gather" rests on it being
the only gather in the crate rather than on a routing trace. **That is precisely
the kind of step ORCH's retraction warns about and I flag it as unclosed.**

**Sub-pixel residual in the frame-pair covariance** and **`SEARCH = 10`
saturation** both bias the frame arm's signal down, flattering the merge, and so
work against the deficit rather than for it.

### 13.12 A question back to BUILD-SHARP about the frequency axis

Given that the gather runs on half-resolution planes, **in which units is the `f`
column of BUILD-SHARP 20.3 and 21.5?** If those are output pixels, the table
evaluates the kernel at half the frequency the plane sees and under-prices the
chain. If they are plane pixels, then `f = 0.35` there corresponds to
`0.175` cyc/output-px and the 1.43x is a monochromatic figure near the top of
this instrument's band rather than across it. The two readings differ by a factor
of two in frequency and it changes their headline, not just mine.

### 13.13 This does not touch the H1 verdict

`flowers-cpl`'s verdict rests on `detail` = 48/352, computed from
`snr = sqrt(Sft / F)`, in which `Sft` is a frame-pair covariance and `F` a
fixed-pattern floor. **The merge never enters that quantity**, so no merge-side
resampling argument can move it. H1 stands exactly as written in section 1.
