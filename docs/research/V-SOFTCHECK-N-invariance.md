# V-SOFTCHECK: N-invariance at depth

**The pooled statistic reads zero because two defects cancel.** Everything below was
measured at the SHIP-V4 pin `44C2F2CD2E5B2894`, matched development gain audited on
every arm, sharpness and noise on the same pixels, band and frame count named.

## 1. Summary

| # | finding | status |
|---|---|---|
| 1 | The standing `0.114` on `113MSDCF` **survives** independent re-derivation | CONFIRMED |
| 2 | My own first re-measurement read `-0.0007` dex and I nearly retracted it. It was diluted, not clean | SELF-CAUGHT |
| 3 | At depth, `bee-1-cpl` N=149->299 at matched range: **N=299 is 18.8% softer** | MEASURED |
| 4 | Cost per doubling of N is the same on both subjects to within **0.002 dex** across a 4.7x difference in depth | MEASURED |
| 5 | The deeper merge is **noisier**, not cleaner, which removes the confound that forced my earlier refusal | MEASURED |
| 6 | The orchestrator's third arm (N held, step doubled) **supports** the dilution model | MEASURED, confounded |
| 7 | Acceptance gate delivered, commissioned in both directions with pixel-domain plants | DELIVERED |

## 2. The thing that nearly cost the project a true result

I re-measured my own standing `0.114` with an independently written instrument that
compares the two merges **directly**, tile by tile, rather than each against a shared
reference. Over a uniform 486-tile grid it read:

```
113MSDCF  N=32 vs N=63, 0.30-0.35 cyc/output-px
  median-of-ratios  -0.0007 dex   CI [-0.0090,+0.0099]   49.5% of tiles
```

Nothing. On the same two files the published number says `+0.0748` dex. The 63-frame
arm is **byte-identical** to the one the `0.114` was measured on
(`sha256 3C097FBA746B9955...`), so the pixels were never in question.

Stratifying the *same* uniform grid by scene contrast explains it completely:

| decile (low-band energy) | 0.30-0.35 dex | % tiles N=32 sharper |
|---|---:|---:|
| 0 flattest | **-0.1708** | 0.0% |
| 1 | -0.1145 | 0.0% |
| 2 | -0.0560 | 9.1% |
| 3 | -0.0293 | 20.5% |
| 4 | -0.0042 | 43.2% |
| 5 | +0.0096 | 54.5% |
| 6 | +0.0485 | 86.4% |
| 7 | +0.0557 | 95.5% |
| 8 | +0.0590 | 90.9% |
| 9 most textured | **+0.0815** | 93.5% |

Monotone, and it **reverses sign**. The deeper merge loses detail where there is
detail and adds energy where there is none. Pooled, they cancel to zero.

Top two deciles: `+0.0712 dex, 92.2% of tiles`, against the old instrument's
`+0.0775 dex, 93.7%` on its own tile set, against the published `+0.0748 dex`. The
old tile set was the top 300 by low-band energy -- a high-contrast set. **It was
right, and my uniform grid was the broken instrument.**

This is the trap the project has now hit four times, in its purest form: *a statistic
that improves when the image gets worse*. My pooled reading of `-0.0007` would have
certified a merge carrying two defects as clean, and I would have retracted a true
finding on the strength of it.

## 3. Depth: the number that matters

`bee-1-cpl`, the deepest capture, **matched focus range 0-298 on both arms**, so there
is no range confound and no focus mask is needed. This is the direct analogue of
113MSDCF's N=32 -> N=63.

```
A1'  Q (N=149, step 2)  ->  R (N=299, step 1)     range HELD 0-298
  0.30-0.35 cyc/output-px, top two contrast deciles, 99 tiles
    +0.0748 dex   CI [+0.0651,+0.0932]   86.9% of tiles
    ==> N=299 is 18.8% SOFTER than N=149 on the same scene
  flat two deciles, same pixels
    -0.0450 dex   ==> N=299 holds 10.9% MORE energy where there is no detail
  POOLED over all 459 tiles:  +0.0352 dex   (diluted, do not quote)
```

**Cost per doubling of N at matched range:**

| subject | N | doublings | dex per doubling | % softer | tiles |
|---|---|---:|---:|---:|---:|
| `113MSDCF` | 32 -> 63 | 0.98 | **+0.0732** | 14.9% | 93.2% |
| `bee-1-cpl` | 149 -> 299 | 1.00 | **+0.0748** | 18.8% | 87.0% |

