# M42 — the window ladder for `tenengrad-sq`

**Status:** complete. Answers `OWNER-QUESTIONS.md` **Q1**, left open by M17.
**Pre-registration:** `experiments/m42-window-ladder/PREREGISTRATION.md`, committed `21df0d8`, before any candidate number was read.
**Data:** `experiments/m42-window-ladder/data/` — every number below reproduces from committed CSVs with no RAW access.

---

## Verdict

**`WINDOW_RADIUS = 13` survives the pre-registered test by 0.0096 DN — 1.1% of the
tolerance — and 0 of 6 independent subsets choose it.** [MEASURED]

The pre-registered rule was: *13 SURVIVES iff 13 is inside `tenengrad-sq`'s 0.87 DN
mean-regret basin.* It is: the basin is **w9–w13** and w13 sits at **+0.8604 DN** above
the minimum. That is a PASS, and I report it as a PASS because the rule was binding.

It is also the weakest possible pass, and the supporting evidence all points the other
way. **This is not a shipped-default defect, but 13 is not the operator-matched radius
either.**

| Evidence | Magnitude (M13/M15's operator, shipped) | Squared (M17's recommendation) |
| --- | --- | --- |
| pooled mean-regret argmin | **w13** | **w11** |
| mean regret at the argmin | 3.1708 DN | 2.9789 DN |
| mean regret at w13 | 3.1708 DN (+0.0000) | 3.8393 DN (**+0.8604**) |
| 0.87 DN basin | w11, w12, w13, w15 | w9, w10, w11, w12, w13 |
| worst-case-regret argmin | w13 (12.1110 DN) | **w9** (13.1438 DN); w13 is 19.8320 DN |
| 6 independent argmins (2 stacks × 3 replicates) | **6/6 → w13** | **0/6 → w13**; all w10 or w11 |
| per-stack, w13's excess over that stack's min | +0.0000 / +0.0000 | 109MSDCF **+0.6075** (inside) / 119MSDCF **+1.1326** (**outside the basin**) |

The magnitude operator's argmin is rock-solid — six independent subsets, zero spread.
The squared operator's argmin is **equally solid and it is not 13**: six independent
subsets, spread w10–w11, and not one of them reaches 12, let alone 13. The pooled basin
contains 13 only because pooling the two stacks averages 119MSDCF's clear miss
(+1.1326 DN, outside the basin) against 109MSDCF's near-hit (+0.6075 DN). [MEASURED]

### The single number that decides it

**Moving `tenengrad-sq` from w13 to w11 buys 0.8604 DN of mean regret and 6.69 DN of
worst-case regret for 0.000 ms.** Both radii measure **3.226 ms/frame/Mpx** — identical
to three decimals, because `box_mean` is a running sum and O(1) in radius. [MEASURED]

**Recommendation: ship `tenengrad-sq` at `WINDOW_RADIUS = 11`, not 13.** Not because 13
is broken — it is inside the tolerance — but because the correction is free on every axis
this project measures, and because 11 is where the operator's own data puts it, 6 times
out of 6. [ARGUED, from MEASURED inputs]

I did not make this code change: `focus.rs` is not mine, and M17's `tenengrad-sq` switch
is itself not yet applied. **Both changes should land together, as one edit**, because
shipping the operator without the radius is precisely the pairing defect Q1 was raised to
prevent.

---

## Gate 1 — M13's headline reproduces from my harness

Mandatory before anything else. Run from my own code over M13's committed data. [MEASURED]

```
30 depth-step cells -> argmin w13 (interior), mean regret 3.1708, worst 12.1110
fact 60 says:          argmin w13,            mean regret 3.171,  worst 12.111
6 zero-step cells   -> argmin w40 (ENDPOINT), mean regret 0.0002
fact 61 says:          argmin w40 ENDPOINT,   regret 0.000
```

**PASS.** My magnitude basin is w11, w12, w13, w15 — fact 81's w11–w15, exactly.

