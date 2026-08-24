# M88b pre-registration — paired merge-sharpness instrument

**Status:** frozen before the treatment arm exists. The M86 alignment wiring
was not finished when this file was written, so no aligned merge had been
produced, let alone measured. Everything below is fixed in advance.

---

## 1. The question

Does M86's alignment measurably sharpen a focus merge? The comparison is
**paired**: merge the same stack twice, alignment OFF and alignment ON, with
every other input byte-identical — same frames, same gate, same demosaic, same
subject, same session.

## 2. Why this is not a fifth metric hunt (ARGUED, with one MEASURED leg)

Four sharpness metrics have died in this corpus (facts 468, 476, 612–613,
617/708, 809). All four asked the same question: **order arbitrary images by
absolute sharpness, with no ground truth, against a noise floor that swamps
the signal.** This asks a different question.

**Leg 1 — the confound cancels (ARGUED).** M88's own negative result was that
`rise² = d² + c²` is unidentifiable because the subject-intrinsic term `c`
(~30 µm) is about three times the diffraction term `d`, and no single
measurement separates them. In a paired design `c` is **held fixed by
construction**, because both arms see the same physical subject through the
same optics. It cancels in the difference:

```
rise_off² − rise_on²  =  (d² + c² + a_off²) − (d² + c² + a_on²)  =  a_off² − a_on²
```

The exact confound that made M88's absolute measurement UNIDENTIFIED is the
thing this design controls. That is the inversion, and it is why the paired
form is admissible where the absolute form was not.

**Leg 2 — the class-killing proof does not apply (MEASURED, `b02`).** Fact
617/708 is a proof, not a measurement: ring FRC is `C/(C+U)`, and a linear
post-filter scales `C` and `U` by the same `|H|²`, so the ratio cannot move.
That proof is about a **ratio of powers**. The 10–90 rise is a **distance on
the edge-spread function**, which a low-pass strictly widens. This was tested
rather than asserted, by planting a linear post-filter and reading both
statistics off the same images:

| planted σ (px) | ring FRC @0.25 | Δ FRC | rise (µm) | Δ rise (µm) |
| --- | --- | --- | --- | --- |
| 0.00 | 0.9742 | +0.0000 | 14.258 | +0.000 |
| 0.50 | 0.9745 | +0.0003 | 19.066 | +4.808 |
| 1.00 | 0.9746 | +0.0004 | 29.732 | +15.474 |
| 2.00 | 0.9756 | +0.0015 | 41.619 | +27.362 |

FRC spans **+0.0015** where the rise spans **+27.362 µm**: the rise is
**18,644× more responsive** to the same planted degradation. The dead class is
dead for a reason that does not reach this statistic. Verdict string in
`out/b02_graveyard.json`: `ESCAPES`.

**Leg 3 — the difference has zero run-to-run noise (MEASURED, `b03` N0).**
The merge is byte-deterministic: `109MSDCF` merged twice gives SHA-256
identical TIFFs, and the paired statistic reads **|Δ| = 0.000000000 µm exactly**
across all six ROIs. `dsig` never had this; it fought run-to-run variance it
could not remove.

## 3. The instrument

- **Statistic:** 10–90 edge rise in µm, from a slanted-edge ESF, reused
  **verbatim** from M88's validated core (`m88lib.py`, unmodified, imported
  read-only). M88 measured it to +1.19% ± 1.50% on planted 60–140 cy/mm and
  showed model-free reach to 114.6 cy/mm from a 48.83 cy/mm sublattice.
- **Reported quantity:** `Δ = rise_OFF − rise_ON`. **Positive means alignment
  sharpened.**
- **Frozen settings**, taken unchanged from M88's s12:
  `BIN_UM = 0.64`, `TAPER = 0.10`, `CORE_UM = 24.0`, `HALF_WIDTH_UM = 96.0`,
  `MERGE_PITCH_UM = 10.24`.
- **Edge is refit independently in each arm.** This is deliberate and it is
  the lesson of M88's own Bar 3 confound.
- **Windows are registered before measurement.** Phase correlation on a padded
  neighbourhood, **integer shift only** — a sub-pixel correction would resample
  the ON arm and inject interpolation blur into the quantity being measured.

## 4. Named ROIs — committed before any treatment result exists

