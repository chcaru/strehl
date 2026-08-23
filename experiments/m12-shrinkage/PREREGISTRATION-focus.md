# M12-F — pre-registration: is the focus stepping uniform, and do 112/113 share an interval or a step?

Written and committed **before** the measurement was run. Supplements
`PREREGISTRATION.md`; everything there still binds.

## 0. Why this exists

The orchestrator retracted the briefing's claim that the physical step differs between `112MSDCF`
and `113MSDCF` "by a factor of ~78/62 = 1.26", on the ground that it was computed as
`span/(n−1)` and is therefore an arithmetic identity, not a measurement. That retraction is
correct and I accept it.

It also lands on my own report. M12 §4.1 refuted fact 49's premise using **magnification** as the
observable, which *is* an image measurement and *is* independent of `span/(n−1)`. But
magnification is a **proxy** for focus position: equal magnification change implies equal focus
change only if the local magnification-vs-distance map is the same in both captures and locally
linear. That is an assumption, it was not stated as one, and it deserves an independent observable.

This sub-experiment supplies one: **where the in-focus band actually sits, measured per frame,
from the pixels.** It is a different physical quantity from magnification, obtained from a
different part of the image formation, and it can be compared between the two stacks without any
metadata, any `span/(n−1)`, and any assumption about the distance map.

## 1. The two hypotheses, stated so they make different predictions

Both stacks image the same static subject at the same framing. Let `p(t)` be the frame index at
which scene tile `t` is maximally in focus — the **focus index** of that tile. `p` is a monotone
function of the tile's physical depth, and the *shape* of that function is a property of the
subject and the lens, identical for both captures.

