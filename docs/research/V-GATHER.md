# V-GATHER — the chroma cost is not the demosaic, it is a stale noise gate

*Lane V-GATHER, verification. Every number below was produced by code in
`experiments/V-GATHER/` (commits `03b8d36e`, `c0cb236c`) and is quoted from that
lane's own runs. **This file was written by ORCH from V-GATHER's reported
findings**, because that lane operates under a constraint that forbids it writing
findings to files; the scripts are its own, this prose is not. Anything here that
is wrong is mine to have transcribed wrong, and the scripts are the arbiter.*

---

## 0. The verdict, first

I sent this lane to settle whether a measured chroma excess in flat regions —
high-pass R−B up **+25.2% to +48.6%** after the full-resolution gather flip — was
noise **restored** (always present, previously suppressed by a Catmull-Rom
low-pass at double pitch) or noise **created** by demosaicing twice. Those have
opposite implications: the first is an honest price, the second is a defect in
the shipping path.

**Neither. The double demosaic is exonerated and the excess is noise the merge
stopped averaging away.**

That distinction is not a technicality. The fix for a demosaic artifact is in the
demosaic; the fix for this is in the gate, and I had an implementer working the
wrong file when this landed.

---

## 1. The double demosaic is exonerated, three independent ways

**(a) It is an exact no-op at zero shift — predicted from the code, then
measured.** At identity the gather samples `2.0*T(px + dx*0.5, py + dy*0.5)`,
which reduces to `2px + dx`, an **integer**. Catmull-Rom is interpolating, and
Malvar returns `known` at a site's own channel, so the composition is the
identity on the sample grid rather than approximately so.

```
C3 NULL (identity warp) : OLD max|d| = 0.000e+00   NEW max|d| = 0.000e+00
   -> the DOUBLE DEMOSAIC alone is a no-op; PASS
```

**(b) A tap-for-tap ported simulation reproduces the luma excess and refuses to
reproduce the chroma one.** Malvar stencils ported from `demosaic.rs:161-217`,
Catmull-Rom from `restore.rs`, both gather orders from `align_cmd.rs`:

| transform | luma HP new/old | chroma HP new/old | chroma new/NOGATHER |
|---|---:|---:|---:|
| pure shift .5,.5 | 1.864 | 1.029 | 0.670 |
| pure shift .27,.61 | 1.279 | 0.799 | 0.598 |
| rot 0.05 deg | 1.156 | 1.018 | 0.827 |
| rot 0.15 deg + scale | 1.218 | 0.914 | 0.720 |

Luma **×1.16–1.86** against the measured **×1.267–1.870** — reproduced. Chroma
**0.80–1.03** against a measured **+25.2% to +48.6%** — not reproduced, and
always *below* the no-resample ceiling.

**(c) On real pixels, the gather REDUCES chroma noise.** A `--gate 0` render
(elected frame, no averaging, no band-power weighting) isolates the gather:

| f | `foam` merge | `foam` g0 | `couch` merge | `couch` g0 |
|---:|---:|---:|---:|---:|
| 0.0938 | 1.455 | 0.836 | 1.547 | 0.742 |
| 0.1354 | 1.732 | 0.707 | 1.791 | 0.573 |
| 0.1771 | 1.937 | 0.652 | 1.920 | 0.498 |
| 0.2396 | 2.252 | 0.717 | 1.993 | 0.691 |

Up to **50% less** chroma noise from the gather alone. **The excess exists only
when the merge runs.**

---

## 2. What actually makes it, and the tool prints its own evidence

```
selection  : SOFT -- weight = (band power above the noise floor)^exponent
noise gate : 2.00 x the modelled band-noise power
band noise gain : 0.8898 0.0529 0.0101 0.0024 0.0006 0.0001 0.0000 0.0000   <- g0
band noise gain : 0.8898 0.0529 0.0101 0.0024 0.0006 0.0001 0.0000 0.0000   <- g1
```

**Byte-identical across the two arms.** The gather flip legitimately raises
per-frame band power. The modelled noise floor did not move with it. So
noise-dominated pixels now clear the gate, switch from **averaging (÷N) to
selecting (÷1)**, and carry their own noise into the output.

`averaged` — the fraction of pixels whose band power fell below the gate, so the
merge averaged instead of selecting, band 0:

| subject | plane | fullres | Δpp |
|---|---:|---:|---:|
| `coffee-bubbles` | 65.9 | 26.1 | **−39.8** |
| `foam` | 94.1 | 79.5 | −14.6 |
| `tweezers-cpl` | 86.6 | 72.3 | −14.3 |
| `bee-1-cpl` | 91.2 | 77.7 | −13.5 |
| `couch-fibers-cpl` | 95.6 | 82.7 | −12.9 |
| `flower-bud-alone-cpl` | 91.8 | 79.1 | −12.7 |
| `flat-on-ruler-cpl` | 62.5 | 50.5 | −12.0 |
| `wrapped-text-1` | 72.8 | 63.7 | −9.1 |
| `lavendar-cpl` | 95.1 | 86.3 | −8.8 |
| `wrapped-text-2` | 95.8 | 87.4 | −8.4 |
| **null (align refused)** | **58.1** | **58.1** | **0.0** |

**Ten of ten aligned subjects move; the null moves exactly zero.** The null is
the placebo and it is flat to the printed precision.

Noise power the merge removes, against an ideal unweighted mean of N frames:

| f | `foam` plane | `foam` fullres | `couch` plane | `couch` fullres |
|---:|---:|---:|---:|---:|
| 0.1354 | 13.06× | 4.10–5.33× | 10.29× | 3.30× |
| 0.1771 | 13.25× | 4.46× | 11.03× | **2.86×** |

**3.2–3.9× less noise power removed.**

---

## 3. It is broadband, not a maze

Structured chroma noise at a fixed spatial frequency is a labyrinth artifact and
is far more visible than its rms suggests, so it had to be ruled out rather than
assumed away. A **graded** planted diagonal-Nyquist chroma maze on `foam` drove
corner selectivity to **129×** (corner ratio `1.912 / 4.223 / 12.479 / 45.506 /
177.622` at 2/5/10/20/40 DN, axis fixed at 1.372). The real excess reads
selectivity **1.07**. It is broadband noise.

An apparent ratio peak at `f ≈ 0.37` is an artifact of the denominator: `foam`
g0 dips to a local minimum of `1.0988e6` there while g1 rises monotonically
through it. **A ratio peak is not a signal peak when only the denominator moved.**

---

## 4. Statistic D, commissioned in both directions

| arm | reading |
|---|---|
| null | `1.000000000` in every band |
| planted maze | rises monotonically |
| **planted improvement** | falls to **0.045** |
| amplitude ×2 | **×2.0000** |

The amplitude arm is the one that killed its predecessor: `overshoot_frac`
returned **×1.000000** there, because it thresholded a high-pass at 3σ *of that
same high-pass*, so amplitude cancelled algebraically. The exposure trap was
checked — all renders are `--linear-srgb --demosaic` with no `exposure :` line in
any log, so this is one gauge throughout.

