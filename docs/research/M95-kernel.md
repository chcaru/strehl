# M95 arm 9 — Lanczos-3 lands switchable, the default does not move, and the ringing case is weaker than my own earlier number said

`experiments/M95-kernel/`, pre-registration and ADDENDUM 2 in that directory.
Every number below was printed this session by `crates/strehl-cli/examples/m95-kernel.rs`,
`experiments/M95-kernel/src/k1_radius.py` or `experiments/M95-kernel/src/k5_port.py`,
and is transcribed from `experiments/M95-kernel/out/k6_dump.txt`, which exists so
that no figure here comes out of my notes.

## 1. Headline

The orchestrator asked for four things: the kernels landed and switchable with
the default unchanged, a ringing measurement on a population where ringing
actually occurs, 100% crops judged by eye, and an election-neutrality result
with a separation control. All four are here. Three of them went differently
than I predicted, and the largest correction is to a number of my own.

**Landed:** Lanczos-3 is a selectable `Resampler` variant at all six
registration points. The default at `align_cmd.rs:78` is **unchanged at
`catmull-rom`**. The prefiltered cubic B-spline **does not ship**, by the
falsifier its own bar registered in advance.

**The correction.** Arm 7 (`docs/research/M95-cdiff.md` §7) reported that
Lanczos-3 rings **9.902×** more than Catmull-Rom. Measured here on a clean
1000 DN step at half-pixel phase:

| kernel | overshoot | % of step | ring reach |
| --- | --- | --- | --- |
| nearest | 0.0000 DN | 0.0000% | 0 px |
| bilinear | 0.0000 DN | 0.0000% | 0 px |
| catmull-rom | 62.5000 DN | **6.2500%** | 2 px |
| lanczos3 | 111.4132 DN | **11.1413%** | 3 px |

**1.78×, not 9.9×.** The 9.9× figure is not fabricated — it reproduces at
**9.06×** on the *ungated* population of a real frame, where 99.87% of pixels
have essentially no local contrast and the statistic is measuring noise
excursions rather than edges. It is a true number about the wrong population.
The ringing case against Lanczos-3 that I handed the orchestrator was, on the
quantity that matters, overstated by a factor of five.

**The other side of the same correction, and it cuts against Lanczos-3.** Gate
the population on real local contrast and the ratio does not shrink — it
diverges, because Catmull-Rom's overshoot goes to exactly zero while
Lanczos-3's does not.

## 2. B23 — ringing on real edges

`DSC00150.ARW`, the centre frame of `bee-3-cpl`; 1536×1536 G1 plane; half-pixel
shift; overshoot in **absolute DN** outside the 2×2 bracketing interval, which
is kernel-independent by construction. Gradient percentiles on this frame:
**p99 = 85.42 DN**, **p99.9 = 204.71 DN**.

| gate | population | pop % | nearest | bilinear | catmull-rom mean/max | lanczos3 mean/max |
| --- | --- | --- | --- | --- | --- | --- |
| 0 DN | 2 356 225 | 100.0000% | 0.0000 | 0.0000 | 0.0121 / 33.2539 | 0.1098 / 76.8477 |
| 50 DN | 92 039 | 3.9062% | 0.0000 | 0.0000 | 0.0010 / 27.3203 | 0.0177 / 76.8477 |
| 100 DN | 7 455 | 0.3164% | 0.0000 | 0.0000 | 0.0002 / 1.6992 | 0.0567 / 34.1569 |
| 200 DN | 813 | 0.0345% | 0.0000 | 0.0000 | **0.0000 / 0.0000** | 0.0570 / 25.0261 |
| 400 DN | 42 | 0.0018% | 0.0000 | 0.0000 | 0.0000 / 0.0000 | **0.0000 / 0.0000** |

Mean-overshoot ratio, lanczos3 / catmull-rom: **9.06× / 18.57× / 244.54× / ∞ /
0-over-0**.

Three things are in that table.

**Catmull-Rom does not ring at all on this frame's real hard edges.** At the
200 DN gate it reads exactly 0.0000, mean and max. The reason is structural,
not lucky: Catmull-Rom reproduces linear ramps exactly, and a high-gradient
pixel on a lens-blurred macro frame is almost always mid-ramp rather than at a
true discontinuity. Lanczos-3's negative lobes sit at ±2 and ±3 px and reach
past the local ramp into curvature, so it overshoots even where the local
neighbourhood is linear.

**The absolute magnitudes are small.** At the 200 DN gate Lanczos-3's mean
overshoot is **0.0570 DN** against edges of ≥ 200 DN — 0.03%. Its worst is
25.03 DN, 12.5% of the gate, consistent with the 11.14% clean-step figure.

**Only 0.0345% of the plane carries ≥ 200 DN of local bracket contrast.** That
is a finding about the owner's data rather than about kernels: on `bee-3-cpl`
hard edges barely exist. It is also the reason the ungated statistic is
dominated by noise.

### Spatial extent

Mean overshoot in DN against Chebyshev distance from a gated (≥ 100 DN) edge
pixel:

| kernel | d=0 | d=1 | d=2 | d=3 | d=4 | d=5 | d=6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nearest | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| bilinear | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| catmull-rom | 0.0000 | 0.1447 | 0.0671 | 0.0309 | 0.0265 | 0.0326 | 0.0229 |
| lanczos3 | 0.1572 | 0.6154 | 0.2389 | 0.1841 | 0.1613 | 0.1664 | 0.1382 |

Lanczos-3 is elevated **2.5–4.2×** at every distance and **neither kernel
decays to zero by d=6**. I do not read that as a 6-px ring: top-0.1% gradient
pixels on a macro bee frame are dense enough that one edge's neighbourhood
contains the next edge. The honest statement is that this population cannot
separate ring decay from edge density, and a clean step can — which is what
K22's reach column measures, at exactly each kernel's support radius.

### Controls

- **K20 — nearest reads exactly 0.0000 at every gate.** PASS. It copies a
  bracketing sample and structurally cannot leave the interval.
- **K21 — bilinear reads exactly 0.0000 at every gate.** PASS. Second
  independent structural zero.
- **K22 — power.** PASS, and stronger than registered. Catmull-Rom's clean-step
  overshoot is **6.2500%**, which is **exactly 1/16**: the half-pixel weights
  `[−1/16, 9/16, 9/16, −1/16]` applied to `[lo, lo, lo, hi]` give
  `lo − (hi − lo)/16`. `k5_port.py` re-derives 6.2500% and 11.1413% in Python
  from the weight definitions, independently of the Rust, and agrees to
  **0.000e+00** and **1.645e-07**. The reach column returns 2 px and 3 px —
  each kernel's support radius. The instrument agrees with algebra, not merely
  with itself.

Two structural zeros and one positive is the discipline-594 shape: the
instrument demonstrably can say otherwise, and the values it returns when it
does are the ones closed-form analysis predicts.

### Deviation from pre-registration, disclosed

ADDENDUM 2 registered the statistic as overshoot **normalised** by
`max(hi − lo, eps)`, over populations `ALL` / `EDGE` (top 1% gradient) / `TOP`
(top 0.1%). I changed it, and the reason is a falsifier the pre-registration
also named.

**The eye refuted my own metric.** Rendering the 100% crops, the normalised
statistic's argmax landed on a **featureless white patch with no edge in it**.
Dividing a ~1 DN noise excursion by a ~1 DN bracket manufactures a large
"overshoot". The pre-registration says: *if the eye disagrees with the metric,
the eye wins and the report says the metric was wrong.* It was wrong. The
statistic is now **absolute DN**, gated on local contrast.

Two consequences, stated so the change cannot be read as convenient:

- The **ratios between kernels were never affected** — the denominator is
  kernel-independent at each pixel, so it cancels. Only the tail values were
  uninterpretable. The change does not move the comparison the arm exists to
  make.
- A **ladder** replaced the two registered percentile cuts because a single
  gate is a number I would have chosen after seeing data. The registered
  populations are inside the ladder: p99 = 85.42 DN sits between the 50 and 100
  DN rungs, p99.9 = 204.71 DN sits at the 200 DN rung.

Spatial extent was registered as "count of pixels per edge whose overshoot
exceeds 1% of local contrast" and is reported instead as mean DN against
distance, for the same reason: the 1% threshold is a normalised quantity.

### Prediction, registered, confirmed

`lanczos3 > catmull-rom` on every population and `nearest = bilinear = 0`.
Confirmed at every gate. This is the one prediction of mine that survived.

## 3. B24 — the kernel *does* move the election

16 frames at stride 18, 1024×1024 quad crop, **921 600 px** compared,
`ILCE-7CM2` ISO 100. The real `gather_checked`, the real
`green_luma_with_clip`, the real `FocusField::compute` at the real
`WINDOW_RADIUS`, the real `profile::noise_model_for`. Sub-pixel warp phases are
**per-frame**, `ax = frac(0.37 i)`, `ay = frac(0.61 i)` — a common phase would
make the kernel effect common-mode and bias the answer toward neutrality by
construction.

| comparison | winners moved |
| --- | --- |
| **K23 null** — catmull-rom vs itself | **0.000000%** |
| **K24 power** — vs σ = 1.0 px planted on frame 8 | 1.532444% |
| **B24** — catmull-rom vs lanczos3 | **0.673720%** |
| reference — catmull-rom vs bilinear | 1.132487% |

**B24 is not neutral, and I predicted that it would not be.** ADDENDUM 2
registered "non-zero, between 0.1% and 10%", on the structural ground that
`merge_cmd.rs:919-960` warps the frame *before* the focus statistic is
computed, so the election consumes resampled pixels. 0.673720% is inside the
registered interval. This is the finding the orchestrator asked to have stated
rather than absorbed: **selecting Lanczos-3 would change which frame wins about
1 pixel in 150.**

**But the flips are ties, not disagreements.** Median relative margin at the
pixels where Lanczos-3 disagreed: **0.007684**. Median over all live pixels:
**0.427391**. **Ratio 55.6×.** The election changes hands almost exclusively
where the top two frames were within sub-percent of each other on the focus
statistic — the pixels where "which frame is sharper" is close to undefined.

### K24 FAILED its registered bar, and the bar was mine

K24 registered **≥ 5%** of winners moved. It read **1.532444%**. That is a
**FAIL** and I am reporting it as one.

The diagnosis is that I mis-specified the bar rather than that the instrument
is dead. The planted frame's own win share is **5.4532%** of the crop, so
planting a blur on it can only ever change winners on pixels it was winning
or could plausibly win. K24 moved **28.1016% of what was reachable**, and the
separation over the null is **infinite** — the null is exactly 0.000000, which
clears the registered ≥ 10× requirement by construction rather than by
measurement.

Win share by frame: `0.003 0.000 0.000 0.000 0.003 0.171 0.384 0.166 0.055
0.055 0.107 0.021 0.021 0.008 0.003 0.005`. I registered "≥ 5% of all pixels"
without first checking that any single frame in a 16-frame focus sweep wins
anything like 5% of the plane. The correct bar was a share of the planted
frame's own territory. **I am not restating the bar to make it pass** — it is
recorded as failed, and the reachability figure is offered as the reason,
for the orchestrator's verifier to accept or reject.

What the control does establish: the harness is exactly deterministic
(K23 = 0.000000%), it responds to a real optical change with a real signal, and
the reference comparison against bilinear (1.132487%) shows a coarser kernel
change moving 1.7× more winners than Lanczos-3 does. The instrument is not
silent.

## 4. B22 — the port is exact, and the gain survives it

Tap weights were read back out of the **shipped binary** by delta probe: a
single-valued source pixel at `i0 + off`, sampled at `x = i0 + f`, returns
exactly that tap's weight including normalisation. Probed at **64 phases**
across the unit interval and compared to textbook weights recomputed
independently in Python:

| kernel | support | taps | offsets | max abs weight difference |
| --- | --- | --- | --- | --- |
| nearest | 0.5 | 2 | 0..1 | 0.000e+00 |
| bilinear | 1.0 | 2 | 0..1 | 0.000e+00 |
| catmull-rom | 2.0 | 4 | −1..2 | 4.841e-14 |
| lanczos3 | 3.0 | 6 | −2..3 | **2.969e-08** |

The Lanczos-3 residual is the f32 storage of f64-computed normalised weights.
**B21 PASS** at 2.969e-08 against a 1e-5 bar.

Because the shipped weights and the measurement library's weights are the same
function to 3e-8, arm 8's kernel figure can be re-derived independently. Same
40 tiles, same 8 real warps from the `bee-3-cpl` warp map, same paired
band-ratio cost, re-implemented in this session:

| arm | gather cost | n |
| --- | --- | --- |
| catmull-rom | **+0.1845 ± 0.0049 dex** | 320 |
| lanczos3 | **+0.0685 ± 0.0049 dex** | 320 |
| **kernel gain** | **+0.1160 dex** | |

Arm 8 measured **+0.1160 dex**. **|difference| = 0.0000.** **B22 PASS**
against a 0.01 dex bar.

That is the number the default decision turns on: switching the kernel recovers
**+0.1160 dex** of the gather's cost, against **+0.0179 dex (9.7%)** recoverable
from removing the coverage scale, which arm 8 measured. The kernel lever is
**6.5×** the coverage lever.

### A defect this arm caught in its own harness

The first version of `k5_port.py` computed `np.log10(M.band_ratio(t, step))`.
`band_ratio` already returns log10, and the level is negative, so every value
came back NaN and B22 read `FAIL` on a NaN. I had written that line from my
recollection of arm 8's shape rather than from arm 8's file; the actual line is
a **paired** difference, `band_ratio(base, 1.0) − band_ratio(out, step)`. Two
notes: the NaN made the defect loud rather than silent, and it is the same
failure mode rule 21 exists for — I reconstructed a formula from memory instead
of reading it.

A second version drove the gather from the probed tap table by snapping each
sample's phase to the nearest probed row. That is also reported as discarded:
at 8 probed phases the snap error is 0.125 px, far larger than the effect being
measured. Raising the probe to 64 phases and showing functional identity to
3e-8 is the sound version of the same claim.

## 5. The B-spline does not ship

B20 registered: the truncated FIR must match the exact IIR-prefiltered B-spline
to **max abs < 1e-4**, `R` chosen as the smallest radius clearing it, and **if
no R ≤ 12 clears it, the B-spline does not ship and I say so.**

Prefilter impulse response `h[k] = √3 · z^|k|`, `z = √3 − 2 = −0.2679491924`;
effective kernel `w(u) = √3 Σ_k z^|k| β³(u − k)`. Truncation error decays by
`1/|z| = 3.7321` per unit `R`:

| R | taps | max abs error vs exact IIR |
| --- | --- | --- |
| 8 | 16 | 5.058880e-01 |
| 9 | 18 | 1.365147e-01 |
| 10 | 20 | 3.710337e-02 |
| 11 | 22 | 9.979257e-03 |
| 12 | 24 | 2.675412e-03 |

**NOT MET at any R ≤ 12.** B21 interpolation error at integer taps is
2.220e-16 — the kernel itself is correct; the truncation is what fails.

One caveat, stated because it cuts against my own falsifier: the bar was
**dimensionally strict**. It is an absolute error on data spanning ~10⁴ DN, so
R=8's 0.5 is ~5e-5 relative — below the quantisation step. A relative bar would
have passed at R=8. But B20 registered the consequence in advance and the
consequence is what binds; I am not rewriting a bar after seeing its result.

Independently of the bar, a *correct* prefiltered B-spline needs a whole-plane
IIR prefilter pass before the gather, not a wider FIR. That is a change to the
merge path. `merge_cmd.rs` is contended and not mine: **reported, and stopped.**

## 6. Deliverable 2 — the crops, judged by eye

