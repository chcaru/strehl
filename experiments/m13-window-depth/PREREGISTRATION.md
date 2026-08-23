# M13 — pre-registration

**Registered before any M13 measurement was run.** Committed ahead of the data so
`git log` carries the ordering. SYNTHESIS §5 item 14: enumerate every cell of the
outcome space *including the ones that embarrass the hypothesis*, and say in
advance what each cell would mean.

Milestone question: SYNTHESIS §10 question 15, both halves.

---

## 0. What is already fixed and will not be re-derived

Gate 0 (`m13_reproduce_m11.py`, output in `data/gate0-reproduce-m11.txt`)
reproduces 23 of M11's published numbers from M11's committed CSVs — 10 `N`, 6
`S`, 7 `φ` — to ±5e-5, including the A4 extension row `tenengrad-w11`
(`N = 1.0908`, `S = 0.9407`, `φ = 0.1089`). It carries a built-in negative
control showing that an unstratified reader gets different answers
(`ring-1-3` → 1.1410 instead of 1.3475). **That gate passed before this file was
written.** M11's arithmetic is therefore taken as given and M13 measures only
what M11 did not.

Definitions carried over unchanged, so the columns join:

| symbol | definition | where from |
| --- | --- | --- |
| `N` | `sigma(merged) / sigma(single middle frame)`, both spatial sd over the same flat ROI; median over the 4 flat ROIs, then mean over the 2 stacks | M11 |
| `S` | fraction of ROI pixels electing exactly the planted frame; median over (ROI × `w_true`) at `roi_kind = detail`, `width = 1`, then mean over stacks | M11 |
| `φ` | `\|Δr(0)\| / Σ_d \|Δr(d)\|` under a finite-difference bump, lattice estimator, fixed accumulation reach | M9 §3.2, M11 `phi` |
| `width` | **regulariser** box width applied to the focus field before argmax | M11 |
| `w` in `tenengrad-wN` | the **operator's own** summation box *radius*; diameter `2N+1` | M11 |

`J = (1 − S/Smax) + λ·max(0, N − 1)` with `λ = 1` is M11's registered scalar.
**M13 will not use it as its sweep objective**, and the reason is registered here
rather than discovered later: `Smax` is the maximum over whichever set is being
ranked, so extending a sweep moves the yardstick. In M11's own A4 table the
extension winner has `S/Smax = 1` by construction and its `J` is therefore
numerically equal to `N − 1`. A moving normaliser cannot detect turnover. M13
registers two fixed-scale objectives instead:

- `J13 = (1 − S) + max(0, N − 1)` — same shape, `S` raw, nothing moves.
- `E = RMS(merged − ideal)` in DN over the scored region — the actual
  reconstruction error, in physical units, needing no weighting choice at all.

---

## 1. Question 15a — where the window optimum sits on continuous plants

### Sweep

`tenengrad-wN` for `N ∈ {0, 1, 2, 3, 5, 8, 11, 15, 20, 26, 33, 40}` — twelve
points, the widest being an **81×81** operator window against M11's widest of
23×23. Regulariser `width ∈ {1, 9, 17}` as in M11. Plants: fronto-parallel
(`tilt 0`) and tilted (`tilt ∈ {4, 8, 16, 32}`), on real corpus texture,
`109MSDCF` and `119MSDCF`.

Frame count is decoupled from the stack size (`--frames`), because M11's tilt
runs used 22 frames with `w_at(x) = w_true + tilt·(x − xc)/256` and at `tilt 32`
the truth clamps against the end of the ladder over much of the ROI, which
flattens the depth surface exactly where the experiment needs it steep.

### Registered hypotheses

**H1 (the load-bearing one). On a fronto-parallel plant, `S` cannot turn over in
window: it is non-decreasing across the whole sweep, up to noise.** The truth is
spatially constant, so averaging the focus field over any window mixes only
pixels whose right answer is identical. This is SYNTHESIS fact 42 — "the
objective's optimum only exists once the plant has depth structure" — applied to
the *operator* window instead of the regulariser. M11's A4 extension was measured
on `planted-*-p1`, which is fronto-parallel. **If H1 holds, M11's "still
improving at w11" is not evidence about an optimum at all**, because the
objective it was read off cannot have an interior one.