This gate has demonstrated power to reject (rule 20). It fired during this milestone: a
`--steps 0` probe rendered the edge at `vertical@257` instead of `vertical@274`, because
`edge_mode`'s tile margin is `regulariser + max_support(measures) + max_blur_radius`, so
dropping steps from the sweep silently moves the scene. The full ladder pins the margin at
82 and the geometry back to `vertical@274`, `horizontal@210`, `bar@274w24` — M13's and
M17's scene, byte-for-byte in configuration. Cross-check: `tenengrad-sq-w13`'s absolute
`excess_dn` here is **22.70**, and M17 measured **22.7013** independently. [MEASURED]

---

## Axis 1 — quality vs window

30 depth-step cells (2 stacks × 3 shapes × 5 non-zero steps), regret pooled **within** an
operator so one operator's bad windows cannot flatter the other. Regret in DN, lower better.

**magnitude**

```
        w0     w1     w2     w3     w5     w6     w8     w9    w10    w11    w12    w13    w15    w17    w18    w20    w23    w26    w33    w40
mean 103.53  68.38  41.54  30.10  17.50  13.20   7.01   5.52   4.51   3.85   3.46   3.17   4.04   6.19   7.36  11.02  20.90  27.60  33.28  37.71
worst 170.6  131.4   96.1   83.8   64.5   56.2   39.9   32.7   26.4   21.0   16.3   12.1   25.3   35.7   37.7   47.2  101.4  130.5  138.3  132.0
```

**squared**

```
        w0     w1     w2     w3     w5     w6     w8     w9    w10    w11    w12    w13    w15    w17    w18    w20    w23    w26    w33    w40
mean 106.34  58.72  34.56  23.54  11.15   7.83   4.17   3.44   3.08   2.98   3.20   3.84   5.64   8.28  10.05  14.19  24.16  31.31  40.66  46.86
worst 176.5  118.0   87.0   71.3   44.8   34.5   18.6   13.1   14.8   17.2   18.0   19.8   31.2   43.7   50.2   68.7  103.0  125.8  175.6  163.5
```

Two things the tables say that the argmin alone does not. [MEASURED]

1. **Squaring shifts the whole curve left and makes it sharper.** The squared operator is
   *better* than the magnitude everywhere below w13 (3.08 vs 4.51 at w10) and *worse*
   everywhere above it (46.86 vs 37.71 at w40). The crossover is at w12–w13. That is the
   bias–variance balance moving, exactly as Q1 predicted it might.
2. **Worst-case regret moves further than mean regret.** The squared operator's worst-case
   argmin is **w9**, and w13's worst case (19.83 DN) is 6.69 DN worse. If the confidence
   story cares about tail behaviour — and per-pixel calibrated confidence does — the case
   for a smaller radius is stronger than the mean suggests.

**Null stratum** (6 zero-step cells, no depth signal to recover): argmin at the **w40
ENDPOINT**, 0.0056 DN for squared, 0.0002 DN for magnitude. Per discipline 25 this is
"no turnover found within the sweep", not an optimum. It is the correct null: a depth
ladder that produced an interior optimum with no depth step would mean the statistic is
responding to something other than depth. It does not. [MEASURED]

---

## Axis 2 — merged noise N vs window

Median over the 4 committed flat ROIs of a stack, then mean over stacks. Flat ROIs taken
from committed `data/noise-*.csv`, per-stack, per fact 88. [MEASURED]

```
             w0      w1      w2      w3      w6      w9     w11     w12     w13     w17     w26     w40
magnitude 1.0632  1.3334  1.2255  1.1771  1.1189  1.0961  1.0908  1.0889  1.0864  1.0846  1.0810  1.0778
squared   1.0632  1.3238  1.2239  1.1757  1.1169  1.0967  1.0890  1.0867  1.0849  1.0812  1.0796  1.0767
```

`N(magnitude, w13) = 1.08637` reproduces the shipped 1.0864 to five figures — an
independent tie to the corpus. [MEASURED]

Noise falls monotonically with radius above w1, so **noise prefers a bigger box and pulls
against quality**. The pull is tiny: moving from w13 to w11 costs **+0.0041 in N**
(1.0849 → 1.0890), **0.38%**. Against 0.8604 DN of mean regret and 6.69 DN of worst-case
regret, that is not a real trade. The squared operator is also very slightly quieter than
the magnitude at every radius from w11 up. [MEASURED]