Written to `C:\dev\strehl-out\M95-kernel\`: five-panel 100% strips (original,
nearest, bilinear, catmull-rom, lanczos3) at 192×192, 6× nearest-neighbour
zooms, and signed `lanczos3 − catmull-rom` difference maps.

| window | subject | p99.9 abs diff | RMS edge | RMS flat | edge/flat |
| --- | --- | --- | --- | --- | --- |
| x640 y1120 | defocused silhouette | 12.50 DN | 4.242 | 3.040 | **1.40×** |
| x64 y64 | sharp detail | 20.50 DN | 6.775 | 1.757 | **3.86×** |
| x352 y928 | textured edge | 21.50 DN | 7.445 | 2.319 | **3.21×** |

Worst gated overshoot in the crops: **18.38 DN at x214 y231**, against a local
contrast of **123.0 DN**.

What the eye sees, stated plainly. On the difference maps, bipolar light/dark
fringes hug hairs and specular points — that is genuine ringing and it is
visible. Alongside it there is recovered detail on textured edges that
Catmull-Rom does not carry. In **defocused** regions the difference is almost
entirely amplified noise: edge/flat 1.40×, barely above unity, meaning
Lanczos-3 is mostly re-rendering grain there.

**Where the eye and the metric disagree, and it is not where I expected.** The
metric prefers Lanczos-3 by +0.1160 dex; the eye finds real fringes at hairs.
Neither is wrong. They are measuring different things at the same frequency,
which is precisely the orchestrator's objection. On these three windows I do
not think the fringes make the image worse — but I did not test that on a
population where they would be worst, and §7 says so.

## 7. Deliverable 3 — which kernel I would default, and what it costs

**In this commit: Catmull-Rom, unchanged, unconditionally.** That was fixed
before any measurement.

**For the later decision I would default Lanczos-3**, and the case is stronger
than my own arm-7 report implied:

- **+0.1160 dex** recovered — 6.5× the coverage lever. ~~on the exact deficit
  the owner is complaining about~~ **— RETRACTED, see §23.** That clause is
  wrong. §23 measured the fraction of the 0.30–0.48 cyc/px scoring band that is
  real captured subject detail, on the same 40 tiles this gain was scored on,
  and it is **12.8%** (95% CI 12.2–13.4%). The band is **87% sensor noise and
  the demosaic's response to it**, so recovering energy in it is mostly
  recovering noise, and it is *not* the owner's deficit. The **+0.1160 dex** is
  a correct measurement of the kernel's transfer function and is retained as
  such; the sharpness framing around it is withdrawn.
- On real gated edges its mean overshoot is **0.0570 DN** against ≥ 200 DN
  edges.
- Election flips sit **55.6×** below the typical decision margin, and are
  confined to near-ties.
- Its clean-step behaviour is textbook and verified against algebra.

**What would be given up, itemised so the decision is not made on the upside
alone:**

1. **11.1413% step overshoot vs 6.2500%** — 1.78× on a true discontinuity.
2. **3 px ring reach vs 2 px**, measured as support radius on a clean step.
3. **Catmull-Rom currently rings exactly zero on this frame's hard edges;
   Lanczos-3 does not.** On the gated population the ratio is ∞, not 1.78×.
   This is the strongest argument against the change and I am not going to
   soften it.
4. **Noise amplification on flat ground**: 1.76–3.04 DN RMS in the difference
   maps, in regions with no detail to recover.
5. **12 `sin()` calls per sample** vs Catmull-Rom's ~10 flops. Unmeasured in
   wall-clock; this is a performance regression of unknown size on a project
   whose name is about speed.
6. **`support() = 3.0` rejects a 3 px border** where Catmull-Rom rejects 2 —
   in exactly the region the coverage crop already makes fragile.

**What would change my recommendation.** A ringing measurement on the
occluding-edge cells M87 is working, which is the population where the artifact
should be worst and which I did not have access to. On `bee-3-cpl` alone,
hard edges are 0.03% of the plane — this stack cannot settle the question, and
I would not want the default changed on this evidence alone.

## 8. Deliverable 4 — election path untouched

The byte-frozen election path is untouched. The change is additive: a new
`Resampler` variant plus three match arms. `align_cmd.rs:78` still parses
`catmull-rom` as the default, so every existing invocation resolves to the
identical kernel and the shipped election is byte-unchanged.

Sidecar serialisation is by **name**, not discriminant (`warpmap.rs:534-551`),
so adding a variant cannot invalidate an existing warp map. There are exactly
**three** exhaustive matches on `Resampler` in the tree —
`align.rs::sample`, `align.rs::support`, `warpmap.rs::resampler_name` — all
three updated, and the compiler enforces that the set is complete.

And, per §3: **yes, the kernel does move the election** — 0.673720% of pixels,
at margins 55.6× below typical. Stated, not absorbed.

## 9. Implementation notes worth keeping

**Normalisation is load-bearing.** Unnormalised Lanczos-3 weights sum to
**0.9942985** at half-pixel phase — a **−0.5701%** gain error, and half-pixel
is the worst phase of the 63 tested. A separable 2-D gather squares it, giving
**0.9886296**, or **−1.1370%**. That is a phase-dependent *gain*, which would
appear as a modulation pattern rather than as blur and would be easy to misread
as something else entirely. Weights are computed in f64, normalised, then
stored f32.

*Provenance note against rule 21:* an earlier note of mine recorded this as
0.9939802. That number is not reproduced by any code run in this session; the
measured value is 0.9942985. The recalled figure was wrong in the fourth
decimal, which is the second time this session a number from my own notes has
failed to survive being re-measured. The first was arm 7's 9.902×.

**At integer phase Lanczos-3 is exactly interpolating**: every tap's `t` lands
on a zero of `sinc` except the centre. Measured 2.220e-16 for the B-spline path
and confirmed by the f=0 tap row `[−1.6e-17, 3.2e-17, 1.0, 3.2e-17, −1.6e-17,
1.5e-33]`.

**`sample_checked` widens with the kernel.** `support()` returns 3.0, so
`Lanczos3.sample_checked(p, 2.0, 2.0)` is `None` where `CatmullRom`'s is
`Some`. That is asserted in a unit test, because getting it wrong reads
out-of-bounds at exactly the frame edges the coverage crop already stresses.
Below `width < 6` the implementation falls back to Catmull-Rom.

## 10. Candidate facts

**P95.** Lanczos-3 overshoots a clean 1000 DN step at half-pixel phase by
**11.1413%** against Catmull-Rom's **6.2500%** — a ratio of **1.78×**, not the
9.902× M95 arm 7 reported. The 9.9× figure reproduces at **9.06×** only on an
ungated population that is 99.87% noise.

**P96.** Catmull-Rom's half-pixel step overshoot is **exactly 1/16**
(6.2500%), because weights `[−1/16, 9/16, 9/16, −1/16]` on `[lo,lo,lo,hi]`
give `lo − (hi−lo)/16`. Independently re-derived in Python, agreeing with the
Rust to 0.000e+00.

**P97.** On `bee-3-cpl` frame `DSC00150.ARW`, **Catmull-Rom's overshoot is
exactly 0.0000 DN** on pixels with ≥ 200 DN local bracket contrast, while
Lanczos-3 reads 0.0570 DN mean / 25.03 DN max. Catmull-Rom reproduces linear
ramps exactly and lens-blurred macro edges are mid-ramp.

**P98.** Only **0.0345%** of `bee-3-cpl`'s plane carries ≥ 200 DN of local
bracket contrast (p99 gradient 85.42 DN, p99.9 204.71 DN). Hard edges barely
exist in this data, which is why ungated ringing statistics measure noise.

**P99.** Changing the resampling kernel **does** move the focus election —
**0.673720%** of pixels change winning frame between Catmull-Rom and Lanczos-3
— because `merge_cmd.rs:919-960` warps before `FocusField::compute`. The flips
are near-ties: median relative margin **0.007684** at a flip against
**0.427391** overall, **55.6×**.

**P100.** Lanczos-3's shipped weights match textbook Lanczos-3 to
**2.969e-08** across 64 probed phases, and re-measuring arm 8's kernel gain
independently through that agreement reproduces **+0.1160 dex** to four
decimal places.

**P101.** The prefiltered cubic B-spline's truncated-FIR error is
**2.675e-03** at R=12 against a registered 1e-4 bar, decaying 3.7321× per unit
R, so it would need R ≈ 15 (30 taps, a 15 px rejected border). A correct
implementation needs a whole-plane IIR prefilter, which is a merge change.

**P102 (negative, about my own instrument).** A ringing statistic normalised by
local bracket contrast puts its argmax on a **featureless flat patch**, because
a ~1 DN noise excursion over a ~1 DN bracket manufactures a large ratio. Found
by looking at the image, not by any bar.

**P103.** Unnormalised Lanczos-3 weights sum to **0.9942985** at half-pixel
phase (the worst of 63 phases tested), a −0.5701% gain error that a separable
2-D gather squares to −1.1370%. Normalisation is a correctness requirement, not
a refinement; without it a constant plane comes back darkened by a
phase-dependent factor.

## 11. Scope and falsifiers

- Ringing is measured on **one** frame of **one** stack. `bee-3-cpl` has almost
  no hard edges; the population where Lanczos-3 would look worst — M87's
  occluding-edge cells — was not available to me. **A ringing measurement there
  could reverse §7's recommendation** and I would accept that.
- B24 is measured on a 1024×1024 quad crop with synthetic per-frame phases, not
  on the real warp map. The real aligner's phases are not uniformly
  distributed, so the true flip rate could differ.
- **K24 failed its registered bar.** The reachability diagnosis is offered as
  an explanation, not as a pass. A verifier is entitled to treat B24 as
  under-powered and I would not argue.
- The +0.1160 dex gain is measured through the band-ratio metric on 40 tiles ×
  8 warps. It is the same instrument arm 8 used and inherits arm 8's scope.
  **§23 has since measured that band to be 87% sensor noise on those same 40
  tiles, and the sharpness reading of this number is retracted there.**
- **Lanczos-3's runtime cost is unmeasured.** 12 `sin()` per sample is a real
  cost on a performance-oriented stacker and nobody has put a number on it.

## 12. Verification of this report

`experiments/M95-kernel/src/verify_report.py` re-reads
`out/k1_radius.json`, `out/k3_kernel.json`, `out/k3_port64.json` and
`out/k5_port.json`, and checks every numeric claim in this file against them in
two passes: PRESENT (each expected value appears) and DISCRIMINATE (a mutated
value is rejected).

`experiments/M95-kernel/src/verify_negative_control.py` plants three defects —
a wrong number in the report, a wrong number in a source JSON, and a stripped
fact label — and requires the verifier to go **green → red** on each and back
to green on restore. **3/3 detected, byte-identical restore verified for both
files.**

The verifier caught two real defects in its own first run, both worth
recording because they are the failure modes this project keeps hitting:

- A structural check searched the **raw** report for "unchanged at
  `catmull-rom`" and reported NO, because the phrase spans a line break. Prose
  wraps; substring checks must run on whitespace-collapsed text.
- Five DISCRIMINATE checks failed on short tokens — `0.5`, `1.0`, `64`, `320`,
  `1.40` — whose last-digit decoys occur elsewhere in a 400-line report by
  coincidence. Fixed by anchoring each on a neighbouring literal from the same
  table row, which restores the check rather than relaxing it.

### The test suite, and why it had to be run in a copy

`cargo test -p strehl-core` **does not compile in the shared tree right now**.
Six errors, all in `crates/strehl-core/src/color.rs`, which is dirty and is
**M100's file** (last commit `fb2f4ef`, "M100: exposure control for the viewing
path"). It is in-flight work, it is not mine, and the orchestrator's standing
instruction is to coordinate on `color.rs` through it rather than touch it.

So `experiments/M95-kernel/src/k7_isolated_test.py` copies the workspace
sources to a scratch directory, restores **only** `color.rs` there from its
committed HEAD blob — read as **bytes** via subprocess, never `git show >
file`, which re-encodes the stream on Windows — and runs the suite in the copy.
The live tree is never written to, and the script asserts and prints that.

| | result |
| --- | --- |
| `cargo test --release -p strehl-core` | **265 passed, 0 failed** |
| `align::tests::lanczos3_is_interpolating_and_preserves_dc` | ok |
| `align::tests::lanczos3_support_matches_its_reach` | ok |
| `align::tests::every_resampler_survives_a_name_round_trip` | ok |

`rustfmt --edition 2024 --check` is clean on `align.rs`, `warpmap.rs` and
`m95-kernel.rs` (the workspace is edition **2024**, not 2021). `cargo clippy
--release -p strehl-core --lib -- -D warnings` and `cargo clippy --release -p
strehl-cli --example m95-kernel -- -D warnings` both return 0.

Two pre-existing `rustfmt` diffs in `align_cmd.rs` are **not mine**:
`experiments/M95-kernel/src/k2_fmt_baseline.py` reads the HEAD blobs as bytes
and shows the same two diffs at HEAD, before my two added lines.

### End-to-end acceptance, from the command line

Every measurement above runs through library calls. This is the check that the
shipped binary actually exposes the kernel, with its own negative control:

| invocation | result |
| --- | --- |
| `strehl align --help` | `--resampler <RESAMPLER>` … `[default: catmull-rom]` |
| `strehl align --resampler lanczos3 <missing dir>` | fails on the **directory**, so the kernel parsed |
| `strehl align --resampler bogus-kernel <missing dir>` | `Error: unknown resampler "bogus-kernel"` |

The pair matters more than either half. The first alone would also pass if the
parser silently accepted anything; the second shows it does not. And the
`--help` line confirms the default is still `catmull-rom` in the shipped
binary, not merely in the source.

## 13. For the orchestrator

- **Landed and switchable, default unchanged.** `--resampler lanczos3` on
  `align`; the `--resampler-cost` table gained a row.
- **`merge_cmd.rs` untouched.** The B-spline needs a merge-side prefilter pass;
  reported and stopped, as instructed.
- **I request an independent verifier**, per the standing arrangement. In
  particular I want K24's failure adjudicated by someone other than me, since
  the reachability argument is one I constructed after seeing the failure.
- **`python scripts\corpus_lint.py` is red on 7 S1/S6 violations in
  `docs/research/M107-chroma.md`**, which is M107's file and not mine. Not
  fixed, disclosed.
- **`crates/strehl-core/src/color.rs` does not currently compile** — six
  errors, dirty in the tree, M100's file. It blocks `cargo test -p strehl-core`
  for every agent in this tree, not just me. I did not touch it and I ran my
  tests in a scratch copy instead (§12). **You may want to know that this is
  blocking the shared suite.**
- **Capture request** (I cannot file it — `docs/captures-needed.md` is yours):
  a stack containing genuine hard occluding edges. Every ringing conclusion
  here is limited by `bee-3-cpl` having 0.0345% of its plane above 200 DN local
  contrast, and the default decision needs a population where the artifact can
  actually appear.

---

## 14. The shared-sidecar hazard — measured, and the premise has moved

The orchestrator broadcast that `strehl align` writes its sidecar to
`<stackdir>/warpmap.txt` inside the read-only capture library, and that seven
live agents have been silently redefining each other's renders through it. I
tested the claim rather than adopting it. Instruments:
`experiments/M95-kernel/src/k9_sidecar.py` and `k10_resampler_field.py`; raw
output in `out/k9_sidecar.{json,txt}` and `out/k10_resampler_field.{json,txt}`.
Every bar below was written into the script docstring before the run.

### 14.1 The corpus write is already fixed (H0)

**The premise is out of date.** `sidecar_path()` no longer returns
`<stackdir>/warpmap.txt`. `align_cmd.rs:805-817` returns
`cache_root()/<leaf>-<key:016x>.warpmap.txt`, and `cache_root()`
(`align_cmd.rs:820-831`) resolves `$STREHL_CACHE_DIR`, else
`%LOCALAPPDATA%\strehl\warpmaps`. This landed at **`8118dd7`**, *"M97f: fix the
read-only corpus write, and measure that torn sidecars are rejected"*.

Measured now: `D:\personal\macro\bee-3-cpl\warpmap.txt` **does not exist**, and
a glob for `*/warpmap.txt` across the whole library returns **0 files**. The
capture library is clean.

### 14.2 The hazard did not go away — it relocated (H1)

The three live cache entries at the time of the run:

| entry | bytes | frames | reference | resampler |
| --- | --- | --- | --- | --- |
| `bee-3-cpl-ea1d38ea5c9523c5` | 1 292 | **6** | 3 | catmull-rom |
| `dry-erase-marker-head-cpl-57fff568a7ede183` | 41 027 | 299 | 149 | catmull-rom |
| `lavendar-cpl-47e596c1cc69bdfc` | 40 812 | 299 | 149 | catmull-rom |

`bee-3-cpl` is at **6 frames** — the same oscillation the orchestrator
described (299 -> 60 -> 2), now happening in `%LOCALAPPDATA%` instead of the
capture directory. Seven agents still share one file per stack.

**`--out` protects the shared cache (H1 = PASS):** an `align --limit 6 --out
<my scratch>` left all three entries byte-identical by SHA-256, and the shared
cache was still byte-identical at the end of the whole run.

**But `--out` does not protect a *reader*, and that is the part the broadcast
gets wrong.** `strehl stack` calls `align_cmd::load_or_solve`, which reads
`sidecar_path(dir)` — the shared entry — no matter what any agent passed to
`align --out`. The isolation primitive that covers **both** directions is
**`$STREHL_CACHE_DIR`**, which `cache_root()` honours ahead of `%LOCALAPPDATA%`.
Recommended standing rule, stronger than the one broadcast:

```
$env:STREHL_CACHE_DIR = "C:\dev\strehl-out\<MILESTONE>\warpmaps"
```

### 14.3 The two guards the orchestrator asked for already exist and already fire (H3)

It offered to assign *"the tool should refuse a sidecar whose frame count or
stack digest disagrees with the bracket"*. **Both are already implemented and
enforced on the default path.** `load_or_solve` (`align_cmd.rs:967-980`) checks
`map.check_stack(&identity)` and `map.len() == paths.len()`, and `check_stack`
(`warpmap.rs:419-420`) delegates to `StackIdentity::check` (`warpmap.rs:256`).

Power control, run **before** the treatment so a dead loader could not be
mistaken for a clean result: a genuinely different bracket (`--limit 5`)
applied to the 6-frame bracket was **refused, rc=1**:

```
Error: the sidecar named by STREHL_WARPMAP (...\side-5-cr.txt) was not fitted on this bracket
Caused by: this warp map was fitted on stack "bee-3-cpl" (digest 0a23bab801e24617, 5 frames)
           but was applied to "bee-3-cpl" (digest 216b68743acc6a1c, 6 frames)
