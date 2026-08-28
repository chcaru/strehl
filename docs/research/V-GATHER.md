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


## Part 12 - the merge's selection law, made the independent variable

My previous report claimed the merge manufactures detail and supported it two
ways: `stack.rs:11` names the mechanism, and 13 of 19 masters exceed their own
focus ceiling. I also filed the gap against myself:

> merge attribution is mechanistic, not experimentally isolated.

An argument about code and an observation about pixels are not an experiment.
Neither varies the merge. This part varies it.

**Design.** `--pyramid-sharpen 1.0` disables the per-octave ramp, so
`--pyramid-exponent e` sets one flat selection exponent at every band. I
rendered `e = 1, 2, 4, 8, 16` plus the shipping default on nine subjects - the
six worst by measured ceiling excess, and three that the sharpness axis had
placed *within* their ceiling as negative controls - and re-measured ceiling
excess on each with the same gauge, no threshold moved between arms.

**Prediction under test**, as ORCH stated it: ceiling excess rises
monotonically with the exponent and approaches zero at exponent 1. If excess is
flat across a 16x range, or large at exponent 1, the selection law is not the
mechanism.

**Verdict, in two parts, because the experiment gave two answers.**

1. **The selection law is confirmed as the dominant lever.** 9 of 9 subjects and
   89 of 92 individual sites rise monotonically with the exponent. The three
   negative controls are not inert - every one crosses above its ceiling as the
   exponent rises. `112MSDCF` swings from 10.8% *below* its ceiling to 16.9%
   *above* it on one knob, everything else frozen.
2. **It is not the only source, and this half refutes ORCH's prediction.** The
   prediction was that excess "should approach zero at exponent 1". On the two
   deep stacks it does not. I suspected my own under-sampled ceiling, said in
   advance what would settle it, and ran an **exhaustive every-frame ceiling**
   over all 299 frames. It absorbed **17.1%** of the residual and left
   **+36.2%** standing. By the criterion I set before seeing the number, the
   selection exponent does not account for the whole effect (12.9).

Both halves are load-bearing. The first is what a build lane can act on. The
second is an open mechanism this project has not yet identified, and I would
rather hand it over named than let the 9-of-9 result cover it.

### 12.1 A correction to the brief's stated rationale

ORCH's reason for expecting zero at exponent 1 was that "at exponent 1 the
weights are proportional to excess and the output is a convex combination of
the inputs - which cannot leave the hull."

**The premise does not hold, and I read it off the shipping binary rather than
off `crates/`, which is dirty under the build lane and would not describe the
pin.** `--pyramid-select soft` is a convex combination weighted by excess band
power *at every exponent*. The exponent sharpens the weights; it does not
switch the merge between convex and non-convex. Convexity therefore does not
separate the arms, and a convex combination of registered-and-warped frames is
not confined to the per-site hull of the *unwarped* inputs the ceiling is
measured on.

This weakens the a-priori argument for the prediction without settling the
prediction itself, which is empirical. The ladder then confirms its
monotonicity half and refutes its approach-zero half (12.9) - so the rationale
and the outcome are wrong in the same place, which is worth knowing. I record
it because a prediction resting on a false rationale is a coincidence until
someone checks, and the check is cheap.

### 12.2 Commissioning the gauge for amplitude, not for presence

ORCH required the gauge report a plant "at the right magnitude, not merely to
report *something*", with a planted improvement as well as a planted defect.
`lad_commission.py` fires 15 arms. All 15 pass.

The load-bearing arm is SCALE, because its prediction is *exact*. For
`band(a) = std(DoG(a)) / mean(a)` and `a' = m + k(a - m)`, the predicted excess
is algebraic, not approximate:

```
  k           predicted       measured      rel err
  0.5       -51.797736%    -51.797730%    9.88e-08
  0.8       -22.876377%    -22.876378%    4.47e-08
  1.0        -3.595471%     -3.595471%    0.00e+00
  1.25       20.505661%     20.505671%    4.99e-07
  2.0        92.809058%     92.809078%    2.20e-07
  [PASS] SCALE two-sided   improvement -51.798% < base -3.595% < defect +92.809%
```

INJECT adds an *independent* bandpass field, so the bands add in quadrature and
the prediction is a different formula, stated in advance. Measured correlation
between the plant and the master is `+0.0038`, confirming the independence the
quadrature assumes; worst relative error 4.5e-02.

Two physical arms bracket it. HALO plants an unsharp overshoot and must raise
the reading at every amplitude (`+2.12% / +10.77% / +25.38%`). BLUR is the
**planted improvement**: removing mid-band contrast must *lower* manufactured-
detail excess (`-5.81% / -18.86% / -43.66%`). A statistic whose error sign is
bounded below - one that can ignore a defect but never charge for an
improvement - passes defect-only commissioning trivially, and this project has
shipped exactly that failure before. BLUR is the arm that excludes it.

NANGUARD is not decoration. It confirms the unguarded value is `nan`, that
`nan > 0` is `False`, and that a missing measurement would therefore have read
as *within ceiling* - a silent PASS. The gauge returns `None` instead.

**The SCALE arm caught a real defect in me, and only SCALE could have.** Its
first run failed at every `k` except 1.0, by 2e-3 to 9e-3, on a relation I had
asserted was analytically exact. `lad_scalediag.py` showed the relation holds to
1.06e-07 in float32 and 0.00e+00 in float64: the gauge was right and my harness
was wrong. I had built the affine map around `mean(big)` over a 576 px margined
window while `band()` normalises by `mean(core)` over 512 px, so my normaliser
moved with `k` by exactly the 0.42% the two means differ by. An arm that had
only asserted "the number should go up" would have passed, and the bug would
have shipped *inside the instrument certifying the ladder*.

### 12.3 Potency, the null, and the licence to freeze the ceiling

Three gates before any interpretation (`lad_probe.py`):

| gate | result |
|---|---|
| **Potency** - are the arms actually different renders? | **98.18-99.07%** of 98,898,048 samples differ between arms. ORCH's known-potent reference for `--pyramid-exponent 4.0` is 90.98%. Not stale bytes. |
| **Null** - reproducibility floor | The same arm re-rendered is **byte-identical**, SHA256 `398B5E43..`. The floor is exactly 0, so any inter-arm difference is real. |
| **Ceiling invariance** | A *single source frame* rendered at exponent 1 and at 16 is **byte-identical**, SHA256 `DA1AB73C..`. |

The third is the licence for the whole design. With one frame the merge has
nothing to select between, so the exponent cannot reach the output; the ceiling
is therefore a property of the inputs and not of the arm. That lets me freeze
the sites *and* the ceiling and vary only the master - 5 renders per subject
instead of a full re-derivation per arm - and it forecloses the population-
mismatch failure that made an earlier rim instrument in this same lane read a
*blurred* image as ringing more than the master.

Provenance is captured per arm from the tool's own log line, which prints
`per-band exp : 1 1 1 1 1 1 1` when the ramp is disabled.

### 12.4 The ladder

Median ceiling excess. Positive means the master carries **more** mid-band
contrast than the best single input frame achieves at that site.

| subject | e1 | e2 | e4 | e8 | e16 | shipping |
|---|---:|---:|---:|---:|---:|---:|
| coffee-bubbles* | -20.70% | -10.21% | -4.67% | -1.46% | -4.10% | -1.62% |
| 109MSDCF* | -22.70% | -15.61% | -10.13% | -5.44% | +6.68% | -5.50% |
| 119MSDCF* | -22.14% | -12.95% | -5.66% | -1.25% | +344.72% | -1.32% |
| foam | -4.87% | +12.05% | +19.18% | +22.86% | +1204.28% | +23.24% |
| wrapped-text-1 | +0.77% | +15.78% | +23.86% | +27.08% | +1975.75% | +28.32% |
| leaf-2-cpl | -3.82% | +9.63% | +19.03% | +23.99% | +10.57% | +24.12% |
| flower-inner-edge-cpl | +28.78% | +49.84% | +61.16% | +65.15% | +2728.92% | +69.37% |
| pencil-steep-angle-cpl | +43.64% | +69.85% | +86.64% | +95.80% | +515.63% | +96.41% |
| 112MSDCF | -10.78% | +1.80% | +11.06% | +16.89% | +5.17% | +17.03% |

`*` = negative control.

**All nine rise monotonically `e1 < e2 < e4 < e8`.** One subject landing on that
ordering by chance is 1 in 24; nine independently is **P = 3.785e-13**. The
exponent is not inert.

The magnitude matters as much as the ordering. On `112MSDCF` the master goes
from **10.8% below** its ceiling to **16.9% above** it purely by turning one
knob, with the input frames, the sites and the gauge all frozen.

`wrapped-text-1` needs a caveat I will not let the table hide: at `+0.775%` it
is the one subject still nominally above ceiling at exponent 1, but that is
1/37th of its shipping excess and smaller than the ceiling's own measured
reproducibility floor of 2.38% (12.9). I would not defend it as a non-zero
residual.

Two subjects that were re-run in full as replication controls - `112MSDCF`
after a self-inflicted concurrency failure, and all nine in the per-site pass -
reproduced every previously measured median **exactly to six decimal places**.

### 12.5 The negative controls respond, which closes ORCH's second route to refutation

ORCH: *"A subject that was within ceiling and stays within ceiling at exponent
16 is a second, independent way for the mechanism to be wrong."*

None of the three stays within ceiling.

| control | shipping | e1 | e16 median | e16 max site |
|---|---:|---:|---:|---:|
| coffee-bubbles | -1.62% | -20.70% | -4.10% | **+315.53%** |
| 109MSDCF | -5.50% | -22.70% | **+6.68%** | +216.71% |
| 119MSDCF | -1.32% | -22.14% | **+344.72%** | +15620.13% |

