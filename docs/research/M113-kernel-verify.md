# M113 — independent verification of fact 1420 (the Lanczos-3 kernel claim)

**Agent:** M113-kernel-verify. **Author of the claim:** M95/M85, not consulted.
**Build:** `git archive HEAD` of `e924229` into `C:\dev\strehl-out\M113\tree-head`,
built with a private `CARGO_TARGET_DIR`. Nothing under `crates/` was touched;
nothing under `D:\` was written.

## 1. Verdict

**The physics survives. The published numbers do not, and the controls do not.**

Lanczos-3 really is more accurate than Catmull-Rom, by three independent
instruments, and it does **not** ring visibly in the shipped merge. But every
headline figure in fact 1420 is wrong in the same direction — too large — and
"4 of 4 controls passing" overstates a control set of which two cannot fail, one
is a copy of code that no longer ships, and the discriminating one rewards
ringing.

| # | claim | verdict |
| --- | --- | --- |
| 1 | +0.1343 dex, lanczos3 over catmull-rom | reproduces **synthetically** (+0.1366 my route); **fails end-to-end** at +0.083 to +0.099 |
| 2 | "worth 9.4x the rescale fix" | cross-instrument. Matched-instrument is **6.5x**, which `align.rs` itself says |
| 3 | "a verified patch exists, carried verbatim" | the patch is **not what shipped**; `align.rs` carries different source |
| 4 | "4 of 4 controls passing" | C2 and C3 **cannot fail**; C1 is the only sound one |
| 5 | "control C4 discriminating (0.6466 against 0.4488)" | reproduces exactly, but C4 **ranks a 137%-overshoot kernel first** |
| 6 | corroborating in-crate −0.2894 dex | **confirmed exactly** |
| 7 | metric figure −0.2360 dex | end-to-end, single-frame, cache-exposed in principle |
| 8 | fact 1374, `nearest` resolves hairs | **supported by eye**, with an aliasing caveat |

## 2. Cache contamination (fact 1446) — answered first, as asked

Confirmed in source and empirically at HEAD `e924229`, and **worse than stated**:
`strehl stack` has no `--resampler` flag at all, so a merge's kernel is set
**entirely** by whatever sidecar the cache happens to hold.

```
A1  virgin cache                                        9110C686...
A1b cache wiped, byte-identical command line            9110C686...   (null passes)
A2  after `align --limit 8 --reference 0 --resampler lanczos3`   83A79D6C...
A3  after `align --limit 8 --reference 4 --resampler lanczos3`   DAB7F2AF...
```

**Fact 1420's headline is not exposed.** The +0.1343 comes from
`experiments/M95-resample/src/x3_kernel.py`, which is pure NumPy over one image
and never invokes the binary. The orchestrator's symmetric-collision argument is
correct as far as it goes, but the real exposure is not two arms colliding — it
is one arm silently receiving a kernel nobody asked for, which is one-sided and
can move a result either way. My own arms were isolated with `STREHL_WARPMAP`
(rule 45) and a redirected `STREHL_CACHE_DIR`.

## 3. The number, re-derived by my own route

### 3.1 Synthetic — reproduces

`experiments/M113-kernel-verify/src/k1_truth.py`: M95's `band_ratio` imported
verbatim, plus two reference-based statistics it does not have — RMS against a
Fourier-exact shift, and a round-trip whose truth is the input itself — over an
8-kernel ladder and **117 geometrically-chosen tiles**, against M95's 40
sharpest-by-gradient (rule 24: re-choose, do not re-compute).

```
kernel       band_delta   RMS_TRUTH   RMS_TRIP      (real strehl decode, 117 tiles)
catmullrom      -0.1988     0.02529     0.03518
lanczos3        -0.0622     0.01825     0.02077
```

**+0.1366 dex** against M95's +0.1343. All three instruments rank lanczos3
above catmull-rom on synthetic *and* real data. The gain is real.

### 3.2 End-to-end — does not reproduce

Two full 299-frame merges, one solve, sidecars differing by **exactly one line**
(`Compare-Object`: `resampler catmull-rom` / `resampler lanczos3`), reference
149, coverage 0.9315, pixel-aligned by construction so no registration enters
the measurement. The catmull-rom arm re-rendered from scratch is **byte-identical**
(`9F99A5E3AD5F00F60A27AA06506D5427C195099723D6F7BBFA1F567CBE54F852` twice), so
the arms are reproducible.

```
region             tile      n   gain dex      sem
central half         64   1944    +0.0887   0.0010
central half        128    486    +0.0824   0.0016
central half        256    117    +0.0830   0.0023
central half        512     24    +0.0875   0.0031
whole frame          64   7957    +0.0299   0.0018
whole frame         128   1944    +0.0081   0.0042
whole frame         256    486    +0.0181   0.0073
whole frame         512    117    +0.0409   0.0111
```

Tile-free control, one FFT over the whole plane-grid image, no tiling choice to
make: catmull-rom −2.9355, lanczos3 −2.8362, **gain +0.0994 dex**.

**The end-to-end answer is +0.083 to +0.099 dex, not +0.1343.** That is 26–38%
below the claim. It is also below the author's own corrected +0.1160
(`M95-dose.md` P90, self-labelled a 15.8% over-estimate) — so the correction was
in the right direction and still did not go far enough.

Two things the spread shows. The central-half readings are stable across a 64x
range of tile areas, so **+0.085 is robust**; the whole-frame readings are not,
because most of the frame is featureless white where the metric is measuring
noise. **Range across eight defensible tilings of the same two files: 0.0806 dex** —
more than half the effect being claimed to four decimal places.

## 4. Is the metric rewarding ringing? No — but it would if asked

This was the orchestrator's prime suspicion and it deserves a direct answer.

**The metric is foolable.** Control N3 plants a pure passband boost with no new
information: `x1.5` reads **+0.3510 dex** while RMS-against-truth *worsens* to
0.03035; `x3.0` reads **+0.9553 dex** at RMS 0.12140. A high-band statistic does
rise with manufactured power, exactly as feared.

**It is not being fooled here.** Every kernel on the ladder reads a *negative*
band_delta — none manufactures power, the ideal is 0, and lanczos3 recovers 69%
of the available headroom. And two instruments with no band statistic in them
agree on the ranking. Caveat stated plainly: `RMS_TRUTH` is biased toward
sinc-like kernels because its reference *is* the infinite sinc, which is why
sinc16 wins that column on real data; `RMS_TRIP` has no reference kernel and it
penalises sinc16 below lanczos12.

## 5. Ringing on real occluding edges — it does not survive the merge

M95 measured p99.9 overshoot 9.902x Catmull-Rom's, on a **single frame at a
half-pixel phase**. On the shipped 299-frame merge, on ORCH's two
geometry-chosen ROIs (reused from `experiments/ORCH-drift-check/kernel_crops.py`,
chosen by a third party before any of this ran):

```
reference-free artefact census (strict 8-neighbour extrema, no reference image)
  thorax hair   lanczos3 / catmull-rom   minima 0.9924x   maxima 0.9938x
  leg + claw    lanczos3 / catmull-rom   minima 1.0039x   maxima 1.0048x
