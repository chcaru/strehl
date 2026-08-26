# BUILD-TRIAGE: which subjects are the merge's fault, and which are the camera's

**Status:** complete. 26 of 26 subjects classified; instrument commissioned
(C1-C8, E1-E5, C9-C11, **C12-C17**). **Headline: the merge is not losing detail
on any subject. Over 75 evidence-bearing sites the merge is behind the best
corrected source frame at exactly one site, on one subject, by 5.2%
(+464.3 DN/px, 0.49 px equivalent, on `bee-1-cpl`) -- below the 0.80 px
threshold and not visible at 1:1. 19 of 26 are GOOD; the 7 that are not are
capture-limited, and only 3 of those have a focus problem at all.** See section
4 for the classification and **section 7 for the corrected arithmetic**.

**Section 7 supersedes the merge-loss arithmetic in section 4.1 and the
`flowers-cpl` mechanism in sections 3 and 4.2.** The best-frame picker was found
to be biased -- twice, in opposite directions, depending on whether it was
normalised by level -- and the edge metric was found to be reading grain as
detail at empty sites. All three defects were fixed and the corpus re-measured.
The headline is unchanged in substance: the corrected estimator independently
reproduces the `bee-1-cpl` deficit to within 0.4% (+464.3 vs +462.6 DN/px) and
raises the evidence-bearing site count from 64 to 75. What changed is that it
now rests on an instrument commissioned against a control with real power,
rather than on one that happened to be right.

Section 6 replaces the coverage detector used in the first pass of this report.
Adopting the per-pixel election map — the instrument recorded in
`docs/captures-needed.md` section 23 — moved **7 subjects out of "coverage gap"
and into GOOD**, because the previous 24-block aggregate was firing on
featureless backdrop rather than on the subject. The counts in section 3 are the
corrected ones.

The owner looked at the shipped 26-subject gallery and called it horrible. The
gallery is not uniformly bad — it is *inconsistent*, and it ships with no
indication of which tile is which. This report classifies every subject, and
every region within a subject, against one question:

> Is this soft because **the merge lost detail the source frames contain**
> (retouch — a bug we fix), or because **no source frame ever contained that
> detail** (reshoot — a capture limit we report)?

Those demand opposite responses, and the project previously could not tell them
apart.

---

## 1. What was measured, and on which side of every transformation

The single most expensive recurring error in this project is comparing two
things that are not on the same side of a transformation. This work compares a
*merge output* against a *source frame*, which is the comparison most likely to
trip it. Every defence is listed here explicitly.

### 1.1 Nothing numeric was taken from the shipped masters

The `SHIP-V1` masters are `--srgb`, i.e. tone-curved. **No number in this report
comes from them.** Both arms were re-rendered from the RAW stacks with the
*pinned binary that produced the masters*
(`C:\dev\strehl-out\ORCH-SHIP\src\target\release\strehl.exe`), in camera-linear
space:

| | arm A (merge) | arm B (source frame) |
|---|---|---|
| command | `stack <dir> --merge pyramid --pyramid-gate 4.5 --linear-srgb --demosaic` | identical, plus `STREHL_ONLY_FRAME=<k>` |
| transfer curve | none | none |
| demosaic | Malvar-He-Cutler | Malvar-He-Cutler |
| lateral CA, colour matrix, black/white points | from the log, identical | from the log, identical |

`--demosaic` is implied by `--srgb` but **not** by `--linear-srgb`; without it
arm A comes back 3516x2344 binned against the masters' 7032x4688. That was
caught in a smoke test before any measurement, not after.

Everything except the merge itself is common-mode. The masters are used only as
pictures, for the contact sheet.

### 1.2 The alignment gather is handled by self-calibration, not by a constant

`STREHL_ONLY_FRAME` truncates the path list *before* alignment, so a one-frame
stack re-solves alignment and lands on an identity warp with coverage
`k = 0.9974` (the 3 px floor), while real merges use their own `k`, measured
across this corpus at **0.8429 – 1.0000** (median 0.9525). The two arms are
therefore *not* on the same side of the gather.

The `k = 1.0000` end is not a rounding artefact and deserves naming, because it
is a subject on which the whole gather correction must be switched off.
`highly-angled-ruler-mm-cpl` is the corpus's only stack where the aligner
*declines* to align: its log states `alignment: REFUSED -- tilted subject; a
global similarity transform inappropriate`, followed by `alignment: OFF --
frames combined unregistered`, and it stacks 299 frames unwarped. Its output is
7040x4688 with no FOV crop, so `k = 1.0`, there is no gather on either arm, and
the correction is correctly a no-op. `tri.read_log()` derives this from the
positive log statement rather than defaulting, and hard-errors if the log does
not say so -- an earlier run stopped outright rather than silently assume a `k`
for it, which is the behaviour wanted.

Arm B is resampled onto arm A's grid with the pipeline's own Catmull-Rom kernel,
which leaves arm B carrying one gather more than arm A. That handicap is **not**
taken from the quoted "1.43x at f = 0.35 c/sample" constant. It is measured, per
subject and per site, by putting **arm A through the identical extra gather on
identical content** and reading the cost off that:

```
cost = statistic(gather(armA_tile)) / statistic(armA_tile)
armB_corrected = statistic(armB_tile) / cost
```

Both raw and corrected values are reported, along with `cost`, for every site.

Two independent estimators of `cost` are computed and cross-checked:

* **phase-averaged shift** (primary) — pure sub-pixel translations at phases
  0.125/0.375/0.625/0.875. A scale gather by `s` sweeps the fractional offset
  uniformly through `[0,1)` with period `1/(1-s)` px — 13.5 px at `s = 0.926`,
  so ~38 full cycles across a 512 px window. Averaging translation cost over
  those phases reproduces that uniform-phase average without magnifying content.
* **exact-`s` rescale** (cross-check) — arm A through the real rescale, read at
  `k·s` so both arms are compared at matched *sensor* frequency.

On well-signalled sites the two agree to ~1% (e.g. bee-1-cpl DETAIL: 0.853 vs
0.865). Where they diverge the site is flagged and the robust estimator is used.

**For the primary metric the gather turns out to be nearly irrelevant**:
commissioning E5 measures its cost on edge slope at **0.9976**. The confound the
brief warned about is real for band amplitude and almost absent for the
statistic actually used.

