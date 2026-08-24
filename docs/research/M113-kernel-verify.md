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
| 9 | provenance of the arms | **no sidecar at all** — a single frame, synthetic phases; and the "corrected" +0.1160 sits on M112's refuted 8-frame sidecar |

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
(`M95-dose.md` P90, self-labelled a 15.8% over-estimate). **I withdraw the
endorsement of +0.1160 that an earlier draft of this report carried**: §10 shows
that figure has the same provenance defect M112 found under the "9.4x"
denominator, and it is not a sound replacement for +0.1343.

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

Not tested: the interaction with M87's halo
work, which `M95-resample.md` requires before shipping and which fact 1420 drops
along with that report's actual recommendation (**the cubic B-spline, not
Lanczos-3**). Fact 1420 also describes a blocker that no longer exists —
Lanczos-3 landed at `843f6e1`.

## 10. Provenance of the arms — there is no sidecar

The orchestrator asked, after M112 refuted the "9.4x" denominator as an 8-frame
quarantined measurement, what frame set, reference index and `stack-digest` fact
1420's own arms were measured on. The answer is not "the wrong stack". It is
**no stack**.

`experiments/M95-resample/src/x3_kernel.py`, the sole source of +0.1343 /
−0.0663 / −0.2006, imports `IMAGES, TILE, band_ratio, load_luma, pick_tiles`
from `x2_pairs` and runs on `IMAGES["B0"]` — `single-noalign.tif`, which
`x2_pairs.py` documents as *"strehl 1 frame, NO resample"*, k=1.0. Sub-pixel
phases are then applied **in NumPy**. So:

| quantity | frames | reference | stack-digest |
| --- | --- | --- | --- |
| +0.1343 / −0.0663 / −0.2006 (fact 1420 headline) | **1, unaligned** | none | **none** |
| +0.1160 ("the correction", quoted in `align.rs:2752`) | **8** | **4** | **165a1ff35968c615** |
| 0.0143 (the 9.4x denominator, per M112) | **8** | **4** | **165a1ff35968c615** |
| **+0.0830 / +0.0994 (this report, §3.2)** | **299** | **149** | **8d023c0fe355d109** |

The middle two rows are the same sidecar. `experiments/M95-dose/src/y2_combined.py`
declares a primary `MAP` at `D:\personal\macro\bee-3-cpl\warpmap.txt` and a
fallback `MAP_ALT`; `Test-Path` on the primary returns **False**, so the fallback
ran, and the script's own recorded output says so:

```
experiments/M95-dose/out/y2_combined.json
  warpmap  = C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt
  n_placed = 8
```

That sidecar's header reads `stack-digest 165a1ff35968c615`, `frames 8`,
`reference 4`, `heldout-px none`. **This is M112's `bee8`** — the same
quarantined sidecar whose `fix_recovery_dex` M112 showed becomes −0.0030 on the
shipped solve. `M95-dose.md:195` concedes the 8-frame limit but scopes the
caveat to the COMP column only, while P88 presents +0.1160 as measured "on the
real warps". Both KERN and TODAY are warp arms, so the caveat does cover
+0.1160; the report does not apply it there.

**Not one published figure in fact 1420 was measured on the solve the owner
renders.** The +0.0830 in §3.2 is, so far, the only one that was.

## 11. Stack-independence — the gain is flat, and that is not the good news

M112 handed over a prediction it did not test: the coverage fix's recovery
ranges **−0.0330 to +0.1516** across nine stacks, so if the kernel gain is a
real property of the kernel it should be far flatter. It is —
`experiments/M113-kernel-verify/src/k9_stacks.py`, one un-resampled frame from
each of the same nine captures, 117 geometrically-chosen 256 px tiles each,
seven sub-pixel phases, pure NumPy and therefore immune to fact 1446 by
construction:

```
bee-3-cpl  +0.1428   flat-on-ruler-cpl  +0.1428   tweezers-cpl     +0.1428
leaf-2-cpl +0.1430   foam               +0.1433   lavendar-cpl     +0.1427
flowers-cpl +0.1426  lead-1-cpl         +0.1430   flower-bud-alone +0.1425

mean +0.1428   sd 0.0002   range 0.0008 dex   CV 0.002
```

Phase-0 null read 0.00000 dex for both kernels on all nine, so both interpolate
and the table is not an artefact of the harness.

The range is **0.4% of the spread M112 measured for the coverage fix over the
same nine captures**. On the orchestrator's discriminator — *"stack-independence
is exactly what a ringing artefact would not show"* — this is a clean pass, and
it agrees with §5's extrema census and §5's crops: **the gain is not ringing.**

