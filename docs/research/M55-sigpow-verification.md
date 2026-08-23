# M55 — Adversarial verification of M46's `sigpow` detail metric

**Verdict: `sigpow` reproduces M46's 0.937 separation exactly on M46's own plant, but it is not a detail metric — it is non-monotone in true resolution (it reads 2.03x *above* baseline while true MTF is 0.007), it is exactly quadratic in photometric gain, it separates at S = 0.523 / 0.464 rather than 0.937 / 0.917 on real disjoint half-stack merges, and when used as M46 proposes to score a real merge parameter it names near-pure per-pixel selection (n_eff = 1.55) as the most detailed configuration — so fact 619 is refuted, fact 610's attribution to fixed-pattern noise is refuted by direct measurement of 242 dark frames (231x shortfall in variance), fact 620 is refuted, while fact 617's algebra and M46's matched-cost design both survive intact.**

Milestone M55. Read-only with respect to `crates/`, `experiments/m46-detail-metric/` and
`experiments/m41-r3-kill/` — verified by `git status` at commit time. All new work is under
`experiments/M55-sigpow-attack/`.

---

## 0. On the brief

The brief was checked for a smuggled expected sign (discipline 305). **It is clean.** Every
one of the five suggested attack routes is phrased as a mechanism plus an observable
("check whether that asymmetry is doing the work", "a directly measured `rho` that agrees or
disagrees"). Route 2 is the closest to a direction — quoting fact 614's asymmetry — but it
names the mechanism and asks whether it is load-bearing rather than asserting that it is.
**It was right to ask and the answer was no** (PR7 below): the matched-cost design survived,
and that was *my* objection that the data refuted, not the brief's.

---

## 1. Pre-registration

Thirteen predictions were registered with a success criterion **and an explicit falsifier of
my own objection** before the deciding run. PR1–PR9 in the session store before any script
ran; PR10–PR13 in the script docstrings, which are committed in the same commit as their
output, so the ordering is checkable.

| PR | Target | Criterion | Outcome |
|----|--------|-----------|---------|
| PR1 | fact 610 `rho` is FPN | refuted if dark FPN + <=1% PRNU cannot reach within 2x in variance | **refuted, 231x** |
| PR2 | fact 612 FPN white / censoring | white if ring spectrum flat +-20%; mechanism refuted if real `C` is >4x FPN | **split: white yes, amplitude no** |
| PR3 | fact 610's out-of-sample check | no power if the formula tracks every planted `rho` to <2% | **no power** |
| PR4 | photometric sensitivity | defect if `eps*` < 1% | **defect, `eps*` ~ 0.4%** |
| PR5 | rule 18, fooled upward? | inadmissible if sigpow >= baseline while true MTF falls | **fooled upward, +17.3%** |
| PR6 | does the product escape 617? | fails if S <= 0.5 against a contrast-restoring low-pass | **fails, S = 0.095** |
| PR7 | is 0.937 operating-point-specific? | specific if S moves by more than +-0.05 over `k` | **my objection REFUTED** |
| PR8 | fact 620 on real half-stacks | survives if S >= 0.90 with no plant; refuted if S < 0.5 | **refuted / partial: 0.523, 0.464** |
| PR9 | implementation vs concept | H1 if `sigpow_ring/C_direct` within 2% and S >= 0.90 | **both, quantified** |
| PR10 | is PR5 an amplitude artefact? | property if sigpow >= baseline at every width | **worse: non-monotone** |
| PR11 | score the real merge gate | prediction: sigpow rises as the gate *widens* | **MY PREDICTION REFUTED, sign inverted** |
| PR12 | scale invariance | derived: exponent 2 | **exactly 2.000000** |
| PR13 | which factor carries PR11 | decomposition, no direction | **entirely `P_ring`** |

Two of the thirteen refuted my own stated objection. Both are reported as such.

---

## 2. What survives

### 2.1 Fact 617 is correct, and it is correct for the reason M46 gave — MEASURED

Against a linear post-filter, `frc2_at_fsig` reads `d = +0.0001` (`e5`, ARM 0) and against
a contrast-restoring low-pass `d_sigpow = +0.00005` with FRC unmoved. The ratio `C/(C+U)`
genuinely cannot move under a common `|H|^2`. **Fact 617 survives without qualification.**

### 2.2 `C` really is noise-invariant *as an estimator* — MEASURED, and this is M46's algebra vindicated

The sharpest thing I can say in M46's favour is a control it did not run. In `e4`, I added
**15.6 / 37.1 DN of independent white noise** back onto the shipped half-merge pair, which
leaves the delivered scene untouched by construction:

```
  1/2 pair            C  3.9166e+07  P_a  5.6756e+07  FRC  0.8487
  1/2 + noise (x4)    C  3.7308e+07  P_a  6.5875e+07  FRC  0.4900
  C moved by  -4.743%  (M3 is live if |.| > 10%)
```

FRC collapsed 0.849 -> 0.490 and `C` moved 4.7%. On the flat ROI, 6.6%. **`sigpow = C` is a
real and correct identity, and `C` is genuinely blind to added noise.** M46's §6.5 derivation
is right. What fails is not the algebra — it is the premise that the two half-merges being
compared deliver the *same latent*, which is §3.4 below.

### 2.3 The matched-cost design is fair — MY OBJECTION REFUTED (PR7) — MEASURED

I predicted that matching on `hp_sd` was easier to satisfy in the smoothing arm and was
manufacturing the separation. Sweeping the smoothing factor `k` from 1.05 to 8.0:

```
     k       matched sb    S(sigpow)  S(ringpow)  S(hp_sd)  S(oracle_mtf)
    1.050       0.02155       0.942      0.590      0.501      0.963
    1.414       0.04999       0.937      0.587      0.501      0.958
    8.000       0.06999       0.917      0.578      0.501      0.938
```

S(sigpow) moves by 0.025 over a 60x range of `k`. **The matched-cost design is not doing the
work; my objection is wrong and fact 614's asymmetry is not the mechanism.** Worth noting
for scope: matched `sb` saturates at 0.07 px even at k = 8, so M46's entire separation
experiment lives in blurs below a tenth of a pixel. That is fact 614 restated, and it matters
for §3.1.

### 2.4 FPN is approximately white — MEASURED, on 242 dark frames

The dark cross-half FPN ring spectrum at ISO 500 reads **0.0989 DN² at `f_sig` and 0.0788 DN²
at 0.45 cyc/px**. Flat to about 20% across the band. **Fact 612's whiteness sub-claim
survives.** Its amplitude and attribution do not (§3.2).

### 2.5 M46's plant reproduces exactly from an independent implementation — MEASURED

`e5` ARM 0, written from the paper rather than by calling `b3`, lands on matched
`sb = 0.04999 px` against b3's published 0.04999, `S(sigpow) = 0.937` against 0.937,
`S(hp_sd) = 0.501` against 0.501, `ringpow 0.587`, `mean_grad 0.233`. **M46's numbers are
not a reporting error and nothing in this report is an arithmetic dispute.** Every finding
below is about what the plant cannot express.

---

## 3. What does not survive

### 3.1 `sigpow` is non-monotone in true resolution, and is fooled upward — PR5/PR10 — MEASURED

Rule 18 requires a stated failure direction. M46 gives none. Adversary **PM_M**: destroy real
resolution with a blur, add a fixed high-frequency texture *common to both half-merges*, and
solve the amplitude so `hp_sd` returns exactly to baseline. This is not exotic — **any merge
with a component shared between the two halves does it**: a shared guide or reference frame,
a shared flat-field, a shared sharpening or deconvolution kernel, a learned prior, or plain
fixed-pattern noise, which is the case M46 itself identified in fact 612 and treated only as
a nuisance.

At sb = 1.0 px (`e5` PR5):

```
  metric          baseline    blur1.0 only   PM_M (blur+fake)   d(PM_M)   verdict
  hp_sd                58.801       44.493         58.798    +0.0001   blind
  mean_grad            239.32       195.92         270.64    -0.1309   FOOLED UPWARD
  ringpow          5.1222e+07   4.4702e+06     6.0023e+07    -0.1718   FOOLED UPWARD
  frc2_at_fsig        0.99081      0.89393        0.99183    -0.0010   blind
  sigpow_fsig      5.0752e+07   3.9962e+06     5.9533e+07    -0.1730   FOOLED UPWARD
  oracle_mtf           1.0008      0.22043        0.22315    +0.7770   detects
```

PR10 asked whether that was an artefact of one amplitude. Sweeping the blur, re-solving the
amplitude at each width so `hp_sd` is matched to baseline to four figures:

```
    sb    fake amp   hp_sd     oracle_mtf   sigpow/base  c_direct/base  mean_grad/base
   0.25     12.496   58.8009      0.9113        0.9503        0.9506         1.0284
   0.50     23.174   58.7998      0.6870        0.8865        0.8872         1.0721
   1.00     38.373   58.7982      0.2231        1.1730        1.1749         1.1309
   2.00     51.865   58.7973      0.0068        2.0299        2.0331         1.1543
```

This is worse than PR5 reported. **`sigpow` is not a monotone function of the resolution it
claims to measure.** It moves in the correct direction below about 0.7 px of destroyed
detail and **inverts above it**, reading `2.03x baseline` at the point where true MTF at
`f_sig` is `0.0068` — essentially all real detail gone. There is no threshold that makes it
safe, because the response is U-shaped in the thing being measured. `c_direct` tracks it to
0.2%, so this is not the D1/D2 implementation defects: **the concept is fooled, not the
code.** M46's separation experiment sits at `sb ~ 0.05 px`, an order of magnitude inside the
regime where the sign happens to be right (§2.3), which is why the plant never sees this.

### 3.2 Fact 610's `rho = 0.3094` is not fixed-pattern noise — PR1 — MEASURED, out of sample

Open question 142, taken. 242 ARW across 11 ISOs at `D:\macro-dark-frames`, ISO 500 =
`125MSDCF`, same green-quad plane construction and same ROI coordinates as M46, FPN by
disjoint-half cross-covariance:

```
  1. PR1 VERDICT -- can rho = 0.3094 be fixed-pattern noise?
       rho=0.3094 REQUIRES sigma_FPN =  4.390 DN (var   19.270 DN^2)
       measured dark FPN (quad plane, ISO 500) = 0.2888 DN (var  0.08341 DN^2)
       shortfall:    15.20x in sd,     231.0x in VARIANCE
       a multiplicative PRNU term would have to be  4.119% of signal to close it
```

The measurement cross-checks against M50/fact 565 by a different route: M50's 0.3943 DN per
raw pixel becomes 0.2788 DN on the 2-pixel-averaged green quad plane, against my 0.2888 DN —
**3.6% agreement across two decoders, two estimators and two milestones.** The DN²
normalisation was calibrated against a synthetic white field (13.86 measured vs 13.69
expected, ratio 1.013).

`rho = 0.3094` needs **231x more variance than this sensor has**. Closing the gap needs a
4.1% PRNU term; question 111 leaves PRNU unmeasured, but 4.1% is roughly an order of
magnitude above typical CMOS PRNU and I regard it as implausible (ARGUED, not measured).

**`rho = 0.3094` is a valid measurement of a common-mode fraction. Its attribution to
fixed-pattern noise is wrong.** What is common between two half-stack merges of the same
scene is dominated by scene and aliased content, not sensor pattern — measured directly in
`e2`, where `C(f)` on the *flat* ROI runs from `221 959x` the dark FPN level at f = 0.051
down to `44.9x` at f = 0.488, and falls steeply with frequency instead of being flat. A white
FPN component would read the same value at every `f`. It does not.

### 3.3 Fact 610's "0.4% out-of-sample confirmation" has no power to reject anything — PR3 — MEASURED

Rule 21. M46 solves `rho = FRC/(1-FRC)/n_eff` from a reading, then confirms it by planting
`rho` and checking `FRC(0.45)` against `rho/(rho+1/n_eff)`. That is the algebraic inverse of
the equation. Sweeping the planted `rho` over a 150x range:

```
     planted rho   n_eff    predicted    measured    ratio
          0.0200    8.784       0.1494      0.1443    0.9658
          0.3094   10.366       0.7623      0.7606    0.9978
          3.0000   10.366       0.9688      0.9687    0.9998
```

**Every value passes.** The check confirms that `make_fpn` plants the variance it is asked
for and that `frc` implements its own definition. It cannot discriminate `rho = 0.02` from
`rho = 3.0`. The 0.4% figure is a numerical-accuracy statement, not a confirmation.

### 3.4 Fact 620 fails on real disjoint half-stacks — PR8 — MEASURED, no plant anywhere

The shippable configuration, end to end on real photons. 76 frames of 112MSDCF, stride-4
interleaved quarters, merged with frozen `m41lib.arm_A`. BASELINE = (Q0,Q1). SMOOTH =
((Q0+Q2)/2,(Q1+Q3)/2), which is **exactly k = sqrt(2) of real noise reduction with no
synthetic noise anywhere**. BLUR matched on `hp_sd`. Rule 20 positive control first —
planted blur tracks `|H(f_sig)|^2` to 0.02%–2% over sb = 0.05–1.0 px, so the instrument has
power.

```
ROI detail
  metric          baseline      BLUR-ONLY    SMOOTH-ONLY   d_blur   d_smooth      S
  hp_sd                59.887       59.383       59.383 +0.0084 +0.0084   0.500
  mean_grad            238.22       236.63       235.98 +0.0067 +0.0094   0.415
  ringpow          6.5528e+07   6.1951e+07   5.8555e+07 +0.0546 +0.1064   0.339
  sigpow_fsig      4.7737e+07   4.5132e+07   5.0111e+07 +0.0546 -0.0497   0.523

ROI flat
  sigpow_fsig      1.7249e+06   1.1179e+06   2.4259e+06 +0.3519 -0.4064   0.464
```

Against fact 619's **0.937 and 0.917**: measured **0.523 and 0.464**, both below PR8's
pre-registered survival line of 0.90 and at the boundary of its refutation line of 0.50.
Note the sign: `d_smooth` is **negative**. On real data `sigpow` does not merely fail to fall
under pure noise reduction — **it rises**. Pure noise removal is scored as a *gain* in
delivered signal.

**Why**, decomposed in `e3`/`e4` and stated as three separate defects:

- **D1, frequency mismatch (implementation).** `b3` reads FRC by interpolation at
  `f = 0.2762` but takes ring power from the ring whose centre is `0.27734`. On the real flat
  ROI at low FRC this is worth a **factor of 2.1**; on real detail, 1.4%. In the plant, where
  FRC ~ 0.99 and flat, it is invisible.
- **D2, asymmetry (implementation).** `sigpow_ring = C * sqrt(P_a/P_b)`. It equals `C` only
  when the two half-merges have equal ring power, and **it changes if you swap which merge is
  `y1`**. Measured `sqrt(P_a/P_b)` = 0.865 (detail) / 0.839 (flat) on real merges. **M46's
  plant draws both images with identical noise by construction, so this term is exactly 1 and
  can never be seen.** This is a rule-34-shaped blind spot.
- **D3, the premise (conceptual, and the load-bearing one).** `C` is noise-invariant (§2.2),
  yet it still rises **+27% (detail) / +812% (flat)** along a real frame-count ladder. The
  reason is that *a merge of one subset delivers a different latent than a merge of another
  subset* — a nonlinear merge's output scene depends on which frames it was given. `e4`
  splits it with a placebo: a **plain linear mean** on the same subsets already rises
  +16% / +132% (focus-sampling variance), and `arm_A` adds the rest, +36% / +1355%
  (noise-driven selection instability). **M46's plant holds the latent fixed by construction
  and is structurally incapable of expressing this** (rule 13).

So fact 620's stated premise — that two disjoint half-stack merges "share a fixed pattern and
differ in independent noise" — is **false for a nonlinear merge**. They also differ in
delivered latent, and that difference is 10x larger than the effect being measured.

### 3.5 `sigpow` is exactly quadratic in photometric gain — PR4/PR12 — MEASURED

DERIVED: FRC is a normalised correlation and is gain-invariant; ring power is quadratic;
so the product is quadratic. MEASURED on real half-stack merges:

```
     gain g     FRC(f_sig)      P_ring       sigpow    sigpow/sigpow(1)
      0.900     0.868960   4.7735e+07    4.148e+07        0.81000
      1.100     0.868960   7.1308e+07   6.1964e+07        1.21000
  d(log sigpow)/d(log gain) = 2.000000
  FRC total spread over the gain sweep = 1.363e-08
```

The exponent is 2 to six decimal places and FRC does not move at all. On the plant this is
harmless because every arm is built from one latent at one level. On real merges it is not:
PR4 shows a **0.4% gain applied to one arm drops S(sigpow) from 0.937 to 0.493**, and 0.1%
already costs 0.829. And PR11 measures that **changing a real merge parameter moves the median
level by up to 11.7%** — 30x the tolerance. **`sigpow` cannot be used to compare two merge
configurations without a photometric normalisation that M46 does not specify and does not
apply.** A 1.117x level difference is a 1.25x `sigpow` difference with no change in detail at all.

### 3.6 M46's own proposed use, run on real data, names a selector as the winner — PR11 — MEASURED

M46 §8 proposes `sigpow` to test "that gate width trades noise against resolution as claimed".
I ran exactly that, on the fact-620 configuration: two disjoint 36-frame half-stack merges of
112MSDCF, sweeping the acceptance gate. `arm_A_gated` is a documented copy of `arm_A` with
`GATE` lifted to a parameter; `m41lib` was not edited (rule 15) and equality with `arm_A` at
gate 0.5 is **asserted in the script, not assumed** (rule 36) — it printed `True` on both ROIs.

I pre-registered the prediction that `sigpow` would rise as the gate *widened* (more frames
accepted). **The data refuted me with the sign inverted.**

```
ROI detail: two disjoint half-stacks of 36 frames
  gate   n_eff    level DN    hp_sd     P_ring      C_direct     sigpow    sigpow/gate0.5
   0.00  36.000     273.090    12.390   1.2589e+06   7.9738e+05   9.1539e+05     0.0179
   0.50   5.549     244.400    59.466   5.8933e+07   4.4728e+07    5.121e+07     1.0000
   0.99   1.550     239.000    74.177   1.8372e+08    9.369e+07   1.0373e+08     2.0257

ROI flat
   0.00  36.000     108.306     2.911        97755        36425        35134     0.0185
   0.50   4.926     105.333    17.271   2.8484e+06   1.9654e+06   1.8986e+06     1.0000
   0.90   2.193     104.500    25.764   1.1474e+07   7.6446e+06   7.8528e+06     4.1361
```

`sigpow` **rises monotonically as the gate narrows, all the way to the boundary.** There is
no interior optimum, so **it cannot be used to choose a gate at all** — it will always name
the narrowest. At gate 0.99 the merge has `n_eff = 1.55`: it is, to within a frame and a
half, **the per-pixel selector that this entire project exists to argue against.** A team
tuning `strehl` by `sigpow` would tune it into the thing `strehl` says is wrong.

Two things make this decisive rather than merely awkward:

**(a) The rise happens on the flat ROI too — 4.14x, on a patch with no detail to deliver.**
There is no resolution there to recover. What rises is common structure manufactured by
selection: both halves see the same scene, so both preferentially accept frames near the same
focus position, and the same residual defocus mottle is amplified in both. **That is PM_M
(§3.1) occurring naturally, unplanted, on real data** — destroyed averaging plus amplified
common structure, scored as delivered signal. PR5's adversary is not a contrived plant; it is
a description of what a narrowing gate actually does.

**(b) The monotonicity is carried entirely by the un-normalised factor** (PR13):

```
  ROI detail
   gate     n_eff    FRC(f_sig)    P_ring/P(0.5)   sigpow/sig(0.5)
    0.50    5.549      0.8690           1.0000          1.0000
    0.90    2.098      0.5640           2.9017          1.8835
    0.99    1.550      0.5646           3.1174          2.0257
```

FRC **falls** 0.869 -> 0.565 while `P_ring` rises 3.12x. **The two factors of the product
disagree in sign, and `P_ring` wins.** The whole reason `sigpow` was constructed — that
multiplying by `P_ring` lets the product escape fact 617's blindness — is also the reason it
inherits `P_ring`'s two vices: quadratic gain sensitivity (§3.5) and indifference to whether
power at `f_sig` is signal or amplified common pattern (§3.1). The escape from 617 was
purchased, not free, and M46 does not price it.

---

## 4. True, but not claimed by M46

1. **`oracle_mtf` is equally blind to a contrast-restoring low-pass.** PR6 found
   `d_sigpow = +0.00005` at sb = 0.05 px, S = 0.095 — but the ground-truth oracle reads
   `+0.00003`. **This is a limit on single-frequency amplitude probes in general, not a
   defect specific to `sigpow`**, and it means M46's §6.4 "post-filter completeness" claim
   would not be rescued by adding ground truth. Any merge free to rescale its own output at
   the probe frequency is invisible to any single-frequency statistic.
2. **The dark-frame `rho` route cross-validates M50/fact 565 at 3.6%** across two decoders and
   two estimators, on a plane construction M50 never used. That is a free out-of-sample
   confirmation of a *different* fact, obtained while refuting fact 610.
3. **`C` being noise-invariant is a genuinely useful result on its own** (§2.2) and survives
   everything in §3. The failure is entirely in the premise that the compared merges deliver
   the same latent — which is a statement about *nonlinear merges*, not about `C`.
4. **The plant's blind spots are enumerable in advance**, and all three follow from the same
   root: the plant draws both half-images from one latent with identically-distributed noise.
   That makes D2's asymmetry exactly 1, D3's latent drift exactly 0, and §3.5's gain ratio
   exactly 1. Three of this report's findings are invisible in the plant for one reason.

## 5. Rule 34 audit of M46's plants — as asked

The constants shared between M46's plants and the statistic under test are:
`sigma = sig_d/sqrt(n_eff)` (drawn noise), `rho` and `sig_d` (planted FPN via `make_fpn`),
`n_eff`, `F_SIG` and the ring binning, and `det` (the latent).

- **`rho`/`n_eff`: the classic rule-34 disease, confirmed present in b4** — `rho` is planted
  from the same number the check predicts from, so the check is scale-invariant in `rho`
  itself (§3.3, PR3). This is exactly the failure mode the brief describes.
- **`sigma`: not diseased.** PR4 shows the statistic is *not* invariant to amplitude
  (exponent 2), so a wrong `sigma` would show up. It is safe here, but for the opposite of
  the usual reason, and that non-invariance is itself defect §3.5.
- **`det`: diseased in a new way not covered by rule 34's wording.** The plant shares one
  latent between both arms and between baseline and treatment. It is therefore invariant to
  *latent drift* — which is the largest real effect (§3.4, D3, +812%). Rule 34 is about a
  shared *constant*; this is a shared *object*. **Proposed discipline below.**

---

## 6. Proposed facts

Numbers are placeholders; the orchestrator assigns SYNTHESIS numbers.

- **P1 (MEASURED).** Directly measured per-pixel dark FPN on the green-quad plane at ISO 500,
  from 242 dark frames at `D:\macro-dark-frames`, is **0.2888 DN** (0.08341 DN²) by
  cross-half covariance; 0.2869 DN bias-corrected. This agrees with fact 565's 0.3943 DN per
  raw pixel, divided by sqrt(2) for the quad plane, to 3.6%. Answers question 142.
- **P2 (MEASURED).** `rho = 0.3094` requires sigma_FPN = 4.390 DN at the flat ROI. The
  sensor delivers 0.2888 DN — a **231x shortfall in variance**. Fact 610's `rho` is a valid
  common-mode fraction but **is not fixed-pattern noise**; closing the gap needs a 4.1% PRNU
  term (ARGUED implausible; question 111 remains open).
- **P3 (MEASURED).** Dark FPN ring cross-spectrum at ISO 500 is flat to ~20% (0.0989 DN² at
  `f_sig`, 0.0788 DN² at 0.45 cyc/px): **FPN is white, as fact 612 says.** But the common
  power between two real half-stack merges runs 44x–221 959x above it and falls steeply with
  frequency, so **FRC censoring on real data is scene and aliased content, not FPN.**
- **P4 (MEASURED).** Fact 610's out-of-sample confirmation tracks its closed form to within
  4% for every planted `rho` from 0.02 to 3.0. **It has no power to reject any `rho`** and is
  the algebraic inverse of the equation `rho` was solved from (rule 21).
- **P5 (MEASURED).** `sigpow` is homogeneous of degree exactly 2 in photometric gain
  (`d log sigpow / d log g = 2.000000`, FRC spread 1.4e-8). A 0.4% gain on one arm drops
  M46's separation from 0.937 to 0.493. Real merge-parameter changes shift median level by up
  to 11.7%.
- **P6 (MEASURED).** `sigpow` is **non-monotone in true MTF**. Against a merge that destroys
  resolution and adds a fixed structure common to both halves, at `hp_sd` matched to four
  figures, `sigpow/baseline` = 0.950, 0.887, **1.173, 2.030** for blur = 0.25, 0.5, 1.0,
  2.0 px, while true MTF at `f_sig` = 0.911, 0.687, 0.223, **0.007**. No threshold makes it
  safe. Violates rule 18.
- **P7 (MEASURED).** On real disjoint half-stack merges with no plant, at exactly k = sqrt(2)
  of real noise reduction, **S(sigpow) = 0.523 (detail) and 0.464 (flat)**, not 0.937/0.917,
  and `d_smooth` is negative — `sigpow` **rises** under pure noise removal. Fact 619 refuted
  outside its plant.
- **P8 (MEASURED).** `sigpow_ring = C * sqrt(P_a/P_b)`, so it equals `C` only when the two
  half-merges have equal ring power and **it is not symmetric under swapping the two inputs**.
  Measured `sqrt(P_a/P_b)` = 0.865 / 0.839 on real merges, exactly 1 in M46's plant.
- **P9 (MEASURED).** `b3_separation.py` evaluates FRC by interpolation at `f = 0.2762` and
  ring power at the ring centred `0.27734`. Worth a factor 2.1 on the real flat ROI.
- **P10 (MEASURED).** The per-ring common power `C` is noise-invariant as an estimator (adding
  15.6/37.1 DN of independent noise moves it 4.7%/6.6% while FRC collapses 0.849 -> 0.490),
  **but it still rises +27%/+812% along a real frame-count ladder**, because a nonlinear merge
  of one subset delivers a different latent than a merge of another. A plain-mean placebo
  accounts for +16%/+132% of it (focus sampling); `arm_A` adds the rest (selection
  instability). Fact 620's premise is false for nonlinear merges.
- **P11 (MEASURED).** Scored by `sigpow`, the merge gate has **no interior optimum on real
  data**: `sigpow` rises monotonically as the gate narrows (0.018 -> 1.00 -> 2.03 on detail,
  0.019 -> 1.00 -> 3.96 on flat, gate 0 -> 0.5 -> 0.99), naming `n_eff = 1.55` — near-pure
  per-pixel selection — as the most detailed configuration. **The metric built to score
  strehl's estimator-vs-selector thesis selects the selector.**
- **P12 (MEASURED).** That monotonicity is carried entirely by `P_ring` (x3.12 detail, x4.58
  flat) while `FRC` moves the opposite way (0.869 -> 0.565). The two factors disagree in sign.
- **P13 (MEASURED).** On the flat ROI, which contains no detail, narrowing the gate raises
  `C` 3.9x and `sigpow` 4.1x. Selection manufactures common structure between disjoint halves,
  and `sigpow` credits it as delivered signal.
- **P14 (MEASURED).** Fact 617 survives: FRC reads `d = +0.0001` against a linear post-filter
  and `+0.00005` against a contrast-restoring low-pass. **A ground-truth oracle at a single
  frequency is equally blind** (`+0.00003`), so §6.4's completeness gap is a property of
  single-frequency amplitude probes, not of correlation metrics specifically.
- **P15 (MEASURED).** M46's matched-cost design is fair: S(sigpow) = 0.942 -> 0.917 across
  k = 1.05..8.0. Fact 614's asymmetry is **not** manufacturing the separation. Scope note:
  matched blur saturates at 0.07 px, so M46's separation is measured entirely at blurs below
  a tenth of a pixel — inside the regime where P6's sign inversion has not yet set in.

## 7. Proposed disciplines

- **A plant that shares one latent object between both arms is invariant to latent drift, and
  latent drift is what nonlinear merges actually do.** Rule 34 covers a shared *constant*;
  extend it to a shared *object*. State explicitly, for every plant, which objects — not just
  which constants — the treatment and control share.
- **A statistic proposed to score a merge must be swept over a real merge parameter before it
  is believed.** A statistic with no interior optimum over the parameter it is meant to tune
  is not a criterion, whatever its separation score on a plant.
- **Report a metric's homogeneity degree in amplitude alongside its separation score.** Any
  metric that is not degree 0 requires a stated photometric tolerance; if that tolerance is
  tighter than the level drift between the configurations being compared, the metric cannot
  compare them.
- **Rule 18 requires monotonicity, not just a direction.** A metric whose sign inverts as the
  defect grows is more dangerous than one that is merely blind, because it reads best exactly
  where the output is worst.
- **Decompose a product metric and report both factors.** When factors disagree in sign, the
  product is reporting the un-normalised one and the normalisation is decorative.

## 8. Proposed questions

- What is this sensor's PRNU? Fact 610 needs 4.1% to be rescued; question 111 is unmeasured
  and the flats to measure it exist.
- Is there **any** statistic computable without ground truth that is monotone in MTF and
  degree 0 in amplitude? PR6 shows the ground-truth oracle fails the first at a single
  frequency, so the answer may require a spectral *shape* comparison rather than a
  single-frequency probe.
- What *does* set the gate, if not `sigpow`? P11 leaves the shipped gate = 0.5 without a
  measured justification.
- How much of a real half-stack merge's common power at `f_sig` is aliased content rather than
  resolved detail? P3 rules out FPN; the remainder is unattributed.

---

## 9. What would be needed before `sigpow` could be trusted in shipped code

1. **Fix D1** — evaluate both factors on the same ring.
2. **Fix D2** — measure `C` directly as `Re<A conj(B)>/M` rather than as a product, restoring
   symmetry under input swap.
3. **Normalise photometry** to better than 0.1% between compared configurations, and state
   that tolerance in the code. Real configuration changes are 100x outside it (P5).
4. **State and demonstrate a failure direction** (rule 18). P6 says there currently isn't one:
   the response is U-shaped, so this may require abandoning the single-frequency form.
5. **Validate against a latent-varying plant** — a nonlinear merge whose delivered scene
   depends on which frames it receives. Every plant in `m46lib` holds the latent fixed, and
   that is where the real 10x effect lives (P10).
6. **Do not use it to select merge parameters** until P11 is resolved; it currently has no
   interior optimum and prefers the selector limit.

Until at least 1, 2, 3 and 5 are done, no number produced by `sigpow` should be folded as
evidence about resolution. **The corpus still has no instrument able to score its central
claim** — M46's central negative finding stands, but its positive one does not.

---

## Appendix — evidence

| Script | Output | Attacks |
|---|---|---|
| `experiments/M55-sigpow-attack/src/e1_dark_rho.py` | `out/e1_dark_rho.log/.json` | PR1, PR2 |
| `src/e2_real_halfstacks.py` | `out/e2_real.log/.json` | PR8, PR2 |
| `src/e3_decompose.py` | `out/e3_decompose.log/.json` | PR9 (D1, D2) |
| `src/e4_placebo.py` | `out/e4_placebo.log/.json` | PR9 (D3), M3 control |
| `src/e5_adversaries.py` | `out/e5_adversaries.log/.json` | ARM 0, PR3–PR7 |
| `src/e6_gate_and_grade.py` | `out/e6_gate.log/.json` | PR10, PR11 |
| `src/e7_gain_and_frc.py` | `out/e7_gain.log/.json` | PR12, PR13 |

Every number quoted above appears verbatim in those logs. `.npz` intermediates are gitignored
but present on disk. No file under `crates/`, `experiments/m46-detail-metric/` or
`experiments/m41-r3-kill/` was modified; `arm_A_gated` in `e6` is a documented copy whose
equality with `m41lib.arm_A` at gate 0.5 is asserted at runtime.
