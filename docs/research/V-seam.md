# V-seam — is M122's "structure loss" the election seam?

**Verifier:** V-veiling / V-seam. **Status:** pre-registration, written and committed
**before any slope was computed**. Evidence rows appear above every verdict line.
**Pin:** `C:\dev\strehl-out\pin-859edac\target\release\strehl.exe`, sha256
`DF209CE0...F97DC70F`. Linear renders only, never `--srgb`, never JPEG.

## The collision

M122 returned **KEEP-OFF** on criterion K2, whose single worst subject is
`flower-bud-alone-cpl`: Theil-Sen slope of level-normalised `hf1` on `hf0` = **0.9444**
[0.9312, 0.9598], top-decile ratio **0.9365**. In V-veiling I measured, on the same
subject and the same flag, that `--photometric on` recovers **+1415 DN** of aura at
d = 120-200 px and removes 35-47% of it in the affected bands.

**H-SEAM:** the "real fine structure" M122 measured `--photometric` destroying is,
wholly or partly, **election-seam step edges** — that is, the artifact. The merge elects
frame 10 at d = 120-200 and frame 114 in the far field (V-veiling §2); the fitted gain
span across the bracket is **1.2350**. A boundary between two frames 23.5% apart in level
is a step, a step is high-frequency energy, and `hf` is an energy statistic with no
spatial argument.

## Pre-registered method

M122's statistic, reproduced exactly, then given a spatial argument.

**Arms.** `stack <dir> --gate 4.0 --out X.tif` (A0, correction off) and the same with
`--photometric on` (A1). **Binned** camera-native linear output, 3520 x 2344 — the grid
M122 scored, and the grid the `--index-map` plane is already on, so no resampling enters.

**Statistic, unchanged from M122.** `load` = mean of the three channels, float64,
`uint16` asserted. `hf` = RMS of the 5-point Laplacian. Windows `S = 256`,
`BORDER = 400`, `STRIDE = 128`, which yields exactly **220** windows.
`hf1n = hf1 / (m1/m0)` with `m0`, `m1` the window means. `k` = Theil-Sen slope of `hf1n`
on `hf0` over the **upper half** of `hf0`.

**Commissioning.** My instrument must reproduce M122's global `k` = 0.9444 on this
stack before any partitioned number is read. A different commit built M122's arms, so I
register agreement to **+/- 0.01** as the bar, and I will print my global `k` beside
M122's whatever it comes out at.

**The partition, and its thresholds, fixed here.**

- **Seam set.** A plane-grid pixel is a seam pixel if the **range (max - min) of the
  elected frame index over its 3x3 neighbourhood is >= 8 frames**. Chosen below the
  merge's own depth tolerance of `tau = 25.4` frames so a real depth boundary is caught,
  and above +/-1 election jitter. Dilated by **4 px** to cover the seam's real width.
- **SUBJECT** = inside the subject mask, outside the dilated seam set.
- **BACKGROUND** = outside the subject mask, outside the dilated seam set.
- Subject mask: `< 0.60 x` the binned merge median, 15x15 closing then opening, largest
  connected component — the same mask V-veiling used.
- **PLACEBO** = drawn from non-seam pixels, matched to the seam set in **count** and
  jointly in **local |Laplacian|** and **local level**, by decile-cell matching on the
  symmetric mean `(A0+A1)/2` so neither arm chooses the pixels it is judged on.
- Per window and per partition, `hf` and the window means are computed over **that
  partition's pixels inside that window**; a window contributes to a partition only if
  it holds **>= 2048** of that partition's pixels. A partition needs **>= 8** windows in
  the upper half of its own `hf0` to report a slope.

**Sensitivity, also pre-registered:** `tau` in {4, 8, 16, 32} frames and dilation in
{2, 4, 8} px, reported as a grid.

## Pre-registered reading rule

| condition | verdict |
|---|---|
| `k_seam` < 0.97 **and** `k_subject` >= 0.99 **and** `k_placebo` >= 0.99 | **H-SEAM CONFIRMED** — K2 counted the artifact as signal |
| `k_subject` < 0.97 | **H-SEAM REFUTED** — the correction damages real detail, KEEP-OFF is right |
| neither | **MIXED** — report the share of removed Laplacian energy lying in the seam set |
| `k_placebo` <= `k_seam` + 0.01 | **VOID** — the discriminator is measuring gradient and level, not seams |

`k_placebo` is printed next to `k_seam` on every line that reports `k_seam`.

## Second measurement — is the gain derivable from geometry?

Registered separately: fit `g_k / g_ref = [(1 + m_ref/p) / (1 + m_k/p)]^2` against the
fitted per-frame gains, with `m_k` from the alignment scale ladder and/or the camera's
per-frame `SonyFNumber2`, and report the residual, the fitted `p`, and whether `p` is
**identifiable**. Sanity bound registered in advance: `p` outside **0.3 to 1.5** means
the model is wrong, not that the lens is exotic.