---

## 5. The fix, and the fix that must not be attempted

**Derive the per-band noise floor from the actual warped frames rather than
carrying a constant.** Consumer is `merge_cmd.rs`.

**Do not patch it with a closed-form kernel ratio.** The transfer depends on
per-frame warp phase — the simulation in §1(b) spans **0.80–1.03 across four
transforms** — so any single analytic factor is fitted to one phase and wrong at
the others. That is the same shape as the scalar-transferred correction this
project already refuted once, and it would be refuted the same way.

---

## 6. Memory, in absolute terms — and a severity this lane downgraded on itself

`bee-3-cpl`, 299 frames, the deepest bracket the owner has shot,
`stack <DIR> --out <F> --srgb --auto-exposure`, peak private commit:

| run | arm | cache | peak MiB | free min |
|---|---|---|---:|---:|
| ship-g1 | fullres | own | **13,445** | 32.89 GiB |
| iso-g0 | plane | own | **14,435** | 6.32 GiB |
| iso-g1 | fullres | own | **12,489** | **0.00 GiB** |
| ship-g0 | plane | sidecar | 6,214 | 31.65 GiB |

**The peak is in ALIGNMENT and is arm-independent** (12.5–14.4 GiB).

- **Can the shipping default OOM on the deepest real stack? No.** ~21% of
  61.6 GB, **4.3–4.9× headroom**. Two runs drove free physical to **0.00 GiB**
  under contention from other lanes and *both completed* with valid
  197,801,296-byte output. The `0xC0000409` aborts seen elsewhere were
  contention, not depth.
- **Largest bracket that fits:** alignment slope 21–41 MiB/frame ⇒
  **~1,200–2,200 frames**. Treat **≥1,200** as the floor, not 2,200 as the
  answer — it is a two-point extrapolation over the alignment regime.
- **The 503.0 MiB/warp under-pricing is confirmed and exactly quantified.** Fold
  plateau 5,988 MiB (plane) against ~8,000 (fullres); Δ = 2.0 GiB =
  **4 × 503.0 MiB**. Fold peak is **1.51×** the printed `5.2 GB` plan.
- **The lane downgraded its own HIGH to MEDIUM.** Its 29% overrun came from the
  **estimator** path (`--gate 0`, 11 workers), where 11 × 503 MiB does set the
  peak. On the default's 4 workers it does not. A severity that survives only in
  the configuration it was measured in is not the severity of the default path.

---

## 7. Defects, as filed

| severity | defect | site |
|---|---|---|
| **HIGH** | stale noise gate on the now-default path | `merge_cmd.rs` (consumer) + the gather flip |
| MEDIUM | 503.0 MiB/warp priced in neither planner | `align_cmd.rs:1706,1718,1719,1720` |
| LOW | false doc: calls Malvar "a reference arm, not the shipping path", but `use_directional()` returns `false` when `STREHL_DEMOSAIC` is unset — **Malvar is the shipping default** | `demosaic.rs:390` |

---

## 8. Gaps, stated by the lane against itself

- **Backend confound.** `--gate 0` uses the estimator while merge renders use
  pyramid, so "the excess appears with the merge" is confounded with a backend
  swap. **The `averaged` diagnostic is not confounded** — it is measured inside
  the pyramid runs on both arms and its null moves exactly 0.0 — so the
  conclusion rests on that and not on the `--gate 0` table.
- **How much of the gate crossing is genuine detail rather than noise is
  unmeasured.** Some pixels *should* now be selected. The lane quantified the
  cost, not the net, and the fix must not assume the net is negative.
- **Timing was contaminated** by concurrent lanes (free physical 0.00–47 GiB
  across runs); only same-run paired stage times are safe. Both directions agree
  the fullres fold is faster (quiet 60.7 s vs 80.8 s; loaded 99.4 s vs 106.9 s).
- `STREHL_DEMOSAIC=directional` was not tested against any of this.
- **A self-caught error, disclosed:** the lane set the maze PASS bar at ×20
  arbitrarily and logged a FAIL at ×12.48 when the instrument was 9.1×
  corner-selective at that amplitude. Fixed with a graded curve. An arbitrary
  bar on an uncalibrated instrument produces a verdict about the bar.

---

## Section 105 resolved: the sharpness metric measured exposure, not sharpness

*Prose mine (ORCH). Every number and every script below is V-GATHER's; the
scripts are the arbiter, not this summary.*

`orch_sharp1to1.py` was the instrument standing between this project and any
statement about output quality. It was commissioned with three arms —
SELECTION 1.0000, DEFECT 0.1717, RECONSTRUCT 3.4867 — including the planted
*improvement* arm this project learned the hard way to require. Then five of
nine real subjects read **above** the RECONSTRUCT arm, and every sharpness
number in this project was barred from leaving the veiling log until that was
explained.

It is now explained. The instrument is unsound on real data, and the two
largest causes were both invisible to a commissioning that looked exemplary.

### The gauge: numerator and denominator were different image pipelines

The numerator is a strehl master rendered `--srgb --auto-exposure`, whose own
provenance string reads verbatim `TONE CURVE APPLIED -- DO NOT MEASURE
NUMERICALLY`. The denominator is `rawpy.postprocess(no_auto_bright=True)`.

The masters therefore carry a per-image auto-exposure gain the reference never
sees — measured across this corpus at **0.79× to 13.6×** — and the statistic is
*exactly* proportional to gain: a synthetic gain of 8.00 reads 8.0000. On real
pixels, one multiply in linear light before the sRGB curve:

| stops | gain | detail | vs +0.00 |
|---|---|---|---|
| −0.34 | 0.790 | 1219.57 | |
| 0.00 | 1.000 | 1345.40 | 1.000× |
| +1.50 | 2.828 | 1743.03 | 1.296× |
| +2.27 | 4.823 | 1928.31 | 1.433× |
| +3.76 | 13.548 | 2100.75 | 1.561× |

Same statistic, two gauges, and both subjects **sign-flip**:

| subject | exposure | original gauge | matched gauge | inflation |
|---|---|---|---|---|
| `coffee-bubbles` | −0.26 | 1.138 | **0.9269** | 1.23× |
| `wrapped-text-1` | +2.27 | 4.767 | **0.9314** | **5.12×** |

> **Every real-subject sharpness number this project produced was inflated by
> an amount chosen per image for aesthetic reasons.** That is worse than a
> wrong constant, because it is invisible and it varies by subject.

### The reference: a 1-in-30 subsample nothing had ever tested

`main()` samples `nsrc=10` frames — one in thirty on a 299-frame stack.
Thinning the reference **alone**, master untouched in every row:

| subject | keep | frames | sites | F med | inflation |
|---|---|---|---|---|---|
| `coffee-bubbles` | 1 | 19 | 67 | 0.9339 | 1.000× |
| `coffee-bubbles` | 2 | 10 | 45 | 1.1658 | 1.248× |
| `coffee-bubbles` | 4 | 5 | 18 | 1.4610 | 1.564× |
| `109MSDCF` | 1 | 22 | 18 | 0.8531 | 1.000× |
| `109MSDCF` | 4 | 6 | 12 | 1.0440 | 1.224× |
| `119MSDCF` | 1 | 33 | 53 | 0.8616 | 1.000× |
| `119MSDCF` | 6 | 6 | 39 | 1.1110 | 1.289× |

