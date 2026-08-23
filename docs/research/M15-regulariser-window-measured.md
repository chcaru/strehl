# M15 — does the focus-measure window optimum survive the merge regulariser?

**Status:** measured. Answers SYNTHESIS §10 open question 17.
**Experiment:** `experiments/m15-regulariser-window/` — chain script, independent analyser, committed CSVs.
**Reproduce:** `experiments/m15-regulariser-window/run-m15.ps1`, then `python m15_analyse.py --out data/analysis.txt`.
**Pre-registered before any result was read:** `experiments/m15-regulariser-window/PREREGISTRATION.md`, commit `645a337`.
**Harness:** M13's, **unmodified**. `crates/**` was not touched; no code was written for this milestone.

Every claim below carries a label. `MEASURED` = a number this milestone
produced. `VERIFIED` = a number produced twice through disjoint paths.
`DERIVED` = follows from a stated rule applied to measured numbers.
`ARGUED` = a mechanism I believe and have not isolated. `UNVERIFIED` = a
belief I am flagging so nobody quotes it as fact.

---

## The one-paragraph answer

**The w13 recommendation survives, and it survives everywhere the project would
plausibly operate.** Across regulariser widths 1, 3, 5, 9, 13, 17, 25 and 33 the
window argmin over 30 occluding-edge cells is **13 or 14 — always `interior`,
never an endpoint** — and the DN penalty for shipping M13's w13 instead of the
per-width optimum is **0.000–0.121 DN**, against a pre-registered primary
threshold of 0.87 DN. At the project's reference regulariser width 17 the
penalty is **0.050 DN**. The hypothesis that the two mechanisms are redundant,
and that the optimum should therefore move narrower, is **refuted on the
aggregate**. But it is refuted in an informative way, and the honest headline is
not "nothing happens": the aggregate is flat because **two real, opposite,
cell-level movements cancel**. On cells whose only problem is variance the
substitution is not merely 1:1 but **super-unit — s ≈ 1.7** — and on the
`horizontal` edge geometry **10 of 10 cells move narrower**, exactly as
predicted. On the `vertical` geometry 6 of 10 move **wider**, and the two
cancel. The window's job at an occluding boundary is not the job the regulariser
does, so buying variance reduction elsewhere does not buy the window's optimum
away.

---

## 0. Provenance and the guards that had to pass first

### 0.1 The corpus was not touched `VERIFIED`

Audited before and after, by two disjoint methods, with `-Force`.

```powershell
# harness (before, and again after the whole chain)
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
..\m13-window-depth\target\release\m13-window-depth.exe audit
# independent
Get-ChildItem -LiteralPath $r -Recurse -File -Force |
  Measure-Object -Property Length -Sum
```

| root | files | bytes |
| --- | ---: | ---: |
| `C:\dev\macro` | 18530 | 286,893,514,060 |
| `D:\macro-dark-frames` | 242 | 8,179,392,512 |
| `D:\personal\macro` | 632 | 18,194,001,522 |

Before and after are byte-identical strings (`data/audit-before.txt` vs
`data/audit-after.txt`, `data/audit-before-powershell.txt` vs
`data/audit-after-powershell.txt`), and the totals match M13's published
figures exactly. `MEASURED`

### 0.2 Gate A — M13 reproduces, byte for byte `VERIFIED`

SYNTHESIS §5 item 15 requires reproducing one of M13's published numbers before
re-analysing its design. I did better than that by accident of the harness being
deterministic: **re-running M13's exact command line reproduced M13's committed
CSVs bit for bit.**

```powershell
Get-FileHash data\repro-edge-109MSDCF.csv -Algorithm SHA256
Get-FileHash ..\m13-window-depth\data\edge-109MSDCF.csv -Algorithm SHA256
```

| stack | SHA-256 | bytes | identical |
| --- | --- | ---: | --- |
| 109MSDCF | `5a35b7e6ae7c14acbaccea08d00465fa19f02696913e02badbd011e0922951e4` | 231,241 | **yes** |
| 119MSDCF | `6f5f89c82e9517d35fa8db3d3e76ddace616bda5405619068ebecd83385a0409` | 233,210 | **yes** |

And M13's headline recovers from those bytes through a **separately written**
analyser (`m15_analyse.py`, written before the sweep ran, committed `97cc879`):

| quantity | target (M13) | recovered | label |
| --- | --- | --- | --- |
| argmin mean regret, 30 step>0 cells | w13, 3.171 DN | **w13, 3.171 DN** | `interior` |
| argmin worst regret, 30 step>0 cells | w13, 12.111 DN | **w13, 12.111 DN** | `interior` |
| argmin, 6 step=0 cells | w40, 0.000 DN | **w40, 0.000 DN** | `ENDPOINT` |

**Gate A: PASS.** `VERIFIED`

**Disjointness, stated plainly (§5 item 20).** This is a *consistency check on my
harness*, not independent evidence for M13. It is the same binary reading the
same RAW files with the same seeds, so byte-identity was close to guaranteed and
proves only that I invoked it correctly. The parts of M15 that are **disjoint**
from M13's measurements are: every row at `width ≠ 1` (34,560 of 38,880), the
four window radii M13's ladder omits (**w4, w7, w14, w16**), and the two seeds
M13 did not use (`13371337`, `90210`). Everything in §§2–6 below rests on those.
The one place I re-use M13's own bytes is §7.3, and it is labelled there.