Every one crosses above its own ceiling as the exponent rises. Their being
within ceiling at the shipping setting is a fact about how much selection
pressure that setting applies to *their* content, not evidence that the
mechanism is absent from them.

### 12.6 Per site

Medians can be produced by a few sites moving a lot. They were not.

**89 of 92 sites (96.7%) rise monotonically `e1 < e2 < e4 < e8`**, against 4.2%
expected by chance. The three exceptions are two sites in `coffee-bubbles` and
one in `foam`. Five of the nine subjects are 100% monotone at every site.

### 12.7 Exponent 16 is degenerate, and I am not counting it as evidence

e16 is *erratic*, not extreme in one direction: `+1975.75%` on `wrapped-text-1`
but `+5.17%` on `112MSDCF`, which is **below that subject's own e8**. I
excluded it from the monotonicity test in advance, and I want to be explicit
that this cuts against me - a degenerate arm is not evidence for a trend in
either direction, and including it would have made my own result look worse,
not better.

The registration audit flagged 15 sites, all in e16, with physically impossible
shifts like `(350, -356)`. Those sites read correlation confidence **2.09-3.56**
against **31-58** where the lock held: no peak at all, not a displacement. A
low-pass did not restore the lock, refuting the obvious "the coarse structure is
still shared" story.

The control that settles it is Pearson `r` of heavily blurred windows **at zero
shift, with no registration applied at all**:

| arm | min r | median r |
|---|---:|---:|
| e1..e8 (all subjects) | >= 0.83 | >= 0.9985 |
| e16 | **-0.61** | +0.10 to +0.93 |

The frozen windows are on the same content in every arm the shipping ladder
actually spans. e16's apparent displacement is genuine decorrelation of the
image content - a second signature of the same effect, not a measurement
defect. The shipping configuration runs 2..8, so nothing operational depends on
e16.

### 12.8 The shipping arm is a flat exponent 8, on this statistic

Read off the binary: exponent 2.00, ramp 1.4x/octave, per-band `2 3 4 5 8 8 8`,
gate 2.00, 7 bands plus a plain-mean base. This statistic lives in the fine
bands, where the ramp has saturated at 8.

Shipping minus flat-e8 across all nine subjects: **-0.162 to +4.213 pp**,
median +0.134 pp. The prediction holds, and it means the ladder's e8 arm is a
faithful stand-in for what ships.

### 12.9 The confound in my own headline number, and how far it goes

Seven of nine subjects fall to zero or below at exponent 1. Two do not:
`flower-inner-edge-cpl` (+28.8%) and `pencil-steep-angle-cpl` (+43.6%). **Those
two are the only 299-frame stacks in the set.** That is a suspicious
coincidence and I went after it rather than reporting the residual as merge
behaviour.

`sharpaxis.py` caps its ceiling search at 56 renders. A 299-frame stack is
therefore searched at **18.1% coverage** against **78.9%** for a 19-frame stack.
An under-sampled maximum is *too low*, and a ceiling that is too low inflates
excess. Across the nine subjects:

- Spearman(ceiling coverage, excess at e1) = **-0.8167**
- Spearman(n_raw, excess at e1) = **+0.9333**

That is the signature of my own sampling, not of the merge.

**The control.** `lad_ceiling.py` recomputes the ceiling **exhaustively, every
frame**, on the deep subject and on a shallow one as a control on the method
itself. The shallow result is in and it is the one that makes the deep result
interpretable:

```
119MSDCF (33 frames, exhaustive)   ceiling rose: median +0.00%  max +2.38%
  default  excess   sampled -1.322%  ->  exhaustive -2.329%
```

A maximum over more draws is larger in expectation even from pure noise, so a
ceiling that rose everywhere would have proved nothing. Here it rises by a
median of **zero**, and 5 of 8 sites do not move at all. The procedure is not
inflating the ceiling by construction.

That control also hands me a number I did not have. `119MSDCF` has 33 frames
against a search cap of 56, so its sampled ceiling was **already exhaustive** -
the two runs saw the same frames. Three of its eight sites nevertheless moved,
by up to **+2.38%**. That is not coverage; it is the ceiling statistic's own
run-to-run floor, consistent with the `STREHL_ONLY_FRAME` drift I filed earlier
in this lane. **No excess difference smaller than 2.4% should be read as
meaningful**, and I have applied that above to `wrapped-text-1`.

**The deep subject, and the answer to the question I set.**

```
pencil-steep-angle-cpl (299 frames, exhaustive)   ceiling rose: median +5.49%  max +9.60%
  e1       excess   sampled +43.644%  ->  exhaustive +36.164%
  e2                        +69.848%  ->             +61.003%
  e4                        +86.637%  ->             +76.917%
  e8                        +95.799%  ->             +85.602%
  default                   +96.409%  ->             +86.181%
```

The confound is **real**: the median ceiling rise of +5.49% is well above the
2.38% floor, so the deep stack's ceiling genuinely was under-sampled, exactly as
the rank correlations predicted. And it is **not large enough**. At exponent 1
the residual falls from +43.644% to +36.164% - the exhaustive search absorbs
**7.48 pp, or 17.1% of it. 82.9% survives.**

I stated the reading in advance and I am holding to it: *if the residual
survives an exhaustive ceiling, the selection law is not the only source.*
**It survives.**

Three things make the surviving +36.2% a conservative figure rather than an
inflated one, and I looked for biases in the other direction first:

- The ceiling is now a maximum over **every** input frame. No further sampling
  can raise it. It is not an estimate.
- The ceiling frames are rendered singly and are therefore **noisier** than a
  299-frame merge, and `band()` is a standard deviation, which counts noise.
  Single-frame noise inflates the ceiling and merge noise-averaging deflates the
  master. Both bias excess **downward**.
- The master's contributions are warped by a per-frame similarity and the
  ceiling frames are not; resampling blurs, which again raises the ceiling
  relative to the master and biases excess **downward**.

**What the residual might be, stated as an untested hypothesis and labelled as
one.** My gauge is a DoG at sigma 1.0-2.5, whose passband spans **more than one
pyramid band**. The merge selects per band, so adjacent bands at one site can be
drawn from *different* frames. Their reconstructed sum can exceed any single
frame's contrast inside my passband even where every individual band is a convex
combination. That mechanism is **exponent-independent**, which is the shape of a
residual that survives at exponent 1. It is a hypothesis. I have not tested it,
the obvious test is a DoG narrow enough to sit inside one pyramid band, and I am
naming it so the next lane does not have to rediscover it.

### 12.10 Defects I found in my own harness

Four, all found by controls rather than by reading, which is the argument for
the controls.

| # | defect | what caught it |
|---|---|---|
| 1 | The commissioning affine map normalised by `mean(big)` over a 576 px window while `band()` normalises by `mean(core)` over 512 px, so my planted amplitude moved with `k`. | **SCALE**, because it predicts an exact value. A "the number should go up" arm passes this bug and ships it inside the instrument. |
| 2 | Render-failure capture sliced the **tail** of stderr, which on this tool is a progress line. A failed arm reported `field of view scaled to 0.9765..` and named nothing. | Reproducing the failing arm standalone, where it exited 0. |
| 3 | Self-inflicted concurrency: I launched a second render while the ladder ran, and each process plans 5.2 GB against a 6,144 MB budget. Read as a subject-specific failure. | The standalone reproduction succeeding. **Do not run renders concurrently on this machine.** |
| 4 | The report printed "removed -1174.7% of the excess" for subjects whose shipping excess is negative - a quotient of two negatives, printed as a confident number meaning nothing. | Reading my own output rather than its exit code. |

Defect 4 is the smallest and the most characteristic: it did not fail, it
printed. Everything in this part is now guarded so that an undefined quantity
says so instead of rendering as a figure.

### 12.11 What this means operationally

**Exponent 1 is not the fix.** It removes the manufactured detail on the shallow
subjects and replaces it with genuine softness: `-20.70%`, `-22.70%` and
`-22.14%` below ceiling on the three controls, and `-4.87%` to `-10.78%` on
`foam` and `112MSDCF`. Trading a master that invents contrast for one that
throws away a fifth of what the sensor recorded is not an improvement, and on a
print it would read as mush.

The measured zero-crossings - where a subject's master exactly meets its
ceiling - cluster far below what ships:

| subject | crosses zero at exponent | ships at |
|---|---:|---:|
| foam | 1.22 | 8 |
| leaf-2-cpl | 1.22 | 8 |
| 112MSDCF | 1.81 | 8 |

The three shallow controls never cross by exponent 8; the two deep stacks are
already above ceiling at exponent 1. **The subject dependence is real and it is
partly confounded** - the controls in this set are shallow and the excess
subjects are deep - so I do not offer a single recommended exponent. What the
ladder does support is that the fine-band exponent of 8 is far above the point
at which these subjects begin manufacturing detail, and that the cost of moving
it is measurable in both directions on the same gauge.

### 12.12 Gaps

- **The residual mechanism is unidentified.** 12.9 names a cross-band
  hypothesis and does not test it. This is now the largest open question in this
  lane and it is more interesting than the result that prompted it.
- **The exhaustive ceiling was run on two subjects, not nine.** 299 frames at
  ~10 s each is ~50 minutes per subject. The seven others' e1 values still carry
  a sampled ceiling and are upper bounds on excess by an amount that grows with
  stack depth.
- **`e16` is reported and excluded from every test.** It decorrelates the
  content, so nothing about it should be read as a trend.
- **One gauge, one passband.** Every number here is a DoG at sigma 1.0-2.5
  normalised by local mean. It is commissioned for amplitude, but a second
  passband would be an independent check and there is not one.
