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

- **+0.1160 dex** recovered — 6.5× the coverage lever, on the exact deficit the
  owner is complaining about.
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
cyc/px band — **59% of the high-band loss**, the largest single sharpness
number on the table — and arm 9 shipped `--resampler`, the flag that writes
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

**Verdict: NO-FALSE-GREEN.** Across 20 arms on two shells, **no arm read 0 for
a probe whose true exit code was 1.** A failing command was never read as
success. The remedy — capture first, then filter — is right, and I have adopted
it; the stated mechanism is not what these shells do. What they actually do:

1. **Windows PowerShell 5.1 returns `-1`** when truncation kills a *still
   running* process — wrong for both a true 1 and a true 0. It is wrong in both
   directions, but it is **nonzero**, so a gate written `if ($code -ne 0)
   { throw }` **fails closed**. That is a false *red*, the safe direction.
2. **pwsh 7.6.5 emitted no exit code at all** in the truncated arms: the
   pipeline stop aborted the remaining statements in the command, so the
   `Write-Output $LASTEXITCODE` after it never ran. **This is the hazard worth
   broadcasting** — not a gate that reads the wrong value, but a gate that
   **never executes**, which is how a check gets silently skipped.
3. **Truncation only bites a process that is still running.** Every fast-probe
   arm is correct on both shells, including the truncating one.

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