### 0.3 Gate B — the regulariser is switched on and is doing work `VERIFIED`

**B1, against M2's published pair.** `ring-1-3` merged-noise excess on
109MSDCF ROI `2272,1344,256,256`:

| regulariser width | N | M2 published |
| ---: | ---: | ---: |
| 1 | **1.2527×** | 1.2527× |
| 17 | **1.0737×** | 1.0737× |

Exact to 4 dp. `data/xcheck-109MSDCF.txt`. `VERIFIED`

**B2, across the whole M15 regulariser ladder**, median over M11's four
committed flat ROIs per stack:

| stack | g=1 | g=3 | g=5 | g=9 | g=13 | g=17 | g=25 | g=33 | g=49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 109MSDCF `ring-1-3` | 1.2773 | 1.3856 | 1.1924 | 1.1014 | 1.0807 | **1.0748** | 1.0724 | 1.0717 | 1.0735 |
| 119MSDCF `ring-1-3` | 1.4177 | 1.4785 | 1.2950 | 1.1815 | 1.1438 | **1.1202** | 1.0911 | 1.0806 | 1.0795 |

Registered requirement: `N(17) < N(1)` for `ring-1-3` by ≥ 0.10 ratio units.
Achieved 0.2025 (109) and 0.2975 (119). **PASS.** `MEASURED`

**An unregistered positive control fell out of this.** N gets *worse* at g=3
than at g=1 on both stacks (1.2773 → 1.3856; 1.4177 → 1.4785) before improving.
That independently reproduces SYNTHESIS fact 36 — M9's finding that a narrow
regulariser is *actively harmful* — on a different measure, a different harness
and a different stratum. I did not register it and I am not resting anything on
it, but it is the strongest evidence in this milestone that the regulariser axis
is wired to the mechanism it claims to be wired to. `MEASURED`

### 0.4 Gate C — `W_bleed`'s blind spot, asserted rather than caveated `MEASURED`

M13 §2.5 item 1 discloses that `W_bleed` cannot see a selector electing a
*compromise* frame between two layers. §5 item 26 says assert a claimed defect,
do not caveat it. Two assertions:

1. **Synthetic**, in the harness self-test (27/27 passed, `data/selftest.txt`):
   a planted compromise election at radii 4, 12, 30 gives `bleed = 0.0` while
   `mis = 3.0 / 11.0 / 29.0`. The blind spot is exact, not approximate.
2. **On M15's own real data**: searching all 38,880 rows for pairs where
   `bleed_fg` collapses > 5 px while `excess_dn` *rises* > 2 DN finds
   **1,935 instances**. The most extreme:

   | width | cell | w_a | w_b | bleed_a | bleed_b | exc_a | exc_b |
   | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
   | 5 | 109MSDCF/vertical/s32 | 6 | 40 | 19.00 px | **0.78 px** | 25.84 DN | **32.12 DN** |
   | 9 | 109MSDCF/vertical/s32 | 7 | 33 | 18.75 px | **0.58 px** | 23.15 DN | **27.25 DN** |

   Reading `W_bleed` alone would call w40 nearly halo-free while it is in fact
   6.3 DN *worse*. Only the oracle-referenced `E_excess` sees through it — which
   is why `E_excess` is the registered primary and `W_bleed` is not. **PASS.**

### 0.5 Gate D — the placebo `MEASURED`

Disjoint seed halves `{20260823, 771117}` vs `{4242424, 13371337, 90210}`, at
each width, same everything else. If the argmin wanders between disjoint seed
sets, an argmin shift across widths means nothing.

| width | 1 | 3 | 5 | 9 | 13 | 17 | 25 | 33 | 49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| w* half A | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| w* half B | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| \|shift\| | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

**Placebo shift: 0 window steps at every one of the 9 widths.** The design's
null movement is exactly zero, so a ±1 movement across widths is real signal —
it is simply a *small* one. **PASS.** `MEASURED`

### 0.6 The ROI trap, closed `VERIFIED`

`run-m11.ps1` does not list the ROIs in M11's committed CSVs. M15's noise ROIs
came in via M13's `run-m13.ps1`, which took them from the committed data. I
checked all eight directly against `m11-focus-bakeoff/data/noise-*.csv`:

| stack | ROI | M11 `single_sigma` | M15 `single_sigma` |
| --- | --- | ---: | ---: |
| 109MSDCF | `2272,1344,256,256` | 28.2007 | 28.2007 |
| 109MSDCF | `2496,432,256,256` | 29.9800 | 29.9800 |
| 109MSDCF | `2656,1504,256,256` | 28.5771 | 28.5771 |
| 109MSDCF | `320,1344,256,256` | 27.5739 | 27.5739 |
| 119MSDCF | `2704,1664,256,256` | 53.0804 | 53.0804 |
| 119MSDCF | `2896,1968,256,256` | 50.8408 | 50.8408 |
| 119MSDCF | `3056,1568,256,256` | 48.9754 | 48.9754 |
| 119MSDCF | `3056,416,256,256` | 43.2042 | 43.2042 |

