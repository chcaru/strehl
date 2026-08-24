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