Two subjects, a 4.7x difference in absolute depth, agreeing to **0.002 dex per
doubling**. That is a stronger regularity than I expected and it is two points, not a
curve; N=100 and N=200 rungs and `flower-bud-alone-cpl` (N=205) are not measured.

## 4. The spectra separate the two defects

Median log10 ratio, fewer-N over more-N, same pixels, `bee` A1':

| tiles | 0.05-0.10 | 0.10-0.15 | 0.15-0.20 | 0.20-0.25 | 0.25-0.30 | 0.30-0.35 | 0.35-0.40 |
|---|---:|---:|---:|---:|---:|---:|---:|
| flat 2 deciles | -0.0280 | -0.0403 | -0.0371 | -0.0384 | -0.0469 | -0.0450 | -0.0389 |
| top 2 deciles | -0.0151 | -0.0163 | +0.0121 | +0.0307 | +0.0659 | **+0.0748** | +0.0662 |

- **Textured tiles: the deficit rises monotonically with frequency.** That is what
  losing resolution looks like. A gain error or a tone difference would be flat.
- **Flat tiles: the excess is roughly constant across all seven bands.** Broadband and
  scene-free, i.e. *noise*, not mottle -- mottle would be weighted to low frequency.

## 5. This removes the confound that forced my earlier refusal

I previously refused a verdict because the obvious alternative explanation was:
*more frames -> less noise -> less band power -> reads as softening*. That argument
requires the deeper merge to be **cleaner**.

Measured: on flat tiles the deeper merge carries **10.9% more** band power on `bee` and
**48% more** on `113MSDCF`, broadband. The deeper merge is **noisier**. The noise term
moves in the wrong direction to explain the textured-tile deficit, so the deficit is
not a noise artifact. The refusal is lifted on evidence, not on preference.

This is also positive evidence for a selection mechanism, and it is measured where no
scene content can be responsible: a merge that *averaged* would get cleaner with N. One
that *elects* on a noisy statistic gets noisier with N, because the winner is a maximum
over more draws.

## 6. The orchestrator's third arm

`A3`: N held (150 vs 149), focus step doubled. Same subject, same merge, same chain
length -- N is removed entirely.

```
P (N=150, step 1, range 0-149)  ->  Q (N=149, step 2, range 0-298)
  0.30-0.35, top two deciles:  -0.1156 dex  CI [-0.1519,-0.0904]   9.1% of tiles
  ==> the COARSER-STEP arm is 23.4% SHARPER
  flat two deciles: +0.0014 dex  -- noise-matched by construction, as designed
```

This is the direction the dilution model predicts and nothing about frame count can
explain it. **It is confounded**, exactly as I pre-registered: the arms differ in
range, and the wider-range arm covers more depth, which favours it for reasons
unrelated to dilution. The NEAR-masked pooled read of the same arm was `-0.0696` dex --
smaller, same sign. **NEAR mask intersected with contrast deciles was not measured**
and is the single most valuable missing number in this document.

`A3` does disfavour **alignment drift** as the mechanism: both arms stack ~150 frames,
so cumulative chain length is equal, and the arm spanning *more* physical depth -- and
therefore more accumulated warp -- is the **sharper** one.

## 7. Controls

**Functionals** (`d113recon.py`). The published number is a ratio of medians; mine is
a median of per-tile ratios. Both were commissioned on real band-power arrays:

```
key non-trivial: 300 distinct values, spread 0.469 dex
NULL identical arm    mor +0.000000   rom +0.000000    (both must be 0)
SCALE uniform x1.10   mor +0.041393   rom +0.041393    (both must be +0.041393)
PLANT median-1 ratio  mor +0.000000   rom +0.012570    (true median ratio 1.0000)
```

The third is the load-bearing one: a per-tile ratio field whose true median is exactly
1.000 by construction but correlated with the denominator. The median-of-ratios
recovers the truth; the ratio-of-medians reports `+0.0126` dex of pure denominator
effect. So the published functional does carry a denominator bias -- but at `0.0126`
dex it accounts for a sixth of the effect, not the effect.

**Contrast cut** (`dstrat.py`). Mottle is low-frequency and the cut variable is
low-frequency, so the deep merge could in principle inflate its own cut variable:

