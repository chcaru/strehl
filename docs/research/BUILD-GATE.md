# BUILD-GATE — the band-noise gate is stale with respect to *warping*, not with respect to the gather flip, and the remedy runs the other way

**Facts, disciplines and open questions in this file are numbered LOCALLY as
`D1, D2, …` per rule 28.** The orchestrator allocates absolute numbers at fold.

Every claim is labelled **MEASURED**, **DERIVED** or **ARGUED**. An unlabelled
claim is unfounded and should be read as such.

**Source revision at start:** `bfd7cfbd` (`V-REVIEW aura: 28.5x confirmed in
direction, refuted as a quotable multiplier`). Working tree shared with
`BUILD-DEFECT`, which holds `crates/strehl-core/src/defect_map.rs`; this lane
touched no file it holds.

**Instrument:** `crates/strehl-cli/examples/build-gatefloor.rs`. Synthetic
probe only — no read-only stack was read, nothing was written outside the repo.

---

## 0. The commission

> **Derive the per-band noise floor from the actual warped frames rather than
> carrying a constant.** … The fix must show the `averaged` fraction and the
> removed-noise-power ratio **recovering toward the plane-arm values** on the
> same 10 subjects.

The first sentence is right and this file supplies the measurement that justifies
it. **The second sentence is wrong**, and §3 is the measurement that says so.
I stopped before building the fix, because a fix built to that acceptance test
would have been steered in the wrong direction by it.

---

## 1. The answer, up front

**The gate is stale — confirmed — but the diagnosis in the commission is
mis-scoped and the predicted remedy is inverted.**

Three findings, in order of how much they change what should be built:

**(a) The floor is not wrong *because of the flip*. It is wrong for every
warped frame, and was wrong before the flip.** **MEASURED.** At band 0 the
ratio `beta_actual / beta_white` is

| arm | span across 8 representative warps |
|---|---|
| plane (pre-flip) | **0.3432 … 0.9838** |
| fullres (shipping) | **0.6294 … 0.9981** |

Both are below 1.0 at every warp. `beta_white = 0.88980` is the constant the
shipping gate carries. The gather flip did not make the gate stale; it moved
the fullres arm **closer** to the constant than the plane arm ever was.

**(b) The shipping floor is therefore too HIGH, not too low — so the merge has
been over-averaging, and the correct fix pushes the `averaged` fraction DOWN in
both arms, not back up.** **DERIVED** from (a). The gate is
`floor = gate * beta * v` with `gate = 2.0`. Using `beta_white` where the true
value is `0.54 * beta_white` sets the bar at **3.7×** the actual noise-only band
power instead of the intended 2.0×. A floor that is too high averages *more*
pixels, not fewer.

**(c) No closed-form correction can exist, and the reason is sharper than
"phase-dependent": the two arms are different *functions of phase*, with
different periods.** **MEASURED**, §4.

---

## 2. Commissioning

Five controls, run before any result was read. Both halves of §110.6 (a planted
defect **and** a planted improvement) and §111.3's healthy control that
superficially resembles the defect.

```
BUILD-GATE -- is the pyramid band-noise floor stale after the gather flip?
  probe 512x512 quad (1024x1024 photosites), 7 bands, 8 realisations, CatmullRom, sigma_p 40 DN

== commissioning ==
  C0 green-luma level-0 variance: measured 800.74 DN^2, expected sigma_p^2/2 = 800.00   ratio 1.0009   PASS
  C1 null, no warp: beta_actual == BandGain::measure, PER BAND
     band            0         1         2         3         4         5
     white     0.88980   0.05294   0.01010   0.00236   0.00058   0.00014
     probe     0.88982   0.05280   0.01004   0.00234   0.00057   0.00013
     gap         0.00%    -0.27%    -0.61%    -0.80%    -1.23%    -6.88%
     verdict      PASS      PASS      PASS      PASS      PASS      excl
     bands trusted: [0, 1, 2, 3, 4]   (excluded bands are probe-limited, not gate findings)
  C2 amplitude x2: beta unchanged (it is a ratio)      worst gap 0.046%   PASS
     numerator DID move: E[L_0^2] 712.5 -> 2849.9 DN^2 (x4.000), so C2 is not a dead statistic
  C3 planted defect (5x5 pre-blur, a stronger low-pass than any warp):
     beta[0] 0.8898 -> 0.4872   PASS - falls
  C4 planted improvement (identity warp, full-res gather):
     beta[0] 0.8898 vs unwarped 0.8898   gap +0.000%   PASS - flat
```