Thinning the reference moves the reading **across unity** with the master
untouched.

The reason no arm caught it is one line. `commission()` line 281 builds all
three arms from a single shared source set, `srcs = [blur(lat,k) for k in
(2,3,4,5)]`, and only `master` varies between arms.

> **A commissioning that perturbs only the numerator certifies half an
> instrument.** Three arms, one of them a planted improvement, and all three
> were blind to both dominant defects because the denominator never moved.

### "Above RECONSTRUCT" was never a meaningful phrase

With a stack whose best frame is genuinely soft (σ₀ = 1.0), a *perfect*
reconstruction reads **2.6242** — below the 3.4867 the arm reports under its own
box-blur plant.

> **A planted-improvement ceiling is a property of the plant, not of the
> physics.** "Above RECONSTRUCT" has no meaning without naming the plant.

### The physics-fixed arm that made the replacement trustworthy

`STREHL_ONLY_FRAME=k` (`merge_cmd.rs:1762`) renders exactly one source frame
with no election. **A render containing one frame cannot reconstruct**, so it
must read ≤ 1 whatever the statistic claims. Measured 0.245–1.024 across three
plants on eight subjects; the 1.0236 excursion is the replacement's residual
bias from per-site LO normalisation, reported rather than hidden.

### Two further defects, still live in the original file

- Masters are 1.01–1.19× larger than the raw frames while `register()` is pure
  integer translation with `SEARCH=48`. Scale-induced displacement reaches
  **559 px** at radius 3000 on `flower-inner-edge-cpl` — twelve times the search
  range — and was observable live as `site 2 UNREGISTERED, 10 of 10 source
  frames correlated below 0.50`.
- `best_site()` applies a *relative* floor (`SITE_SHARE=0.25`) after selection,
  so on low-texture subjects it returns background.

### Instruments retired by their own author

Statistic **E** used a HI/LO ratio as an argmax over the focus stack and
**selected defocus**: the worst-correlating frame won 15.2% of sites, 31.8% of
sites picked a stack end, and `M/F = 17.9` at low frequency, which defocus
cannot cause. Statistic **F**'s content anchor at 0.05–0.12 cyc/px is not
defocus-invariant at macro scale. **F2** fails its own arms on 3 of 10 subjects
— `flat-on-ruler-cpl` reads `PIXBLUR 2.5643`, meaning blurring the master
*raised* its score — and those subjects are refused rather than reported.

### The surviving statement

> On this corpus no defensible claim can be made that the strehl merge
> out-resolves its own sharpest input frame. On the three subjects where every
> source frame was rendered through the identical pipeline and the instrument
> passes its full commissioning, the master's detail-band energy at 0.15–0.30
> cyc/output px is bracketed between **0.85× and 1.32×** that of the sharpest
> single frame at the same site — and the bracket straddles unity on all three.

Subject partition, summing to 26: **3 MEASURED**, 2 arms-pass-but-reference-
subsampled (refused), 3 FAILED-ARM, 2 REFUSED thin data, 16 not rendered.

### The reframe, which is larger than the defects

> *"The merge's product is depth of field — the fraction of the field in focus
> simultaneously. A per-site peak-detail ratio prices only the resampling cost
> and none of the benefit, which is why a well-built instrument lands near 1.0.
> The defensible quality claim probably lives in a field-coverage statistic, not
> a sharpness ratio."*

At any single site, some individual frame is focused there **by definition**.
Asking whether the master beats it prices what the merge costs and none of what
it delivers. Nobody stacks 299 frames to win at one point; they stack to have
the whole subject sharp at once. A field-coverage statistic has the properties
this one lacked: any single frame scores its own depth of field, which is a
measured floor rather than a planted one; a perfect stacker scores 1.0, a
ceiling defined by the data, which removes the "above RECONSTRUCT" pathology
entirely because an oracle cannot be exceeded; and it is gauge-invariant by
construction when master and reference come from the same pipeline, killing the
auto-exposure defect at the root instead of correcting for it.

That statistic is being built now.

### The capture that turns the refusal into a number

**One repeat frame at an already-captured focus position, per stack.** It makes
read noise directly measurable, collapsing the `[F, F/(1−nb)]` bracket from
0.15–0.47 wide to a point. It is the cheapest capture change available and it is
the difference between a bracket and a figure.

## Print certification of the 26 delivered masters, on a gauge that supports the statistic

The shipped verdict was **17 PASS / 9 ACQUITTED / 0 FAIL**. Recomputed here it is
**17 PASS / 5 FAIL / 4 REFUSED**. Every one of the nine acquittals was wrong;
five are defects and four cannot be decided with the frames available.

### The three defects underneath the clean sheet

**1. The baseline was the worst frame.** The rule frozen at
`experiments/V-REVIEW/vr_baseline.json:7` is `max over registered source frames`.
`blotch` and `chroma` are low-is-good, so the max is the *worst* frame in the
bracket. Nine subjects were acquitted for being cleaner than the worst frame in
their own stack. Measured, the baseline choice is worth up to **7.5x**:
`couch-fibers-cpl` reads 2.64x against the worst frame and 6.96x against the
best.

**2. The ratio crossed two fitted tone curves.** `--srgb` fits black and white
points from *each image's own* luminance percentiles
(`crates/strehl-cli/src/image_out.rs:165-176`), so a 123-frame master and a
single source frame sit on two different content-derived nonlinear curves.
`blotch = band/mean` survives a linear gain and does not survive a fitted curve.
The documented defence — forcing `--exposure` — reaches no pixel: commanded 64x,
delivered gain `1.0000000`, **0 of 98,898,048 samples changed**. Both percentiles
are linear in the data, so the normalised result is invariant and no gain could
have survived it.

**3. The banding term is pinned at its own floor.** Found here, not previously
reported. `banding()` returns a median of differences between indices where
rounded luma changes, which is **bounded below by 1 by construction**. All 26
masters read `run 1.0px` against `BAND_RUN_MIN = 4.0`. The FAIL path requires
`run >= 4 AND step >= 4`; the conjunction can never fire, leaving `clip > 0.1%`
as the only live term, against a measured range of 0.0000–0.0691%.

> A gate term that cannot fire is not a lenient gate. It is an absent one
> wearing a threshold.

### Two questions, two gauges, on purpose

Re-running the old gate on `--linear-srgb` would have produced a number that
looked like a verdict and was not one, because the thresholds were calibrated on
tone-mapped output. The split avoids porting any threshold onto a gauge it was
not calibrated for:

- **Is it visible?** Absolute, on the delivered sRGB file. This is not defect 2
  repeated: defect 2 is a defect in *ratios* between two images on two curves. A
  single absolute reading on the file the printer receives is display-referred by
  definition. The thresholds keep their calibration **because the gauge did not
  move** — re-justification, not re-derivation, and stated as such.