- **`--pyramid-gate` and `--pyramid-bands` were held fixed.** Only the exponent
  was varied. A different knob could produce the same ordering.


## Part 13 - the hull ladder: the level-0 clamp is not the mechanism

ORCH proposed a fix that is already built, already tested, and does not ship:
`Hull::PerLevel`. The argument was that a band excursion born at a coarse level
and guillotined at level 0 leaves a run of pixels pinned flat at `lo` and `hi` -
a squared-off edge higher in contrast than any input, sitting entirely inside
the value hull. A cut-out sticker rim is what a level-0 clamp looks like from
the outside. ORCH called it a hypothesis and asked me to kill or confirm it.

**Verdict: refuted, with a bound rather than a shrug.** Switching the level-0
clamp off *entirely* changes mid-band contrast by **+0.32% to +2.14%**. The
manufactured detail it is offered to explain is **+17% to +96%** ceiling excess.
`PerLevel` moves it by **-0.11% to +0.42%** - and on the three worst subjects the
sign is *up*, not down. A hard per-level projection, the strongest the code can
express, reaches only **-0.22%**. The clamp axis is one to two orders of
magnitude too small to be the mechanism, and ORCH's own stated criterion was
"if it does not move it at all, the level-0 clamp is not the mechanism and I am
wrong."

For scale, from Part 12 on the same subjects: the *exponent* removes 54.7% to
163% of the same excess. The hull removes 1.17% to 10.12%. `PerLevel` removes
between -1.30% and +0.59%.

### 13.1 Three things I checked before rendering anything

**`crates/` was clean, not dirty.** ORCH said `pyramid.rs` "is dirty right now".
`git status --porcelain -- crates/` returned empty at `fc83eb4e`. That is the
better case - I compiled committed code - but it also means the build lane can
land mid-experiment, so the binary is pinned (13.2) rather than trusted.

**`--per-level` is wired.** `blend-render.rs:138`. It is absent from the usage
string at `blend-render.rs:101`, which advertises `--unclamped` and not
`--per-level`, so it is reachable and undocumented. Three further hull knobs
exist that the brief did not mention: `--hull-lambda`, `--hull-from`,
`--hull-low-only`.

**The tool's own clamp diagnostic cannot answer this question, and I nearly
quoted it as if it could.** `hull clamp : ...` reads *identically* under
`InputRange` and `PerLevel` on all eight subjects, to three decimals. That looks
exactly like `PerLevel` failing its documented claim that "by the time the
reconstruction reaches level 0 there is far less for the last clamp to do".
It is not. `clamped_fraction` at `pyramid.rs:2251` constructs a *fresh* merge
with `hull: Hull::Unclamped` and empty `lo_lv`/`hi_lv`, then measures that
reconstruction against the level-0 bounds. It reports the unclamped excursion
regardless of the configured mode, so it is invariant to the very knob under
test and carries no information about it either way. I record this because the
line is operator-facing and reads like evidence.

### 13.2 The instrument, and a conflict in the brief

ORCH asked for two things that cannot both be done: "run your corrected
ceiling-excess gauge, unchanged" and "do not compare a `blend-render` number
against a `strehl stack` number". The ceiling in `sharp.json` comes from
`strehl.exe` single-frame renders driven by `STREHL_ONLY_FRAME`, and that
variable lives in `merge_cmd.rs`, which `blend-render` does **not** include - it
takes `align_cmd.rs` and `image_out.rs` by `#[path]` and nothing else. So the
frozen ceiling is a strehl-stack quantity and dividing a blend-render master by
it is precisely the forbidden comparison.

I resolved it toward the safety rule. The primary measurand is the **paired arm
ratio** `band(arm) / band(inputrange)` at frozen sites, entirely inside
`blend-render`. It needs no ceiling, so it cannot make the forbidden
comparison, and it is strictly more sensitive than a difference of two excesses
because the ceiling's noise is absent from it. All three predictions are claims
about a change between arms, so all three survive the translation.

Both arms come from **one pinned copy** of the binary,
`37A1B1D49E11713E216E6893CF932B6570869F1197774EDDE77386AFA5F1F037`, hashed
before the first render and again after the last, and it was unchanged. Output
space is `--camera-linear`: camera-native primaries, linear, no matrix, no
transfer curve. `blend-render`'s two declared gaps - no photometric
normalisation, no clip handling - cancel exactly in a within-`blend-render`
difference because both arms are missing the same two stages. That cancellation
is the only thing that makes this instrument admissible and it is void the
moment a number from here is set beside a `strehl stack` number. Nothing in
this part does that.

### 13.3 Commissioning, including the specific artifact under test

All arms pass. `NULL` gives ratio exactly `1.0`, so the reproducibility floor is
zero. `GAIN` x0.5/x2/x8 gives `max |r-1| = 0.000e+00` - both statistics are
exactly invariant to a pure gain, which matters because two separate renders are
not forced to share an absolute level. `SCALE` is exact to **3.01e-08** across
k = 0.5..2.0. `BLUR` is the planted improvement and lowers both statistics
monotonically. `HALO` is the planted defect and raises band monotonically.

The arm that earns its place is **HALOCLAMP**, because it plants ORCH's
mechanism rather than a generic defect: create an unsharp overshoot, then clamp
it back inside the local input range, so an edge is squared off and *no*
overshoot survives outside the hull.

| alpha | band ratio | acuity ratio | px pushed outside the hull |
|---:|---:|---:|---:|
| 0.25 | 1.1146 | 1.1248 | 6.5% |
| 0.50 | 1.2105 | 1.2384 | 11.9% |
| 1.00 | 1.3495 | 1.4196 | 23.6% |

Two things follow. **ORCH's mechanism is physically real** - a clamped overshoot
genuinely carries more mid-band contrast than its source while remaining inside
the value hull. And **the gauge can see it**, at the right sign and monotone in
amplitude. A null from this gauge is therefore a statement about the renders and
not about the instrument's reach.

A separate `PIN` arm, which compresses a window's whole range instead, *lowers*
both statistics (0.83 / 0.73 / 0.61). The two are different artifacts and I keep
them apart; conflating them is how a softening would get reported as a fix.

### 13.4 Potency, and the guard P2 needs

ORCH: run `--unclamped` first. Done, and it raises band on **7 of 8** subjects
(+0.32% to +2.14%), one flat. The gauge responds to the hull axis.

A second potency question the brief did not ask for. Prediction P2 is
"`PerLevel` is inert on the controls", and inertness is indistinguishable from
dead plumbing. `pyramid.rs:3256` records that `hull_lambda` shipped **WIRED AND
INERT** - plumbed correctly, plausible, and moving the output by 0.008%. So
before reporting any null:

| pair | samples differing | median abs delta | max |
|---|---:|---:|---:|
| inputrange vs perlevel, 112MSDCF | **3.790%** | 1 DN | 179 |
| inputrange vs perlevel, coffee-bubbles | **17.468%** | 5 DN | 7304 |
| inputrange vs unclamped, 112MSDCF | 26.077% | 4 DN | 636 |
| inputrange vs unclamped, coffee-bubbles | 37.679% | 8 DN | 11687 |

`--per-level` moves 470x to 2180x more samples than the setting judged inert. It
is doing something substantial to pixels. What follows is therefore inertness of
the *statistic*, not dead plumbing.

### 13.5 The ladder

Median ratio against the `inputrange` (shipping) arm, 40 frozen sites each.

| subject | prior excess | perlevel band | perlevel acuity | unclamped band | unclamped acuity |
|---|---:|---:|---:|---:|---:|
| pencil-steep-angle-cpl | +96.4% | **+0.037%** | +0.000% | +0.575% | +0.468% |
| flower-inner-edge-cpl | +69.4% | **+0.424%** | +0.028% | +2.138% | +1.451% |
| wrapped-text-1 | +28.3% | **+0.287%** | +0.102% | +0.594% | +0.238% |
| foam | +23.2% | -0.110% | -0.149% | +1.907% | +1.739% |
| 112MSDCF | +17.0% | -0.009% | -0.015% | +0.772% | +0.390% |
| 109MSDCF * | -5.5% | +0.000% | -0.000% | +0.799% | +0.119% |
| coffee-bubbles * | -1.6% | -0.009% | -0.007% | +1.286% | +0.938% |
| 119MSDCF * | -1.3% | +0.000% | -0.002% | +0.319% | +0.126% |

`*` = negative control. Acuity is quoted on the same pixels as band throughout,
as ORCH required, and it tracks band closely everywhere - so there is no hidden
sharpness trade in either direction. `PerLevel` neither removes manufactured
detail nor costs acuity; it does very little to either.

**P1 is refuted.** `PerLevel` does not reduce manufactured detail on the excess
subjects. On the three worst it *raises* it, one of them by +0.42% with a
worst site at +7.4%.

**P2 is confirmed but uninformative.** `PerLevel` is inert on the controls
(+0.000%, -0.009%, +0.000%). It is equally inert on the excess subjects, so this
is not the selective inertness the prediction described - it is global
inertness.

Arms are on the same pixel grid: zero-shift Pearson r has median >= 0.9996 and
minimum 0.9974 across every subject and arm, with no registration applied.

### 13.6 Is the null a result, or is my site set pointed away from it?

`--per-level` moves up to 17.5% of samples while the gauge reads ~1.0000. Those
are compatible two ways, and only one is a result. Three checks, none of which
uses the site list:

| subject | global band ratio, no sites | at the 24 most-changed tiles | mean abs delta: frame / my sites / hottest tiles |
|---|---:|---:|---|
| foam | 0.998874 | 0.998531 | 8.90 / 8.46 / 24.76 DN |
| 112MSDCF | 0.999880 | 0.999780 | 0.151 / 0.143 / 0.749 DN |
| coffee-bubbles | 0.998831 | 0.996591 | 4.72 / 6.11 / 48.34 DN |