Same pixels, same numbers to 4 dp. **PASS.**

> **A correction to the flat-ROI discriminator as it is usually quoted.** The
> familiar "flat ROI has `single_sigma` ≈ 28–30 DN" is **109MSDCF-specific**.
> M11's own committed data puts 119MSDCF's four flat ROIs at **43.2–53.1 DN**.
> Applying the 109 band to 119 would reject four correct ROIs. `MEASURED`

### 0.7 One disclosure

A timing probe (`data/_probe.csv`, one cell × 22 measures × 6 widths) was run
before the pre-registration to size the sweep, and **deleted without any column
being read**. It informed only the cost estimate. This is recorded in
PREREGISTRATION.md §1.

---

## 1. The design, and the one thing it had to get right

**Grid.** 2 stacks × 3 occluding-edge geometries × 6 depth steps (0, 2, 4, 8,
16, 32) × **24 windows** × **9 regulariser widths** × **5 seeds** = **38,880
measurements**, against M13's 7,200.

**Window ladder (24).** M13's twenty — 0, 1, 2, 3, 5, 6, 8, 9, 10, 11, 12, 13,
15, 17, 18, 20, 23, 26, 33, 40 — plus **w4, w7, w14, w16**. M13's ladder omits
w14, so its "w13" was an argmin over a ladder *that cannot distinguish w13 from
w14*. Endpoints are unchanged (w0, w40) so `interior`/`ENDPOINT` labels stay
comparable with M13's.

**Regulariser ladder (9).** 1, 3, 5, 9, 13, 17, 25, 33, 49. Justification, all
pre-registered: **1** is M13's setting and my control; **3, 5** sit in the region
M9 found actively harmful (fact 36); **9** and **17** are the points M2/M9/M11/M13
used, and **17 is the project's reference operating point**; **13, 25** bracket
it; **33, 49** stress the region past fact 42's selectivity decline. All widths
odd — the harness rejects even ones.

**Seeds (5).** M13's three (`20260823`, `771117`, `4242424`) plus `13371337`,
`90210`.

**The one thing the design had to get right.** The harness's tile margin is
`max_w (w−1)/2 + max_support + max_blur_radius`, so it depends on the *widest
regulariser in the invocation*. Running each width in its own invocation would
have given every width a different tile and therefore a different noise
realisation — a nuisance factor **perfectly confounded with the treatment**. So
all 9 widths run in **one invocation per (stack, seed)**: every width sees the
identical plant, the identical noise draw and the identical focus volume. A
paired design. The price is that the sweep's `width = 1` rows are not
bit-identical to M13's (margin 106 px vs M13's 82 px), which is precisely why
Gate A is a *separate* replication run reproducing M13's command line exactly.

---

## 2. The surface — the argmin at every regulariser width `MEASURED`

Stratum: rows filtered to `width == g`; cell = `(stack, shape-without-tile-coordinate, step)`;
value = mean of `excess_dn` over the 5 seeds; regret vs the per-cell minimum
**taken within that column**.

### 2.1 The 30 cells with a depth step — the decision

| width g | radius | w*(mean) | label | mean regret | w*(worst) | label | worst regret | regret @ w13 | **Δ13** |
| ---: | ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 0 | **13** | `interior` | 3.284 | 13 | `interior` | 11.899 | 3.284 | **0.000** |
| 3 | 1 | **14** | `interior` | 3.384 | 13 | `interior` | 13.646 | 3.417 | **0.033** |
| 5 | 2 | **13** | `interior` | 3.304 | 14 | `interior` | 16.301 | 3.304 | **0.000** |
| 9 | 4 | **13** | `interior` | 3.396 | 14 | `interior` | 17.865 | 3.396 | **0.000** |
| 13 | 6 | **14** | `interior` | 3.262 | 15 | `interior` | 18.028 | 3.342 | **0.080** |
| **17** | 8 | **14** | `interior` | 2.970 | 16 | `interior` | 18.056 | 3.020 | **0.050** |
| 25 | 12 | **13** | `interior` | 2.166 | 16 | `interior` | 15.956 | 2.166 | **0.000** |
| 33 | 16 | **14** | `interior` | 1.722 | 14 | `interior` | 10.670 | 1.842 | **0.121** |
| 49 | 24 | **8** | `interior` | 2.143 | 5 | `interior` | 8.766 | 2.694 | **0.551** |

**Every argmin is `interior`.** There is a genuine turnover at every regulariser
width — the window axis never degenerates into "wider is always better" on a
scene with a depth discontinuity, no matter how much smoothing the regulariser
supplies. That is a stronger statement than M13 could make, because M13 only
tested one regulariser setting.

`Δ13(g) = meanregret(w13, g) − meanregret(w*(g), g)` is the registered decision
quantity: the DN the project pays for shipping M13's w13 at that regulariser
width. It is realisable — no oracle is needed to choose w13 — which is the point
of §5 item 27.

### 2.2 The same table on M13's three seeds only `MEASURED`