- **C0** — the probe reaches the pyramid through the *real* path. It builds a
  `Frame`, runs the shipping `warp_frame_in_place*`, deinterleaves with
  `merge_cmd::load_frame`'s own offsets and forms `L = (G1+G2)/2`. Green luma
  from two independent greens has variance `sigma_p^2/2`; measured 800.74
  against 800.00 expected. The plumbing is right.
- **C1** — the **null**. With no warp the probe must reproduce
  `BandGain::measure` exactly, because that is the same computation. It does, to
  0.00% at band 0. Per band and not pooled, on purpose: band 5 is 16×16 before
  cropping, so one worst-case number would either hide a real gap at band 0 or
  condemn the probe for sampling noise at band 5. Band 5 is **excluded and
  named** rather than carried.
- **C2** — an invariance the statistic must have (`beta` is a ratio) paired with
  a quantity that must move (the numerator, ×4.000 for ×2 amplitude). §110.6's
  failure mode was a statistic that was invariant to *everything*; this is the
  check that catches it.
- **C3 — the planted DEFECT.** A 5×5 box pre-blur is a stronger low-pass than
  any warp, so `beta[0]` must fall: 0.8898 → 0.4872. *5×5 and not 3×3*: the
  merge runs on the **quad** grid where adjacent samples are two photosites
  apart, and a measured 3×3 attempt moved `beta[0]` by only −19%. A weak
  planted defect is a failed commission, not a passed one.
- **C4 — the planted IMPROVEMENT, and simultaneously the healthy control.** An
  identity warp is a warp in every mechanical respect — same gather, same
  Catmull-Rom, same buffers — and must leave the floor exactly where it was.
  Gap **+0.000%**. This is what §111.3 asks for: an arm that superficially
  resembles the defect and must be scored clean.

**Two instrument bugs were found and fixed by these controls, not by
inspection.** **MEASURED.**

1. The last pyramid level is the **base band** and carries the scene DC. The
   probe sits at 2000 DN, `BandGain::measure`'s probe is zero-mean, so the base
   band read 4996.5 against ~0. The base band is never consulted by the gate
   (`beta` is used only for Laplacian bands `k in 0..sizes.len()-1`), so it is
   excluded.
2. `warp_frame_in_place_*` leaves out-of-source samples at **black**, a ~2000 DN
   ring. At ~0.78% border pixels this raises whole-plane variance from ~800 to
   ~31000 DN² (**39×**) and swamps the coarse bands. Uncorrected it made C4 read
   `beta[0] = 0.0225` against 0.8898 and made the warp sweep return physically
   impossible ratios up to **14.19**. Fixed with an interior crop.

**D1 (discipline).** A synthetic probe pushed through a warp must be cropped
inside the black border the warp leaves, and the crop must be validated by an
identity-warp arm that returns the unwarped value **exactly**. Without the
identity control the border reads as a 39× noise increase and every downstream
ratio is fiction.

**Not certified:** C1 certifies the *pyramid* at bands 0–4 but it is an
**unwarped** control, so it cannot certify the *border crop* at those bands.
Bands 4–5 in the warped tables below return 6.1× and 458×, which are border
residue, not gate findings. They are shown struck out rather than deleted. It
does not matter for the conclusion: `beta_white` is 0.00058 and 0.00014 there,
i.e. **0.065% and 0.016% of band 0**.

---

## 3. The measurement: the floor is too high in both arms

`beta_actual / beta_white` at band 0, over eight warps chosen to span the
translation, scale and rotation range real alignment produces. **MEASURED.**

```
== beta_actual / beta_white, by arm and by warp ==
  the factor the SHIPPING floor is wrong by. 1.000 would mean the gate is fine.

    trans  scale% | b0 plane  b0 full b0 white |  r plane   r full | full/plane
     0.44    0.04 |   0.4807   0.5763   0.8898 |   0.5403   0.6477 |    1.1989
     0.06    0.00 |   0.8754   0.8600   0.8898 |   0.9838   0.9665 |    0.9824
     0.71    0.00 |   0.3054   0.8881   0.8898 |   0.3432   0.9981 |    2.9081
     1.60    0.00 |   0.5132   0.5600   0.8898 |   0.5768   0.6294 |    1.0912
     3.92    0.00 |   0.5371   0.5674   0.8898 |   0.6036   0.6377 |    1.0565
     0.44    0.50 |   0.5597   0.6281   0.8898 |   0.6290   0.7059 |    1.1223
     0.44    2.30 |   0.5590   0.6232   0.8898 |   0.6282   0.7003 |    1.1149
     3.05    1.20 |   0.5558   0.6250   0.8898 |   0.6247   0.7024 |    1.1245

  plane arm   beta_actual/beta_white spans 0.3432 .. 0.9838
  fullres arm beta_actual/beta_white spans 0.6294 .. 0.9981
  A SINGLE CONSTANT CANNOT SERVE BOTH: the two arms' spans DO overlap.
```