The global ratio, computed over the entire frame with no site selection at all,
reproduces the site reading to four decimals. And **where `PerLevel` acts
hardest** - tiles carrying 3x to 10x the frame-average change - mid-band
contrast still does not move. The same global measure reads 1.019 / 1.007 /
1.018 for `--unclamped`, so it is not a measure that refuses to move. The null
is a property of the renders.

### 13.7 Is `PerLevel` merely configured too soft?

`hull_lambda` defaults to 2.0 and `pyramid.rs:1013` documents `hull_lambda = 0`
as a hard per-level projection, so a null at the default is ambiguous between
"wrong mechanism" and "too weak a bound". The sweep removes the ambiguity.

| arm | foam band | coffee-bubbles band | what it is |
|---|---:|---:|---|
| `--hull-from 5` | 1.00007 | 1.00000 | bound confined above the visible scales - **internal null** |
| `--per-level` (lambda 2.0) | 0.99890 | 0.99991 | the mode as it would ship |
| `--hull-lambda 0.5` | 0.99819 | 0.99968 | |
| `--hull-lambda 0` | **0.99778** | **0.99941** | **hard projection, the strongest available** |
| `--unclamped` | 1.01907 | 1.01286 | no hull at all - **potency** |

The arms order monotonically by bound strength and the internal null lands at
1.00007, so the sweep is responding to the knob and is capable of printing a
null when a null is correct. The entire span from the weakest per-level bound to
the hardest is **0.23%** on `foam` and **0.06%** on `coffee-bubbles`. There is
no setting of this mechanism that reaches the effect.

### 13.8 What the clamp is worth, projected onto the excess

The ratios above are dimensionless and measured within one binary. Projecting
them onto Part 12's ceiling excess assumes the ratio transfers between the two
renderers; it is labelled a projection for that reason and the primary result
above does not depend on it.

| subject | excess | removed by `PerLevel` | removed by removing the clamp entirely |
|---|---:|---:|---:|
| pencil-steep-angle-cpl | +96.4% | -0.08% | -1.17% |
| flower-inner-edge-cpl | +69.4% | -1.04% | -5.22% |
| wrapped-text-1 | +28.3% | -1.30% | -2.69% |
| foam | +23.2% | +0.59% | -10.12% |
| 112MSDCF | +17.0% | +0.06% | -5.31% |

Negative means the arm *added* excess. The shipping level-0 clamp is already
worth between 1.17% and 10.12% of the manufactured detail - it helps, mildly -
and `PerLevel` adds nothing on top of it.

### 13.9 What this result does and does not say

It says the level-0 clamp is not the mechanism behind ceiling excess, and it
bounds the whole clamp axis at ~2% of mid-band contrast.

It does **not** independently re-open the rim question, but it does bound it.
`HALOCLAMP` shows this gauge reads a clamped overshoot at +11% to +35% band, so
a sticker rim of any material amplitude would be visible to it. Removing the
clamp entirely moves the measured band by at most 2.14%. Whatever rim the
level-0 clamp creates on these eight subjects is therefore small on this
statistic. A dedicated rim instrument zoning on occluding edges - Part 11's
axis, or V-HEADTOHEAD2's - remains the right tool for the rim question, and this
is a bound, not a substitute for it.

It also does not touch the residual identified in 12.9. That residual survives
an exhaustive ceiling at exponent 1, and the hull is now excluded as its source
too, which makes the cross-band hypothesis in 12.9 more attractive by
elimination and no better tested.

### 13.10 Defects I found in my own harness

| # | defect | what caught it |
|---|---|---|
| 1 | `hul_report.py` read its subject list from `hull-render.json`, which `hul_run.py` only writes after the last subject. It examined **0** subjects, summed its partition to `0 == 0`, called that OK, and printed **"the gauge is NOT sensitive to the hull axis"** from n = 0. | Reading the output instead of the exit code. It now hard-errors on an empty population and prints NOT EXAMINED rather than a verdict. |
| 2 | The same run's partition was a green produced by nothing being examined - the exact ambiguity this lane filed against the print gate. | Now a partition that balances at zero is an explicit failure. |
| 3 | The `PIN` commissioning arm printed a "pixels pinned" figure computed as `100 * p / 100 * 100 / 100 * p`, which is not the quantity named. | Reading my own output. Replaced with an actual count. |
| 4 | I was about to cite the identical `hull clamp` lines as evidence that `PerLevel` fails its documented claim. | Reading `clamped_fraction` rather than trusting the label (13.1). |

Defect 1 is the serious one and it is the same shape as the finding this lane
filed against the print certification: a conclusion printed from an empty
population, wearing the same glyph as a conclusion drawn from evidence.

### 13.11 Gaps

- **Eight subjects, not the full 26.** The five with the largest measured excess
  and all three within-ceiling controls.
- **One gauge, one passband.** Mid-band contrast at DoG sigma 1.0-2.5 plus a
  gradient acutance. Commissioned for amplitude, but a rim-specific zoning
  statistic is a different instrument and is not run here.
- **The projection in 13.8 assumes the ratio transfers between renderers.** It
  is labelled and nothing depends on it.
- **`--hull-low-only` was not swept.** The sweep covers bound strength and bound
  placement, not one-sidedness.
- **`blend-render` is missing photometric normalisation and clip handling.**
  That is admissible here only because both arms are missing them equally.

## Part 14 - STREHL_GATE_FLOOR: the fix is real, its stated reason is inverted

ORCH asked for a `STREHL_GATE_FLOOR=white` vs default A/B on the rim subjects,
as a retrospective control on the pin: `white` restores the pin's floor
behaviour inside the current binary, so one variable moves instead of
eighteen commits. That framing is right and I adopted it. I did not adopt the
mechanism it came with, because the mechanism does not survive measurement.

The short version: **the gate-floor default is a genuine improvement, it
denoises rather than softens, it does not touch rim - and the justification
written in its own module docs has the wrong sign for the configuration
strehl actually ships.**

### 14.1 Premises checked first

| ORCH's premise | verdict |
| --- | --- |
| `9b05d0b7..HEAD` is 13 commits / 26 files / +12,637 / -538 | **stale**. Measured 18 commits, 29 files, +15,047 / -604. HEAD moved after they measured; the direction of their point is unaffected. |
| `gatefloor.rs` does not exist at the pin | **confirmed**. `git cat-file -e 9b05d0b7:...` rc=128, present at HEAD rc=0. |
| `78fed9a1` landed | **confirmed**, `git merge-base --is-ancestor` rc=0. |
| on by default unless `STREHL_GATE_FLOOR=white` | **confirmed** at `gatefloor.rs:92-99`, `.unwrap_or(true)`. |
| `crates/` clean | **false**. `pyramid.rs` carries 43 uncommitted lines from the build lane. |

That last one matters procedurally. **I did not build "HEAD".** I built
`f1f40150` plus 43 uncommitted lines in `pyramid.rs`, and the diff is saved at
`experiments/V-GATHER/gf-tree-dirt.diff` so the arm can be identified later.
It is admissible because both arms come from **one binary**
(`16E645FD0AD42260...`, hashed before and after the whole run, unchanged), so
the dirt is common to both and cancels in the paired difference. It would not
be admissible against any number rendered from a different build.

**A trap worth naming.** `STREHL_FULLRES_GATHER` panics on an unrecognised
value by design. `STREHL_GATE_FLOOR` does **not**: anything that is not
`white` enables the measured floor. A typo in the control arm therefore
silently produces two default arms, and the experiment reads as a clean null.
Every arm below is backed by a positive presence check, never by the spelling
of an environment variable.

### 14.2 Potency, established three ways before anything was interpreted

| check | result |
| --- | --- |
| output bytes differ between arms | `white` 1F937943.. vs `measured` CDC0C458.. - differ |
| `measured floor` banner | present in default, **absent** under `white` (0 lines) |
| `debug` is reporting-only | `debug` output is **byte-identical** to the default arm (CDC0C458..) |

The third is a control I have not seen asked for and it is worth keeping: it
proves `STREHL_GATE_FLOOR=debug` can be used to read the mechanism without
changing the render being read.

### 14.3 The finding: the documented premise is inverted where strehl ships

The module docs state the white floor **over-states** the true one, citing
BUILD-GATE's `beta_actual / beta_white` in **0.3432 .. 0.9981**, "every entry
below 1.0", measured "in **both** gather arms".

That reproduces only with `STREHL_FULLRES_GATHER=0`. At the shipping default -
full-res gather ON, the flip I verified in Part 1 - it inverts:

| subject | gather=0 (old plane path) | gather=1 (**shipping**) |
| --- | --- | --- |
| 109MSDCF | 0.6219 | **1.2332** |
| 119MSDCF | 0.6227 | **1.1655** |
| 112MSDCF | 0.6188 | **1.2151** |
| wrapped-text-1 | 0.6115 | **1.1619** |
| 113MSDCF | - | **1.2151** |
| coffee-bean | - | **1.1609** |
| flat-on-ruler-cpl | - | **1.1736** |
| leaf-2-cpl | - | **1.5504** |

**4 of 4 below 1.0 in the old path; 8 of 8 above 1.0 in the shipping path, all
outside the cited range.** The two arms were run from one binary at identical
warps - the debug lines print the same displacements per frame
(`frame 0 d=(-0.0778,+0.5023)` in both) - so the gather path is the only
variable.

The mechanism is not mysterious. The old path deinterleaves to half-res planes
and interpolates, which correlates neighbours and *lowers* band-0 noise power.
The new path demosaics, and Malvar interpolation *raises* it. Both floors are
measured correctly. Only the sentence explaining why is wrong.

