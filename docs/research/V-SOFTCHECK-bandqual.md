# V-SOFTCHECK: band qualification of 0.30-0.35 cyc/output px

**Verdict: PARTIAL WITHDRAWAL.** My operating band is **MARGINAL** on both subjects --
it is not a noise band, but it does not clear the bar I set before running. The
`+0.0732` / `+0.0748` dex-per-doubling numbers are withdrawn as resolution claims. The
**sign survives, re-derived, in bands that qualify**, on both subjects, with every
confidence interval excluding zero.

Instrument `experiments/V-SOFTCHECK/bandqual.py`. Decision rule and kill condition
pre-registered in `experiments/V-SOFTCHECK/PREREG-bandqual.md`, committed at `11ede945`
**before any statistic was computed**. Develop path, stated explicitly as required:
`strehl.exe stack <dir> --out <x>.tiff --srgb --exposure <n>`, pin
`44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490`, all `STREHL_*`
cleared but `STREHL_CACHE_DIR`. **No `--auto-exposure`, no `--linear-srgb`, no
Lightroom at any stage of any arm.**

## 1. What was challenged, and what was actually open

V-LINEAR measured in-focus/defocused band power of **1.015, 1.043, 1.004, 1.138** over
0.20-0.48 cyc/px on `--linear-srgb --demosaic` single frames, against 2.1-3.0 for
Lightroom develops of the same frames, and concluded the band is noise on this corpus.
My entire N-invariance finding lives at 0.30-0.35, inside that interval.

I could not dismiss this by pointing at pooling. V-LINEAR's own banner already found
and fixed that: per-tile focus selection recovered **R = 2.419** at 0.20-0.25 where
whole-frame pairs read 1.188, and they report it still failing above 0.30. The pooling
defect was theirs to find and they found it. My band failed *on their data* with the
fix applied.