| width | 1 | 3 | 5 | 9 | 13 | 17 | 25 | 33 | 49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| w* (5 seeds) | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| w* (M13's 3 seeds) | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| Δ13 (3 seeds) | 0.000 | 0.026 | 0.000 | 0.000 | 0.084 | 0.045 | 0.000 | 0.122 | 0.566 |

Identical argmins at all 9 widths. The two extra seeds change nothing.

### 2.3 The same table on M13's 20-window ladder only `MEASURED`

| width | 1 | 3 | 5 | 9 | 13 | 17 | 25 | 33 | 49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| w* on the 24-window ladder | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| w* on M13's 20-window ladder | 13 | 13 | 13 | 13 | 13 | 13 | 13 | 15 | 8 |

**This is the answer to the question the brief asked about M13's ladder
resolution.** M13's ladder cannot express w14, so on M13's ladder the argmin
reads "w13" at six of the nine widths where the finer ladder says w14. The
difference is worth **0.033–0.121 DN** — i.e. M13's ladder gap costs nothing
decision-relevant, but it *was* concealing a one-step movement. The finer ladder
was worth adding and it did not change the ruling.

### 2.4 The null: the 6 zero-step cells `MEASURED`

| width g | w*(mean) | label | regret @ w13 |
| ---: | ---: | --- | ---: |
| 1 | 40 | `ENDPOINT` | 5.762 |
| 3 | 40 | `ENDPOINT` | 3.997 |
| 5 | 40 | `ENDPOINT` | 3.094 |
| 9 | 40 | `ENDPOINT` | 2.463 |
| 13 | 33 | `interior` | 1.847 |
| 17 | 26 | `interior` | 1.296 |
| 25 | 20 | `interior` | 0.454 |
| 33 | 16 | `interior` | 0.042 |
| 49 | 10 | `interior` | 0.000 |

The registered null (fact 61: with no depth step, wider is always better, so w*
must be the `ENDPOINT` w40) **appears to fail above g = 9**. Outcome O7 required
me to diagnose that before believing anything else. §3 does.

---

## 3. The null did not fail — the *label* did `MEASURED`

The zero-step regret ladder, in full:

| w | g=1 | g=9 | g=13 | g=17 | g=25 | g=33 | g=49 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 13 | 5.7621 | 2.4629 | 1.8474 | 1.2961 | 0.4536 | 0.0425 | 0.0002 |
| 20 | 1.9990 | 0.2921 | 0.1716 | 0.0723 | **0.0000** | 0.0002 | 0.0002 |
| 26 | 0.8248 | 0.0855 | 0.0235 | **0.0002** | 0.0000 | 0.0002 | 0.0002 |
| 33 | 0.1448 | 0.0447 | **0.0003** | 0.0002 | 0.0000 | 0.0002 | 0.0002 |
| 40 | **0.0000** | **0.0000** | 0.0003 | 0.0002 | 0.0000 | 0.0002 | 0.0002 |

The curve does not turn over. It **flattens to the fourth decimal place** and
the argmin then lands wherever floating-point rounding puts it.

| width | w* | regret @ the w40 endpoint | seed sd | sd of a 6-cell mean | verdict |
| ---: | ---: | ---: | ---: | ---: | --- |
| 13 | 33 | 0.0003 DN | 0.0915 | 0.0167 | **tie — label artefact** |
| 17 | 26 | 0.0002 DN | 0.0813 | 0.0148 | **tie — label artefact** |
| 25 | 20 | 0.0000 DN | 0.0715 | 0.0131 | **tie — label artefact** |
| 33 | 16 | 0.0002 DN | 0.0622 | 0.0113 | **tie — label artefact** |
| 49 | 10 | 0.0002 DN | 0.0622 | 0.0113 | **tie — label artefact** |

At every width the endpoint's regret is **two orders of magnitude below a
3-sigma bar** on the seed noise. **Fact 61 survives intact.** What changed is
that with the regulariser on, "wider is better" stops *paying* — the benefit
saturates rather than reversing. `MEASURED`

> **This is a defect in the `interior`/`ENDPOINT` rule as currently written, and
> I am reporting it rather than working around it.** §5 item 25 correctly refuses
> to call an endpoint argmin an optimum. It says nothing about the opposite
> error: an **`interior` label on a plateau is not a turnover either**. An
> argmin label is only meaningful when the argmin is separated from its
> neighbours — and in particular from the endpoints — by more than the noise
> floor. Proposed as new discipline item 30. `ARGUED`

---

## 4. Where the substitution actually happens `MEASURED`

This is the mechanism result, and it is the reason the aggregate is flat.

`H_sub` (the brief's hypothesis) predicts `w*(g) = w*(1) − (g−1)/2`, slope
**s = 1**: each unit of regulariser radius buys away one unit of window radius.
`H_none` predicts **s = 0**.

| stratum | g=1 | g=3 | g=5 | g=9 | g=13 | g=17 | g=25 | g=33 | g=49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| step > 0 — variance **and** halo | 13 | 14 | 13 | 13 | 14 | 14 | 13 | 14 | 8 |
| step = 0 — variance **only** | 40 | 40 | 40 | 40 | 33 | 26 | 20 | 16 | 10 |

OLS of `w*` on regulariser radius `r = (g−1)/2`:

| stratum | ladder | **s** | r² |
| --- | --- | ---: | ---: |
| step > 0 | all 9 widths | 0.160 | 0.449 |
| step > 0 | g ≤ 33 | **−0.029** | 0.096 |
| step > 0 | g ≤ 17 (ship range) | **−0.095** | 0.284 |
| step = 0 | all 9 widths | 1.441 | 0.937 |
| step = 0 | g ≤ 33 | **1.720** | 0.943 |
| step = 0 | g ≤ 17 (ship range) | **1.695** | 0.796 |

Registered endpoint contrast (g=1 vs g=17): `s = (13 − 14)/8 = −0.125` on the
decision stratum.

**Read this carefully, because it is the whole milestone.**

- On the stratum where the window's *only* job is variance reduction, the
  substitution is real, large, and **stronger than 1:1 — s ≈ 1.7** with r² 0.94.
  The hypothesis is not just correct there, it understates the effect.
- On the stratum that carries an occluding edge, **s ≈ 0** — indistinguishable
  from `H_none`, and if anything faintly negative.

**This doubles as the positive control that the design can resolve a moving
optimum.** Same ladder, same seeds, same objective, same regret rule, same
harness invocation — and on the null stratum the argmin travels from w40 to w10.
So the flat result on the decision stratum is not a failure of sensitivity, and
§5 item 24's warning ("a plant that cannot express the failure mode is not
evidence about it") is answered by demonstration rather than by assertion: this
plant **does** express the failure mode, on the cells where the mechanism
applies. `MEASURED`

**The mechanism, argued not isolated.** Tenengrad computes `|∇L|`, box-means it
over radius `w`, and *then* divides pointwise by `σ(L(p))`. The regulariser
box-means the *finished* focus field. Both are box means over nearly the same
field, so on a scene whose only difficulty is noise they are near-perfect
substitutes — which is what s ≈ 1.7 says. At an occluding boundary the window is
not buying variance reduction; it is buying **contrast localisation across a
discontinuity**, and the regulariser cannot supply that because it operates
*after* the per-frame focus field has already been formed and cannot
un-contaminate a window that straddled two depths. `ARGUED`

---

## 5. The decision rule, applied `MEASURED`

Registered before any result:

- **primary** `Δ(g) ≤ 0.87 DN` — M13's own published w11–w15 basin flatness;
- **sensitivity** `Δ(g) ≤ 0.29 DN` — M13's w12→w13 gap;
- **worst-case arm** `worstregret(w13, g) ≤ 12.111 DN` — M13's published worst case;
- **headline taken at g = 17**, the project's reference operating point.

| width | w*(g) | **Δ13** | primary (0.87) | sensitivity (0.29) | worst @ w13 | worst gate (12.111) |
| ---: | ---: | ---: | --- | --- | ---: | --- |
| 1 | 13 | 0.000 | PASS | PASS | 11.899 | PASS |
| 3 | 14 | 0.033 | PASS | PASS | 13.646 | FAIL |
| 5 | 13 | 0.000 | PASS | PASS | 17.232 | FAIL |
| 9 | 13 | 0.000 | PASS | PASS | 19.718 | FAIL |
| 13 | 14 | 0.080 | PASS | PASS | 22.167 | FAIL |
| **17** | **14** | **0.050** | **PASS** | **PASS** | 24.641 | FAIL |
| 25 | 13 | 0.000 | PASS | PASS | 21.947 | FAIL |
| 33 | 14 | 0.121 | PASS | PASS | 13.697 | FAIL |
| 49 | 8 | 0.551 | PASS | FAIL | 12.280 | FAIL |

**Headline: at g = 17, Δ = 0.050 DN. w13 SURVIVES.** It fails the primary
threshold at **no width in the ladder**, including g = 49. It fails the tighter
sensitivity threshold only at g = 49.

**Is 0.050 DN resolvable, or is it noise?** Resolvable, and I am not hiding
behind that. The measured seed-to-seed sd of `E_excess` at g = 17 is 0.153 DN,
giving a standard error on a 30-cell 5-seed mean regret of **0.0125 DN** — so
0.050 DN is about 4 SE, and Gate D's disjoint seed halves *both* pick w14 at
g = 17. The w13 → w14 movement is **real and it is one ladder step and it is
economically irrelevant**. This is outcome **O3** with a resolvable-but-negligible
±1 wobble, not outcome O5 ("not resolvable").

### 5.1 The worst-case arm failed, and the failure is mine, not the data's

`worstregret(w13, g)` rises from 11.899 DN at g=1 to 24.641 DN at g=17. Taken at
face value that says the regulariser makes w13 dangerous. It does not.

| width | worst @ w13 | driving cell | w* on that cell | E@w13 there | E@w* there | **mean E@w13 over all 30 cells** |
| ---: | ---: | --- | ---: | ---: | ---: | ---: |
| 1 | 11.899 | 119MSDCF/horizontal/s8 | 7 | 30.92 | 19.02 | **24.79** |
| 5 | 17.232 | 119MSDCF/vertical/s32 | 26 | 52.69 | 35.46 | **20.59** |
| 13 | 22.167 | 119MSDCF/vertical/s32 | 23 | 48.81 | 26.64 | **16.50** |
| 17 | 24.641 | 119MSDCF/vertical/s32 | 23 | 50.12 | 25.48 | **15.99** |
| 33 | 13.697 | 119MSDCF/vertical/s32 | 20 | 38.85 | 25.15 | **17.76** |

`E@w13` is **absolute** reconstruction error over the per-cell floor, not
regret, so it is comparable across columns. **w13's absolute error falls by 35%,
from 24.79 DN to 15.99 DN, over exactly the range where its worst-case *regret*
doubles.** The gate is firing on the **dispersion of the per-cell optima**, not
on w13 degrading. Shipping w13 at g=17 is strictly better in DN than shipping
w13 at g=1 — it is just further from an oracle that has itself moved much
further away.

> **I registered a threshold on a statistic that is not comparable across my own
> treatment axis, and I am saying so rather than quietly dropping it.** A *mean*
> of within-cell regrets is comparable across the treatment, because the cell set
> is fixed. A **max** over cells is not: a treatment that widens the spread of
> per-cell argmins inflates the max even when every cell improves in absolute
> terms. Proposed as new discipline item 31. `ARGUED`
>
> This is the same family of error as the one §5 item 27 already names — I
> registered on `Δ13`, which *is* realisable, and got that arm right; I then also
> registered a secondary arm on a max-regret whose comparability I had not
> checked. The primary arm carries the ruling and is unaffected.

---

## 6. The flat aggregate is a cancellation, not an absence `MEASURED`

This is the finding I would most want a reader to take away, because "the
optimum does not move" is true of the aggregate and false of the parts.

Per-cell argmin at the control g=1 and at the reference g=17, over the
24-window ladder:

| geometry | cells | median w*(1) | median w*(17) | median shift | narrower | wider | same |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bar` | 10 | 10.5 | 12.0 | +1.0 | 2 | 6 | 2 |
| `horizontal` | 10 | 9.0 | 7.0 | **−2.5** | **10** | **0** | 0 |
| `vertical` | 10 | 17.0 | 19.0 | **+1.5** | 2 | **6** | 2 |
| **ALL** | **30** | **13.0** | **12.0** | **0.0** | 14 | 12 | 4 |

**On `horizontal` occluding edges the hypothesis is correct, unanimously —
10 of 10 cells move narrower.** On `vertical` edges it is wrong, 6 of 10 moving
wider. The aggregate median shift is exactly 0 because the two cancel.

Two cells, in full, showing both directions (absolute `E_excess`, comparable
across columns):

**`109MSDCF/horizontal/s32` — the hypothesis, confirmed:**

| width | w* here | E@w* | E@w13 | w13 penalty |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 15 | 12.38 | 12.85 | 0.47 |
| 9 | 8 | 11.93 | 13.00 | 1.07 |
| 17 | **8** | 11.25 | 13.07 | 1.82 |

**`119MSDCF/vertical/s32` — the hypothesis, reversed:**

| width | w* here | E@w* | E@w13 | w13 penalty |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 20 | 49.64 | 59.78 | 10.14 |
| 9 | 26 | 29.17 | 48.88 | 19.72 |
| 17 | **23** | 25.48 | 50.12 | 24.64 |

On that second cell the regulariser and a *wide* window are **complementary**:
the cell's best achievable error falls from 49.64 DN to 25.48 DN, but only a
window near w23 can cash it in. w13 sits at ~50 DN throughout.

**Why the geometry matters is not measured.** The Sobel kernel pair and the box
window are both 90°-symmetric, so the asymmetry must come from the underlying
macro texture or from the band geometry (`|d| ≤ 24` around a vertical edge is a
48×256 strip; around a horizontal edge a 384×48 strip). I did not isolate it and
nobody should quote a mechanism for it. `UNVERIFIED`

---

## 7. What did not survive contact with the data

### 7.1 The hypothesis under test `MEASURED`

**Refuted on the aggregate.** The brief's stated expectation — "the optimum
should move narrower than w13", and "the project is about to ship a window
roughly 1.5× too wide" — is not what the data says. At g=17 the optimum is w14,
one step *wider*, and shipping w13 costs 0.050 DN. There is no 1.5× error.

The reasoning behind the hypothesis was sound and is half-confirmed: the
regulariser genuinely does buy the variance reduction (§0.3, §4), and where
variance is the *only* problem it buys it at s ≈ 1.7. The step the hypothesis
missed is that on an occluding edge the window's benefit is not principally
variance reduction.

### 7.2 M13's ladder resolution `MEASURED`

The brief's suspicion is confirmed: M13's ladder omits w14, and on the finer
ladder w14 is the argmin at 4 of the 9 regulariser widths including g=17 — and
also at **g=3 with the regulariser essentially off**. So M13's published "w13"
is w13-or-w14, and at width 1 specifically the finer ladder still says w13
(3.284 vs w14's 3.464), so **M13's headline is correct as published**. The
missing rung concealed a movement worth ≤ 0.121 DN.

### 7.3 M13's headline is an aggregate over a much larger spread than it reads `MEASURED`

Computed from **M13's own committed bytes** (`experiments/m13-window-depth/data/edge-*.csv`,
width 1, its 20-window ladder, its 3 seeds) — this is the one place I re-use
M13's data, and it is a re-analysis, not a corroboration:

| geometry | cells | median w* | min | max |
| --- | ---: | ---: | ---: | ---: |
| `bar` | 10 | 10.5 | 9 | 18 |
| `horizontal` | 10 | 10.5 | 8 | 15 |
| `vertical` | 10 | 17.0 | 13 | 33 |
| **ALL** | **30** | **13.0** | **8** | **33** |

M13's w13 is the aggregate of cells whose own optima span **w8 to w33**, with a
7-step gap between the `vertical` median and the other two. M13 does report
per-cell dispersion, and its recommendation is explicitly a regret-minimising
compromise, so this is not a contradiction — but "the optimum is w13" reads far
more pointed than a 25-step spread justifies, and M15 finds the same spread at
every regulariser width. `MEASURED`

### 7.4 Nothing else `MEASURED`

M13's argmin structure, its regret ladder, its zero-step endpoint result, its
`W_bleed` blind spot, its self-test, its ROI provenance and its corpus totals
all reproduced. Gate A was byte-exact.

---

## 8. Secondary objectives — does the ruling depend on which metric I picked? `MEASURED`

Registered as a check, because `E_excess` is band-restricted (`|d| ≤ 24`) while
part of the regulariser's benefit lives outside the band.

| objective | g=1 | g=9 | g=17 | g=33 | g=49 |
| --- | ---: | ---: | ---: | ---: | ---: |
| **`E_excess`** (primary) | **13** | **13** | **14** | **14** | **8** |
| max mis-selection width (px) | 23 | 20 | 20 | 17 | 12 |
| `dmae` in the band (frames) | 14 | 14 | 12 | 16 | 14 |
| `far_rms` (DN, **disjoint** pixel set) | 40 `ENDPOINT` | 33 | 26 | 26 | 20 |

Three things to say honestly:

1. **The halo-width objective would have given a different answer.** Minimising
   the maximum mis-selection width wants w23 at g=1, not w13 — and it *does*
   narrow monotonically with the regulariser (23 → 12). Had I registered the
   halo metric as primary I would be reporting a confirmed hypothesis. The
   registered primary is `E_excess`, for the reason Gate C demonstrates: the
   halo-width metrics are blind to compromise elections, and 1,935 rows in this
   dataset exercise that blindness.
2. **`far_rms` behaves like the null stratum**, moving from the w40 endpoint
   toward w20 as the regulariser widens. `far_rms` and `band_rms` are **disjoint
   pixel sets**, so this comparison is legitimate (M13 §2.5 item 5). It says the
   same thing §4 says: outside the discontinuity, the window and the regulariser
   substitute.
3. **`acc` and `acc_band` are nested sets and are never quoted here as
   agreeing.** They do not appear in any table above.

---

## 9. The joint (window, regulariser) surface — the pair the project would ship `MEASURED`

Per cell the minimum is taken over **all (w, g) pairs at once**, so this table is
comparable in level, unlike §2.

| rank | window | regulariser width | mean regret | worst regret |
| ---: | ---: | ---: | ---: | ---: |
| 1 | **14** | **17** | **3.701** | 22.553 |
| 2 | 13 | 25 | 3.745 | 21.947 |
| 3 | **13** | **17** | **3.752** | 25.095 |
| 4 | 12 | 25 | 3.792 | 23.624 |
| 5 | 14 | 25 | 3.836 | 20.444 |
| … | | | | |
| 216 | 0 | 1 | 113.003 | 183.387 |

Best window at each regulariser width, on the joint scale:

| width | best w | mean regret | w13's mean regret | penalty |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 13 | 12.549 | 12.549 | 0.000 |
| 9 | 13 | 5.540 | 5.540 | 0.000 |
| **17** | **14** | **3.701** | **3.752** | **0.050** |
| 25 | 13 | 3.745 | 3.745 | 0.000 |
| 33 | 14 | 5.401 | 5.522 | 0.121 |
| 49 | 8 | 15.764 | 16.316 | 0.551 |

**The project's existing pair — w13 at regulariser width 17 — ranks 3rd of 216,
0.051 DN behind the global optimum of the entire surface.** And the g=49
collapse to w8 is not the optimum "sliding narrower": at g=49 the whole surface
is 4× worse (15.764 vs 3.701), so w8 there is the argmin of a degenerate regime,
not a better operating point. `DERIVED`

---

## 10. The seed noise floor, measured `MEASURED`

| width | 1 | 5 | 9 | 13 | 17 | 25 | 33 | 49 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| median seed-to-seed sd of `E_excess` (DN) | **0.228** | 0.191 | 0.171 | 0.156 | **0.153** | 0.136 | 0.137 | 0.187 |

Over 720 (cell, window) groups of 5 seeds each, per width. M13 published 0.193 DN
at g=1 with 3 seeds; mine is 0.228 DN at g=1 with 5 seeds on a different tile
margin — same order, slightly larger as more seeds sample more of the tail.
**The regulariser reduces seed noise by 33% (0.228 → 0.153 DN at g=17)**, which
is a further independent sign it is doing the variance work it claims to.

`DERIVED` standard error of a 30-cell mean regret: 0.0186 DN at g=1, **0.0125 DN
at g=17**. Both thresholds (0.87, 0.29) sit 23× and 70× above it.

---

## 11. Cost

The regulariser axis is free at the window's expense in neither direction — this
milestone measured no timings of the shipped pipeline, and M13 §5's cost table
stands unmodified. The sweep itself, on 32 threads: the 38,880-measurement
surface took **462 s** (249 s for 109MSDCF, 213 s for 119MSDCF, 10 invocations),
and the whole chain — audit, self-test, cross-check, the 6-run Gate A
replication, two noise ladders, the surface, audit-after and the analysis —
took **651 s**. Derived from file mtimes in `data/`. `MEASURED`

---

## 12. The recommendation

**Ship `tenengrad-w13` with the merge regulariser at width 17.** `DERIVED`

- w13 survives at every regulariser width in the ladder, on the registered
  primary threshold, with a maximum penalty of 0.121 DN (at g=33) and 0.050 DN
  at the reference width.
- w14 is very slightly better at g=13/17/33 and very slightly worse at
  g=1/5/9/25. It is one ladder rung and 0.05 DN. **Either is defensible; there
  is no reason to change a shipped constant for 0.05 DN**, and w13 has M13's
  independent verification behind it.
- **Do not run the regulariser at width 49.** It is 4× worse than width 17 on the
  joint surface and it is the only setting where w13 fails the sensitivity
  threshold.
- **Do not run the regulariser at width 3.** Gate B2 shows merged noise is
  *worse* at g=3 than with the regulariser off, on both stacks, reproducing
  fact 36.

### What question 17 closes, and what it does not

**Question 17 closes.** The last unmeasured factor that could move M13's
recommendation has been measured and does not move it. The remaining four items
in M13 §7.6 (disocclusion, human perception, curved boundaries, magnification
scaling) are scope caveats and are untouched by this milestone.

**One new question opens** (§6): the direction of the window-optimum shift under
regularisation is **set by edge orientation** — unanimously narrower on
`horizontal`, mostly wider on `vertical` — and I did not isolate why. If that is
a texture-anisotropy effect it is a property of these two stacks and harmless.
If it is a property of the *band geometry* used by `E_excess`, it is a defect in
the metric that M13 and M15 share.

---

## 13. Gates

| gate | requirement | result |
| --- | --- | --- |
| **0** | corpus audit before/after, both methods, `-Force` | **PASS** — identical, matches M13's totals |
| **A1** | replication CSV byte-identical to M13's | **PASS** — SHA-256 match, both stacks |
| **A2** | recover w13 / 3.171 / 12.111 and w40 `ENDPOINT` 0.000 | **PASS** — exact |
| **B1** | `ring-1-3` 1.2527× → 1.0737× (M2) | **PASS** — exact to 4 dp |
| **B2** | `N(17) < N(1)` by ≥ 0.10 for `ring-1-3` | **PASS** — 0.2025 / 0.2975 |
| **C** | assert `W_bleed`'s blind spot, synthetic **and** real | **PASS** — 27/27 self-test; 1,935 real instances |
| **D** | placebo: disjoint seed halves at fixed width | **PASS** — 0 window steps at all 9 widths |
| **null** | zero-step argmin is the `ENDPOINT` | **PASS in substance** — §3; label artefact above g=9 |
| **worst-case arm** | `worstregret(w13, g) ≤ 12.111` | **FAIL above g=1** — §5.1; the statistic is not comparable across the treatment. My registration error, disclosed. |
| **self-check** | every headline number reproduces through a **second, disjoint** code path | **PASS** — `verify_headline.py`, 47/47 |

**Outcome grid: O3** — "the optimum does not move; question 17 closes and the
project ships w13 with confidence" — with the §3 and §5.1 deviations reported
above, plus the §6 heterogeneity finding which the grid did not anticipate.

---

## 14. Reproduce

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd projects\strehl\experiments\m15-regulariser-window
.\run-m15.ps1                                  # ~11 min, writes data\*.csv
python m15_analyse.py --out data\analysis.txt  # every table above
python verify_headline.py                      # 47 headline numbers, disjoint code path
```

`verify_headline.py` deliberately shares **no code** with `m15_analyse.py` — a
different CSV reader, a different grouping, a different regret loop — and
re-checks Gate A off M13's committed bytes plus the w*/Δ13 pair at all 9
regulariser widths and the null-stratum plateau. It reports **47 of 47 OK**. If
it ever disagrees with `data/analysis.txt`, one of the two is wrong and nothing
in this report is safe.

Committed CSVs: `data/edge-109MSDCF.csv`, `data/edge-119MSDCF.csv` (19,440 rows
each — the surface); `data/repro-edge-*.csv` (Gate A); `data/noise-*.csv`
(Gate B2); `data/analysis.txt`, `data/run-log.txt`, `data/selftest.txt`,
`data/xcheck-109MSDCF.txt`, `data/audit-*.txt`.

Section numbers in `data/analysis.txt` map to this report as: §1 → report §2;
§2 → the full 24×9 regret surface; §3 → report §9; §4/§15 → report §4;
§5 → report §5; §6 → basin widths; §7 → report §10; §8 → report §0.5;
§9 → report §8; §10 → report §0.4; §11 → report §0.3; §12/§19 → report §6;
§13 → report §2.3; §14 → report §3; §16/§18 → report §5.1 and §6;
§17 → report §0.6.