### 1.3 Bands, where used, are defined in sensor frequency

A merge crops the field of view to `k` and upsamples back, so content is
magnified by `1/k` and a feature of sensor frequency `f` lands at `f·k` cycles
per *output* sample. With `k` spanning 0.8429–1.0000, "0.35 cycles per output
sample" is a different physical frequency in every render; comparing arms at
equal *output* frequency smuggles in a ~1.08x handicap as a band definition.
`tri.band_amp(tile, k)` evaluates at `f·k`, in each arm's own grid, with neither
arm resampled to achieve it.

### 1.4 Absolute levels in DN, always

Every site reports `merge`, `frame` and `frame_corrected` in **DN** (edge slope
in DN/px), plus tile mean, median, sd, and **pixel noise in DN**, not only
ratios. An additive bias is invisible in a ratio and invisible in an error, and
this project has already been bitten by exactly that. In this work the additive
term turned out to be the whole story — see §2.

---

## 2. The instrument, and the two verdicts it reversed

### 2.1 Commissioning caught three defects, two of them in my own code

An uncommissioned instrument and a genuinely null result look identical, so the
instrument was commissioned before it was trusted (`commission.py`,
`commission_shift.py`, `commission_noise.py`, `commission_edge.py`).

1. **Keys-cubic sign error.** The outer taps must be `w0 = a(t³−2t²+t)`,
   `w3 = a(t²−t³)`; both were negated. Weights summed to `1 + 2a(t−t²)` = 1.25 at
   `t = 0.5`, and a constant 1234.5 came back 1691.76 (max 1929 = 1234.5 × 1.25²).
   Fixed, with a partition-of-unity assertion so it cannot recur.
2. **A control that compared displaced content.** A rescale about the centre
   moves a feature at radius `r` by `(1−s)·r` — 3.4 px at `r = 384`, ~75 px at a
   real site radius. Comparing equal *coordinates* after a rescale compares
   different *content*: the project's signature error, inside the instrument
   built to avoid it. Symptoms were a 35% level shift and a mid-band *gain* of
   1.74x, both physically impossible. It recurred once more in the rewritten
   self-calibration (`cost = 1.320` — a blur that amplifies) and was fixed by
   placing the window at the analytic destination `(src − c)/s + c`.
3. **UTF-16 logs read as UTF-8.** PowerShell `>` writes UTF-16LE with a `ff fe`
   BOM. Read as UTF-8 it yields NUL-interleaved mojibake, every pattern misses,
   and the parser returns `{}`. Combined with a `.get(key, default)` fallback
   this would have silently substituted `k = 0.9887` for every subject — a 6%
   error for bee-3-cpl (real `k = 0.9321`) in the exact quantity everything
   rests on. `tri.read_log` now sniffs the BOM, and `require=` makes a missing
   key a hard error. All silent defaults were removed.

### 2.2 The metric had to be replaced, and a crop is what caught it

The first instrument measured **high-band amplitude**. On `119MSDCF` it returned
`merge/source = 0.549` at the merge's best site and `0.256` at another — a
catastrophic-looking merge defect.

**The crop refutes it.** The merge is visibly *sharper*: crisper blue halftone
stipple, finer speckle in the dark band. The source frame's extra high-band
energy is **noise**. A single frame carries full shot and read noise; a pyramid
merge of many frames averages it down. Measured on the same tiles:

| site | merge noise | frame noise | ratio |
|---|---|---|---|
| 119MSDCF DETAIL | 52.4 DN | 71.7 DN | 1.37x |
| 119MSDCF SOURCE-BEST | 32.9 DN | 63.5 DN | 1.93x |

Band amplitude cannot tell detail from noise, and on this corpus that
distinction *is* the question. Commissioning check C8c quantifies the damage: in
the weak-signal regime that actually applies here, **noise alone manufactures a
2.05x false sharpness advantage for the noisier arm.**

The primary metric is therefore **edge slope**: the 99.5th percentile of
gradient magnitude on a 3x3-median-filtered tile, in **DN per pixel**. The
median removes isolated noise excursions while leaving a step edge intact, so
the statistic responds to blur and not to noise.

### 2.3 Commissioning of the replacement metric

| check | result |
|---|---|
| **E1** null — a tile against itself | ratio **exactly 1.000000** |
| **E2** noise immunity — +10 to +160 DN added noise | **0.45%** worst deviation across a 16x noise range |
| **E3** planted Gaussian blur, monotonicity | 0.4 px → 0.993, 0.6 → 0.962, 0.8 → 0.936, 1.2 → 0.882 (monotone) |
| **E3b** blur round-trip in pixels | planted 0.5/0.8/1.2/1.8 px recovered to **±0.01 px**; planted 0.30 px reads 0.21 px |
| **E4** teeth — old metric vs new on the same real pixels | band **0.315** vs edge **0.982**; the two disagree by **3.12x**, and the crop adjudicates for the edge metric |
| **E5** gather cost on this statistic | **0.9976** — the gather confound is nearly absent |

A raw edge-slope ratio is *compressed* (E3: a planted 1.2 px blur reads 0.88), so
quoting it as a percentage would badly understate a defect. Ratios are therefore
converted to an **equivalent Gaussian blur in pixels** by planting known blurs
*on that same tile* and interpolating — the same self-calibration principle used
for the gather. **The instrument's resolution floor is ~0.3 px**; anything at or
below that is reported as at-floor and never as a defect.

### 2.4 Capture-side evidence is measured frame-against-frame only

Two further instruments never touch a merge, so what they report cannot be an
artefact of one:

* **`focuscurve.py`** builds through-focus curves from raw Bayer green planes on
  a 6x4 fractional-coordinate grid. Frames are compared only against other
  frames, inside a single transformation. It yields the best frame per block,
  coverage-gap detection, and *which end* of the bracket is missing.
* **`localmotion.py`** closes a blind spot the first detector had: global phase
  correlation sees only *rigid* translation, which is exactly what the aligner
  removes. It instead exploits the fact that adjacent frames are one focus step
  apart, so structural change between neighbours after low-passing is motion,
  not focus. Validated against both known-motion stacks:

| stack | median adjacent-frame NCC | worst block | blocks < 0.98 |
|---|---|---|---|
| `foam` (known moved) | 0.97944 | 0.91263 | 20 / 24 |
| `coffee-bubbles` (known bubble motion) | 0.94587 | 0.75450 | 20 / 24 |
| `bee-3-cpl` (reference) | **0.99967** | 0.99306 | **0 / 24** |
| `wrapped-text-2` | 0.99950 | 0.99449 | **0 / 24** |

Both positive controls fire; the reference stack is static. `wrapped-text-2`'s
regional blur is **not** motion.

### 2.5 The best-frame pick was biased in the flattering direction

Stage 1 picks the best frame from a coarse ladder (40 of up to 299 frames) over a
768 px window, while stage 2 compares over 512 px. An under-selected "best frame"
makes the source look worse and therefore biases toward certifying the merge
GOOD. `refine_best_frame()` re-searches the neighbourhood at the compare window
and site. It moves the pick and it matters: on `bee-1-cpl` DETAIL it moved frame
46 → 44 and the source's measured sharpness rose from 136.3 to 250.7 DN, taking
`ratio` from 1.90 to 1.04. Every reported figure uses the refined frame, and
`moved_by` is recorded per site so the refinement is auditable.

### 2.6 Corrected aperture census

The brief states "5x f/5.6, 1x f/8, no f/11". Read from EXIF across all 26
stacks, that is wrong:

| marked aperture | subjects |
|---|---|
| f/11 | 3 (`109MSDCF`, `112MSDCF`, `113MSDCF`) |
| f/8 | 3 (`coffee-bean`, `coffee-bubbles`, `foam`) |
| f/5.6 | 20 |

All 26 were shot on the FE 100mm F2.8 Macro GM with a 2x teleconverter at
200 mm. **f/11 is present**, on three subjects, and at this magnification marked
f/11 is optically ~f/33.

---

## 3. Triage table

All 26 subjects. `merge` and `best frame` are edge slope in **DN/px**,
measured on camera-linear renders of *both* arms, at the same site, over
the same window, with the source frame carried through the identical
alignment gather (section 1.2). The pair quoted is the subject's *worst*
evidence-bearing site -- the one most favourable to a merge-loss verdict.
`deficit` is positive when the source frame is ahead of the merge (a
defect) and negative when **the merge beats every single source frame**.
`worst px` is the equivalent Gaussian softening; the instrument floor is
0.30 px, so any value at or below that is *no measurable difference*.

| # | subject | verdict | WxH | merge DN/px | best frame DN/px | deficit DN/px | worst px | evidence |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | `109MSDCF` | **GOOD** | 7032x4688 | 824 | 836 | +12.0 | 0.75 | at DETAIL, +1.4% |
| 2 | `112MSDCF` | **GOOD** | 7032x4688 | 920 | 916 | -4.4 | 0.00 | at DETAIL, -0.5% |
| 3 | `113MSDCF` | **GOOD** | 7032x4688 | 1975 | 2013 | +37.2 | 0.40 | at DETAIL, +1.9% |
| 4 | `119MSDCF` | **GOOD** | 7032x4688 | 2123 | 2222 | +99.3 | 0.65 | at DETAIL, +4.5% |
| 5 | `bee-1-cpl` | **GOOD** | 7032x4688 | 8463 | 8926 | +462.6 | 0.49 | at DETAIL, +5.2% |
| 6 | `bee-2-cpl` | **GOOD** | 7032x4688 | 1891 | 1324 | -567.4 | 0.00 | at DETAIL, -42.9% |
| 7 | `bee-3-cpl` | **GOOD** | 7032x4688 | 2198 | 1368 | -830.8 | 0.00 | at SOURCE-BEST, -60.7% |
| 8 | `coffee-bean` | **GOOD** | 7032x4688 | 5558 | 5310 | -247.9 | 0.00 | at DETAIL, -4.7% |
| 9 | `couch-fibers-cpl` | **GOOD** | 7040x4688 | 1883 | 1124 | -758.5 | 0.00 | at DETAIL, -67.5% |
| 10 | `dry-erase-marker-head-cpl` | **GOOD** | 7040x4688 | 2225 | 961 | -1264.2 | 0.00 | at SOURCE-BEST, -131.6% |
| 11 | `flat-on-ruler-cpl` | **GOOD** | 7040x4688 | 2441 | 2407 | -33.4 | 0.00 | at SOURCE-BEST, -1.4% |
| 12 | `flower-bud-alone-cpl` | **GOOD** | 7040x4688 | 1559 | 1400 | -158.7 | 0.00 | at DETAIL, -11.3% |
| 13 | `flower-inner-edge-cpl` | **GOOD** | 7032x4688 | 284 | 73 | -211.0 | 0.00 | at DEFICIT, -287.5% |
| 14 | `lavendar-cpl` | **GOOD** | 7040x4688 | 3191 | 1943 | -1248.4 | 0.00 | at DETAIL, -64.3% |
| 15 | `pencil-flatter-angle-cpl` | **GOOD** | 7032x4688 | 2738 | 1845 | -893.5 | 0.00 | at DETAIL, -48.4% |
| 16 | `pencil-steep-angle-cpl` | **GOOD** | 7032x4688 | 1399 | 1125 | -273.9 | 0.00 | at SOURCE-BEST, -24.3% |
| 17 | `tweezers-cpl` | **GOOD** | 7040x4688 | 3562 | 3475 | -86.7 | 0.00 | at DEFICIT, -2.5% |
| 18 | `wrapped-text-1` | **GOOD** | 7032x4688 | 804 | 750 | -53.5 | 0.00 | at DEFICIT, -7.1% |
| 19 | `wrapped-text-2` | **GOOD** | 7032x4688 | 779 | 734 | -44.6 | 0.00 | at DEFICIT, -6.1% |
| 20 | `flower-bud-with-background-fern-cpl` | **CAP: coverage gap** | 7040x4688 | 2143 | 1869 | -274.2 | 0.00 | 6.20% of detail-bearing pixels elect the **last** frame (1.19x its own shuffled null; 5.20% of all pixels); at SOURCE-BEST, -14.7% |
| 21 | `highly-angled-ruler-mm-cpl` | **CAP: coverage gap** | 7040x4688 | 2139 | 929 | -1210.0 | 0.00 | 7.34% of detail-bearing pixels elect the **last** frame (1.50x its own shuffled null; 4.90% of all pixels); at DETAIL, -130.2% |
| 22 | `flowers-cpl` | **CAP: occluded geometry** | 7040x4688 | -- | -- | -- | -- | 55.17% of detail-bearing pixels at a bracket end (1.57x null), but on occlusion edges, not a short bracket; no site had signal over noise in either arm |
| 23 | `coffee-bubbles` | **CAP: motion** | 7032x4688 | 337 | 350 | +12.8 | 0.47 | NCC 0.94587, 20/24 blocks moving; at DEFICIT, +3.7% |
| 24 | `foam` | **CAP: motion** | 7032x4688 | 10198 | 8087 | -2111.6 | 0.00 | NCC 0.97944, 20/24 blocks moving; at DEFICIT, -26.1% |
| 25 | `lead-1-cpl` | **CAP: motion** | 7040x4688 | 220 | 205 | -15.7 | 0.00 | NCC 0.98563, 19/24 blocks moving; at SOURCE-BEST, -7.7% |
| 26 | `leaf-2-cpl` | **CAP: motion** | 7040x4688 | 470 | 481 | +10.6 | 0.41 | NCC 0.98932, 11/24 blocks moving; at DETAIL, +2.2% |