**Three things to read off this, in order of importance.**

**(1) Every entry is below 1.0.** **MEASURED.** The shipping constant
over-estimates the true noise-only band power at every warp in both arms. At the
typical warp (0.44 px) the true floor is `0.54 * beta_white` (plane) and
`0.65 * beta_white` (fullres). The gate is set at `2.0 * beta_white`, which is
`3.7 *` and `3.1 *` the actual noise power respectively. **DERIVED:** the merge
has been averaging pixels with up to 3.7× noise power — i.e. pixels carrying
genuine weak signal — as though they were pure noise.

**(2) `full/plane` is 1.06–1.20 at ordinary warps.** **MEASURED.** This is the
mechanism behind the commission's symptom and it is confirmed. With one fixed
floor, the fullres arm's higher band power puts more pixels above it, so
`averaged` falls — the reported 94.1% → 79.5%. The commission's *mechanism* is
right.

**(3) The two arms' spans overlap.** **MEASURED.** 0.3432–0.9838 against
0.6294–0.9981. There is no constant that is right for the plane arm and wrong
for the fullres arm, or vice versa. The staleness is not a property of the arm.

**F1 (fact).** The pyramid band-noise floor `BandGain::beta` is exact for
**unwarped** frames (C1 and C4 both return it to 0.00%) and over-estimates the
true noise-only band power for **every** warped frame measured, by 1.02× to
2.91× at band 0. It is stale with respect to *resampling*, not with respect to
the gather flip.

### 3.1 Which bands the correction reaches

```
== does the correction matter beyond band 0? ==
   band      white    plane/w     full/w full/plane       C1
      0    0.88980     0.5403     0.6477     1.1989       ok
      1    0.05294     0.9592     0.8794     0.9167       ok
      2    0.01010     0.9908     0.9637     0.9727       ok
      3    0.00236     0.9906     0.9831     0.9924       ok
      4    0.00058    17.2592     6.1139     0.3542       ok   <- border residue, see §2
      5    0.00014  1513.6195   457.9213     0.3025     excl   <- border residue, see §2
```

**MEASURED.** The correction is **a band-0 phenomenon**. Band 0 moves by
−35% to −46%; band 1 by −4% to −12%; bands 2–3 by under 2%. This is physically
what one expects — a resampling kernel attenuates near Nyquist and leaves the
low-frequency bands almost untouched — and it means a fix that corrects bands
0–1 and leaves the rest at the white value would capture essentially all of the
effect. **That is a measurement, not an assumption, and it is the justification
for any such shortcut.**

---

## 4. Why no closed-form correction can work — the phase sweep

The commission forbids a closed-form kernel ratio, on the grounds that the
transfer depends on per-frame warp phase. That is a claim about a *function*, so
I measured the function: a pure diagonal translation swept across one full plane
pixel. **MEASURED.**

```
== the phase sweep: pure diagonal translation across one plane pixel ==
  a closed-form correction would have to be ONE number for this whole column.

     dx=dy  full px |  b0 plane   b0 full |   plane/w    full/w
    0.0000   0.0000 |    0.8898    0.8898 |    1.0000    1.0000
    0.1250   0.2500 |    0.7736    0.6864 |    0.8695    0.7714
    0.2500   0.5000 |    0.5468    0.5149 |    0.6145    0.5787
    0.3750   0.7500 |    0.3682    0.6860 |    0.4138    0.7709
    0.5000   1.0000 |    0.3054    0.8881 |    0.3432    0.9981
    0.6250   1.2500 |    0.3683    0.6850 |    0.4139    0.7698
    0.7500   1.5000 |    0.5470    0.5147 |    0.6147    0.5784
    0.8750   1.7500 |    0.7739    0.6872 |    0.8697    0.7723
    1.0000   2.0000 |    0.8900    0.8900 |    1.0003    1.0003

  plane   spans 0.3432 .. 1.0003  (x2.91 across phase)
  fullres spans 0.5784 .. 1.0003  (x1.73 across phase)
```

