# M13 — the focus-measure window optimum, and what a depth discontinuity does to it

**Status:** measured. Answers SYNTHESIS §10 open question 15 (both halves).
**Experiment:** `experiments/m13-window-depth/` — harness, controls, chain script, committed CSVs.
**Reproduce:** `experiments/m13-window-depth/run-m13.ps1`, then `python m13_analyse.py --out data/analysis.txt`.
**Pre-registered before any data was read:** `experiments/m13-window-depth/PREREGISTRATION.md`, commit `c92d683`.

Every claim below carries a label. `MEASURED` = a number this milestone
produced. `VERIFIED` = a number produced twice through disjoint paths.
`DERIVED` = follows from a stated rule applied to measured numbers.
`ARGUED` = a mechanism I believe and have not isolated. `UNVERIFIED` = a
belief I am flagging so nobody quotes it as fact.

---

## The one-paragraph answer

M11 recommended Tenengrad under an **11×11** box (`tenengrad-w5`) and noted its
post-hoc extension was still improving at 23×23. It was right to be suspicious.
On the plants M11 used, the objective **cannot** turn over — a fronto-parallel
plant has no interior optimum for a symmetric box window, so "still improving at
23×23" carried no information at all `MEASURED`. Once an **occluding depth
discontinuity** is planted, the objective turns over sharply and reproducibly at
**window radius 13, a 27×27 box** `MEASURED`, and the basin **w11–w15 (23×23 to
31×31)** is flat to within ~0.9 DN. M11's 11×11 is not merely a lower bound; it
is **dominated** — `tenengrad-w8` (17×17) beats it in **36 of 36** edge cells,
on lower merged noise, at identical cost `MEASURED`. The implementation should
use **`tenengrad-w13`, a 27×27 box**. A spatially adaptive rule has real oracle
headroom (5–47%) but **none of the realisable rules I tested capture it**
(best +5.4%, usually negative), so adaptivity is *not* recommended and *not*
closed — it becomes a new open question `MEASURED`.

---

## 0. Provenance and the guards that had to pass first

### 0.1 The corpus was not touched `VERIFIED`

| path | files before | bytes before | files after | bytes after |
| --- | --- | --- | --- | --- |
| `C:\dev\macro` | 18530 | 286,893,514,060 | 18530 | 286,893,514,060 |
| `D:\macro-dark-frames` | 242 | 8,179,392,512 | 242 | 8,179,392,512 |
| `D:\personal\macro` | 632 | 18,194,001,522 | 632 | 18,194,001,522 |

`data/audit-before.txt` and `data/audit-after.txt` are byte-identical, including
the newest mtime in each tree. A third audit taken after the report was written
(`data/audit-final.txt`) is identical again.

**A gotcha worth recording `MEASURED`.** Verifying the audit with an ad-hoc
`Get-ChildItem -Recurse -File C:\dev\macro | Measure-Object` returns **17449**
files / 286,581,830,721 bytes — 1081 files and ~312 MB *short* — and looks
exactly like evidence that something was deleted. It is not. `Get-ChildItem`
silently omits hidden and system files without `-Force`; adding `-Force` returns
18530, matching the harness audit exactly. The checking tool was wrong, not the
thing being checked. Anyone re-verifying a corpus audit in PowerShell must pass
`-Force`.

Incidental finding `MEASURED`: `C:\dev\macro\test\119MSDCF` and
`D:\personal\macro\119MSDCF` are **the same 33 frames**. Running the whole edge
sweep against each produced a **byte-identical** CSV
(sha256 `F076E402…D11798`, `data/mirror-check.txt`). The `D:` tree is a mirror,
not an independent stack; nothing in this project should treat them as two
samples.

### 0.2 Gate 0 — M11's published numbers reproduce from M11's own CSVs `VERIFIED`

`m13_reproduce_m11.py` re-derives **23** published M11 figures (10 × N, 6 × S,
7 × φ) from `experiments/m11-focus-bakeoff/data/*.csv` to within ±5×10⁻⁵,
including the A4 extension rows. `data/gate0-reproduce-m11.txt`.

The gate carries its **own negative control**, because the brief warned that a
previous analysis silently kept the last row per operator:

| reader | `ring-1-3` N | `tenengrad-w5` S |
| --- | --- | --- |
| unstratified (last row per measure) | 1.1410 | 0.7376 |
| stratified (`roi_kind`, `width`) | **1.3475** | **0.8007** |
| M11 published | **1.3475** | **0.8007** |

Both unstratified readers disagree with the published value; both stratified
ones agree. Every table in `m13_analyse.py` names the stratum it filtered on.

### 0.3 Gate 1 — the same numbers reproduce from the RAW files `VERIFIED`

Gate 0 reads M11's CSVs. Gate 1 re-decodes the ARWs through M13's own harness
and never touches M11's data — **disjoint measurements** (SYNTHESIS §5 item 20).
On `109MSDCF`, ROI `2272,1344,256,256`:

| | M13 measured | M2 published |
| --- | --- | --- |
| `ring-1-3`, regulariser width 1 | **1.2527×** | 1.2527× |
| `ring-1-3`, regulariser width 17 | **1.0737×** | 1.0737× |

Exact to 4 dp through an independent decode, tile, focus-volume and merge path.
`data/xcheck-109MSDCF.txt`.

### 0.4 The harness self-test — 27/27 `MEASURED`

