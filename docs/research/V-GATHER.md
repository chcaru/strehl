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