- **Did the merge cause it?** A ratio on a matched `--linear-srgb --demosaic`
  pair, master against best source, same sealed binary, same run. The decision
  point is **1.0**, which needs no calibration on any gauge — only that numerator
  and denominator share one.

A print defect is **visible AND attributable**. Mottling the sources carry just
as strongly is the subject's own texture; it is the photograph.

`--linear-srgb` does not imply `--demosaic`: measured, `--linear-srgb` alone
gives 3516x2344 and with `--demosaic` 7032x4688. The lattice is read from every
file rather than inferred from flags, and any file carrying `Tone rendering` in
its ImageDescription is refused.

### The denominator elects defocus, and it took a positive control to see it

`best source frame` is an argmin of a low-is-good statistic. Blur removes
mid-scale band energy, so the smoothest frame over a focus stack can be simply
the least focused one. `certcommission.py` plants a blurred frame: it wins the
plain argmin at **every blur radius tested, down to r=1**. The selector is
focus-qualified as a result.

The first run of that arm read **ok** — falsely. A zero-padded box blur in the
harness had corrupted 60% of the planted frame's window, so the "blurred" frame
was not really blurred. The same bug made a repaired image score **359** against
a defect that scored 20.9. Both were caught by the planted-**improvement** arm,
not by inspection.

> A defect-only commissioning suite cannot separate a metric that is blind from
> one that is perverse, because both present as a pass. Only a planted
> improvement, required to score better, distinguishes them.

On real subjects the confound measures small — window focus spreads 1.1x while
global focus spreads 1.3–1.8x — because the window is the flattest region and
flat regions are focus-insensitive. That is a measurement with its own positive
control, not an assumption.

### The instrument's own worst defect, found and only partly fixed

`STREHL_ONLY_FRAME=k` emits a frame **in its own geometry**, not warped into the
reference grid. Measured by integer-shift cross-correlation with planted-shift
controls: drift of about **0.9 px per frame**, position-dependent in the way
focus breathing predicts. On a 299-frame bracket the last frame's content has
walked ~270 px across a 900 px window, so the pinned window was comparing
different scene content, worse the deeper the stack.

The signature was unmistakable once looked for: the ratio tracked **stack depth**
at rho **+0.764**, and on every deep stack the elected "best" frame was the last
one — the most drifted.

Registering each window by an integer-only shift did not fix it. The correlation
**rose to +0.867**, because the refusals it introduced are themselves
depth-dependent: where the window has left the sensor there is no data, deep
stacks lose more frames, and a minimum over fewer frames can only sit higher.
Gating on coverage — the candidate set must span 60% of the bracket and 60% of
the sampled frames — collapses the residual to **+0.310** over the 8 qualifying
subjects, and refuses the 4 it cannot support.

> Registration removed a contamination and revealed a second one wearing its
> shape. The number that mattered was not the ratio but its correlation with a
> quantity that should have been irrelevant to it.

### One suspicion raised and refuted

`blotch = band_dn / mean_dn`, and every PASS subject's window sits on a
near-saturated backdrop at ~62,000–63,400 DN while the flagged ones sit at
2,364–14,078. That is the shape of a statistic measuring its own denominator.
Measured across the 26: `band_dn` spans **390x** against `mean_dn`'s 26.8x, and
`log(blotch)` tracks `log(band_dn)` at rho **+0.947** (R^2 0.870) against
**-0.752** (R^2 0.584) for `log(mean_dn)`. The statistic is dominated by its
numerator and the suspicion is refused. One exception is named rather than
buried: `coffee-bubbles` has an unremarkable `band_dn` of 234 on a window at
3.6% of full scale, and its reading *is* a denominator effect.

### Commissioning

`certcommission.py`, **15/15**: an exact-unity null; an arithmetic bound (a
master that *is* one of its sources cannot beat the best of them); a three-rung
defect ladder; a blind band-stop repair and a four-rung graded repair, both
required to score *better*; a reference-only perturbation; and three
focus-selector arms including a live positive control asserting the plain argmin
**is** fooled, so the guard's pass is not vacuous.

`certnegctl.py`, **6/6** anchored controls, each hard-erroring if it fails to
land and each required to compile so a `SyntaxError` cannot masquerade as a
catch. Both protections fired during development: the `POP` arm's first anchor
produced a broken program and reported a false MISS, and the `PERMIT` anchor went
stale when the coverage branch was added, stopping the run with `MUTATION TARGET
NOT FOUND` rather than reporting four greens and a silent skip.

A driver defect was caught the same way: frames were counted as directory
entries, but three subjects carry an `.xmp` sidecar per raw, making the count
**exactly 2x** the bracket. `113MSDCF` read 126 for 63 real frames and would have
had six of twelve sample indices refused, drawing every survivor from the first
half of the stack. It surfaced only because an out-of-range frame index panics
rather than clamping.

### The partition, summing to 26

**17 PASS, 5 FAIL, 0 SUBJECT, 4 REFUSED, 0 NOT EXAMINED.**

| verdict | subjects |
| --- | --- |
| FAIL | `112MSDCF` 1.39x, `113MSDCF` 1.30x, `flat-on-ruler-cpl` 1.32x, `foam` 1.23x, `lead-1-cpl` 2.43x |
| REFUSED | `coffee-bubbles`, `couch-fibers-cpl`, `flower-inner-edge-cpl`, `leaf-2-cpl` |

`flower-inner-edge-cpl` is the sharpest refusal: **0 of 12** sampled frames
retained the master's measurement window at all.

Controls behaved: `109MSDCF` 0.96x, `119MSDCF` 0.81x and `bee-1-cpl` 0.87x all
read clean absolutely *and* below unity in ratio, including `bee-1-cpl` at 299
frames — a deep stack that is clean, which is the counterexample the depth
artifact could not survive.

### What is not certified, for all 26

This measures mid-scale luminance mottling, chroma mottling and clipping. It does
**not** measure halos or ringing at edges — the owner's loudest complaint —
sharpness, sensor dust (known, located, unfixed), or structure finer than 50 px
or coarser than 400 px. A PASS is silence on those, not a clean bill.

> "17 PASS" was read as a clean sheet while covering roughly a third of what
> makes a print unusable, and the third it covered was measured against the
> worst frame in the bracket on a gauge that could not carry the statistic.

### For the owner, in plain English

Nineteen of the twenty-six are fine to print as far as anything here can tell,
and that includes every bee, flower, pencil, ruler and text sheet. Five are not,
and they fail for a reason worth knowing: the stacked result is *mottlier than
the best single frame that went into it*, so the blotchiness is being
manufactured by the merge rather than photographed. Those five are **foam**,
which is much the worst and looks visibly clouded in its smooth areas;
**113MSDCF** and **112MSDCF**, which carry both luminance and colour mottling;
**flat-on-ruler-cpl**; and **lead-1-cpl**, whose problem is colour blotching
rather than brightness. Four more — **coffee-bubbles**, **couch-fibers-cpl**,
**flower-inner-edge-cpl** and **leaf-2-cpl** — are visibly mottled, but the frames
drift so far across these deep stacks that the region in question is not present
in most of the originals, so I cannot honestly say whether the merge caused it;
they need re-checking, not shipping. And one caution that applies to all
twenty-six: none of this looks at halos around edges, at sharpness, or at dust,
so a pass here means "not blotchy", not "print-ready".