### 14.4 Consequence: the gate gets stricter, and ORCH's prediction is refuted in sign

ORCH predicted the fix "makes the gate **less** strict, so it should
**increase** selection and **reduce** softening". Band-0 averaging, the
fraction of pixels the gate averages rather than selects:

| subject | white | measured (default) | change |
| --- | --- | --- | --- |
| leaf-2-cpl | 7.1% | 54.4% | **+47.3** |
| 109MSDCF | 52.5% | 72.5% | +20.0 |
| 119MSDCF | 15.5% | 34.4% | +18.9 |
| 112MSDCF | 14.8% | 32.1% | +17.3 |
| 113MSDCF | 16.0% | 28.6% | +12.6 |
| coffee-bean | 1.5% | 7.5% | +6.0 |
| wrapped-text-1 | 0.3% | 1.1% | +0.8 |
| flat-on-ruler-cpl | 0.0% | 0.0% | 0.0 |

**Rose on 7 of 8, fell on none.** The gate became *more* strict at band 0, not
less. Under `STREHL_FULLRES_GATHER=0` the same knob moves 109MSDCF's averaging
76.8% -> 16.9%, which is the intended direction. The fix does what BUILD-GATE
says - in the gather arm strehl no longer uses.

### 14.5 But the effect is denoising, not softening - and that overturned my own reading

Global acuity fell (leaf-2-cpl 0.9165, i.e. -8.35%) and I was heading for
"the default softens". That would have been wrong. Frame averaging lowers
mid-band energy two ways that mean opposite things, and a global number cannot
separate them, so I split the frame by local structure measured on a reference
built from **both** arms, privileging neither.

Commissioned with a planted denoise and a planted softening, because a
discriminator that has only seen one cannot be known to separate them:

| arm | flat | detail | required |
| --- | --- | --- | --- |
| DENOISE (noise halved, signal untouched) | **0.5000** | 0.9983 | flat<<1, detail~1 |
| SOFTEN (signal blurred, noise untouched) | 1.0000 | **0.7313** | detail<<1 |
| NULL | 1.000000 | 1.000000 | exactly 1 |

`0.5000` for an exact halving is amplitude fidelity, not merely direction.
Separation in detail territory is 0.2670. The result:

| subject | flat | detail | reading |
| --- | --- | --- | --- |
| leaf-2-cpl | 0.8082 | 0.9895 | denoise only |
| 109MSDCF | 0.7374 | 1.0021 | denoise only |
| 112MSDCF | 0.8578 | 1.0039 | denoise only |
| 113MSDCF | 0.8983 | 1.0042 | denoise only |
| 119MSDCF | 0.9079 | 1.0004 | denoise only |
| coffee-bean | 0.9471 | 0.9999 | denoise only |
| wrapped-text-1 | 0.9997 | 1.0002 | inert |
| flat-on-ruler-cpl | 1.0003 | 1.0000 | inert |

leaf-2-cpl loses **19.2% of flat-field mid-band energy and 1.05% of detail**.
The -8.35% global acuity was almost entirely noise.

Two independent reasons this is not an artifact of my cut. Sweeping the detail
quantile from 0.50 to 0.99, leaf-2-cpl runs 0.9539 -> 0.9735 -> 0.9895 ->
0.9984 -> **1.0114**: the tighter the cut onto real structure, the closer to
and then above unity, which is the signature of noise removal rather than
detail loss. And every arm registers at integer shift **(0,0)**, so no band
difference is fabricated by misalignment.

### 14.6 Rim does not move

The axis ORCH was most worried about. Sites frozen once on a rim-free
reference built from both arms - an earlier version of this instrument
reselected per arm and compared two different populations, which is the same
defect that makes the inherited v3 read +14.85% on a rim-free image.

| subject | rim white | rim measured | delta | verdict |
| --- | --- | --- | --- | --- |
| leaf-2-cpl | +0.1038 | +0.1012 | -0.0026 | UNRESOLVED |
| coffee-bean | +0.1440 | +0.1438 | -0.0002 | UNRESOLVED |
| 113MSDCF | +0.0864 | +0.0868 | +0.0004 | UNRESOLVED |
| flat-on-ruler-cpl | +0.1007 | +0.1008 | +0.0002 | UNRESOLVED |
| 112MSDCF | +0.0930 | +0.0908 | -0.0022 | UNRESOLVED |
| wrapped-text-1 | +0.1012 | +0.1014 | +0.0002 | UNRESOLVED |
| 109MSDCF | +0.0366 | +0.0364 | -0.0002 | UNRESOLVED |
| 119MSDCF | +0.0288 | +0.0288 | -0.0000 | UNRESOLVED |

`partition: 8 = 0 PASS + 0 FAIL + 8 UNRESOLVED + 0 REFUSED + 0 NOT EXAMINED`

**UNRESOLVED is not PASS.** Every delta is smaller than the gauge's own
deformation floor, so the honest statement is that this instrument cannot
resolve a rim change of this size - not that there is none.

That floor is itself a measurement. The BLUR commissioning arm **failed** in
its strict form: a sigma-2 blur, which cannot create a rim, still moved the
statistic by **+0.0039**. Rather than move `FLATTEN` until it passed - fitting
the instrument to the answer - I recorded +0.0039 as the floor for comparing
two *different* images. The byte-identical floor is exactly 0; this one is not,
and this one governs an A/B. The largest rim delta observed is 0.0026, which
is 67% of it.

Calibration, stated as a limit: the SCALE arm recovers planted amplitude with
slope **0.644**, monotone over 0.05..0.40. Rim readings here are **lower
bounds**, understated by about 1.55x.

### 14.6a Commissioning, in full

| arm | result |
| --- | --- |
| NULL | rim delta 0.000e+00, acuity ratio 1.000000000000 |
| GAIN (x1.7) | both **exactly** invariant - the `--auto-exposure` trap in miniature |
| SCALE | monotone, slope 0.644 - measures amplitude, not presence |
| BLUR | acuity -36.1%; rim +0.0039 = the deformation floor |
| RIMPLANT | +0.0000 -> +0.3262 |
| IMPROVE (detail added away from edges) | acuity +0.2%, rim +0.0002 - **not** fooled by sharpening as such |
| DERIM | +0.3262 -> +0.0000 - removing a rim scores better, so the axis is not perverse |
| NANGUARD | a NaN does not read as a clean pass |

`IMPROVE` and `DERIM` are the planted-improvement arms. Without them a suite of
degradations cannot distinguish a gauge that is blind to a defect from one that
is perverse on it.

### 14.7 Two natural nulls I did not have to build

`flat-on-ruler-cpl` averages **0.0% in both arms** - the mechanism is inert
there by the tool's own accounting - and reads acuity 1.0001, detail 1.0000 at
every quantile from 0.50 to 0.99, rim +0.0002. `wrapped-text-1` moves 0.8
points and reads 1.0002 / 1.0002. The gauge is quiet exactly where the
mechanism is quiet, which is what makes the movement elsewhere interpretable.

### 14.8 A defect in the module's own control

`gatefloor.rs` ships a self-check that measures the probe at an **identity
warp** and compares it to white:

```
gate floor: NULL frame 18 identity warp  b0=0.8895 (0.9997x white)  worst band +0.736%  PASS
```

It passes at `0.9996x`..`0.9997x` in **both** gather arms. It has to: the
module's own docs say the full-res gather "is an exact no-op at integer
full-res shifts". So the control is evaluated at precisely the one point where
the two gather paths agree by construction, and is **structurally incapable**
of detecting that they diverge to 0.62x and 1.55x at real warps. The control is
sound for what it tests and blind to the thing that turned out to matter.

### 14.9 Verdict

- **Keep the default on.** It removes up to 26% of flat-field mid-band energy
  and costs at most 1.05% of detail on the worst subject tested, and it does
  not move rim.
- **The docstring and the commit message are wrong for the shipping
  configuration** and should not be cited as the reason. `beta_actual/beta_white`
  is 1.16..1.55 at band 0 under the default gather, not "every entry below 1.0".
  Anyone reasoning forward from that sentence - as ORCH did, and as I nearly
  did - will predict the wrong sign.
- **ORCH's prediction is refuted in sign, and their fear is not realised.** The
  gate got stricter, not looser; and rim did not get worse. Both halves needed
  measuring because neither was implied by the other.
- **This does not explain the rim failures.** Rim does not move, so the
  already-landed fix accounts for **none** of the 13, and re-certifying against
  a HEAD baseline will not clear them by this mechanism.

### 14.10 My own defects this part

1. `gf_commission.py` had a format string with four placeholders and three
   arguments; it crashed before printing a baseline.
2. My first discriminator fixture used 20 px flat runs against a 33 px variance
   window, so no window was ever purely flat and a planted **halving** of noise
   read 0.9161 instead of 0.5000. The fixture was wrong, not the instrument;
   widening the runs gave exactly 0.5000. Caught only because the planted arm
   had a predicted *value* rather than a predicted direction.
3. I read the `x white` banner with a pattern that also matched the per-frame
   `0.9993x white` NULL lines, and briefly tabulated NULL values as banner
   values.

### 14.11 Gaps

- 8 subjects of 26. Chosen by rim severity at the pin; that selection cannot
  bias a paired A/B run entirely at HEAD, but it does not make them typical.
- **The rim axis is UNRESOLVED, not clean.** A change smaller than 0.0039
  would not have been seen.
- Isolation excludes most high-contrast features on some subjects, as
  V-HEADTOHEAD2 found; the rim numbers speak only to edges that settle within
  7 px.
- Noise reduction is measured as mid-band energy in flat territory, not as a
  photon-noise estimate against a dark-frame model.
