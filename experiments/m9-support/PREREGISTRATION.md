# M9 pre-registration

**Written and committed before any cross-measure result was computed.** The git
history is the evidence: this file lands in its own commit, and the sweep CSVs
that decide the question land in a later one.

Question: SYNTHESIS §10 open question 9 — *is the coupling between the focus
measure and the merge regulariser severe enough that it must appear on the
public plugin interface?* Ruling wanted on §3.4.1 item **B3**, which proposes a
mandatory `support_px()` on the focus-measure trait.

---

## 0. What had already been looked at when this was written

Honesty about the order of operations, because a pre-registration written after
the fact is worthless:

- The **shipped measure only** (`ring-1-3`), on the **single flat ROI M2 used**
  (`2272,1344,256,256` of `109MSDCF`), coupled and placebo, over the 16 default
  widths. That is `data/pilot-shape.csv` and `data/pilot-placebo.csv`, both
  committed alongside this file.
- The purpose of that pilot was to fix the *form* of the statistic, and it
  changed it: the noise-ratio curve **saturates** rather than turning over, so a
  literal grid `argmin` is not identifiable (the last ten widths sit inside a
  0.005 band). A knee statistic is used instead. Recording that here rather than
  quietly switching later.
- **No measure other than `ring-1-3` has been run at this point**, on any ROI,
  in any mode. No support radius other than 3 has been observed. No comparison
  across measures, families or supports exists yet.

## 1. The metric

M2's flat-ROI noise ratio, unchanged: the **spatial** standard deviation of the
stacked green plane over a signal-free ROI, divided by the **spatial** standard
deviation of the same ROI in a single frame (the middle frame, index
`n_frames / 2`, exactly as `strehl-cli` does). Both sides are spatial sd in DN
over the same pixels, so project rule 10 — never compare a spatial sd to a
temporal sd — is satisfied by construction, and no temporal quantity appears
anywhere in this milestone.

Lower is better. M2 measured naive per-pixel argmax at **1.253x** and an
unweighted mean at **0.534x** on this ROI. This harness reproduces the argmax
figure at **1.2527x** and M2's 17x17-regularised figure at **1.0737x** against
its published **1.075x** (`data/xcheck-109MSDCF.txt`).

The regulariser is a centred box mean of width `w = 2r+1` applied to each
frame's focus field before the per-pixel argmax, using the shipped
`strehl_core::boxfilter::box_mean` so the border convention is the product's.

## 2. Pre-registered statistics

### S1 — the knee, `W90(m)`

For measure `m`, let `c_m(w)` be the coupled flat-ROI ratio at regulariser width
`w` over the swept grid `W = {1,3,5,7,9,13,17,21,25,33,41,49,65,81,97,129}`.
Let `top = c_m(1)` and `floor = min_w c_m(w)`.

> `W90(m) = min { w in W : c_m(w) <= floor + 0.10 * (top - floor) }`

the smallest swept width that realises 90% of the improvement the sweep achieves
anywhere. Well posed whether or not the curve has an interior minimum, which
matters because the pilot says it does not.

`W90` is computed per (measure, ROI) and aggregated across ROIs by the median.
The literal `argmin_w c_m(w)` is also reported, with an explicit flag for
whether it is interior to the swept grid, but it is **not** the decision
statistic and it was demoted before any treatment was run, for the reason in §0.

### S2 — does the knee track support?

Spearman rank correlation `rho(support_radius(m), W90(m))` over the **16
treatment measures** (4 families x 4 support radii). Reported two-sided:
either sign counts as coupling, because two mechanisms are live and they predict
opposite signs.

- *B3's reading*: a wider measure needs a wider regulariser. `rho > 0`.
- *Total-smoothing reading*: the regulariser only has to make up the smoothing
  the measure does not already do internally, so a measure that already averages
  heavily needs a **narrower** regulariser. `rho < 0`.

Because the design is crossed, `rho` alone is not the answer. Two-way
decomposition, both reported:

- **Within-family effect of support**: for each family, the slope of `W90` on
  `log2(support_radius)`, and the range `max W90 - min W90` across the four
  supports.
- **Between-family effect at fixed support**: at each support radius, the range
  of `W90` across the four families.

If the between-family range at fixed support is comparable to or larger than the
within-family range across support, then whatever `W90` tracks, it is not
support, and `support_px()` is the wrong number even if a coupling exists.

### S3 — the decision statistic: one-width regret

This is what actually decides B3, because a coupling that is real but cheap to
ignore does not earn a place on a public interface.

For measure `m`, `F(m) = min_w c_m(w)` is the best the sweep can do for that
measure. A framework that does **not** know a measure's support must pick one
width `w0` for everything. Its cost is

> `regret(w0) = max_m [ c_m(w0) - F(m) ]`, over the 16 treatment measures
> `R* = min_{w0 in W} regret(w0)`, and `w0* = argmin_{w0} regret(w0)`

`R*` is the worst-case noise penalty, in ratio units, of not knowing the
support. Aggregated over ROIs by taking `c_m(w)` as the mean over the flat ROIs
before the minimisation, and also reported per ROI.

### S4 — the detail-side cost