```

So the loader **can** say otherwise, and M99's *"truncated sidecars are silently
accepted by short runs"* is not what this code does. What actually happens is
duller and still bad: a `--limit 40` run legitimately matches a 40-frame entry,
because the digest is computed over the 40 files you passed. Each individual
run is correct; the *cache thrashes*, and every mismatched run pays a full
silent re-solve.

### 14.4 The field that is NOT guarded is `resampler` — and it is the one I just shipped (H2, H4)

`StackIdentity::check` compares **digest and frame count only**. Nothing
compares `resampler`. Mutating one line of a sidecar, `resampler catmull-rom`
-> `resampler lanczos3`, and applying it to the bracket it was actually fitted
on:

| sidecar | rc | announcement line |
| --- | --- | --- |
| catmull-rom | 0 | `alignment      : ON (sidecar-override), reference frame 0, 6 placed / 0 refused` |
| lanczos3 | 0 | `alignment      : ON (sidecar-override), reference frame 0, 6 placed / 0 refused` |

**Accepted, and the two announcements are byte-identical.** The operator gets
no signal whatever.

That is only a hazard if the field is honoured on the read path, so K10 tested
it, determinism control first:

| check | result |
| --- | --- |
| H4c determinism: same sidecar rendered twice | **PASS** — byte-identical, `f049786a…`, 49 449 626 B |
| H4 treatment: catmull-rom vs lanczos3 sidecar | **HONOURED** — `f049786a…` vs `9f309ca9…` |
| differing bytes | **26 278 128 / 49 449 626 = 53.1412%** |

**A stale cache entry silently changes which kernel gathers every pixel, moving
53.1412% of the output bytes, while announcing itself identically.**

This matters more than a generic staleness bug because of what this milestone
just measured and landed. The kernel is worth **+0.1160 dex** on the 0.30–0.48
cyc/px band — ~~**59% of the high-band loss**, the largest single sharpness
number on the table~~ **— the "sharpness" framing is RETRACTED, see §23; the
59%-of-the-gather's-loss arithmetic itself stands** — and arm 9 shipped `--resampler`, the flag that writes
this field. **I have made an unguarded field easier to vary.** If one agent
caches a `lanczos3` solve for a bracket, every later render of that same
bracket by any agent silently gathers with Lanczos-3, and any sharpness number
taken from it is drawn from a different pipeline than the one its author
believes they are measuring.

### 14.5 The fix I recommend, and I hold the file

`align_cmd.rs` is assigned to me. **I am reporting rather than fixing, per your
instruction.** The change is small: `StackIdentity::check` is the wrong place —
it identifies a *stack*, not a *solve* — so the comparison belongs next to the
existing `map.len()` check in `load_or_solve`, where a mismatch already
re-solves rather than failing. Treat a resampler mismatch exactly as the frame
count is treated:

```rust
Ok(()) if map.len() == paths.len() && map.resampler() == want_resampler => {
    return Ok(Some((map, "sidecar")));
}
```

…with the `eprintln!` naming both kernels. That keeps cache semantics (re-solve
on a miss, never consume the wrong thing) and costs nothing when they agree.
Two caveats I cannot resolve from my side: the merge has no `--resampler` of
its own, so `want_resampler` has to come from somewhere — the honest default is
`Resampler::CatmullRom`, matching the solve `load_or_solve` would produce — and
the `STREHL_WARPMAP` path in `merge_cmd.rs:1060` deliberately hard-fails
instead of re-solving, so it needs the same comparison as an `ensure!`.
**`merge_cmd.rs` is contended (M97), so I have not touched it.**

Separately: the announcement line should print the resampler. It currently
prints reference frame and placed/refused counts, which is exactly the
information that was already guarded, and omits the one field that is not.

### 14.6 What this does and does not invalidate in my own work

**I was not the agent writing that file.** No `warpmap*.txt` exists anywhere
under `D:\personal\macro`; my only two `strehl align` invocations before tonight
targeted `C:\nonexistent-dir-m95` and failed on the directory (`Test-Path` =
False, nothing created); and a grep of all my committed code for
`D:\personal|D:\macro|write_text|write_bytes|std::fs::write|File::create`
returns only **read-only** path constants at `k5_port.py:38` and
`k8_population.py:74`. Every write goes to `experiments/M95-kernel/out/`,
`C:\dev\strehl-out\M95-kernel\`, or `$env:TEMP`. Tonight's K9/K10 runs used
`--out` and `STREHL_WARPMAP` throughout and left the shared cache
byte-identical, asserted at the end of both scripts.

**Nothing I have reported is invalidated.** Arm 9's B23 ringing, K22 step, B24
election, the crops and the B22 taps never read a sidecar at all — B24 uses
synthetic per-frame phases `frac(0.37i)`/`frac(0.61i)`, a choice registered in
ADDENDUM 2 precisely to avoid common-mode bias. Only the B22 dex gain read one,
and it read the **quarantined 8-frame copy**, not the shared file. `k8_population.py`
then re-measured that gain across four populations — including one with **no
sidecar and no coverage zoom at all** — and found the worst deviation
**0.0007 dex against a 0.02 bar registered before the run**, with the K25 null
exactly 0.000000 on all four. The cr/lz *levels* move with the population
(0.1845 -> 0.1755) while the paired *difference* does not, so the instrument is
demonstrably responsive to geometry and the paired design is what makes it
immune.

**One honest residual.** Arm 8's ISO/COMP dose-ladder *values* were taken
through sidecar warps and were not individually re-run under a different
population; only the structural claim was cross-checked, via NOZOOM's
`cr = +0.1755` at scale exactly 1.0 reproducing `COMP(1.0) = +0.1667` on a
sidecar-free population, differing by 0.0088 dex. The conclusion survives; the
values are mildly population-dependent. Say the word and I will re-take them.

---

## 15. Two orchestrator corrections, re-tested

Instruments: `experiments/M95-kernel/src/k11_exitcode.py` (+ the two probes it
drives), raw output in `out/k11_exitcode.{json,txt}`. Bars in the docstring,
written before the run.

### 15.1 The truncated-pipeline exit code — the remedy is right, the mechanism is not

The report was that `... | Select-String ... | Select-Object -First N` makes
`$LASTEXITCODE` read **0** after a command whose true code is 1, and that this
"turns a red control green". A false green is the dangerous direction, so the
bar was: **CONFIRM-FALSE-GREEN** if any arm reads 0 for a probe whose true code
is 1, **NO-FALSE-GREEN** otherwise.

Two probes separate the candidate triggers: a *fast* one that has already
exited when the consumer stops the pipeline, and a *slow* one streaming over
~6 s so truncation stops it mid-run. Wall-clock is the positive control that
truncation actually happened — a truncated arm must finish in ~1–2 s against
~6 s or it proves nothing. Shells: **pwsh 7.6.5** and Windows PowerShell
**5.1.26100.9168**.

| shell | arm | true | read | secs | truncated |
| --- | --- | --- | --- | --- | --- |
| pwsh 7.6.5 | slow exit1, no pipeline | 1 | 1 | 6.3 | no |
| pwsh 7.6.5 | slow exit1, `-First 3 of 10` | 1 | **none emitted** | 2.1 | yes |
| pwsh 7.6.5 | slow exit0, `-First 3 of 10` | 0 | **none emitted** | 2.1 | yes |
| pwsh 7.6.5 | slow exit1, `-First 99` | 1 | 1 | 6.3 | no |
| powershell 5.1 | slow exit1, `-First 3 of 10` | 1 | **-1** | 1.4 | yes |
| powershell 5.1 | slow exit0, `-First 3 of 10` | 0 | **-1** | 1.4 | yes |
| powershell 5.1 | fast exit1, `-First 3 of 10` | 1 | 1 | 0.1 | n/a |

**Verdict as originally recorded: NO-FALSE-GREEN.** Across 20 arms on two
shells, no arm read 0 for a probe whose true exit code was 1.

> **RETRACTED 2026-08-24 15:5x — THIS VERDICT IS REFUTED, AND THE ORCHESTRATOR'S
> ORIGINAL REPORT WAS RIGHT.** K11 could not have produced a false green: every
> arm ran in a fresh `-Command` session, where the value `-First` leaves behind
> is `$null`, never 0. The instrument was blind to the disturbance it was aimed
> at, and I read its silence as evidence of absence. Measured refutation and
> mechanism in **§15.3**; the false green reproduces on pwsh 7.6.5 the moment
> the preceding command exits 0, which is the ordinary case in every script.
> Items 2 and 3 below are wrong and are struck in place rather than deleted.

The remedy — capture first, then filter — is right, and I have adopted it.
What the shells actually do:

1. **Windows PowerShell 5.1 returns `-1`** when truncation kills a *still
   running* process — wrong for both a true 1 and a true 0. It is wrong in both
   directions, but it is **nonzero**, so a gate written `if ($code -ne 0)
   { throw }` **fails closed**. That is a false *red*, the safe direction.
2. ~~**pwsh 7.6.5 emitted no exit code at all** in the truncated arms: the
   pipeline stop aborted the remaining statements in the command, so the
   `Write-Output $LASTEXITCODE` after it never ran.~~ **STRUCK — the mechanism
   is wrong.** §15.3 measures the statement *completing* (`DONE=True`) on every
   pwsh arm. Nothing was aborted. `-First` simply **never assigns
   `$LASTEXITCODE`**, so K11's fresh session printed an empty `$null`, which
   K11's digit parser recorded as "none emitted".
3. ~~**Truncation only bites a process that is still running.** Every fast-probe
   arm is correct on both shells, including the truncating one.~~ **STRUCK —
   false on pwsh.** K11's own artifact contains the disconfirming row
   (`fast exit1 | -First 3 of 10` → `None`, `wrong (None)`,
   `out/k11_exitcode.txt` line 9); the §15.1 table above shows 7 of the 20 arms
   and that row is not among them. **I generalised from the excerpt I had
   pasted rather than from the artifact I had generated.**

The half of the report that reproduces exactly is the one about **output**:
the `-First 3` arms saw 3 of 10 lines, so truncation does hide the diagnosis.

**Audit of my own gates — none of them is affected.** Every pass/fail
determination in this milestone was made by `subprocess.run(...).returncode`
inside Python (`k8`, `k9`, `k10`, `k11`, the negative controls), which is immune
to PowerShell pipeline semantics by construction. The two shell-side checks:
`verify_s14.py` was read through `| Tee-Object | Select-Object -Last 6`, and
`-Last` must consume the whole stream so it cannot truncate upstream — it
demonstrably read `exit=1` while the report was RED and `exit=0` once it was
GREEN, which is the discrimination in situ. `corpus_lint` was re-run this
session capture-first: **exit 0, 1235 facts, no violations**.

### 15.2 The sidecar location — re-measured, and the `frames 40` file is M98's scratch

Re-checked at 12:5x, after the correction:

- `Get-ChildItem D:\personal\macro -Recurse -Depth 1 -Filter warpmap*.txt` →
  **count = 0**. There is still no sidecar anywhere in the capture library.
- The shared cache entry `bee-3-cpl-ea1d38ea5c9523c5.warpmap.txt` reads
  **frames 6, reference 3**, mtime **10:39:03** — unchanged across ~2.5 h, so
  nothing has re-solved it.

The file reading **`frames 40, reference 20`** is
`C:\dev\strehl-out\M98\frames\112MSDCF-A\warpmap.txt` — M98's private scratch
copy of a *different* bracket (`112MSDCF`, not `bee-3-cpl`). M98's own
`bee-3-cpl-A` scratch reads `frames 150, reference 75`. Those are copies of
frames into scratch directories, where a sidecar beside the frames is that
run's own business and harms nobody.

`sidecar_path()` (`align_cmd.rs:805-817`) returns
`cache_root()/<leaf>-<key:016x>.warpmap.txt`, and `cache_root()`
(`:820-831`) resolves `$STREHL_CACHE_DIR` first. **`STREHL_WARPMAP` and
`STREHL_CACHE_DIR` are complementary, not alternatives:** `STREHL_WARPMAP`
pins one file for one command and validates it hard, which is what a *control*
needs; `STREHL_CACHE_DIR` relocates the whole read-and-write cache, which is
what an *agent* needs so its ordinary renders neither read nor poison a shared
entry. M97 is already doing the latter —
`C:\dev\strehl-out\M97\cache\bee-3-cpl-ea1d38ea5c9523c5.warpmap.txt` carries
the same canonical-path hash as the shared entry under a private root, which is
the mechanism working as designed.

**One residual worth a line:** a stale per-agent binary built before `8118dd7`
still writes `<stackdir>/warpmap.txt`. The source is fixed; the binaries in
seven `target-*` directories are not necessarily rebuilt. That, rather than
current `main`, is the remaining route by which a file could reappear in the
capture library.

### 15.3 The retraction, measured: `-First` never assigns, and my harness was blind by construction

Instruments: `experiments/M95-kernel/src/k19_preclear.py` and `k19b_seeds.py`,
raw output in `out/k19_preclear.json` and `out/k19b_seeds.json`. Bars in each
docstring, written before the run. Prompted by the orchestrator's 15:51
correction, which added the confound K11 did not control: `$LASTEXITCODE`
retains the previous command's value, so an un-pre-cleared arm can look correct.

**K11's defence, and why it only half works.** K11 ran each arm in a fresh
`-Command` process, so there was no previous command to inherit from. That is
at least as strong as a pre-clear *provided* a fresh session starts unset, so
K19 measured it rather than assuming it: on both hosts, a fresh session prints
`CODE=` empty with `DONE=True`. Isolation holds. K19 then re-ran every arm with
`$LASTEXITCODE` **seeded to 7**, which discriminates four outcomes a pre-clear
to 0 cannot: *set correctly* (reads 1), *never set* (reads 7), *false green*
(reads 0), *statement skipped* (nothing printed).

**K19 result — K11's five "safe" arms per host all genuinely set the code**
(`-First 99`, `-Last 3`, `Select-String`, `Out-String`, no-pipeline all read 1
against a seed of 7). **VERDICT-STAND.** Those claims were established by
isolation, not by luck. But the same run showed the two `-First` arms on pwsh
reading back **7** with `DONE=True` — the statement ran, and the assignment
never happened.

**K19b — the disturbance K11 was blind to.** One arm, three seeds, probe's true
exit code always 1. If the cell echoes its seed, `-First` never set the code.

| shell | arm | seed 0 | seed 7 | seed 1 | reading |
| --- | --- | --- | --- | --- | --- |
| pwsh 7.6.5 | no pipeline (control) | 1 | 1 | 1 | sets it correctly |
| pwsh 7.6.5 | `\| -First 3 of 10` | **0** | 7 | 1 | **never sets it — echoes seed** |
| pwsh 7.6.5 | `\| -Last 3` | 1 | 1 | 1 | sets it correctly |
| pwsh 7.6.5 | slow `\| -First 3 of 10` | **0** | 7 | 1 | **never sets it — echoes seed** |
| powershell 5.1 | no pipeline (control) | 1 | 1 | 1 | sets it correctly |
| powershell 5.1 | `\| -First 3 of 10` | 1 | 1 | 1 | sets it correctly |
| powershell 5.1 | `\| -Last 3` | 1 | 1 | 1 | sets it correctly |
| powershell 5.1 | slow `\| -First 3 of 10` | **-1** | **-1** | **-1** | corrupted, but nonzero |

**VERDICT: FALSE-GREEN-CONFIRMED.** On pwsh 7.6.5 a command whose true exit
code is 1 reads **0** whenever the preceding command succeeded — which is the
ordinary case in every script. §15.1's `NO-FALSE-GREEN` is refuted, and the
orchestrator's original report was correct on this shell.

**The two hosts fail by different mechanisms, and each explains one side of an
argument that has been running all night:**

- **pwsh 7.6.5 — not a race and not a corruption.** `-First` leaves
  `$LASTEXITCODE` exactly as it found it. The *fast* probe, already exited in
  0.3 s, loses the code just as the slow one does, so timing is irrelevant; what
  matters is whether the short-circuit fires at all, which is the quota
  condition `N ≤ objects` (`-First 99` over 10 lines sets the code correctly).
  **The hazard is inheritance, and it is a false green.**
- **Windows PowerShell 5.1.26100.9168 — a genuine race.** The fast arm is
  correct under all three seeds; only truncation of a *still-running* process
  corrupts, and it writes **-1** regardless of seed. **That is a false red and
  a `-ne 0` gate fails closed.**

Both readings in circulation were right about one host and wrong about the
other. The operative rule is unchanged and now rests on three independent
routes: **never read `$LASTEXITCODE` after a pipeline containing `-First`.**
`-Last` and `Out-String` are measured safe here on both hosts, under seeds
chosen to expose staleness.

**What this cost me, stated plainly.** I told the orchestrator their mechanism
was wrong. It was right, and my refutation came from an instrument that could
not have returned the other answer. K11 satisfied the letter of the power
control — it had a positive control for *truncation* (wall-clock 2.1 s against
6.3 s) — but no control at all for the thing it concluded about, the inherited
value. **A positive control for the stimulus is not a positive control for the
conclusion.** The seeded design is the cheap fix and should be standard in any
future exit-code work here.

### 15.4 The quota rule holds on pwsh and is refuted on 5.1 — the mechanism is host-dependent

Instrument: `experiments/M95-kernel/src/k19c_quota.py`, artifact
`out/k19c_quota.json`, **pre-registered and committed at `817038d` before the
run**, prediction included so it could be scored. Prompted by the
orchestrator's correction #2 (16:20), which states the trap is *"deterministic
on QUOTA: `-First N` loses the exit code whenever `N ≤ the number of objects
produced`"*, with no volume threshold.

Every arm is pre-cleared to a literal seed and asserted, 3 reps, true exit code
1, every pipeline emitted as **literal text** — no `switch` and no scriptblock
dispatch, because the orchestrator's own `scriptblock_masks_the_trap.ps1` shows
`& $sb` changes the answer.

| host | arm | objects | N | seed 0 | seed 7 | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| pwsh 7.6.5 | `-First 3` | 50 | 3 | 0,0,0 | 7,7,7 | LOST (echoes seed) |
| pwsh 7.6.5 | `-First 49` | 50 | 49 | 0,0,0 | 7,7,7 | LOST (echoes seed) |
| pwsh 7.6.5 | `-First 50` exact | 50 | 50 | 0,0,0 | 7,7,7 | LOST (echoes seed) |
| pwsh 7.6.5 | `-First 51` | 50 | 51 | 1,1,1 | 1,1,1 | preserved |
| pwsh 7.6.5 | `SS \| -First 3` | 50 | 3 | 0,0,0 | 7,7,7 | LOST (echoes seed) |
| pwsh 7.6.5 | `-Last 3` | 50 | 3 | 1,1,1 | 1,1,1 | preserved |
| powershell 5.1 | `-First 3` | 50 | 3 | 1,-1,1 | -1,1,1 | **NON-DETERMINISTIC** |
| powershell 5.1 | `-First 49` | 50 | 49 | -1,-1,1 | 1,1,-1 | **NON-DETERMINISTIC** |
| powershell 5.1 | `-First 50` exact | 50 | 50 | -1,1,-1 | 1,-1,-1 | **NON-DETERMINISTIC** |
| powershell 5.1 | `-First 51` | 50 | 51 | 1,1,1 | 1,1,1 | preserved |
| powershell 5.1 | `SS \| -First 3` | 50 | 3 | 1,1,1 | 1,1,1 | **preserved** |
| powershell 5.1 | `SS \| -First 3` | 10 | 3 | 1,1,1 | 1,1,1 | **preserved** |
| powershell 5.1 | `-Last 3` | 50 | 3 | 1,1,1 | 1,1,1 | preserved |

**`-Command` vs `-File`, on the arm the orchestrator cites for the `-1` value:**

| host | `-File` seed 0 | `-File` seed 7 | `-Command` seed 0 | `-Command` seed 7 |
| --- | --- | --- | --- | --- |
| pwsh 7.6.5 | 0,0,0 | 7,7,7 | 0,0,0 | 7,7,7 |
| powershell 5.1 | -1,-1,-1 | -1,-1,-1 | -1,1,-1 | -1,1,1 |

**Four results, in descending order of how much they should change behaviour.**

1. **On pwsh 7.6.5 the quota rule is exactly right,** including the boundary:
   `-First 50` loses and `-First 51` preserves over 50 objects, 3/3 reps each,
   under both seeds. This reproduces the orchestrator's 5/5 independently, on a
   different harness. **Quota confirmed.**
2. **On Windows PowerShell 5.1 the direct shape is NON-DETERMINISTIC** — three
   consecutive reps of an identical, pre-cleared command returned `1,-1,1`.
   Not a quota, not reliably a trap: **a coin flip.** That is strictly more
   dangerous than a deterministic failure, because it can pass a test and fail
   in production.
3. **Interposing `Select-String` PROTECTS on 5.1 and does nothing on pwsh.**
   `SS | -First 3` preserved 1,1,1 under both seeds at both line counts on 5.1,
   and lost on pwsh. **This retrospectively vindicates M104c:** its 50-line
   `Select-String | -First 3` arm reading the true code was dismissed as the
   stale-value confound, and it reproduces here *under a pre-clear*. M104c was
   most likely right and measuring 5.1.
4. **`-File` makes 5.1 deterministic where `-Command` is not** (`-1,-1,-1`
   against `-1,1,-1`). That is the source of the orchestrator's observation
   that the corrupted value is `-1` under `powershell -File`: the invocation
   mode is a real variable, not just the host.

**Scoring my registered prediction, which was half wrong.** I predicted
`QUOTA-HOLDS` on pwsh — **correct** — and `QUOTA-REFUTED` on 5.1 *at N=3 over
10 lines, on both shapes* — **wrong on the direct shape**, which is
non-deterministic rather than preserved. My own registered contingency turned
out to be nearer the truth: *"if 5.1 loses on the direct shape and preserves
only via Select-String, the variable is pipeline shape rather than host."* It
is both, interacting — shape matters **on 5.1 only**.

**The operative rule is untouched and I am not proposing any change to it.**
`-First` is unsafe on both hosts: deterministically on pwsh, as a coin flip on
5.1 direct, and safe on 5.1 only through a `Select-String` hop that provides no
protection whatsoever on the other shell. `-Last 3` preserved 1,1,1 under both
seeds on both hosts and both modes.

**But the rationale should not become "deterministic on quota" either.** That
sentence licenses the 5.1 direct case, which is a coin flip, and it licenses an
agent who tests `SS | -First 3` once on 5.1, sees a clean `1`, and concludes
the shape is safe. **This is the same failure the previous rationale had, in
the opposite direction: a mechanism stated more confidently than it was
measured, licensing the case that actually breaks.** The rule needs no
mechanism at all to be followed correctly.

---

## 16. What each kernel does to the chromatic fringing

The orchestrator's third message made this a hard precondition for any default
change: `nearest` was seen to amplify chromatic fringing on the hairs, so a
statement about my kernel's effect on fringing is owed before Lanczos-3 could
be defaulted. Two instruments were built. **The first failed its own power bar
and is reported as a failure**; the second passes on controls that are
structural rather than chosen, and it answers the question in a way that
changes what the by-eye observation means.

### 16.1 The instrument that failed — K12, and it is reported, not patched

`experiments/M95-kernel/src/k12_fringe.py`. It measured surviving lateral
chromatic aberration as the RMS chroma gradient at edges, and validated itself
by planting a known R-vs-G displacement. Bars registered in the docstring
before the run: **C-POWER requires the planted fringe to move the statistic by
at least +0.10 dex.**

| plant | statistic | base | planted | dex | verdict |
| --- | --- | --- | --- | --- | --- |
| 0.5 px | F | 495.1464 | 503.8205 | +0.0075 | fail |
| 0.5 px | Fn | 0.8901 | 0.9312 | +0.0196 | fail |
| 1.0 px | F | 495.1464 | 524.5432 | +0.0250 | fail |
| 1.0 px | Fn | 0.8901 | 1.0214 | +0.0598 | fail |

`C-NULL` passed at max |diff| = 0.000000, so the instrument is deterministic;
it is simply not sensitive enough. **ARM VOID. The bar was not moved and no
kernel number from K12 is quoted anywhere.**

Two disclosures, because both errors were mine. The first version of C-POWER
put only the planted arm through an extra Catmull-Rom gather, so the plant
carried a blur the baseline did not, and that blur partially cancelled the very
fringe being planted; the arms are now resample-matched. Adding the matched
plant and a normalised statistic `Fn` moved the best reading from +0.0075 to
+0.0598 — a factor of eight, and still short.

The diagnosis is worth keeping because it generalises: **at a strong edge,
R − G has a large gradient whether or not the channels are displaced.** A
coloured edge is not a fringe. The planted signal therefore sat on a baseline
roughly seventeen times larger, and no amount of care in the plant fixes a
statistic whose denominator contains the answer. The response was monotonic
across the ladder (495.15 → 503.82 → 524.54), which is what says the metric is
sound and merely swamped rather than broken.

### 16.2 The decidable question, and why it is a different one

Kernels cannot create lateral chromatic aberration. The same geometric
displacement is applied to every channel, so no interpolator introduces a
differential channel shift. What a negative-lobe kernel *can* create is
**ringing** — and ringing becomes a *colour* fringe exactly when the channels
overshoot by different amounts.

So K13 (`src/k13_chroma_ring.py`) measures **differential chroma overshoot**:

> `o_X(i)` is how far channel X's interpolated value at output pixel `i` falls
> outside the range of the two source samples bracketing it — the same
> definition §2 used for luma, where Catmull-Rom's 6.2500% was re-derived
> algebraically as exactly 1/16. `DCO` is the RMS over edge pixels of
> `sqrt((o_R − o_G)² + (o_B − o_G)²)`.

Differential, so ringing that is equal in all three channels contributes
nothing. Only overshoot that differs *between* channels counts, and that is
precisely a kernel-generated colour fringe. Demosaic-free binned quads,
3514 × 2344, 24 tiles of 512 px, five phases, edge mask the top 1% of |grad G|
computed on the **source** and held fixed across kernels so no kernel can
select its own favourable population.

### 16.3 The controls are structural, which is the point

Registered before the run:

- **S1** `nearest` and `bilinear` are monotone: their output is a convex
  combination of the two bracketing samples and **cannot** leave that range.
  Both must read **exactly** 0.000000. This is a positive control that could
  have failed and cannot be met by choosing a threshold.
- **S2** Catmull-Rom and Lanczos-3 both have negative lobes and must read > 0.
- **S3** predicted ordering `DCO(lanczos3) > DCO(catmull-rom)`, from the luma
  overshoot ratio 11.1413 / 6.2500 = **1.7826×**.

| kernel | DCO (DN) | sd | band | Δ band vs cr | DCO vs cr |
| --- | --- | --- | --- | --- | --- |
| nearest | **0.000000** | 0.000000 | −2.3668 | **+0.4135** | 0.0000× |
| bilinear | **0.000000** | 0.000000 | −3.1206 | **−0.3404** | 0.0000× |
| catmull-rom | 2.480280 | 1.905828 | −2.7803 | +0.0000 | 1.0000× |
| lanczos3 | 4.852171 | 3.685417 | −2.5117 | +0.2685 | **1.9563×** |

**S1 PASS** at exactly zero for both. **S2 PASS. S3 PASS** at 1.9563×, close to
the 1.7826× predicted from luma alone. Paired across all 120 tile-phase
samples: **Lanczos-3 exceeds Catmull-Rom on 120/120 = 100.00%**, bootstrap 95%
CI on the ratio **[1.9045, 2.0104]**.

**The row that shows DCO is not a restatement of sharpness:** the two kernels
reading *exactly zero* sit at **opposite ends** of the sharpness range —
nearest +0.4135 dex sharper than the default, bilinear −0.3404 dex softer.
A metric that merely renamed sharpness could not do that. This matters here
specifically, because twice tonight a high-frequency scalar preferred an image
inspection rejected, and the standing objection is that a sharpness metric and
a ringing artifact are the same signal. In DCO they are demonstrably not.

### 16.4 The answer to the question that was asked

**What Lanczos-3 does to the chromatic fringing: it creates 1.9563× the
colour fringe Catmull-Rom creates, and buys +0.2685 dex of band sharpness for
it — 8.8328 DN of new colour fringe per dex.** That fringe is *manufactured by
the kernel*; it is not in the sensor data.

**And this reinterprets the by-eye observation rather than contradicting it.**
`nearest` was seen to amplify chromatic fringing on the hairs. Its DCO is
exactly zero, and provably so. Therefore the fringing seen under `nearest` is
**not created by `nearest`** — it is lateral CA already present in the data,
made visible because a zero-order hold applies no low-pass at all. Catmull-Rom
was not removing that fringe as a virtue; it was blurring it along with the
hairs the owner wants. Two different fringes have been conflated under one
name, and they call for opposite remedies:

| | source | remedy |
| --- | --- | --- |
| fringe seen under `nearest` | optics — lateral CA in the capture | a CA correction, not a blurrier kernel |
| fringe created by `lanczos3` | the interpolator's negative lobes | a kernel with smaller negative lobes |

Blurring the image to hide an optical defect is the trade the pipeline is
currently making by default, and it is the trade the owner is complaining
about.

### 16.5 What this does to my default recommendation — it weakens it

I will not fold this into the Lanczos-3 case. §5 already declined to ship the
B-spline; §7 recommended Lanczos-3 with reservations. **This arm is evidence
against my own recommendation** and it is stated that way: a doubling of
manufactured colour fringe, 120/120 paired, is a real cost on a subject that is
wall-to-wall occluding edges. My position remains that the default stays
Catmull-Rom until the ringing evidence is judged by eye at 100%, and this
result makes me less rather than more confident that Lanczos-3 is the answer.
The kernel that would win on this evidence is one with a **smaller negative
lobe than Catmull-Rom's** — sharper than bilinear, gentler than Lanczos-3 —
and I have not measured one.

**Capture request, for the orchestrator to file:** a lateral-CA target (a
high-contrast radial or slanted-edge chart at the working magnification, same
lens and teleconverter) would let the optical fringe be measured and corrected
directly, which is the remedy the left-hand row above calls for. `bee-3-cpl`
cannot supply it — only 0.0345% of it exceeds 200 DN local contrast.

---

## 17. Fact 1370 fixed — `align --reference` no longer defaults to a worse answer

`align_cmd.rs` came free: M110 committed its `STREHL_SMOOTH` work at `79264b6`,
so the file I had been holding back from is clean and I took the fix rather
than handing it back.

**The trap, confirmed verbatim in the source before touching it.**
`AlignArgs::reference` carried `#[arg(long, default_value_t = 0)]` while the
automatic merge-side path calls `merge_reference(n) = n / 2`. The doc comment
on `merge_reference` already explains why the middle is right — the uncovered
border grows with distance from the reference, and on `bee-3-cpl`'s 186.7 px of
end-to-end drift that is a ~187 px border against a ~93 px one. So an operator
following rule 45 and invoking `align` by hand got a **strictly worse
registration than one who did nothing**, silently.