- One binary at `f1f40150` + 43 uncommitted lines. Not a clean HEAD, and not
  reproducible from a commit alone.
- `STREHL_GATE_FLOOR_SCALE` was not swept. It is the knob that could correct
  band 0 alone, and it is the obvious next measurement.

## Part 15 - ORCH's correction, corroborated, bounded, and one consequence refuted

ORCH retracted the direction they had relayed and asked all lanes to
reproduce before relying on it. Part 14 had already run the experiment. This
part reconciles the two, generalises the half of their correction that holds,
bounds the half that does not, and refutes the reconciliation they drew from
it.

### 15.1 Independent corroboration of the headline

| | ORCH | V-GATHER (Part 14) |
| --- | --- | --- |
| binary | `AAAF8666B5F08DA5`, clean HEAD | `16E645FD0AD42260`, HEAD + 43 uncommitted lines |
| recipe | `--srgb --auto-exposure` | `--srgb`, no exposure applied |
| leaf-2-cpl band-0 `x white` | **1.5504** | **1.5504** |

Two lanes, two builds, two recipes, the same number. That also retires my own
Part 14 caveat about the dirty `pyramid.rs`: the floor ratio is identical on a
clean tree, so the dirt did not touch it.

### 15.2 "Every entry is ABOVE 1.0" - true for their subject, false for most

ORCH generalised from `leaf-2-cpl`. Across the eight subjects already rendered:

| subject | band 0 | band 1 | band 2 | band 3 |
| --- | --- | --- | --- | --- |
| leaf-2-cpl | 1.5504 | 1.0693 | 1.1132 | 1.1386 |
| wrapped-text-1 | 1.1619 | 1.0139 | 1.0796 | 1.1068 |
| 109MSDCF | 1.2332 | **0.9475** | **0.9963** | 1.0196 |
| 112MSDCF | 1.2151 | **0.9650** | 1.0186 | 1.0430 |
| 113MSDCF | 1.2151 | **0.9574** | 1.0097 | 1.0339 |
| 119MSDCF | 1.1655 | **0.9368** | **0.9880** | 1.0114 |
| coffee-bean | 1.1609 | **0.9808** | 1.0409 | 1.0668 |
| flat-on-ruler-cpl | 1.1736 | **0.9745** | 1.0329 | 1.0570 |

**Band 0 is above 1.0 on 8 of 8** (1.1609..1.5504) - the headline holds and
generalises. **Band 1 is BELOW 1.0 on 6 of 8.** The two subjects where "every
entry" holds are ORCH's own and `wrapped-text-1`.

So the composition ORCH describes - warping pulls down, demosaic pulls up - is
right, but which term wins is **band-dependent and subject-dependent**, and it
only reliably wins at band 0.

### 15.3 "The gate does not fire above level 0" - confirmed, and it generalises

This is the more valuable half of ORCH's message and it survives widening.
`averaged`, default arm, all eight subjects:

| subject | L0 | L1 | L2 | L3..L6 |
| --- | --- | --- | --- | --- |
| 109MSDCF | 72.5% | 0.2% | 0.0% | 0.0% |
| 119MSDCF | 34.4% | 0.0% | 0.0% | 0.0% |
| 112MSDCF | 32.1% | 0.7% | 0.0% | 0.0% |
| 113MSDCF | 28.6% | 1.1% | 0.1% | 0.0% |
| leaf-2-cpl | 54.4% | 0.0% | 0.0% | 0.0% |
| coffee-bean | 7.5% | 0.0% | 0.0% | 0.0% |
| wrapped-text-1 | 1.1% | 0.0% | 0.0% | 0.0% |
| flat-on-ruler-cpl | 0.0% | 0.0% | 0.0% | 0.0% |

The literal "0.0% at levels 1 through 6" is not exact - `113MSDCF` reaches 1.1%
at L1 and 0.1% at L2 - but **the maximum anywhere above level 0, across eight
subjects, is 1.1%**. By the banner's own criterion the gate is a level-0
device. Confirmed at 8x the evidence ORCH had.

### 15.4 Their new prediction for me: half confirmed, half refuted

> "`white` is the *looser* gate on real frames, so `white` should select more
> and soften less. If rim worsens under `white`, that supports the
> excursion-then-clamp mechanism."

- **"`white` selects more" - CONFIRMED.** Band-0 averaging is lower under
  `white` on 7 of 8 and equal on the eighth (Part 14 §14.4).
- **"and softens less" - REFUTED as stated.** `white` is not sharper in real
  detail; it is **noisier**. The structure-split discriminator, commissioned to
  read exactly `0.5000` on a planted halving of noise, puts the whole
  difference in flat territory.
- **"if rim worsens under `white`" - it does not, either way.** 8 of 8
  UNRESOLVED, every delta below the gauge's own +0.0039 deformation floor. This
  neither supports nor refutes excursion-then-clamp; the instrument cannot
  resolve a change of that size, and that is reported as UNRESOLVED rather than
  as a clean bill.

### 15.5 The reconciliation with BUILD-PLUGIN is probably wrong

ORCH now reads BUILD-PLUGIN's **-9.9% to -39.9% sharpness** as vindicated by
the stricter gate, and has promoted "`k` was tuned against the wrong floor" to
leading candidate. Before that is acted on, the same pixels pooled two ways,
on `leaf-2-cpl`, white -> default:

| sigma | GLOBAL (no structure split) | flat | detail |
| --- | --- | --- | --- |
| 0.7 | **-22.42%** | -51.24% | **-1.21%** |
| 1.4 | -8.33% | -33.13% | +0.64% |
| 2.8 | -2.89% | -9.75% | +0.04% |
| 5.6 | -1.23% | -2.04% | -0.63% (scale blind) |
| 11.2 | -0.52% | -0.64% | -0.30% (scale blind) |

**A global sharpness metric reports -22.42% on pixels where detail is
-1.21%.** That lands inside BUILD-PLUGIN's reported range, from noise removal
alone, on the subject and the change in question.

I have not read BUILD-PLUGIN's instrument and I am not asserting it is wrong. I
am asserting that **an error of exactly their magnitude is available here**,
that I nearly published it myself in Part 14 before the discriminator caught
me, and that it is cheap to exclude: `gf_discriminate.py` and
`gf_multiscale.py` are committed and take one extra pooling step over bands
they already compute.

The two coarsest scales are marked blind because a **planted** softening reads
only 0.9598 and 0.9888 there - they cannot see the defect, so they are excluded
rather than counted as evidence of its absence.

### 15.6 A falsifiable prediction for the re-tuned `k`

If the measured -9.9%..-39.9% is noise rather than detail, then **lowering `k`
will restore noise and not sharpness.** Concretely, on `leaf-2-cpl`:

- band-0 averaging falls from 54.4% toward the `white` arm's 7.1%;
- flat-territory mid-band energy rises back toward 1.0 - most of the -51.24% at
  sigma 0.7 returns;
- **detail-territory energy moves by ~1%, because it only moved by 1.21% in the
  first place.**

If a lower `k` recovers materially more than ~1% of *detail* energy, this
analysis is wrong and BUILD-PLUGIN's reading is right. That is the experiment
that separates them, and it is one render plus one pooling.

One caution on the direction: because the gate already fires at 0.0-1.1% above
level 0, **`k` has no authority there** - lowering it can only act at band 0.
And the band-1 floor moved *down* on 6 of 8 subjects, so the stated
justification ("the floor moved up and `k` did not move with it") is a band-0
argument, not a pyramid-wide one. The per-band `STREHL_GATE_FLOOR_SCALE` knob
exists for exactly this asymmetry, and its own docstring says `--pyramid-gate`
"is a single number by construction and the measurement that motivated the knob
wants opposite moves at opposite ends of the pyramid".

### 15.7 The `--auto-exposure` recipe is safe here

ORCH's recipe uses `--auto-exposure`, which chooses a gain per image and is a
documented trap. Read from the fixed-exposure logs, which print the gain that
*would* have been chosen, the two arms agree on **7 of 8** subjects; `109MSDCF`
differs by 6.063x vs 6.105x, or 0.7%. Since the metrics here are normalised, a
pure gain cancels exactly (commissioned: `GAIN` arm invariant to 1e-12). So
exposure is **not** the explanation for BUILD-PLUGIN's magnitude, and ORCH's
recipe does not need changing.

**CORRECTION, 2026-08-27. The last clause of that paragraph is refuted, and the
evidence was already in it.** ORCH measured that `--srgb --auto-exposure` at HEAD
blows 11 of 18 masters, `109MSDCF` reaching 92.03% of pixels clipped at 65535
with a pure-white median, where the same command without `--auto-exposure` clips
0.00%. A tone stage added since the pin performs the normalisation that
`--auto-exposure` used to perform, so HEAD applies it twice.

**Why this section missed it.** I compared the two arms' *gains* -- 6.063x
against 6.105x, 0.7% apart -- and concluded the confound cancelled because a
pure gain cancels in a normalised ratio. It does. But those are the same two
numbers ORCH now cites as proof that **the gain is not the regression**: the
gain is correct, and what changed is the baseline it multiplies. I checked the
multiplier and never asked what it was multiplying. Clipping is not a gain. It
is destructive, it is not invertible, and it does not cancel in a normalised
metric -- a saturated region has no structure for a structural metric to read,
so a blown master can read clean on every axis.

The commissioned `GAIN` invariance result stands and is unaffected; it shows the
metrics are blind to a gain, which was never the failure mode. **My
recommendation that the recipe did not need changing is withdrawn.**