What was open is the develop path, which that lane states is the operative variable and
demonstrates spans 1.004 to 3.0 on the same frames. Their measurement is single frames,
linear, in cyc/px of a develop. Mine is `--srgb` merged masters, in cyc/**output** px.
So the number had to be re-taken on my path.

## 2. The instrument, and the defect it found in itself

Per tile: choose the most- and least-focused probe frame, take the ratio of band power
between them. Probes are single bracket frames rendered through `STREHL_ONLY_FRAME` at
the **identical** pipeline, tone curve and explicit gain as the merges they qualify, so
both sides of every ratio are developed identically.

**The trap, which is the entire design problem.** Choosing the in-focus frame by the
same band being measured is an order statistic: the max over 32 draws of a noise field
beats the min over 32 draws. A pure noise band would read R >> 1 and qualify itself.
Measured on a pure noise stack: **selecting on the measured band inflates R to 1.1489**.
So focus is selected on a disjoint band, 0.10-0.20.

**The defect my own null caught, which is worse and which other lanes should check for.**
The first commissioning **FAILED**: the pure-noise null read **1.3512** against a
tolerance of 1.30, and the run aborted with no verdict. Diagnosis: a frame that is
merely *brighter* carries more power in **every** band at once, so per-frame gain
variation makes gain masquerade as focus through any selection band. I had invented 3%
jitter; the **measured** spread on `113MSDCF` probes is **1.32x** (rel sd 0.0765).

> **Without per-frame gain normalisation this test reads `R = 2.3451` on a stack of
> pure noise.** That is above the bar of 2.0 I had pre-registered. An uncorrected
> version of this measurement would have *qualified a noise band as signal* and handed
> me a false PASS on my own headline.

Band power goes as gain^2 and the tile mean as gain^1, so the statistic is normalised by
the per-frame level. The null then reads 0.9959. The failure is subject-dependent and
invisible unless the jitter is measured: on `bee` the spread is only 1.06x and the
uncorrected null reads 1.1029, so a lane that commissioned on `bee` alone would never
have seen it.

### Commissioning, both directions, on each subject

| control | 113MSDCF | bee-1-cpl | truth | |
|---|---:|---:|---:|---|
| C3 noise-stack null, gain-normalised | 0.9959 | 0.9961 | 1.000 | ok |
| C3 same, **not** normalised | **2.3451** | 1.1029 | 1.000 | the defect above |
| C3 selection on the measured band | 1.1488 | 1.1489 | 1.000 | the pre-registered trap |
| C4 band-invariant null (selection moves 8.8x, measured band untouched) | 1.0019 | 1.0012 | 1.000 | ok |
| C5 known-ratio positive control | 196.0850 | 80.8614 | 195.8308 / 80.7646 | 0.1% err |
| C6 signed control | 0.1309 | 0.1427 | < 1 | ok |
| C2 aligner, planted rolls | 3/3 | 3/3 | exact | ok |

C5 commissions **magnitude**, not merely direction. C6 proves R is not bounded below by
1, so the instrument is free to report that a band does not respond -- a statistic that
can only return ">= 1" would pass every qualification ever put to it. C4 is a pixel-domain
plant: a scalar multiply would shift every band by `log10(1/s)` regardless of content and
is the kind of control that cannot fail.

## 3. The qualification ladder

R_top = in-focus/defocused band power, per-tile focus selection on 0.10-0.20,
gain-normalised, median over the top two contrast deciles -- **the exact tiles the
withdrawn numbers were measured on**. Bar: R >= 2.0 with bootstrap low > 1.5 and the
flat-tile null < 1.3.

| band | 113MSDCF | bee-1-cpl | |
|---|---:|---:|---|
| 0.05-0.10 | 208.33 | 597.13 | qualifies |
| 0.10-0.15 | 37.70 | 92.23 | qualifies |
| 0.15-0.20 | 10.02 | 17.27 | qualifies |
| 0.20-0.25 | 3.32 | 4.93 | qualifies |
| 0.25-0.30 | 1.82 | 2.32 | 113 marginal, bee qualifies |
| **0.30-0.35** | **1.55** | **1.85** | **MARGINAL on both** |
| 0.35-0.40 | 1.53 | 1.77 | marginal |

```
0.30-0.35  113MSDCF  R_top 1.5525  CI [1.4583,1.6437]  R_flat 1.1309  TOP/FLAT 1.373
0.30-0.35  bee-1-cpl R_top 1.8480  CI [1.6403,2.0347]  R_flat 1.1532  TOP/FLAT 1.603
                     interior-peak tiles only (76/90)   1.8721  CI [1.6590,2.1792]
                     selection band 0.05-0.10 instead   1.7039  CI [1.6035,1.9263]
```

**The band is not noise.** Both CIs exclude 1.0 by a wide margin, textured tiles respond
1.37x and 1.60x more than flat tiles at the same sites, and the result is stable across
two disjoint selection bands and under an interior-peak restriction. **It is also not
qualified**: 1.55 and 1.85 against a bar of 2.0. There is no cliff anywhere in the
ladder -- response decays smoothly with frequency, which is what defocus plus a rising
noise floor should look like. "Noise band" is the wrong shape for this data; **low
signal-to-noise band** is the right one.

## 3b. Attribution of the threshold, verified at source

ORCH corrected the attribution of the bar after this was measured. I verified the
correction at the primary source rather than accepting it, and it is **exactly right**:

| rule | source | boundary |
|---|---|---|
| noise vs detail | `experiments/V-LINEAR/noisefloor.py:93` | `NOISE-DOMINATED if r < 1.3 else carries real detail` |
| eligibility to be the comparison band | `experiments/V-LINEAR2/bandsignal.py:94-99` and `V-LINEAR2/PREREGISTRATION.md` sec.2 | `PASS if r >= 2.0 and CI low >= 1.5; MARGINAL if r >= 1.3; else FAIL(noise)` |

**The correction does not move my verdict, and my bar was not borrowed.** The PASS
condition I fixed at `11ede945` -- `R >= 2.0` and bootstrap low `> 1.5` -- is the same
condition `bandsignal.py` encodes, arrived at before I had read either file. Re-scored
under both rules by `experiments/V-SOFTCHECK/rescore.py`, with nothing re-measured:

| subject | band | R | 95% CI | `bandsignal.py` | `noisefloor.py` |
|---|---|---:|---|---|---|
| 113MSDCF | 0.30-0.35 | 1.5525 | [1.4583,1.6437] | MARGINAL | carries real detail |
| bee-1-cpl | 0.30-0.35 | 1.8480 | [1.6403,2.0347] | MARGINAL | carries real detail |

**Correction back to the orchestrator.** "0.30-0.35 is inside the confirmed noise region
0.25-0.48" is true of V-LINEAR's `--linear-srgb --demosaic` single frames and **false of
this lane's `--srgb` merged masters**. On my develop path the band is `MARGINAL`, not
`FAIL(noise)`: R = 1.5525 and 1.8480, and **both CIs exclude 1.3**, the noise boundary.
That is precisely the develop-dependence V-LINEAR itself flagged, so the region label
cannot be carried across develop paths without re-measuring -- which is what this
document did.

Applying `PREREGISTRATION.md` sec.2's own band-selection rule -- *"the comparison band is
the HIGHEST-frequency PASSing band"* -- to my data gives **0.20-0.25 for `113MSDCF`** and
**0.25-0.30 for `bee-1-cpl`**. Those are the two bands section 5 already re-derives in,
chosen before I had read that rule.

## 4. What is withdrawn

**`+0.0732` dex/doubling (113MSDCF) and `+0.0748` dex/doubling (bee-1-cpl) at
0.30-0.35 cyc/output px -- 17.8% and 18.8% softer -- are withdrawn as resolution
claims.** They are correctly measured band-power ratios; they are not a resolution
statement, because the band they were measured in is marginal on both subjects.

**Also withdrawn, and this one dies hardest.** Finding 4 of
`V-SOFTCHECK-N-invariance.md` -- *"cost per doubling is the same on both subjects to
within 0.002 dex across a 4.7x difference in depth"* -- **does not survive.** At the
lowest band that qualifies on both subjects (0.20-0.25) the two read **+0.0106** and
**+0.0305** dex/doubling: a factor of **2.9** apart, not 0.002 dex. That agreement was
a property of an unqualified band and I had already cautioned it must not be quoted as
a law. It should now not be quoted at all.

## 5. What survives, re-derived in qualifying bands

`experiments/V-SOFTCHECK/rederive.py`. Every band printed for both subjects in both
strata, with the qualification carried in the same table, so no row can be quoted
without it. Sign convention: positive means the **deeper** merge holds less band power.

| subject | band | R_focus | dex/doubling | 95% CI | % softer |
|---|---|---:|---:|---|---:|
| 113MSDCF | 0.20-0.25 | 3.32 | +0.0106 | [+0.0023,+0.0177] | 2.4% |
| bee-1-cpl | 0.15-0.20 | 17.27 | +0.0121 | [+0.0013,+0.0219] | 2.8% |
| bee-1-cpl | 0.20-0.25 | 4.93 | +0.0305 | [+0.0070,+0.0563] | 7.3% |
| **bee-1-cpl** | **0.25-0.30** | **2.32** | **+0.0656** | **[+0.0495,+0.0950]** | **16.4%** |

**The sign survives on both subjects, in bands that qualify, with every CI excluding
zero.** On `bee` -- the deep subject, and the one that matters for the depth
hypothesis -- the deficit is **16.4% per doubling in a band that passes qualification
at R = 2.32**. That is nearly the whole of the withdrawn 18.8%, now standing on a
qualified band. On `113MSDCF` the surviving effect is much smaller, 2.4%.

So the depth mechanism is **not** an artifact of measuring in a noise band. What the
qualification removes is the *magnitude* at 0.30-0.35 and the false precision of the
cross-subject agreement.

## 6. Noise on the same pixels

Required by standing rule and it is load-bearing here. Flat two deciles, same tiles,
same bands, same arms (dex; negative = the deeper arm holds MORE power):

```
113MSDCF   -0.0521  -0.0708  -0.1051  -0.1348  -0.1446  -0.1516  -0.1532
bee-1-cpl  -0.0280  -0.0403  -0.0371  -0.0384  -0.0469  -0.0450  -0.0389
```

**The deeper arm is noisier at every band on both subjects, while holding LESS power in
textured tiles at fine bands. A pure noise difference cannot change sign between
strata.** So the textured deficit is not the noise term, and the noise term biases
*against* the finding: the deeper arm receives a noise bonus in textured tiles too, so
the true scene deficit is larger than the measured one. This also means no arm can pass
by getting quieter -- on blotch alone the plain mean wins while destroying 78% of the
sharpness, and that trap is closed here by construction.

## 7. The confound that remains, and it is not resolved

The deficit rises monotonically with frequency. Band signal-to-noise falls monotonically
with frequency. **A real blur and a difference in noise policy predict the same monotone
rise**, because both are frequency-ordered. The qualification narrows this but does not
settle it.

What is now established: the effect is largest exactly where the band is least
trustworthy (17.8-18.8% at R = 1.55-1.85), and it remains significant where the band is
trustworthy (16.4% at R = 2.32 on bee, 2.4% at R = 3.32 on 113MSDCF). Anyone quoting a
depth number must quote its band's R with it.

## 8. Limits

- **Two subjects, one rung each.** `flower-bud-alone-cpl` (N=205) is unqualified and
  unmeasured. Nothing here is a corpus claim.
- **Pin-scoped.** Measured at `9b05d0b7`, now 325 commits behind HEAD. Whether any of
  this survives the build lane's exposure fix and merge changes is unmeasured.
- **bee's probes stop at frame 200 of 299**, because probes 225-298 register 250-330 px
  out, past the T/2 trust limit. Tiles whose true focus lies beyond 200 have their peak
  clamped to the ladder edge, which *understates* focus response. Restricting to
  interior-peak tiles moved R from 1.8480 to 1.8721, so the bias is small and in the
  conservative direction.
- The qualification is measured on **single frames**; the deficit is measured on
  **merges**, whose noise floor is lower. The qualification is therefore a conservative
  proxy for the merged band's SNR, not a direct measurement of it.