---

## Part 11 — the three blind axes

My previous report closed with the sentence ORCH sent back to me:

> Nothing here measures halos, sharpness, or dust; a PASS is silence on those,
> covering roughly a third of what ruins a print.

This part closes that gap. It adds a rim axis, a sharpness axis and a dust axis
to the certificate, each built to the standard the blotch axis was held to: a
planted defect *and* a planted improvement, a demonstrated ability to FAIL, and
a partition that sums to the seal census.

It also retracts two pieces of my own committed work. Both were found by
controls rather than by reading, which is the argument for the controls.

### 11.1 Retraction: the registration sign was inverted

`certmeasure.py` registers a source frame against the master by integer FFT
cross-correlation before comparing windows. The estimator was commissioned and
its sign is not in doubt: `est_shift(a, roll(a, k))` returns `-k`, and the
control at `certmeasure.py:246` asserts exactly that.

The consuming code then wrote `ab = (y + dy, x + dx)`. Since the estimator
returns the negated displacement, **every window was displaced away from the
matching content by twice the drift.**

`signcheck.py` settles it without appeal to the estimator's docstring. It plants
a known `(23, -17)` displacement and asks which candidate window actually
matches the content:

```
plant (dy,dx) = (23,-17)
  y - dy  wins 8 of 8 sites   residual 0.0 DN
  y + dy          0 of 8      residual 339 - 1648 DN
```

The fix is one line, applied inside `window_shift` so that all call sites are
correct as written. `signcheck.py` is kept as a standing regression control.

**What the defect cost, and what it hid.** With registration corrected, the
windows land on the content:

| subject | usable windows before | after |
| --- | ---: | ---: |
| `flower-inner-edge-cpl` | 0 of 12 | 12 of 12 |
| `couch-fibers-cpl` | 5 of 12 | 9 of 12 |

The four subjects the previous certificate REFUSED for insufficient coverage
were refused **because of this defect**, not because the data could not support
a verdict. All four now resolve, and all four resolve to FAIL. The retracted
data is preserved at `cert-wrongsign.json` rather than deleted, because a
retraction that erases its own evidence leaves the next reader unable to check
the correction.

This also supplies the missing explanation for a result I reported earlier and
could not account for: adding registration made the depth confound *worse*
(rho +0.764 to +0.867). It did, because the registration was pushing windows
off the content by an amount proportional to the drift, and the drift is itself
depth-dependent.

**Independent corroboration.** With the sign corrected, `coffee-bubbles` reads
**1.428x** the best source frame. V-NEVERWORSE, a different lane using a
different instrument, convicted the same subject at **1.4501x**. Two
independently written instruments agreeing to within 1.5% on a subject that my
own certificate had previously declined to score is the strongest evidence in
this report that the merge manufactures mid-scale structure.

### 11.2 Retraction: a NaN reached the data

`certmeasure.py` bounds-checked the blotch window against the frame and did not
bounds-check the chroma window four lines later. When the chroma window
registered off the frame the slice was empty, and `chroma` came back `NaN`. One
such value reached `cert.json`, at `bee-2-cpl/sources[11]/chroma`.

It did not change a verdict, because the blotch ratio does not consume chroma.
That is luck, not design. **`NaN` compares False against every relational
operator**, so a missing measurement flowing into `if x > threshold` produces a
PASS. The failure mode is identical to the one this whole certificate exists to
prevent: an absence reading as a clean result.

Two repairs, because one of them is not enough:

1. `certmeasure.py` now applies the same bounds check to the chroma window, and
   **refuses to write any non-finite measurement at all**. Note that passing
   `at_chroma=None` would *not* have been the repair: `measure()` falls back to
   `pick_window()`, which would have silently measured a different region of the
   source than the master window it is compared against.
2. Every verdict function now refuses a non-finite statistic.

The second is commissioned by `nanguard.py` with both arms, because the first
arm alone proves nothing:

```
with the guard in place
  rim    NaN   -> REFUSED
  sharp  NaN   -> REFUSED
  dust   NaN   -> REFUSED

with the guard removed -- the same records must become PASS
  rim    NaN   -> PASS: the guard was load-bearing
  sharp  NaN   -> PASS: the guard was load-bearing
  dust   NaN   -> PASS: the guard was load-bearing
```

Without the guard, a NaN reads as a clean print on all three new axes. The
hazard was real and is now closed at both ends.

### 11.3 The rim axis — halos

**Instrument.** Overshoot in a band adjacent to a high-contrast occluding edge,
measured as a fraction of the edge step. I did not write a new one. The v3 rim
instrument is inadmissible — V-HEADTOHEAD2 measured it reading **+14.85% on a
rim-free image** — so `rimaxis.py` imports `V-H2H2-RIMCLIP/rimv6.py` unmodified
and adds only the subject-level policy around it.

**The floor is measured per subject, not assumed.** The first smoke test read
**+5.014%** on `foam` against a *smoothed, rim-free* control image. The
instrument was reporting a large halo on an image that has no halo in it. The
cause was mine: I had hardcoded the flatness cut at 0.10, where `rimv6` sweeps
it. `select_for()` now sweeps `rimv6.FLAT_CANDIDATES` and picks the cut that
minimises the control's departure from its structural null, and **refuses any
subject whose floor still exceeds 2%**. `foam` refuses honestly rather than
reporting a halo that is not there.

**The threshold is derived, not typed.** `RIM_MAX` was initially typed at 3.0%,
and the FIRE arm of the commissioning caught that **no planted rim ever reached
it** — the inert-threshold mode, the same defect I had convicted `banding()` of.
It is now *derived*: `RIM_MAX = FLOOR_MAX = 0.02`. An axis may not claim to
resolve an excursion smaller than the largest floor it tolerates.

**Commissioning: 11 arms, 11 pass.** FLOOR, BOUND, LADDER, SENSITIVE, FIRE,
NOTALWAYS, REPAIR, RESTORE, BLIND-GAIN, BLIND-OFF, ISOLATION. Two of them found
defects in the axis. FIRE found the inert threshold above. FLOOR found that my
own floor arm was **tautological** — `score(ref)` subtracted the floor measured
on `ref` itself and therefore returned `+0.0000%` by construction, a green that
could not have been anything else. It is re-anchored on the raw residual.

**The confound, and its refutation.** The largest rim readings landed on the
subjects with the fewest usable edges: `rho(corrected, n_sel) = -0.716`. That is
exactly the shape of a small-sample artifact, so I tested it rather than
arguing about it. `rimsubsample.py` draws random subsets of a *single subject's
own* edges, holding subject type fixed and varying only n:

```
119MSDCF    n=4572  ->  -1.750%
119MSDCF    n=  72  ->  -1.747%
worst drift over all subjects, n=72:  +1.315 points
```

Sample size alone cannot manufacture +37%. But `P(reading > +5%) = 33%` at
n=72, so the FAIL conjunction requires **both** the point estimate and the 95%
bootstrap lower bound to clear the threshold, plus a measured `+1.5` point
allowance for subjects under 200 edges.

**What this axis cannot see.** It speaks only to edges isolated enough to
plateau within 7 px. That fraction is **12% to 72%** depending on subject, and
it is printed per subject in the certificate. On `wrapped-text-2` the axis
speaks to 12% of the high-contrast features present. An axis that can see a
quarter of the edges must say so, and it does.

### 11.4 The sharpness axis

**Instrument.** Not a comparison against another render. Each site is compared
against **the best any input frame achieves at that location** — the per-site
focus ceiling. The statistic is `band = std(gauss(1.0) - gauss(2.5)) / mean`,
which is invariant to gain; the 1.0-2.5 octave was chosen because it excludes
photon noise, measured: injecting sigma = 60 DN of noise moves it by 0.03%.

Four successive defects, each caught by a control rather than by inspection:

1. **`MIN_CONF = 6.0` was typed** and refused 16 of 16 sites on a subject whose
   registration was demonstrably working. `confderive.py` then asked whether the
   confidence statistic can gate *at all*: RECOVERABLE sites median **3.20**,
   UNLOCALISABLE sites median **3.21**. It does not separate, so it cannot be a
   gate. Replaced with a direct per-site planted-shift recovery test.
2. Diagnosing that produced the **registration sign defect** in section 11.1.
3. **`bee-1-cpl` read a -317.8% deficit** — the master four times "sharper" than
   its own ceiling, which is impossible and therefore an instrument fault. The
   ceiling had been built from a set of defocused frames. Adding an interior
   local-maximum requirement (the focus peak must be *bracketed*) moved it to
   -100.9%, still wrong; windowed `memmap` reads plus an iterative refinement
   loop with an explicit convergence criterion fixed it. The subject now
   **REFUSES** rather than reporting a number.
4. The **SENSITIVE** arm demanded detection of a sigma = 0.3 blur, which is
   0.129% on this statistic — *below the axis's own measured 0.771% floor*. That
   arm was asking the instrument to resolve something it had already been shown
   unable to resolve. Replaced by a RESOLUTION arm that measures and reports the
   limit instead of asserting one.

`SHARP_MAX = 0.032`, derived as 4x the measured floor. **11 arms, 11 pass.**

**Every deficit is a lower bound.** The ceiling is a max over *sampled* frames,
and a max over a subsample can only sit at or below the true max. A larger
denominator makes the deficit look smaller. This is the same correction
V-NEVERWORSE applied to itself, and it points the same way: the softness
reported here is the least it can be.

### 11.5 The dust axis

**The detector, not the corrector.** The question is whether a shipped master
still carries warp-smeared trails from fixed-pattern sensor defects.

**The defect map had to be built twice, and the first empty result was not
believed.** Selecting on per-frame excess over 48 darks returned **0 sites**. An
absence is a statement about the query until the query's reach is measured, so
`dustreach.py` swept the threshold rather than accepting the zero: this sensor
has roughly **2-3 persistent hot photosites**, and the single-frame 99.99th
percentile of excess is 78 DN. Three sites cannot support a statistical
detector. A first pivot to flat fields drew frames sitting 171 DN above black,
where shot noise is 7.6% against a 2% depth cut, and **174 of 178 detections
were 1-3 px PRNU**. The working design selects on **mean excess across darks**,
where averaging suppresses noise by sqrt(48), with the cut derived at 8 robust
sigmas: **600 sites, 10.1 to 330.9 DN**.

**Commissioned with a power curve and an improvement arm.** Planted defects are
detected at 2000 DN and missed at 500 DN. The improvement arm — a master with
its defect sites *repaired* — drops the statistic from 3.41 to 0.94, confirming
the axis is not merely bounded below.

**Its power limit is stated, because it matters.** The strongest defect this
sensor has is 331 DN of mean excess in raw, and the axis becomes blind below
about 500 DN in master units. All 26 subjects read at or below **1.0203**
against a 1.05 threshold. That result should be read as *"no trails at or above
this axis's power limit"*, which is what the certificate prints, and not as
*"no dust"*.

### 11.6 Independent re-derivation of the rim finding

`rimaxis.py` imports `rimv6`. If `rimv6` has a systematic fault my axis inherits
it whole, **and so do all eleven of my commissioning arms**, because they
exercise the same code. Green arms around a shared instrument are not
independence. So I rewrote the measurement from scratch — `rimindep.py` shares
no code with `rimv6`, only the input file.

The first two attempts were both inadmissible, and saying how they failed is
more useful than the final number:

1. **n = 0 to 10 usable edges, and the null control also returned n = 0.** The
   dominance test compared each gradient against its *immediate* neighbours, but
   a real step is 2-3 px wide, so its own shoulders always disqualify it. A NaN
   control licenses no reading of the master whatsoever.
2. **The null read +8.61% against a master of +7.19%** — a blurred, rim-free
   image reading as ringing *more* than the picture. The cause was population
   mismatch: I was reselecting edges per arm, and blurring removes weak edges
   from the qualifying set (n = 6000 against n = 2788), so the difference carried
   the change in population rather than the change in rim. Sites are now selected
   once on the rim-free reference and every arm measures those same sites.

**Commissioned on synthetic edges before being pointed at any picture**, because
a real photograph has no known rim value to check against:

```
SHARP-CLEAN  (ideal step, no overshoot)  reads   +0.16%
RINGING      (same step, planted rim)    reads   +5.28%
separation                                       +5.12 points
```

A third defect surfaced only after this. The instrument passed on synthetic
edges yet read **+27%** on `119MSDCF`, which `rimv6` calls clean. On a synthetic
edge the plateau is flat; on a photograph the `t = +2..+7 px` band is full of
ordinary texture, and a maximum over a textured band is not an overshoot. Adding
an **isolation criterion** — the profile must actually settle before the
instrument is allowed to ask whether it overshot — is what reconciles them. That
is the same criterion V-HEADTOHEAD2 reports excluding about 75% of
high-contrast features, and this is independent confirmation that it is
load-bearing rather than conservative housekeeping.

**The two instruments then agree on the finding, having been built separately:**

| subject | `rimindep` (independent) | `rimaxis` (via `rimv6`) |
| --- | ---: | ---: |
| `wrapped-text-2` | **+9.27%** | **+10.93%** |
| `leaf-2-cpl` | +7.12% | +37.07% (n=112) |
| `lavendar-cpl` | +3.73% | +8.01% |
| `pencil-flatter-angle-cpl` | +2.97% (n=16) | clean |
| `119MSDCF` | **-0.19%** | **-1.75%** |