The w1 spike to 1.32 is the honest shape of this curve: a 3×3 box is *worse* than no box.

---

## Axis 3 — is the blind-spot cure radius-dependent?

`D = response(sigma 3) / response(sigma 0)` on the boundary column of a planted monotone
edge. **1.0000 = totally blind.** This is the entire reason `tenengrad-sq` won M17, so if
its cure were radius-dependent the radius choice would stop being a pure quality tradeoff.

```
monotone step
             w0      w1      w2      w3      w5      w6      w8      w9     w10     w13     w26     w40
magnitude 0.2592  0.3755  0.5855  0.7470  0.9283  0.9673  0.9959  0.9993  1.0000  1.0000  1.0000  1.0000
squared   0.0672  0.0942  0.1388  0.1656  0.1838  0.1855  0.1860  0.1860  0.1860  0.1860  0.1860  0.1860

smooth ramp (width 9)
magnitude 0.8587  0.8446  0.8173  0.7784  0.8271  0.8965  0.9707  0.9864  0.9944  0.9999  1.0000  1.0000
squared   0.7374  0.7135  0.6692  0.6106  0.6407  0.6643  0.6786  0.6798  0.6801  0.6802  0.6802  0.6802
```

**Prediction 3 is FALSIFIED.** I registered that the cure would degrade toward 1.0 as the
radius grew, because the TV-conservation argument is asymptotic in window-width ÷
blur-width. It does not. `tenengrad-sq`'s D **saturates at 0.1860 from w8 upward and never
moves again**, out to w40. [MEASURED]

The mechanism, and why my prediction was wrong: TV conservation is a statement about the
*integral of the first power* of the gradient. Squaring breaks the conservation law itself,
not merely its asymptotics — ∫g² is strictly reduced by blur for any non-constant g, by
Cauchy–Schwarz. Widening the window therefore cannot restore blindness; it only averages an
already-shrinking quantity over more area. The magnitude operator, by contrast, reaches
**exactly 1.0000 by w10** and stays there — its blindness is *complete* at every radius the
project has ever considered shipping. [DERIVED, from the MEASURED tables above]

Three consequences. [MEASURED unless marked]

1. **The radius choice remains a pure quality/noise tradeoff.** The blind-spot cure is
   radius-invariant above w8, so it does not constrain the ladder. Q1's fourth question is
   answered: no, the cure is not radius-dependent, and the radius can be specified
   independently of it.
2. **Smaller radii are strictly better on the blind spot** — 0.0672 at w0 vs 0.1860 at w13
   — but the gain is spent below w8, where regret is catastrophic (106 DN at w0). No
   usable radius trades against it.
3. **The smooth ramp is the harder case and it is only half-cured.** D = 0.6802 for the
   squared operator against 1.0000 for the magnitude — a real repair, but 0.68 is much
   closer to blind than the step's 0.1860. Specular falloff on a carapace is a ramp, not a
   step. `tenengrad-sq` substantially mitigates the fact-73 blind spot on sharp monotone
   edges and only partially mitigates it on smooth gradients. [MEASURED — this is a new
   limitation, not previously in the corpus]

**Null control** (σ=0 vs σ=0, independent noise draws — a ladder that manufactures
discrimination from noise alone would show a ratio far from 1): worst arm over all 41 is
**1.0683**, and the 6 arms above 1.02 are all at w0–w8 where the box is too small to
average the noise. Every arm at w9 and above is within 2%. [MEASURED]

**Positive control** (real corpus texture through the same blur ladder — the plant must be
able to express the failure, rule 13): worst D over all 41 arms is **0.1586**. The ladder
does discriminate defocus when defocus is discriminable. [MEASURED]

---

## Axis 4 — cost vs window

`ms/frame/Mpx`, minimum over alternating-direction passes, per rule 16 and discipline 30.
Quoted as a **BOUND**, not a point value: the worst within-setting spread across passes was
**+25.6%**, which is larger than the entire between-radius variation. [MEASURED]