**H2. On a tilted plant, `S` does turn over, and the optimal window falls as
tilt rises.** A window spanning `2w+1` px covers a depth range proportional to
`w · tilt`; once that exceeds about one frame of the ladder the window is
averaging genuinely different answers.

**H3. `N` falls monotonically in window across the whole sweep, and degenerates.**
As the window grows the focus field becomes spatially near-constant, the argmax
collapses toward a single frame for the whole ROI, and `N` approaches M11's
`ctl-const` instrument floor (0.8377 / 0.7168) rather than approaching 1. If so,
"`N` still falling at w11" is also not evidence of an optimum — a lower `N` is
being bought with a *less selective* merge, which is the same trade M11 already
knew about, not a free lunch.

**H4. φ rises with window on real texture (M11 A1) but falls with window under
`Norm::None`.** The self-test already establishes the second half analytically
and by measurement (`data/selftest.txt`, group B). If both hold, M11's φ trend is
a property of the *pointwise normaliser*, not of windowing, and the
"windowing re-introduces a centre tap" mechanism in M11 §"Why zero-φ operators
are hard to build" needs a more careful statement.

### Outcome grid for 15a

| | H1 holds (flat plant monotone) | H1 fails (flat plant turns over) |
| --- | --- | --- |
| **H2 holds** (tilt turns over) | The optimum is a property of depth gradient, not of the operator. Report a window **conditional on scene depth structure**, and state plainly that M11's A4 could not have found an optimum. | Both plants turn over; the flat-plant optimum is the safer recommendation and H1's mechanism argument is wrong. Say so loudly. |
| **H2 fails** (tilt monotone too) | No interior optimum exists on *any* continuous plant in reach. The window must then be chosen by something else entirely — cost, or the edge behaviour of 15b. This is a legitimate outcome and would make 15b decisive rather than supporting. | Incoherent; would indicate a harness defect. Stop and debug, do not report. |

Every cell above is reportable. The one marked incoherent is a stop condition,
registered so that "it turned out weird" cannot later be resolved by choosing
whichever run looked better.

**Turnover rule, registered.** A sweep is declared to have turned over only if
the objective is worse at the two largest windows than at its argmin *and* the
gap exceeds the spread across the two stacks. An endpoint argmin is reported as
"no turnover found within the sweep", never as an optimum. This is the exact
error M11 made and M13 exists to fix, so it is registered as a rule rather than
left to judgement.

---

## 2. Question 15b — the occluding edge

### The plant

Two-layer alpha composite (Porter–Duff `over`) of **two real corpus textures**
from different ROIs of the same frame, so noise and detail statistics are honest:

```text
sigma_n(k) = sigma0 + alpha·|k − w_near|      sigma_f(k) = sigma0 + alpha·|k − w_far|
N_k = blur(T_near · M, sigma_n)   A_k = blur(M, sigma_n)   F_k = blur(T_far, sigma_f)
I_k = N_k + (1 − A_k)·F_k
ideal = composite(sigma0, sigma0)
```

Pre-multiplying the near texture by the mask and blurring the mask with the same
kernel keeps every output a convex combination of real sample values, so the
plant invents no brightness. Nothing is ever resampled or shifted (SYNTHESIS §5
item 11). Geometry: straight vertical edge, straight horizontal edge, and a thin
bar (two boundaries a known distance apart — a bar narrower than the window is
the configuration a wide window should destroy).

### The metric — two parts, because each is blind where the other sees

1. **`W_bleed`, equivalent width in plane px.**
   `W = Σ_{d=1}^{baseline_lo−1} max(0, wrong(d) − baseline)` where `wrong(d)` is
   the fraction of pixels at signed distance `d` electing a frame strictly nearer
   the *wrong* layer's depth, and `baseline` is the median of `wrong(d)` over a
   far band. No threshold and no curve fit. Ties are not counted as wrong, which
   is what makes the zero-depth-step null read exactly `0` instead of `0.5`.
2. **`H = excess edge error`,** `mean_band RMS(merged − ideal) −
   mean_band RMS(oracle − ideal)`, reported in DN and in units of the injected
   per-sample noise sigma. The oracle subtraction is load-bearing: at an
   occluding boundary **no** per-pixel frame selector can reconstruct `ideal`,
   because every frame has the near layer's blur spilling across the boundary.
   `E_oracle` is that irreducible physical floor and is built from the noise-free
   stack so it does not move with the noise realisation.