They agree on sign for every subject that either has enough edges to speak
about, they agree that `wrapped-text-2` is among the worst, and they agree that
`119MSDCF` is clean. The magnitudes diverge where the sample is small, which is
where they should diverge. **The rim finding is corroborated: the masters carry
real overshoot at occluding edges, and it is not an artifact of `rimv6`.**

### 11.7 Two axes, independently, convict the same subjects

The sharpness axis **refuses** `wrapped-text-1` and `wrapped-text-2`, and the
reason it refuses is itself a result:

```
wrapped-text-1   median deficit -28.3%  the master exceeds the best source frame
wrapped-text-2   median deficit -16.9%  the master exceeds the best source frame
```

A stack cannot be optically sharper than the sharpest frame that went into it.
When a band-energy statistic says it is, the extra band energy was manufactured
rather than photographed — and edge overshoot is precisely a mechanism that
manufactures mid-band energy.

These are the same two subjects the rim axis reads as the loudest overshoot, and
the rim reading was corroborated in 11.6 by an instrument sharing no code. The
refusal is not a gap in the sharpness axis; it is the sharpness axis detecting
the ringing from the other side. This is not universal — `109MSDCF` reads a
clean +5.5% deficit and `coffee-bubbles` +1.6% — so it is a property of those
subjects, not a bias in the instrument.

### 11.8 The warp kernel is refuted as the source of the overshoot

The obvious mechanism for edge overshoot is the resampler. Every frame is warped
by a per-frame similarity, and the shipped default is **catmull-rom, which has
negative lobes**. A kernel with negative lobes produces overshoot at a step by
construction. `nearest` has no negative lobes and **cannot ring**.

So the prediction is sharp and falsifiable: if the warp kernel makes the halos,
swapping to `nearest` must largely remove them.

`kerneltest.py` renders `wrapped-text-2` three ways from the same sealed binary,
on a linear gauge so no per-image tone fit can distort an edge profile, with
edge sites selected once and every arm measured at those same sites:

```
MINSTEP derived on this gauge: 0.0180 (99.5th pct of |grad|)
4218 edge sites, frozen, measured identically on every arm
null (blurred shipped arm): +3.93%   <- the instrument floor

  kernel        overshoot    corrected
  catmull-rom     +12.81%       +8.89%
  nearest         +13.77%       +9.85%
  lanczos3        +14.57%      +10.64%
```

**The overshoot does not fall. It rises.** The hypothesis predicted that
`nearest` would read near zero; it reads **+9.85%**, which is not near zero by
any reading of the instrument's +3.93% floor. The conclusion is robust to the
noise floor because the predicted effect is a collapse and the observed effect
is an increase.

**The warp resampler is not the source of the overshoot.** Whatever
manufactures it survives the removal of every negative lobe in the
interpolation, which points at the merge and the election rather than the
gather, and is consistent with V-NEVERWORSE's independent finding that the merge
manufactures mid-scale structure.

Two notes against over-reading this. `nearest` aliases badly, and a jagged edge
can present local maxima in the measurement band that are not ringing, so its
+9.85% should not be taken as a *quality* ranking. And this is one subject; the
refutation of the kernel hypothesis is what it establishes, not a kernel
recommendation.

A defect in this script is worth recording because it is the same one this
report keeps finding. Its first run selected **zero** edges — `MINSTEP` had been
calibrated on tone-mapped output and linear light puts the same visual edge at a
much lower normalised amplitude — **and it printed a conclusion anyway**, from
`n=0`. A threshold carried across a gauge change is the same defect as a ratio
carried across one. `MINSTEP` is now derived on the gauge in use, and every
empty arm hard-errors rather than reporting.

### 11.9 Negative controls on the certificate itself

The certificate is a program, and an unfalsified program is an unverified one.
`cert4negctl.py` plants defects that *should* change the printed partition and
requires the change to appear. Every mutation is anchored on a unique full line
and **hard-errors if the anchor does not land**, because a mutation that
silently fails to apply produces a green that means nothing.

```
  RIM-THRESH         CAUGHT   a rim threshold of 90% cannot be exceeded
  RIM-CI             CAUGHT   FAIL conjunction weakened to a disjunction
  RIM-SMALLN         CAUGHT   a 50-point small-sample allowance excuses everything
  SHARP-THRESH       CAUGHT   a 90% softness threshold cannot be exceeded
  DUST-THRESH        CAUGHT   a threshold below every measured ratio
  REFUSED-AS-PASS    CAUGHT   a refusal reported as a pass
  PARTITION-TRUNCATE CAUGHT   a verdict outside the declared partition
  PARTITION-GUARD    CONFIRMED load-bearing: with the check removed the same
                              truncation exits 0 undetected
restore verified by SHA256: all 4 mutated files byte-identical to their
pre-mutation contents
```

Four defects surfaced in the controls themselves, and they are worth naming
because each is a way a commissioning suite can lie:

1. **An anchor that did not land.** `REFUSED-AS-PASS` matched zero times. The
   harness hard-errored instead of reporting a green, which is the behaviour
   that makes the other seven readable.
2. **A mutation planted on a branch that never executes.** The first
   `PARTITION` arm mutated `dust_verdict`'s REFUSED return — but **no subject is
   REFUSED on the dust axis**, so the plant was inert and the arm reported
   MISSED against a certificate that was in fact guarded. An inert plant and a
   blind instrument produce the identical glyph.
3. **A guard commissioned by breaking the guard.** The same arm disabled the sum
   check while the partition was still correct, so there was nothing to catch. A
   guard is commissioned by breaking **the data it protects**, then shown to be
   load-bearing by removing it and watching the same break survive.
4. **A restore loop that reinstated a mutant.** Both paired edits target one
   file; the loop restored backups **in order**, putting the clean copy back
   first and the once-mutated copy back on top of it, twice leaving a mutation
   in the tree. Restores must unwind in reverse, and the restore is now verified
   by SHA256 against pre-mutation copies rather than by re-reading the output —
   an output check would have conflated "the harness corrupted the tree" with "a
   sweep advanced the data underneath it", and only the first is a defect.

### 11.10 What the sharpness axis found, and the mechanism the source already names

The sharpness axis asks a question with a physical answer: **is the shipped
master as sharp, at each location, as the best frame that went into it?** A
stack cannot be optically sharper than its sharpest input. The axis therefore
treats a *negative* deficit not as an excellent result but as a refusal — the
instrument saying it has not found the ceiling, or that something is wrong.

Of the subjects measured, **two returned a positive deficit and thirteen
refused**, and the refusals are overwhelmingly of one kind:

| subject | median deficit | renders spent on the ceiling |
| --- | ---: | ---: |
| `pencil-steep-angle-cpl` | **-96.4%** | 12 + 44 |
| `wrapped-text-1` | -28.3% | 12 + 43 |
| `leaf-2-cpl` | -24.1% | 12 + 30 |
| `foam` | -23.2% | 12 + 11 |
| `112MSDCF` | -17.0% | 12 + 18 |
| `wrapped-text-2` | -16.9% | 12 + 41 |
| `113MSDCF` | -16.4% | 12 + 15 |
| `lead-1-cpl` | -5.8% | 12 + 28 |
| `flat-on-ruler-cpl` | -5.6% | 12 + 24 |
| `109MSDCF` | **+5.5%** | 12 + 2 |
| `coffee-bubbles` | **+1.6%** | 12 + 3 |