The fix is `Option<usize>` resolved against `merge_reference(n)` once the frame
count is known, since clap cannot see `n` at parse time. The resolved value is
now **announced**, because a dynamic default that is not printed is its own
small trap.

### 17.1 Bars, registered before the run

`experiments/M95-kernel/src/k14_reference.py`, output in `out/k14_reference.{json,txt}`.
`--out` and `STREHL_CACHE_DIR` both point into `C:\dev\strehl-out\M95-ref`, so
the capture library and the shared cache are untouched.

| bar | result | | |
| --- | --- | --- | --- |
| **R1** default is the middle | `reference frame 3 (middle, default)`, sidecar `reference 3` | rc 0 | **PASS** |
| **R2** *power* — the flag still works | `reference frame 0 (--reference)`, sidecar `reference 0` | rc 0 | **PASS** |
| **R3** range guard survives | `Error: --reference 6 is out of range for 6 frames` | rc 1 | **PASS** |
| **R4** the change is not cosmetic | the two sidecars differ | | **PASS** |

**R2 is the control that could have failed and matters most.** R1 alone is
satisfied by a build that ignores `--reference` entirely — which would replace
one silent trap with a worse one. R3 matters because the guard was re-plumbed
to read the resolved value rather than the raw argument, so it was genuinely at
risk.

### 17.2 R4 passed for the wrong reason first, and I caught it

R4's first diagnostic printed `0/1 frame rows differ`: my row filter looked for
lines starting with `frame`, and sidecar placement rows start with the frame
*index*. So R4 was passing on a whole-file comparison that the `reference N`
metadata line alone would have satisfied. A bar that passes for a reason other
than the one it was written for is not evidence, so the diagnostic was fixed to
read the quantity the reference choice actually controls:

> worst-case `|dx|` over placed frames: **reference 3 → 4.8652 px**,
> **reference 0 → 6.3751 px**. The old default cost **1.3103×** the worst-case
> displacement.

That ratio is measured on a 6-frame bracket, where consecutive-frame drift is
small and asymmetric; it **understates** the full-bracket case the
`merge_reference` comment describes. It is quoted as what it is.

`cargo test -p strehl-cli --bin strehl`: **62 passed, 0 failed.**

### 17.3 Scope

This changes the *default* of a flag, so a caller passing `--reference`
explicitly is unaffected, and the merge-side automatic path never read this
argument at all. Sidecars already written keep whatever reference they were
written with — the field is stored and parsed, not inferred.

---

## 18. The quarantined sidecars — audited, and two of the orchestrator's readings do not hold

Instrument: `experiments/M95-kernel/src/k15_audit.py`, output in
`out/k15_audit.txt`. Bars A1–A4 registered in the docstring before the run.
The prompt for this was an orchestrator report that 11 stray sidecars had been
moved out of the capture library, one of them a **40-frame** solve for
`bee-3-cpl` that any 299-frame render might have silently picked up.

### 18.1 First, my own claim was the one most likely to be wrong

Section 15.2 says a recursive search of `D:\personal\macro` returned **count =
0** at ~12:5x. A file with mtime **09:38:52** was then quarantined out of that
library. Both cannot be right, and one of them is mine, so it was tested first.

**A1/A2 — the probe shape is sound.** Rebuilding section 15's exact command
against a synthetic tree with a file at the same depth as
`<library>\<stack>\warpmap.txt`: `-Recurse -Depth 1 -Filter warpmap*.txt`
returns **1**, and the no-`-Depth` control also returns **1**. The probe was
not blind.

**And a second, independent instrument agrees.** `k10_resampler_field.py`
recorded `"legacy_exists": false` in `out/k10_resampler_field.json` — a Python
`Path.exists()` on `D:\personal\macro\bee-3-cpl\warpmap.txt`, committed at
`c3bb379`, taken at ~12:40. Two instruments of different kinds both say the
file was **absent** an hour after its own mtime.

`map.save()` writes a fresh file and stamps the current time. A file that did
not exist at 12:40 and carries a 09:38:52 mtime was therefore **copied in with
timestamps preserved, not written in place**. That is a different mechanism
from the one rule 45 addresses, and it means the library was written to
**after** `8118dd7` fixed `sidecar_path()`.

### 18.2 The `bee-3-cpl` sidecar holds 8 frames, not 40

Read directly from the quarantined file: `frames 8`, `end 8`, **8 placement
rows, all placed**, `reference 4`, digest `165a1ff35968c615`.

The orchestrator's own byte count refutes the frame count. Across the
quarantine, large solves run at a median **137.5 B/frame** (`bee-2-cpl` 40807 B
/ 299, `lavendar-cpl` 40812 B / 299, `leaf-2-cpl` 25024 B / 182):

> a 40-frame sidecar would weigh about **6000 B**. The file is **1560 B**,
> which is what **8** frames weigh.

**`reference 4` is `merge_reference(8)`.** So this file was written by the
merge-side cache path, **not** by `strehl align`, whose reference defaulted to
0 until §17. It is evidence for a stale pre-`8118dd7` binary, not for the
`align`-default story.

### 18.3 The 299-vs-8 hazard described cannot occur through that path

`load_or_solve` compares `map.len() == paths.len()` and re-solves on a
mismatch. §14.3 measured that guard firing: a 5-frame map applied to a 6-frame
bracket was **refused, rc=1**, with both digests named in the error. A
299-frame bracket meeting an 8-frame sidecar re-solves; it does not silently
merge 8.

The hazard that **is** real is the one §14.4 reported and this does not change:
a sidecar whose count *coincidentally matches*, and the **`resampler` field,
which is validated by nothing** — mutating that one line moved **53.1412%** of
output bytes.

### 18.4 Nothing in this milestone is contaminated, and item 2 changes nothing

Three scripts here invoke `strehl.exe`. `k9_sidecar.py` and
`k10_resampler_field.py` set **`STREHL_WARPMAP`**, whose override path never
reads `sidecar_path()` and is hard-validated; the runs print
`alignment : ON (sidecar-override), reference frame 0, 6 placed / 0 refused`
on a 6-frame bracket — placed equals bracket. `k14_reference.py` scopes both
`--out` and `STREHL_CACHE_DIR` into `C:\dev\strehl-out\M95-ref` and solves
fresh.

**Arm 9's attribution numbers never rendered at all** — they are NumPy gathers
over decoded frames, with no merge and no sidecar in the path.

On the `885e9f7` watershed at `2026-08-24 03:15:23`: every artifact in this
milestone was measured after **12:27** today, so both arms of every comparison
sit on the aligned side, and the kernel attribution is paired regardless.
**No number here needs retaking.**

### 18.5 On recording the whole invocation

Already the practice here, and it is worth confirming rather than promising:
`k10_resampler_field.py:64` records `stack <dir> --limit 6 --gate 0 --out
<dst>` in committed source, with `--gate 0` written explicitly even though the
arm wanted the one-frame case. `k14_reference.py` records `--limit 6`, `--out`
and the full environment override. I will keep doing it.

---

## 19. Both requested fixes were already landed, and the escalation rests on pre-fix evidence

Instrument: `experiments/M95-kernel/src/k16_timeline.py`, output in
`out/k16_timeline.txt`. Bars T1–T4 registered before the run, T4 written
specifically so T2 could not be a foregone conclusion.

### 19.1 Fix 2 landed at `19f1be0`, twenty minutes before it was requested

`--reference` is `Option<usize>` resolved against `merge_reference(n)`, with the
resolved value announced. Bars in §17: R1 default is the middle, R2 the flag is
still honoured, R3 the range guard survives, R4 the change is not cosmetic
(worst |dx| **6.3751 → 4.8652 px**). `cargo test -p strehl-cli --bin strehl`:
**62 passed, 0 failed.** Nothing further is needed.

### 19.2 Fix 1's default location landed at `8118dd7`, and it is the design asked for

Read from the HEAD blob as bytes, not through a shell redirect:

```
pub fn sidecar_path(dir: &Path, config: u64) -> PathBuf {   // canonical path + config
    ...
    cache_root().join(format!("{leaf}-{key:016x}.warpmap.txt"))
}
fn cache_root() -> PathBuf {                          // STREHL_CACHE_DIR, then
    ...  LOCALAPPDATA / XDG_CACHE_HOME  ... .join("strehl").join("warpmaps")
}
```

**T2 PASS:** `sidecar_path` at HEAD resolves under `cache_root()` and contains
no `dir.join(...)`. The caching benefit is kept, `--out` still overrides, and
`STREHL_CACHE_DIR` gives each agent a private root. That is
`%LOCALAPPDATA%\strehl\warpmaps\<leaf>-<canonical-path-hash>.warpmap.txt` —
the per-user, identity-keyed location requested, already shipped.

### 19.3 The remaining piece is in flight by another agent — I did not converge on it

The third point, that a reused sidecar must reject a **mismatched configuration**,
is right and is exactly the hole §14.4 measured at **53.1412%** of output bytes.
It is also **already implemented, and landed at `69f7b4c` while this section was
being written**: `solve_config_key(reference, spans, resampler)`, a
`SOLVE_ENV` list folding `STREHL_SMOOTH`/`STREHL_SMOOTH_HUBER` into the digest,
`merge_config(n)`, and a two-argument `sidecar_path(dir, config)`. The comments
cite M97.

I saw it first as 139 uncommitted insertions in the working tree and left it
alone; M97 committed it minutes later. **That design is better than the
validate-on-load I would have written.** Putting the configuration in the *key*
means differently-configured solves cannot occupy one entry at all, so there is
no mismatch left to detect. I have not touched the file. Two agents in one
function is the failure mode this whole instruction sequence exists to prevent.

*This paragraph originally said the work was uncommitted. `verify_s19.py`
failed on that claim — it re-derives the fact from `git status` and the HEAD
blob rather than from my prose — and the text was corrected to match the world
rather than the check relaxed.*

### 19.4 The returning files do not indict current source

The escalation cites `coffee-bean/warpmap.txt` returning at **10:27:37**,
**10:31:11** and **10:33:42**, concluding that a convention announced is not
enforced and needs code. But the code landed at **10:32:43**.

| cited time | vs the fix | |
| --- | --- | --- |
| 10:27:37 | **−306 s** | before the fix |
| 10:31:11 | **−92 s** | before the fix |
| 10:33:42 | **+59 s** | after, by under a minute |

**T4 PASS, 1 of 3 post-dates the fix.** Two of the three are explained by the
old code outright. The third trails the commit by **59 seconds**, which a
process already running on an already-built binary explains and a fresh
invocation of fixed source does not.

Read from disk, the five quarantined `coffee-bean` files carry mtimes spanning
09:24:21 to 10:33:42 on 2026-08-24; the newest artifact in the quarantine is
`round4-1033` at 10:33:42. That span is the durable form of the claim. What
this paragraph first said was that every one of them was **187 to 256 minutes
old**, which was true when it was written, at roughly 13:40, and false within
the hour — an age is a function of `now`, so recording one records a claim with
an expiry date. `verify_s19.py` duly went RED on it later the same afternoon,
reading 220 to 290, and the verifier was right. None of these files is recent.
"The file returns within minutes" and "just now" describe a population that was
already hours old when the claim was made.

**So the remaining route is stale per-agent binaries built before `8118dd7`** —
the residual §15 flagged as prediction and §18 confirmed by evidence. No further
source change reaches them, because they are compiled artifacts. What closes it
is rebuilding the `target-*` trees, which is an operational step and not a
patch. I would broadcast that rather than another convention.

### 19.5 One correction carried forward

This message repeats that the quarantined `bee-3-cpl` sidecar held a **40-frame**
solve. §18 measured it directly: `frames 8`, `end 8`, **8 placement rows**,
`reference 4`, **1560 B** against a corpus median of **137.5 B/frame**, so 40
frames would weigh about 6000 B. It is an 8-frame solve, and `reference 4` is
`merge_reference(8)`, meaning the merge-side cache wrote it rather than
`strehl align`.

## 20. Crop-instead-of-upsample — already priced, and dead against bars set before it was asked

The orchestrator has re-raised, as facts 1400/1402 and "the cheapest real
sharpness gain on the table", the proposal that `fit_to_cover` stop stretching
the coverage-cropped field back to sensor dimensions and emit the cropped
region at native sampling instead.

M95 arm 5 already priced exactly this proposal, against bars registered in
`experiments/M95-coverage/PRE-REGISTRATION.md` before that arm ran and long
before this request existed. Those bars are reused here verbatim, because
inventing new ones after the fact is moving the goalposts:

  B2-SHIPS  the crop ships if  cost(FIX) < cost(NOW) - 0.10 dex
  B2-DEAD   the crop is dead if cost(FIX) > cost(NOW) - 0.03 dex

The numbers below were printed by `experiments/M95-kernel/src/k17_crop.py` in
this session. Arm 5's own outputs are not cited: a number recalled from an
earlier artifact is not a measurement.

### 20.1 Why it had to be re-run, not cited

`x8_fix.py` reads `D:\personal\macro\bee-3-cpl\warpmap.txt`, falling back to
the quarantined copy. **That original has been quarantined and the fallback now
resolves to an EIGHT-frame solve under a different stack digest**
(`165a1ff35968c615`, not `8d023c0fe355d109`). Re-running arm 5 today would read
8 frames where it originally read 299, and would print a plausible number.
`k17_crop.py` therefore pins its own sidecar and hard-errors on the wrong frame
count, digest **or reference frame**.

### 20.2 The K0 control fired, and the reason is the finding

The first run of `k17_crop.py` **failed** its K0 control: bisection returned
k = 0.997438 against the tool's printed 0.9315. Rather than adjust the bar, I
ran `k17b_kdiag.py` over every available `bee-3-cpl` solve:

