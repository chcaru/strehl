# M39 - independent verification of the M38 detail metric

**Verifier:** independent agent. Not the author of `merge_cmd.rs`, `merge.rs` or M38.
The brief was to try to FALSIFY the claims, not to confirm them.
**House rule:** every statement below is labelled MEASURED / DERIVED / ARGUED.
**Evidence:** `experiments/m39-verify/src/01..15-*.py` -> `experiments/m39-verify/out/*`.
No existing repo file was modified; this file and `experiments/m39-verify/` are the only
things written.

## Verdicts at a glance

| Claim | Verdict | One-line reason |
|---|---|---|
| **A** noise confounds mean-abs-grad, same sign as blur | **CONFIRMED**, 2 qualifications | Demonstrated both directions on real data: argmax raises `m2` +5.04% on a **flat** ROI; the plain mean drops it -60.3% with zero blur. But the correction removes only the *model-predicted* noise, and the statistic is an RMS. |
| **B** -45% -> -4.6% / -3.6% | **CONFIRMED**, wider error bar | Independent numpy re-implementation reproduces **every cell of both 6-gate tables to 4 dp**. But the figures carry a +/-2 pp band from the noise-model scale, which M38 does not state. |
| **C** `2*s_i^2 + s_{i+1}^2 + s_{i+w}^2` is exact | **CONFIRMED** | Derived from scratch, same coefficients; 4e6-trial Monte Carlo agrees to 0.2% while three sum-preserving rivals miss by 24-39. One precondition (pixel independence) is unstated and violated by the roadmap. |
| **D** fact 24 carries the same confound reversed | **CONFIRMED in direction**; the 1.253x **COULD NOT VERIFY** | argmax raises `m2` +6.42% / +5.09% and raises noise 1.0739x, measured together. But 1.253x belongs to M2's `ring(1,3)`, not the shipped Tenengrad; the right factor for today's operator is ~1.07x, making the noise share ~22%, not ~83%. |

**Biggest single finding (MEASURED, §5.1):** the positive control M38 never ran. The
corrected metric reads the *known-bad* plain 22-frame mean at **-48.4% / -13.0%** against
the gated merge's **-4.6% / -3.6%**. Invariant 2 does discriminate success from failure.
Raw `m2` does not (-45.5% vs -60.3%, a factor of 1.3).

**Biggest single defect (MEASURED, §5.2):** the correction leaves the selection-induced
excess noise in place, and I show it crediting a **flat** ROI with **+35.5% detail**.

---

## §1 The algebra of CLAIM C, checked from scratch

### 1.1 My own derivation (DERIVED, done before reading the author's)

Let `v[i] = s[i] + e[i]` with `s` deterministic and `e` zero-mean, independent across
pixels, `Var(e[i]) = sigma_i^2`. Forward differences as the code writes them:

```
dx_i = v[i+1] - v[i] = (s[i+1] - s[i]) + (e[i+1] - e[i])
dy_i = v[i+w] - v[i] = (s[i+w] - s[i]) + (e[i+w] - e[i])
```

`E[dx_i^2] = (ds_x)^2 + Var(e[i+1] - e[i]) = (ds_x)^2 + sigma_{i+1}^2 + sigma_i^2`
(the signal x noise cross term is `2*ds_x*E[e[i+1]-e[i]] = 0`).
Likewise `E[dy_i^2] = (ds_y)^2 + sigma_{i+w}^2 + sigma_i^2`. Adding:

```
E[dx_i^2 + dy_i^2] = signal + 2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2
```

**I get exactly the author's coefficient structure**, and the `2*` on `sigma_i^2` is
right for the stated reason: pixel `i` is the *base* of both differences, so its noise
enters twice.

### 1.2 Monte-Carlo check with rivals that could fail (MEASURED)

`experiments/m39-verify/src/01-algebra.py`, 4e6 trials, 9x7 plane, a deliberately
NON-uniform sigma field (a uniform field cannot discriminate any coefficient set
summing to 4).

```
model                                           max |per-px err|  rel err on mean
CLAIM C  2*s_i^2 + s_{i+1}^2 + s_{i+w}^2                 0.09556        1.227e-04
rival A  1*s_i^2 + s_{i+1}^2 + s_{i+w}^2                24.69234        3.173e-01
rival B  4*s_i^2 (all weight on i)                      39.42749        3.853e-02
rival C  2*(s_{i+1}^2 + s_{i+w}^2)                      39.38826        3.555e-02

mean noise contribution (MC)   : 41.990040
mean noise contribution CLAIM C: 41.984888
MC standard error on that mean : 0.008253  (rough)
```

CLAIM C's residual (0.0956 max, on a quantity of size ~42) is MC sampling error; the
three rivals miss by 24-39 per pixel. **CLAIM C's formula is CONFIRMED as the exact
expectation** under the stated model.

### 1.3 Where the exactness is conditional (ARGUED)

The formula is exact **only** under the assumptions it names. Four of them are load
bearing and are not all true of the merged image:

1. **Noise independent across pixels.** True for shot + read noise (adjacent plane
   pixels use disjoint photosites; green luma `(G1+G2)/2` at pixel `i` and at `i+1`
   share no photosite). FALSE for fixed-pattern noise, and false for anything that
   spatially correlates the two. See §2.
2. **`sigma_i` is the true sigma of `v[i]`.** The code uses the *model* sigma. Any
   model error propagates straight into the subtraction, and it is a systematic
   error, not a random one.
3. **The subtraction is of an expectation from a sample.** `raw_rms^2` is one
   realisation; `noise_rms^2` is an expectation. With ~65k differencing sites the
   sampling error on `raw_rms^2` is small but not zero.