**No measurement in this report moves.** Every V-GATHER render is plain `--srgb`
with no exposure applied; verified three ways in Part 16's reply -- no V-GATHER
script contains the flag, the render logs record `Nothing was applied`, and the
pixels read 0.00-0.03% clipped across all 16 masters. The 26 delivered SHIP-V4
masters, on which the rim corpus verdict rests, measure 0 blown with worst-case
clipping 0.134%.

### 15.8 Gaps

- Band 1's sub-1.0 ratio is measured but its behavioural consequence is not,
  because the gate barely fires there. If a lower `k` makes L1 gating live, that
  floor becomes relevant and has not been evaluated.
- The multi-scale check ran on `leaf-2-cpl` only - the largest effect, but one
  subject.
- Two of five scales are blind to a planted softening; a softening confined to
  sigma >= 5.6 would not be caught by anything here.
- I still have not seen BUILD-PLUGIN's instrument. §15.5 is an available
  explanation, not a diagnosis.

## Part 16 - The per-band gate-floor knob does not move the rim

ORCH asked for the rim axis on two files said to be on disk, and asked to be
told early if the knob is worthless. The knob is not worthless. It is also not
doing what ORCH argued, and the falsification condition ORCH wrote first is the
one that fired.

### 16.1 The two files ORCH cited do not exist