| solve | frames | reference | k | 1/k | crop |
| --- | ---: | ---: | ---: | ---: | ---: |
| `M95-pin/...warpmap-bee-3-cpl.txt` | 299 | 0 | 0.997438 | 1.0026 | 0.26% |
| `ORCH-kernel` catmull-rom / nearest / bilinear | 299 | 149 | 0.931464 | 1.0736 | 6.85% |
| `ORCH-gallery3`, `M106` snapshot, `M107-chroma` | 299 | 149 | 0.931464 | 1.0736 | 6.85% |
| quarantined `bee-3-cpl--warpmap.txt` | 8 | 4 | 0.990429 | 1.0097 | 0.96% |
| `M97`/`M113` cache entries | 60 / 8 | 30 / 4 | 0.972688 / 0.990429 | | |

Six independent `reference 149` solves give **k = 0.931464**, agreeing with the
tool's printed 0.9315 to **3.6e-5**. The re-implementation was right; the
sidecar was unrepresentative. Every derived k was checked to be a tight
bracket — covered at k, not covered at k + 1e-6.

**The finding: k is a function of the reference frame.** A reference at the end
of the focus bracket needs a 0.26% crop; a reference in the middle needs 6.85%,
a **26x** difference. The merge's automatic path uses `merge_reference(n) = n/2`,
so the shipped render is the 6.85% one. This also explains the k = 0.9974 that
arm 4 saw and never accounted for.

### 20.3 The measurement

Pinned sidecar `C:\dev\strehl-out\M95-crop\bee-3-cpl-ref149.warpmap.txt`,
sha256 `AA2DE54A47BC4AEE19DE117ED606F949D6BFB11E78D2D250EEC6796D96CB7B71`,
299 frames, reference 149, digest `8d023c0fe355d109`. Base image
`single-noalign.tif` 7032x4688. 40 tiles x 24 frames = 960 pairs per arm.

Controls first, because a null without them is not a claim about the world:

| control | reading | bar | |
| --- | ---: | --- | --- |
| K0 DERIVE k vs the tool | 0.931464 vs 0.931500 | \|d\| < 0.001 | PASS |
| K1 NULL identity warp, no coverage | -0.000041 dex | \|x\| < 0.005 | PASS |
| K3 POSITIVE planted sigma=0.30 px | +0.220899 dex | >= 0.15 | PASS |
| K6 the coverage scale acting alone | +0.183640 dex | — | — |

The arms:

| arm | cost (dex) | sem | n | mean step | near-integer | what |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| NOW | +0.1813 | 0.0031 | 960 | 0.9332 | 9.99% | coverage scale folded in, 7032x4688 |
| FIX | +0.1855 | 0.0017 | 960 | 1.0019 | 10.01% | no coverage scale, ~6548x4366 |
| SNAP | -0.0003 | 0.0005 | 960 | 1.0000 | 100.00% | integer translation, unit scale |

**The crop recovers -0.0042 dex. It is very slightly worse. B2-DEAD fires.**

### 20.4 The composition argument is refuted by measurement

The request argues: *"a global non-integer scale means no output pixel is ever a
pass-through, so the resampler kernel is applied continuously to every pixel"*,
and that this is what makes the -0.2360 dex kernel result bite.

Registered before running: the claim is SUPPORTED if removing the scale puts
>= 50% of sample positions within 0.05 px of an integer, REFUTED if < 15%.
Uniform phase gives 10%.

- **P1 POWER (mandatory, discipline 595).** SNAP is integer by construction and
  reads **100.00%**. The phase metric can see pass-through when it exists.
- NOW reads **9.99%**. FIX reads **10.01%**.

**REFUTED.** Removing the coverage scale changes the pass-through fraction by
**0.02 percentage points**. The scale is not what destroys pass-through — the
per-frame registration translation already has, and it survives the crop. This
is the same conclusion arm 5's phase model reached, now measured directly on
the quantity the argument is about rather than inferred from cost.

SNAP is the geometry floor: with every translation rounded to an integer and
unit scale, the gather costs **-0.0003 dex**, i.e. nothing. **The entire
+0.18 dex is sub-pixel phase**, and no crop reaches it.

### 20.5 The reference frame is not a resampling lever either (R5)

Registered before running: the reference frame is a lever if the NOW arm costs
at least 0.03 dex less on the reference-0 solve. It prices the gather only.

| reference | k | crop | cost (dex) | mean step |
| ---: | ---: | ---: | ---: | ---: |
| 149 | 0.931464 | 6.85% | +0.1813 | 0.9332 |
| 0 | 0.997438 | 0.26% | +0.1975 | 0.9514 |

**NOT A LEVER**, and note the direction: the solve with the **26x smaller crop
resamples 0.0162 dex more expensively**, because its per-frame relative scales
are all one-sided. Crop size and resampling cost are decoupled, which is an
independent confirmation of the phase model from a direction arm 5 never tested.

### 20.6 The scoping claim, checked from source

I was asked to confirm from source rather than from the summary. It does not
hold as stated, in two ways.

**There is no separate `--srgb` output to crop.** `main.rs` sets
`demosaic: demosaic || (srgb && !binned)`, so `--srgb` implies `--demosaic`
unless `--binned` is given. Verified against the shipped binary: `strehl stack
--srgb` on `coffee-bean` wrote `7032 x 4688 ... Malvar-He-Cutler demosaic`.

**And the byte-frozen branch is not the linear branch — it is reached by
elimination.** `write_merged` dispatches: demosaic first, then
`if matrix.is_some() || !applied.is_identity()`, then the frozen arithmetic.
That last branch contains `let v = if srgb { srgb_encode(v) } else { v };`, so
it **can** run with `srgb = true` — whenever there is no usable camera
characterisation and no exposure. `--srgb` is a flag that selects a branch by
interacting with two other conditions, not a separate path.

**The blocker is real but differently shaped.** The crop cannot be a write-branch
decision at all. Output dimensions come from `let geom = first.geometry();` in
`merge_cmd.rs` — decoded from frame 0, before any warp map exists — and that
`geom` feeds the scratch buffers, the estimator, the election and all three
encoders. `fit_to_cover` cannot change it: it returns
`WarpMap::new(prov, geom, map.resampler(), warps)`, the same geometry it was
given. It changes the *mapping*, never the *grid*. Cropping means changing the
grid at its single upstream source, which every branch including the frozen one
reads.

That is survivable — an opt-in flag defaulting to off leaves the frozen bytes
untouched, which is how this codebase already keeps `--srgb` off the frozen
path. But it is not the narrow write-path change the request assumed, and by
20.3 it buys no sharpness.

### 20.7 What the crop is actually worth

My metric compares at matched **object** frequency, deliberately: `m95cov`'s own
docstring records that a fixed band across arms of different sampling density
"is a units error that penalises the magnified arm". So it answers *is
information lost*, and the answer is no — the crop recovers -0.0042 dex.

It does not answer *what does the owner see at 100%*, and there the crop has a
real, non-sharpness benefit worth stating plainly: a 7032x4688 file carrying
6548x4366 of real sampling shows, at 1:1, a **107.36%** view of the data
(1/k = 1.0736). Cropping would show the same field of view with 7.36% more
scene detail per screen pixel, in a smaller file. That is an honesty-of-pixel-count
fix with a presentation benefit, and it is worth doing on those grounds.

**It is not a sharpness recovery and must not be sold as one.** It buys
-0.0042 dex, against -0.2360 dex for the kernel. I would rank it below the
kernel work and below anything that attacks sub-pixel phase, which SNAP shows
is where the entire +0.18 dex lives.

### 20.8 A defect I own

`x8_fix.py`'s fallback to the quarantined sidecar is a live trap in my own
committed experiment: re-running it today reads 8 frames and prints a plausible
wrong number. Guarded in this commit — it now hard-errors unless it sees 299
placed frames — rather than left as a silent hazard.

### 20.9 Verification, and a hole the negative control found

`experiments/M95-kernel/src/verify_s20.py` re-derives every claim above from
the artifact that produced it — the k17 JSON, the k17b output, the pinned
sidecar's own bytes, and the four source files read out of the working tree —
never from this report's prose. It also re-reads the pre-registered bars out of
the committed blob at HEAD, so "the bars predate the run" is checked rather than
asserted. GREEN on 40 checks.

`negctl_s20.py` plants five defects and requires a RED on each. **Its first run
caught only 4 of 5**, and the miss was a defect in the verifier, not the report:
the check for the SNAP pass-through figure used the same string as both the
value and its anchor, so mutating the table left the identical figure in the
prose of 20.4 for the anchor to find, and the check passed on a report that had
become wrong.

Fixed structurally rather than case by case: `num()` now **refuses to run** a
check whose anchor overlaps its own token, and requires every anchor to be
unique in the section. That surfaced a second latent problem immediately — one
anchor did occur twice — which would otherwise have sat there reading green.
Re-run: 5/5 caught, restore byte-identical, post-restore GREEN.

This is the third time in this milestone that a weak anchor produced a green
check on a claim it was not actually testing. The rule that survives: an anchor
must be a *neighbour* of the value, never the value itself.

---

## 21. The gate that could not report its own findings

The orchestrator sent a notice with no task attached: `scripts/corpus_lint.py`
had been unable to print the violations it found, because Python selects the
ANSI codepage for redirected stdout and cp1252 cannot encode the characters
this corpus is written in. `print()` raised mid-loop, the violation list
truncated to nothing, and the process exited 1 — the same code the linter uses
for *violations found*. Their closing line was the part addressed to me: *worth
checking against any harness you have built this session that reports through
stdout.*

I checked. **It was in mine too, and one of the two gates it broke is the one
behind this milestone's headline.**

### 21.1 First, their claim, checked rather than accepted

`e3c01aa` is an ancestor of HEAD, and `scripts/corpus_lint.py:1529` carries
`_stream.reconfigure(encoding="utf-8", errors="backslashreplace")`. Re-run at
HEAD: 158 markdown files, 53 rust files, 1247 facts, **exit 0, no violations**.
That capture is pinned at `out/lint_s21.txt`, and it needs to be, because those
counts and that exit code are properties of the whole shared tree at one
instant — see §21.9. The seven live violations they routed to M107 were fixed
in `63d24ca` before I looked. Nothing I have committed is implicated, which is
the specific question they asked me to answer.

Earlier in this session I saw `corpus_lint` exit 1 once, re-ran it, got exit 0,
and wrote it off as a concurrent writer mid-edit. That explanation may well have
been wrong: an exit 1 with no violation text printed is exactly this defect's
signature. **I recorded a guess where I had no measurement, and the guess was
comfortable.** I cannot now distinguish the two, and I am not going to
retrofit a reason.

### 21.2 The same defect, in my own verifier, measured before it was repaired

`k18_gate702.py`. The subject is `verify_s20.py`, the gate behind section 20.
Both arms run it with stdout on a **pipe**, exactly as an agent tool call or a
CI log does, differing only in `PYTHONIOENCODING`.

The power control comes first, because without it a clean reading below would
be vacuous: a canary printing `Δ − → ≤` must break in the hostile arm. It does
— rc=1, 522 bytes of traceback, `UnicodeEncodeError` — and survives utf-8 at
rc=0. **The instrument can say otherwise.** Then:

| arm | rc | stdout chars | ok lines | verdict printed |
|---|---:|---:|---:|---|
| `PYTHONIOENCODING=utf-8` | 0 | 2300 | 40 | GREEN |
| `PYTHONIOENCODING=cp1252` | 1 | 1937 | 35 | none |
| **unset** | **1** | **1937** | **35** | **none** |

**B1 = EXPOSED.** It died at check 36 of 40, lost 363 characters of its own
report, and never printed a verdict at all.

**B2 = COLLIDING.** The tool failure exits **1**. A subject failure — the
report being wrong — also exits 1. A caller reading the exit code cannot tell
"your report is wrong" from "the verifier fell over".

The third row is the one that matters. **Unset is the default**, and unset is
identical to cp1252. This never showed up because I set `PYTHONIOENCODING=utf-8`
by habit before every python call in this session. That habit is a convention
announced, not a convention enforced, and it was the only thing standing
between me and a silently broken gate.

### 21.3 How wide it was

`k18b_gates.py` runs every read-only `verify_*.py` in this milestone twice,
utf-8 against unset. A gate is EXPOSED if the two runs disagree on anything a
caller reads. Absolute pass or fail is not judged: a gate that is RED in both
modes is consistent and therefore not exposed. The `negctl_*.py` controls are
deliberately **not** run here — inducing a fault in a script whose job is to
restore a file on disk is a bad trade for a number available another way.

**2 of 10 exposed, 3409 characters of verification output lost.**

| gate | utf-8 | unset | exposed |
|---|---|---|---|
| `verify_s16.py` | GREEN, 49 lines | none, **4 lines** | YES |
| `verify_s20.py` | GREEN, 55 lines | none, 47 lines | YES |
| the other eight | unchanged | unchanged | no |

`verify_s16.py` is the worse one and it is already committed. In the caller's
mode it prints four lines and exits 1. Anyone re-running it — another agent, a
future me, CI — would read that as *section 16 fails verification*, which is
precisely the misreading the orchestrator warned about, and would have been
reasonable.

The other eight are not safe, only lucky. They print report text; the day a
report they read gains a minus sign they behave like these two.

### 21.4 The finding that could have withdrawn section 20, and did not

Section 20's negative control scores a planted defect CAUGHT on a non-zero exit
plus a positive BAD count. If a *tool* failure can present the same way, that
5/5 was counting crashes and proves nothing. This is B3, and I registered
before running that a CAUGHT reading here means the 5/5 is withdrawn.

The predicate is read out of `negctl_s20.py` at runtime rather than retyped, so
the arm cannot drift from the control it is testing. A tool-failed run gives
**rc=1, BAD=0**, and the predicate scores it **MISSED**.

**B3 = FAILS SAFE. Section 20's 5/5 stands.**

I want to be exact about why, because it is not to my credit. The predicate
required a positive signal parsed from stdout — `bad > 0` — rather than merely
a non-zero exit. I wrote it that way to count *which* checks failed, not to
defend against a crashing verifier. **It paid a debt I had not knowingly taken
out.** Had I written the obvious `if rc != 0`, this section would be a
withdrawal.

It is now `rc == 1 and bad > 0`, which is strictly stronger, and the control has
gained a **standing tool-failure arm**: it deletes an artifact the verifier must
read, requires rc=2 and a MISSED scoring, and restores the artifact
byte-identically. Discipline 702 is now re-checked on every run rather than
measured once tonight.

### 21.5 The repair, and the same measurement afterwards

Two lines reconfigure both streams to utf-8 with `errors="backslashreplace"`,
which cannot itself raise. Then, for the pair behind the live result, the deeper
half: an `excepthook` that prints the traceback and exits **2**, four explicit
guards routed through the same path, and a terminator line so a truncated run is
visible even by eye. `os._exit(2)` was probed first rather than assumed — a
`sys.exit(2)` inside an excepthook does not set the code.

`k18c_patch_gates.py` applies the shallow half to all 14 gates, byte-compiling
each and rolling back from memory on failure: 12 patched, 2 already repaired, 0
failed.

| after the repair | result |
|---|---|
| canary still breaks under cp1252 | **yes** — the harness is still reproducing the mode |
| `verify_s20.py`, all three arms | rc=0, 2377 chars, 40 ok, GREEN, identical |
| B1 | **NOT EXPOSED** |
| B4 | **FIXED**, tool-failure codes seen `[0, 2]`, never 1 |
| fleet | **0 of 10 exposed**, `verify_s16.py` restored 4 → 49 lines, GREEN |
| `negctl_s20.py` | **5/5** under the stricter predicate, tool arm rc=2 → MISSED, **PASS** |

The canary row is load-bearing. A "0 of 10 exposed" reading is only worth
something if the harness could still have found an exposure, and the canary
still dies in the hostile arm.

### 21.6 Two gates that were RED, and both were telling the truth

Restoring the output made me read gates I had stopped reading. Two were RED in
both modes — consistent, so not exposed, but RED is a claim.

**`verify_s19.py`: I had written a claim with an expiry date.** Section 19 said
every quarantined `coffee-bean` file was *187 to 256 minutes old*. That was true
when written, at roughly 13:40. Read again four hours later it is 220 to 290 and
the gate went RED. **An age is a function of `now`, so recording one records
something that becomes false without anybody touching it.** The report now
records the mtime span, 09:24:21 to 10:33:42, which is the same observation in a
form that does not decay, and the check reads it off the filesystem and requires
the report to state it. GREEN.

**`verify_report.py`: 91 of 93, and neither failure was a wrong number.** Both
claims were present; what failed was *decoy discrimination*. The ladder checks
searched the whole document, and section 20 — written hours later — introduced
`-0.0003` and a timestamp ending `43`, the decoys for a `0.0002` and a `42`
belonging to section 4. **A decoy is a property of the entire document, so
appending a section can retroactively blunt a discriminator written before it
existed.** Anchoring each ladder figure on its own table row fixes it: **93/93
numeric and 17/17 structural, GREEN.**

That is a new failure mode for this milestone's running list. The earlier three
were about anchors being too weak *in place*; this one is about a check that was
sound when written and was invalidated by text added elsewhere, later. Verifiers
rot.

### 21.7 What I am not claiming

I have **not** shown that any number I have reported is wrong. The encoding
defect destroyed output, it did not fabricate it: every arm that printed a
result printed the same result. Both REDs in §21.6 were instrument scope and one
report claim that aged out. Section 20's arms are unmoved, and its 5/5 survives
a control specifically designed to break it.

Residual, stated so it is not discovered later as a surprise: **only
`verify_s20.py` and `negctl_s20.py` have the distinct tool-failure exit code.**
The other twelve gates can no longer be silenced by a codepage, but a genuine
crash in them still exits 1 and is still indistinguishable from a subject
failure. That is a real remaining hole, it is narrower than the one closed, and
it is follow-up work rather than something I am going to claim is done.

### 21.8 Verification, and the two holes the control found

`verify_s21.py` re-derives every figure above from the artifact that produced
it — the pre-fix captures, the post-fix JSON, the negative control's own log,
the source of the repaired gates, `git merge-base` for the ancestry claim, and
the filesystem for the mtime span — never from this section's prose. It is
GREEN, and its run log is `out/verify_s21.txt`. It deliberately does not verify
its own passing-check count: a verifier that checks how many checks it ran
changes that number by doing so, and a self-referential figure is not evidence.

`negctl_s21.py` plants seven defects. **On its first run it caught five**, and
the two it missed were both real holes in the verifier, of two different kinds.

**The first turned a subject failure into a tool failure.** I had anchored the
cp1252 row's ok-line count on a string that contained the same row's character
count. Mutating that character count destroyed the anchor, so the verifier
exited 2 — *I cannot run* — instead of 1, and the control scored it MISSED: the
planted defect was never reported as a subject failure at all. **An anchor must
not contain another verified value**, or breaking one claim silences the check
on its neighbour.

**The second read green on a report that was wrong**, which is the serious one.
The control changed a table cell from one exposure count to another and every
check still passed. Three lines below that table, in prose I wrote myself, the
same figure appears again inside the search window — so the mutation removed
one copy and the check found the other. Anchor uniqueness, which §20.9 added,
does not cover this: **the token has to be unique in the window too.** `num()`
now counts occurrences and treats more than one as a tool failure, which fires
on the *unmutated* report, at authoring time, where it costs a minute.

That makes four distinct ways a weak check has read green in this milestone:
a decoy that occurred by chance, an anchor spanning a line break, an anchor
that was its own token, and now a token with a twin inside its own window. The
rule accumulated so far: **an anchor must be a neighbour of the value, must not
be any other checked value, and the value must appear once and only once in the
window it is checked in.**