### 3.1 The arithmetic

```
   19  GOOD
    0  MERGE-LIMITED
    2  CAPTURE-LIMITED - coverage gap
    1  CAPTURE-LIMITED - occlusion/geometry
    0  CAPTURE-LIMITED - diffraction/magnification
    4  CAPTURE-LIMITED - motion
    0  UNRESOLVED
  ---
   26  TOTAL
```

    19  +  0  +  2  +  1  +  0  +  4  +  0  =  26

The zero rows are printed on purpose. A count that does not move looks identical whether nothing was wrong or nothing was examined, so `MERGE-LIMITED 0`, `CAP: diffraction 0` and `UNRESOLVED 0` are stated rather than omitted.

### 3.2 What each class needs

| verdict | n | who fixes it | action |
|---|---:|---|---|
| GOOD | 19 | nobody | ship as-is |
| MERGE-LIMITED | 0 | the software | route to the merge; source frames hold detail the merge discarded |
| CAP: coverage gap | 2 | the camera | reshoot extending the bracket past the stated end. The end is named per subject in the table and on the contact sheet, so this is actionable without re-measuring. The merge cannot invent focus no frame captured. |
| CAP: occluded geometry | 1 | nobody, with frames | **more frames will not help.** The unresolved pixels are occluded from the lens, not out of focus, so extending the bracket changes nothing. Reshoot from another angle or accept the subject's geometry. |
| CAP: diffraction | 0 | the camera | reshoot at a wider marked aperture |
| CAP: motion | 4 | the camera | shorten the bracket or stabilise; no merge change recovers a subject that moved |
| UNRESOLVED | 0 | nobody yet | re-site the comparison; not a statement about the image |

---

## 4. Verdict

### 4.1 The merge is not losing detail. On any subject.

This is the headline and it is unambiguous.

Across **64 evidence-bearing sites on 25 subjects**, the largest deficit of the
merge against the best single source frame anywhere in the corpus is:

```
    bee-1-cpl, DETAIL site (3845,1502)
    merge          8463.0 DN/px
    best frame     8926.0 DN/px   (frame 44, gather-corrected)
    deficit        + 462.6 DN/px  = +5.2%
    equivalent to  0.49 px of Gaussian blur
                   (instrument floor 0.30 px; MERGE-LIMITED threshold 0.80 px)
```

That is the **worst case in the entire corpus**, and it does not reach the
threshold. Nineteen of the twenty-five subjects that have any evidence-bearing
site have the merge **ahead of the best single frame even at their own worst
site**, by as much as 2111 DN/px (`foam`, -26.1%) and 131% (`dry-erase-marker-
head-cpl`). Where the merge wins it wins large; where it loses it loses by a few
percent.

Two things make even that 5.2% an overstatement rather than an understatement:

* At `bee-1-cpl` DETAIL the single frame's tile mean is **2904 DN against the
  merge's 2610 DN** -- the frame is 11% brighter. Edge slope in DN/px scales
  with level, so part of the 5.2% is a level difference, not a sharpness
  difference. Corpus-wide the two arms agree to a **median of -3.5 DN (1.55%)**,
  so this is a local outlier and not a systematic additive bias -- but at this
  particular site it flatters the frame.
* That site registers at `ncc = 0.691`. It is depth-complex: the merge there
  legitimately resembles no single frame, because it is combining several.

**Nothing in this corpus should be routed to the merge.** There is no retouch
work here. `MERGE-LIMITED = 0` is not an unexamined category -- it is a measured
result over 64 sites, each with a crop that was opened and looked at.

### 4.2 The three subjects named in the brief

**`bee-3-cpl` is confirmed as the reference for the GOOD class.** The merge is
ahead of the best single frame at *every* site: DETAIL 3115 vs 1720 DN/px
(1.81x), SOURCE-BEST 2198 vs 1368 (1.61x), DEFICIT 1340 vs 487 (**2.75x**), with
`blur_equiv = 0.00 px` throughout. The crop shows individually resolved leg
hairs and a clean flat field. Confirmed, not merely consistent.

**`flowers-cpl` is not a merge failure, and three independent lines of evidence
now say so.** First, after gating, **not one site on this subject has edges clear
of pixel noise in *either* arm**. The crop shows why — three of its four sites
are featureless pale panels in both merge and frame. Its raw numbers looked like
a catastrophic merge failure (`ratio 0.388`, `blur 3.00 px` at DEFICIT); the crop
showed blank panels, and the source's 96.7 DN/px "edge" sitting on **46.7 DN of
its own noise**. See 4.4.

Second, the per-pixel election map (section 6) puts **55.17% of its
detail-bearing pixels at an end of the bracket** — by far the corpus maximum,
against 0.00% on `bee-3-cpl`. So detail genuinely was not brought into focus.

Third, and this is what changes the *advice*: that is **not a bracket that
stopped short**. Section 23 of `docs/captures-needed.md` established
per-pixel that the boundary pixels are thin ribbons tracing petal edges,
concentrated 7.8x in the highest-contrast decile, and it **explicitly withdrew
the "reshoot wider" recommendation**. My election map confirms it and adds a
second component the earlier work did not name: broad interstitial shadow
between overlapping petals, which is *occluded from the lens*, not merely out of
focus. Neither component is recoverable with more frames.