`data/selftest.txt`. Groups A (the window axis means what its name says),
B (the centre-tap decomposition), C (the occluding-edge plant), D (the halo
metric's nulls, positive control, complementarity control and chance control),
E (tile exactness at the widest window — project rule 7's corollary).

### 0.5 A trap I fell into, disclosed

`experiments/m11-focus-bakeoff/run-m11.ps1` does **not** list the ROIs that
appear in M11's committed CSVs. I ran the first noise and planted sweeps from
the script's ROIs, got numbers that did not reproduce M11, and had to re-run
against the ROIs actually present in `noise-*.csv` and `planted-*.csv`. The
quick discriminator: a flat ROI has `single_sigma ≈ 28–30 DN`, a detail ROI
`≈ 630–700 DN`. `run-m13.ps1` hard-codes the committed-CSV ROIs.

### 0.6 A naming collision to state loudly

**"Halo" already means something else in this project.** SYNTHESIS fact 32 and
§3.4.1 B1 use `halo()` for the *rectangle expansion* a plugin needs
(19.42 / 32.39 / 89.23 plane px) — an alignment and warp margin. This report is
about the *artifact*. I use **"occlusion halo"** or **"edge bleed"** throughout
and never the bare word.

---

## 1. Where the window optimum sits on continuous plants

### 1.1 The merged-noise axis does not turn over — it asymptotes `MEASURED`

N = σ(merged) / σ(single middle frame), both spatial sd over the same flat ROI,
median over four flat ROIs per stack, then mean over the two stacks; regulariser
`width = 1`, stratum `roi_kind = 'flat'`. Same rule as M11.

| w | 0 | 1 | 2 | 3 | 5 | 8 | 11 | 13 | 15 | 20 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N | 1.0632 | 1.3334 | 1.2255 | 1.1771 | **1.1324** | 1.1019 | **1.0908** | 1.0864 | 1.0851 | 1.0849 | 1.0810 | 1.0810 | 1.0778 |

The w0 / w2 / w5 / w8 / w11 entries reproduce M11's published N **exactly to
4 dp** — but from the RAW files through M13's harness, not from M11's CSVs.
That is a genuinely disjoint reproduction, not the circularity of §5 item 20.

N falls monotonically over w1–w40 and **asymptotes near 1.078**. Going from
M11's w5 to w11 buys 0.042; from w11 all the way to w40 buys only 0.013. There
is no interior optimum on this axis and the sweep does not need extending
further to know it — the remaining distance to the asymptote is smaller than
the step between adjacent windows.

Note that bare Sobel (`w0`, N = 1.0632) beats every windowed variant on N. It is
useless anyway: its selectivity is 0.31. The noise axis alone never selects a
window.

### 1.2 A fronto-parallel plant **cannot** turn over — and that is why M11's A4 said nothing `MEASURED` + `ARGUED`

Continuous plant, 45 frames, planted frame 22, three detail ROIs per stack,
stratum `roi_kind='detail'`, `width=1`, mean over two stacks:

| w | 0 | 5 | 11 | 15 | 20 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact-hit acc | 0.3128 | 0.7855 | 0.9194 | 0.9479 | 0.9633 | 0.9761 | 0.9867 | **0.9946** |
| mean \|k − truth\| | 6.04 | 2.22 | 1.09 | 0.74 | 0.54 | 0.36 | 0.20 | **0.064** |

Both axes improve monotonically all the way to w40 (an 81×81 box, more than a
quarter of the ROI's width). **Reported as "no turnover found within the sweep",
never as an optimum** — that is the rule I registered.

The mechanism `ARGUED`: on a fronto-parallel plant the true depth is *constant*,
so a box average of the focus response is an unbiased estimator of a constant,
and every additional tap is pure variance reduction. There is nothing for the
window to smear. **M11's A4 extension was measured on exactly this
configuration.** Its observation that both axes were "still improving at 23×23"
is therefore not weak evidence of an optimum beyond 23×23 — it is *no* evidence,
because that experiment could not have produced any other result.

This is the first half of SYNTHESIS fact 42 sharpened. Fact 42 says the optimum
only exists once the plant has depth structure. M13 measures that **depth
structure is not sufficient**: it must be *discontinuous*. See §1.3.

### 1.3 A depth *ramp* turns over on one axis and not the other `MEASURED`

Tilt is planted in DN-frames per pixel: the true frame index varies linearly
across the ROI.

| tilt | 0 | 4 | 8 | 16 | 32 |
| --- | --- | --- | --- | --- | --- |
| argmax of exact-hit acc | w40 (endpoint) | **w33** | **w18** | **w11** | **w8** |
| argmin of mean \|k − truth\| | w40 (endpoint) | w40 (endpoint) | w40 (endpoint) | w40 (endpoint) | w40 (endpoint) |

The two axes **disagree**, and the disagreement is not noise — it is exact and
holds at every tilt. Reporting only one of them would have produced a confident
wrong answer in either direction.

The mechanism `ARGUED`: a symmetric box average of a **linear** ramp is
unbiased — the over- and under-estimates on the two sides cancel exactly at the
centre tap. So the *mean* error keeps falling with window, because variance
keeps falling and bias stays zero. But exact-hit accuracy is a **quantised**
statistic: it counts pixels whose estimate lands on precisely the right integer
frame. Averaging over a ramp spreads the estimate over a range of frames
proportional to `tilt × (2w+1)`, and once that spread exceeds one frame the
exact-hit rate falls even though the mean is still centred. That predicts the
argmax should scale roughly as `1/tilt`, and it does: 33 / 18 / 11 / 8 against
tilts 4 / 8 / 16 / 32 — successive halvings of the tilt move the optimum by
factors of 1.83, 1.64, 1.38. `DERIVED` from the measured argmaxes; the
prediction is qualitative and the fit is not exact, so I label the mechanism
`ARGUED` and not established.

**A linear ramp is the friendliest possible non-flat plant for a box window.**
That is precisely why it fails to settle the question, and why the brief's
insistence on a discontinuity was correct.

### 1.4 A correction: M11 A1's φ claim is false when extended `MEASURED`

φ is the centre-tap fraction — the share of the operator's sensitivity at a
point that comes from the point itself. M11 A1 reported φ rising monotonically
with window. Its published values at w0/w2/w5/w8/w11 are
**0.0335 / 0.0612 / 0.0728 / 0.0872 / 0.1089**, and M13's φ mode reproduces all
five to ±5×10⁻⁵ under M11's own ROI and reach (Gate 0, §0.2). The brief carries
the monotonicity forward as verified.

**The rise is real over M11's five sample points and the monotonicity claim is
false in two separate ways.** Extended to w40 on real 109MSDCF texture, ROI
`2080,1056,512,512`, reach 43 px (uniform across the sweep, set from the widest
operator so no arm is truncated):

| w | 0 | 1 | 2 | 3 | 5 | 8 | 11 | 13 | **15** | **17** | 18 | 20 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| φ (δ=8 DN) | 0.0290 | 0.0882 | 0.0685 | 0.0631 | 0.0676 | 0.0933 | 0.1238 | 0.1390 | 0.1471 | **0.1474** | 0.1462 | 0.1415 | 0.1304 | 0.1235 | 0.1146 |

1. **φ peaks at w15–w17 and then declines** `MEASURED`. The turnover reproduces
   at all three probe amplitudes (δ = 1, 8, 32 DN) with the argmax at w17 in
   every one. By w40, φ = 0.1146 — back below its w13 value.
2. **φ is not even monotone at small w** `MEASURED`. On this ROI it *spikes* at
   w1 (0.0882), dips to a local minimum at w3 (0.0631), and only then begins the
   rise M11 saw. M11's ladder (w0/w2/w5/w8/w11) does not sample w1 or w3, and on
   M11's own ROI the five sampled points happen to be monotone. Whether the w1–w3
   dip is ROI-specific or general I did not test — one ROI `UNVERIFIED`.

I am not calling M11's *numbers* an error: A1's five values are correct and I
reproduce them. The claim of **monotonicity** was an extrapolation past the data
in one direction and an interpolation across an unsampled dip in the other. It
is the same class of error as the A4 window claim — both come from stopping at
w11 with a coarse ladder.

The un-normalised arm shows why. With `Norm::None`, φ is a pure **dilution**:

| w | 1 | 2 | 3 | 5 | 8 | 11 | 15 | 20 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| φ measured | 0.0686 | 0.0294 | 0.0162 | 0.00712 | 0.00314 | 0.00176 | 0.000985 | 0.000570 | 0.000345 | 0.000217 | 0.000149 |
| 1/(2w+1)² | 0.1111 | 0.0400 | 0.0204 | 0.00826 | 0.00346 | 0.00189 | 0.001041 | 0.000595 | 0.000356 | 0.000223 | 0.000152 |
| ratio | 0.62 | 0.73 | 0.80 | 0.86 | 0.91 | 0.93 | 0.95 | 0.96 | 0.97 | 0.98 | 0.98 |

`DERIVED` + `MEASURED`: **φ_nonorm(w) → 1/(2w+1)² asymptotically**, ratio rising
smoothly from 0.62 at w1 to 0.978 at w40. The derivation (a box mean over
(2w+1)² taps dilutes any single tap by that factor) and the measurement (a
finite-difference probe on real texture) are disjoint. The shortfall at small w
is the Sobel's own 3×3 support, which is not a point. And φ_nonorm at w0 is
**exactly 0.000000000**, confirming M11 A1's φ = 0 result for bare Sobel.

So: **windowing alone drives φ monotonically to zero.** The rise M11 saw is
entirely a property of the *pointwise normaliser*, whose own 1-px centre tap
becomes a larger share of a shrinking total — until the window gets wide enough
that the normaliser's neighbourhood term dilutes too, which is the turnover at
w15–w17.

*Practical consequence*: the `focus.rs` test `centre_tap_fraction_is_the_value_m9_measured`
pins φ = 1/18 and 49 taps for `ring(1,3)`. At `tenengrad-w13` the tap count is
**(2·14+1)² = 841** `DERIVED` (support radius = 1 + w; verified in self-test
group A at w0/w2/w5/w11/w20/w40) and φ is **0.1390** on 109MSDCF real texture at
δ = 8 DN `MEASURED`. The φ figure is texture-dependent — it is *not* an analytic
constant like 1/18 — so pinning it to 4 dp would be pinning a property of one
ROI. See §6.4 for what I think the test should assert instead.

---

## 2. The halo metric

### 2.1 The plant

No plant in M11 contained a depth discontinuity, so I had to build one. It is a
textbook Porter-Duff `over` composite of **two real corpus textures** at two
different planted depths — no synthetic patterns, so the noise and detail
statistics are the sensor's own:

```
sigma_n(k) = sigma0 + alpha*|k - w_near|      near (occluding) layer defocus
sigma_f(k) = sigma0 + alpha*|k - w_far|       far layer defocus
N_k = blur(T_near * M, sigma_n)               premultiplied occluder
A_k = blur(M,          sigma_n)               its coverage, same kernel
F_k = blur(T_far,      sigma_f)
I_k = N_k + (1 - A_k) * F_k
ideal = composite(sigma0, sigma0)             both layers in focus at once
```

Two design points matter. Pre-multiplying by the mask and blurring the mask with
**the same kernel** keeps every output pixel a convex combination of real sensor
values, so no brightness is invented at the boundary. And nothing is resampled
(SYNTHESIS §5 item 11) — the layers are read at integer pixel offsets.

The plant self-tests (group C): with `w_far == w_near`, frame `w` is
**byte-equal** to `ideal` (max difference 0.00 DN) — an exact null. Far from the
boundary each layer's own frame is exactly ideal. Geometries: vertical edge,
horizontal edge, and a bar (an occluder *narrower* than the window — the
configuration a wide window should destroy).

### 2.2 The floor: no per-pixel selector can win at an occluding boundary `MEASURED`

At the boundary itself, `ideal` contains a mix of both layers within one pixel.
No choice of a single source frame can reproduce it. An **oracle** built from
the noise-free stack — per pixel, the frame whose value is closest to ideal —
still has RMS **294.96 DN** at d ∈ [0, 6) (self-test group C).

This is why the headline metric is **excess over the floor**, not raw error:
`E_excess = band_rms − floor`, where the floor is that same oracle evaluated on
the *noise-free* stack for that exact cell. It is a property of the cell, not of
the window, and is subtracted identically from every window — so the ranking is
untouched, but the *magnitudes* become interpretable as damage the operator is
responsible for. On `109MSDCF/vertical` the floor is 0.00 DN at step 0 and
29.55 DN at step 32, over the same band, and is constant across all 20 windows
in each cell (`data/analysis.txt` §4). The self-test's 294.96 DN is a different
quantity — a narrower band, d ∈ [0, 6), on the self-test scene — and the two are
not comparable.

> **H = E_excess = mean_band RMS(merged − ideal) − mean_band RMS(oracle − ideal)**

in DN. Subtracting a floor computed from the *noise-free* stack keeps the floor
from moving with the noise realisation. A metric that charged the operator for
physically irreducible error would rank windows by how much boundary they
happen to contain.

### 2.3 The four parts, and why one is not enough

| part | what it measures | null | positive control |
| --- | --- | --- | --- |
| `W_bleed` | equivalent width in px over which the selector elects a frame **strictly nearer the wrong layer** | **exact 0** | recovers planted width exactly |
| `H` = `E_excess` | DN of reconstruction error above the physical floor, in a band around the boundary | exact 0 under ground-truth selection | — |
| `mis_width`, `dmae` | width / mean magnitude of selections off by ≥ 2 frames | ≈ 0, **no exact null** | recovers planted width exactly |
| `bias(d)` | *signed* mean error by distance | 0 | — |

`W_bleed(d) = Σ_{d=1}^{baseline_lo−1} max(0, wrong(d) − baseline)`, baseline =
median of `wrong(d)` over the far band. Ties are **not** counted as wrong; that
is exactly what makes the zero-step null read exactly zero.

`bias` is in the set because a human sees bright and dark fringes, and RMS
cannot show sign. It is reported but did not drive any decision here.

### 2.4 The controls — all four registered before the data `MEASURED`

From `data/selftest.txt`:

**NULL 1 (ground truth).** Feed the metric the true frame map. `bleed_bg` and
`bleed_fg` = 0.000e0 px, `mis_bg`/`mis_fg` = 0.000e0 px, `excess` = 0.000e0 DN.
Exact, not approximate.

**NULL 2 (a real operator, an intensity edge, no depth step).** `tenengrad-w11`
on a scene with both textures, the composite, the noise, and a hard *intensity*
edge — but `w_far == w_near`. `bleed_bg = 0.000e0 px`, `mis_bg = 0.000 px`. The
metric does not fire on an intensity edge. This is the control that matters: it
proves the metric is reading *depth* discontinuity and not *any* edge.

**POSITIVE.** Plant a halo of known width by dilating the wrong-layer selection
by R px:

| planted R | 1 | 3 | 8 | 17 | 32 | 64 |
| --- | --- | --- | --- | --- | --- | --- |
| `bleed_width` | 0.0 | 2.0 | 7.0 | 16.0 | 31.0 | 63.0 |
| `mis_width` | 0.0 | 2.0 | 7.0 | 16.0 | 31.0 | 63.0 |

Exact recovery of **R − 1**, because `d = 0` is the first covered pixel and the
sum runs from `d = 1`. All widths in this report are on that convention.

**COMPLEMENTARITY (the blind spot, measured not asserted).** Elect the frame
*midway* between the two layers within R px of the boundary. It is wrong for
both layers but not strictly nearer either, so `W_bleed` is blind by
construction:

| planted R | 4 | 12 | 30 |
| --- | --- | --- | --- |
| `bleed_width` | **0.0** | **0.0** | **0.0** |
| `mis_width` | 3.0 | 11.0 | 29.0 |

**CHANCE.** A uniformly random selector: `bleed_bg = 1.59 px` (small) with
`excess = 117.2 DN` (huge). Width and magnitude see different damage, so both
must be reported.

### 2.5 What this metric cannot see — honestly

1. **A compromise election is invisible to `W_bleed`.** Measured in §2.4, and it
   happens *in the real data*: on `109MSDCF/vertical`, step 32, `bleed_fg` falls
   from **18.75 px at w8 to 1.19 px at w33** while `E_excess` *rises* from 25.9
   to 33.5 DN. Reading `W_bleed` alone would have concluded that w33 is nearly
   halo-free. `mis_width` mostly catches this but not always — at w33 it also
   collapses (1.33 px). **Only the oracle-referenced `E_excess` sees through it
   in every case.** `MEASURED`
2. **`mis_width` has no exact null.** Operators mis-select away from edges too,
   so its far-field baseline does real work and the "zero" is empirical
   (0.000 px measured on NULL 2, but not guaranteed).
3. **It cannot see anything a human sees that is not error against `ideal`.**
   Perceptual quality, texture coherence, whether the halo *looks* like a halo
   rather than blur — none of that is in scope. `ARGUED`
4. **It cannot see failures on real occlusion boundaries with parallax.** The
   plant has no disocclusion: both layers are fully observed everywhere. A real
   macro stack has pixels visible in *no* frame. `UNVERIFIED` — untested.
5. **`acc` and `acc_band` are nested sets** (the band is inside the ROI). They
   must never be quoted as agreeing. `far_rms` and `band_rms` *are* disjoint
   pixel sets and may be compared.
6. **One texture pair per stack.** The 119MSDCF horizontal cell behaves
   differently from every other cell (§3.6, §6.2) and I cannot tell from this
   data whether that is a property of occlusion geometry or of that texture
   pair.

---

## 3. What a depth discontinuity does to the trade-off — quantified

Design: 2 stacks × 3 geometries × 6 depth steps (0, 2, 4, 8, 16, 32 frames) ×
20 windows × 3 noise seeds = 7,200 measurements. `data/edge-*.csv`.

### 3.1 The discontinuity is what *creates* the optimum `MEASURED`

The decision rule is **regret**: `regret(w, cell) = E_excess(w, cell) −
min_w' E_excess(w', cell)`, seed-averaged, then aggregated over cells. Regret,
not raw error, because a cell containing more boundary has a higher floor and
would otherwise dominate.

| cell set | n | argmin of mean regret | argmin of worst-case regret |
| --- | --- | --- | --- |
| **step = 0 (no discontinuity)** | 6 | **w40 — ENDPOINT** | **w40 — ENDPOINT** |
| step > 0 | 30 | **w13 — interior** | **w13 — interior** |
| all | 36 | **w13 — interior** | **w13 — interior** |

That is the null/positive pair for the whole of question 15b, and it is as clean
as this project gets. **Remove the depth step and the objective stops turning
over** — it runs to the wide endpoint with regret 0.000 DN at w40 and never
looks back. **Put the step back and an interior optimum appears at w13.**

The same structure holds under two *other* objectives, which matters because a
recommendation that depends on which of my own metrics I picked is not a
recommendation:

| objective | step = 0 | step > 0 |
| --- | --- | --- |
| `E_excess` (DN over the floor) | w40 ENDPOINT | **w13** interior |
| max `mis_width` (px) | w40 ENDPOINT | **w23** interior |
| `dmae_band` (frames) | w40 ENDPOINT | **w15** interior |

All three agree on the *qualitative* claim (no interior optimum without a
discontinuity; a clear one with) and place the quantitative optimum in
**w13–w23**. `E_excess` is the one with an exact physical floor and the
strongest justification, and it is the narrowest of the three — so following it
is the conservative choice.

### 3.2 The turnover is sharp, and the cost of getting it wrong is large `MEASURED`

Mean and worst-case regret across the 30 depth-step cells:

| w | 8 | 9 | 10 | 11 | 12 | **13** | 15 | 17 | 18 | 20 | 23 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mean regret (DN) | 7.01 | 5.52 | 4.51 | 3.85 | 3.46 | **3.17** | 4.04 | 6.19 | 7.36 | 11.02 | 20.90 | 27.60 | 33.28 | 37.71 |
| worst regret (DN) | 39.9 | 32.7 | 26.4 | 21.0 | 16.3 | **12.1** | 25.3 | 35.7 | 37.7 | 47.2 | 101.4 | 130.5 | 138.3 | 132.0 |

Going from w13 to w40 costs **12× the mean regret**. Going from w13 down to
M11's w5 costs **5.5×** (17.50 DN mean regret at w5). The penalty for being too
wide is steeper than for being too narrow, which is the opposite of what the
continuous-plant measurements alone would suggest.

**Stability `MEASURED`:** rebuilding the entire regret table inside each of the
three noise seeds independently gives argmin **w13 in all three**, on both mean
and worst-case regret. The median seed-to-seed sd of `E_excess` is **0.193 DN**,
against a w12→w13 gap of 0.29 DN and a w13→w15 gap of 0.87 DN. The choice is
resolved above the noise floor, but only just at w12/w13 — hence "basin", not
"point", in the recommendation.

### 3.3 The damage is spatially explicit `MEASURED`

`data/edgeprof-*.csv`, `m13_profiles.py`. 109MSDCF, vertical boundary, depth
step 32. `d < 0` is the near (occluding) layer, `d ≥ 0` the far layer.
Reconstruction error against `ideal`, in DN:

| d | −32 | −16 | −8 | −4 | **0** | 4 | 8 | 12 | 16 | 24 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **w5** | 52.9 | 46.9 | 38.3 | 35.3 | 157.4 | 128.6 | 73.5 | 50.8 | 40.0 | 32.0 | 39.0 |
| **w13** | 29.5 | 26.5 | 24.9 | 23.8 | 158.2 | 144.5 | 88.6 | 46.1 | 30.1 | 18.1 | 22.3 |
| **w40** | 17.7 | 15.3 | 15.7 | **60.2** | 156.2 | **185.4** | **173.6** | **107.0** | 30.3 | 16.5 | 16.6 |

Read across, then down. At **d = 0** all three are ~157 DN — the irreducible
floor, identical for every window, as it must be. In the **far field**
(|d| ≥ 24) the ordering is w40 < w13 < w5: the wide window is much better on
smooth surface, exactly as §1.2 predicts. In the **near field** (d = 4…12) the
ordering **reverses**: w40 is 185 / 174 / 107 DN where w13 is 145 / 89 / 46.

That is the occlusion halo, resolved in space. **A wide window's advantage on
smooth surfaces is paid for at the boundary, and the payment is localised in a
band roughly as wide as the window's support.** w40 also damages the *near*
side (60.2 DN at d = −4, against 15.7 DN at the next sample out, d = −8) — the
smear is bidirectional.

### 3.4 The optimum is not an artifact of the plant `MEASURED`

If the measured optimum simply tracked the size of the planted feature, it would
be an artifact. Sweeping the occluding bar's width over an order of magnitude
(`data/barwidth-109MSDCF.csv`):

| bar width (px) | 8 | 16 | 24 | 48 | 96 |
| --- | --- | --- | --- | --- | --- |
| argmin, step 8 | w6 | w11 | w10 | w17 | w12 |
| argmin, step 32 | w26 | w8 | w10 | w15 | w11 |

No monotone relation — the argmin scatters in w6–w26 with no trend. `E_excess`
at w13 is within **3.5 DN** of the per-cell minimum in **7 of the 10** cells
(rule: `E_excess(w13, cell) − min_w E_excess(w, cell)`), and within 0.2 DN in
both 96 px cells. The three exceptions are 8 px/step 8 (4.8 DN),
16 px/step 32 (6.9 DN) and — the worst — the **8 px bar at step 32**, where w13
costs **13.1 DN** over the w26 optimum. A very thin occluder at a large depth
step is the one configuration where w13 is clearly not the right window; I have
not chased it further.

Residual scene dependence of a few window steps is real and is the honest reason
the recommendation is a basin.

### 3.5 M11's metric class is structurally blind to this — quantified `MEASURED`

The brief's central hypothesis for 15b. Direct test: in each depth-step cell,
compare the window M11's **per-pixel exact-hit accuracy** would choose against
the window `E_excess` chooses.

- The accuracy argmax is **strictly wider** than the `E_excess` argmin in
  **30 of 30** cells. Strictly narrower in **0 of 30**.
- Mean penalty for following accuracy: **18.48 DN** of excess error.
- Worst: **101.35 DN** (119MSDCF, bar, step 32 — accuracy picks w23, `E_excess`
  picks w10).

Restricting accuracy to the band around the boundary (`acc_band`) *helps* but
does **not** fix it — it still picks wider than `E_excess` in most cells
(e.g. 109MSDCF/bar/step 32: `acc_band` → w20, `E_excess` → w10).

The single clearest illustration, 109MSDCF/vertical/step 32:

| w | 0 | 5 | 8 | 13 | **15** | 20 | 26 | 33 | 40 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| exact-hit `acc` | 0.266 | 0.720 | 0.824 | 0.894 | 0.908 | 0.927 | 0.943 | 0.957 | **0.967** |
| `E_excess` (DN) | 76.6 | 30.6 | 25.9 | 22.9 | **22.7** | 25.0 | 30.5 | 33.5 | 37.8 |
| `bleed_fg` (px) | 7.9 | 15.1 | 18.8 | 17.0 | 15.8 | 12.7 | 9.2 | **1.2** | 1.5 |

**M11's metric rises monotonically to w40 on a scene with a 32-frame depth
discontinuity in it.** It reports the widest window as the best one while the
reconstruction is 66% worse than at the optimum. The brief's claim that "a
haloed edge can still elect the correct source frame at every individual pixel
while looking obviously wrong" is confirmed — and the reason is visible in the
third row: the damage concentrates in a band that is a small fraction of the ROI
by area, so a per-pixel average over the ROI barely moves.

Note also `bleed_fg` collapsing at w33 — the disclosed blind spot of §2.5, item
1, occurring in real data rather than in a control.

### 3.6 The depth step's magnitude barely matters `MEASURED`

Across the five non-zero steps on 109MSDCF/horizontal, the argmin is w13 at
steps 2, 4, 8 and 16, and w15 at step 32. On 109MSDCF/vertical it is w18 / w17 /
w13 / w13 / w15. The optimum is set by **whether** there is a discontinuity and
by the local geometry, far more than by **how deep** it is. A 2-frame step is
already enough to move the optimum from the endpoint to the interior.

---

## 4. Should the answer be adaptive?

The brief asks this directly and warns against inventing complexity the data
does not demand. I measured it.

Setup: two fixed windows, plus an **oracle** (per pixel, whichever window's
output is closer to `ideal` — reads the answer, a strict upper bound, never a
proposal), plus a **realisable** rule (use the narrow window wherever the two
windows' selections disagree by more than τ frames; no ground truth read),
τ ∈ {1, 2, 3, 4, 6, 8}. Six window pairs × five depth steps.
`data/adaptive-109MSDCF.csv`.

| narrow / wide | step | E_narrow | E_wide | E_oracle | oracle gain | best realisable rule | rule gain |
| --- | --- | --- | --- | --- | --- | --- | --- |
| w2 / w40 | 8 | 50.43 | 47.14 | 25.06 | **46.8%** | τ=6 | **−5.7%** |
| w5 / w40 | 8 | 38.30 | 47.14 | 23.77 | **38.0%** | τ=2 | +1.2% |
| w8 / w40 | 8 | 34.27 | 47.14 | 26.25 | **23.4%** | τ=3 | +1.1% |
| w11 / w40 | 8 | 33.36 | 47.14 | 29.46 | 11.7% | τ=1 | +0.3% |
| w2 / w40 | 16 | 60.28 | 69.95 | 39.96 | **33.7%** | τ=8 | **+5.4%** |
| w5 / w15 | 8 | 39.02 | 35.80 | 24.01 | **32.9%** | τ=2 | −8.1% |

Gain rule: `100 × (min(E_narrow, E_wide) − E_arm) / min(E_narrow, E_wide)`,
band RMS.

**The oracle gain is large and real — 5.7% to 46.8% across the 24 configurations
that contain a discontinuity (1.5% to 46.8% across all 30, the widest gaps being
the six `step = 0` nulls where there is nothing to adapt to). There is genuine
headroom for spatial adaptivity `MEASURED`.** But the realisable rule captures
essentially none of it: across all 30 configurations its gain ranges from
**−153.6% to +5.4%** and it is negative in **18 of 30**; restricted to the 24
discontinuity cells it ranges **−70.6% to +5.4%** and is negative in **12 of
24**. Making the selection worse is not a rare failure mode of the disagreement
gate; it is its typical behaviour.

**Pre-registration deviation, disclosed.** I registered a 5% threshold *on the
oracle*: "if the oracle beats the better fixed window by <5%, recommend a single
global window." By that letter, the oracle exceeds 5% in 28 of 30 configurations
and the registered verdict is "ADAPTIVE". **I registered the wrong test.** The
oracle reads the answer; I documented it in the harness as "a strict upper
bound, never a proposal" *before* running it, and then registered a threshold on
it anyway. The decision-relevant quantity is the realisable rule, and on that
the answer is unambiguous. I am reporting the registered result, saying it fires,
and overriding it on stated grounds rather than quietly re-cutting the
threshold.

**Verdict `MEASURED`: recommend a single global window.** Adaptivity is not
rejected — it is *unrealised*. The headroom exists; the obvious gate does not
reach it. That becomes a new open question rather than a closed one (§7).

---

## 5. Cost

`data/cost-109MSDCF.csv`, 9 repetitions, 0.353 Mpx tile, 109MSDCF.

| measure | w0 | w1 | w5 | w11 | **w13** | w18 | w20 | w40 | `ring-1-3` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ms/frame/Mpx | 1.924 | 3.348 | 3.381 | 3.354 | **3.381** | 3.325 | 3.328 | 3.335 | 3.331 |

**Cost is flat in the window radius `MEASURED`.** Spread over w1–w40 is
**2.53%** (rule: `100 × (max − min) / min` over the windowed rows only:
min 3.3251 at w18, max 3.4093 at w9), with no trend in the radius — the two
extremes are at w18 and w9, not at the ends. That is what a running-sum box
filter must do: O(1) per pixel independent of radius. `w0` is cheaper only
because it skips the box filter entirely.

**A wide window is free.** Widening from M11's w5 to w13 costs **+0.00%**
(3.3805 → 3.3806 ms/frame/Mpx) — a coincidence at 4 dp, but the point stands
that the difference is far inside the 2.53% run-to-run scatter.

**Do not cross-quote these against M11's cost table.** M11 published
`tenengrad-w5` at 6.411 and `ring(1,3)` at 5.987 ms/frame/Mpx; M13 measures
3.381 and 3.331 on the same machine. The absolute scales differ by ~1.9× because
the two harnesses time different amounts of work, and I have not reconciled them
`UNVERIFIED`. The claim here is only about the **window axis within M13's own
measurement**, where every row is measured identically.

M13 measures `tenengrad-w5` at **+1.49%** of `ring-1-3` where M11 measured
+7.08% (rule for both: `100 × (t − r) / r`). The direction agrees and neither
gap affects M11's Pareto conclusion — Tenengrad dominates on N and S, and a
smaller cost gap only strengthens it — but the factor-of-4.7 discrepancy in the
gap is unexplained and I flag it rather than paper over it.

---

## 6. The recommendation

### 6.1 The window `MEASURED` + `DERIVED`

> **`tenengrad-w13` — a 27×27 box (radius 13), support radius 14, 841 taps.**

Evidence, in the order it should be weighed:

1. **Regret argmin, both mean and worst-case, on the primary objective**, over
   all 36 edge cells *and* over the 30 depth-step cells (§3.1, §3.2).
2. **Stable across all three independent noise seeds** — argmin w13 in each,
   on both mean and worst-case regret (§3.2).
3. **Better merged noise than M11's choice**: N = 1.0864 vs 1.1324 — the
   noise excess drops from 13.24% to 8.64%, a **34.8% reduction in excess**
   (rule: `(0.1324 − 0.0864)/0.1324`) (§1.1).
4. **Better selectivity on continuous plants**: exact-hit 0.9348 vs 0.7855;
   mean frame error 0.90 vs 2.22 (§1.2).
5. **Free**: +0.00% cost against w5, inside a 2.53% total spread over the
   windowed rows (§5).
6. **Not an artifact of the plant**: the argmin does not track the planted
   feature size (§3.4).

**The honest band.** Mean regret across the depth-step cells is 3.85 / 3.46 /
3.17 / 4.04 DN at w11 / w12 / w13 / w15, against a seed noise floor of 0.19 DN.
The differences are resolved but small. **Anything in w11–w15 (23×23 to 31×31)
is defensible; w13 is the argmin and is what I recommend.** Do not read the
27×27 as precise to the pixel.

### 6.2 If a single number is unwelcome

The fallback with the strongest guarantee is **`tenengrad-w8` (17×17)**: it beats
M11's `tenengrad-w5` in **36 of 36** edge cells with a worst-case single-cell
loss of **0.00 DN** `MEASURED` — a strictly dominating, zero-risk upgrade. It
costs 2.2× w13's mean regret (7.01 vs 3.17 DN), so it is worse, but it cannot be
wrong anywhere M13 measured.

For completeness, cell-by-cell against w5 on `E_excess`:

| candidate | better in | worse in | worst single-cell loss |
| --- | --- | --- | --- |
| w6 | 36/36 | 0 | 0.00 DN |
| **w8** | **36/36** | **0** | **0.00 DN** |
| w9 | 35/36 | 1 | 0.17 DN |
| w11 | 33/36 | 3 | 5.19 DN |
| **w13** | **33/36** | **3** | **6.86 DN** |
| w15 | 32/36 | 4 | 19.92 DN |
| w20 | 25/36 | 11 | 44.29 DN |

All three cells where w13 loses to w5 are in the 119MSDCF horizontal texture
pair, the outlier cell of §3.6. w13's *worst-case regret* is 12.1 DN against
w5's 64.5 DN, so w13 is far safer overall despite losing three head-to-heads.

### 6.3 What the implementation should do

The crate change is not mine to make (`crates/` is out of scope for M13). For
whoever lands it:

- Replace `ring(1,3)` with Tenengrad (Sobel gradient energy) under a **27×27
  box window**, i.e. radius 13, per M11's operator ruling and M13's window
  ruling.
- **Do not make it adaptive.** §4 measured the obvious adaptive rule and it does
  not pay.
- The box filter must be the running-sum form for the cost result to hold; a
  naive (2w+1)² convolution at radius 13 would be ~841× the work.
- **Support radius is 14** (1 for the Sobel + 13 for the box). Anything that
  sizes tile margins or plugin halos from the focus operator's support — the
  `halo()` rectangle expansion of SYNTHESIS fact 32 — must be told, or tiles
  will not be margin-independent. Self-test group E verifies margin-independence
  holds at w5 / w11 / w20 with the correct margin.

### 6.4 The pinned test

`crates/strehl-core/src/focus.rs` has `centre_tap_fraction_is_the_value_m9_measured`,
pinning φ = 1/18 and 49 taps for `ring(1,3)`. M11 correctly said it must be
**updated, not deleted**.

- **Tap count → 841** `DERIVED`, exactly `(2·(1+13)+1)²`. Assert this; it is
  analytic and verified in self-test group A across six windows.
- **φ → do not pin a 4-dp number.** M13 measures φ = **0.1390** at w13 on
  109MSDCF real texture at δ = 8 DN `MEASURED`, but §1.4 shows φ under pointwise
  normalisation is texture- and probe-dependent, unlike the 1/18 for `ring(1,3)`
  which is a property of the kernel alone. Pinning 0.1390 would pin a property
  of one ROI. Suggested `ARGUED`: assert the *analytic* quantity instead —
  un-normalised φ at radius 13 is `1/27² = 0.001372` to within the measured
  ratio 0.94 (§1.4) — or assert a loose bracket such as `0.10 < φ < 0.18` with a
  comment pointing here. This is a judgement call for the implementer, not a
  measurement.

---

## 7. Does this change M11's ruling, and does it close question 15?

### 7.1 M11's operator ruling stands `MEASURED`

Nothing in M13 challenges Tenengrad. Every M13 measurement is *within* the
Tenengrad family; the operator bake-off is untouched, and M11 fact 37 (across 47
operators, none reaches the noise-free bar) is not in question. M13 makes the
Tenengrad case slightly stronger, since the window that was chosen for it was
too narrow on every axis M13 measured.

### 7.2 M11's window ruling is superseded `MEASURED`

`tenengrad-w5` (11×11) is not a lower bound on the optimum, it is **dominated**.
`tenengrad-w8` beats it in 36/36 edge cells at no cost and with lower noise, and
`tenengrad-w13` is the measured argmin. This is the milestone's main correction.

M11's A4 amendment should be read as **structurally uninformative** rather than
incomplete: it was measured on a fronto-parallel plant, where monotone
improvement is forced (§1.2). The right lesson is not "extend the sweep further"
but "that plant could not answer the question."

### 7.3 One published claim is corrected `MEASURED`

**M11 A1's "φ rises monotonically with window" is false when extended.** φ peaks
at w15–w17 and declines to w40 (§1.4), reproducibly at three probe amplitudes,
and on M13's ROI it is not monotone at small w either — a spike at w1 and a
local minimum at w3 that M11's ladder does not sample.
A1's *numbers* are right and M13 reproduces all five to ±5×10⁻⁵; the
monotonicity was extrapolation past the data at the wide end and interpolation
across an unsampled dip at the narrow end.
Un-normalised φ falls monotonically toward `1/(2w+1)²` (ratio 0.62 → 0.978), so
the rise is a property of the pointwise normaliser, not of windowing.

### 7.4 SYNTHESIS fact 42 is sharpened, not refuted `MEASURED`

Fact 42 says the objective's optimum only exists once the plant has depth
structure. M13 measures that **structure is not sufficient — the structure must
be discontinuous.** A linear depth ramp (the friendliest non-flat plant for a
box window) still fails to produce an interior optimum on mean frame error at
any tilt up to 32 DN-frames/px (§1.3). Only a discontinuity produces an interior
optimum on every objective tested (§3.1).

### 7.5 Question 15 closes; two narrower ones open

**Q15 is answered and should be closed.** 15a: the optimum is at radius 13
(27×27), it does turn over, and M11's plants could not have shown it. 15b: a
depth discontinuity moves the optimum from the sweep endpoint to w13 and imposes
up to 138 DN of worst-case regret on windows chosen without it; the answer is a
single global window, not an adaptive rule.

Two new questions, both narrower:

- **The adaptive headroom is real and unclaimed.** The oracle gains 5.7–46.8%
  over the better fixed window across the 24 discontinuity configurations; every
  realisable gate I tried gains ≤5.4% and usually loses (§4). A rule that
  reaches even half the oracle gain would be
  worth more than any window choice. Candidates not tried: gating on the focus
  *curve's* peak sharpness rather than on inter-window disagreement; a
  guided-filter or cross-bilateral regulariser on the selection map; explicit
  occlusion detection.
- **The 119MSDCF horizontal texture pair is an outlier** and I cannot explain it
  (§3.6, §6.2). Its `E_excess` optimum sits at w8 at **all five** depth steps —
  it is the only cell with a constant argmin — while the other five cells scatter
  over w9–w33, and it is the source of every head-to-head loss w13
  suffers against w5. One texture pair per stack is not enough to tell whether
  this is geometry or texture.

### 7.6 What I could not measure

1. **Real occlusion with disocclusion.** The plant observes both layers
   everywhere. Real macro stacks have pixels visible in no frame. `UNVERIFIED`
2. **Human perception.** `E_excess` is DN against an ideal. Whether w13's
   residual halo *looks* acceptable is untested. `UNVERIFIED`
3. **Interaction with the merge regulariser.** Everything here is at `width=1`.
   M2 measured the regulariser suppresses noise strongly (1.2527 → 1.0737); its
   interaction with a 27×27 focus window at an occluding edge is unmeasured.
   `UNVERIFIED`
4. **Curved and oblique boundaries.** Three geometries, all axis-aligned.
5. **Whether the optimum scales with magnification or pixel pitch.** One lens,
   one sensor, one teleconverter. `UNVERIFIED`

---

## 8. Gates

```
cargo fmt --all -- --check                          exit 0
cargo clippy --workspace --all-targets -- -D warnings   exit 0
cargo test --workspace                              exit 0
    test result: ok. 18 passed; 0 failed
    test result: ok. 41 passed; 0 failed
    test result: ok.  8 passed; 0 failed
                     ---
                      67 passed, 0 failed
```

The M13 experiment is its own workspace (`experiments/m13-window-depth/`, empty
`[workspace]` table) and is not in the repo-root workspace, matching M11's
layout. Its own gates: `cargo fmt`, `cargo clippy --release --all-targets -D warnings`,
6 unit tests, and the 27-check self-test, all clean.

**Disclosed:** on the final gate pass the experiment's `cargo test` did not
*compile* — two `#[cfg(test)]` `ProfileConfig` literals had not been updated when
I added the `mis_tol` field mid-milestone. `cargo build --release` does not build
`#[cfg(test)]` code, so the binary that produced every number in this report was
unaffected and the 27-check self-test passed throughout; re-running it after the
fix still gives 27/27. No measurement is affected, but it is exactly the kind of
silent gap that should be caught earlier, and running the experiment's own
`cargo test` should be part of the chain script rather than a final check.

---

## Proposed changes to SYNTHESIS.md and AGENTS.md

*I have not edited either file. Exact paste-ready text follows. Facts are
numbered from 60 as instructed; 50–59 belong to the concurrent milestone.*

### §4 — new facts

```
60. The focus-measure window optimum is at **radius 13 (a 27×27 box)** for
    Tenengrad. Measured by regret against per-cell best over 36 cells
    (2 stacks x 3 occluding-edge geometries x 6 depth steps x 20 windows x
    3 noise seeds), where regret(w, cell) = E_excess(w, cell) - min_w'
    E_excess(w', cell). Argmin of both mean regret (3.17 DN) and worst-case
    regret (12.11 DN), and stable across all three noise seeds independently.
    The basin w11-w15 (23x23 to 31x31) is flat to within 0.9 DN against a
    0.19 DN seed noise floor. [M13 §3.1, §3.2, §6.1]

61. **The optimum exists only because of depth discontinuity.** On the same
    36-cell grid, the 6 cells with zero depth step have their argmin at the
    sweep endpoint (w40, an 81x81 box) with regret 0.000 DN — no interior
    optimum. The 30 cells with a non-zero step all have interior argmins.
    This holds under three independent objectives (E_excess, mis_width,
    dmae_band). A 2-frame step is already enough. This sharpens fact 42:
    depth *structure* is insufficient; the structure must be *discontinuous*.
    [M13 §3.1]

62. **A fronto-parallel plant cannot turn over.** Exact-hit accuracy and mean
    frame error both improve monotonically from w0 to w40 (0.313 -> 0.995 and
    6.04 -> 0.064 frames) on a continuous fronto-parallel plant. A symmetric
    box mean of a constant is unbiased, so every extra tap is pure variance
    reduction. M11's A4 amendment was measured on exactly this configuration;
    its observation that both axes were "still improving at 23x23" is
    therefore not weak evidence of an optimum beyond 23x23 but *no* evidence.
    [M13 §1.2]

63. **A linear depth ramp is nearly as uninformative.** Under tilt, exact-hit
    accuracy turns over (argmax w33/w18/w11/w8 at tilt 4/8/16/32
    DN-frames/px) but mean frame error does not — its argmin is the w40
    endpoint at every tilt. A symmetric box mean of a *linear* ramp is also
    unbiased. Reporting either axis alone would give a confident wrong answer.
    [M13 §1.3]

64. **M11's per-pixel selectivity metric is structurally blind to occlusion
    halo.** In 30 of 30 depth-step cells the window chosen by per-pixel
    exact-hit accuracy is **strictly wider** than the window chosen by
    reconstruction error against the ideal; strictly narrower in 0 of 30.
    Mean penalty for following accuracy: 18.48 DN of excess error; worst
    101.35 DN. On 109MSDCF/vertical/step 32 accuracy rises monotonically to
    0.967 at w40 while E_excess is 66% worse than at its w15 optimum.
    Restricting accuracy to a band around the boundary helps but does not fix
    it. [M13 §3.5]

65. **`tenengrad-w5` (11x11) is dominated, not merely a lower bound.**
    `tenengrad-w8` (17x17) beats it in 36 of 36 edge cells with a worst-case
    single-cell loss of 0.00 DN, at lower merged noise (N 1.1019 vs 1.1324)
    and identical cost. M11's window recommendation is superseded; its
    operator recommendation stands untouched. [M13 §6.2, §7.2]

66. **Focus-operator cost is flat in the window radius.** Measured spread over
    w1-w40 is 2.53% (rule: 100*(max-min)/min over the windowed rows), with no
    trend in the radius - the extremes are at w18 and w9, not at the ends - as
    a running-sum box filter must be: O(1) per pixel
    independent of radius. A wide window is free; the w5 -> w13 widening
    costs +0.00% (3.3805 -> 3.3806 ms/frame/Mpx). Absolute ms/frame/Mpx figures
    are NOT comparable to M11's
    table — the two harnesses time different work and the scales differ by
    ~1.9x, unreconciled. [M13 §5]

67. **Spatial adaptivity has real headroom that no realisable rule reached.**
    A per-pixel oracle choosing between a narrow and a wide window gains
    5.7-46.8% of band RMS over the better fixed window across the 24
    configurations that contain a discontinuity. The realisable disagreement
    gate (use narrow where the two windows disagree by more than tau frames,
    tau in 1..8) gains at most
    +5.4% and is negative in 18 of 30 cells, down to -153.6%. Recommendation is
    a single global window; adaptivity is unrealised, not rejected. [M13 §4]

68. **CORRECTION to M11 A1: phi does not rise monotonically with window.**
    Under pointwise normalisation on real texture, phi peaks at w15-w17
    (0.1474) and declines to 0.1146 at w40 — reproducibly at probe amplitudes
    delta = 1, 8 and 32 DN. On M13's ROI it is also non-monotone at small w:
    it spikes at w1 (0.0882), dips to a local minimum at w3 (0.0631), then
    rises. A1's five values (0.0335/0.0612/0.0728/0.0872/0.1089 at
    w0/w2/w5/w8/w11) are correct and M13 reproduces them to +-5e-5; the
    monotonicity claim was extrapolation past the data in one direction and
    interpolation across an unsampled dip in the other - the same error class
    as A4.
    Under Norm::None, phi falls monotonically toward the analytic dilution law
    1/(2w+1)^2, with measured/analytic ratio rising 0.62 (w1) -> 0.978 (w40),
    and is exactly 0.000000000 at w0. The rise M11 observed is a property of
    the pointwise normaliser's own 1-px centre tap, not of windowing. [M13 §1.4]

69. `C:\dev\macro\test\119MSDCF` and `D:\personal\macro\119MSDCF` are the same
    33 frames. A full edge sweep against each produced a byte-identical CSV
    (sha256 F076E402...D11798). The D: tree is a mirror, not an independent
    sample, and must never be treated as a second stack. [M13 §0.1]
```

### §5 — new discipline items

```
21. **A plant that cannot express the failure mode is not evidence about it.**
    M11's A4 ran a window sweep on a fronto-parallel plant and reported "still
    improving at the edge of the sweep". That plant is mathematically incapable
    of producing an interior optimum for a symmetric window (fact 62), so the
    observation carried no information. Before sweeping a parameter, ask what
    the plant would have to contain for the answer to be anything other than
    the endpoint — and if the answer is "nothing it contains", fix the plant,
    not the sweep range.

22. **Report an endpoint argmin as "no turnover found within the sweep", never
    as an optimum.** Mechanical rule; M13's analysis script labels every argmin
    interior/ENDPOINT automatically so the distinction cannot be lost in prose.

23. **Where a metric has a known blind spot, control for it rather than
    disclosing it in prose.** M13's `W_bleed` cannot see a selector that elects
    a compromise frame between two layers. That is asserted as a *test* — a
    planted compromise of radius R reads bleed 0.0 and mis R-1 — not as a
    caveat. The blind spot then showed up in real data (bleed_fg collapsing
    from 18.75 px at w8 to 1.19 px at w33 while excess error rose), and it was
    recognised immediately because the control existed.

24. **When a pre-registered threshold is on the wrong quantity, say so and
    override it explicitly.** M13 registered a 5% threshold on an *oracle* gain
    it had already documented as "a strict upper bound, never a proposal". The
    threshold fired; the decision-relevant quantity was the realisable rule,
    which said the opposite. Report the registered result, state that it fires,
    and override on stated grounds. Do not quietly re-cut the threshold.

25. **Verify a corpus audit with `Get-ChildItem -Force`, never without it.**
    Without `-Force`, `Get-ChildItem -Recurse -File C:\dev\macro` reports 17449
    files / 286,581,830,721 bytes; with `-Force` it reports 18530 /
    286,893,514,060, matching the harness audit exactly. The 1081-file gap is
    hidden and system files, not deletion. An agent spot-checking a read-only
    guarantee this way will conclude it violated the guarantee when it did not.
```

### §10 — question 15

```
15. **CLOSED by M13.** The focus-measure window optimum is at radius 13 (27x27)
    for Tenengrad; it turns over sharply, and it turns over *only* because of
    depth discontinuity. M11's plants could not have located it. A single
    global window is recommended; spatial adaptivity was measured and is not
    recommended. See docs/research/M13-window-depth-measured.md.
```

### §10 — two new questions

```
NN. **Can any realisable rule reach the adaptive headroom?** A per-pixel oracle
    choosing between a narrow and a wide focus window gains 5.7-46.8% of band
    RMS at occluding edges (fact 67). Every gate M13 tried reached at most
    +5.4% and usually lost. That headroom is larger than the entire w5 -> w13
    window improvement, so it is worth more than any further window tuning.
    Untried: gating on the focus curve's peak sharpness rather than on
    inter-window disagreement; a guided-filter or cross-bilateral regulariser
    on the selection map; explicit occlusion detection.

NN. **Why does the 119MSDCF horizontal texture pair behave differently?** Its
    E_excess optimum sits at w8 at all five depth steps - the only cell with a
    constant argmin - while the other five cells scatter over w9-w33, and it is
    the source of every head-to-head loss w13
    suffers against w5. One texture pair per stack cannot distinguish an
    occlusion-geometry effect from a texture effect. [M13 §3.6, §6.2]
```

### AGENTS.md

Two additions. First, to whichever section carries the corpus rules:

```
`C:\dev\macro\test\119MSDCF` and `D:\personal\macro\119MSDCF` are the same 33
frames (verified byte-identical through a full measurement sweep, M13 fact 69).
Two stacks means two *different* stacks; use 109MSDCF and 119MSDCF, or
112MSDCF and 113MSDCF, not a directory and its mirror.

When verifying the read-only guarantee from PowerShell, **always pass `-Force`**:
`Get-ChildItem -Recurse -File -Force`. Without it, `Get-ChildItem` silently skips
hidden and system files and under-reports `C:\dev\macro` by 1081 files and
~312 MB, which looks exactly like evidence that the tree was modified.
```

Second, to the terminology section — this one has already caused confusion:

```
**"Halo" is overloaded.** In the plugin interface and SYNTHESIS fact 32 it
means the *rectangle expansion* a filter needs beyond its output tile (19.42 /
32.39 / 89.23 plane px) — an alignment and warp margin. In the focus-stacking
literature it means the *artifact* at an occluding edge where the selector
drags one surface across another. Say "plugin halo" or "occlusion halo"; never
the bare word.
```

Third, if the harness-reuse guidance is worth pinning:

```
`experiments/m11-focus-bakeoff/run-m11.ps1` does **not** list the ROIs present
in M11's committed CSVs. Reuse the ROIs from `data/noise-*.csv` and
`data/planted-*.csv`, not from the script. Quick check: a flat ROI has
single_sigma ~28-30 DN, a detail ROI ~630-700 DN.
```
