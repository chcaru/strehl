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