After both repairs: **7/7 caught**, every one at `rc=1` with a positive BAD
count, restore byte-identical, post-restore GREEN, and the standing
tool-failure arm reporting `rc=2` scored MISSED, PASS. `corpus_lint` reports
**no violation in any file I own** — the form of that claim is deliberate and
§21.9 says why.

One more thing about that 5, because it would otherwise be a number I remember
rather than one I measured: the passing run overwrote the capture file that
recorded it. `k18d_replay_first.py` regresses exactly the two guards, replays
the control, and restores the verifier from a copy taken beforehand — checking
the restore is byte-identical, and hard-erroring if any regression anchor fails
to land, since a silent no-op would replay 7/7 and let me claim the holes never
existed. It reproduces **5/7 with the same two misses**, and that capture is
`out/negctl_s21_FIRST.txt`. The incidental BAD counts differ slightly from the
original run, because the replay regresses the two guards rather than every
intermediate edit; the two misses are identical.

### 21.9 A green linter is a claim about the tree, not about your commit

I nearly committed §21.8 saying "`corpus_lint` exit 0", which is the same defect
as §19's decaying age in a different coat. Measured, minutes apart, with no edit
of mine in between:

| run | capture | exit | violations |
|---|---|---|---|
| first | not saved to a file | 1 | 1, in `docs/research/M87-occlusion.md` |
| second | `out/lint_s21_now.txt` | 0 | none |

The last commit touching that file **at the time of those two runs** is
`82a6dbb`, `2026-08-24 13:56:49 -0700`, which is before both of them. So the
violation was in another agent's **uncommitted working-tree edit**, and it went
away when they saved a fix. `corpus_lint` reads the working tree of a repository
that seven agents are writing to, so its exit code is a property of the tree at
an instant, not of my commit.

Two consequences, and I am acting on both.

**The claim has to be scoped to what I own.** `verify_s21.py` now parses the
violation lines out of the live capture and requires that none of them names a
path I own, rather than requiring the run to be globally green. That claim is
stable under other agents' work; the old one was not, and would have gone RED
for a reason having nothing to do with me.

That check is green on a capture with no violations in it at all, which makes
it exactly the kind of null this milestone is not allowed to report. So
`negctl_s21.py` carries a standing power control: it plants
`docs/research/M95-kernel.md:1: [S6] planted by the power control` into the
capture and requires the verifier to notice. It does — **rc=1, BAD=1**, capture
restored byte-identical, **PASS**. The check can say otherwise, so its silence
is worth something.

**The first run's output is an observation, not an artifact, and I am marking it
as one.** I did not save it, and M87's buffer is gone, so I cannot re-derive it.
It appears in the table above with its capture column reading *not saved*, and
nothing in §21 depends on it. The rule I broke is my own — capture first, then
read — and it is worth noting that I broke it on the run I did not expect to be
interesting.

This section's own verifier check decayed **inside two minutes** of my writing
it. I checked the attribution by asking git for the *latest* commit touching
that file; it went RED on the next run because M87 committed again at
`14:33:27`. The claim I needed was never "this is the latest commit" but "this
commit predates my runs", which is true forever. So the check now asks whether
`82a6dbb` exists at that timestamp and is an ancestor of HEAD, and says nothing
about what is newest. Second time this milestone — §19's age was the first —
and both times the tell was the same: **the check consulted `now`.**

One thing does fall out of this in my favour. Post-`e3c01aa` the two causes of
`exit 1` are distinguishable: the encoding defect prints **no** violation text,
a real violation prints it. My second run printed the offending line and file,
which is how I could attribute it in one step. Before the fix both causes
printed nothing and exited 1, so the earlier exit 1 I saw in §21.1 remains
unattributable — a concurrent writer is now *confirmed to be a mechanism that
exists*, which is not the same as evidence that it was the cause that time.

## 22. The four-point ladder, the owner's montage, and three instruments that failed their own controls

The orchestrator asked for four things: land the new kernel switchable with the
default unchanged; price Mitchell-Netravali and Lanczos-2, the two intermediates
nobody had measured; score ringing with a registered metric and a flat-region
control; and render a montage for the owner to judge by eye. This section is all
four, plus the three instruments that broke along the way. Two of the three
breakages were caught by controls I had registered against myself, and one of
those controls caught a design flaw in an instrument before its result reached
this report.

Every number in this section was printed by code run in this session. Nothing is
recalled from an earlier note.

### 22.1 Step 1 was already shipped, and Mitchell was already retired

Before building anything I re-derived the state of the tree rather than trusting
the brief. Two things did not match it.

`Resampler::Lanczos3` had already landed switchable with the default unchanged,
at commit `843f6e1`, "M95 arm 9: Lanczos-3 lands switchable, default unchanged
at catmull-rom". Step 1 was done.

Mitchell-Netravali had already been retired in `align.rs:3552`, on the ground
that with `B != 0` the Keys/Mitchell kernel is not interpolating. The
orchestrator's hypothesis was that Mitchell might recover most of the sharpness
at a fraction of the ringing, and so dissolve the trade. It does not, and the
reason is structural rather than a matter of degree: a non-interpolating kernel
does not reproduce a sample it lands exactly on, so it blurs an image even where
nothing has moved.

So the genuinely new kernel was Lanczos-2, which landed at `ac95e1b` with the
default unchanged, together with a test asserting that it has Catmull-Rom's 2.0
px support **and** that Lanczos-3 refuses a border position Lanczos-2 accepts.
That second assertion exists so the support claim cannot be vacuous.

### 22.2 The ladder, against bars committed before the kernel entered any script

B25 to B29 were committed at `42a0c7c`, 15:04:14, before `lanczos2` appeared in
any measurement script. That commit is the evidence that what follows was not
reverse-engineered from a result.

**B25, the identity-phase gate. Disqualifying.** A resampler asked for the pixel
it is already sitting on must return it.

| kernel | identity dex | verdict |
|---|---|---|
| catmull-rom | +0.000000 | PASS |
| **mitchell** | **-0.200830** | **FAIL, not interpolating** |
| lanczos2 | +0.000000 | PASS |
| lanczos3 | +0.000000 | PASS |
| bspline | +0.000000 | PASS |

Mitchell loses 0.2008 dex of high-band amplitude at zero phase shift. That is
the whole of the orchestrator's hypothesis, answered: the trade does not
dissolve, because the kernel that was supposed to dissolve it fails a bar that
has nothing to do with the trade.

**B26, phase-averaged sharpness**, 40 tiles by 7 phases, against Catmull-Rom:

| kernel | phase-avg dex | gain vs C-R | effective support |
|---|---|---|---|
| catmull-rom | -0.2006 | — | 2.0 px |
| mitchell | -0.3738 | -0.1732 | 2.0 px |
| lanczos2 | -0.1963 | **+0.0043** | 2.0 px |
| bspline | -0.0951 | +0.1055 | 2.0 px, IIR prefilter |
| lanczos3 | -0.0663 | **+0.1343** | 3.0 px |

**B27, ringing on a clean 1000 DN step at half-pixel phase.** The harness is
verified analytically: Catmull-Rom must read 6.2500%, exactly 1/16, and it does,
which is what makes the other rows readable.

| kernel | overshoot % | reach px | vs C-R |
|---|---|---|---|
| catmull-rom | 6.2500 | 3 | 1.00x |
| mitchell | 3.4722 | 3 | 0.56x |
| lanczos2 | **6.2500** | 3 | **1.00x** |
| bspline | 10.0481 | 9 | 1.61x |
| lanczos3 | 11.1413 | 5 | **1.78x** |

**B28 fired, and B29 passed.** B28 required the flat-region gain to be reported
beside the detail-region gain. For Lanczos-3 they are +0.1368 flat against
+0.1343 detail: the same number. B29, the ordering control, put Mitchell below
Catmull-Rom as required (-0.3738 against -0.2006), so B26 is readable.

### 22.3 The lever is effective support width, not kernel family

Read the two tables together and the ladder is monotone in support, not in
family. Lanczos-2 has Catmull-Rom's 2.0 px support, and it lands on Catmull-Rom's
sharpness to within 0.0043 dex **and on its ringing figure exactly**, 6.2500%
against 6.2500%. Two kernels from different families with the same support are
the same kernel to within measurement. Lanczos-3, at 3.0 px, is where the
sharpness is. B-spline reaches +0.1055 dex on four taps because its IIR prefilter
is effectively global, which is the same lever reached a different way.

That is the transferable result of this milestone. Choosing a kernel is choosing
a support width; the family name is close to decoration.

### 22.4 The 9.902x ringing figure is stale, and it is still being quoted

The case against Lanczos-3 as default has been carried by a figure of 9.9x the
ringing of Catmull-Rom. That number is retired in this report already, and B27
re-derives the real one this session: **1.78x on a true discontinuity**, reach 5
px against 3. Section 22.7 measures it again on real edges, where it is weaker
still. Anyone still deciding against Lanczos-3 on the strength of 9.9x is
deciding on a number that no longer exists.

### 22.5 The montage, and the rule 47 record

Three arms on the owner's 299-frame `bee-3-cpl`, from one solve, with the kernel
as the only variable. The base sidecar is the orchestrator's own verified
299-frame solve, copied into my scratch and rewritten on the single
`resampler` line, with a hard error if that anchor failed to land exactly once.