The commission's constraint is upheld, and by a stronger argument than it used:

- **The plane arm has period 1 plane-pixel.** Minimum **0.3432** at the
  half-pixel, maximum 1.0 at both integer ends.
- **The fullres arm has period 1/2 plane-pixel** — i.e. one *full-res* pixel.
  It returns to **0.9981** at the half-plane-pixel shift, because that is an
  **integer** shift in full-res space and the gather is an exact no-op there.
  Its minima are at the quarter-pixels, **0.5784**.
- The two curves **cross**. At `d = 0.25` the plane arm is *above* the fullres
  arm (0.6145 vs 0.5787); at `d = 0.5` it is far *below* (0.3432 vs 0.9981).

**F2 (fact).** The band-0 noise transfer of the two gather arms is not two
constants but two **different periodic functions of sub-pixel warp phase**, with
different periods (1 plane-pixel vs 1/2 plane-pixel) and crossing values. Any
single scalar correction, per-arm or global, is fitted to one phase and wrong at
the others by up to **2.91×**.

**Internal control:** `d = 0` and `d = 1.0` both return 1.0000/1.0003. Integer
plane shifts are no-ops in both arms, so the sweep is measuring phase and not
accumulating drift.

**D2 (discipline).** When a correction factor is proposed for a resampled
quantity, sweep the sub-pixel phase across a full period before accepting any
scalar. A single-phase measurement cannot distinguish a constant from the
extremum of a curve, and here the two differ by 2.91×.

---

## 5. What this does to the commission's acceptance test

The commission requires:

> The fix must show the `averaged` fraction and the removed-noise-power ratio
> **recovering toward the plane-arm values** on the same 10 subjects.

**A correct fix will not do this, and I am reporting that instead of building
toward it.** **DERIVED** from §3, and the derivation is short:

- The shipping floor is `2.0 * 0.8898 * v` in both arms.
- The correct floor at a typical warp is `2.0 * 0.4807 * v` (plane) and
  `2.0 * 0.5763 * v` (fullres).
- Both corrected floors are **lower** than the shipping floor. A lower floor
  averages **fewer** pixels. So `averaged` falls further in *both* arms — and it
  falls **more** in the plane arm, which is the more mis-calibrated of the two.

So the fix moves the fullres arm's 79.5% **down**, not back up to the plane
arm's 94.1%; and it moves the plane arm's 94.1% down past it. What the fix
*does* deliver is the property that actually matters:

**The two arms converge.** Once each arm's floor tracks its own measured band
power, a noise-only pixel sits at the same multiple of its own floor in both
arms, so the arms' `averaged` fractions agree — which is the defensible reading
of "recovering toward the plane-arm values", but not the literal one.

**The null is protected by construction, not by luck.** **MEASURED (C4).** For
an align-refused subject the frames are not warped, so `beta_actual` is
`beta_white` **exactly** (+0.000%), the floor does not move, and the output is
bit-identical. The placebo stays at 0.0 Δpp because the correction is
identically 1.0 there — a structural guarantee, not an empirical hope.

**Q1 (open question).** Given F1, the pre-flip plane arm's 94.1% `averaged`
was *also* wrong — more wrong than the post-flip 79.5%. Was the merge's
noise-removal ratio of 13.06× on `foam` ever a measure of noise removal, or
partly a measure of weak signal being averaged away? This file does not answer
it, and it should be answered before the plane-arm numbers are used as a target
by any lane.

---

## 6. The parked patch

I did not land the fix. Two reasons, in order:

1. **§5.** The acceptance test in the commission is inverted with respect to
   what a correct fix does. Landing a change to the default render — which will
   move byte-freezes on every aligned subject — against an acceptance test that
   the change cannot pass is how a lane gets reverted. This needs the owner's
   decision first.
2. `merge_cmd.rs` is a live seam. `BUILD-DEFECT` holds
   `crates/strehl-core/src/defect_map.rs` in this tree; the merge itself is
   currently free, but the change below spans three files and is not a seam I
   should take without the §5 decision.

**The exact sites.** **DERIVED**, not measured — this is a design, not a result.

- `crates/strehl-core/src/pyramid.rs`, `BandMerge::add_frame` ~L1345–1365:
  `let beta = self.gain.beta(k);` becomes a per-frame value. The minimal shape
  is a `frame_beta: Option<&[f32]>` argument to `add_frame`, `None` preserving
  today's behaviour exactly, so the unwarped and align-refused paths are
  bit-identical by construction rather than by test.