Project rule 9: a sharpness metric never travels alone, and neither does a noise
metric. `g_m(w)` is the mean central-difference gradient magnitude, in DN/px, of
the stacked plane over a **high-detail** ROI. Over-regularisation must be
allowed to show up as lost detail, otherwise "wider is always fine" is an
artefact of measuring only one side.

Per measure, the **usable band** is

> `B(m) = { w in W : c_m(w) <= floor_m + 0.10*(top_m - floor_m)  AND  g_m(w) >= 0.95 * max_w g_m(w) }`

If `intersection over m of B(m)` is non-empty, a single framework-chosen width
satisfies every measure on both sides at once and the framework does not need to
know the support.

### S5 — the harm zone

`Wharm(m) = max { w in W : c_m(w) > c_m(1) }`, or 0 if no such width — the
widest regulariser that is *worse than not regularising at all*. The pilot shows
this is not empty: `w=3` scores 1.3625x against 1.2527x at `w=1` for the shipped
measure. Reported because a framework picking a width blind must clear every
measure's harm zone, and because if `Wharm` tracks support that is a coupling
worth naming even if `R*` says it is cheap.

## 3. What confirms B3 and what kills it

Fixed now, before the treatments run.

**B3 is CONFIRMED** if all of:

1. `|rho| >= 0.6` with the within-family range of `W90` across support at least
   twice the between-family range at fixed support — i.e. `W90` tracks support
   specifically, not operator family; **and**
2. `R* > T`, the severity threshold of §4; **or** the band intersection of S4 is
   empty, meaning no single width serves every measure.

**B3 is KILLED** if:

1. `R* <= T`, **and**
2. the band intersection of S4 is non-empty.

In that case a framework can pick one width, pay at most `R*` ratio units
against a support-aware oracle, and `support_px()` buys less than the threshold.
This holds *even if* `rho` is large and significant: a real but cheap coupling is
a documentation note, not an interface obligation.

**Intermediate** — `R* > T` but `W90` tracks family as strongly as support — is
reported as "coupled, but not to support", and B3 still comes off the interface
because `support_px()` would not be the number that fixes it. What would go in
its place is then a separate design question, and this milestone says so rather
than inventing one.

## 4. The severity threshold `T`

`T = max(0.02 ratio units, 3 x s_roi)` where `s_roi` is the **measured**
between-ROI spread of the same statistic: the sd across flat ROIs of
`c(ring-1-3, 17)`, one fixed configuration measured in several places.

Justification for the 0.02 floor: M2 ran its identical configuration on two flat
ROIs and got 1.253x and 1.263x, a spread of **0.010 ratio units** for a
difference that is pure ROI choice. A coupling that moves the noise ratio by
less than twice that is inside the measurement's own reproducibility and cannot
justify a mandatory method on a public trait. `s_roi` is measured here rather
than assumed, and `T` is whichever bound is larger.

For scale: the whole defect B3 exists to manage is worth `1.253 - 1.074 =
0.179` ratio units. `T = 0.02` is 11% of it.

## 5. Controls, and what they have to show

Nothing downstream of a failed control is worth reading.

- **Null control — declared support varies, operator fixed.** `nullctl-d{1,3,6,12,24}`
  are all literally `ring(1,3)`; only the `support_px()` they declare differs.
  A framework that sized its regulariser from the declaration would use five
  different widths for one operator. `W90` **must be identical across all five**.
  If it is not, `W90` is reading something other than the operator and every
  number in this report is noise.
- **Positive control — support genuinely varies, family fixed.** `posctl-e{0,4,10,20,38}`
  are `ring(1,3)` with an extra box smooth of width `e+1` folded into the
  measure, giving real support radii 3, 7, 13, 23, 41 with the operator family
  held constant. `W90` **must move** across these. Direction is not pre-supposed:
  the total-smoothing model predicts it moves *down* as internal smoothing rises.
  If `W90` does not move here, the statistic has not been shown able to detect
  support-driven knee movement, and a null result on the treatments would be
  uninformative rather than negative — this milestone would then report an
  inconclusive result, not a ruling.
- **Placebo — selection decoupled from evaluation.** Selection reads G1,
  evaluation reads G2: two physically separate photosites, so the noise that
  drove the choice is not the noise being scored. Structure, drift, defocus and
  the frame-choice mechanism all survive; only the pixel's own noise is removed
  from the loop. If `W90` moves with support in the coupled run but not in the
  placebo, the movement is about noise election, which is what B3 is about. If
  it moves in both, it is an artefact of geometry or structure.
- **Synthetic controls on the statistic itself**, run before any data:
  `m9-support selftest`, 102 checks, including planted-knee curves whose answer
  is known by construction and a flat curve that must not produce a spurious
  knee.

## 6. The discriminator the design exists for

`dsml-s12` reads pixels 12 px away but averages **nothing** — a three-tap
stencil at stride 12. `ring-4-12` reads the same distance and averages a 25x25
box. Both would return `support_px() = 25`. If `W90` differs between them, then
`support_px()` — a read-extent number — is not the quantity the merge needs,
whatever the coupling turns out to be, and B3 is proposing the wrong field.

## 7. Deviations

Any departure from this document is to be listed explicitly in
`docs/research/M9-support-coupling-measured.md` under its own heading, with the
reason. Silent revision is the failure mode this file exists to prevent.