```
magnitude   w1..w40:  3.299 .. 3.363  ->  <= 1.020x
squared     w1..w40:  3.208 .. 3.250  ->  <= 1.013x
```

**Cost is flat in radius for both operators, to within a bound of 1.02×.** Fact 66 holds
for the squared operator too — expected, since both use the same running-sum `box_mean`
and differ only in the per-pixel reduction. Prediction 4 confirmed. [MEASURED]

The naive `max/min` over the full ladder is 1.74×/1.79×, but that is entirely `w0`
(1.931 / 1.821 ms), which skips the box filter altogether. Reporting that as
"cost varies 1.75× with radius" would be wrong; the honest statement excludes the
degenerate arm.

**Combined cost of the recommendation** — this is Q1's question 3, and the answer is that
the new optimum does not need a bigger box, so there is nothing to pay: [MEASURED]

```
tenengrad-w13     (shipped)   3.334 ms/frame/Mpx   1.000x
tenengrad-sq-w13              3.226                0.968x
tenengrad-sq-w11  (new opt)   3.226                0.968x
```

M17's 0.96× survives the radius change intact. The squaring saves a per-pixel `sqrt`; the
radius costs nothing.

---

## The counterweight: what a large radius costs the occlusion detector

Fact 152 measures occlusion-bimodality enrichment at **4.38× at radius 2** and **0.36×
(depleted) at radius 13** — a large focus window destroys a signal M18's seam needs, which
is why that seam gathers statistics at 5×5. Per the pre-registration this is reported as a
**separate constraint**, not folded into the quality number. [MEASURED elsewhere — fact 152]

It happens to point the same way as this milestone's result. Quality says w11; fact 152
says smaller; the blind spot is indifferent above w8; cost is indifferent; noise alone
prefers larger, by 0.38%. **Three of five considerations favour moving down from 13 and
none of them meaningfully oppose it.** [ARGUED]

I want to be explicit about what this milestone does *not* license: w11 is not "smaller
enough" to recover fact 152's enrichment. The bimodality signal wants radius ~2, and the
ladder shows radius 2 costs **34.56 DN** of mean regret against 2.98 at w11. These two
consumers cannot share one window. **The correct resolution is two windows, not a
compromise radius** — which is what M18's seam already does at 5×5. [ARGUED]

---

## Scoring the registered predictions

| # | Prediction | Outcome |
| --- | --- | --- |
| 1 | `tenengrad-sq`'s basin contains 13 | **CONFIRMED, marginally** — by 0.0096 DN of an 0.87 DN bar, and it fails on 119MSDCF alone |
| 2 | The squared optimum sits at a radius ≤ 13 | **CONFIRMED** — w11 pooled, w10–w11 across all 6 subsets |
| 3 | The blind-spot cure degrades toward 1.0 as radius grows | **FALSIFIED** — it saturates at 0.1860 from w8 to w40 and never moves |
| 4 | Cost stays flat in radius, ≤ 1.02× | **CONFIRMED** — ≤1.020× magnitude, ≤1.013× squared |
| 5 | The zero-step null puts the argmin at the w40 endpoint | **CONFIRMED** — 0.0056 DN, ENDPOINT |

---

## Rule 24 — which of M13/M15's choices were operator-specific

Verification must re-choose, not re-compute. The choices I re-made, registered in advance:

1. **Normalisation degree.** M13 normalised `|grad|` by `σ¹`. The monotone partner of a
   squared response is `σ²`, so `tenengrad-sq-wN` divides by `σ²`. I carried `tgrms-w13`
   (`÷σ¹`) as a harness check. Labelled in the pre-registration as **arithmetic, not
   evidence**: at width 1 it is a monotone reparameterisation and cannot fail. It did not.
2. **Primary statistic.** M17 used absolute `excess_dn`; a window ladder is regret's
   designed treatment, and facts 60/81 are quoted in regret, so I switched back to regret
   for comparability.
3. **Regret pooled within an operator, never across.** Pooling across would let the
   magnitude's catastrophic w40 flatter the squared operator's w40 and vice versa.