These are not shallow searches. The refinement loop spent up to 44 additional
renders climbing the focus curve, and the excess survived. `pencil-steep-angle-cpl`
carries roughly **twice** the mid-band energy of the best frame that went into
it.

**This is on a sound gauge.** Both sides are rendered `--linear-srgb --demosaic`
by the sealed binary, the lattice is verified from the file, and
`certmeasure.read_rgb` refuses outright any file whose description carries a
tone stage. The statistic is a bandpass contrast normalised by local mean, so it
is invariant to a linear gain. This is not the two-gauge defect this report
convicted elsewhere.

**The mechanism is documented in this project's own source.** The merge is a
per-pixel election, and `crates/strehl-core/src/stack.rs` states the defect
plainly:

> argmax over N noisy frames systematically electing noise

with `pyramid.rs` adding that in such a region the merge "reliably selects the
frame whose noise happened to be largest". A per-pixel maximum over noisy
candidates is **biased upward by construction**, whether or not any real detail
exists at that pixel. The gate and the regularisation in `merge.rs` exist
precisely to suppress this. What these measurements say is that in the shipped
configuration **the suppression is incomplete**: the output carries more
mid-band energy than any input frame supplies at the same location.

I have not isolated that experimentally — the merge belongs to a build lane and
I am measuring output, not changing how it is made. What I can state is bounded
and measured: the excess is real, it is large, it survives 56 renders of ceiling
search, it is not a gauge artifact, it is **not** produced by the warp
resampler's negative lobes (11.8), and it coincides subject-for-subject with the
independently corroborated edge overshoot (11.6, 11.7).

**A caution that cuts against my own numbers.** The ceiling is a maximum over
*sampled* frames, so the true ceiling is at or above the measured one, and the
true excess is therefore at or below what is tabulated. The magnitudes above are
upper bounds on the excess. The *sign* is what the refusals rest on, and the
sign is not affected.

### 11.11 The four-axis certificate

```
               BLOTCH    RIM  SHARP   DUST
  PASS             17      9      2     26
  FAIL              8     13      1      0
  SUBJECT           1      0      0      0
  REFUSED           0      4     16      0
  NOT EXAMINED      0      0      7      0
  TOTAL            26     26     26     26

COMBINED -- a print is only as good as its worst axis
  clean on all four axes        1
  FAIL on at least one axis    17
  no FAIL, some axis silent     8
  no FAIL, source-attributed    0
  TOTAL                        26
```

Every column sums to the seal census independently, and the guard that enforces
that was commissioned by truncating the data it protects and shown load-bearing
by removing it (11.9). The seven NOT EXAMINED on the sharpness axis are honest
absence: those are 299-frame stacks whose ceiling search did not fit in the
time available. **They are counted, and they are not PASSes.**

**ORCH asked whether the PASS count would fall. It did.** Nine subjects change
verdict, all of them from clean to failing, and eight of the nine on the rim
axis the previous certificate could not see:

```
109MSDCF                 now FAIL on sharp
bee-1-cpl                now FAIL on rim
coffee-bean              now FAIL on rim
flat-on-ruler-cpl        now FAIL on rim
flowers-cpl              now FAIL on rim
lavendar-cpl             now FAIL on rim
pencil-steep-angle-cpl   now FAIL on rim
wrapped-text-1           now FAIL on rim
wrapped-text-2           now FAIL on rim
```

Combined with the four subjects that moved from REFUSED to FAIL on the blotch
axis once the registration sign was corrected (11.1), **the number of masters
clean on every axis the certificate can measure is one: `119MSDCF`.**

The earlier headline, "17 PASS / 9 ACQUITTED / 0 FAIL", came from a gate
comparing against the worst frame in the bracket, on a gauge that could not
carry the statistic, defended by a flag that reached no pixel, and blind to
halos, softness and dust. The corrected four-axis figure is **1 clean, 17
failing, 8 unexamined on at least one axis.**

### 11.12 What a PASS still does not cover

- **RIM** speaks only to edges isolated enough to plateau within 7 px. The
  isolated fraction runs from **12% to 72%** across subjects and is printed for
  each one. On `wrapped-text-2` the axis speaks to 12% of the high-contrast
  features present.
- **SHARP** resolves softness down to about blur sigma 0.6 and is silent below
  it. Every deficit is a lower bound. Sixteen subjects refused and seven were
  not examined, so this axis speaks to three of twenty-six.
- **DUST** detected planted defects at 2000 DN and missed them at 500 DN, while
  this sensor's worst site carries 331 DN of mean excess. Its 26 PASSes mean
  "no trails at or above this axis's power limit", not "no dust".
- **None of the four** measures colour accuracy, tonal rendering, composition or
  the print medium.

### 11.13 For the owner, in plain English

Of the twenty-six files, **one — `119MSDCF` — comes through every check I can
run without a mark against it.** Seventeen have something measurably wrong, and
the problems fall into two families.

The first you already know about, because it is the complaint you started with:
**halos.** Thirteen of the twenty-six show real bright overshoot hugging their
high-contrast edges, and I confirmed this with two instruments built separately
that share no code, so it is not an artifact of one measurement. The worst are
`leaf-2-cpl`, `coffee-bean`, `113MSDCF`, `flat-on-ruler-cpl`, `112MSDCF` and
both `wrapped-text` sheets. On a large print this reads as a thin bright fringe
outlining edges, and it is the thing that makes an image look processed.

The second is worse and it is new: **the stacker is inventing fine detail that
was never photographed.** On most subjects I checked, the finished file contains
*more* fine structure than the sharpest single frame that went into it — on
`pencil-steep-angle-cpl`, about twice as much. That is not possible optically. A
stack can at best keep what the best frame had. The extra comes from how the
merge picks a winner for each pixel: picking the highest of many noisy
measurements tends to pick the noisiest, and the project's own source code says
so in as many words. In a print this shows up as crunchy, slightly artificial
texture in areas that should be smooth, and as the mottling you can already see
in `foam`.

**Do not print `foam`, `112MSDCF`, `113MSDCF`, `couch-fibers-cpl`,
`flower-inner-edge-cpl`, `lead-1-cpl`, `leaf-2-cpl` or `coffee-bubbles`** — those
are mottled beyond the best frame that went into them, and several are also
haloed. **`119MSDCF` is safe to print.** The remainder sit in between: haloed but
not mottled, which may still be acceptable at smaller sizes, and you are the
right judge of that with a proof in your hand. What I would not do is call any
of this print-worthy on the strength of the earlier clean sheet, because that
sheet was produced by a gate that could not see either of the two problems above.

One honest limit: I could not finish the sharpness check on seven of the deepest
stacks, and I have counted them as unexamined rather than passed.