`C:\dev\strehl-out\ORCH-BANDGATE\` is not a directory on this machine.
`Test-Path` returns False, a recursive search of `C:\dev\strehl-out` for
`A-unset.tiff` and `C-coarse8.tiff` returns nothing, and there is no
`ORCH-BANDGATE` among the 32 lane directories there. The SHA-256 prefix ORCH
quoted for the unset arm, `171981BC7DC8CD7D`, does not exist on disk either.

What does exist is `C:\dev\strehl-out\V-BANDFLOOR\`, where **another lane has
already rendered the same treatment on six subjects**, naming the coarse arm
`B-coarse8` rather than `C-coarse8`. I used those. ORCH should know two lanes
are pointed at this knob.

### 16.2 The provenance I proved before using someone else's renders

Reading another lane's output is only admissible if the pair is a real A/B, so
each of these was checked rather than assumed:

| check | evidence |
| --- | --- |
| same binary | `target-orch\release\strehl.exe`, mtime **3:31:38 PM**, predating both renders (**4:38:21 PM**, **4:44:50 PM**) and unmodified between them |
| same recipe | both `stack <dir> -o <out> --srgb`, no other flag |
| one variable | `STREHL_GATE_FLOOR_SCALE` `None` against `'1,8,8,8,8,8,8'` |
| the treatment is ORCH's | banners reproduce ORCH's quoted lines **exactly**: `54.4% 0.0% 0.0% 0.0% 0.0% 0.0% 0.0% 100.0%` and `54.4% 19.4% 5.2% 4.0% 2.4% 0.5% 0.0% 100.0%` |
| no exposure confound | neither arm applied exposure; the trap ORCH warned about is avoided because plain `--srgb` reports the gain and applies nothing. The gains it *would* have chosen differ by 0.7% (+3.19 vs +3.20 stops) and were not applied |
| a free byte-identical null | a third arm at `'1,1,1,1,1,1,1'` hashes **`B8EDBF4B19C39C49`**, identical to the unset arm; the treatment hashes `84E0EB3B9C9FC0EF` |

That last row is worth more than the rest. ORCH's commissioning claim that
all-ones is byte-identical to unset **reproduces on a different lane's renders
with a different binary**, and it hands the rim gauge a perfect null for free.

### 16.3 Fact 1807: corroborated by a second knob, and my own §15.3 was wrong

ORCH withdrew "the gate never fires above level 0" after seeing coarse bands
gate at `--pyramid-gate 8` and `64`. **The withdrawal is right, and there is
independent evidence for it in the very files ORCH sent me to.** ORCH raised
`k`; V-BANDFLOOR's B arm holds `k = 2.0` fixed and raises only the per-band
floor, and bands 1 through 5 go from `0.0%` to **`19.4 / 5.2 / 4.0 / 2.4 /
0.5%`**. Two different knobs, two lanes, same conclusion: the coarse gate is
capable, it is simply never reached at the shipping constant.

**My §15.3 is corrected.** Its measurement stands - across eight subjects at the
shipping `k`, the maximum averaging anywhere above level 0 is 1.1%. Its last
sentence does not: I wrote *"by the banner's own criterion the gate is a level-0
device, confirmed at 8x the evidence"*, which states as a structural property
what is only a property of `k = 2.0`. I amplified ORCH's over-generalisation
instead of catching it, and I had the data to catch it, because "the floor is
never reached" and "the gate cannot fire" are different claims and only the
first is measured. Read §15.3 as **"at the shipping constant"** throughout.

### 16.4 Three instruments were ruled inadmissible before one was trusted

None of this is padding; each refusal changed what could be reported.

1. **My own from-scratch paired gauge (`bg_lib.py`) is inadmissible on this
   subject.** It could not recover a planted blur of 1.2 px at any isolation cut
   leaving 30 edges, reading `-0.045`, `+0.016`, `-0.089` px of sigma where
   `+0.455` was planted, while base rim read `+0.277` - the textured-band
   pathology `rimindep.py` already documents at +27%. It is retained only for
   the coupling number it did produce.
2. **The 10-90 rise is driven by the rim it is supposed to be independent of.**
   A planted aura of 0.15 moved rise from 3.71 px to 3.18 px on an edge of
   identical blur: **-3.85 px per unit rim, R^2 0.9617** over a four-point
   ladder. That coupling runs the wrong way here - an arm that genuinely removed
   an aura would have been reported as softening. A centre-slope variant cut it
   to -3.3 and did not remove it.
3. **`rimv6.edge_width` is inadmissible as a softening detector**, which matters
   because it is the obvious answer to ORCH's trap. Against a planted blur
   ladder at the frozen sites it fails at every rung and is **non-monotonic**:

   | planted sigma | 0.4 | 0.8 | 1.2 | 2.0 | 3.0 |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | predicted d width | +0.121 | +0.466 | +0.991 | +2.399 | +4.521 |
   | measured d width | **-0.101** | **-0.135** | +0.061 | +0.999 | +2.296 |

   It reads *negative* for small blurs and recovers about 40% at sigma 3. **The
   width column in §16.6 is therefore not evidence and must not be read as
   any.** This was caught because the blur arm and the median arm disagreed in
   the wrong direction, not by inspection.

A fourth was a defect in my harness rather than an instrument: `rimv6.choose_cut`
requires 1000 edges, was forced onto a loose cut, left the floor at +2.641% and
made the instrument refuse. `rimaxis.py`'s own sweep takes any cut at 30 edges
and minimises the floor, reaching +1.513%. I used the committed logic. The 2%
floor rule was not relaxed, and `coffee-bubbles` is REFUSED below because of it.

### 16.5 What the trusted gauge demonstrated before it was believed

The rim core is committed `rimv6`, unmodified. Changed only: two explicit paths
instead of the SHIP-V4 seal, selection frozen **once on the smoothed control and
reused by both arms** so the comparison is paired, and a bootstrap over the
paired per-edge difference. rimv6 defaults to unpaired because different
comparators carry a 1.005x raster scale; that does not apply to two renders from
one binary and one registration, and the integer shift is asserted `(0,0)`.

- **Null: exactly `+0.000%`, 95% CI `[+0.000%, +0.000%]`**, on all three
  subjects that have a byte-identical arm. The gauge is exactly deterministic,
  so there is no noise floor to clear - a rarity worth stating plainly.
- **Amplitude, not presence.** ORCH asked for this in an earlier task and it is
  discharged here: planted auras of 0.02 / 0.05 / 0.10 / 0.15 read **0.0175 /
  0.0437 / 0.0868 / 0.1295**, monotone, roughly 87% of planted.
- **Per-subject potency.** A planted USM was run on every subject, because a
  gauge must be shown to see a rim *on the subject in hand* before its silence
  there means anything: `+14.377%` (leaf-2-cpl), `+7.399%` (wrapped-text-1),
  `+2.165%` (bee-2-cpl), `+2.140%` (dry-erase), `+0.184%` (119MSDCF).

### 16.6 The result: rim does not move

Paired 95% CI is on the **raw** bright delta, which uses neither the null table
nor `edge_width`, so §16.4's third refusal does not touch the headline.

| subject | L1 averaged, A -> B | d rim corrected | paired 95% CI (raw) |
| --- | --- | ---: | --- |
| coffee-bubbles | 3.1 -> 60.6% | *REFUSED* | instrument floor |
| 119MSDCF | 0.0 -> 57.1% | -0.005% | [-0.009%, -0.003%] |
| dry-erase-marker-head-cpl | 2.2 -> 45.7% | +0.014% | [-0.260%, +0.028%] |
| bee-2-cpl | 0.0 -> 33.3% | -0.020% | [-0.075%, +0.014%] |
| leaf-2-cpl | 0.0 -> 19.4% | -0.505% | [-2.538%, +1.215%] |
| wrapped-text-1 | 0.0 -> 1.0% | +0.006% | [-0.045%, +0.102%] |

Four of five CIs span zero. The fifth, `119MSDCF`, excludes zero at **-0.005%**,
which is a twentieth of that subject's own USM response and is statistical
significance without magnitude. On `leaf-2-cpl` - ORCH's chosen subject, the
worst rim in the corpus, and the least sensitive here at n=424 - the effect is
bounded at **|d rim| < 2.54%** against a measured rim of +14.4%.

### 16.7 The dose-response, which is where this stops being one A/B

The knob's own potency varies **57-fold** across these subjects, read from each
render's banner rather than assumed. `wrapped-text-1` is a natural null: the
treatment was applied and the gate barely moved. If the knob drove the rim, rim
change would track that range.

- **|d rim| against dose: Spearman -0.400**, the wrong sign, over a rim range of
  0.005 to 0.505 points - and the 0.505 belongs to the least sensitive subject.
- **flat-region noise against dose: Spearman -0.900.**

There is a strong, monotone dose-response in these renders. It is not in the rim.

### 16.8 What the knob does do, on the same pixels

Measured with the structure-split discriminator from Part 14, unchanged, which
is commissioned on a planted denoise **and** a planted softening: `DENOISE flat
0.5000 detail 0.9983`, `SOFTEN detail 0.7313`, separation 0.2670, `NULL exactly
1.000000`. A planted softening was additionally run on **each subject's own
pixels** as a per-subject potency arm; all six read 0.7962 to 0.8697, below the
0.90 bar, so silence from this instrument is meaningful on all six.

| subject | flat (noise) | detail |
| --- | ---: | ---: |
| 119MSDCF | **0.9262** | 1.0013 |
| coffee-bubbles | 0.9538 | 1.0009 |
| bee-2-cpl | 0.9665 | 1.0047 |
| dry-erase-marker-head-cpl | 0.9709 | 1.0025 |
| leaf-2-cpl | 0.9856 | 1.0078 |
| wrapped-text-1 | 1.0020 | 1.0066 |

**Flat-region noise falls by up to 7.4%; detail energy is >= 1.0009 everywhere.**
The knob is a denoiser that costs no detail. That is a real benefit and it is
not the one that was argued for.

**The band, named per ORCH's rule of 2026-08-27.** No acuity claim may be quoted
without its band. This one is a difference of Gaussians, `sigma = 1.4` against
`2.8`, whose transfer function I computed rather than assumed and then checked
against sinusoidal gratings pushed through the same code path:

| quantity | value |
| --- | ---: |
| peak response | **0.1093 cyc/px** (empirical peak 0.109, 99.9% of analytic) |
| half-power span | 0.0658 - 0.1650 cyc/px |
| half-amplitude span | 0.0511 - 0.1922 cyc/px |

Two consequences, and the second is a caveat rather than a clearance.

**This is not the disputed band.** ORCH withdrew the licence on figures measured
at 0.30-0.35 cyc/px. That slice sits at **3.6% of this band's peak response**, so
those numbers and these are not measuring the same thing and the withdrawal does
not reach this table.

**The margin against the corpus noise boundary is thin, and I will not round it
in my favour.** ORCH states the signal/noise boundary moves 0.17 to 0.48 cyc/px
across this corpus. At the half-power definition my upper edge is 0.1650, below
the corpus *minimum* of 0.17 on every subject. At the half-amplitude definition
it is 0.1922, which **exceeds 0.17** -- so on whichever subject carries the
lowest boundary, the skirt of this band reaches into that subject's noise. The
claim is safe at the -3 dB definition and grazes at the -6 dB one. It is not
qualified per-subject, because I have not measured a per-subject boundary; that
is a gap, recorded in 16.11.

Of the six subjects here, `dry-erase-marker-head-cpl` appears on V-LINEAR's
qualified list (N=300, R=4.877 PASS at 0.30-0.40) and `coffee-bubbles` is the one
V-LINEAR reports has never been band-qualified at all -- which is also the
subject this report REFUSES on the rim axis.

**And `coffee-bubbles` sets the floor of the detail claim, so the claim was
re-run without it.** ORCH's instruction of 2026-08-27 is not to score acuity on
that subject. Its 1.0009 is the *minimum* of the detail column, so it is exactly
the value `>= 1.0009 everywhere` is pinned to. Dropping it leaves five subjects
with a minimum of **1.0013** (`119MSDCF`), so the conclusion does not merely
survive the exclusion -- **the floor rises**. The detail finding is not carried
by the unqualified subject, and nothing in it depends on that subject's number.

### 16.9 Verdict against ORCH's own falsification conditions

> "Falsified if: rim is unmoved between the two files, or moves in the wrong
> direction, or moves only by softening the edge itself rather than the aura."

**The first condition fired. Rim is unmoved**, across five measurable subjects
spanning a 57-fold range of the treatment's own potency, against a gauge with an
exactly-zero null and a demonstrated per-subject response to a planted aura.

So **rim is not a coarse-scale selection artifact that coarse-band averaging can
cut.** The mechanism ORCH argued predicts the aura should fall when coarse bands
stop selecting and start averaging; bands 1 through 5 went from 0.0% to as much
as 60.6% averaged and the aura did not move at all.

The third condition - the trap - **does not arise**, and I want to be exact
about why, because "the trap did not fire" and "I could not have seen it" are
different. Nothing moved, so there is no reduction to attribute; and
independently, the split's detail channel is >= 1.0009 on all six subjects with
a working per-subject potency arm, so there is no softening either.

**The knob is worth keeping and it is worth re-aiming.** It buys up to 7.4% less
flat-region noise for no detail, dose-tracking at Spearman -0.900. It is not a
rim fix and should not be sold as one.

### 16.10 My own defects this round

- **I amplified ORCH's over-generalisation in §15.3** instead of catching it,
  and I had the measurement that distinguishes "the floor is never reached" from
  "the gate cannot fire". Corrected in §16.3.
- **I shipped a harness whose isolation rule was evaluated per arm**, admitting
  182 sites on the control and 296 on a blur of the same image - a 63% larger
  population - which is the exact population-drift defect my own docstring warns
  about two paragraphs above the offending line. Caught by commissioning, not by
  reading.
- **I twice tried to engineer around the rise/rim coupling before measuring
  it.** The correct move was the third one: measure the coupling, fit it, and
  quote it. It is -3.85 px per unit rim and it would have inverted the sign of a
  softening claim.

### 16.11 Gaps

- `coffee-bubbles` is REFUSED on rim and contributes only to the split. It is
  the highest-dose subject at 60.6%, so the one subject where the treatment did
  the most is the one the rim gauge cannot speak to.
- `119MSDCF`'s USM potency is only `+0.184%`. Its rim null is weak evidence in
  isolation; it carries weight here because its *flat* channel moved most.
- **There is no working edge-softening detector inside the rim instrument.**
  `edge_width` failed its ladder. Softening is covered by the independent split,
  but the two do not share edges, so "rim flat and detail flat" is two
  instruments agreeing, not one instrument measuring both on identical pixels.
- The rim gauge is a *median* over edges. A rim confined to a small minority of
  edges would not show, and no per-edge tail analysis was run.
- All six subjects come from one lane's renders at one binary. I verified the
  pair, not the lane.
- ORCH's remaining hull item is already closed: `--unclamped` ran in §13.4 as
  the potency arm (+0.32% to +2.14% of band on 7 of 8). `pinned_to_hull` is
  `pyramid.rs:3252`, a **unit-test helper**, not a runtime statistic - it is not
  reachable from the CLI, so measuring it on a real subject needs a change in
  `crates/`, which is not mine to make.


---

## Part 17 - Reading notes at wind-down (2026-08-28)

Two scope notes, both required by ORCH's wind-down instruction. Neither is a new
measurement; both mark existing numbers so a later reader cannot misread them.

### 17.1 `112MSDCF` carries band claims here, in a band nobody has qualified

ORCH's instruction is that a number measured on a failing subject must be marked
rather than quietly kept. `112MSDCF` appears 23 times in this report and carries
band percentages at L1283, L1291, L1334 and L1164.

**The FAIL does not transfer, and I am not going to pretend it does.** V-LINEAR
measured `112MSDCF` at R = 1.079, 95% CI [1.040, 1.121], FAIL(noise) **at
0.30-0.35 cyc/px**. Every band number in this report is measured through
`gf_discriminate.band_rms`, a DoG(1.4, 2.8) whose peak is **0.1093 cyc/px** and
whose half-power support is 0.0658-0.1650 (Part 16 band declaration, re-derived
in `bg_band.py`). The disputed slice sits at 3.6% of my peak. Importing a
verdict measured at 0.30-0.35 into a statistic centred at 0.1093 would be the
same band-transfer error ORCH has twice asked to be called out on, and I am not
committing it in the other direction.

**But I cannot claim the subject is qualified either.** No one has measured the
signal/noise boundary for `112MSDCF` at 0.1093 cyc/px. The corpus boundary moves
0.17-0.48 across subjects; 0.1650 clears the corpus minimum at half power and
0.1922 grazes it at half amplitude. So the honest status of every `112MSDCF`
band number here is **UNQUALIFIED IN BOTH DIRECTIONS** - not vindicated by the
band mismatch, not condemned by V-LINEAR's FAIL. Ranked first in GAPS.

### 17.2 "Thirteen haloed" and "no halo is demonstrated" are both true

ORCH reports all four HALO verdicts are false positives and no halo is
demonstrated on any of the 26 masters. This report says thirteen of twenty-six
show bright overshoot hugging their edges (L1105). **These do not contradict
each other, because they are measurements at disjoint scales.**

`halo_profile.py` walks 2-120 px and takes its far reference at 400-900 px; the
refuted defect is the unmeasured 120-400 px gap, exactly where a halo's decay
separates from a lighting falloff. The rim axis here imports only `rimv6`, which
walks a contiguous +-12 px with its reference inside the same profile. There is
no gap of that kind, and there is also no ability to see anything wider than
about 12 px. This report contains 0 occurrences of `halo_profile`.

Therefore: ORCH's refutation is a statement about the wide scale and does not
reach the rim axis; and the thirteen rim failures are a statement about the
tight scale and **do not rescue `halo_profile`**. A reader must not use either
as evidence about the other. Section 11.3 already records that this instrument
was caught making the same class of false positive on itself - `foam` read
+5.014% on a rim-free control - and now REFUSES any subject whose floor exceeds
2%.