But nine subjects — a bee, foam, a steel ruler, a leaf, tweezers, lavender —
cannot agree to four decimal places about anything real, so I treated the
agreement itself as the next hypothesis to kill (`k10_blind.py`). The
instrument's reading is a power-weighted average of the kernel's |H(f)|² over
two fixed bands, so if |H|² varies slowly the photograph cancels out:

```
closed form, flat spectrum, NO IMAGE AT ALL   +0.1464   (cr -0.2445, l3 -0.0980)
white noise, no photograph                    +0.1466
1/f^2 noise, no photograph                    +0.1408
gaussian blobs, no photograph                 +0.1167
nine real photographs                         +0.1428
```

My pre-registered bar was a spread below 0.02 dex across all five arms. The
spread is **0.0299 — the bar FAILED**, and I report it failed. The failure is
carried entirely by the artificial blob field, which is band-limited and has
almost no power in the scoring band; across the four arms with realistic spectra
the spread is **0.0058 dex**.

The substantive reading survives the failed bar. **A closed form with no image
at all lands within 0.0036 dex of nine photographs — the photographs move the
answer by 2.5%.** Fact 1420's headline is, to 97.5%, a restatement of the two
kernels' transfer functions over two fixed bands. It could have been computed
from the coefficients with no camera, no capture and no stack.

That reframes the provenance question in §10 rather than answering it. The arms
having no sidecar does not make +0.1343 *wrong* — but it does mean the figure is
a **kernel datasheet number, not a corpus measurement**, and it cannot be
evidence about what any render gains. What the shipped pipeline actually
delivers is §3.2's **+0.0830**: the datasheet figure overstates delivery by
**72%**.

Edge density (`k11_density.py`, after repairing a first attempt that read
0.0000 on seven of nine — another dead instrument, cf. §5) varies **9.6x** across
the nine, from 0.00441 on tweezers to 0.04225 on leaf-2, while the gain varies
**0.57%**. The rank correlation is positive (+0.77) but the amplitude it
explains is 0.0008 dex. Edge density does not drive this number.

## 13. Ringing where `n_eff` is small -- the orchestrator's stated weakest point

Section 5's anti-ringing result rests on a **mean-field** argument: mean `n_eff`
is 55.3, so each pixel averages many frames at many sub-pixel phases and
phase-dependent ringing cancels. **That argument has no force where `n_eff` = 1,
and `n_eff == 1` is 38.77% of quads.** The objection is well-posed and I set out
to confirm it. Three corrections came out of it, one of them to me.

Everything below is on the **plane grid**, 3516x2344, which is both the merge's
native output grid and the `n_eff` map's grid -- 1:1, so no resampling of mine
enters the analysis. Binary rebuilt at `93f10a5` because `--n-eff-map`
(`8e5eb6e`) is **not** an ancestor of the `e924229` I measured at first. Control:
the rebuilt binary reproduces `mean n_eff` **55.321 / 53.674** exactly, so 69
commits have not moved the gate under my earlier numbers.

### 13.1 The number the objection rests on was retired by its own author

`M95-kernel.md` section 22.4 is titled *"The 9.902x ringing figure is stale, and
it is still being quoted"*, and P95 re-derives it: **1.78x**, not 9.902x, with
the note that *"the 9.9x figure reproduces at 9.06x only on an ungated
population that is 99.87% noise"*. My own positive control, on real pixels at a
half-pixel phase, reads **1.793x**. Two routes, one retired number.

**This matters beyond my brief.** My instructions, and
`docs/research/ORCH-kernel-decision.md:49`, both still cite 9.902x as the live
threat. It has not been the live threat since M95 corrected it.

### 13.2 My own power bar failed, and it failed for that reason

I pre-registered "overshoot ratio > 2.0x or the census is a dead instrument".
It read **1.793x. The bar FAILED**, and I report it failed. It failed because I
set it from 9.902x -- a number that no longer exists -- so the bar demanded more
signal than physics supplies. The instrument recovers 1.793x against a true
value of 1.78x; it is not dead, my calibration was.

### 13.3 Low `n_eff` is where the EDGES are, not where they aren't

The brief carries M111's finding that `n_eff` collapses in **flat** regions. On
`bee-3-cpl` at gate 4 the association runs the other way:

| stratum | % of quads | median 5x5 range | median grad |
| --- | --- | --- | --- |
| `n_eff == 1` | 38.77% | **1654 DN** | 269.6 |
| 2 | 21.42% | 989 DN | 165.4 |
| 9-16 | 2.75% | 323 DN | 63.5 |
| 129+ | 17.88% | **46 DN** | 9.3 |

**36x more local contrast in the `n_eff == 1` stratum than in the flattest one.**
So the census has full power exactly where the objection lives -- and the
objection deserved the test it got.