- commit SHA at render time: `adff9c8b7818624ba24cd5d21ffd108630e3055d`
- `STREHL_ALIGN` unset, `STREHL_FIX_HALO` unset, `STREHL_WARPMAP` per arm into
  `C:\dev\strehl-out\M95-montage\`, never the capture library
- threads 13, output 7032 x 4688, 197 797 874 bytes per arm
- every arm logged `ON (sidecar-override), reference frame 149, 299 placed / 0 refused`
- invocation, identical but for the output path:
  `strehl stack D:\personal\macro\bee-3-cpl --srgb --exposure 1.54 --gate 4.0 -o <out>.tif`
- `--gate 4.0` is the default value, passed explicitly and recorded, per the
  habit the orchestrator asked for after the M106 freeze attribution

| arm | sha256 | gather, summed across workers |
|---|---|---|
| catmull-rom | `E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112` | 330.606 s |
| lanczos2 | `CE1710CED111C419AA02960963B2FD7C422FCABA7DDA0A5F5C2E6F1CE7C03983` | 1386.041 s |
| lanczos3 | `DC6555BCDAE0FC4B334DE31AD130A0C644068647FA77F5FDD94F3271044B26A9` | 2292.288 s |

The catmull-rom arm reproduces `E400A63A..7112`, which is the hash the
orchestrator's own gate ablation produced. All three arms therefore sit on a
baseline that has been confirmed twice by different agents.

**The cost, with the honesty the measurement requires.** I re-ran the
catmull-rom arm unchanged. It reproduced its output **bit for bit**, and its
gather timer read **411.261 s** against the first run's **330.606 s**. That is
**+24% on an identical invocation**, from contention with the other agents on
this machine. So the cost ratios are a range, not a point:

| arm | vs C-R at 330.6 s | vs C-R at 411.3 s |
|---|---|---|
| lanczos2 | 4.19x | 3.37x |
| lanczos3 | 6.93x | 5.57x |

Lanczos-2 costs between three and four times Catmull-Rom for **+0.0043 dex**.
It has the same support and therefore the same tap count, so the cost is the
transcendental sinc evaluation, not the window. That is the clearest verdict in
this section: Lanczos-2 is an option, not a default, and my pre-registered bar
said "below +0.02 dex is not worth a default change" before I knew the number.

### 22.6 The PIL truncation defect, caught in session

The first montage build read the renders with PIL and printed
`(4688, 7032, 3) uint8`. The tool had written 16-bit RGB. I read the TIFF IFD by
hand, without a library: `BitsPerSample (16, 16, 16)`, and
`7032 * 4688 * 3 * 2 = 197 796 096` against a 197 797 874 byte file. PIL has no
16-bit RGB mode and hands back `mode='RGB'` truncated to 8 bits, `max=255`;
`tifffile` returns `uint16`, `max=65535`.

Every per-crop number that first run printed measured 8-bit quantisation rather
than the kernel, and its region selection picked a defocused background tile
with a 10 DN range and called it texture. None of it was reported. The rebuilt
script asserts the dtype and exits rather than measuring the wrong thing.

I checked the other harnesses for the same defect. `k4_png.py` reads 8-bit BMPs
for display and derives no numbers; `f1_figure.py` uses PIL only to draw. The
registered sharpness instrument reads raw frames through rawpy and never touched
a TIFF. So the blast radius was one unreported run.

**Worth passing on: `ORCH-drift-check/kernel_crops.py`, which produced the
earlier by-eye kernel comparison, reads the same 16-bit TIFFs through PIL.** Its
`to8()` has a `uint16` branch that can never have fired. That comparison was
deliberately visual and computed no sharpness number, so its conclusions stand,
but any number taken from that script in future would be quantisation.

### 22.7 Ringing on real edges: three bars failed, and one of the failures was the point

**Arm 12, registered at `85ee287` before the script existed.** The instrument was
`excess(p) = max(0, A(p) - localmax_C(p), localmin_C(p) - A(p))` over the 3x3
neighbourhood of the shipping default, binned by the default's local gradient
into FLAT, MID and EDGE deciles. R1 required Lanczos-3's EDGE excess to be at
least 3x its FLAT excess; R3 planted a +2000 DN ring on EDGE pixels and required
80% recovery.

| arm | FLAT mean excess | MID | EDGE | n EDGE px |
|---|---|---|---|---|
| lanczos2 | 0.60 DN | 0.97 | 0.48 | 3 323 301 |
| lanczos3 | 30.46 DN | 15.54 | 6.68 | 3 323 301 |

R1 read **0.22x** against a bar of 3.0x: FAIL. R2 passed at 0.071. **R3
recovered 144.1 DN of a planted 2000 DN, 7.2%: FAIL.**

R3's failure is the most useful result in this section, because it makes R1
unreadable. The diagnosis is arithmetic, not statistical. `excess` can only
report an overshoot larger than the local headroom `localmax_C - C`, and at an
edge pixel the 3x3 window already contains the far side of the step, so the
headroom is the height of the step. **The instrument is blind precisely where it
was aimed.** R1's FAIL is a statement about that blind spot and not about
Lanczos-3, and without R3 I would have reported it as evidence that Lanczos-3
does not ring.

I have to own the other half of that. The plant I registered was arithmetically
close to impossible to recover, and I did not see it when I wrote the bar. A
control that cannot pass is no more a control than one that cannot fail.

**Arm 12b, registered at `35c40c2` before its script existed.** ADDENDUM 4's
bars were left exactly as written; their verdicts stand above. The corrected
instrument measures the same exact `excess`, but only on pixels where the
headroom is small and stated, so absorption cannot hide the effect:

- SENSITIVE: `localmax_C - C < 200 DN` and `C - localmin_C < 200 DN`
- NEAR: SENSITIVE, within 2 px of a top-decile-gradient pixel, not itself one
- FAR: SENSITIVE, more than 8 px from any such pixel

The same selection is applied to both bins, so NEAR against FAR is like-for-like.

| arm | NEAR mean excess | FAR mean excess | NEAR/FAR | n NEAR | n FAR |
|---|---|---|---|---|---|
| lanczos2 | 1.33 DN | 0.65 DN | 2.05x | 11 124 | 9 829 407 |
| lanczos3 | 37.34 DN | 28.63 DN | **1.30x** | 11 124 | 9 829 407 |

**R6, the power control, passed: 1874.4 DN recovered of 2000 planted, 93.7%.**
The instrument is alive.

**R4 failed, on a live instrument: 1.30x against a bar of 3.0x.** Lanczos-3's
overshoot is not concentrated near edges. By the bar I registered before
measuring, **this is not ringing and I will not call it ringing.**

**R5 passed decisively: 0.036**, so Lanczos-2's real-edge behaviour is 28x
quieter than Lanczos-3's and B27's synthetic prediction transfers.

What Lanczos-3 actually does is push pixels outside the default's local range
**everywhere**, by 28.63 DN of 65535 in locally flat regions and 37.34 DN near
edges. That is 0.04% to 0.06% of full scale, and it is amplification of whatever
is present rather than an edge artefact. It is the same finding as B28 reached
from the spectral side, and the same finding as the post-hoc scene probe, which
recovered the Lanczos-3 gain in full on synthetic scenes with no noise process
in them at all: +0.1332 on 1/f detail, +0.1366 on a flat spectrum, +0.1368 on
pure white noise, a spread of 0.0036 dex against a kernel separation of 0.3108
dex. `band_ratio` after a resample measures the kernel's transfer function. A
linear kernel cannot choose what to amplify, so on noise-dominated ground the
recovered high-band energy is noise.

### 22.8 The montage, and what the owner is actually choosing between

`C:\dev\strehl-out\M95-montage\M95-kernel-montage.png`, 3760 x 3934,
sha256 `3975bd3b64f25bda8067ceb34db1687dd9ae61fc5f12528f23db0b8f519d73b1`.

Four regions at 1:1, magnified 2x by nearest neighbour so the reader is looking
at real pixels. Two regions are chosen from the data by a stated criterion and
two are the hand-picked regions from the earlier by-eye comparison, carried
unchanged. The automatic regions are selected **on the catmull-rom arm only**,
the shipping default, so the selection cannot favour the challenger.

The selection criterion for the texture region was changed once, and the change
is disclosed: the first version maximised high-band *share*, which is maximised
by flat noisy regions because the denominator collapses, and it duly chose
defocused background. Absolute high-band power cannot be gamed that way. No
pass/fail bar moved.

Per-crop difference from the default, in 16-bit DN of 65535:

| region | lanczos2 mean, max | lanczos3 mean, max |
|---|---|---|
| auto boundary, 31 602 DN step | 46.5, 5 851 | 145.2, 27 697 |
| auto texture | 42.3, 7 658 | 125.0, 10 624 |
| hand thorax hair, in focus | 48.2, 17 410 | 149.7, 16 308 |
| hand leg and claw | 30.3, 6 436 | 101.0, 19 385 |

On the boundary crop the largest single-pixel step is 31 602 DN for the default,
**31 607 for Lanczos-2**, and **37 293 for Lanczos-3**. Lanczos-2 changes the
strongest edge in the frame by five parts in thirty thousand.

Mitchell is deliberately absent from the montage. It fails B25 and is not
shipped, and putting it in front of the eye would invite a judgement on a kernel
that is disqualified on a ground the eye cannot see.

**A metric I retired rather than rescue.** The montage script also computed a
crop-level band-power number. Its power control planted blurs at sigma 0.35 and
0.7 px and required both to move it by at least 0.05 dex. Sigma 0.7 moved it
-0.5374 dex; **sigma 0.35 moved it -0.0263 dex and failed.** I did not relax the
bar. The metric is retired, still printed but labelled, and it adjudicates
nothing here: its measured floor is 6.1x the +0.0043 dex Lanczos-2 effect it
would have had to resolve. The montage's conclusions rest on the exact per-pixel
DN comparison, which is a byte difference and needs no power control, and on the
owner's eye.

### 22.9 Predictions of mine that the measurements refuted

- I expected Lanczos-3's NEAR excess to be of order 100 to 400 DN. It is
  **37.34 DN**, well below my range.
- I expected R4 to pass with a large margin. It **failed at 1.30x**, on an
  instrument proven live at 93.7% recovery. Lanczos-3 does not ring in any
  edge-localised sense on this data.
- I expected R3 to pass. It failed at 7.2%, and on inspection it could hardly
  have done otherwise. That is a defect in my pre-registration, not only in the
  instrument.
- I registered before rendering that Lanczos-2 would be visually
  indistinguishable from Catmull-Rom. At preview scale it is. The owner's
  judgement at 100% is the test that matters, and if they can see a difference
  then B26's +0.0043 dex is wrong.

### 22.10 What I would ship, and what I will not decide

I will not move the default on my own measurement, and I am not able to verify
my own work here.

The evidence, stated so someone else can disagree with it: Lanczos-3 buys
**+0.1343 dex**, 1.363x high-band amplitude, for between 5.6x and 6.9x the
gather cost; it does not ring in an edge-localised way on real data; what it
does instead is amplify everything present, noise included, by about 0.05% of
full scale. Lanczos-2 buys **+0.0043 dex** for between 3.4x and 4.2x the cost
and should ship as an option and nothing more. B-spline is the unpriced
candidate worth a look next: **+0.1055 dex**, 79% of Lanczos-3's gain, on four
taps and 2.0 px of support with no extra border, though its ring reach of 9 px
is the widest measured and it has never been rendered on a real stack.

The question the montage puts to the owner is not "is Lanczos-3 sharper". It
measurably is. It is whether 1.363x high-band amplitude on a subject this
noise-limited reads as detail or as grain, and that is a judgement about the
photograph rather than about the kernel.


### 22.11 The gate on this section, and what its control found in me

`verify_s22.py` is the gate: 57 checks, GREEN. It reconstructs both results
tables cell by cell from the JSON the measurement scripts wrote, hashes all
three renders and the montage off disk and requires those digests to appear in
the prose, and asserts the pre-registration commits are cited. Its exit contract
is three-valued, because after `e3c01aa` a tool failure and a subject failure are
different observations and a gate that cannot tell them apart makes a green run
and a broken run the same: 0 verified, 1 a claim failed, 2 the verifier itself
broke.

`negctl_s22.py` is the control: **7 of 7 planted defects caught, tool arm PASS
(a planted exception exits 2, not 0 and not 1), power arm PASS**, and the report
restored byte-identical after every arm. The power arm appends one byte to the
montage on disk and requires the gate to notice, so the hash checks are shown to
be live rather than vacuously green.

Three defects in my own instruments surfaced here rather than in the report, and
they are the reason this section has a control at all.

**The gate caught me miscounting.** I asserted a figure appeared three times in
this section. It appears five. The assertion was descriptive rather than
load-bearing, but a count I wrote from memory was wrong on the first try, which
is the whole argument for making the machine print it.

**The control caught a weak check.** The first run reported `MISSED` on the R4
ratio: I had planted a wrong value in the results table, and the gate stayed
green because its check required the correct value to appear merely *somewhere*,
and the prose still carried a second copy. A value stated in more than one place
needs its occurrence count asserted, not its presence. Both results tables are
now reconstructed verbatim from the artifacts instead, which checks every cell
at once and is immune to the short-token collision that had a two-decimal value
matching three unrelated places in this section.

**The control's own anchor guard fired.** One planted anchor was written as a
sentence and the sentence wraps across a line in the file, so it matched zero
times. The script hard-errors on a miss rather than proceeding, which is the
only reason that did not become a silently green run proving nothing. Same
failure as the CRLF miss in section 21, and the same fix: anchor on a single
line, never on prose that the formatter is free to re-wrap.

## 23. The scoring band is 87% noise — my own headline, retracted and replaced

The orchestrator issued a HIGH method defect against the high-band-energy metric
family and named this milestone's `+0.1160 dex` directly: *"if any published
sharpness number in this project uses high-band energy without a flat-ROI
placebo, it is mostly measuring noise suppression."* A sibling, M104c-verify,
had published a −33.0% headline that inverted when its own pre-registered
placebo ran, because the flat ROI dropped 30.3% — 92% of the apparent sharpness
loss was interpolation smoothing *noise*.

**The instruction was to run the placebo and report the result either way. I ran
it, and the answer is worse for me than the orchestrator's framing predicted.**

### 23.1 The placebo was already answered, twice, and I had buried it

Before spending a decode I checked what was already known, because duplicating a
live verifier is waste.

- **My own B28 control had already fired.** §22 records a flat-region control at
  **+0.1368** against **+0.1343** on detail — ratio **1.019**, comfortably past
  the orchestrator's ≥0.80 "noise-dominated" threshold.
- **§22.7 had already concluded** that `band_ratio` after a resample measures the
  kernel's transfer function, having found the gain to be **+0.1332** on 1/f
  detail, **+0.1366** on a flat spectrum and **+0.1368** on pure white noise — a
  spread of 0.0036 dex across scenes that share no structure at all.
- **M113-kernel-verify, an independent audit of my instrument, measured it 97.5%
  image-blind**: a closed form over a flat power spectrum with *no image in it*
  reads **+0.1464** against **+0.1428** for nine photographs.

So the placebo question had an answer and I had written two of the three
sentences that answer it. **The defect in my report was never a missing control.
It was placement.** The §22.7 rider sits roughly 1,500 lines below the §7 and
§14.4 headlines it qualifies, and no reader who stops at the executive summary
will ever reach it. A control that fires into a footnote has not been reported.

### 23.2 What I got wrong about the orchestrator's rule, registered before the data

A linear resampling kernel multiplies signal and noise by the same |H(f)|.
Therefore the flat/detail gain ratio **must** read ≈1.0 for *any* linear filter
regardless of what the scene contains. **R ≈ 1 is evidence that the filter is
linear, not evidence that the band is noise.** The orchestrator's ratio rule is
sound for an adaptive or nonlinear process and is **non-diagnostic for a linear
resampler.**

This was registered in commit `c1bd702` *before* any of the data below existed,
precisely so it could not read as a rationalisation after an inconvenient result.
It means the question that actually decides the owner's outcome is not the
placebo ratio at all. It is: **how much of the 0.30–0.48 cyc/px scoring band is
real captured signal in the first place?** Nobody had measured that. Arms 13
through 13g exist to measure it.

### 23.3 Arm 13 — the placebo, run a third time, on a dark frame

`src/x11_bandsignal.py`, registered at `c1bd702`, run before results were seen.

| ROI | kernel gain, catmull-rom → lanczos3 |
| --- | --- |
| 40 sharpest detail tiles | **+0.1284 dex** |
| 40 flattest tiles | **+0.1278 dex** |
| **dark frame, no photograph in it at all** | **+0.1285 dex** |

`R1_flat/detail` = **0.9955**. `R1_dark/detail` = **1.0006**.

**A dark frame reproduces the kernel gain to 0.1%.** This is a stronger form of
M113's closed-form argument, because it runs the real instrument end to end on
real sensor data containing zero scene content. Under the orchestrator's rule the
verdict is NOISE-DOMINATED and the detail claim is not established.

**Controls (P3, P4).** Planting a known signal fraction of 0.90 recovers
**0.8996**; planting 0.00 recovers **−0.0027**; a σ=1.0 px blur moves the
statistic **−2.1465 dex**. The instrument responds, and could have said
otherwise.

**Optics, re-derived from primary rather than recalled (P5).** Decoded
4688×7028, pitch **5.108 µm**. With `FNumber 5.6` and a 2× teleconverter at this
magnification, `N_eff = 5.6 × (1 + 2) = 16.80`, giving a diffraction cutoff of
**108.2 cy/mm** against a Nyquist of **97.9 cy/mm**, so **MTF@Nyquist = 0.0349**
— against the corpus's independently measured **0.036**. The scoring band spans
**58.7–94.0 cy/mm** where MTF falls **0.3447 → 0.0563**. **MTF at 74 cy/mm is
0.2030**, landing inside M85 §7's stated 19–34% range. My predecessor's artifact
floor sits where the optics still deliver about a fifth of full contrast.

**The CFA geometry, which is the mechanism.** Only **2.82%** of the 0.30–0.48
cyc/px scoring band lies inside the red/blue Nyquist cell, and **48.99%** inside
the green quincunx cell. The low band used as the denominator is **100%** inside
red/blue. **Most of the scoring band is past the point where two of three colour
channels can carry any real information at all**, so whatever survives there is
substantially the demosaic's invention plus noise.

**Where arm 13 failed.** Its signal-fraction bracket was **0.1111 to 0.9995** —
useless. The bar was mine and it was badly designed: at ISO 100 on a lit subject,
shot noise dominates read noise by orders of magnitude, so a dark frame cannot
serve as the noise floor for a photograph. Measured near-Nyquist ratio, photograph to
dark: **1820.5×**. `S_upper = 0.9995` passed my registered bar while
saying almost nothing. **I did not bank that pass.** My registered prediction of
0.3–0.7 was **wrong**.

### 23.4 Arm 13b — VOID by its own bar, and the failure was the useful part

`src/x12_bandsnr.py`, registered at `e84082a`. An in-band photon transfer curve,
fitted over **486** non-clipping tiles from 554 to 14663 DN:

    floor(L) = -91.9393 + 0.1372 · L

| bar | result | |
| --- | --- | --- |
| Q1 monotonicity | spearman **+1.0000** | PASS |
| Q3 negative, held-out flat tiles, true S = 0 | **+0.2506** (bar 0.25) | **FAIL** |
| Q2 power, plant S = 0.50 | **+0.6253** (bar ±0.12) | **FAIL** |
| Q2 power, plant S = 0.90 | **+0.9250** | PASS |
| Q4 extrapolation guard | detail 2145–13770 inside fit 1188–13840 DN | PASS |

**Headline `S_detail = +0.1698` is VOID by pre-registration and is not quoted as
a result.** My prediction was wrong again.

**One scalar explains both failures, and that is why the arm was worth running.**
If true noise is *c* × the fitted floor, a pure-noise tile reads `1 − 1/c` and a
plant at 0.50 reads `1 − 1/(2c)`. Q3 gives `c = 1/(1−0.2506) = 1.3341`, which
predicts Q2's 0.50 arm at `1 − 1/2.6682 = 0.6252` against the **0.6253**
observed — **four significant figures**. The model was right and the
*calibration* was wrong, with an identifiable cause: **"flattest by gradient
variance" is a spatial-domain criterion that says nothing whatever about power at
0.30–0.48 cyc/px**, so my calibration set was never the signal-free set I assumed
it was.

### 23.5 Arm 13c — a null guaranteed by physics instead of by a fit

`src/x13_focusnull.py`, registered at `282ad84`. This is a *focus stack*: at a
fixed tile position, frames far from focus are low-passed by a defocus disc whose
cutoff is far below 0.30 cyc/px. Such a tile holds sensor noise and the
demosaic's response to it and essentially no subject detail — at the same
position, sensor, illumination and demosaic as the in-focus frame. No fit, no
sensor constant, no dark frame.

    S = 1 − P_defocus · levelcorr / P_focus

Arm 13b's broken fit is still usable for `levelcorr` alone, because a *ratio* of
`a + b·L` at two levels cancels any scalar error *c* exactly.

| control | result | |
| --- | --- | --- |
| N3 non-degeneracy | **11** distinct sharpest-frames over 40 positions (bar ≥ 4) | PASS |
| N1 null, two most-defocused frames, true S = 0 | **+0.0033** (bar 0.25) | PASS |
| N2 power, plant 0.50 | **+0.5004** (bar ±0.12) | PASS |
| N2 power, plant 0.90 | **+0.8998** | PASS |

**S_detail = +0.1138** (mean +0.1582, min −0.2212, max +0.6167). Verdict
NOISE-DOMINATED, all controls pass. My registered prediction of 0.35–0.65 was
**wrong** — the third in a row.

**A defect I caught in this arm before running it.** The first draft of N2
computed the planted tile's band power *arithmetically* rather than planting a
field into real pixels and measuring it. That control could not have failed. It
was rewritten to plant a real image. Arm 12's R3 taught me that one; discipline
706 names it.

### 23.6 Arm 13d — I attacked my own result and it did not survive

`src/x14_levelsens.py`, registered at `63ba90f`.

One line of arm 13c's own output impeached it. The median focus/defocus band
power ratio was **1.9649×**, so with a neutral level correction the estimator
reads `1 − 1/1.9649 = +0.4910` — the *real signal* bucket. The whole distance
from +0.4910 to +0.1138 was the level correction, whose median was **1.6778×**.
**The correction was doing more work than the measurement it corrected, and I had
not tested it.**

Worse: **my own N1 null could not have caught this.** N1 compares the two most
defocused frames, which sit at nearly the same exposure level, so `levelcorr ≈ 1`
there and N1 passes whether the correction is right or catastrophically wrong. It
is a control that cannot fail in the one dimension that matters — the same defect
I caught in N2 and missed in N1, in the same script.

Measured levels: defocus **5562.4 DN**, focus **9362.3 DN**.

| model | levelcorr | S_detail | bucket | N1 | plants 0.50 / 0.90 | |
| --- | --- | --- | --- | --- | --- | --- |
| M-none, `p = 0` | 1.0000× | **+0.4910** | PARTIAL | +0.0827 | +0.4567 / +0.8904 | admissible |
| M-shot, `p = 1` | 1.6129× | **+0.1573** | NOISE-DOMINATED | +0.0187 | +0.4918 / +0.8983 | admissible |
| M-ptc | 1.6778× | **+0.1138** | NOISE-DOMINATED | +0.0033 | +0.4953 / +0.8989 | admissible |

**All three passed their own controls, the buckets disagreed, and by the bar I
registered before running, arm 13c's headline was downgraded to a bracket
[+0.1138, +0.4910] with the noise-dominated claim NOT asserted.** M-none is the
model most favourable to my published framing and I included it for that reason.

My prediction was structurally right — the models disagree and D2 forces a
bracket — and wrong on one of three values (M-shot predicted ≈0.25, measured
+0.1573).

### 23.7 Arm 13e — stop arguing about the level law and measure it

`src/x15_defocusptc.py`, registered at `acc9a98`.

The three models differ in exactly one physical claim: how in-band noise scales
with exposure level. That is measurable, and I had been arguing about it instead.

**The calibration set, chosen by physics.** A tile position that never comes into
focus *in any frame of the stack* is defocused in all of them. Detect it as
band-power swing < 1.35× across the sampled frames: a position that focuses
somewhere shows a peak, one that never focuses does not. **25 of 64** grid
positions qualified, and they span exposure level naturally because the
defocused background is unevenly lit.

    log10(P) = −1.1839 + 1.0751 · log10(L)
    p = 1.0751,  95% CI [1.0579, 1.0953],  n = 300

| bar | result | |
| --- | --- | --- |
| E3 level span | **4.653×** (bar ≥ 2.0) | PASS |
| E1 held-out null | **0.0183** (bar ≤ 0.25) — arm 13b failed this same bar at +0.2506 | PASS |
| E2 power, plant 0.50 | **+0.4884** | PASS |
| E2 power, plant 0.90 | **+0.8979** | PASS |
| E4 CI excludes `p = 0` (M-none) | **yes** | M-none REFUTED |
| E4 CI excludes `p = 1` (M-shot) | **yes** | |
| E4 CI excludes `p = 1.059` (M-ptc) | no | M-ptc consistent |

**The held-out null improved 13.7× over arm 13b's failed one**, which is the
measurement that vindicates choosing the calibration set by physics rather than
by gradient variance.

**S_detail = +0.1281**, and propagating the CI on *p* gives **[+0.1216,
+0.1336]** — NOISE-DOMINATED across its entire width. **13d's bracket loses its
upper end, because M-none is refuted by measurement rather than by preference.**
First registered prediction of the session to land: I predicted `p` in 0.8–1.1.

### 23.8 Arm 13f — the robustness annex, including a bar I failed

`src/x16_robust.py`, registered at `03dedb0`. `p = 1.0751`, se **0.00585**.

| bar | result | |
| --- | --- | --- |
| F1 extrapolation guard | calibration **3208.7–14930.9 DN**, detail **2092.9–14171.2 DN** | **FAIL — headline is EXTRAPOLATED at the dim end** |
| F2 curvature | quadratic term `q = +0.08001`; S_detail linear **+0.1281**, quadratic **+0.1310**, Δ **0.0028** (bar ≤ 0.02) | PASS |
| F4 own held-out null | **0.0167** | PASS |
| F4 own plants | **+0.4920 / +0.8983** | PASS |

**F3, the number that decides whether any of this is robust:**

| | required `p` | distance from the fit |
| --- | --- | --- |
| S_detail reaches 0.20 (leaves noise-dominated) | **+0.9000** | **29.9 se** |
| S_detail reaches 0.50 (becomes "real signal") | **−0.0250** | **188.1 se** |

I predicted F1 would fail. It did — but at the **dim** end, not the bright end I
guessed, so the prediction was directionally wrong.

### 23.9 Arm 13g — closing the two loose ends with arithmetic, not argument

`src/x17_close.py`. No new bar, no new fitted quantity; every input is a number
printed by a registered arm above.

**The F1 failure, bounded rather than argued.** 32 of 40 detail tiles lie
entirely inside the calibration range (80.0%). Dropping the 8 extrapolated ones
moves S_detail from **+0.1281** to **+0.1188** — a movement of **0.0093**, and
*toward* more noise. **The extrapolation is harmless and, if anything, the
headline is conservative.**

**How far below 1 can `p` actually be dragged?** In-band noise power is
`read + shot·L + prnu·L²`. Read noise is level-independent and drags the log-log
slope *below* 1; PRNU is ∝ L² and pushes it *above*. Measuring `p = 1.0751`
therefore says multiplicative structure slightly outweighs read noise in this
band — which is what one expects at ISO 100 on a well-exposed frame, and it
means the two mechanisms are bounded in opposite directions. Arm 13 measured the
read-noise size directly:

| quantity | value |
| --- | --- |
| in-band power, 40 detail tiles | 1.3728e+03 |
| in-band power, dark frame | 6.7027e-01 |
| read-noise fraction of in-band power | **4.883e-04 (0.0488%)** |
| ⇒ read noise alone bounds the slope at | **p ≥ 0.999512** |
| drag below 1 required to flip the verdict | 0.1000 |
| **required drag ÷ measured read-noise bound** | **205×** |

**Reaching `p = 0.90` would need a level-independent noise term 205× larger than
the dark frame actually shows.**

**The verdict under every level model considered this session:**

| model | S_detail | bucket |
| --- | --- | --- |
| `p = 0` — M-none, refuted at 95% by arm 13e | +0.4910 | PARTIAL |
| `p = 1` — pure shot noise, read- and PRNU-free | **+0.1573** | NOISE-DOMINATED |
| `p = 1.0751` — measured | **+0.1281** | NOISE-DOMINATED |
| 95% CI on `p` propagated | [+0.1216, +0.1336] | NOISE-DOMINATED throughout |

**Only the refuted model escapes the noise-dominated verdict.**

### 23.10 The headline

> **On the same 40 tiles the `+0.1160 dex` kernel gain was scored on, 12.8% of
> the power in the 0.30–0.48 cyc/px band is real captured subject detail. 87.2%
> is sensor noise plus the demosaic's response to sensor noise.**
>
> 95% CI [12.2%, 13.4%]. Robust to every level model that survives its own
> controls, to curvature, and to dropping every extrapolated tile.

**What this retracts.** §7's *"on the exact deficit the owner is complaining
about"* and §14.4's *"the largest single sharpness number on the table"* are
withdrawn, struck in place at both sites. **The `+0.1160 dex` measurement itself
stands** — it is a correct measurement of the kernel's transfer function, it
reproduces to four decimal places, and `x3_kernel.json` re-ran byte-identical.
What is withdrawn is the claim that it is *sharpness*, and therefore the claim
that it is the owner's deficit.

**What this does not say.** It does not say Lanczos-3 is a bad default. A linear
kernel that passes more of the band passes more of *whatever is in* the band, and
12.8% of something is not nothing. It says the gain is roughly one part detail to
seven parts noise, so it should be argued on the owner's montage in §22 and on
ringing, not on a dex figure. **The owner is the only party who has said the
renders look wrong, and the decision remains theirs.**

**What it says about the project-level question.** M85 (fact 1196) established
the softness is upstream of the combination stage. This arm says something
sharper about *why the instrument keeps finding nothing there*: at
`N_eff = 16.80` the optics deliver **MTF 0.0349 at Nyquist**, only **2.82%** of
the scoring band is inside the red/blue CFA Nyquist cell, and the band is 87%
noise. **The scoring band is largely past where this rig records information at
all.** A metric evaluated there is measuring the pipeline's treatment of noise,
which is a real property but not the owner's complaint.

### 23.11 Scoring my own predictions, and what I would do differently

| arm | registered prediction | outcome |
| --- | --- | --- |
| 13 | `S_upper` 0.3–0.7 | **wrong** — 0.9995, and the bar was badly designed |
| 13b | (headline) | **VOID** — failed 2 of 3 own controls |
| 13c | PARTIAL, 0.35–0.65 | **wrong** — +0.1138 |
| 13d | models disagree, bracket; M-none ≈0.49, M-shot ≈0.25, M-ptc 0.11 | **structurally right**, 2 of 3 values right |
| 13e | `p` in 0.8–1.1, NOISE-DOMINATED | **right** — 1.0751 |
| 13f | F1 fails, F2 < 0.01, F3 threshold near `p = 0` | **F1 right but wrong end**, F2 right, F3 right |

Four wrong, one partial, one right. **The predictions were worth registering
precisely because they were mostly wrong**: each one that failed identified a
defect in the arm that produced it, and the sequence 13 → 13b → 13c → 13d → 13e
is a chain of instruments each built to fix the specific failure of the last.

**Two errors I would not repeat.** First, the §22.7 rider was correct and I
placed it 1,500 lines below the headline it qualifies; a control that fires into
a footnote has not been reported, and the placement was the defect, not the
measurement. Second, in arm 13c I caught a control that could not fail (N2) and
shipped another one in the same script that could not fail in the dimension that
mattered (N1). **Auditing one control does not audit the others.**

### 23.12 For the orchestrator

- **The placebo you asked for now has three independent answers, all the same.**
  My own B28 (ratio 1.019), M113's 97.5% image-blindness, and now a **dark frame
  reproducing the kernel gain to 0.1%** (ratio 1.0006).
- **Your ratio rule is non-diagnostic for a linear resampler,** and this was
  registered in `c1bd702` before the data existed. A linear kernel multiplies
  signal and noise by the same |H(f)|, so `R ≈ 1` is evidence of *linearity*.
  The rule is sound for adaptive or nonlinear processes — M104c's case — and
  should carry that scope condition when it is folded.
- **The quantity that decides the question is the in-band signal fraction, and it
  is now measured: 12.8%, CI [12.2%, 13.4%].** I recommend that number, not the
  ratio, as the corpus's test for this metric family.
- **Your HIGH defect is upheld against my report, on placement rather than on a
  missing control.** Both sites are struck in place.
- **A recommendation for the corpus.** M95's `+0.1160 dex`, M104c's `−33.0%`, and
  any other figure in this metric family should carry the in-band signal fraction
  next to it. On this rig it is ~1 part in 8, and that ratio — not the dex — is
  what tells a reader whether a band-energy number is about sharpness.
- **The slanted-edge MTF you suggested is the right instrument and I did not
  build it.** `flat-on-ruler-cpl` would support it and it has no failure mode of
  this kind. That is the single highest-value follow-up here.
- **I have not verified my own work.** Arms 13c through 13g each attack the arm
  before them, but the chain is mine end to end and wants an independent
  verifier.

### 23.13 Artifacts

| file | what |
| --- | --- |
| `src/x11_bandsignal.py`, `out/x11_bandsignal.json` | CFA geometry, optics from primary, three-ROI placebo, controls P3/P4/P5 |
| `src/x12_bandsnr.py`, `out/x12_bandsnr.json` | in-band PTC — **VOID**, retained because its failure is diagnostic |
| `src/x13_focusnull.py`, `out/x13_focusnull.json` | the defocus null, 4/4 controls |
| `src/x14_levelsens.py`, `out/x14_levelsens.json` | three level models, the bracket |
| `src/x15_defocusptc.py`, `out/x15_defocusptc.json` | the measured level law, `p = 1.0751` |
| `src/x16_robust.py`, `out/x16_robust.json`, `out/x16_tiles.npz` | extrapolation, curvature, overturn thresholds; per-tile cache. **The `.npz` is gitignored by `*.npz` and is not committed — rerun `x16_robust.py` to regenerate it (12 decodes). Nothing in the gate depends on it; `x17_close.py` consumes it but its outputs are committed as `x17_close.json`.** |
| `src/x17_close.py`, `out/x17_close.json` | closing arithmetic |

Registration commits, each made **before** its script was run: `c1bd702`,
`e84082a`, `282ad84`, `63ba90f`, `acc9a98`, `03dedb0`.

**No source under `crates/` was changed by any arm in this section.**
`D:\personal\macro` was read only. Dark frame:
`D:\macro-dark-frames\118MSDCF\DSC00001.ARW`, same body, ISO 100.

### 23.14 Verification of this section, and two defects the control found in it

`src/verify_s23.py` reconstructs every number above from the JSON artifacts and
requires it to appear in the section. Nothing is copied from the report into the
gate, so it fails if the two drift apart in either direction. It reports
**76/76 GREEN**.

A gate that has never failed is not a gate, so `src/negctl_s23.py` plants defects
and requires the gate to catch them. Result: **7/7 subject defects caught (rc=1),
2/2 tool defects distinguished (rc=2), report restored byte-exact, gate green on
the restored file.**

**The negative control earned its keep: it found two real holes in the gate.**

- **D1** changed the fitted exponent from `1.0751` to `1.0752` on the law line
  and the gate still read green, because that value appears at three sites and a
  presence check is satisfied by any of them. Fixed by reconstructing the entire
  law line from the artifact and requiring it verbatim. **This subsection
  originally quoted that line back as an example and thereby recreated the very
  duplicate the fix depends on — the control caught that too, on the next run.
  A measured value gets one canonical site in the report; restating it in prose
  is what defeats the check.**
- **D5** deleted the §7 retraction and the gate still read green, because it
  searched the whole document for `RETRACTED, see §23` and **§14.4's identical
  phrase satisfied §7's check**. Fixed by pinning each retraction to its own
  strikethrough anchor. *A check that can be satisfied by the wrong site is not
  checking that site.*

Three normalisations were needed before the gate could read this corpus at all,
each for a failure measured here: **U+2212** minus against Python's ASCII hyphen,
**blockquote markers** surviving whitespace collapse, and **line wrapping**
breaking any quoted phrase matched as a plain string. The section is sliced with
`re.search(r"^## 23\. ", body, re.M)` and never with `split("## 23.")`, which
would also match `### 23.1` and truncate the section to its opening paragraph.