Selected in `b01` on **geometry only** (edge angle, contrast, straightness,
wing flatness, non-saturation). No sharpness quantity entered the selection;
`rise` was recorded under the key `rise_um_NOT_USED_IN_SELECTION`.

Two gates were then applied, in this order:

**Gate A — null admission (`b03` N1, bar `p95|Δ| ≤ 1.0 µm`, pre-declared).**
5 of 15 geometric ROIs survived: `M94`, `M95`, `RU1`, `TW1`, `TW5`.

**Gate B — responsiveness (`b04`, bar `Δ > floor` at both 4.00 and 5.78 merge
px).** Passing a null is **necessary and not sufficient**: an ROI that is quiet
because it *cannot respond* passes Gate A and then dilutes the treatment toward
a false null. Measured:

| ROI | stack | axis | Δ @4.00 px | Δ @5.78 px | verdict |
| --- | --- | --- | --- | --- | --- |
| M94 | 109MSDCF | vertical | −0.217 | +1.010 | REJECT — non-monotone/unstable |
| M95 | 109MSDCF | horizontal | +4.013 | +5.034 | **RESPONSIVE** |
| RU1 | ruler | vertical | +6.960 | +14.402 | **RESPONSIVE** |
| TW1 | tweezers | horizontal | +0.133 | −0.222 | REJECT — blind |
| TW5 | tweezers | horizontal | +2.243 | +5.626 | **RESPONSIVE** |

**The treatment set is fixed as `M95`, `RU1`, `TW5`** (3 of 5). Exact windows
are in `out/b03_nulls.json` under `rois`. The mechanisms behind TW1's blindness
and M94's instability are **not identified**; both are excluded on the measured
rule above, not on a diagnosis.

## 5. Measured floors and declared confounds

| quantity | value | source |
| --- | --- | --- |
| run-to-run noise (N0) | **exactly 0.000000000 µm** | byte-identical re-merge |
| instrument floor (N1, worst admitted p95) | **0.6699 µm** | 32 noise realisations/ROI |
| pooled sd over admitted ROIs | 0.2497 µm | N1 |
| gain sensitivity (N2, ±8.93%/−6.84%) | **exactly 0.0000 µm** | degree 0 in gain by construction |
| pedestal +200 DN (N3) | 0.5956 µm (0.89× floor) | below floor |
| integer 3 px displacement (N4), **unregistered** | 5.7054 µm (8.52× floor) | — |
| integer 3 px displacement (N4), **registered** | **exactly 0.0000 µm** | registration fixes it |
| sub-pixel 0.37 px shift + 1 resample (N4) | 2.3987 µm (3.58× floor) | **declared confound** |
| resample round-trip, net zero displacement (N5) | up to 2.1799 µm (3.25× floor) | **declared confound** |

**The dominant confound is resampling, and its sign is known.** N5 plants a
net-zero displacement and varies only the number of interpolations; mean Δ goes
**+0.3117 → −0.2752 → −0.4052 µm** for 2 → 4 → 8 interpolations. Δ becoming
more negative means the resampled arm's edge is **wider**. In the real
comparison the ON arm gathers through warps and therefore pays one
interpolation the OFF arm does not.

**Consequence, and it is asymmetric:** resampling biases Δ **downward**, i.e.
*against* finding that alignment helps. A positive result is therefore
**conservative**; a negative result is **not**, because resampling alone could
produce it. The decision rule below encodes that asymmetry rather than
averaging over it.

## 6. Sensitivity (MEASURED, `b04`)

Planted misregistration is modelled as the mean of copies displaced along a
line — M86 measured the drift as **smooth and monotonic**, so a line is the
faithful model and isotropic jitter would not be. Direction 30°, exercising
both axes.

- **Window-validity bound, derived a priori:** `HALF_WIDTH_UM / MERGE_PITCH_UM
  = 96 / 10.24 = 9.375` merge px. The 16.00 px rung exceeds it, breaks down
  (median −2.376, one ROI fails outright) and is **excluded by geometry, not by
  its result**.
- **Monotone across every in-range rung that clears the floor**: medians
  `2.243 → 5.034 → 8.537 µm` at 4.00 / 5.78 / 8.00 px. MEASURED, `monotone_resolved = true`.