`flowers-cpl` is therefore classified **CAPTURE-LIMITED — occlusion/geometry**,
and its remedy on the contact sheet reads *"not fixable by more frames: those
regions are occluded, not merely defocused. Reshoot from another angle."* An
earlier draft of this report and of the sheet told the owner to reshoot with
~67% more frames at the far end. That advice was wrong, it had already been
measured and withdrawn once, and it is corrected here.

**`wrapped-text-2`: the lower-left region was measured directly, and the merge
is not responsible.** Forcing a comparison site at focus-grid block (3,0) --
the owner's blurred corner -- gives, at `ncc = 0.998`:

```
    LOWER-LEFT  (512,3846)      merge  519.5   best frame  528.4 DN/px
                                ratio 0.9832   deficit +8.9 DN/px   0.44 px
    RIGHT-REF   (6190,2674)     merge 1214.1   best frame 1026.2 DN/px
                                ratio 1.1831   merge ahead by 187.9 DN/px
```

The merge reproduces **98.3%** of the best frame's edge slope in the soft
corner. The softness is in the source frames.

And the apparent *regional* blur is largely not blur at all. The lower-left tile
mean is **4469 DN against 13207 DN** on the right of the same frame -- it is
**2.95x darker**. Edge slope in DN/px scales with illumination, so comparing
519 against 1214 across that is a comparison across a transformation, exactly
the error this project keeps repeating. Normalised by local mean, the lower-left
carries **more** relative edge contrast than the sharp right side (0.1162 vs
0.0919). That normalisation is itself imperfect -- the two tiles hold different
content -- so the defensible claim is the narrow one: **the matched merge-vs-
source comparison at that spot shows no merge defect**, and a large illumination
falloff is present and sufficient to explain what the eye sees at 1:8.

### 4.3 What is actually wrong with the gallery

Seven of 26 subjects have a real defect, and **every one of them is a capture
limitation**. Only three of the seven are a focus problem at all:

* **2 coverage gap**, both at the **last** frame of the bracket, both localised
  to a nameable thing in the picture.
  `flower-bud-with-background-fern-cpl` (6.20% of detail-bearing pixels, 1.19x
  its own null) — the background fern sits entirely beyond the far end; the bud
  itself is a smooth, fully-spanned depth map.
  `highly-angled-ruler-mm-cpl` (7.34%, 1.50x) — a flat plane cannot occlude
  itself, and its election map shows a clean monotonic depth ramp that
  *saturates* at the last rung. Both are genuinely fixable by extending the
  bracket, and both name the end to extend.
* **1 occluded geometry.** `flowers-cpl`, 55.17% — see 4.2. More frames will not
  help.
* **4 motion.** `foam` and `coffee-bubbles` were known; the instrument found
  them at ranks 1 and 2 of 26 by adjacent-frame NCC, which is what earns the
  threshold. `lead-1-cpl` and `leaf-2-cpl` join them. The corpus separates
  cleanly -- the four lowest medians are 0.9459/0.9794/0.9856/0.9893 and the
  next subject jumps to 0.99642.
* **0 diffraction-limited.** This is a real result, not an untested category.
  The corpus does contain f/11 on three subjects (see 2.6, which corrects the
  census in the brief), and at this magnification that is optically ~f/33 -- but
  no subject failed *because* of it. On every subject some site resolves detail
  well clear of noise.

The remaining **19 are GOOD**. That number is 7 higher than this report's first
pass, and the correction is entirely due to replacing the coverage detector
(section 6): the old 24-block aggregate counted blocks whose *average* focus
peaked at a bracket end, which on a subject with a large blown backdrop is a
statement about the backdrop. `tweezers-cpl` is the clearest case — 4.76% of all
its pixels elect a bracket end and **0.00%** of its detail-bearing pixels do.
Its election map shows the tweezers as one uniform, fully-spanned depth field
with every machining striation resolved, and all the end-elections out in the
blown white surround.

### 4.4 The two verdicts this instrument reversed, and what they cost

Both were caught by opening a crop, not by a number.

1. **Band amplitude counted noise as signal.** A single frame carries up to 2.5x
   the pixel noise of a pyramid merge, and high-band amplitude cannot tell noise
   from detail. It scored `119MSDCF` at `ratio 0.549` -- a claimed 45% detail
   loss -- on a crop that plainly showed the *merge* sharper. Commissioning C8c
   quantifies the mechanism: **noise alone manufactures a 2.05x false sharpness
   advantage for the noisier arm.** The metric was replaced (2.2, 2.3), not
   patched. Old and new disagree by **3.12x on identical pixels**, and the crop
   adjudicates for the new one.
2. **The noise gate was one-sided, which is the wrong side.** It required only
   the *merge* arm to be clear of its own noise. Because the merge is the
   cleaner arm, that put the stricter test on the wrong side and admitted
   exactly the sites where a source looks sharper *because* it is noisier.
   `flowers-cpl` DEFICIT passed it and scored the corpus's worst apparent merge
   failure off two blank panels. The gate is now two-sided: a site may testify
   to merge *loss* only if **both** arms clear 4x their own noise.

A third correction never reached a verdict but shaped the table: a site's noise
figure is now quoted from the designated FLAT reference only. `pixel_noise()` is
a median residual, so wherever there is real detail it counts that detail as
noise -- corpus medians are **1.47x (merge cleaner) at FLAT but 0.72x at
DETAIL**. Reporting the DETAIL figure would have printed "bee-3-cpl: 2.08x more
pixel noise" underneath the sharpest render in the set.

### 4.5 What would change this verdict

Stated plainly, so the result can be attacked:

* The comparison samples **3-4 sites per subject**, chosen by gradient
  percentile plus a source-favouring DEFICIT site. A merge defect confined to a
  region none of those sites lands on would be missed. The `--block R,C` override
  exists for exactly this and was used on `wrapped-text-2`; it can be pointed at
  any block on any subject in about four minutes.
* `blur_equiv` saturates at 3.00 px and floors near 0.30 px. Verdicts inside
  those bounds are quantitative; outside them they are directional only.
* The 0.80 px MERGE-LIMITED threshold is a judgement, not a measurement. It sits
  2.7x above the instrument floor. The corpus does not come close to it from
  either side -- the worst subject is 0.75 px and the next is 0.65 px -- so no
  verdict in this table flips under a reasonable change to it. Lowering it to
  0.70 px would move `109MSDCF` alone.
