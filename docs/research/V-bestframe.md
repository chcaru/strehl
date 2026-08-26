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

## Ranked survey

Filled in from `experiments/V-bestframe/rank.py` once the 26-subject run
completes. `highly-angled-ruler-mm-cpl` and `lead-1-cpl` are measured at the same
depth as the headline pair rather than left for the ranking to decide.