---

# Results

Everything below was computed after the pre-registration above was committed (`42164aa`).
The thresholds and the reading rule were not edited. All numbers are from linear binned
renders on the 3520x2344 grid, one pinned binary, arms `A0-binned.tif` (`--photometric`
off) and `A1-binned.tif` (`--photometric on`), election map `idx-binned.tif` co-gridded
1:1 with the arms.

## C1. Commissioning: I missed my own bar

| statistic | mine | M122 published | delta |
|---|---|---|---|
| windows | 220 | 220 | 0 |
| global `k` | **0.9273** [0.9107, 0.9436] | **0.9444** [0.9312, 0.9598] | **-0.0171** |
| top-`hf0`-decile ratio | 0.9249 | 0.9365 | -0.0116 |

The window grid reproduces exactly. The slope does not: I registered a bar of +-0.01
and missed it by 0.0071. **I am recording this as NOT COMMISSIONED at my registered
bar.** The two confidence intervals do overlap on [0.9312, 0.9436], and my arms come
from a newer binary than M122's (`pin-859edac` against M122's `4beac73`), with several
merge changes landed in between, so the merge itself is not the same image. My `k` is
*lower* than M122's, meaning the effect I go on to partition is if anything larger than
the one M122 measured.

The partition test below is an **internal contrast** between partitions of the *same*
two arms. A 0.017 offset in the absolute global `k` does not propagate into it. That is
why I proceeded. It is a real qualification and it is the reason the headline verdict
below is stated with one.

## C2. The partition, at the registered operating point (`tau` = 8, dilation 4)

Evidence rows first.

| partition | pixels | windows | `hf0` median (DN) | level A0 (DN) | `k` | 95% CI |
|---|---|---|---|---|---|---|
| **SEAM** | 6 163 162 | 212 | 127.3 | 18 654.7 | **0.9338** | [0.9208, 0.9481] |
| **PLACEBO** (matched) | 855 489 | 163 | -- | -- | **0.9886** | [0.9519, 1.0198] |
| **SUBJECT** (no seam) | 1 514 709 | 118 | 280.8 | 1 743.0 | **0.9957** | [0.9888, 1.0022] |
| **BACKGROUND** (no seam) | 573 009 | 97 | 382.6 | 15 841.0 | **1.0287** | [1.0021, 1.0622] |

Laplacian energy removed inside the seam set: **85.7%** of all energy removed, from
**74.7%** of the pixels (enrichment 1.15x).

**Power check, because a flat SUBJECT partition would make its ~1.00 slope meaningless.**
It is not flat. It is the *most* textured partition in the frame:

| partition | median `hf0` (RMS Laplacian, DN) |
|---|---|
| SUBJECT-only windows | **280.8** |
| whole-frame windows (M122's own statistic) | 141.7 |
| SEAM-only windows | **127.3** |

Subject texture carries **2.2x** the high-frequency energy of the seam set, and the
top-`hf0` decile windows are 41.7% SUBJECT against 39.0% SEAM. The partition where the
real fine structure lives is the partition that loses nothing.

## C3. The decomposition that settles it

Splitting the seam set by distance from the silhouette moves the whole result into one
cell:

| partition | pixels | windows | `hf0` median (DN) | level A0 (DN) | `k` | 95% CI |
|---|---|---|---|---|---|---|
| SEAM, far background (d > 200 px) | 5 052 778 | 113 | **106.6** | 18 895.3 | **0.6647** | [0.5431, 0.7899] |
| SEAM, near subject (d < 200 px) | 1 110 384 | 149 | 418.4 | 15 440.0 | 0.9395 | [0.9089, 0.9689] |
| SEAM, inside subject | 290 070 | 102 | 829.8 | 2 592.3 | **0.9941** | [0.9727, 1.0118] |
| SUBJECT, no seam | 1 514 709 | 118 | 280.8 | 1 743.0 | **0.9957** | [0.9888, 1.0022] |
| BACKGROUND, no seam | 573 009 | 97 | 382.6 | 15 841.0 | **1.0287** | [1.0021, 1.0622] |

**All of the harm is in the far background**, at `k` = 0.6647 -- a 33% cut -- in the
partition with the *lowest* high-frequency energy (106.6 DN) and no scene content at
all. Every partition that contains actual structure sits between 0.9941 and 1.0287.
Inside the subject, on the bud itself, `--photometric` removes **0.6%** and the CI
includes 1.00.

And the far background is not fine structure. It is election noise:

```
election instability, far background (d>400px):
  median 3x3 elected-index range = 7 frames
  49.7% of pixels have a >=8-frame index jump inside a 3x3 neighbourhood
  elected index p5..p95 = 3..195   of a 0..204 bracket
far background level:  A0 18696.2 DN   A1 18697.7 DN   (delta +1.5 DN)
far background pixel sd: A0 1204.5 DN  A1 1193.1 DN    (-0.9%)
```

On a featureless white sweep there is no focus signal to elect on, so the election picks
essentially at random across the whole 205-frame bracket, pixel by pixel. Because those
frames differ in level by up to 23.5% (`gain span 1.2350`), a random election writes a
random *level*, and that is the pixel-scale speckle M122's Laplacian was measuring.
`--photometric` equalises the levels and the speckle falls by a third, while the smooth
backdrop gradient is untouched -- which is exactly why the whole-partition sd moves only
-0.9% while the Laplacian slope moves to 0.6647. **Both numbers are in the table above,
because they disagree in magnitude by a factor of 37 and only the pair is honest.**

## C4. Verdict on H-SEAM

**Applying the pre-registered rule verbatim: MIXED.** `k_seam` = 0.9338 < 0.97 (pass)
and `k_subject` = 0.9957 >= 0.99 (pass), but `k_placebo` = 0.9886 falls **0.0014 short**
of the registered 0.99, which drops it out of CONFIRMED and into MIXED. I am reporting
the rule's answer rather than relaxing a bar I wrote myself six hours ago.

**On the substance: H-SEAM is confirmed**, and the mechanism is sharper than the
hypothesis. The structure `--photometric` destroys is not mostly step edges at patch
boundaries; it is **election-noise speckle on the featureless backdrop**, 5.05 million
pixels of it, where the merge elects a near-random frame per pixel out of 205 frames
whose levels span 23.5%. That is an artifact by any definition. M122's K2 counted it as
"real fine structure" because K2 is an energy statistic with no spatial argument and
cannot tell a random-election level step from a bud hair.

The share is not ambiguous. Of the total Laplacian energy `--photometric` removes,
**85.7% lies in the seam set**, and inside the seam set the harm is concentrated in the
content-free far background. On the subject -- the thing K2 was protecting -- the
measured loss is 0.4 to 0.6% with a CI that includes zero loss.

**Therefore M122's KEEP-OFF rests on K2 mislabelling the artifact as signal.** The
qualification I attach is C1: I did not reproduce M122's absolute `k` to my own bar.

## C5. Sensitivity grid, including the cell my own rule voids

| `tau` | dil | `k_seam` | `k_placebo` | `k_subject` | `k_background` |
|---|---|---|---|---|---|
| 4 | 4 | 0.9383 | 0.9966 | 0.9924 | 1.0298 |
| 8 | 2 | 0.9260 | 1.0198 | 1.0000 | 1.0524 |
| **8** | **4** | **0.9338** | **0.9886** | **0.9957** | **1.0287** |
| 8 | 8 | 0.9393 | **0.9394** | 0.9932 | 0.9727 |
| 16 | 4 | 0.9339 | 0.9986 | 0.9959 | 1.0107 |
| 32 | 4 | 0.9411 | 0.9776 | 0.9904 | 1.0141 |

`k_seam` is between 0.9260 and 0.9411 in every cell and its CI excludes 0.97 everywhere.
`k_subject` is between 0.9904 and 1.0000 in every cell.

**The cell at `tau` = 8, dilation 8 is VOID by my own registered rule**: `k_placebo`
0.9394 <= `k_seam` 0.9393 + 0.01. At dilation 8 the seam set swells to 80% of the frame
and the matched placebo has to be drawn from the 20% remaining, which sits immediately
adjacent to seams. The discriminator degenerates there. It is reported because it was
registered, not because it changes the reading of the other five cells.

## C6. The pictures

`SUBJECT-top-hf0.png` (columns: A0 | A1 | `|L0| - |L1|` | election index) is the direct
visual confirmation. In the highest-texture subject windows, A0 and A1 are
indistinguishable -- the same micro-speckle, the same hairs, the same edges. The removed-
energy column is not a copy of the subject texture. It is a set of **closed contour
loops**, and those loops are pixel-for-pixel the boundaries of the grey patches in the
election-index column. What the correction removes is the outline of the election map.

`OVERVIEW-removed-vs-election.png` shows the backdrop election map as salt-and-pepper
noise, and the removed energy concentrated in a bright ring on the silhouette -- the same
place the +1415 DN aura recovery was measured in `V-veiling.md`.

The pictures and the numbers agree.

# Second measurement -- the gain against geometry

## G1. The alignment-ladder route is dead before any fit

| quantity | value |
|---|---|
| alignment scale ladder span, 205 frames | **1.000233** (0.0233%) |
| ladder min / max | 0.99989499 / 1.00012845 |
| `corr(log a, k)` | **-0.5130** -- not monotone |
| fitted photometric gain span (merge log) | **1.2350** |
| exponent `q` needed for span_gain = span_ladder^`q` | **904** |

The registered model reads `m_k` off the alignment scale ladder. On this stack the
ladder does not contain a magnification ramp -- it spans 0.02% and is not even monotone
in `k`. Producing a 23.5% gain span from it requires an exponent of 904 where physics
says 2. **This route is refuted on this stack, arithmetically, without fitting.**

## G2. The EXIF route lands, with zero free parameters, and explains two thirds

`flower-bud-alone-cpl` is **Manual** exposure program and Manual exposure mode.
`SonyExposureTime` (1/6 s), `SonyFNumber` (5.8) and ISO (100) are **constant across all
205 frames** -- one distinct value each. There is no autoexposure confound. But the
camera's recorded *effective* f-number does move:

| quantity | value |
|---|---|
| `SonyFNumber2` (N_eff) frame 1 -> frame 205 | **13.50 -> 12.60**, monotone, `corr(N_eff, k)` = **-0.9940** |
| predicted gain span `(N_eff,max / N_eff,min)^2` | **1.1480** |
| fitted gain span | **1.2350** |
| share of fitted log-span explained | **65.4%** |
| unexplained residual | **34.6%**, fitted/predicted = **1.0758** |

So **65.4% of the photometric drift this project fits with 205 free parameters is
predicted by a number the camera already wrote into every file, with zero free
parameters.** That materially weakens M122's harm mechanism, which requires the gain to
be free enough to absorb scene content. Two thirds of it is not free. It is not,
however, the whole story: a 7.58% residual remains and I cannot attribute it.

## G3. An independent cross-check of the magnification ramp

`N_eff/N = 1 + m/p`, so EXIF gives `m/p` per frame directly: **1.3276 -> 1.1724**, a
**13.24%** linear span in magnification.

In `V-veiling.md` I measured the subject silhouette's linear drift across the same
bracket, from the rendered frames, as **12.60%**.

**Two fully independent routes -- the camera's effective f-number, and my own silhouette
measurement on the pixels -- agree to 0.64 percentage points.** The magnification ramp
is real and it is about 13%.

That closes an open question from `V-veiling.md` and opens a worse one: **the aligner's
fitted scale ladder spans 0.0233%, which is 540x too small to be tracking a 13%
magnification ramp.** I am not asserting the aligner fails to correct magnification --
it may carry it in a term I did not parse out of the warpmap. But the ladder I parsed
does not contain it, and two independent measurements now say the ramp exists. This
should be routed to BUILD-SHARP.

## G4. `p` is not identifiable, and I am not reporting a number for it

Only the ratio `m/p` is observable. EXIF gives `N_eff/N`, which **is** `1 + m/p`
identically, so it contributes zero information about `p` separately. My silhouette
measurement gives `m` only up to an unknown pixels-to-magnification constant, so
regressing one on the other returns the lumped `c/p` and never `p`.

The registered sanity bound of 0.3 to 1.5 is therefore unreachable, and **no fitted `p`
appears in this report.** This is not a novel lens measurement and should not be written
up as one.

It is, however, one cheap capture away from being real: **`p` becomes identifiable the
moment one bracket contains a physical scale reference** -- a stage micrometer or ruler
in frame gives absolute `m`, and `p = m / (N_eff/N - 1)` follows per frame with the
existing EXIF. `FocusDistance2` is present but quantised to 6 distinct values over 205
frames (0.2707 to 0.2878 m) and is not a substitute.

# The number that does not fit

**`k_background` = 1.0287, CI [1.0021, 1.0622].** Away from both the subject and the
election seams, `--photometric` *increases* high-frequency energy by 2.9%, and the CI
excludes 1.00. Under a pure "the correction is a gentle level equalisation" story this
number should be 1.000. It is not, in five of six sensitivity cells (1.0107 to 1.0524).

I do not have an explanation I can defend. The candidates are that my seam mask leaks --
non-seam background at `tau` = 8 still contains sub-threshold index jumps that
`--photometric` sharpens rather than removes -- or that equalising levels genuinely
restores real backdrop micro-texture that level scatter was washing out. The second
would be good news and I have not earned the right to claim it.

It matters because it is the same sign as the effect that would make K2 read *harm* if
it appeared on the subject, and it did not appear on the subject. Flagging it rather
than smoothing it.

Second, smaller: the seam set is **74.7% of the frame** at the registered threshold.
"Seam" is not a thin line on this stack; the election is fragmented nearly everywhere.
That is a fair criticism of the word, not of the partition, and it is why C3's
decomposition by distance is the row that should be quoted rather than C2's.