* Everything numeric is camera-linear on **both** arms. Nothing was measured
  from the shipped `--srgb` masters (1.1).

---

## 5. Reproducing this

```
python experiments/BUILD-TRIAGE/commission.py          # C1-C6  instrument
python experiments/BUILD-TRIAGE/commission_shift.py    # C7     gather stand-in
python experiments/BUILD-TRIAGE/commission_noise.py    # C8     noise subtraction
python experiments/BUILD-TRIAGE/commission_edge.py     # E1-E5  primary metric
python experiments/BUILD-TRIAGE/focuscurve.py  <subject>   # capture side
python experiments/BUILD-TRIAGE/localmotion.py <subject>   # motion
python experiments/BUILD-TRIAGE/compare.py     <subject>   # merge vs source
python experiments/BUILD-TRIAGE/crops.py       <subject>   # the picture
python experiments/BUILD-TRIAGE/dims.py                    # master dimensions
python experiments/BUILD-TRIAGE/coverage.py                # C9-C11 + coverage
python experiments/BUILD-TRIAGE/covermap.py    <subject>   # the coverage picture
python experiments/BUILD-TRIAGE/triage.py                  # the table
python experiments/ORCH-drift-check/makeviewable.py \
    --triage C:\dev\strehl-out\BUILD-TRIAGE\triage.json     # the honest gallery

# the election maps coverage.py reads (about 2h for all 26; no --out, so no
# 188 MB TIFF is written -- only pass-one state is needed):
strehl stack D:\personal\macro\<subject> --merge estimator --gate 2 \
    --index-map C:\dev\strehl-out\BUILD-TRIAGE\cover\<subject>.idx.tiff

# interrogate a NAMED region rather than a percentile-selected one:
python experiments/BUILD-TRIAGE/compare.py wrapped-text-2 --tag ".region" \
    --block "LOWER-LEFT:3,0" --block "RIGHT-REF:2,5"
```

Artefacts:

| what | where |
|---|---|
| labelled contact sheet (deliverable 2) | `C:\dev\strehl-out\SHIP-V1\viewable\contact-triage.jpg` |
| per-subject 1:1 crop sheets, all 26 | `C:\dev\strehl-out\BUILD-TRIAGE\crops\<subject>.jpg` |
| per-subject election maps, all 26 | `C:\dev\strehl-out\BUILD-TRIAGE\covermaps\<subject>.jpg` |
| raw election maps + estimator logs | `C:\dev\strehl-out\BUILD-TRIAGE\cover\<subject>.idx.tiff` |
| machine-readable verdicts | `C:\dev\strehl-out\BUILD-TRIAGE\triage.json` |
| coverage statistics, all 26 | `C:\dev\strehl-out\BUILD-TRIAGE\coverage.json` |
| master dimensions | `C:\dev\strehl-out\BUILD-TRIAGE\dims.json` |
| per-subject measurements | `C:\dev\strehl-out\BUILD-TRIAGE\compare\<subject>.json` |
| matched tiles (re-score without re-rendering) | `C:\dev\strehl-out\BUILD-TRIAGE\tiles\<subject>.<site>.npz` |

Scratch, renders and per-subject JSON live in `C:\dev\strehl-out\BUILD-TRIAGE\`.

---

## 6. The coverage instrument, and why raw `boundary %` is not it

### 6.1 The statistic

`docs/captures-needed.md` section 23 records the right primitive: the fraction of
output pixels whose **elected frame is the first or last rung of the bracket**.
A pixel whose best focus sits at a boundary is telling you its true optimum lies
outside the bracket. It is merge-independent, it is cheap, and the shipped binary
will dump the whole field with `--merge estimator --gate 2 --index-map <path>`.
That map is on the plane grid at half sensor resolution and is *exactly* half the
linear render in both axes, so the two overlay with a factor-2 block mean and no
resampling. Election indices are frame numbers, not photometric values, so no
tone curve can touch this measurement at all.

### 6.2 Commissioning (C9-C11)

* **C9 — null, against the binary itself.** My independent recomputation of
  `boundary %` from the election map reproduces the figure the binary prints in
  its own log, on **26 of 26 subjects**, worst disagreement **0.0047 percentage
  points**. Any later disagreement is therefore between builds, not between me
  and the binary.
* **C10 — morphology positive control.** A 3 px-wide synthetic ring and a filled
  disk of *identical area* must be separable by erosion survival. Measured:
  contour **0.0000**, region **0.7947**.
* **C11 — contrast null and plant.** A shuffled mask of matched size returns a
  top/bottom decile ratio of **0.966** (flat, as it must be); a mask planted on
  the top contrast decile is recovered at a ratio >50. The shuffled null is
  carried per subject in every reported figure, not just at commissioning.
* **Reproduction of the published values.** Section 23 measured, at `e47cf81`,
  `flowers-cpl` 33.74%, `bee-3-cpl` 1.00%, `leaf-2-cpl` 0.12%. I measure
  **35.07 / 1.10 / 0.13** on the shipped binary — a 281x dynamic range reproduced
  within 10% on all three.

### 6.3 The correction: restrict to detail-bearing pixels

Raw `boundary %` is **not usable as a coverage verdict on this corpus**, and the
failure is not subtle. `tweezers-cpl` has **4.76%** of its pixels at a bracket
end and **0.00%** of its detail-bearing pixels there; `coffee-bean` falls
**8.57% → 0.00%**. In both, the subject is a single smooth fully-spanned depth
field and every end-election is out in a blown, featureless surround where the
focus argmax has nothing to lock onto. Electing an end where there is no detail
costs nothing, and no reshoot can change it. Taken at face value, raw
`boundary %` would have sent the owner out to re-photograph two subjects that are
correctly captured.

So the reported statistic is the end-election rate **among pixels that carry
resolvable detail** (top three contrast deciles), together with its own
size-matched shuffled null. On the print-worthy reference `bee-3-cpl` this is
**0.00%**; on `flowers-cpl` it is **55.17%**.

One further correction was needed, and it is this project's signature error in
miniature. Contrast was first measured as local standard deviation in DN, which
scales with illumination — so a **dark** but richly detailed object ranks *below*
a bright smooth one. On `flower-bud-with-background-fern-cpl` that put the
background fern, which is manifestly detailed and manifestly beyond the bracket,
at **0.90x** chance: the statistic reported it as carrying less detail than
average purely because it is dark. Dividing by the local mean makes the measure
illumination-invariant and the same subject reads **1.19x**, which is what its
election map plainly shows.

### 6.4 The threshold, read off the corpus

The detail-bearing rate has an empty band in the measured data:

```
  ... 0.499 (119MSDCF)  0.517 (pencil-steep)  0.803 (lavendar)
  |------------------ 3.2x, no subject inside ------------------|
      2.595 (flower-bud-alone)  6.200 (fern)  7.336 (ruler)  55.167 (flowers)
