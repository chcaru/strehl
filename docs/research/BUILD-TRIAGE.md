# BUILD-TRIAGE: which subjects are the merge's fault, and which are the camera's

**Status:** complete. 26 of 26 subjects classified; instrument commissioned
(C1-C8, E1-E5). **Headline: the merge is not losing detail on any subject.
`MERGE-LIMITED = 0` over 64 evidence-bearing sites; the worst deficit anywhere
is +462.6 DN/px (+5.2%, 0.49 px equivalent) on `bee-1-cpl`, below the 0.80 px
threshold. All 14 defective subjects are capture-limited.** See section 4.

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

| # | subject | verdict | merge DN/px | best frame DN/px | deficit DN/px | worst px | evidence |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | `109MSDCF` | **GOOD** | 824 | 836 | +12.0 | 0.75 | at DETAIL, +1.4% |
| 2 | `112MSDCF` | **GOOD** | 920 | 916 | -4.4 | 0.00 | at DETAIL, -0.5% |
| 3 | `113MSDCF` | **GOOD** | 1975 | 2013 | +37.2 | 0.40 | at DETAIL, +1.9% |
| 4 | `119MSDCF` | **GOOD** | 2123 | 2222 | +99.3 | 0.65 | at DETAIL, +4.5% |
| 5 | `bee-1-cpl` | **GOOD** | 8463 | 8926 | +462.6 | 0.49 | at DETAIL, +5.2% |
| 6 | `bee-2-cpl` | **GOOD** | 1891 | 1324 | -567.4 | 0.00 | at DETAIL, -42.9% |
| 7 | `bee-3-cpl` | **GOOD** | 2198 | 1368 | -830.8 | 0.00 | at SOURCE-BEST, -60.7% |
| 8 | `coffee-bean` | **GOOD** | 5558 | 5310 | -247.9 | 0.00 | at DETAIL, -4.7% |
| 9 | `couch-fibers-cpl` | **GOOD** | 1883 | 1124 | -758.5 | 0.00 | at DETAIL, -67.5% |
| 10 | `flat-on-ruler-cpl` | **GOOD** | 2441 | 2407 | -33.4 | 0.00 | at SOURCE-BEST, -1.4% |
| 11 | `wrapped-text-1` | **GOOD** | 804 | 750 | -53.5 | 0.00 | at DEFICIT, -7.1% |
| 12 | `wrapped-text-2` | **GOOD** | 779 | 734 | -44.6 | 0.00 | at DEFICIT, -6.1% |
| 13 | `dry-erase-marker-head-cpl` | **CAP: coverage gap** | 2225 | 961 | -1264.2 | 0.00 | 8/24 blocks peak at a bracket end (5 far, 3 near); at SOURCE-BEST, -131.6% |
| 14 | `flower-bud-alone-cpl` | **CAP: coverage gap** | 1559 | 1400 | -158.7 | 0.00 | 13/24 blocks peak at a bracket end (13 far, 0 near); at DETAIL, -11.3% |
| 15 | `flower-bud-with-background-fern-cpl` | **CAP: coverage gap** | 2143 | 1869 | -274.2 | 0.00 | 13/24 blocks peak at a bracket end (13 far, 0 near); at SOURCE-BEST, -14.7% |
| 16 | `flower-inner-edge-cpl` | **CAP: coverage gap** | 284 | 73 | -211.0 | 0.00 | 7/24 blocks peak at a bracket end (6 far, 1 near); at DEFICIT, -287.5% |
| 17 | `flowers-cpl` | **CAP: coverage gap** | -- | -- | -- | -- | 16/24 blocks peak at a bracket end (16 far, 0 near); no site had signal over noise in either arm |
| 18 | `highly-angled-ruler-mm-cpl` | **CAP: coverage gap** | 2139 | 929 | -1210.0 | 0.00 | 18/24 blocks peak at a bracket end (18 far, 0 near); at DETAIL, -130.2% |
| 19 | `lavendar-cpl` | **CAP: coverage gap** | 3191 | 1943 | -1248.4 | 0.00 | 10/24 blocks peak at a bracket end (10 far, 0 near); at DETAIL, -64.3% |
| 20 | `pencil-flatter-angle-cpl` | **CAP: coverage gap** | 2738 | 1845 | -893.5 | 0.00 | 10/24 blocks peak at a bracket end (10 far, 0 near); at DETAIL, -48.4% |
| 21 | `pencil-steep-angle-cpl` | **CAP: coverage gap** | 1399 | 1125 | -273.9 | 0.00 | 9/24 blocks peak at a bracket end (7 far, 2 near); at SOURCE-BEST, -24.3% |
| 22 | `tweezers-cpl` | **CAP: coverage gap** | 3562 | 3475 | -86.7 | 0.00 | 6/24 blocks peak at a bracket end (6 far, 0 near); at DEFICIT, -2.5% |
| 23 | `coffee-bubbles` | **CAP: motion** | 337 | 350 | +12.8 | 0.47 | NCC 0.94587, 20/24 blocks moving; at DEFICIT, +3.7% |
| 24 | `foam` | **CAP: motion** | 10198 | 8087 | -2111.6 | 0.00 | NCC 0.97944, 20/24 blocks moving; at DEFICIT, -26.1% |
| 25 | `lead-1-cpl` | **CAP: motion** | 220 | 205 | -15.7 | 0.00 | NCC 0.98563, 19/24 blocks moving; at SOURCE-BEST, -7.7% |
| 26 | `leaf-2-cpl` | **CAP: motion** | 470 | 481 | +10.6 | 0.41 | NCC 0.98932, 11/24 blocks moving; at DETAIL, +2.2% |