### 13.4 The confound-free measurement

K13's first pass was contaminated and its own table showed it: merged
**catmull-rom** overshot the nearest arm's envelope by 26.71% where a single
coherent catmull-rom resample of the same content overshoots by 12.83%. A kernel
cannot ring twice as hard as itself -- that excursion is the three arms
**electing different frames**, not interpolating differently.

So I removed the confound instead of modelling it: restrict to quads where
`idx_cr == idx_l3 == idx_nn` **and** `n_eff == 1` in all three. Every arm then
folded exactly one frame, the same frame, the same warp; the only remaining
difference is the kernel. That is **31.61% of all quads (2 605 077)**.

| population | n | cr p99.9 | l3 p99.9 | ratio |
| --- | --- | --- | --- | --- |
| clean stratum, all pixels | 2 605 077 | 58.64% | 67.03% | **1.143** |
| clean stratum, edge pixels | 512 281 | 22.25% | 26.83% | **1.206** |
| clean stratum, top 1% gradient | 58 260 | 9.39% | 13.62% | **1.450** |
| ceiling: one resample, phase-averaged | -- | 14.76% | 21.04% | 1.425 |

**Survival of the excess at `n_eff` == 1: 73.1%.** So the answer to the question
as asked is **yes, ringing is there at low `n_eff`, and section 5's "1.00x, does
not survive the merge" was too strong.** Section 5 used a blunter statistic
(extrema census) over unrestricted ROIs, which diluted an edge-only effect.

**But the ratio does not climb toward 9.9x. It climbs to 1.21x, and the ceiling
it is climbing toward is 1.43x.**

### 13.5 What 1.21x is worth in levels

An averaged edge response over **32 115** clean-stratum profiles, sign-aligned
and normalised to local amplitude:

```
offset px   nearest   catmull-rom   lanczos3
   -2.0     -0.4243     -0.4201     -0.4267   <- deepest
```

The **-42% is the hair itself** -- it is there in the un-interpolated `nearest`
arm, which cannot ring. The kernel-attributable part is the difference:

- lanczos3 vs catmull-rom: **0.655% of edge amplitude = 1.67 / 255 levels**
- lanczos3 vs **un-interpolated nearest**: **0.24% = 0.6 / 255 levels**
- overshoot on the bright side: **+0.041% vs +0.042%** -- no difference at all

M110 reached **<= 1.47/255** end-to-end by a different route. Two uncorrelated
instruments, 1.47 and 1.67 levels.

And the sign test that settles it: lanczos3 sits **closer to the un-interpolated
reference than catmull-rom does** (p99.9 |l3-nn| **45.61/255** against |cr-nn|
**51.70/255**). A kernel that rings moves *away* from the un-resampled truth.

### 13.6 By eye, at the worst locations the data has