```

**1.00x, not 9.9x.** Lanczos-3 creates no excess local extrema in the merged
image. The mechanism is in the run's own log: mean `n_eff` is **55.3**, so each
output pixel averages ~55 independently-warped frames at ~55 different sub-pixel
phases. Ringing is phase-dependent and averages down; passband gain is not and
does not.

An edge-profile probe does find the signature, small: referenced to the far
field, lanczos3 sits +7.91% of local range on the top-1% edges and −4.18% at
2–4 px out on the thorax ROI (a −19.8 DN lobe on a 474 DN local range), with no
negative lobe at all on the leg ROI. In the 1–3 px collar around strong
structure its excursions stay **inside** the un-resampled `nearest` render's
(p1: nearest −2253.7, lanczos3 −2024.5, catmull-rom −1873.0) — it is recovering
contrast, not inventing it.

**By eye at 1:1, magnified x3, no post:** lanczos3 resolves individual thorax
hairs that catmull-rom merges into a soft mass, with no visible fringe or dark
rim on hair silhouettes against the white background. `nearest` is comparably
crisp but carries obvious staircase aliasing on smooth out-of-focus boundaries
and single-pixel colour speckle. **Fact 1374 is supported, with that caveat.**

An earlier envelope-based probe read exactly 0.00 for both arms at the sharpest
edges. That is a **dead instrument, not a clean result** — a 5x5 min/max envelope
widens with the gradient, so it is loosest precisely where ringing lives. It is
recorded here so nobody re-derives it and believes it.

## 6. The arms differ by more than the kernel — a defect nobody has recorded

`merge_cmd.rs::field_for` warps **before** it reads a pixel:
`warp_frame_in_place(..., map.resampler(), ...)` then `green_luma_with_clip`
then `field.compute` then `regularise`. **The resampler is upstream of the focus
field, the gate and the election.** The binary's own printed statistics move:

```
                    catmull-rom   lanczos3