Recorded alongside: the signed `bias(d)` profile (a human sees a bright or dark
fringe; an RMS cannot show sign), `far_rms` (the smooth-surface half of the
trade, same units), `acc`, `acc_band`, `peak_bias`.

### Controls, registered in advance

| control | construction | required reading |
| --- | --- | --- |
| **Null 1** | ground-truth selection map | `W_bleed = 0` and `H = 0` **exactly** |
| **Null 2** | `w_far = w_near` — keeps the intensity edge, both textures, the compositing arithmetic and the noise, removes only the depth step; a real operator then runs on it | `W_bleed = 0` |
| **Positive** | selection map dilated across the boundary by a known `R` | `W_bleed = R − 1` exactly (the sum starts at `d = 1`; `d = 0` is the first covered pixel) |
| **Chance** | `ctl-random` operator | `W_bleed ≈ 0` **with** large `H` — the disclosed blindness of `W_bleed` to a uniformly wrong selector |

All four are asserted in `selftest`, not described in prose, and the run fails if
any misses. `data/selftest.txt` holds the readings.

### Registered hypotheses

**H5. `W_bleed` grows with window radius, with slope of order 1 px per px.**
A box window of radius `w` centred `d` px from the boundary still contains
occluder pixels for `d < w`, so mis-election should persist to roughly `d ≈ w`.

**H6. `H` grows with window** and with depth step.

**H7. The two halves of the trade are optimised at different windows**:
`argmin_w far_rms` (smooth surfaces) is strictly larger than `argmin_w` of the
band error. If H7 fails — one window minimises both — there is no spatial
trade-off to adapt to and a single global number is the answer.

**H8. A spatially adaptive rule is worth building only if the oracle says so.**
The oracle arm picks, per pixel, whichever of two windows lands closer to the
ideal. It reads the answer and is therefore a strict *upper bound*. Registered
threshold: **if the oracle beats the better fixed window by less than 5 % of that
window's `E`, M13 recommends a single global window and says the adaptive idea
was measured and rejected.** A realisable disagreement-gated rule is measured in
the same run so the gap between "possible" and "achievable" is visible.

### Outcome grid for 15b

| | edge damage grows with window | edge damage flat in window |
| --- | --- | --- |
| **smooth error falls with window** | The expected trade. Recommend by the total `E`, and check whether the oracle gap justifies adaptivity (H8). | A wide window is free even at edges; recommend the widest sensible window and say the halo fear was not reproduced. |
| **smooth error flat in window** | Wide windows are all cost and no benefit; recommend narrow. Would contradict M11's A4 and must be shown against it explicitly. | The window barely matters; recommend the cheapest and say the axis is inert. |

---

## 3. Cost

`box_mean` is a separable running sum, O(1) per output pixel independent of
radius, so **the registered prediction is that Tenengrad's cost is flat in window
size** to within measurement noise. If it is flat, a wide window is free and cost
drops out of the recommendation. If it is not flat, the recommendation has to pay
for the window and the reason for the non-flatness must be found before quoting
it.

---

## 4. Circularity guards

SYNTHESIS §5 item 20. Explicitly registered here so no agreement gets quoted by
accident:

- M13's `S` at `w5`/`w8`/`w11` comes from **M13's own planted runs**, not from
  M11's CSVs. It is *not* expected to equal M11's published `S` — different
  frame counts, different ROIs on the tilt runs, different seeds. Any agreement
  quoted must name the two disjoint measurements.
- `E_oracle` and `E_merged` share the scene but not the selection map; the
  difference is the whole point and is not circular.
- The `xcheck` mode reproduces M2's published `1.2527x` through M13's own code
  path. That is a *different code path* from `m13_reproduce_m11.py`, which reads
  M11's CSVs. The two gates are deliberately disjoint.
- `far_rms` and `band_rms` come from disjoint pixel sets of the same merge and
  may be compared; `acc` and `acc_band` are nested (`acc_band ⊂ acc`) and must
  not be quoted as agreeing.

---

## 5. What would make me report "no answer"

Registered so it stays available:

- If the window sweep shows no turnover on **any** plant and the edge experiment
  shows no window dependence, M13 reports that the window is under-determined by
  the evidence and hands the implementation a *range* with the cost argument as
  tie-break, rather than inventing a number.
- If null 2 reads non-zero, `W_bleed` is not a halo metric and the whole of 15b
  is reported as a failed instrument. No result from it would be quoted.