Crops at the densest clusters of (clean stratum AND top-1% gradient) --
`C:\dev\strehl-out\M113\view3\`, all three arms on one intensity scale.
These are hair silhouettes on a bright thorax: the adversarial case. Catmull-rom
is visibly the softest of the three; lanczos3 recovers hairs it merges; **no
bright fringe hugs any dark hair in either arm.** Amplified 24x, the `l3 - cr`
residual is a **single-signed ridge centred on each hair** -- a sharpness
difference -- not the bipolar lobe a ringing artefact makes, and `l3 - nn` is
not visibly stronger than `cr - nn`.

### 13.7 A mechanism I proposed and then falsified

I hypothesised that at `n_eff` = 1 the anti-ringing work is done by **spatial**
phase diversity: neighbouring quads electing different frames, so lobes never
line up. **Measured, and it is false.** Within the clean stratum, horizontally
adjacent quads elect a different frame **0.09%** of the time. There is no
decoherence mechanism. The correct explanation is duller: the single-frame
ringing is 1.4-1.8x, not 9.9x, and 73% of a small number is still small.

### 13.8 What this does not license

**Not an `n_eff`-dependent kernel.** The `n_eff` dependence is real but weak
(1.02x at high `n_eff` to 1.21x at `n_eff` = 1) and the residual it governs is
under two display levels. Switching kernels per pixel would add a spatial
discontinuity worth more than the artefact it removes.

## 12. Facts and disciplines for the orchestrator

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
6. **CORRECTED, see section 13 -- this fact as originally written was too strong.**
   M95's 9.902x ringing figure does not survive the merge:
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
21. **MEASURED.** Fact 1420's arms have **no sidecar, no frame set and no
    `stack-digest`**. `x3_kernel.py` runs on `single-noalign.tif` — one
    unaligned frame — with sub-pixel phases applied in NumPy. The orchestrator's
    question "which solve were they measured on" has the answer "none".
22. **MEASURED.** The "corrected" **+0.1160**, which `M95-dose.md` P88 presents
    as measured "on the real warps" and which `align.rs:2752` quotes in its own
    doc-comment, was measured on the **8-frame, reference-4 quarantined sidecar
    `165a1ff35968c615`** — the same sidecar M112 refuted under the 9.4x
    denominator. `y2_combined.json` records `n_placed = 8` and the quarantine
    path. **This corrects fact 20 of my own previous report**, which recommended
    +0.1160 as the sound replacement figure. It is not one.
23. **MEASURED.** Across M112's nine stacks the synthetic kernel gain is
    **+0.1428 dex, sd 0.0002, range 0.0008** — **0.4%** of the spread of the
    coverage fix over the same nine (0.1846). By the orchestrator's own
    discriminator the gain is **not a ringing artefact**, which agrees with the
    extrema census (0.9924x / 1.0039x) and with the crops.
24. **MEASURED.** That instrument is **97.5% image-blind**. A closed form over a
    flat power spectrum, with no image at all, reads **+0.1464** against
    **+0.1428** for nine photographs; white noise reads +0.1466. Fact 1420's
    headline is a kernel datasheet number, not a corpus measurement.
25. **MEASURED.** Edge density varies **9.6x** across the nine captures
    (0.00441–0.04225) while the gain varies **0.57%**.
26. **DISCIPLINE.** **A correction needs its own provenance check.** M95's
    +0.1160 was published as the fix for +0.1343 and inherits the same defect
    class M112 found beneath the denominator. Fixing a number's arithmetic does
    not fix the stack it was measured on.
27. **DISCIPLINE.** When independent subjects agree to four decimal places,
    **that is the finding, and it is usually that the instrument cannot see
    them.** Run the closed form with no image; if it reproduces the measurement,
    the measurement was never about the data. Pre-register the bar and report it
    failed when it fails — mine did, on an arm I chose badly.
28. **MEASURED.** **Fact 1374's 9.902x was retired by its own author.**
    `M95-kernel.md` section 22.4 and P95 give **1.78x** on a clean step and
    record that 9.9x "reproduces at 9.06x only on an ungated population that is
    99.87% noise". My independent positive control on real pixels reads
    **1.793x**. My brief and `ORCH-kernel-decision.md:49` both still cite 9.902x.
29. **MEASURED.** On `bee-3-cpl` at gate 4, **low `n_eff` is where the detail
    is**: median 5x5 range **1654 DN** at `n_eff == 1` against **46 DN** at
    `n_eff >= 129`, a 36x difference. The brief's premise that low `n_eff` sits
    in flat regions does not hold on this stack.
30. **MEASURED, AND IT CORRECTS FACT 1465/1466.** Ringing **does** survive at
    `n_eff` = 1. In the confound-free stratum (same elected frame and
    `n_eff == 1` in all three arms, **31.61%** of quads) lanczos3 overshoots
    catmull-rom by **1.143x** overall, **1.206x** at edges, **1.450x** at the
    sharpest 1% -- **73.1%** of the single-resample excess. "1.00x, does not
    survive the merge" was measured with a blunter statistic over unrestricted
    ROIs and was too strong.
31. **MEASURED.** The ceiling it climbs toward is **1.425x**, not 9.9x. The
    orchestrator's predicted climb happens; it stops at 1.2-1.45x.
32. **MEASURED.** In display levels the whole effect is **1.67/255** (lanczos3
    vs catmull-rom) and **0.6/255** against the un-interpolated `nearest` arm,
    over 32 115 averaged edge profiles. M110's independent end-to-end figure is
    **<= 1.47/255**.
33. **MEASURED.** Lanczos3 sits **closer to the un-interpolated reference** than
    catmull-rom does (p99.9 |l3-nn| **45.61/255** vs |cr-nn| **51.70/255**). A
    ringing kernel moves away from the un-resampled truth, not toward it.
34. **MEASURED, MY OWN HYPOTHESIS FALSIFIED.** Spatial election diversity is
    **not** the anti-ringing mechanism at `n_eff` = 1: adjacent quads elect a
    different frame **0.09%** of the time.
35. **DISCIPLINE.** **Calibrate a power bar against a number you have checked is
    still current.** My pre-registered bar failed at 1.793x because I set it
    from 9.902x, which had already been retired. A bar built on a stale figure
    fails honest instruments.
36. **RISK.** An `n_eff`-dependent kernel is **not** licensed by this. The
    dependence is 1.02x to 1.21x and governs under two display levels; a
    per-pixel kernel switch would introduce a spatial discontinuity worth more
    than the artefact it removes.