The harness asserts every mutation anchor occurs **exactly once** and hard-errors
otherwise — it fired on the first run, on an anchor written with an ASCII hyphen
where the report has U+2212, which would otherwise have been a silent no-op
scored as a miss. It restores from a byte copy in `%TEMP%` verified by SHA-256,
never with `git checkout --`.

## 24. The cache-contamination control: my renders were immune, and the fix has already landed

The orchestrator issued a highest-severity warning against every A/B run
tonight (fact 1446): an identical command line produces one of two different
output hashes depending only on whether an unrelated `align --reference 40` ran
first, because `StackIdentity` covers the frame set but not `reference` and not
`resampler`. `resampler` is the field this milestone attributes its kernel
numbers to, so the warning names me directly. I was asked to run a control, to
quote both hashes either way, and to report contamination rather than quietly
re-running until it looked stable.

**Result: all five bars passed, including the mandatory power control. Nothing
in this report is contaminated, and I can say why rather than merely that.**

### 24.1 Two things I found before running anything

**The fix already landed.** `69f7b4c`, at 13:41:53 today, *"M97n: key the warp
cache on the solve configuration, not just the path"*. It adds
`solve_config_key(reference, spans, resampler)` at `align_cmd.rs:916`, which
hashes the reference, the span ladder, the resampler's `Debug` token and every
variable in `SOLVE_ENV`; `sidecar_path` at `align_cmd.rs:878` mixes that digest
with the canonicalised capture directory. On HEAD, both named inputs are in the
key. The doc comment describes the defect in the past tense and names this
milestone as the reason it mattered.

That is a **code reading, not a measurement**, and a fix present in the source
is not the same as a fix that works. Everything below exists because of that
distinction.

**My own renders predate it by about six hours.** Every image this milestone
wrote is timestamped 07:31 to 07:45; the fix landed at 13:41:53. So "the fix is
in HEAD" clears nothing of mine. The only question that matters for my numbers
is whether the code path my renders actually took ever consulted the broken key
at all.

### 24.2 The design, and the two bars the orchestrator did not ask for

The prescribed control is: run the arm, hash A; run something that changes
`reference`; re-run the byte-identical arm, hash B; `A != B` means contaminated.
I added two bars to that.

**A determinism baseline (C0).** A hash A/B is meaningless if the merge is not
run-to-run deterministic in the first place. If C0 had failed I would have
reported the whole control void and nothing else.

**A power control (C1).** Discipline 594 came from my own predecessor and it
binds me: a null is a claim about the world only if the instrument could have
said otherwise, and I must show it saying otherwise. So I built a binary from
`11e49dd` -- committed at 13:41:44, **nine seconds before the fix** -- and
verified it contains zero `fn solve_config_key` definitions. If C1 had come back
identical, the honest report would have been *"my control is blind"*, not *"the
fix works"*.

Each `(binary, arm)` sequence runs in one fresh `STREHL_CACHE_DIR` shared across
its steps. A fresh cache per *step* would have made the defect unable to
manifest by construction, which is a rigged null.

The two arms differ only in whether the sidecar is pinned:

| arm | condition | what it stands for |
| --- | --- | --- |
| plain | no `STREHL_WARPMAP` | the code path where the defect lives |
| override | `STREHL_WARPMAP` pinned | **the path my montage actually took** |

Bars and the interpretation of every outcome were committed at `3d00a3e`,
before the script had ever been run, and amended at `448e5b3` for the reason in
§24.5. Neither commit changed a bar.

### 24.3 The measurement

`coffee-bubbles`, 19 frames, merge reference 9, intervening
`align --reference 0`. Hashes are sha256 of the output TIFF, first 16 hex
digits; the full digests are in the artifact.

| bar | binary | arm | A | B | | bar was |
| --- | --- | --- | --- | --- | --- | --- |
| C0 | POST | plain, **nothing between** | `E43C7F14D1EB0B42` | `E43C7F14D1EB0B42` | same | identical -- PASS |
| C1 | **PRE** | plain, align between | `2FD1169422E6A6F1` | `B548E32162522F4E` | **DIFFER** | `A != B` -- PASS |
| C2 | POST | plain, align between | `E43C7F14D1EB0B42` | `E43C7F14D1EB0B42` | same | identical -- PASS |
| C3 | **PRE** | **override**, align between | `2FD1169422E6A6F1` | `2FD1169422E6A6F1` | same | identical -- PASS |
| C4 | POST | override, align between | `E43C7F14D1EB0B42` | `E43C7F14D1EB0B42` | same | identical -- PASS |

**C1 is the whole report.** On the pre-fix binary the defect reproduces exactly
as the orchestrator described it: same command line, different bytes, because an
unrelated `align --reference 0` overwrote the entry the merge then read. My
instrument is not blind, so its nulls are admissible.

**C3 is my clearance.** On that same buggy binary, with the override pinned, the
intervening align changes nothing. The tool says why on its own `alignment`
line: `ON (sidecar-override), reference frame 9, 19 placed / 0 refused`, against
`ON (solved)` on the plain arms. `STREHL_WARPMAP` loads the named file and
hard-validates it with `check_stack`; it never calls `sidecar_path()`, so there
is no key for a stale entry to collide on. My §22 renders were immune **by
construction of the path they took, not by luck of ordering** -- and that is
demonstrated on the binary that carries the defect, which is the strong form of
the claim.

**C2 is for the fleet, not for me.** M97's landed fix holds under the exact
sequence that broke the pre-fix binary.

One internal consistency check worth stating, because it could have gone wrong
quietly: C1's A, C3's A and C3's B are all `2FD1169422E6A6F1`. They should be --
the pinned sidecar was solved at reference 9, which is the same reference the
plain arm's own solve uses, so the override and a clean solve must agree. They
do, to the byte. PRE and POST differ from each other
(`2FD1169422E6A6F1` vs `E43C7F14D1EB0B42`)
because roughly two and a half hours of unrelated commits sit between them,
including M107b's lateral-CA work; that difference is not about the cache.

### 24.4 What this clears, and what it never touched

**§23, tonight's headline, is structurally immune.** Arms 13 through 13g never
invoke the strehl binary at all. They are Python over `rawpy` decodes read
directly from the capture library; grepping their source for
`subprocess|strehl.exe|Popen|os.system` returns only a `git rev-parse` and two
harnesses that spawn `sys.executable`. No `StackIdentity`, no sidecar, no cache.
The same is true of the `+0.1160 dex` kernel figure, which comes from a Python
`resample()` over decoded tiles rather than from the Rust merge.

**§22's montage and B23 ringing are cleared by C3**, on the evidence above.

This also confirms §18.4, which asserted the same immunity from a code reading
in an earlier arm. It was right, but it was an argument; C3 is the measurement.

### 24.5 A finding that nearly cost me the control: a build artifact's mtime lies

I first pinned the shared `target/release/strehl.exe` as my POST binary because
its mtime read 15:46:49, comfortably after the 13:41:53 fix. **That binary's own
`--help` refuted me**: no `--exposure`, no `--demosaic`, no `--binned`, and the
sentence *"It does not yet align, deconvolve, reject outliers, or model
occlusion"*. It therefore predates M86c, M95 and M100 by hours, whatever its
mtime says. Something touched the file without rebuilding it from current
source.

It failed loudly, on an unknown-argument error, which is the only reason I
noticed -- had my arm used only arguments that old surface happened to accept,
I would have reported a stale binary's cache behaviour as HEAD's and never known.
**In a tree with several agents building concurrently, the mtime of a shared
build artifact is evidence of when something touched the file, not of which
source produced it.** Both binaries here are now built from worktrees pinned to
explicit commits, into target directories nothing else writes, and recorded by
sha256:

- PRE `11e49dd`, sha256 `816FA76B87F0FB47…`
- POST `16f2dd2`, sha256 `C9A95492CB675D3A…`

A related honesty note about the artifact: `x18_cachectl.json`'s `post_commit`
field, as written by the run that produced these numbers, records
`8e49842` -- the repository HEAD at the moment the file was written, which had
already moved past the `16f2dd2` the POST binary was built from, because other
agents commit continuously. The field was misleadingly named and I have renamed
it to `repo_head_at_write_time` for future runs. I have **not** re-run to
produce a tidier artifact; the binaries are pinned by sha256, which is a
stronger identity than a commit string, and re-running until the output looks
better is the habit the orchestrator explicitly asked us not to develop.

### 24.6 Environment audit: no further unkeyed solve inputs found

The orchestrator asked that further unkeyed inputs be reported rather than
fixed. Every `STREHL_*` literal in `crates/*/src/*.rs`:

| variable | read at | domain | in the key? |
| --- | --- | --- | --- |
| `STREHL_SMOOTH` | `align_cmd.rs:504` | parameterises the solve | yes, `SOLVE_ENV` |
| `STREHL_SMOOTH_HUBER` | `align_cmd.rs:515` | parameterises the solve | yes, `SOLVE_ENV` |
| `STREHL_ALIGN` | `align_cmd.rs:840` | **gate**, not a parameter | not needed |
| `STREHL_CACHE_DIR` | `align_cmd.rs:943` | the cache root itself | not applicable |
| `STREHL_WARPMAP` | `merge_cmd.rs:1133` | bypasses the cache entirely | not applicable |
| `STREHL_FIX_CA` | `optics.rs:386` | render domain, post-merge | not cached |
| `STREHL_SOFT_GATE` | `merge.rs:331` | merge domain | not cached |
| `STREHL_PHOTOMETRIC` | `merge_cmd.rs:1258` | merge domain | not cached |
| `STREHL_DUMP_ELECTION` | `merge_cmd.rs:1175` | diagnostic | not cached |
| `STREHL_DUMP_NEFF` | `merge_cmd.rs:1255` | diagnostic | not cached |

`STREHL_ALIGN` is the only one worth a sentence: it decides *whether*
registration runs, not *how*, so it cannot produce a differently-configured
sidecar occupying one key. The merge-domain variables change output bytes but
are not cached, so they cannot poison anything -- though they do mean an
identical command line under a different environment still produces different
bytes, which is worth knowing when comparing across sessions.

**One open question for M97, which I did not measure.** `threads` is a parameter
of `solve_map` (`align_cmd.rs:969-977`) and is **not** in `solve_config_key`. If
the pair solve or the global fit is order-dependent across worker counts, thread
count is an unkeyed input to the warps. If it is order-independent it belongs
nowhere near the key. I have not tested it and I am not asserting either way;
it is cheap to settle with the harness in `x18_cachectl.py` and it is M97's
lane, not mine.

### 24.7 What I did not do

I did not touch the cache. `merge.rs` and the cache-key path are M97's exclusive
lane, the fix is already in, and C2 says it works.

The capture library was asserted untouched: `D:\personal\macro\coffee-bubbles`
held 19 files before the control and 19 after. The pre-fix binary honours
`STREHL_CACHE_DIR` (`align_cmd.rs:872` in that tree, `var_os` first), so no
sidecar was ever written beside the RAWs.

### 24.8 Artifacts

| file | what |
| --- | --- |
| `experiments/M95-resample/src/x18_cachectl.py` | the control; bars in the docstring, registered at `3d00a3e` |
| `experiments/M95-resample/out/x18_cachectl.json` | full sha256 digests for all ten renders |
| `experiments/M95-resample/src/verify_s24.py` | reconstructs every number above from that JSON |
| `experiments/M95-resample/src/negctl_s24.py` | plants defects into this section and requires the gate to catch them |

The two pinned worktrees under `C:\dev\strehl-out\M95-cachectl\` are scratch and
are not committed; they are reproducible from the commits named above.

### 24.9 Verification, and one hole the negative control found

`verify_s24.py` reconstructs all 29 claims in this section from the artifact
and reads **29/29 GREEN**. `negctl_s24.py` then plants seven defects into this
section one at a time and two into the gate's own inputs, and requires the gate
to fail on each: **7/7 subject defects and 2/2 tool defects caught**, with the
report restored byte-exact from a `%TEMP%` copy checked by SHA-256 afterwards.

Two design points carried over from the section 23 gate, both of which were
holes there before they were rules here. Table rows are matched **structurally**
-- the one line in the section beginning with that bar's cell -- rather than by
searching the flattened text, because the flattened form of such a cell also
occurs in ordinary prose about that bar and the check would silently window
onto the wrong site. And every anchor must occur **exactly once**, a miss being
a hard error, so that a mutation which fails to land cannot read as a pass.

**The hole this control found is worth stating on its own, because it is a
class of defect rather than a typo.** One check was anchored on the same phrase
that another check asserts as a claim. When the negative control mutated that
phrase, the gate exited 2 -- tool failure -- instead of 1. It noticed the
change, but it reported *"I cannot run"* when the truth was *"the report is
wrong"*, and those are different claims: the first invites you to fix the
harness, the second to fix the number. **An anchor must be prose scaffolding,
never a value the report also claims.** Re-anchored on a neutral phrase, the
same mutation is caught as a subject failure.

Both gates were re-run together after this subsection was written, because
prose that re-quotes a pinned literal recreates the duplicate a check was
pinned against -- which is exactly how section 23's D1 hole reopened once
already. Nothing in this subsection quotes a measured value.