- `crates/strehl-core/src/pyramid.rs` L1429: the hull margin reuses
  `self.gain.beta(k.min(self.sizes.len()-2))` with a doc comment noting that two
  noise models in one merge is two things to keep in step. **It must move with
  the gate.** Leaving it is precisely the divergence its own comment warns
  about.
- `crates/strehl-cli/src/merge_cmd.rs`, `BandWorker::fold` L4407–4437: compute
  the per-frame beta after the warp and pass it to `add_frame`.
- The probe itself: `build-gatefloor.rs`'s `probe_frame` + `green_luma` +
  `band_power`, promoted out of the example. It cannot live in `strehl-core`,
  because it must call `align_cmd::warp_frame_in_place`, which is in the CLI.
  It belongs next to the warp.

**Cost.** **DERIVED.** §3.1 shows the correction is a band-0 effect, so the
probe does not need the full pyramid or the full frame. One realisation on a
512×512 quad probe has 260k band-0 samples, which is ample for a ratio; the
per-frame cost is one 1024² warp plus one 512² pyramid, ~10–20 ms, against a
~15 s render over ~130 frames. **This estimate is not measured.**

**Env vars.** The fix introduces none if the probe is unconditional. If it is
put behind a switch, that switch must go into `RENDER_ENV` in `byte-freeze.rs`
in the same commit.

---

## 7. Two smaller items, both landed

**`crates/strehl-core/src/demosaic.rs` L385 carried a false doc.** **MEASURED.**
It called `demosaic_malvar_row` "a reference arm, not the shipping path … until
the directional green in `demosaic_row` replaced it". `use_directional()` at
L323–330 reads `STREHL_DEMOSAIC` and returns `unwrap_or(false)`, so the
directional green is **opt-in** and Malvar is what every default render uses.
Comment corrected; no behaviour changed.

**`crates/strehl-cli/src/align_cmd.rs` L1479 carried a false doc.**
`WarpScratch` claimed to exist "so a merge does not allocate four planes per
frame". `warp_frame_in_place` L1533 dispatches to
`warp_frame_in_place_fullres` by default, which allocates `mos`, `rp`, `gp`,
`bp` at L1706 and L1718–1720 — four **full-resolution** `f32` planes per call,
outside the scratch. **DERIVED:** `fw * fh == 4 * gw * gh`, so the unpriced
transient is `4 * 4 * 4 * gw * gh` = **64 bytes per quad pixel**, 16× what one
scratch plane costs. The owner's measured figure, 503.0 MiB per warp and
+2.0 GiB at four workers, is recorded in the doc with the fold peak of 1.51×
the printed 5.2 GB plan. Comment corrected; no behaviour changed.

---

## 8. Files

| file | what it is |
|---|---|
| `crates/strehl-cli/examples/build-gatefloor.rs` | the instrument: C0–C4, the warp sweep, the band table, the phase sweep |
| `crates/strehl-core/src/demosaic.rs` | doc-only fix, §7 |
| `crates/strehl-cli/src/align_cmd.rs` | doc-only fix, §7 |
| `docs/research/BUILD-GATE.md` | this file |

Reproduce with:

```
cargo run --release -q -p strehl-cli --example build-gatefloor
```

`REALS=<n>` overrides the realisation count (default 8).

---

## 9. Facts, disciplines and open questions

- **F1** — `BandGain::beta` is exact for unwarped frames and over-estimates the
  true noise-only band power for every warped frame measured, by 1.02× to 2.91×
  at band 0. Stale with respect to resampling, not to the gather flip.
- **F2** — the band-0 noise transfer of the two gather arms is two different
  periodic functions of sub-pixel phase (periods 1 and 1/2 plane-pixel, curves
  that cross), not two constants. No scalar correction can serve.
- **F3** — the correction is a band-0 phenomenon: −35% to −46% at band 0, −4% to
  −12% at band 1, under 2% at bands 2–3.
- **D1** — a synthetic probe pushed through a warp must be cropped inside the
  black border, and the crop validated by an identity-warp arm returning the
  unwarped value exactly. Uncorrected the border reads as a 39× noise increase.
- **D2** — sweep sub-pixel phase across a full period before accepting any
  scalar correction for a resampled quantity. Here single-phase and full-sweep
  differ by 2.91×.
- **Q1** — was the pre-flip plane arm's 13.06× noise-removal ratio ever a
  measure of noise removal, or partly a measure of weak signal averaged away?
  Answer before using plane-arm numbers as a target.