- **H-interval** (the briefing's premise, and the part the orchestrator still retains): the two
  sweeps cover the *same* focus interval at two densities. Then frame index is a linear
  reparameterisation with slope `78/62`, so regressing tile-wise
  `p_112 = α + β · p_113` must give **β = 1.2581**.
- **H-step** (M12 §4.1's magnification finding): the two sweeps share a *per-frame* step and 112
  runs 16 frames further. Then **β = 1.0000**.

These differ by 25.8%. The regression is over **tiles**, not frames, and neither side of it uses
EXIF, `span/(n−1)`, or the magnification measurement.

**A third possibility is admitted in advance**: β could land between the two, or the relation could
be non-linear. Both are reportable outcomes and neither is a failure.

## 2. What is measured, exactly

1. Decode every frame of a stack to the CFA-quad green plane (3516×2344).
2. Fit the **direct** similarity `(0, j)` for every `j`, with the same `m10` estimator M12 used.
   These are used **only to keep a tile on the same scene content** as the frame drifts; the
   maximum corner drift is ~78 plane px and the tile window is 96 px, so this is a book-keeping
   correction, not part of the statistic. A robustness arm repeats the whole measurement with the
   tile grid **frozen** (no warp) to show the statistic does not depend on it.
3. Lay a scene-anchored grid of tile centres in frame-0 coordinates, 96 px stride, 160 px margin.
4. For each frame `j` and tile `t`, map the centre through the `(0, j)` fit, take the 96×96 window
   at the nearest integer position — **no resampling** — and compute two sharpness measures:
   - **Tenengrad**, mean squared Sobel gradient magnitude, divided by the window mean squared;
   - **modified Laplacian** (Nayar), likewise mean-normalised.
   Mean normalisation is mandatory here and not cosmetic: 112 was shot at 1/60 s and 113 at 1/30 s,
   a full stop apart.
5. For each tile, take `S(t, ·)` over frames, smooth with a 3-tap [1,2,1], take the argmax, and
   refine to sub-frame precision by a parabola through the three points around it in `log S`.

**Tile acceptance, fixed now:**

- peak strictly interior — not frame `0` and not frame `n−1` (otherwise the in-focus band entered
  or left the sweep and the peak is censored);
- prominence `S_max / median_i S(t,i) ≥ 1.15`;
- no competing peak: no local maximum ≥ `0.90 · S_max` further than 6 frames from the winner;
- the parabola must be concave and its vertex must fall inside the sampled bracket.

## 3. Registered statistic and threshold

**Primary:** ordinary least squares of `p_112` on `p_113` over tiles accepted in **both** stacks,
matched by scene position after registering 113's frame 0 to 112's frame 0 with the same estimator.
Report **β**, its split-half spread, and `R²`.

**Threshold, and how it is set.** I will not pick a tolerance by taste. The uncertainty is measured
by **split-half**: partition the accepted tiles into two disjoint halves by scene position
(left/right and, separately, a checkerboard), recompute β on each half, and take
`σ_β = |β_A − β_B| / 2` as the empirical uncertainty. Then:

- **H-step** if `|β − 1.0000| ≤ max(0.05, 2 σ_β)` **and** `|β − 1.2581| > 3 σ_β`;
- **H-interval** if `|β − 1.2581| ≤ max(0.05, 2 σ_β)` **and** `|β − 1.0000| > 3 σ_β`;
- **INCONCLUSIVE** otherwise, including if `σ_β > 0.06`, in which case the measurement is too noisy
  to separate hypotheses 25.8% apart and I will say exactly that.

The floor of 0.05 exists so a spuriously tiny `σ_β` cannot manufacture a verdict; the `2 σ_β` term
exists so a noisy measurement cannot be forced into one.

**Secondary — uniformity within each stack.** Two independent tests:

- **U1, cross-stack curvature.** Fit `p_112 = α + β p_113 + γ p_113²`. Non-uniform stepping in
  either stack shows up as `γ ≠ 0`, because two uniform sweeps of the same depth→focus map must be
  related linearly *whatever* that map is — including a nonlinear motor-unit-to-distance map, which
  cancels. Registered: **uniform** if the quadratic term changes the fitted `p_112` by less than
  `2 σ_β · range/2` frames at mid-sweep, i.e. if it is inside the split-half noise;
  **non-uniform** if it exceeds twice that.
- **U2, focus index against measured magnification.** Within one stack, regress `p(t)` on the
  cumulative log-magnification `M(p(t))` already measured by M12. This is *not* independent of the
  magnification measurement and is reported as a **consistency** check only, never as evidence for
  the primary verdict.

## 4. Controls, all registered now

| id | control | what it proves | pass condition |
|---|---|---|---|
| **F1** | run the identical extraction on the C3 **synthetic** stacks — planted magnification, **no focus change** | the sharpness peak reads *focus*, not scale or drift | **≤ 10%** of tiles accepted, against ≥ 50% expected on real stacks |
| **F2** | split 112 into even-index and odd-index sub-stacks and regress their focus indices | precision of the whole pipeline at a **known** answer (β = 2.000 exactly, by relabelling) | `|β − 2.000| ≤ 0.05`. **This cannot test the hypothesis** — it is the same frames relabelled — and is reported only as a precision figure |
| **F3** | 112↔113 frame-0 registration | the two tile grids address the same scene points | fit succeeds, reported with its tile-centre displacement |
| **F4** | Tenengrad vs modified Laplacian | β does not depend on the focus measure | the two β agree within `2 σ_β` |
| **F5** | tile grid **frozen**, no `(0,j)` warp | the statistic does not inherit the similarity fits | β agrees with the warped arm within `2 σ_β` |

## 5. What would make me retract M12 §4.1

**If β = 1.2581 ± 0.05, I am wrong**, fact 49's premise is sound, the pair *does* discriminate
index-span from physical baseline, and M12's §4.1 and proposed fact 50 must be withdrawn and
rewritten. I will do that in full and say so at the top of the report, not in a footnote.

If β = 1.0000 ± 0.05, §4.1 stands and is now supported by **two independent observables** —
magnification and focus-band position — one of which carries no distance-map assumption.

If the result is inconclusive, §4.1's magnification evidence stands on its own but its
assumption gets stated explicitly and its label weakened.

**In every case, any figure computed as `span/(n−1)` is labelled DERIVED-UNDER-ASSUMPTION with the
assumption named**, per the orchestrator's instruction.

## 6. Pre-committed prediction

I expect **β ≈ 1.00**, because M12 measured `rate(112)/rate(113) = 1.0044` by magnification and a
flat per-frame rate profile in both stacks. I am recording this so that if β comes back 1.2581 it
is visible that I predicted wrongly, rather than being quietly absorbed.
