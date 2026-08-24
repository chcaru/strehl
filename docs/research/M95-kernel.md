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