```
cut variable spans 5.14 dex; arms differ on it by 0.0520 dex  (1.0% of the span)
rank agreement between arms: pearson r = 0.99364
frac   cut on R (N=299)        cut on Q (N=149)
0.10   +0.0779  82.6%          +0.0869  84.8%
0.20   +0.0752  87.0%          +0.0824  89.1%
0.30   +0.0763  86.2%          +0.0779  88.4%
0.40   +0.0774  88.0%          +0.0779  88.6%
```

Cutting on the **shallow** arm, which cannot be contaminated by the deep merge's own
mottle, gives a **larger** effect. The reported number is the conservative one.

**Gate** (`ninv_gate.py`), plants applied to pixels and pushed through the whole
statistic:

```
live arms                +0.071553 dex
NULL same arm            +0.000000 dex   (exact)
DEGRADE blur sigma 1.0   +1.842484 dex   (mean |dpx| 585.8)  -> FAIL
IMPROVE unsharp +0.7     -0.342106 dex   (mean |dpx| 410.1)  -> PASS
```

The first version of this commissioning scaled the band-power array by a constant,
which shifts the statistic by exactly `log10(1/s)` whatever the image contains. That is
arithmetic that cannot fail -- the short-circuited-control failure this project has now
seen three times -- and it was replaced before any verdict was formed.

## 8. Deliverable: the acceptance criterion

`experiments/V-SOFTCHECK/ninv_gate.py`, callable by the re-certification harness:

```python
r = ninv_gate.evaluate(fewer_tiff, more_tiff, n_fewer, n_more, subject="bee-1-cpl")
assert r["verdict"] == "PASS", r["why"]
```

**Criterion.** At matched focus range, `depth_cost` -- the median over the top two
contrast deciles of `log10(S_fewer / S_more)` at 0.30-0.35 cyc/output-px -- must not
exceed **+0.0200 dex per doubling of N**. That is 3.5x below both standing baselines
and 1.4x above the widest measured CI half-width, so a pass is distinguishable from the
present state rather than merely inside the error bar.

**Current state: both subjects FAIL**, at `+0.0732` and `+0.0748` dex per doubling.

The gate refuses to be gamed two ways. It reports `flat_excess` on the same pixels and
**never pools it** with the textured number, because pooling is what read zero in §2.
And it reports `absolute_more`, the deep arm's own textured band power, because a fix
could otherwise pass by making the shallow arm worse. It hard-errors on an exposure
mismatch between arms before computing anything.

## 9. What is not established

- **NEAR mask intersected with contrast deciles.** The `dmeasure.py` npz dump was
  patched in but never executed, so the mask was not available here. `A3` is therefore
  reported both unmasked (`-0.1156`) and, from the earlier run, NEAR-masked but pooled
  (`-0.0696`). Neither is the number I want.
- **Two subjects, two rungs.** N=100 and N=200 on `bee`, and
  `flower-bud-alone-cpl` (N=205), are not measured. The agreement to 0.002 dex per
  doubling is two points and must not be quoted as a law.
- **Mechanism.** This lane measures that depth costs sharpness and that the deeper
  merge is noisier. It does not prove the normalising-sum dilution model. `A3`
  supports it and disfavours alignment drift; it does not exclude a third cause.
- **Magnification.** Inter-arm registration is a global integer shift (up to 36 px
  between `bee` arms). Residual differential magnification is uncorrected.
- Focus breathing on `bee` is large: probe-to-merge shifts run to 60 px and drift
  smoothly with bracket index, and probes at index >= 225 cannot be registered to the
  merge by global phase correlation at all. The alignment lane should have this.

## 10. Provenance

Instruments, all independently written for this lane:
`d113measure.py` (direct arm-to-arm), `d113recon.py` (functional reconciliation and
contrast stratification), `dstrat.py` (depth read with cut-robustness controls),
`ninv_gate.py` (the acceptance gate). Renders by `drender.py` / `drender113.py` at the
pin, `--srgb` with an explicit `--exposure` on every arm; `--auto-exposure` is
forbidden here because it solves a different gain per arm and the statistic is linear
in gain.

Machine-readable: `dilut/113MSDCF/d113recon.json`, `dilut/bee-1-cpl/dstrat.json`,
`dilut/ninv_gate.json`.
