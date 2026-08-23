# M55 — Adversarial verification of M46's `sigpow` detail metric

**Verdict: the canonical re-derivation (Appendix A, `a632e46`) genuinely fixes the two defects it names — I found both independently before it reached me, and one of them is 13x larger than it reports — but it fixes nothing that matters, because `sigpow` remains non-monotone in true resolution (reading 344x past the spec's own decision threshold in the "delivered MORE signal" direction at true MTF 0.007), remains quadratic in photometric gain at 78x the tolerance real merges need, still scores 0.037–0.739 rather than 0.936–0.995 on real data across three stacks, and — the finding that subsumes the rest — the separation score `S` itself is not a stable statistic: on the author's own plant with the same seeds and the same blur it ranges 0.770 to 0.980 purely with the number of Monte-Carlo repetitions, because its denominator is a residual consistent with zero. Fact 619's numbers and Appendix A's 0.995 are the same measurement plus noise, and the improvement between them is not resolvable.**

Milestone M55. Read-only with respect to `crates/`, `experiments/m46-detail-metric/` and
`experiments/m41-r3-kill/` — verified by `git status` at commit time. All new work is under
`experiments/M55-sigpow-attack/`.

**Two definitions are under test.** Part I attacks `sigpow = FRC(f)*P_ring(f)` as folded into
SYNTHESIS facts 607–626. Part II attacks the canonical `Re(sum A conj B)/count` of Appendix A,
which is what would ship. Part I is not superseded: fact 619 is in the corpus with the old
numbers, and whether those numbers were sound *as measured* is a fact about how this metric
was validated.

---

## 0. On the brief

Both briefs were checked for a smuggled expected sign (discipline 305). **Both are clean.**
The amendment is scrupulous — it states the two defects and the claimed identity without
saying whether the author thinks the change helped, and explicitly withholds the direction of
the new numbers. The one place a direction could have leaked is "the re-derivation collapses
to something simpler", which reads as approving; but "simpler" is a structural description,
not a claim about the separation score, and the amendment does not say which way `S` moved.

---

## 1. Pre-registration

Twenty-four predictions, each with a success criterion **and an explicit falsifier of my own
objection**, registered before the deciding run. PR1–PR9 and PR14–PR24 in the session store;
PR10–PR13 in script docstrings committed with their output.

**Three of the twenty-four refuted my own stated objection** (PR7, PR11, PR21). Those are
flagged in place.

---

# PART I — the original definition, `FRC(f) * P_ring(f)`

## 2. What survives

### 2.1 Fact 617 is correct, for the reason M46 gave — MEASURED
Against a linear post-filter `frc2_at_fsig` reads `d = +0.0001`; against a contrast-restoring
low-pass, `+0.00005`. The ratio `C/(C+U)` cannot move under a common `|H|^2`.

### 2.2 `C` is noise-invariant *as an estimator* — MEASURED, a control M46 did not run
```
  1/2 pair            C  3.9166e+07  P_a  5.6756e+07  FRC  0.8487
  1/2 + noise (x4)    C  3.7308e+07  P_a  6.5875e+07  FRC  0.4900
  C moved by  -4.743%  (M3 is live if |.| > 10%)
```
FRC collapsed 0.849 -> 0.490 and `C` moved 4.7% (6.6% on flat). **M46's 6.5 algebra is
right.** What fails is the premise that the compared merges deliver the *same latent* (3.4).

### 2.3 The matched-cost design is fair — MY OBJECTION REFUTED (PR7)
`S(sigpow)` = 0.942 -> 0.917 across `k` = 1.05…8.0. Fact 614's asymmetry is **not** the
mechanism. Scope note: matched `sb` saturates at 0.07 px, so M46's separation lives entirely
in blurs below a tenth of a pixel — which matters for 3.1.

### 2.4 FPN is approximately white — MEASURED on 242 dark frames
Dark cross-half FPN ring spectrum at ISO 500: **0.0989 DN^2 at `f_sig`, 0.0788 DN^2 at 0.45**.
Flat to ~20%. Fact 612's whiteness sub-claim survives; its amplitude does not.

### 2.5 M46's plant reproduces exactly from an independent implementation
`e5` ARM 0, written from the paper: matched `sb = 0.04999` vs b3's 0.04999, `S = 0.937` vs
0.937, `hp_sd` 0.501, `ringpow` 0.587, `mean_grad` 0.233. **Nothing here is an arithmetic
dispute.**

## 3. What does not survive

### 3.1 Non-monotone in true resolution, and fooled upward — PR5/PR10 — MEASURED
Adversary **PM_M**: destroy resolution, add a fixed texture *common to both half-merges*,
solve the amplitude so `hp_sd` returns to baseline. Not exotic — **any merge with a component
shared between the halves does it**: a shared guide frame, flat-field, sharpening kernel,
learned prior, or plain FPN, which is M46's own fact 612 treated only as a nuisance.
```
    sb    fake amp   hp_sd     oracle_mtf   sigpow/base  c_direct/base
   0.25     12.496   58.8009      0.9113        0.9503        0.9506
   0.50     23.174   58.7998      0.6870        0.8865        0.8872
   1.00     38.373   58.7982      0.2231        1.1730        1.1749
   2.00     51.865   58.7973      0.0068        2.0299        2.0331
```
Correct sign below ~0.7 px, **inverted above**. Reads 2.03x baseline where true MTF is 0.0068.
`c_direct` tracks to 0.2% — the concept is fooled, not the code.

### 3.2 `rho = 0.3094` is not *dark* fixed-pattern noise — PR1 — MEASURED, out of sample
Question 142, taken. 242 ARW, 11 ISOs, `D:\macro-dark-frames`:
```
       rho=0.3094 REQUIRES sigma_FPN =  4.390 DN (var   19.270 DN^2)
       measured dark FPN (quad plane, ISO 500) = 0.2888 DN (var  0.08341 DN^2)
       shortfall:    15.20x in sd,     231.0x in VARIANCE
       a multiplicative PRNU term would have to be  4.119% of signal to close it
```
Cross-checks M50/fact 565 by a different route: 0.3943 DN per raw pixel / sqrt(2) = 0.2788
against my 0.2888 — **3.6% across two decoders, two estimators, two milestones.** `rho` is a
valid common-mode fraction; the attribution to FPN is wrong. On the real flat ROI `C(f)` runs
221 959x the dark FPN level at f = 0.051 down to 44.9x at 0.488, falling steeply — a white FPN
component would read flat.

**Addendum, added after commit `c7ce4f0`: independently corroborated, and my heading was too
strong.** While I was working, **M48b** took the same route (`12fd078`, `d7eedfa`) with its own
code. Its DSNU at ISO 500 is **0.4029 DN per green plane**; averaging two independent green
photosites into my quad plane predicts `0.4029/sqrt(2) = 0.2849` against my measured
**0.2888** - **1.4%, two implementations, same frames**. It derives the PRNU needed to close
the gap as **4.36%**; I derived **4.119%**. It places the DSNU shortfall at **596x** in
variance at the frame-median signal and **64x** at a tenth of it; I measured **231x** at a
more conservative operating point. **Three numbers, two agents, no shared code.**

M48b also makes a scoping point that corrects **my heading**, and I record it against myself:
`rho_dark = D^2/(R^2+D^2)` and `rho_M46 = (D^2+(P*S)^2)/(g*S+R^2+D^2+(P*S)^2)` are different
quantities, and **PRNU is fixed-pattern too**. The defensible statement is therefore
*"`rho = 0.3094` is not **dark** fixed-pattern noise, and closing it requires a
signal-proportional term of ~4.1-4.4% that is 4-15x published CMOS PRNU"* - not the flat
"is not fixed-pattern noise" I titled 3.2 with. The measurement and the body text are
unchanged and unaffected; the title overstated them. **P2 is worded to the corrected scope.**

### 3.3 Fact 610's "0.4% confirmation" has no power — PR3 — MEASURED
Planted `rho` from 0.02 to 3.0, ratio measured/predicted 0.9658 … 0.9998. **Every value
passes.** It is the algebraic inverse of the equation `rho` was solved from (rule 21).

### 3.4 Fact 620 fails on real disjoint half-stacks — PR8 — MEASURED, no plant
```
ROI detail   sigpow_fsig 4.7737e+07  4.5132e+07  5.0111e+07 +0.0546 -0.0497   0.523
ROI flat     sigpow_fsig 1.7249e+06  1.1179e+06  2.4259e+06 +0.3519 -0.4064   0.464
```
Against 0.937/0.917. `d_smooth` **negative** — `sigpow` *rises* under pure noise removal.
Three separate defects:
- **D1 frequency mismatch** — FRC interpolated at 0.2762, power at the ring centred 0.27734.
  Factor **2.1** on the real flat ROI.
- **D2 asymmetry** — `sigpow_ring = C*sqrt(P_a/P_b)`; changes if you swap the inputs.
- **D3 the premise** — `C` is noise-invariant yet rises **+27%/+812%** along a real frame
  ladder, because a nonlinear merge of one subset delivers a different latent than another.
  A plain-mean placebo accounts for +16%/+132%; `arm_A` adds the rest.

**D1 and D2 are exactly the two defects Appendix A later self-reports.** I found them from
the frozen code, independently, before the amendment reached me. See 4.1 and 7.3.

### 3.5 Exactly quadratic in photometric gain — PR4/PR12
`d(log sigpow)/d(log g) = 2.000000`, FRC spread `1.363e-08`. A 0.4% gain on one arm drops
`S` from 0.937 to 0.493. Real merge changes shift median level by up to 11.7%.

### 3.6 M46's own proposed use names a selector as the winner — PR11 — MEASURED
M46 section 8 proposes `sigpow` to test "that gate width trades noise against resolution". Run
on the fact-620 configuration. **I pre-registered the opposite sign and the data refuted me.**
```
  gate   n_eff    level DN    hp_sd      sigpow/gate0.5      FRC
   0.00  36.000     273.090    12.390        0.0179         0.7271
   0.50   5.549     244.400    59.466        1.0000         0.8690
   0.99   1.550     239.000    74.177        2.0257         0.5646
```
Monotone to the boundary — **no interior optimum, so it cannot choose a gate at all.** At gate
0.99 the merge has `n_eff = 1.55`: the per-pixel selector this project exists to argue against.
It rises **4.14x on the flat ROI, which has no detail** — PM_M occurring naturally, unplanted.
And the monotonicity is carried entirely by `P_ring` (x3.12) while `FRC` *falls* 0.869 -> 0.565:
**the two factors disagree in sign and the un-normalised one wins.**

---

# PART II — the canonical definition, `Re(sum A conj B)/count`

`canon()` in `e8_canonical_plant.py` is my own implementation of A.1, written from the prose.
It imports neither `b3_separation` nor `b6_spec`. It reproduces the author's A.3.1 table to
six significant figures (6.1), so the two implementations agree.

## 4. What the re-derivation genuinely fixes — CONFIRMED, and one is understated

### 4.1 D1 and D2 are real and are fixed — MEASURED
Swap asymmetry, my code, every stack and ROI: **canonical `0.0000e+00` exactly**, in all six
cells. The old form: `9.4e-03` to `2.6e-01`. The fix is real and complete.

### 4.2 The author under-reports its own defect by 13x — MEASURED (PR22)
A.0.2 says swapping the halves moves the old value by `1.96e-02`. On **the author's own stated
configuration** — 112MSDCF frames 6..68, detail ROI, parity split:
```
     P_a 5.893981e+07   P_b 4.523841e+07   P_a/P_b 1.302871
     FRC(a,b) 0.86908375   FRC(b,a) 0.86908375  (symmetric)
     old(a,b) 5.122363e+07   old(b,a) 3.931597e+07
     relative to the mean: 2.6304e-01
     A.0.2 reports 1.96e-02.  canonical swap difference: 0.0000e+00
```
DERIVED and confirmed: `old(a,b)/old(b,a) = P_a/P_b` exactly, because FRC is swap-symmetric
(shown to 8 dp above). The asymmetry is **26%, not 2%**. **This strengthens A.0.2 — the fix
was more necessary than the author knew.**

### 4.3 The lambda^4 docstring error is real — PR21 — AUTHOR CORROBORATED
`b6_spec.py:129-130` says the value "scale[s] as the fourth power". Measured on my own code:
```
      lam    both inputs scaled     exponent      one input scaled   exponent
       3.0        9.000000000000    2.00000     3.000000000000    1.00000
      10.0      100.000000000000    2.00000    10.000000000000    1.00000
```
**Exponent 2, author corroborated.** *Unclaimed extra:* it is **exactly 1 when only one input
is scaled**, which the spec does not state and which matters, because two half-merges of a
real stack do differ in level (4.2 measures `P_a/P_b = 1.30`).

## 5. What the re-derivation does not fix

### 5.1 The identity is algebra, not a measurement — PR14 — MEASURED
A.0.3 verifies `FRC_i * P_i == Re(sum A conj B)/count` "to 1.4e-16". DERIVED: `FRC_i = num/den`
and `P_i = den/count`; the `den` cancels for **any** complex `A,B`. I tried to break it with
every convention the spec agonises over:
```
   case                        Re-form FRC*P vs canon   MAG-form FRC*P vs canon
   ordinary real, n=64              1.172e-16              2.000e+00   <-- MAG-form BREAKS
   ordinary real, n=64 +periodic Hann     0.000e+00        2.000e+00   <-- MAG-form BREAKS
   ordinary real, n=64 +ortho FFT     1.172e-16            2.000e+00   <-- MAG-form BREAKS
   ODD n=65                         0.000e+00              2.000e+00   <-- MAG-form BREAKS
   anti-correlated (neg)            0.000e+00              2.000e+00   <-- MAG-form BREAKS
   COMPLEX-valued input             0.000e+00              2.682e+00   <-- MAG-form BREAKS
```
**Nothing breaks it** — not odd `n`, not complex input, not the wrong window, not `norm=ortho`.
So the `1.4e-16` is a floating-point round-trip through a multiply and a divide. It has **no
power to detect an error in anything**. This is the same rule-21 shape as fact 610's "0.4%
confirmation" (3.3), recurring in the audit that was written to catch such things.

**And there IS an unstated condition, which the numerical check could never have found.** The
identity holds only for the **`Re`-form** of FRC. The other standard convention,
`|sum A conj B| / sqrt(.)`, **breaks it by a relative 2.000 wherever the cross-power is
negative** — which is reachable, is what golden vector **G3 exists to test**, and which A.2.3
explicitly warns implementers about (*"an implementation that takes `abs()` somewhere passes
G2 and fails G3"*). A.0.3 should state: *this derivation assumes the `Re` numerator; with a
magnitude numerator the two factors do not multiply to the canonical value.*

Also unstated: the identity requires `den > 0`, and the frozen `m41lib.frc` clamps
`den = max(den, 1e-30)`, so in the `ZeroPower` regime the two forms diverge by construction.

### 5.2 The rule-18 inversion survives untouched — PR16 — MEASURED
```
      sb    fake amp   hp_sd    true MTF    d(canon)     d(old)    A.4.2 says
     0.25     12.496   58.8009    0.9113    +0.04940   +0.04969    lost signal
     0.50     23.174   58.7998    0.6870    +0.11284   +0.11354    lost signal
     1.00     38.373   58.7982    0.2231    -0.17487   -0.17302    MORE signal
     2.00     51.865   58.7973    0.0068    -1.03306   -1.02991    MORE signal
```
**`d_canon` tracks `d_old` to under 1% at every width.** The inversion is entirely orthogonal
to both convention fixes. At true MTF `0.0068` the canonical form reports `d = -1.033`, which
against A.4.2's own `+-0.003` decision threshold is **344x past it, in the "delivered MORE
signal" direction.** A.4.2's practical reading — *"`d < -0.003`: the test merge delivered more
signal"* — would be fired, at maximum confidence, by a merge that destroyed essentially all
real detail. **Rule 18 is still violated, and now it is violated by a document that states a
decision rule.**

### 5.3 A.4.2's thresholds collide with the degree-2 gain sensitivity — PR20 — MEASURED
```
      eps      d(measured)   saturates which A.4.2 threshold
    0.00025     -0.000500   exceeds the 0.0005 no-claim floor
    0.00150     -0.003002   exceeds the +-0.003 DECISION threshold
    0.11700     -0.247689   exceeds the +-0.003 DECISION threshold
```
DERIVED `d = 1-(1+eps)^2 ~ -2eps`, confirmed to 4 dp. **A 0.15% photometric difference
saturates the decision threshold; 0.025% saturates the no-claim floor.** PR11 measured real
merge-gate configurations differing in median level by up to **11.7%**, giving `d = -0.2477` —
**83x the decision threshold, in the "more signal" direction, from brightness alone.** A.4.1
says to compare only "the same frames", which is satisfied; the level difference comes from the
merge itself, so the contract does not protect against this. **A.4.2's thresholds are unusable
without a photometric normalisation the spec does not specify.**

### 5.4 On real data the canonical form is not better — PR17 — MEASURED, three stacks
Canonical `sigpow`, `k = sqrt(2)` of **real photons**, blur matched on `hp_sd`, no plant:

| stack | ROI | matched `sb` | `d_blur` | `d_smooth` | **S(canonical)** |
|---|---|---|---|---|---|
| 112MSDCF *(author's)* | detail | 0.20411 | +0.11868 | +0.20381 | **0.368** |
| 112MSDCF | flat | 0.41871 | +0.41233 | +0.23674 | **0.635** |
| 113MSDCF *(new)* | centre | 0.17637 | +0.08996 | **-0.15592** | **0.366** |
| 113MSDCF | flat | 0.31245 | +0.25478 | **-6.60469** | **0.037** |
| foam *(new)* | centre | 0.70485 | +0.77804 | +0.27471 | **0.739** |
| foam | flat | 1.00254 | +0.95226 | +0.78099 | **0.549** |

Against Appendix A's **0.995 / 0.936**. **None reaches 0.90; four of six are below 0.5.** On
112MSDCF detail the canonical form is *worse* than the old one on real data (old 0.523 ->
canonical 0.368). ROIs were fixed in advance by PR24 and none was selected on its result.

### 5.5 THE STRUCTURAL RESULT — the separation contrast is not realisable on real data
This is the finding that subsumes 5.4, and it comes out of the author's **own** A.3.1.

On the plant, the `k = sqrt(2)` "smoothing" arm adds less synthetic noise to a **fixed latent**.
On real data you cannot halve the noise without taking more frames, and taking more frames
**changes the depth sampling of the half-stacks**. Appendix A has now measured what depth
sampling is worth. Putting its numbers on one scale, all as `|d|`, canonical form, author's
own stack and ROI:
```
     halving noise variance (k=sqrt2), on the PLANT         0.00021
     a 0.05 px optical blur, on the PLANT                   0.00719
     a 0.15 % photometric gain                              0.00300
     block-4 instead of parity split                        0.35870
     contiguous instead of parity split                     0.99530
     PM_M: destroy detail to MTF 0.007 + common structure    1.03306
```
**Split choice has 50x the leverage of the blur signal the metric exists to detect, and 1751x
the leverage of the noise term it is supposed to be blind to.** Any real-data version of the
separation experiment moves the split and therefore moves the nuisance parameter by orders of
magnitude more than either arm of the contrast. **Fact 619 is therefore testable only on a
plant, and the plant is structurally incapable of expressing latent drift (rule 13).** That is
not a defect in the measurement; it is a limit on what can be measured this way at all.

### 5.6 The separation score `S` is not a stable statistic — PR23 — MEASURED
`S = |d_blur|/(|d_blur|+|d_smooth|)`. My PR15 read `S(canon) = 0.976`; the author reads 0.995.
The entire gap is `d_smooth`: mine `+0.00018`, the author's `+0.00004`. So I tested whether
`d_smooth` is a measurement at all. **Same plant, same seeds, same blur held fixed at
sb = 0.04959; only the number of Monte-Carlo repetitions varies:**
```
     REPS    d_blur      d_smooth    se(d_smooth)   d_smooth/se    S(canon)
        1   +0.00717    +0.00215           nan           nan       0.770
        2   +0.00718    +0.00128       0.00087          1.47       0.849
        4   +0.00719    +0.00080       0.00057          1.39       0.900
        8   +0.00719    +0.00018       0.00054          0.34       0.976
       16   +0.00719    +0.00015       0.00041          0.36       0.980
       32   +0.00719    +0.00048       0.00029          1.66       0.937
       64   +0.00719    +0.00021       0.00020          1.01       0.972
```
`d_blur` is rock solid at `+0.00719`. **`d_smooth` is between 0.34 and 1.66 standard errors
from zero at every repetition count — consistent with zero throughout.** And so
**`S` ranges 0.770 to 0.980 with nothing changed but `REPS`.**

Consequences, and they are large:

1. **`S` is a ratio whose denominator is a noise residual.** As `d_smooth -> 0`, `S -> 1`. Its
   value reports how the noise landed, not how well the metric separates.
2. **0.937 (fact 619) and 0.995 (A.0.4) are the same measurement.** Both lie inside the spread
   I measure for a *single* form. **A.0.4's "the clean form is strictly better" is not
   resolvable** — the claimed improvement is smaller than the statistic's own dispersion.
   The direction is corroborated (`S(canon) 0.976 > S(old) 0.936` in my harness at REPS = 8),
   but the magnitude is not measurable.
3. **Every separation number in this corpus quoted to three figures is over-precise** —
   0.937, 0.917, 0.990, 0.931, 0.973, 0.995, 0.994, 0.936, 0.982, and my own 0.523 and 0.464.
   Mine are not exempt; the real-data ones in 5.4 have large `d_smooth` and are more stable,
   but the plant-based ones are not.

**This is the deepest problem with how `sigpow` was validated, and it applies equally to both
definitions.** The right statistic to report is `d_blur` with a confidence interval, not `S`.

---
## 6. The split contract — A.3

### 6.1 The headline replicates — PR18 — MEASURED, three stacks, six ROIs
`contiguous / parity`: **0.0047, 0.0292, -0.0347, 0.0466, 0.0058, 0.0362** — all six below my
pre-registered 0.10 line. **A.3.1's central claim is a property, not an artefact of one
stack.** And my independent implementation reproduces the author's table to six significant
figures (parity FRC `+0.866128` vs `+0.866129`; sigpow `4.47240e+07` vs `4.47240e+07`;
contiguous 0.0047; block-2 1.0151; block-4 0.6413).

### 6.2 The gradient does NOT replicate — PR18 — MEASURED
A.3.2 derives engineering guidance from the gradient: *"Block-of-2 is fine (1.0151), block-of-4
already loses 36%, random loses 14%."* On stacks the author did not use:

| split | 112 detail | 112 flat | 113 centre | 113 flat | foam centre | foam flat |
|---|---|---|---|---|---|---|
| parity | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| contiguous | 0.0047 | 0.0292 | -0.0347 | 0.0466 | 0.0058 | 0.0362 |
| block-2 | **1.0151** | 0.7140 | 0.9840 | 0.7849 | **0.5172** | **-0.3077** |
| block-4 | 0.6413 | **-0.0509** | 0.3372 | **-0.1525** | 0.2989 | 0.8381 |
| block-8 | 0.2424 | -0.0013 | 0.2207 | -0.0241 | 0.0121 | 0.4069 |
| random | 0.7620 | **-0.2096** | 0.7403 | **1.0202** | 0.8166 | 0.0097 |

**"Block-of-2 is fine" is a one-stack, one-ROI result**: it is 1.0151 where it was measured
and 0.5172 on foam's centre and -0.3077 on foam's flat. **"Random loses 14%"** ranges from
0.0097 to 1.0202 — random *beats* parity on 113's flat ROI. On foam's flat ROI block-4 (0.8381)
beats block-2 (-0.3077), inverting the author's ordering entirely. **The monotone-in-run-length
story is not general; only the parity-vs-contiguous endpoint is.**

### 6.3 The depth mechanism is confirmed where it was derived, and refuted elsewhere — PR19
The discriminator the author did not run: narrow the stack to the `K` frames around best focus
and re-run parity vs contiguous. If depth coverage is the mechanism, the contiguous penalty
must shrink as `K` shrinks.
```
   112MSDCF detail   K=8 0.7325   K=16 0.5917   K=32 0.5801   K=62 0.0047
   113MSDCF centre   K=8 0.4451   K=16 0.3312   K=32 0.2305   K=63 -0.0347
   foam     centre   K=8 0.0979   K=16 0.0901   K=32 0.0934   K=62 0.0058
   112MSDCF flat     K=8 -0.1972  K=16 -0.2251  K=32 -0.2496  K=62 0.0292
   113MSDCF flat     K=8 0.3502   K=16 0.3528   K=32 0.3568   K=63 0.0466
   foam     flat     K=8 -0.2652  K=16 -0.4341  K=32 -0.5530  K=62 0.0362
```
**On detail/centre ROIs the mechanism is confirmed** — 112's contiguous penalty recovers from
0.0047 to 0.7325 as the depth window narrows, exactly as A.3.1's DERIVED explanation requires.
**On flat ROIs it is refuted**: 113's flat is `K`-independent (0.3502 / 0.3528 / 0.3568 — flat
to 2%), and 112's and foam's go *more* negative as the window narrows. So depth coverage is the
mechanism on the ROI it was derived on, and something else operates elsewhere.

**Unclaimed, and it bounds the mechanism:** even at `K = 8` — four adjacent frames per half —
contiguous never recovers past **0.73**, and on foam only to 0.098.

### 6.4 `sigpow` goes negative on real data, and the spec does not handle it — MEASURED
**7 of the 36 real split x ROI cells above are negative.** `sigpow` is a signed cross-power
(A.2.3 says so, and G3 exists to pin it), but:
- **A.4.1's `d = (sigpow_ref - sigpow_test)/abs(sigpow_ref)`** is not analysed for a negative
  reference, and A.4.2's "positive `d` means the test merge lost signal" reading silently
  inverts when `sigpow_ref < 0`.
- **On `foam`'s flat ROI the sanctioned parity split gives FRC = +0.0719** — below A.4.3's own
  ~0.3 validity floor. The diagnostic correctly fires, which is to A.4.3's credit, but it fires
  on the *recommended* configuration of a perfectly ordinary stack, and the spec offers no
  fallback beyond "a diagnostic, not a hard reject".

### 6.5 What the split contract actually is
**ARGUED from 5.5 and 6.1–6.3.** A.3 is presented as an implementation constraint. It is
better read as a **measurement of the metric's dominant nuisance parameter**: the split
controls how much latent the two halves share, and `sigpow` measures shared latent. The
contract is right, and it should ship — but the reason to write it down is not tidiness, it is
that a mis-specified split produces a reading **50x larger than the largest real effect the
metric is meant to detect**, silently, with `Status = Ok`.

## 7. True, but not claimed

1. **`oracle_mtf` is equally blind to a contrast-restoring low-pass** (`+0.00003` vs `sigpow`'s
   `+0.00005`). The 6.4 completeness gap would **not** be closed by adding ground truth. It is
   a limit on single-frequency amplitude probes generally.
2. **The dark-frame route cross-validates fact 565 to 3.6%** across two decoders and two
   estimators — a free out-of-sample confirmation of a *different* fact, obtained while
   refuting fact 610.
3. **D1 and D2 were independently discoverable from the frozen code.** I derived both in `e3`
   before the amendment reached me. Two independent readers found the same two defects, which
   is evidence the code was legible enough to audit and that the corpus's convention-mismatch
   failure mode is systematic rather than incidental.
4. **The plant's blind spots are enumerable in advance and share one root**: it draws both
   half-images from one latent with identically-distributed noise. That makes D2's asymmetry
   exactly 1, D3's latent drift exactly 0, the 3.5 gain ratio exactly 1, and 5.5's split
   nuisance exactly absent. **Four findings, one cause.**

## 8. Rule 34 audit of the plants

Constants shared between plant and statistic: `sigma`, `rho`, `sig_d`, `n_eff`, `F_SIG`, the
ring binning, and `det`.
- **`rho`/`n_eff`: classic rule-34 disease, confirmed in b4** (3.3).
- **`sigma`: not diseased** — the statistic is *not* amplitude-invariant (exponent 2), so a
  wrong `sigma` would show. Safe for the opposite of the usual reason, and that
  non-invariance is itself defect 5.3.
- **`det`: diseased in a way rule 34's wording does not cover.** The plant shares one latent
  *object* between both arms and between baseline and treatment, making it invariant to latent
  drift — the largest real effect. **Rule 34 is about a shared constant; this is a shared
  object.**
- **New, from A.0.3: the identity check is diseased in the b4 shape.** It verifies an algebraic
  cancellation numerically and reports the round-off as a confirmation.

---
## 9. Proposed facts

Numbers are placeholders. **P1–P15 attack the original definition; P16–P29 the canonical one.**

- **P1 (MEASURED).** Directly measured per-pixel dark FPN on the green-quad plane at ISO 500,
  from 242 dark frames, is **0.2888 DN** (0.08341 DN^2); 0.2869 bias-corrected. Agrees with
  fact 565 / sqrt(2) to 3.6%. Answers question 142.
- **P2 (MEASURED).** `rho = 0.3094` requires 4.390 DN; the sensor delivers 0.2888 DN — a
  **231x shortfall in variance**. Fact 610's `rho` is a valid common-mode fraction but is
  **not *dark* FPN (DSNU)**; closing it needs a signal-proportional term of ~4.1% (M48b,
  independently and concurrently, 4.36%), which is 4-15x published CMOS PRNU (ARGUED
  implausible; question 111 open). **Corroborated out of sample by M48b's independent
  measurement**: its DSNU 0.4029 DN/plane vs my 0.2888 DN/quad agree to **1.4%** after the
  sqrt(2) quad average. PRNU is itself fixed-pattern, so the claim is scoped to darks.
- **P3 (MEASURED).** Dark FPN ring spectrum is flat to ~20% — **FPN is white, as fact 612
  says** — but real half-merge common power runs 44x–221 959x above it and falls steeply with
  frequency, so FRC censoring on real data is scene and aliased content, not FPN.
- **P4 (MEASURED).** Fact 610's out-of-sample confirmation tracks its closed form to within 4%
  for every planted `rho` from 0.02 to 3.0: **no power to reject any `rho`** (rule 21).
- **P5 (MEASURED).** Both definitions are homogeneous of degree exactly **2** in photometric
  gain (`d log/d log g = 2.000000`, FRC spread 1.4e-8), and of degree exactly **1** when only
  one half-merge is scaled — the latter unstated in Appendix A.
- **P6 (MEASURED).** `sigpow` is **non-monotone in true MTF**, in **both** definitions.
  `sigpow/baseline` = 0.950, 0.887, **1.173, 2.030** at blur 0.25/0.5/1.0/2.0 px with `hp_sd`
  matched to four figures, while true MTF = 0.911, 0.687, 0.223, **0.007**.
- **P7 (MEASURED).** On real disjoint half-stack merges at `k = sqrt(2)` of real noise
  reduction, the **original** form scores S = 0.523 (detail) / 0.464 (flat), `d_smooth` negative.
- **P8 (MEASURED).** `sigpow_ring = C*sqrt(P_a/P_b)` — not symmetric under input swap.
- **P9 (MEASURED).** `b3_separation.py` evaluates FRC by interpolation at 0.2762 and power at
  the ring centred 0.27734. Worth a factor 2.1 on the real flat ROI.
- **P10 (MEASURED).** `C` is noise-invariant as an estimator (-4.7%/-6.6% when independent
  noise is added back while FRC collapses 0.849 -> 0.490) **but still rises +27%/+812% along a
  real frame ladder**, because a nonlinear merge of one subset delivers a different latent
  than another. A plain-mean placebo accounts for +16%/+132%.
- **P11 (MEASURED).** Scored by `sigpow`, the merge gate has **no interior optimum on real
  data**: monotone as the gate narrows (0.018 -> 1.00 -> 2.03 detail; 0.019 -> 1.00 -> 3.96
  flat), naming `n_eff = 1.55` — near-pure selection — as most detailed.
- **P12 (MEASURED).** That monotonicity is carried entirely by `P_ring` (x3.12) while `FRC`
  moves the opposite way (0.869 -> 0.565).
- **P13 (MEASURED).** On the flat ROI, narrowing the gate raises `C` 3.9x and `sigpow` 4.1x.
  Selection manufactures common structure between disjoint halves.
- **P14 (MEASURED).** Fact 617 survives: FRC reads `+0.0001` against a linear post-filter and
  `+0.00005` against a contrast-restoring low-pass. **A ground-truth oracle at a single
  frequency is equally blind** (`+0.00003`).
- **P15 (MEASURED).** The matched-cost design is fair: S = 0.942 -> 0.917 across k = 1.05…8.0.
  Fact 614's asymmetry is **not** manufacturing the separation.
- **P16 (DERIVED + MEASURED).** A.0.3's identity is the cancellation of a common factor and
  holds for **any** complex `A,B` with `den > 0` — confirmed exact (0.0 to 1.17e-16) under odd
  `n`, complex input, `norm=ortho`, and the periodic window. **The 1.4e-16 verification has no
  power to detect any error.** *Unstated condition:* it requires the **`Re`-form** of FRC; the
  magnitude form breaks it by relative **2.000** wherever cross-power is negative — the case
  golden vector G3 exists to test.
- **P17 (MEASURED).** **The separation score `S` is not a stable statistic.** With the same
  plant, same seeds and same blur, `S(canonical)` ranges **0.770 to 0.980** as `REPS` goes
  1 -> 64, because `d_smooth` is 0.34–1.66 standard errors from zero throughout while `d_blur`
  is fixed at +0.00719. **Fact 619's 0.937 and Appendix A's 0.995 are one measurement plus
  noise; the claimed improvement is not resolvable.** Every three-figure separation score in
  this corpus, mine included, is over-precise.
- **P18 (MEASURED).** The canonical form **does not fix the rule-18 inversion**: `d` = +0.0494,
  +0.1128, **-0.1749, -1.0331** at true MTF 0.911/0.687/0.223/0.0068, tracking the old form to
  under 1%. At MTF 0.0068 it is **344x past A.4.2's own +-0.003 decision threshold in the
  "delivered MORE signal" direction.**
- **P19 (MEASURED).** A.4.2's thresholds collide with P5: **eps = 0.15% photometric gain
  saturates the +-0.003 decision threshold**, eps = 0.025% saturates the 0.0005 floor, and the
  11.7% level difference measured between real merge configurations gives `d = -0.2477` — 83x
  the threshold, from brightness alone.
- **P20 (MEASURED).** A.3.1's headline **replicates**: `contiguous/parity` < 0.10 in 6 of 6
  cells across three stacks, and an independent implementation reproduces A.3.1's table to six
  significant figures.
- **P21 (MEASURED).** A.3.2's **gradient does not replicate**. Block-2 is 1.0151 where it was
  measured but 0.5172 (foam centre) and -0.3077 (foam flat); random ranges 0.0097 to 1.0202 and
  *beats* parity on one ROI. "Block-of-2 is fine" and "random loses 14%" are one-stack results.
- **P22 (MEASURED).** Canonical `sigpow` is **negative in 7 of 36 real split x ROI cells**.
  A.4.1's `d` and A.4.2's sign reading are undefined for a negative reference.
- **P23 (MEASURED).** A.3.1's depth-coverage mechanism is **confirmed on detail/centre ROIs**
  (contiguous penalty recovers 0.0047 -> 0.7325 as the depth window narrows) and **refuted on
  flat ROIs** (113 flat is `K`-independent at 0.350/0.353/0.357; 112 and foam go more negative).
- **P24 (MEASURED).** Even with 4 adjacent frames per half, contiguous never recovers past
  0.73 — depth coverage is most, not all, of the split effect.
- **P25 (MEASURED).** Real-data separation under the **new** contract and the **canonical**
  form: S = 0.368 / 0.635 (112MSDCF), 0.366 / 0.037 (113MSDCF), 0.739 / 0.549 (foam). **None
  reaches 0.90; four of six below 0.5.** On 112 detail the canonical form is *worse* on real
  data than the old one (0.523 -> 0.368).
- **P26 (DERIVED from the author's own measurements).** **The separation contrast is not
  realisable on real data.** Halving the noise requires more frames, which changes the split's
  depth sampling, and split choice has **50x** the leverage of the 0.05 px blur signal and
  **1751x** the leverage of the noise term. Fact 619 is testable only on a plant, and the
  plant cannot express latent drift.
- **P27 (MEASURED).** A.0.2 under-reports its own defect: the old form's swap asymmetry on the
  author's own configuration is **2.63e-01**, 13.4x the reported 1.96e-02, and is exactly
  `P_a/P_b = 1.302871`. The canonical form's swap difference is exactly **0.0** in all six
  cells. **The fix was more necessary than reported.**
- **P28 (MEASURED).** A.0.5 is right: `b6_spec.py:129-130` says "fourth power"; the measured
  exponent is exactly 2.00000 at lambda = 2, 3, 10.
- **P29 (MEASURED).** On `foam`'s flat ROI the **sanctioned parity split** yields
  FRC(`f_sig`) = +0.0719, below A.4.3's own ~0.3 validity floor. The diagnostic fires correctly
  on a recommended configuration of an ordinary stack; the spec provides no fallback.

## 10. Proposed disciplines

- **Do not report a ratio whose denominator is consistent with zero.** Report the numerator
  with an interval. `S = |d_blur|/(|d_blur|+|d_smooth|)` tends to 1 as the nuisance term tends
  to its noise floor, so it rewards a quieter experiment rather than a better metric. Before
  quoting any separation score, test its denominator against zero and sweep the repetition
  count.
- **A plant that shares one latent *object* between both arms is invariant to latent drift, and
  latent drift is what nonlinear merges do.** Rule 34 covers a shared *constant*; extend it to
  a shared object, and state for every plant which objects — not just which constants —
  treatment and control share.
- **Numerically verifying an algebraic cancellation is rule 21 in a new costume.** Before
  quoting a residual as a confirmation, ask what input could make it large. If none can, it is
  a round-off measurement. Instead, name the conditions under which the algebra fails and test
  *those* — for A.0.3 that is the magnitude-form FRC, and it fails by 200%.
- **Measure a metric's dominant nuisance parameter and publish its leverage next to the
  signal.** A split rule worth 50x the effect being measured is not a tidiness constraint, it
  is the headline.
- **A spec that states decision thresholds must state the metric's homogeneity degree and a
  photometric tolerance in the same table.** A degree-2 metric with a +-0.003 threshold is
  implicitly claiming 0.15% photometric control.
- **Rule 18 requires monotonicity, not just a stated direction.** A metric whose sign inverts
  as the defect grows is more dangerous than a blind one: it reads best exactly where the
  output is worst.
- **Replicate any derived engineering guidance on a subject the derivation did not use**
  before writing it into a contract. A.3.1's endpoint replicated; A.3.2's gradient did not, and
  the gradient is what became the advice.

## 11. Proposed questions

- What is this sensor's PRNU? Fact 610 needs 4.1% to be rescued; question 111 is unmeasured and
  the flats exist.
- Is there **any** statistic computable without ground truth that is monotone in MTF and degree
  0 in amplitude? PR6 shows the ground-truth oracle fails the first at a single frequency, so
  the answer may need a spectral *shape* comparison, not a single-frequency probe.
- Can the noise arm of the separation contrast be realised on real data **without** moving the
  split? If not, is there a design that measures blur-vs-noise discrimination on real merges at
  all?
- What sets the gate, if not `sigpow`? P11 leaves the shipped gate = 0.5 without measured
  justification.
- How much of a real half-merge's common power at `f_sig` is aliased content rather than
  resolved detail? P3 rules out FPN; the remainder is unattributed.
- Why is the contiguous-split penalty `K`-independent on flat ROIs (P23)? Something other than
  depth coverage operates there and it is unidentified.

---

## 12. What would be needed before `sigpow` could ship

The two convention fixes are done and correct. What remains:

1. **Stop reporting `S`.** Report `d_blur` with a confidence interval and the repetition count
   (P17). Re-state fact 619 and A.0.4 with intervals; on current evidence neither supports
   three significant figures.
2. **State and demonstrate a failure direction** (rule 18). P18 says there still isn't one:
   the response is U-shaped in true MTF, so this likely requires abandoning the
   single-frequency form rather than adjusting a threshold.
3. **Specify a photometric normalisation** and bound it below 0.1%, or delete A.4.2's numeric
   thresholds (P19).
4. **Handle the negative branch** — `d`'s sign convention, and what `Status` a negative reading
   should carry (P22).
5. **Write the split contract in, with its leverage number** (P20, P26), and weaken A.3.2's
   gradient guidance to the parity-vs-contiguous endpoint, which is all that replicated (P21).
6. **Validate against a latent-varying plant** — a nonlinear merge whose delivered scene
   depends on which frames it receives. Every plant in `m46lib` holds the latent fixed, and
   that is where the 10x effect lives (P10, P26).
7. **State A.0.3's `Re`-form condition** in the spec, next to G3 (P16).

Until 1, 2, 3 and 6 are done, no `sigpow` number should be folded as evidence about
resolution. **M46's central negative finding stands — the corpus had no instrument able to
score its central claim — and after the re-derivation it still does not.** The re-derivation
made the statistic well-defined. It did not make it valid.

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
| **`src/e8_canonical_plant.py`** | `out/e8_canonical.log/.json` | PR14, PR15, PR16, PR20, PR21 |
| **`src/e9_split_contract.py`** | `out/e9_split.log/.json` | PR17, PR18, PR19, PR22, PR24 |
| **`src/e10_stability.py`** | `out/e10_stability.log/.json` | PR23, PR22 verification |

Every number quoted above appears verbatim in those logs. **Known artefact, recorded not
hidden:** `e8_canonical_plant.py` has no `__main__` guard, so `e9`'s import of `canon` re-ran
it; `out/e9_split.log` therefore opens with E8's output. Both runs produced identical values.
`e10` re-implements `canon` locally to avoid the same side effect.

`.npz` intermediates are gitignored but present on disk. No file under `crates/`,
`experiments/m46-detail-metric/` or `experiments/m41-r3-kill/` was modified. `arm_A_gated` in
`e6` and `merge` in `e9` are documented copies; `e6` asserts equality with `m41lib.arm_A` at
gate 0.5 at runtime, and `e9` reproduces the author's A.3.1 table to six significant figures.