- **On the fixed treatment set (`M95`, `RU1`, `TW5`)** the median clears the
  floor at **4.00 merge px** (median 4.013 µm = 6.0× floor) and not at 2.00
  merge px (median 0.477 µm, below floor). **Minimum detectable planted spread
  is therefore between 2 and 4 merge px = 4–8 sensor px.**
- The zero rung is **degenerate and carries no information**: with zero spread
  the simulated merge is byte-identical to the input, so its exact 0.0000 is
  N0 restated. The informative nulls are N1 and N5.

## 7. Decision rule — FIXED

Let `Δ_i = rise_OFF,i − rise_ON,i` over the three fixed ROIs, each measured
with per-arm edge refit and integer registration.

Let **Θ = 2.40 µm**, the worst registered nuisance arm (N4 sub-pixel, 2.3987 µm),
which bounds resampling and residual sub-pixel displacement together and
exceeds both the 0.6699 µm noise floor and the 2.1799 µm N5 bound.

- **SHARPENS** — `median(Δ) ≥ +Θ` **and** all 3 ROIs positive. Conservative,
  since resampling pushes Δ down.
- **NULL** — `|median(Δ)| < Θ`. Report as: alignment does not sharpen the
  merge by more than 2.40 µm at these ROIs. Given base rises of 30–75 µm, that
  bounds any improvement below roughly 3–8% of edge width.
- **BLURS** — `median(Δ) ≤ −Θ`. **Must not be reported as "alignment hurts"**
  without first subtracting the resampling penalty, because N5 alone reaches
  −0.41 µm mean and 2.18 µm max in that direction.
- **INCONCLUSIVE** — signs disagree across the 3 ROIs while `|median| ≥ Θ`.

No threshold below may be adjusted after seeing a treatment number.

## 8. What a null result would mean — stated in advance

If Δ comes back inside ±2.40 µm, that is a **major finding and must not be
softened**. It would mean one of:

1. **The residual is still too large.** M86's 11.56 px held-out residual is
   5.78 merge px, and the ladder shows that a *planted* spread of that size is
   plainly visible (median 5.03 µm). If correcting from ~232.7 px of drift down
   to 11.56 px produces no measurable sharpening, the residual is doing as much
   damage as the drift did — which would be a real result about the alignment,
   not about the instrument.
2. **Something downstream dominates.** The gate, the merge rule, or the binning
   sets the edge width, and registration is not the binding constraint. Base
   rises of 30–75 µm against a diffraction scale far smaller are consistent
   with this.
3. **The stacks measured do not drift like the bees.** See §9 — this is the
   most likely benign explanation and it is a limitation of the fuel, not the
   instrument.

The instrument's own sensitivity is established, so a null cannot be dismissed
as "the metric was too weak". That is the point of doing `b04` before the
treatment.

## 9. Known limitation, stated before the result (MEASURED)

**The instrument cannot be pointed at the stacks the owner is complaining
about.** The bee stacks are edge-poor:

- `bee-2-cpl`: **0** geometrically usable ROIs.
- `bee-3-cpl`: **2** ROIs, and **both fail the null catastrophically** (p95
  |Δ| = 11.50 and 71.06 µm, versus a 1.0 µm bar).
- `wrapped-text-1`: **0** usable ROIs.

Every ROI in the fixed treatment set comes from `109MSDCF`, `ruler` or
`tweezers`. So the treatment will answer "does alignment sharpen *these*
merges", and generalising to the bees is an **extrapolation across subject**,
which this design cannot license. This is the same shape as M88's
"machine built, no fuel" (fact 1184), and it is a capture request, not a
defect in the method.

## 10. Falsifiers for the instrument itself

Any of these would invalidate the treatment result and must be checked before
it is believed:

- N0 ceases to read exactly zero on a byte-identical re-merge.
- The treatment's OFF arm rises differ from the `b04` spread-0 rises
  (`M95` 32.242, `RU1` 30.441, `TW5` 74.807 µm) by more than the floor, which
  would mean the merge inputs are not what was characterised.
- Registration reports a shift larger than the 64 px search bound, which
  silently returns (0, 0) and would reinstate the 5.7 µm displacement artifact.
- Fewer than 3 ROIs return finite values.
