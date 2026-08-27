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