4. **Noise is uncorrelated with the signal.** Not exactly true for a *selected*
   merge: the winner is chosen partly on the pixel's own noise, which is what makes
   argmax 1.253x noisier than one frame (fact 19). See §2.2.

`sq` and `nsq` are accumulated over the identical index set
(`y in 0..h-1`, `x in 0..w-1`) in `detail_metrics`, and every index `i+1`, `i+w`
touched lies inside the ROI, so there is no index-set mismatch and no out-of-ROI
read. VERIFIED by reading `crates/strehl-cli/src/merge_cmd.rs:276-310 (working tree, SHA-256 178B7E97..., verified stable during the run)`.

**Note on the exactness of the identity used later:** because `sigma^2(S) = g*S + rd^2`
is *affine* in S, `mean_i(sigma_i^2) = sigma^2(mean_i S_i)` **exactly** (checked
numerically in script 01: `148.28807964` both ways). This matters in §4.

---

## §2 The FPN bound — direction and size

M38 §2.4 and fact 322 flag: `predicted_sigma` divides by sqrt(n), fixed-pattern noise does
not, so the subtracted term is too small at large n and corrected retention at wide gates
is an **upper bound**.

### 2.1 The direction is right (DERIVED + MEASURED, script 04(c), 11(b), 12)

A spatially white fixed component of standard deviation `f` adds `4f^2` to the true noise
contribution (coefficients 2+1+1), at every gate, and is subtracted at no gate. Two
parameterisations bracket where it sits relative to the profile:

- **P1** (FPN outside the profile): model `= sigma_t^2/n`, truth `= sigma_t^2/n + f^2`.
- **P2** (FPN already inside the profile's single-frame sigma): model `= (sigma_t^2+f^2)/n`,
  truth `= sigma_t^2/n + f^2`. Under P2 the shortfall is `f^2*(1 - 1/n)`, zero at n=1.

Under **both**, retention only falls as `f` rises. **The bound direction is CONFIRMED.**

```
ROI A, gate 0 -> gate 8            ROI A, gate 0 -> gate 2.0 (the intended gate)
   f DN     P1        P2              f DN     P1        P2
  0.000   -4.58%    -4.58%           0.000   -0.18%    -0.18%
  0.377   -4.59%    -4.63%           0.377   -0.18%    -0.22%
  1.000   -4.62%    -4.94%           1.000   -0.18%    -0.44%
  2.000   -4.72%    -6.00%           2.000   -0.19%    -1.24%
  5.000   -5.62%   -13.79%           5.000   -0.22%    -6.99%
 10.000  -17.67%   -50.85%
```

### 2.2 The size (MEASURED, scripts 05 and 06)

The project's own measurement (M4, SYNTHESIS §Threats item 5) puts the **offset FPN
(DSNU) floor at 0.377 DN**. At that value the effect on the headline is **0.01 pp (P1) to
0.05 pp (P2)** at gate 8, and **0.00 to 0.04 pp** at gate 2.0. Negligible.

I made my own upper bound rather than take M4's on trust. Flat ROI `2272,1344`, high-pass
(I - 5x5 box) of the means of two **disjoint** halves of the 22 frames, then their
covariance — temporal noise contributes exactly zero to a covariance of disjoint halves:

```
ROI 2272,1344: disjoint-half high-pass covariance = 24.944 DN^2  ->  f <= 5.097 DN at 2021 DN
ROI 2352,1408: disjoint-half high-pass covariance = 24.425 DN^2  ->  f <= 5.044 DN at 2020 DN
```

That bound is **loose**: the halves are interleaved (even/odd frames), so their mean drift
positions nearly coincide and *shared scene texture is counted as fixed pattern*. It is an
upper bound, not an estimate. Even taken at face value, and even at the pessimistic P2
parameterisation, 5 DN at 2021 DN of signal is at most **-6.99%** instead of -0.18% at
gate 2.0, and a PRNU-like (signal-proportional) component would scale to 5.1*394.6/2021 =
**1.0 DN** at ROI A's own signal level, worth **0.26 pp**.

**Verdict on §2:** the bound direction is CONFIRMED; the size is **not large enough to
change the conclusion at gate 2.0**. To move the ROI A gate-8 reading from -4.6% to -10%
needs `f` around 8 DN under P2 or 14 DN under P1 — 20x to 37x M4's measured DSNU floor.
I did **not** measure PRNU (the project's own open question 5 owes flat fields for it), so
the PRNU component is bounded only by the loose 5.1 DN figure above.

### 2.3 A larger, UNFLAGGED sensitivity in the same place (MEASURED, scripts 04, 06, 11)

M38 flags FPN, which I measure to be worth ~0.05 pp. It does **not** flag the sensitivity
to the **absolute scale of the calibrated sigma**, which is worth ten times more — and the
run's own banner says the gain is `DERIVED from white-level consistency, not a
photon-transfer measurement`.

Scaling every model sigma by `k` (both ends, so nothing cancels):

```
   k     ROI A gate0->gate8   ROI B gate0->gate8      ROI A gate0->gate2
  0.90        -8.49%               -7.46%
  0.96        -6.27%               -5.25%                  -1.52%
  1.00        -4.58%               -3.57%                  -0.18%
  1.05        -2.21%               -1.19%                  +1.72%
  1.10        +0.51%               +1.55%
```

So I measured `k`. Two methods, neither of which uses the noise model:

1. **G1-G2 photon transfer.** The two greens are separate photosites, so
   `Var(G1-G2) = 2*(g*S + read^2) + (local signal difference)^2`. Per-patch ratio to the
   model, low percentiles within narrow signal bins, chi-square percentile divided out
   (14162 patches of 24x24, dof 575):

```
      signal bin      n        p2        p5       p10       p25
      150-   250    337     0.981     0.991     0.986     1.016
      250-   350    411     0.978     0.985     0.985     0.984
      350-   450   1613     0.980     0.983     0.987     0.991     <- ROI A sits at 394.6 DN
      450-   600    981     1.000     1.004     1.007     1.019
     1300-  1700   2391     1.032     1.035     1.038     1.040     <- ROI B sits at 1153 DN
     1700-  2200   6801     1.050     1.050     1.050     1.051
```

2. **Temporal pairs** in the two flat ROIs, `Var(frame_k - frame_k+1)/2`, which cancels any
   static G1/G2 difference exactly:

```
   ROI 2272,1344: k = sqrt(min/model) = 0.9829   sqrt(median/model) = 0.9911
   ROI 2352,1408: k = sqrt(min/model) = 0.9803   sqrt(median/model) = 0.9923
```

Both are UPPER bounds (structure and drift inflate them). Taking `k` in **[0.96, 1.05]**:

- ROI A gate0->gate8: **-6.3% to -2.2%** (published -4.6%)
- ROI B gate0->gate8: **-5.3% to -1.2%** (published -3.6%)
- ROI A gate0->gate2: **-1.5% to +1.7%** (published -0.2%)

**The published figures are inside the band, but the band is +/-2 pp, not the +/-0.05 pp
the two-decimal presentation suggests.** That is the honest error bar on CLAIM B, and it
is dominated by a calibration the project has already told itself is unmeasured.

---

## §3 Independent numerical reproduction

### 3.1 Geometry, identified not assumed (MEASURED)

`rawpy`: `raw_image_visible` is `(4688, 7028)` at `top_margin=0, left_margin=0`.
`raw_image` is `(5120, 7168)`; rows >= 4688 are exactly zero and columns >= 7040 are
exactly zero (MEASURED, script 02 probe). `rawler`'s active area is 7032 x 4688 at
origin (0,0) (`plane.rs:155`, `strehl-raw/src/lib.rs` module docs). **Both crops start at
(0,0)**, so the numpy plane lattice and the Rust plane lattice are the same lattice;
the numpy plane is only 2 px narrower (3514 vs 3516) at the right edge, which neither
ROI reaches. There is NO offset to correct.

CFA phase verified rather than assumed (MEASURED, script 02): sub-lattice means
`(0,0)=1001.12`, `(0,1)=1909.78`, `(1,0)=1908.53`, `(1,1)=1486.59` — the two greens
agree to 0.07%, R and B do not. G1 at `(x=1,y=0)`, G2 at `(x=0,y=1)`, matching
`CfaPlane::rggb_offset`.

### 3.2 A check that does not involve the metric under test (MEASURED)

| quantity | Rust run | my numpy |
|---|---|---|
| flat ROI `2272,1344` mean | 2020.29 DN | **2020.2861** |
| flat ROI `2272,1344` sigma | 28.201 DN | **28.2007** |
| flat ROI `2352,1408` mean | 2019.38 DN | **2019.3762** |
| flat ROI `2352,1408` sigma | 27.491 DN | **27.4909** |

Geometry and decode agree.

### 3.3 The single reference frame (MEASURED, script 02)

| ROI | column | Rust | my numpy |
|---|---|---|---|
| `1630,1044` | corrected | 18.7332 | **18.7332** |
| | raw rms | 25.3920 | **25.3920** |
| | model noise | 17.1412 | **17.1412** |
| | m2 | 11.8907 | **11.8907** |
| | iso | 18.4576 | **18.4576** |
| `64,800` | corrected | 39.4918 | **39.4918** |
| | raw rms | 49.1005 | **49.1005** |
| | model noise | 29.1763 | **29.1763** |
| | m2 | 18.5840 | **18.5840** |
| | iso | 29.7240 | **29.7240** |

### 3.4 The merge, re-implemented in numpy (MEASURED, script 03)

I re-implemented pass one and pass two from `merge.rs`/`focus.rs`/`boxfilter.rs` in
numpy — Sobel/8 with replicate clamp, 27x27 box mean, divide by the calibrated
green-luma sigma, 17x17 box regulariser, argmax with ties to the lower index, then
admit `k` iff it is the winner or `best - focus <= gate*sqrt(2)*0.015214`, average
admitted G1/G2 in raw DN. Only a crop with a 24 px margin per ROI is processed; the
regularised focus value reaches 1+13+8 = 22 px, so every value used is what the full
plane would give.

**ROI A `1630,1044` — my numbers, with the Rust run's in brackets where they differ:**

```
  gate  corrected  retention    raw_rms   noise_rms         m2        iso   n_eff(roi)
  0.00    23.5395     1.257x    29.1091    17.1240    12.6541    19.6696      1.000
  0.50    23.5625     1.258x    27.7924    14.7387    11.3547    17.6611      1.640
  1.00    23.5504     1.257x    26.6405    12.4537    10.2453    15.9459      2.391
  2.00    23.4970     1.254x    25.4698     9.8286     9.0637    14.1150      3.671
  4.00    23.1517     1.236x    24.4171     7.7585     8.0630    12.5632      6.163
  8.00    22.4604     1.199x    23.1781     5.7233     6.8975    10.7449     13.614
  gate 0 -> gate 8 :  m2 12.6541 -> 6.8975 (-45.5%)   corrected 23.5395 -> 22.4604 (-4.6%)
```

**ROI B `64,800`:**

```
  0.00    39.1378     0.991x    48.6292    28.8622    19.5306    31.1880      1.000
  0.50    38.4882     0.975x    46.8931    26.7883    18.3380    29.3479      1.281
  1.00    38.1713     0.967x    45.3381    24.4642    17.1661    27.5463      1.617
  2.00    37.6324     0.953x    42.6961    20.1683    15.0922    24.3468      2.450
  4.00    37.3467     0.946x    40.3383    15.2448    12.7265    20.6828      4.225
  8.00    37.7404     0.956x    39.3000    10.9612    10.8081    17.7752      8.758
  gate 0 -> gate 8 :  m2 19.5306 -> 10.8081 (-44.7%)   corrected 39.1378 -> 37.7404 (-3.6%)
```

**Every cell of both tables matches the Rust run to all four printed decimals**
(`experiments/m38-detail-metric/out/02-merge-roi-pair-A.txt` and `03-...-B.txt`).
Not one digit differs, including the winner-dependent columns. So:

- **CLAIM B's arithmetic is CONFIRMED**: -45.5% / -44.7% uncorrected, -4.6% / -3.6%
  corrected, on the two ROIs, from an implementation that shares no code with the
  author's.
- The §2.3 side claim also reproduces: gate 0 -> gate 2.0 costs **-0.2%** (ROI A) and
  **-3.8%** (ROI B) of corrected gradient. (MEASURED)

**What this does and does not establish (ARGUED).** It establishes that the numbers are
the numbers — no arithmetic slip, no index bug, no ROI mix-up, and the merge rule in
`merge.rs` is the rule that produced them. It does **not** establish that the corrected
metric measures detail, because I wrote my implementation *from* the Rust source: it is
an independent implementation, not an independent specification. §2 and §5 attack that.

---

## §4 The hand calculation, checked

**MEASURED (script 02):** the ROI `1630,1044` black-subtracted mean is **394.6235 DN**, and
`detail_metrics` returns `noise_rms = 17.14123`.

**DERIVED, by hand, from the profile alone:**

```
g       = ISO/436.8 = 160/436.8            = 0.36630037 DN/e-
read_dn = 4.20 e- * g                      = 1.53846154 DN     (ISO 160 < 400)
Var_G   = g*394.6235 + read_dn^2 = 144.5507 + 2.3669 = 146.9176 DN^2
sigma_G = 12.12095 DN
sigma_L = sigma_G / sqrt(2)                = 8.57085 DN         (L = (G1+G2)/2)
2*sigma_L                                  = 17.14169 DN
```

Against the code's 17.14123 DN: **agrees to 2.7e-5 relative.** CONFIRMED.

### 4.1 Is the sqrt(2) and the factor of 2 justified, or fitted? (DERIVED)

Both are forced by §1's algebra, not fitted:

- The **sqrt(2)** is `Var(L) = (Var(G1)+Var(G2))/4 = Var(G)/2` for two independent greens.
  It is asserted in `noise.rs`'s own unit test
  `green_luma_sigma_is_the_averaging_of_two_independent_greens`.
- The **factor 2** is `sqrt(2+1+1) = sqrt(4)`: the coefficients of §1 sum to 4, so
  `noise_rms = sqrt(4*sigma^2) = 2*sigma`.
- And it lands exactly at the ROI **mean** signal because `sigma^2(S) = g*S + read^2` is
  **affine** in S, so `mean_i(sigma_i^2) = sigma^2(mean_i S_i)` identically — no
  small-variation approximation is needed. Verified numerically in script 01
  (`148.28807964` both ways).

### 4.2 But the check is weaker than it looks (MEASURED, script 04(a))

The hand calculation constrains only the **sum** of the coefficients and the sqrt(2). It
cannot see the `(2,1,1)` structure at all, because sigma is nearly constant over the ROI:

```
  ROI A: (2,1,1) as shipped 17.14123 | (1,1,2) -0.0029% | (4,0,0) +0.0025% | (0,2,2) -0.0025%
  ROI B: (2,1,1) as shipped 29.17630 | (1,1,2) -0.0824% | (4,0,0) +0.0884% | (0,2,2) -0.0885%
```

So "17.1412 vs 2*sigma = 17.14" validates *that the model is the calibrated one and that
the total weight is 4*. It does **not** validate the derivation in §1.3 of the doc block.
That validation exists only in my script 01, and (see §5, attack 1) in no test in the
repository.

---

## §5 Attempts to break it

Eight attacks. Three succeeded, five failed. All in `experiments/m39-verify/src/08`, `09`, `10`.

### 5.1 FAILED — the positive control the author did not run, and it passes

The strongest possible attack on CLAIM A is: *if the corrected metric reads the merge at
-4.6%, what does it read the known-bad plain mean at?* Fact 19/24 measured a plain
unweighted mean at 0.534x noise and -58%/-53% detail collapse. If corrected reads the
plain mean at about -4.6% too, invariant 2 is not an acceptance test at all.

**MEASURED (script 09(a)), all 22 frames, same ROIs, same code path:**

```
                      corrected  vs gate0   raw_rms  noise_rms       m2  vs gate0
  ROI A
   gate 0 (selection)    23.5395    +0.00%   29.1091    17.1240  12.6541    +0.00%
   gate 2.0              23.4970    -0.18%   25.4698     9.8286   9.0637   -28.37%
   gate 8.0              22.4604    -4.58%   23.1781     5.7233   6.8975   -45.49%
   PLAIN MEAN n=22       12.1387   -48.43%   12.6770     3.6549   5.0229   -60.31%
  ROI B
   gate 0 (selection)    39.1378    +0.00%   48.6292    28.8622  19.5306    +0.00%
   gate 2.0              37.6324    -3.85%   42.6961    20.1683  15.0922   -22.73%
   gate 8.0              37.7404    -3.57%   39.3000    10.9612  10.8081   -44.66%
   PLAIN MEAN n=22       34.0653   -12.96%   34.6285     6.2199   8.8057   -54.91%
```

**The metric discriminates.** It reads the plain mean at **-48.4%** and **-13.0%** against
the gated merge's -4.6% and -3.6% — a factor of 10.6 and 3.6. The attack failed and CLAIM
A is stronger for it: this is the missing positive control, and it passes.

**Free bonus (MEASURED):** against the single frame rather than gate 0, the plain mean's
`m2` is **-57.8%** (ROI A) and **-52.6%** (ROI B). Fact 24 published **-58%** and **-53%**.
Fact 24 reproduces to 0.2 and 0.4 percentage points on this stack, from an independent
implementation, and its baseline is thereby identified as the single frame.

### 5.2 SUCCEEDED — the correction leaves the selection-noise confound in place

`predicted_sigma` is `sigma_model(luma)/sqrt(n)`. At gate 0, n = 1, so it predicts
**exactly** the single-frame sigma. But a selector is measurably noisier than one frame —
that is fact 19's entire subject.

**MEASURED (script 10), on the FLAT ROI `2272,1344`, where there is no detail to gain:**

```
  single frame 11:            sigma 28.2007 DN   m2 23.2791   raw_rms 41.2512
                              model noise_rms 38.5328   corrected 14.7270
  unregularised argmax        flat-sigma ratio 1.0678x   m2 24.3052 (+4.41%)   raw_rms +4.65%
                              corrected with the SHIPPED model    19.4948  (+32.37%)
  17x17-regularised argmax    flat-sigma ratio 1.0739x   m2 24.4521 (+5.04%)   raw_rms +5.21%
                              corrected with the SHIPPED model    19.9501  (+35.47%)
```

The regularised argmax reproduces fact 23's **1.075x** (I get 1.0739x) and the M38 run's
1.074x — an independent third confirmation of fact 321. And on that same flat ROI **the
shipped corrected metric credits it with +35.5% "detail"**, in a region where selection
cannot create any. That excess is the winner's curse, and the correction does not remove
it because the model has no term for it.

**Consequence for CLAIM B, quantified (MEASURED, script 04(d)):** the gate-0 reference is
inflated by this and gate 8 much less so, so the published figure is **pessimistic**. If
the gate-0 output really is 1.074x noisier than one frame while the model says 1.000x:

```
   ROI A: corrected0 22.5634 (was 23.5395), retention -0.46% (was -4.58%)
   ROI B: corrected0 37.4689 (was 39.1378), retention +0.72% (was -3.57%)
```

The true reading is somewhere in **-4.6% .. -0.5%** (ROI A), because the selection excess
is largest in a flat region and smaller where the focus peak stands clear of noise. It does
not overturn CLAIM B; it does mean CLAIM A's "the correction removes the confound" is only
**partly** true — it removes the model-predicted part, not the selection-induced part,
which is the part fact 19 is about.

### 5.3 SUCCEEDED — an RMS metric bounds the strongest edges, not "detail"

**MEASURED (script 09(b)), on the real gate-0 merged ROIs:**

```
  ROI A: the top 1.30% of difference pairs carry 50% of the squared-gradient energy;
         the strongest 10% carry 73.53%.
  ROI B: the top 1.49% carry 50%; the strongest 10% carry 78.15%.
```

**MEASURED (script 08 attack 4):** on a synthetic field with the same shape — 7 strong step
edges plus low-contrast fine texture everywhere — deleting **100%** of the fine texture
costs the corrected metric **-0.66%** while costing `m2` -44.64%.

So "corrected retention -4.6%" is compatible with total loss of low-contrast fine detail.
Invariant 2 as measured proves something about the strongest few percent of edges in the
ROI. It does not bound fine texture, which is what a focus stack is usually bought for.
This is a **scope** defect in the claim, not an arithmetic one.

### 5.4 SUCCEEDED — the correction is exact only for pixel-independent noise

**MEASURED (script 08 attack 6):** same signal, same **marginal** sigma of 12.0 DN, three
noise spatial structures, corrected against a true (noise-free) value of 23.1781:

```
  white (model is right)   raw_rms 33.311  corrected 23.0999   ( -0.34%)
  correlated 3x3           raw_rms 27.022  corrected 12.4173   (-46.43%)
  anti-correlated          raw_rms 34.836  corrected 25.2502   ( +8.94%)
```

Nothing in the *current* pipeline correlates noise between plane pixels — no alignment, no
resampling, no sharpening, and G1/G2 at neighbouring plane pixels are disjoint photosites —
so this does not touch CLAIM B. But **alignment and deconvolution are both on the project's
roadmap**, and they sit on opposite sides of this: resampling makes the metric
**conservative** by up to -46%; any sharpening or deconvolution makes it **optimistic**, and
an optimistic detail metric would credit amplified noise as detail. The doc block does not
state the independence assumption as a precondition.

### 5.5 FAILED — over-correction into the `max(0, .)` clamp

**MEASURED (script 08 attack 5):** sweeping signal contrast against a fixed 12 DN noise:

```
   contrast   raw_rms  noise_rms  corrected(noisy)  corrected(clean)   error
      1.000    33.316     24.000           23.1080           23.1781    -0.30%
      0.500    26.538     24.000           11.3259           11.5890    -2.27%
      0.250    24.491     24.000            4.8801            5.7945   -15.78%
      0.100    24.209     24.000            3.1745            2.3178   +36.96%
      0.020    23.877     24.000            0.0000            0.4636  -100.00%
```

The estimator does fall apart, and clamps, once the signal gradient drops below roughly
half the noise gradient. **But the real ROIs are not there:** ROI A at gate 0 sits at
corrected/noise = 23.54/17.12 = **1.38**, ROI B at 39.14/28.86 = **1.36**, and at gate 8 at
3.92 and 3.44. All are at or above the "contrast 1.0" row. The attack fails here, but it
locates the boundary, and `run()` only guards `base.corrected_rms > 0.0`, which is a much
weaker bar than this data would need on a darker or lower-contrast ROI.

### 5.6 FAILED — selection seams manufacturing gradient at gate 0

If adjacent pixels take different frames, the step between them is gradient that is not
detail, and it would inflate the gate-0 denominator. **MEASURED (script 08 attack 2):**

```
  ROI A: 3.65% of difference pairs cross a winner boundary, carrying 1.63% of the
         squared-gradient energy; mean squared gradient across a seam is 0.44x the
         within-winner value.
  ROI B: 3.99% of pairs cross a boundary, carrying 4.68% of the energy; 1.18x.
```

Seams sit in *flatter* places than average in ROI A and are barely above average in ROI B.
Worth at most a few tenths of a percent. **Attack failed.**

### 5.7 FAILED — is the metric too blunt to see blur at all?

**MEASURED (script 09(c)):** taking the quietest merged output as signal, blurring **only
the signal**, then adding fresh independent noise at the gate-0 model level:

```
  ROI A     blur sd 0.30 -> -0.02%   0.40 -> -3.83%   0.60 -> -16.22%
  ROI B     blur sd 0.30 -> -0.35%   0.40 -> -3.07%   0.60 -> -9.45%
```

**MEASURED (script 10):** the metric's own repeatability under a fresh noise draw on a
fixed signal is sd **0.269%** (ROI A) and **0.315%** (ROI B).

So -4.58% is about 17 sigma of its own sampling noise, and corresponds to roughly
**0.42 plane px** (0.84 sensor px) of Gaussian blur. Below about 0.3 px the metric cannot
see blur above its own scatter. The attack fails: the metric is not blunt in the regime it
is being used in. It does mean invariant 2 cannot certify sub-0.3 px sharpness.

### 5.8 FAILED — is the `(2,1,1)` structure actually load-bearing?

**MEASURED (script 08 attack 1)**, on the real merged output where `n` runs 1..22 and sigma
runs 0.9..20 DN:

```
  ROI A gate 8.0  n in [1,22]  sigma 1.556-14.139 DN  corrected 22.4604
                  (1,1,2):-0.001%  (4,0,0):+0.004%  (0,2,2):-0.004%
  ROI B gate 0.0  n in [1,1]   sigma 3.979-20.209 DN  corrected 39.1378
                  (1,1,2):+0.046%  (4,0,0):-0.049%  (0,2,2):+0.049%
```

The structure is right (script 01) but worth under 0.05% here. **Test gap, however:** every
`detail_metrics` test in `merge_cmd.rs` passes a spatially **uniform** sigma
(`vec![0.0; ..]` or `vec![sd; ..]`), and a uniform sigma cannot distinguish any coefficient
set that sums to 4. **The `2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2` derivation is
untested in the repository.** `cargo test --release -p strehl-cli` -> `34 passed; 0 failed`,
and none of the 34 can see it.

### 5.9 SUCCEEDED — the "~90% explained" figure mixes two statistics

M38 §2.3 says the noise correction explains "~90%" of the apparent collapse. **MEASURED
(script 11(a)):** that figure compares a **fall in `m2`** (-45.49%) against a **fall in
corrected RMS** (-4.58%) — two different statistics, one a mean absolute gradient, the
other a root-mean-square. Computed within a single statistic:

```
                     raw_rms fall   corrected fall   explained
   ROI A                 -20.38%          -4.58%       77.53%
   ROI B                 -19.19%          -3.57%       81.40%
   (author, m2 vs corrected)                           89.9% / 92.0%
```

The correction really does explain most of the collapse — the qualitative claim survives —
but the honest number is **78% / 81%**, not 90% / 92%. The published pair is inflated by
about 11 percentage points by the convention change.

### 5.10 CLAIM D — reproduced in direction; the 1.253x itself I could not reproduce

**MEASURED (script 10)**, argmax selection versus the single middle frame:

```
                             ROI A          ROI B      flat ROI 2272,1344
   17x17-regularised argmax
      m2                    +6.42%         +5.09%          +5.04%
      raw_rms^2            +202.6 DN^2                     +5.21% in raw_rms
      flat-ROI sigma ratio                                 1.0739x
   unregularised argmax
      flat-ROI sigma ratio                                 1.0678x
```

So argmax does raise gradient and does raise noise, in the same ROI and the same run, on a
flat patch where the gradient increase cannot be detail. **The confound in fact 24 is
real and is the same confound as CLAIM A, with the sign reversed. CLAIM D is confirmed in
direction.**

The **share** is where I part company with the framing. At the noise inflation I can
actually measure for the shipped operator (1.0739x), the noise accounts for about **22%**
of the squared-gradient increase on ROI A. Fact 19's **1.253x** would make it about **83%**.
Those are very different statements, and I **could not reproduce 1.253x**:

- Fact 19 comes from M2, whose focus measure was `ring(1,3)`, not the shipped Tenengrad.
- `focus.rs`'s own comment records **1.3475x** for `ring(1,3)`, **1.1324x** for
  `tenengrad` at w5 and **1.0864x** at w13.
- My independent measurement of the shipped operator on this stack is **1.0739x**
  (regularised) / **1.0678x** (unregularised) on a flat ROI.

Facts 19 and 24 are internally consistent with each other (same M2 harness, same operator),
so pairing them is legitimate. But **1.253x is not the inflation of the operator the project
now ships**, and if fact 24's -58%/-53% is being reinterpreted for today's merge, the
inflation to pair it with is ~1.07x, not ~1.25x. I state this as a **precision** objection
to CLAIM D, not a refutation: the direction and the existence of the confound are confirmed.

---

## §6 Verdicts

### CLAIM A — the metric is confounded by noise, same sign as blur: **CONFIRMED, with two qualifications**

**Evidence for (MEASURED):** on a flat ROI containing no detail at all, the regularised
argmax selector raises `mean|grad|` by **+5.04%** while raising the pixel noise by
**1.0739x** (§5.2) — gradient manufactured purely from noise. In the other direction the
plain 22-frame mean cuts noise to 0.53x and cuts `mean|grad|` by **-60.3%** / **-54.9%**
(§5.1) with no blur applied. Both signs demonstrated on real data. And the corrected metric
does discriminate: it separates the gated merge (-4.6%) from the plain mean (-48.4%) by a
factor of 10.6, which the raw `m2` does not (-45.5% vs -60.3%, a factor of 1.3).

**Qualification 1:** the correction removes the *model-predicted* noise, not *all* noise.
It leaves the selection-induced excess untouched, and I show that residual crediting a flat
ROI with **+35.5% detail** (§5.2). CLAIM A's diagnosis is right; the cure is partial.

**Qualification 2:** the corrected statistic is an RMS and is dominated by the top ~10% of
edges (73-78% of the energy, §5.3). It does not bound low-contrast fine texture; a
synthetic losing 100% of its fine texture reads -0.66%.

### CLAIM B — -45% becomes -4.6% / -3.6%: **CONFIRMED numerically, with a wider error bar than published**

**Evidence (MEASURED, §3):** an independent numpy re-implementation of the whole pipeline
(rawpy decode, CFA extraction, Tenengrad/sigma focus field, 27x27 window, 17x17
regularisation, argmax, gate admission, average, both metrics) reproduces the author's
Rust output for **every cell of both six-gate tables to 4 decimals**, including
`12.6541 -> 6.8975` (-45.49%) and `23.5395 -> 22.4604` (-4.58%) on ROI A, and
`19.5306 -> 10.8081` (-44.66%) and `39.1378 -> 37.7404` (-3.57%) on ROI B.

**Caveat 1 (MEASURED, §2.3):** the figures move +/-2 pp under the measured uncertainty in
the noise model's absolute scale (-6.3%..-2.2% on ROI A). That uncertainty is not stated
in M38, while the ~0.05 pp FPN uncertainty is.

**Caveat 2 (MEASURED, §5.2):** the gate-0 reference is optimistic about its own noise, so
the published figure is pessimistic by up to ~4 pp.

**Caveat 3 (MEASURED, §5.9):** the accompanying "~90% explained" is 78% / 81% within one
statistic.

**Independence note:** my implementation is independent *code* but not an independent
*specification* — I read `merge.rs` to write it. A shared misreading of intent would not be
caught by this. A shared arithmetic error would.

### CLAIM C — the formula is exact: **CONFIRMED**

**Evidence (DERIVED + MEASURED, §1):** I derived `E[(dx)^2 + (dy)^2] = (signal terms) +
2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2` from scratch before reading the author's
derivation, and the `2` is right: pixel i appears in both `dx` and `dy`, contributing
`sigma_i^2` to each. A 4-million-trial Monte Carlo on a 9x7 plane with deliberately
non-uniform sigma matches to 0.096 on a quantity of ~42 (0.2%), while the three
sum-preserving rivals `(1,1,2)`, `(4,0,0)`, `(0,2,2)` miss by 24 to 39.

**Preconditions, all four of which hold in the current pipeline but only three of which are
stated:** zero-mean noise; noise independent of signal *given* S; **noise independent
between plane pixels** (unstated; §5.4 shows -46% / +9% errors when violated); and
sufficient SNR that the clamp is not active (§5.5 locates the failure at
corrected/noise < ~1, real data at 1.36-3.92).

**Test gap (MEASURED):** `cargo test --release -p strehl-cli` -> `34 passed; 0 failed`, but
every metric test uses a spatially uniform sigma, which cannot distinguish `(2,1,1)` from
any other set summing to 4. The coefficient structure ships untested.

### CLAIM D — fact 24 carries the same confound reversed: **CONFIRMED in direction; the 1.253x COULD NOT BE VERIFIED**

**Evidence for (MEASURED, §5.10):** argmax raises `m2` by +6.42% / +5.09% over one frame on
the two detail ROIs, and by +5.04% on a **flat** ROI where it cannot be detail, while
raising noise 1.0739x. Same confound, opposite sign. Confirmed.

**What I could not verify:** fact 19's **1.253x**. It belongs to M2's `ring(1,3)` focus
measure, not the shipped Tenengrad; `focus.rs`'s own comment gives 1.3475x for `ring(1,3)`
and 1.0864x for tenengrad at w13, and I measure **1.0739x** for the shipped operator on this
stack. The share of fact 24's gradient rise that is noise is therefore ~**22%** for today's
operator, not the ~83% that 1.253x would imply. Facts 19 and 24 are consistent with each
other; the number should not be carried over to the current merge.

**Free replication (MEASURED, §5.1):** fact 24's -58% / -53% reproduces at **-57.8%** /
**-52.6%** from my independent implementation, identifying its baseline as the single frame.

---

## §7 Defects found, in order of consequence

1. **The correction does not remove selection-induced noise, and the doc block implies it
   removes the confound.** `predicted_sigma` (`merge.rs:445`) is
   `green_luma_sigma(luma)/sqrt(n)` with no selection term. At gate 0 it returns exactly the
   single-frame sigma where 1.074x is measured. Reproduce: script 10, flat ROI `2272,1344` —
   the corrected metric credits argmax with +35.5% detail on a flat patch. Consequence: the
   -4.6% headline is pessimistic; the true value is in -4.6% .. -0.5%.

2. **The stated error budget is inverted.** M38 flags FPN (worth 0.01-0.05 pp at the
   measured DSNU floor of 0.377 DN) and does not flag the noise-model scale (worth +/-2 pp,
   and DERIVED-not-measured by the run's own banner). §2.2, §2.3.

3. **"~90% of the apparent collapse is explained" compares `m2` against corrected RMS.**
   Within one statistic it is 77.5% / 81.4%. §5.9.

4. **An RMS metric on a top-heavy gradient distribution does not bound fine detail.**
   73.5% / 78.2% of the energy is in the top 10% of pairs; 100% loss of low-contrast texture
   reads -0.66%. Invariant 2 proves less than "detail is not collapsed". §5.3.

5. **The pixel-independence precondition is unstated**, and alignment / deconvolution (both
   on the roadmap) violate it in opposite directions: -46% conservative and +9% optimistic
   respectively. §5.4.

6. **No test can see the `(2,1,1)` coefficient structure** — all seven `detail_metrics` tests
   pass uniform sigma (`merge_cmd.rs:1537, 1579, 1600, 1631, 1676, 1696, 1697`). The structure is correct (I verified it) but it ships untested. §5.8.

## §8 What I could not verify

- **PRNU / signal-proportional fixed pattern.** My disjoint-half bound (f <= 5.1 DN) is
  contaminated by shared scene texture because the halves are interleaved and share a mean
  drift position. A first-half/second-half split would decorrelate the scene further; I did
  not run it. The project's own open question 5 owes flat fields for this.
- **Fact 19's 1.253x**, for the reason in §6/CLAIM D — the operator it was measured on is
  not the operator in the repository.
- **The size of the winner's curse inside a detail ROI.** I measured 1.0739x on a flat ROI
  and argue it must be smaller where the focus peak stands clear of noise, but I did not
  measure it there, so §5.2's -0.46% is a bound, not a value.
- **Absolute pixel identity between my numpy planes and the Rust planes.** I verified both
  crops start at (0,0) and that every printed statistic matches to 4 decimals, which is
  strong evidence, but the numpy plane is 2 px narrower at the right edge (2344x3514 vs
  2344x3516) and I did not do a byte-level comparison of the decoded arrays.
- **Whether the profile's RN_e = 4.20 e- already contains the fixed pattern.** This decides
  between the P1 and P2 parameterisations in §2.1; I report both as a bracket rather than
  choosing.

---

## §9 Provenance of what I actually tested

**MEASURED.** The code under test is **uncommitted working-tree code**, not a commit:

```
> git --no-pager status --porcelain
 M crates/strehl-cli/src/main.rs
 M crates/strehl-cli/src/merge_cmd.rs      <- detail_metrics lives here, +452/-? lines uncommitted
 M crates/strehl-core/src/focus.rs
 M crates/strehl-core/src/lib.rs
 M experiments/m23-metacal/src/main.rs
?? docs/research/M39-verify-detail-metric.md   <- this file (mine)
?? experiments/m39-verify/                     <- my scripts and outputs (mine)
```

I confirmed `merge_cmd.rs` did not change under me during the run
(SHA-256 `178B7E97...F47F` at two times 20 s apart, identical), and re-read
`detail_metrics` at `merge_cmd.rs:276-310` and `predicted_sigma` at `merge.rs:445` after
finishing to confirm they are the functions I verified. **Everything above is a verdict on
that snapshot.** Nothing I verified is pinned to a commit hash, so it can move.

**MEASURED.** `cargo test --release -p strehl-cli` -> `test result: ok. 34 passed; 0
failed; 0 ignored`. All 34 pass. None of them exercises a spatially non-uniform sigma.

## Evidence index

| script | what it establishes |
|---|---|
| `01-algebra.py` | independent derivation + 4e6-trial MC of the `(2,1,1)` coefficients vs 3 rivals; affine-variance identity |
| `02-single-frame.py` | geometry and CFA phase identified; single-frame metrics reproduced to all printed digits |
| `03-merge-numpy.py` | full numpy re-implementation of pass 1 + pass 2; both 6-gate tables reproduced to 4 dp |
| `04-sensitivity.py` | coefficient-structure discrimination on real data; model-scale `k` sweep; FPN sweep; winner's-curse sweep |
| `05,06-noise-scale*.py` | photon-transfer and temporal-pair measurement of `k`; disjoint-half FPN bound; ARW not code-quantised |
| `07-save-merged.py` | merged / winner / n arrays saved for the attacks |
| `08-break.py` | 6 attacks: structure, seams, blur, RMS blindness, low-SNR clamp, correlated noise |
| `09-control.py` | **the plain-mean positive control**; gradient-energy concentration; clean blur calibration |
| `10-claim-d.py` | argmax noise inflation and gradient rise, flat ROI and both detail ROIs; metric repeatability |
| `11-closing.py` | the "90%" figure within one statistic; FPN under P1/P2; retention band from measured `k` |
| `12-gate2.py` | FPN and `k` sensitivity **at gate 2.0**, the gate the design actually rests on |