```

`GAP_DETAIL_PCT = 2.0` sits inside that band. As with the motion threshold, it is
read off the corpus rather than asserted. A second condition — the boundary set
must target detail at least as much as a random mask of the same size would —
is required because `flower-bud-alone-cpl` clears the rate at 2.595% but at
**0.34x** its own null: its bud is fully spanned and its end-elections are on
backdrop streaks.

### 6.5 What this instrument cannot do

**It does not separate a short bracket from an occlusion by itself.**
`flowers-cpl` (occlusion) and `highly-angled-ruler-mm-cpl` (a genuine gap) sit at
enrichment **1.57** and **1.50**, and at high-contrast mass fractions **0.472**
and **0.449** — indistinguishable on every summary statistic I computed. The
split in section 3 is therefore made by **inspecting each election map**, and the
call is recorded in an explicit table in `triage.py` rather than hidden inside a
threshold that does not actually separate the cases. The maps are in
`covermaps\<subject>.jpg`; every subject above the threshold was opened and read.

### 6.6 Two questions this settles

**`119MSDCF` does not have a coverage gap on the shipped path.** The brief cites
7.38% of its pixels peaking at a bracket edge, from an earlier milestone. On the
shipped binary the figure is **0.78%** — below `bee-3-cpl`'s 1.10% — and my
recomputation matches that binary's own printed value to **0.0001 pp**, so this
is a difference between builds and not a measurement error. Its election map
shows a smooth monotonic index ramp from lower-left to upper-right, the exact
signature of a tilted plane properly spanned, with end-elections confined to
specks in the extreme corners where the tilt just overruns. Classified **GOOD**.
Note also that `119MSDCF` (33 frames) and `112MSDCF` (79) both fail the 2x
density gate recorded in `captures-needed.md`, at 2.18x and 2.10x, so neither may
be used as its own ground truth.

**The master width variation is a packaging wart, not an alignment diagnostic.**
The 26 masters are 7032x4688 (15 subjects) or 7040x4688 (11). Width tracks
neither `coverage_k` (Mann-Whitney **p = 0.9586**; medians 0.9572 vs 0.9480 with
almost completely overlapping ranges) nor frame count (**p = 0.2349**). Both
widths are adjacent multiples of 8 — 8x879 and 8x880, against a constant height
of 8x586 — which is consistent with the FOV crop being rounded to a pyramid
level and landing one step apart. It is worth one line to whoever prints the set,
and nothing more. Dimensions are now carried per row in section 3 and on every
tile of the contact sheet.
The RAW stacks under `D:\personal\macro\` were opened read-only and never
written.

---

## 7. The estimator was biased twice, in opposite directions, and fixing it moved the headline

**Status of this section: MEASURED.** It supersedes the merge-loss arithmetic in
S4.1 and the `flowers-cpl` mechanism in S3/S4.2. Everything here was re-measured
with the corrected instrument after the biases below were found.

### 7.1 Two mirror-image biases, both fatal, both invisible in a ratio

The best-frame picker decides which single source frame the merge is compared
against. Get it wrong and the comparison is meaningless in a direction that
depends on *how* you got it wrong:

| estimator | noise scaling | elects | effect on the verdict |
| --- | --- | --- | --- |
| Laplacian RMS in DN | noise ~ `sqrt(level)` | the **brightest** frame | hands the merge a blurrier opponent -- **flatters the merge** |
| Laplacian RMS / level | noise/level ~ `1/sqrt(level)` | the **darkest** frame | hands the merge a grainier opponent -- **manufactures merge deficits** |

Neither is a focus measure at a low-signal site. This corpus makes the trap
unavoidable: **13 of 26 subjects brighten monotonically through the bracket**,
up to `x1.468` on `dry-erase-marker-head-cpl`, so the two estimators disagree
systematically rather than occasionally.

I hit both. The DN form was in `refine_best_frame` and its own docstring warned
the error is "DANGEROUS IN THE FLATTERING DIRECTION". I replaced it with the
ratio form -- and `flowers-cpl` promptly inverted to an apparent
**MERGE-LIMITED** at ratios 0.36-0.52. That reversal was the mirror bias, not a
discovery.

### 7.2 The fix, and a control with real power

`sitescan.focus_score` subtracts the noise power before normalising:

    signal^2 = LapRMS^2 - (a*level + b)          # a, b fitted per frame from
    score    = sqrt(max(signal^2, 0)) / level    # the emptiest tiles per level bin

Commissioned as **C16**, on a plant that had to be rebuilt once. My first
version scaled a window by `s` -- but that scales signal *and* noise together,
so `hf_rel` is exactly invariant under it and the control had **no power**. The
faithful plant is physical: signal `~ level`, shot noise `~ sqrt(level)`, on a
synthetic featureless field, at the exact +19.1% `flowers-cpl` carries, with the
focus never changing. C16 now *requires* both naive estimators to fail before it
will pass:

    hf_dn   x1.092 -> false gap at endN     (= sqrt(1.191), textbook shot noise)
    hf_rel  x0.917 -> false gap at end0     (= 1/sqrt(1.191))
    focus_score: featureless -> no gap called; textured -> flat to x1.0006

**C17** requires the emptiest real tile to score far below the richest
(`x5.5` measured). Its first draft compared the emptiest tile against the frame
*centre* -- which on `flowers-cpl` is itself bokeh, so it compared two
featureless things and proved nothing.

### 7.3 ORCH's ruler control passes, and it passed *harder* after the fix

At `flat-on-ruler-cpl`, all seven sites: merge at or above the corrected best
frame, `blur_equiv 0.00 px`.

| site | merge DN/px | frame corrected | ratio |
| --- | --- | --- | --- |
| METAL | 1553.4 | 1510.9 | **1.0281** |
| MARK | 1769.2 | 1661.4 | **1.0649** |
| MARK-EDGE | 1696.5 | 1596.7 | **1.0625** |

The merge's lead at METAL **shrank** from `x1.0442` to `x1.0281`, because the
corrected estimator found a genuinely better source frame (36, not 38). The fix
moved the numbers in the **unflattering** direction and the merge still won,
which is much stronger evidence than if it had flattered it. Per ORCH's design:
the instrument does not lose sharpness at the metal, so its verdict elsewhere
stands.

### 7.4 The third trap: an edge metric run on grain returns a number that is not an edge

With the picker fixed, `flowers-cpl` *still* showed ratios 0.37-0.52. The noise
column gave it away: at those sites the source frame carries **45.2 DN** of pixel
noise against the merge's **6.7 DN**. A merge averages many frames; a single
frame does not. The merge is up to **10x quieter**, and it loses automatically
wherever neither arm has real detail.

The crop could not settle it, and believing it would have been the same error in
new clothes: at a mean level of 8444 DN, a 91 DN/px modulation is **~1%**, which
after the display transfer is under one 8-bit level. Both arms look blank whether
or not one holds structure. *Look at the picture* is the right instinct and the
wrong instrument at that contrast.

So I measured it instead. `grainprobe.py` exploits the fact that adjacent frames
share their **subject** but not their **grain**: average k neighbours and grain
falls as `1/sqrt(k)` while structure is preserved. Commissioned on synthetic data
(pure grain `x0.452` against a predicted `x0.447`; pure structure `x1.000`).
At the three `flowers-cpl` sites, **54-68% of the source frame's measured edge
power is grain**, against ~3% for the merge.

### 7.5 The gate, read off the corpus

Sorting all 104 sites by how far the weaker arm sits above its own grain floor
gives a distribution with a hole in it:

    1.54 ... 2.99   then   5.59 ... 43.46

Nothing in between -- a `x1.87` empty band, 29 sites below and 75 above. The band
is exactly where the verdicts change:

| min arm SNR | sites | median ratio | % "losing" | median merge edge |
| --- | --- | --- | --- | --- |
| 0-2 | 7 | 0.367 | 71% | 55 DN/px |
| 2-3 | 22 | 0.716 | 55% | 102 DN/px |
| 3-6 | 3 | 0.987 | **0%** | 252 DN/px |
| 6-12 | 29 | 1.129 | **0%** | 718 DN/px |
| 12+ | 43 | 1.260 | 5% | 2143 DN/px |

**Every "the merge loses" verdict in the entire corpus lives below the gap**, at
sites whose merge edge is under ~100 DN/px -- the emptiest parts of each frame,
which is precisely what the `FLAT` and `DEFICIT` percentile selectors pick by
construction. Above the gap the merge's advantage **grows monotonically with how
much real detail the site holds**. A genuine merge defect would do the opposite:
it would get worse where there is more to lose. `MIN_ARM_SNR = 4.0`; any value
inside the band gives identical results.

### 7.6 The corrected headline

**Of 104 sites, 75 carry real detail in both arms. 29 carry detail in neither --
those are capture verdicts, not merge verdicts, and they must never be reported
as ratios.**

**Across the 75 sites entitled to vote, the merge is behind the best corrected
source frame at exactly one site, on one subject, by 5.2%.**

Everywhere else the merge equals or beats the best single frame, typically by a
wide margin: `x2.91` (`flower-inner-edge-cpl`), `x2.32`
(`dry-erase-marker-head-cpl`), `x1.68` (`couch-fibers-cpl`), `x1.64`
(`lavendar-cpl`), `x1.44` (`bee-3-cpl`, confirming ORCH's reference pick).

The one exception, stated with its caveats rather than explained away:

> `bee-1-cpl`, block(1,3) @(3845,1502), frame 44. Merge **8463 DN/px** vs
> corrected source **8926 DN/px** -- ratio **0.948**, deficit **+464 DN/px**,
> `blur_equiv` **0.49 px** (sub-pixel), arm SNR 25.
> **Caveats:** this is the lowest-NCC site measured anywhere in the corpus
> (**0.691**, against a corpus norm above 0.95), and the content is a compound
> eye -- a periodic hexagonal lattice near Nyquist, the worst possible subject
> for a registration-sensitive comparison. At 1:1 **both arms resolve the
> lattice clearly** and no defect is visible. Real but small; worth a look from
> whoever owns the merge; not a gallery-visible fault.

### 7.7 `flowers-cpl` is capture-limited, and this refutes an intermediate draft of my own

`flowers-cpl` and `highly-angled-ruler-mm-cpl` score **0 of 4 sites entitled to
vote** -- no site in either subject holds detail in *either* arm. That is the
strongest capture-limited statement the instrument can make.

An intermediate draft of `triage.py` relabelled `flowers-cpl` a **coverage gap at
`end0`**, on the strength of a frameflip in which frame 0 appeared to resolve
trichomes while every later frame was featureless. That was the `hf_rel` bias
electing the darkest frame, and my reading of the picture was wrong too: what I
called resolved texture was a **defocused blob**, which is large-scale contrast,
not detail. Re-examined at the frames the corrected metric prefers, all six are
featureless and `hf_rel` is **flat at 0.0551 -> 0.0562 across all 176 frames**.
A bracket that stopped short rises toward an end; this does not rise at all.

Where the subject *is* reachable, at (1504,1502), the merge beats the best single
frame **x5.07** and resolves trichomes and pollen grains that no individual frame
holds. The verdict returns to *no focus plane in this bracket reaches most of
this frame*, which no number of extra frames would fix. Drift is 0.00 px, so not
motion.

### 7.8 What this cost, and the rule it confirms

Three separate instrument defects, all the same shape -- **comparing two things
that are not on the same side of a transformation** -- and each one produced a
confident, defensible, wrong answer:

1. an exposure ramp read as a coverage gap (level);
2. a shot-noise floor read as a merge deficit (noise vs level);
3. grain read as detail (merge quieter than a single frame by up to 10x).

Each was caught by a control, and **not one was caught by looking at a ratio.**
Two were caught only because the absolute DN levels were on the page next to
them. The `flowers-cpl` reversal in particular looked exactly like a headline
finding, and shipping it would have routed engineering effort at a merge that is
working correctly.
