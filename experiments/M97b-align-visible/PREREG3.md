# M97d pre-registration — the ruler, an external ground truth

Written before the renders finished and before any measurement. Rule 12.

## Why this target settles it

Every instrument in this milestone so far has been calibrated against either a
metric the project invented or a human looking at a crop. `highly-angled-ruler-mm-cpl`
(299 frames, `D:\personal\macro`, **read-only**) is different: the target's
geometry is known *a priori*.

- A ruler edge is **straight by construction**. Registration error cannot
  straighten it.
- A millimetre scale is a **metric ruler on the output**: tick spacing measures
  residual scale error in real units, not as a proxy.
- **Steeply angled** means the ruler spans a large depth range, so different
  segments of the edge are elected from very different frames.

## The physical prediction, stated before measuring

**A similarity maps a straight line to a straight line.** So uncorrected
breathing does *not* bend the edge by applying one wrong scale — it bends it
because the merge elects a **different frame per pixel**, each frame carrying a
different scale, so each segment of the edge is displaced radially by a
different amount.

**MEASURED-to-be: the null's straightness residual should therefore be
step-structured rather than noise-like**, with steps co-located with changes in
the elected frame, and the effect should grow with distance from the image
centre. If the null's residual is larger but *unstructured*, my mechanism is
wrong even if the bar passes, and I will say so.

## Bars, with failing values stated in advance

**S1 — straightness (primary).** Locate the ruler edge to sub-pixel precision,
fit a line robustly, report the residual **distribution** (p50/p90/p99/max and
RMS), not RMS alone.
- **PASS if the aligned arm's residual RMS is strictly lower than the `zoom`
  null's.**
- **FAIL if `rms_aligned >= rms_null`.** That is a real negative result about
  alignment and I will report it as one.

**S2 — step structure.** Mean absolute first difference of the residual along
the edge, after light smoothing.
- **PASS if the null's step statistic exceeds the aligned arm's.**
- **FAIL otherwise**, which would falsify the per-pixel-election mechanism
  above even if S1 passes.

**S3 — tick spacing, in real units.** Locate tick centres along the ruler,
compute local period, regress period against position along the edge.
- **PASS if `|slope|` is smaller for the aligned arm.**
- **FAIL if `|slope_aligned| >= |slope_null|`.**

**S4 — controls, and none of S1–S3 is admissible without them.**
- **Placebo**: an arm measured against itself must return an identical residual
  and a ratio of exactly 1.0000.
- **Bend plant**: apply a synthetic radial scale error to one arm — the same
  defect uncorrected breathing produces — and the straightness residual **must
  rise**. A metric that cannot see a planted bend cannot see a real one.
  **FAIL if a planted 0.5 px-at-the-corner radial error moves the residual by
  less than the placebo's own noise.**
- **Direction plant**: the planted-bend arm must rank **worse** than the
  untouched null.

**S5 — corpus.** The stray `warpmap.txt` count under `D:\personal\macro` is
**11** before this milestone and must be 11 after. The sidecar is solved with
`align --out` outside the corpus and consumed via `STREHL_WARPMAP`.

## Traps I am pre-committing to handle

1. **Occlusion halo runs along the edge and is present in BOTH arms** (fact
   1236: the halo survives correct alignment, so it is occlusion). A
   straightness metric disturbed by the halo measures the halo. Mitigation:
   locate the edge by a sub-pixel 50%-crossing of the intensity profile taken
   perpendicular to the edge, use a robust (median-based) line fit, and report
   the full residual distribution so a halo-driven tail is visible rather than
   averaged away.
2. **The ruler's manufacturing straightness and the lens's distortion both
   enter the absolute residual.** Neither differs between arms. **I will quote
   only the paired difference and will not present an absolute straightness
   number as registration error.**
3. **FOV.** `STREHL_ALIGN=0` renders a different field of view (discipline 606)
   and is therefore **not** compared geometrically here. The `zoom` null is the
   only honest comparator and is the only one I will measure against.
4. **Edge selection must not differ between arms.** Candidate edge points are
   chosen once, on the mean of the two arms, and both arms are then measured at
   the same points with the same interpolator.

## What would make me report a negative result

S1 failing. If the aligned render's ruler edge is not straighter than the
null's, then on this rig alignment does not improve the geometry of the output,
and that conclusion outranks both the orchestrator's visual impression and my
own §10 edge-width result — because this target's geometry is known and theirs
is not.

---

## Amendment 1 — the instrument, written after seeing ALIGNED and before ZOOMNULL

Recorded honestly: at the time of writing this amendment I have run
`angstraight.py` on the **aligned** arm only and it reports `S_rms_median_px =
1.0744`, `G_median_spacing_px = 99.9936`. **I have not run the null.** The bars
below are therefore still blind to the comparison that decides S1–S3, but they
are no longer blind to the aligned arm's scale, and that is a weaker
pre-registration than the one above. Stated so it can be discounted.

**Change of edge.** The bars above say "the ruler edge". Having opened the
render, the better straight-by-construction target is the **graduations**, not
the ruler's outer silhouette:

- there are ~14 of them inside the usable region, so S1 yields a *distribution
  over independent straight lines* rather than one number;
- they are black-on-white engravings, far higher contrast than the silhouette,
  which here abuts out-of-focus foam;
- the ruler's outer edge is the exact locus of the occlusion halo (trap 1),
  whereas the graduations sit on the flat face where no occlusion boundary
  exists;
- because the ruler is steeply tilted, one graduation spans ~1600 rows of a
  large depth range, so its own length is elected from very different frames.
  A kink *within one tick* is unambiguously registration, not target geometry.

**Deviation from trap 4.** Candidate lines are located independently in each
arm rather than once on the mean of the two, because the arms are laterally
offset by tens of pixels and a shared candidate set would be off-centre in both.
Mitigation: `n_ticks` and the per-tick x positions are reported for both arms
and must correspond one-to-one; if they do not, the comparison is void and I
will say so rather than pair them by index.

**S3 restated for this instrument.** Equal world spacing projects to an exact
3-DOF projective function of tick index, so S3 is the residual about that model
(`G_rms_frac`, dimensionless), plus the first-quartile vs last-quartile spacing
as the raw drift. **PASS if the aligned arm's `G_rms_frac` is lower.**

**S2 restated.** Largest jump between adjacent 64-row block medians of one
tick's residual, median over ticks. Chosen because a similarity cannot bend a
straight line at all, so a bend must arrive as a piecewise step from per-pixel
frame election.