mean n_eff              55.321      53.674
n_eff == 1              38.77%      39.72%
winner response med     4.1675      4.2580
pred sigma gain        0.6273x     0.6314x
```

`--index-map` makes it observable directly: **8.084% of quads elect a different
frame**, 5.643% by more than one frame, mean `|delta index|` 55.24, max 298.
Those pixels are a **different photograph**, not the same photograph differently
interpolated. It also shows up as a level shift — at 8+ px from any edge, on
flat background, lanczos3 reads **+8.83 and +8.78 DN** above catmull-rom in two
independent ROIs, and the stack fits no per-frame gain term.

**This does not rescue the claim, it constrains it — and the direction is
favourable.** Stratifying by election agreement:

| stratum (128 px tiles) | n | gain dex | sem |
| --- | --- | --- | --- |
| agreement >= 0.99 | 12 | +0.0968 | 0.0047 |
| agreement >= 0.95 | 412 | +0.0863 | 0.0015 |
| agreement < 0.95 | 74 | +0.0604 | 0.0056 |

`corr(agreement, gain)` is **+0.30** at 128 px and **+0.41** at 256 px. The gain
is *larger* where the election held still, so **the kernel earns it and the
re-election dilutes it**. Any future end-to-end kernel A/B must report this
split, and so must fact 1374's `nearest` comparison, which will move the
election harder still.

## 7. The controls do not do what the table says

Every published reading reproduces **exactly** — `2.301e-8`, `2.384e-7`,
`0.000e0`, `0.6466` / `0.4488`. The arithmetic is honest. The *power* is not.

| control | published | what would make it fail | verdict |
| --- | --- | --- | --- |
| C1 interpolating | 2.301e-8 | a non-interpolating kernel; Mitchell really does fail it | **sound** |
| C2 partition of unity | 2.384e-7 | nothing — the weights are divided by their sum three lines above | **zero power** |
| C3 support | 0.000e0 | nothing — `if x.abs() >= 3.0 { return 0.0 }` six lines above | **zero power** |
| C4 discrimination | 0.6466 / 0.4488 | a kernel with less passband gain — including every *better* one | **wrong direction** |

C2's own stated purpose is that "a truncated window does not sum to 1 on its
own". Measured un-normalised: **5.701e-3**. Measured through the normaliser:
2.384e-7 against a 1e-6 bar. The normaliser removes the defect C2 exists to
detect by **23914x**, and what remains is f32 rounding of a six-term sum passing
with 4.2x margin over float epsilon (rule 20).

C4 is the one that matters, and it is an **unbounded ordering on passband gain**
when the correct answer is gain = 1.0. Feeding it kernels that are deliberately
worse:

```
kernel                         C4 gain  C4 rank  mean|gain-1|  step over/under
catmull-rom                     0.4488        6        0.5307           0.1250
lanczos3 (patch)                0.6466        4        0.3556           0.2228
lanczos3 (landed f64)           0.6466        5        0.3556           0.2228
catmull-rom + sharpen a=0.25    0.8547        3        0.3023           0.4375
catmull-rom + sharpen a=0.5     1.2606        2        0.4780           0.7500
catmull-rom + sharpen a=1.0     2.0724        1        1.0967           1.3750
```

**C4 ranks first a kernel that overshoots a step by 137% of its own height.** It
cannot guard against ringing; it *rewards* it. That is the exact failure mode
`align.rs`'s own doc-comment names as the reason Lanczos-3 is not the default.

**And the example does not test the code that shipped.** `m95-lanczos.rs`
carries `lanczos3_weights(f: f32)` with two guards; `align.rs` carries
`lanczos3_weights(f: f64)` built from `sinc(t) * sinc(t/3)` with neither. They
agree numerically (worst weight difference 1.192e-7 over a phase sweep) but they
are **separate source, and nothing asserts they agree** — the example would
still print "4/4 controls" after any change to `align.rs`. C3 in particular
asserts a guard clause that the shipped kernel does not contain.

## 8. Cost, which is reported nowhere

Back-to-back on the identical 299-frame stack, same machine, same solve:

```
catmull-rom   total 107.683 s
lanczos3      total 598.655 s        5.56x slower
```

## 9. What reproduces, and what I could not test

`strehl align --resampler-cost --limit 8` reproduces the corroborating figure
**exactly**: catmull-rom retained 0.5139, and `log10(0.5139) = -0.2894`. Note
what it is — the cost of one Catmull-Rom gather against no gather, not a kernel
comparison. Between kernels this instrument reads lanczos3 0.7544, i.e.
**+0.1670 dex**, a third and larger number again.

Not tested: any stack other than `bee-3-cpl`; the interaction with M87's halo
work, which `M95-resample.md` requires before shipping and which fact 1420 drops
along with that report's actual recommendation (**the cubic B-spline, not
Lanczos-3**). Fact 1420 also describes a blocker that no longer exists —
Lanczos-3 landed at `843f6e1`.

## 10. Facts and disciplines for the orchestrator

1. **MEASURED.** The Lanczos-3 gain over Catmull-Rom on the shipped 299-frame
   `bee-3-cpl` merge is **+0.0830 dex (sem 0.0023, n=117)**, stable at +0.0824
   to +0.0887 across tile sizes 64–512 px, and **+0.0994 dex** by a tile-free
   whole-image FFT. Fact 1420's **+0.1343 is 38% high** and M95's own corrected
   **+0.1160 is 28% high**. Two byte-reproducible renders, one solve, sidecars
   differing by one line.
2. **MEASURED.** The synthetic phase-averaged figure **does** reproduce
   independently: **+0.1366 dex** on 117 geometrically-chosen tiles against
   M95's +0.1343 on 40 sharpest-by-gradient. The discrepancy in fact 1 is
   between the synthetic and end-to-end instruments, not an arithmetic error.
3. **MEASURED.** `band_ratio` on the same two files returns anything from
   **+0.0081 to +0.0887 dex** across eight defensible tilings — a spread of
   0.0806 dex. Numbers from it are worth two decimals at most, not four.
4. **MEASURED.** The resampler is upstream of the focus field
   (`merge_cmd.rs::field_for`). Switching catmull-rom to lanczos3 re-elects
   **8.084% of quads**, moves mean `n_eff` from 55.321 to 53.674, and shifts flat
   background by **+8.8 DN**. An end-to-end resampler A/B is **not** a
   single-variable experiment.
5. **MEASURED.** The gain is *larger* where the election held still
   (+0.0968 at agreement >= 0.99 against +0.0604 below 0.95;
   `corr` +0.30 to +0.41). The kernel earns the gain; the re-election dilutes it.
6. **MEASURED.** M95's 9.902x ringing figure **does not survive the merge**:
   strict-extrema census gives lanczos3/catmull-rom **0.9924x and 1.0039x**.
   With mean `n_eff` = 55, phase-dependent ringing averages down and
   phase-independent passband gain does not.
7. **MEASURED, by eye.** At 1:1 lanczos3 resolves thorax hairs catmull-rom
   merges, with no visible fringe on hair silhouettes. Fact 1374 is supported
   for `nearest` too, but `nearest`'s extra detail comes with visible staircase
   aliasing — it is partly alias, not resolution.
8. **MEASURED.** `m95-lanczos.rs` C2 and C3 **cannot fail**: the un-normalised
   weight-sum error is 5.701e-3 and the normaliser three lines above the
   assertion removes it by 23914x; C3 asserts a `return 0.0` written six lines
   above it. "4 of 4 controls" is **1 of 4**.
9. **MEASURED.** C4 is an unbounded gain ordering, and it ranks a kernel that
   overshoots a step by **137%** *above* Lanczos-3. It rewards the ringing
   direction and cannot guard against it.
10. **VERIFIED.** `m95-lanczos.rs` is a **copy** of a superseded patch: f32 with
    two guards, against the landed f64 `sinc(t) * sinc(t/3)` with neither.
    Nothing asserts the two agree, so the example cannot fail in response to a
    change in `align.rs`.
11. **MEASURED.** Lanczos-3 costs **5.56x** the wall clock of Catmull-Rom on the
    same 299-frame stack (598.655 s against 107.683 s). Unreported anywhere.
12. **MEASURED.** The in-crate corroborating figure is exact: catmull-rom
    retained 0.5139, `log10(0.5139) = -0.2894`. It measures one gather against
    no gather, not one kernel against another.
13. **DISCIPLINE.** A ratio between two numbers from **different instruments** is
    not a ratio. Fact 1420's "9.4x" divides a synthetic figure by a real-warp
    one; the matched-instrument answer is **6.5x**, which `align.rs`'s own
    doc-comment already states.
14. **DISCIPLINE.** For every control, write down the input that makes it fail
    **and check that input can reach the assertion**. C2's cannot: it is removed
    by a normalisation between the defect and the check.
15. **DISCIPLINE.** A discriminating control must be bounded by the truth, not
    ordered by a proxy. `assert(a > b)` on a quantity whose correct value is 1.0
    endorses everything above 1.0, which is the artefact.
16. **DISCIPLINE.** An example that carries a **copy** of shipped code verifies
    the copy. Either call the real function or assert the two agree.
17. **DISCIPLINE.** When a knob is upstream of a decision, A/B-ing the knob
    changes the decision too. Report what moved besides the knob — here,
    `--index-map` and the printed `n_eff` both make it visible for free.
18. **DISCIPLINE.** A min/max envelope taken over a neighbourhood widens with
    the gradient, so it has **no power** exactly where edge artefacts live. A
    reading of 0.00 from it is a dead instrument, not a clean result.
19. **DISCIPLINE.** Quote a metric to the precision its **tiling stability**
    supports. Re-run it under two tile sizes and two regions before publishing a
    fourth decimal.
20. **RISK.** `strehl stack` has no `--resampler` flag, so a merge's kernel comes
    **entirely** from cache state. Until M97's `solve_config_key` lands, every
    merge in the corpus has an unpinned kernel, and no record says which one it
    used except the sidecar that happened to be on disk.