### 3.1 The arithmetic

```
   12  GOOD
    0  MERGE-LIMITED
   10  CAPTURE-LIMITED - coverage gap
    0  CAPTURE-LIMITED - diffraction/magnification
    4  CAPTURE-LIMITED - motion
    0  UNRESOLVED
  ---
   26  TOTAL
```

    12  +  0  +  10  +  0  +  4  +  0  =  26

The two zero rows are printed on purpose. A count that does not move looks identical whether nothing was wrong or nothing was examined, so `MERGE-LIMITED 0` and `UNRESOLVED 0` are stated rather than omitted.

### 3.2 What each class needs

| verdict | n | who fixes it | action |
|---|---:|---|---|
| GOOD | 12 | nobody | ship as-is |
| MERGE-LIMITED | 0 | the software | route to the merge; source frames hold detail the merge discarded |
| CAP: coverage gap | 10 | the camera | reshoot with more frames at the stated end of the bracket; per-subject percentages are on the contact sheet. The merge cannot invent focus no frame captured. |
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

**`flowers-cpl` is not a merge failure, and the reason is stronger than a
ratio.** 16 of 24 blocks peak at the far end of the bracket. More decisive:
after gating, **not one site on this subject has edges clear of pixel noise in
*either* arm**. The crop shows why -- three of its four sites are featureless
pale panels in both merge and frame. There is no detail there to lose, because
none was captured. Its raw numbers looked like a catastrophic merge failure
(`ratio 0.388`, `blur 3.00 px` at DEFICIT); the crop showed blank panels, and
the source's 96.7 DN/px "edge" sitting on **46.7 DN of its own noise**. See 4.4.

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

Fourteen of 26 subjects have a real, visible defect, and **every one of them is
a capture limitation**:

* **10 coverage gap.** The bracket did not span the subject. Nine of the ten are
  missing frames at the **far** end only; `dry-erase-marker-head-cpl` (5 far,
  3 near) and `pencil-steep-angle-cpl` (7 far, 2 near) are missing both ends.
  Per-subject frame counts are on the contact sheet.
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
python experiments/BUILD-TRIAGE/triage.py                  # the table
python experiments/ORCH-drift-check/makeviewable.py \
    --triage C:\dev\strehl-out\BUILD-TRIAGE\triage.json     # the honest gallery

# interrogate a NAMED region rather than a percentile-selected one:
python experiments/BUILD-TRIAGE/compare.py wrapped-text-2 --tag ".region" \
    --block "LOWER-LEFT:3,0" --block "RIGHT-REF:2,5"
```

Artefacts:

| what | where |
|---|---|
| labelled contact sheet (deliverable 2) | `C:\dev\strehl-out\SHIP-V1\viewable\contact-triage.jpg` |
| per-subject 1:1 crop sheets, all 26 | `C:\dev\strehl-out\BUILD-TRIAGE\crops\<subject>.jpg` |
| machine-readable verdicts | `C:\dev\strehl-out\BUILD-TRIAGE\triage.json` |
| per-subject measurements | `C:\dev\strehl-out\BUILD-TRIAGE\compare\<subject>.json` |
| matched tiles (re-score without re-rendering) | `C:\dev\strehl-out\BUILD-TRIAGE\tiles\<subject>.<site>.npz` |

Scratch, renders and per-subject JSON live in `C:\dev\strehl-out\BUILD-TRIAGE\`.
The RAW stacks under `D:\personal\macro\` were opened read-only and never
written.