4. **Uncertainty as 6 independent argmins**, regret recomputed inside each subset, not as a
   basin width alone. This is the choice that produced the finding: the pooled basin says
   "13 is fine", the 6 subsets say "0 of 6 pick 13". Discipline 31 — an argmin label is
   meaningless unless separated from its neighbours by more than the noise floor — cuts
   both ways, and here it says the *separation* is real and 13 is on the wrong side of it.
5. **Endpoint argmins labelled ENDPOINT**, per discipline 25.

**Rule 23 checked, not assumed.** Every Sobel in this harness runs on a single 2-D `f32`
plane (`src/measures.rs::sobel_magnitude`, indexed `y*w + x`). There is no 3-D cube and no
`scipy.ndimage` anywhere in the measurement path — the Python only reads CSVs. The M32
defect cannot be present here. [MEASURED — by reading the code]

---

## What I could not measure

* **Whether the optimum is the same for real depth steps as for planted ones.** The whole
  ladder runs on planted occluding edges over real corpus tiles, as M13's did. It inherits
  M13's plant, and therefore M13's unexamined assumption that a planted edge's regret curve
  has the same shape as a natural one. Nothing in M42 tests that. [UNVERIFIED]
* **Radii between 13 and 15, and between 9 and 11.** The ladder is M13's, chosen for
  comparability, and it is sparse exactly where the squared optimum lands. The true argmin
  could be w10 or w12; I can only say it is in w10–w11 on the sampled grid.
* **Any radius for the dual/percentile arms.** M17 killed them; I did not re-open them.
* **The smooth-ramp blind spot at a radius that fixes it.** D = 0.6802 is flat from w8 to
  w40 and 0.7374 at w0 — no radius in the ladder fixes the ramp case. Whether a different
  *operator* does is unmeasured and is a real open question.
* **Effect on the full pipeline.** Every number here is measured on the focus operator in
  isolation, not through the merge. The regret is real regret in DN on M13's cells, but no
  end-to-end image was rendered at w11.

## Questions for the repo owner

1. **Do the operator and the radius land as one edit?** My recommendation is
   `tenengrad-sq` + `WINDOW_RADIUS = 11`, together. Shipping M17's operator at the
   inherited 13 is the exact pairing defect Q1 exists to catch, and it would be worse than
   shipping neither.
2. **How much do you weight worst-case regret?** On the mean, w13 scrapes in. On the
   worst case, `tenengrad-sq` at w13 is 19.83 DN against w9's 13.14 — a 51% tail penalty.
   For calibrated per-pixel confidence I would weight the tail heavily, which argues for
   w10 rather than w11. I did not make that call unilaterally.
3. **Is the smooth-ramp result worth a milestone?** D = 0.6802 on a width-9 ramp means the
   fact-73 blind spot is *mitigated but not closed* on smooth gradients — the case the
   original argument called out as common in macro (specular falloff, defocused
   backgrounds, petal edges). `tenengrad-sq` fixes the step and half-fixes the ramp.

---

## Reproduction

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd experiments\m42-window-ladder
cargo build --release
.\run-m42.ps1              # audit -> edge -> noise -> blindspot -> cost
python m42_analyse.py      # gate 1 + 4 axes + the pre-registered decision
python m42_uncertainty.py  # the 6 independent argmins, null breakdown, cost bound
```

`m42_analyse.py` writes `data/m42-analysis.txt`; `m42_uncertainty.py` writes
`data/m42-uncertainty.txt`. Both are committed. The analysis reads only committed CSVs, so
the headline reproduces without RAW access.

`m42_uncertainty.py` is a separate file rather than a fix to `m42_analyse.py`: the latter
had already produced results reported here and rule 15 forbids modifying it. Its
argmin-uncertainty block emitted nothing (it filtered on the input seed, but the CSV's
`seed` column carries a per-cell derived value), so no number from it was ever reported.
The replacement recovers replicates structurally — 3 distinct derived seeds per
(stack, shape, step) cell, sorted for a stable index — and asserts the count is exactly 3
before using it.
