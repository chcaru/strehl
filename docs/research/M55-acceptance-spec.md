# M55b — Pre-registered acceptance specification for a detail metric, v1

**This document and `experiments/M55-acceptance-spec/src/spec_v1.py` are committed before
any candidate metric exists, and neither may be relaxed to admit one.** The battery is
executable; the thresholds are numbers, not adjectives; every threshold's provenance is a
SYNTHESIS fact or a measurement made here and quoted verbatim from a committed log.

The battery has been **calibrated against four reference metrics before publication**: it kills
all three known-bad references and passes a passability probe, so it has demonstrated power in
both directions (rule 39). **The calibration changed the battery twice, and both revisions and
their logs are disclosed in §6 rather than hidden**, because a battery revised after seeing its
own results is exactly the risk pre-registration exists to control.

I did not look at M57's work and did not coordinate with it. No candidate influenced any
number here.

**Amended once after registration, on 2026-08-23**, because the owner renamed five corpus
directories mid-milestone and the rename exposed a defect in B6. Every amendment **tightens**
B6 and none loosens anything; the trigger was external to any candidate; no candidate existed.
The full account, the defect, the repair and the proof that the repair moved no number are in
§4.1 and P42-P43.

---

## 0. How this is used

A candidate is anything that answers *"did this merge deliver less real detail than that one?"*
It ships a `Candidate` object (§2) and is run through ten batteries. **A candidate is ACCEPTED
only if every battery passes.** There is no partial credit and no "noted but proceeding".

```
python experiments/M55-acceptance-spec/src/calibrate.py         # battery self-check
python experiments/M55-acceptance-spec/src/e14_b6_rollup_test.py  # B6 property tests
python experiments/M55-acceptance-spec/src/validate_heldout.py    # EXIF only
python experiments/M55-acceptance-spec/src/e13_rename_check.py    # EXIF only
```

`spec_v1.py` imports no candidate. `ref_metrics.py` exists solely to give the battery power.

---

## 1. The two decisions I was asked to make rather than assume

### 1.1 Decision — the parity split is a **pinned requirement**, and its leverage is **also** measured per candidate. MEASURED, and the reason is new.

The brief asked whether facts 641/702's parity contract belongs in the spec as a requirement or
as a property to be re-measured per candidate. **The answer is both, and the reason is that a
contiguous split is not a degraded measurement — it is a null reading.**

I built an empirical null for a ring cross-power by rolling one half-merge by ≥ 64 px, which
destroys pixel correspondence while preserving the marginals, the window and the ring exactly.
48 rolls per cell, three stacks, two ROIs each (`out/e12_null.log`):

```
   stack      ROI      split         C            mode-SE      sd(NULL)   NULL/modeSE     z
   112MSDCF   detail   parity       +4.4724e+07   1.4456e+06   1.2892e+06         0.9x     34.74
   112MSDCF   detail   contiguous   +2.1133e+05   3.3115e+05   4.7653e+05         1.4x      0.53
   112MSDCF   flat     parity       +1.8912e+06   9.6593e+04   1.1946e+05         1.2x     15.95
   112MSDCF   flat     contiguous   +5.5139e+04   3.3412e+04   6.9297e+04         2.1x      0.84
   113MSDCF   centre   parity       +5.3745e+07   1.9114e+06   2.9726e+06         1.6x     18.24
   113MSDCF   centre   contiguous   -1.8641e+06   5.2628e+05   1.2944e+06         2.5x     -1.25
   113MSDCF   flat     parity       +5.4186e+06   2.9644e+05   4.0203e+05         1.4x     13.79
   113MSDCF   flat     contiguous   +2.5227e+05   8.2454e+04   2.0039e+05         2.4x      1.45
   foam       centre   parity       +2.4702e+09   9.5842e+07   1.1869e+08         1.2x     20.58
   foam       centre   contiguous   +1.4292e+07   4.1623e+06   7.6286e+06         1.8x      1.91
   foam       flat     parity       +1.2561e+08   5.2672e+07   5.4348e+07         1.0x      2.18
   foam       flat     contiguous   +4.5459e+06   2.4176e+06   3.2544e+06         1.3x      1.28
```

**Contiguous sits inside the null in 6 of 6 cells — detail ROIs as well as flat.** Parity gives
z = +2.18 to +34.74. So facts 641/702's "contiguous/parity = 0.0047" is not a 99.5% loss of
signal; it is **a number divided by noise**, and every ratio built on it — including A.3.2's
block-of-2/block-of-4/random gradient, which I already refuted as fact 702 — was a ratio taken
inside the null.

Therefore: **`B6_SPLIT = "parity"` is pinned in the spec** (so no candidate can pick a
flattering split), **and** the split appears in every candidate's declared `nuisances` and is
scored by B3, because pinning a nuisance in a document does not stop an implementer getting it
wrong. On the development cell, sigpow's measured split leverage is **5.21x** the reference
signal step, which fails B3's pinned limit of 1.00.

### 1.2 Decision — a candidate **may** consume the calibrated sensor model, and doing so moves it into a stricter tier (B8). ARGUED from measured history.

The trade. **Against:** this project's calibration has been wrong, twice, in ways that survived
for months — the gain was wrong by a factor of two through twelve milestones (fact 599),
`rho = 0.3094` was refuted out of sample (fact 697), and read noise moved under M48 while three
agents were mid-flight. A metric that consumes a calibration constant inherits every one of
those. **For:** a metric forbidden the sensor model is blind to the one thing `strehl` claims to
know, and the project's whole thesis is that the estimator is noise-aware.

**Decision: permitted, with three conditions.** (a) The candidate must *declare*
`consumes_calibration` as a machine-readable list of attribute names. (b) B8 re-runs every other
battery with each named constant perturbed by **x0.5, x0.9, x1.1 and x2.0** and **the verdict of
every battery must be unchanged**. The x2.0 factor is not arbitrary: it is the size of the error
that actually happened. (c) Rule 34 binds: the plant must not supply the constant the candidate
consumes, so `Plant` takes `gain` from the caller and B8 perturbs it from outside.

A candidate that declares no calibration constant skips B8 and is recorded as
`skipped=True` — never as `passed` without qualification.

---

## 2. B0 — the candidate contract

Ten fields, all required, all machine-readable. Missing any one is a kill.

| field | meaning |
|---|---|
| `name`, `version` | identity |
| `consumes_calibration` | tuple of attribute names; triggers B8 |
| `uses_ground_truth` | bool; a true value makes the candidate inadmissible for shipping but still scoreable |
| `declared_range` | `(lo, hi)`; B5 enforces it on real data |
| `no_claim_floor` | `abs(d)` below which the candidate asserts nothing |
| `decision_threshold` | `abs(d)` above which it declares a change |
| `failure_direction` | which sign of `d` means detail was lost — **rule 18** |
| `nuisances` | dict name -> admissible values; every entry is scored by B3 |
| `property_tests` | path to an executable file asserting monotonicity, homogeneity, swap invariance and the negative branch |

**`property_tests` exists because of fact 711.** `b6_spec.py` is frozen with eight golden
vectors and no monotonicity, homogeneity or negative-branch test, which is precisely why three
critical defects survived freezing. **Golden vectors pin values; they do not pin properties.**
A candidate that ships golden vectors and no property tests fails B0 outright.

`value(a, b, ctx) -> (float, status)`. `status` may be `"Ok"` only when the reading is
admissible. **A non-Ok status must not be read as a number** — that is fact 706's failure mode
written into the type.

---

## 3. The batteries

### B1 — monotonicity in true resolution. Three arms, three threat models.

**Grid.** True MTF at `f_sig`, geometric from **0.98 to 0.01**, **17 points**, max adjacent
ratio **1.3318** (`out/calibrate.log`). Provenance: fact 703's inversion appeared between MTF
0.687 and 0.223, so a grid coarser than ~1.35 per step can straddle it.

**The reference signal step is a 10% MTF loss: Gaussian sd = 0.2645 px.** MEASURED
(`out/e11_q165.log`):
```
   PR29  Gaussian sigma 0.0500 px -> true MTF at f_sig=0.2762 is 0.996242   (loss  0.376 %)
   PR29  Gaussian sigma 0.1245 px -> true MTF at f_sig=0.2762 is 0.976929   (loss  2.307 %)
   PR29  Gaussian sigma 0.2645 px -> true MTF at f_sig=0.2762 is 0.900011   (loss  9.999 %)
   PR29  Gaussian sigma 0.5000 px -> true MTF at f_sig=0.2762 is 0.686288   (loss 31.371 %)
```
**M46's 0.05 px reference blur is a 0.376% MTF loss.** Every separation number in facts 619/640
was conditioned on a signal step three tenths of one percent in the quantity being measured,
while its nuisance moved the statistic by 100% (fact 705). That asymmetry is why the spec fixes
the signal step in **MTF**, which is physical, rather than in **pixels**, which is not.

**Arms.**
- **B1a — plain blur.** KILL on any resolved inversion.
- **B1c — blur plus a shared component capped at the measured non-generative bound.** The cap is
  **0.486%** of the reference merge's high-pass sd, DERIVED from fact 698's measured
  0.2888 DN sensor fixed pattern against a measured 59.47 DN reference `hp_sd`. KILL on any
  resolved inversion.
- **B1b — blur plus an unbounded shared component solved to restore `hp_sd` exactly**, which is
  fact 703's adversary. **RECORDED as a declared blind spot**, and killing only a candidate that
  claims safety against generative merges. §6.2 explains why this arm was demoted, and it is a
  softening of my own fact 703.

**RESOLVED** means the inversion exceeds **both** the candidate's own `no_claim_floor` **and**
3x the standard error of `d` over `b1_nrep = 8` noise realisations. A single realisation
manufactures inversions out of noise: this battery did exactly that to itself in calibration
(§6.1), which is rule 39 turned on the battery.

### B2 — homogeneity, both-sided and one-sided, plus swap invariance.

**Threshold: an 11.7% photometric gain applied to ONE input alone must move `abs(d)` by less
than the candidate's own `no_claim_floor`.** Provenance: 11.7% is the largest median level
difference measured between two merge configurations of the same stack (fact 704), so it is the
smallest perturbation the spec can afford to ignore. The one-sided case is the one that arises
— fact 701 measured `P_a/P_b = 1.30` between two real half-merges and nobody had tested it.

**Swap invariance is in the same battery**: `abs(value(a,b) - value(b,a))` must be below the
same floor. Provenance: fact 700 — the original `sigpow` was asymmetric by `P_a/P_b`, reported
as 1.96e-02 and actually 2.63e-01.

The battery also reports the measured homogeneity **degrees** `p_both` and `p_one`. A candidate
with either degree non-zero must ship a normalisation and be re-measured through it.

### B3 — nuisance leverage. The most valuable gate, and the newest.

For every nuisance an operator must choose, `L = max|d| across admissible values / |d| for the
reference signal step`.

**Thresholds: `L <= 0.10` for an unpinned nuisance; `L <= 1.00` for one the spec pins.**

*Defence of 0.10:* a 10% MTF loss must still read at >= 90% of its true value at the worst
admissible nuisance setting, so a nuisance error contributes at most a tenth of the signal.
*Defence of 1.00 for a pinned nuisance:* pinning stops a nuisance being *chosen* wrong; it does
not stop it being *implemented* wrong, and an implementation slip that outweighs the entire
signal is not survivable in shipped code. **Above 1.00 the candidate is not realisable** — the
operator cannot distinguish a real 10% resolution loss from a configuration choice.

Measured on the development cell (`out/calibrate.log`), against a signal step of `|d| = 0.19114`:
```
   sigpow-canonical      split 5.21x   nbin 1.00x   ring_offset 2.05x     (limit 1.00)
   band-ratio-PROBE      split 5.07x   nbin 2.12x   f_ref      10.91x     (limit 1.00)
```
**Which ring you evaluate has twice the leverage of a 10% MTF loss.** Both references die here.

### B4 — power. Specificity and sensitivity, both, at a realistic noise level.

Per rule 39, planting a wrong answer is mandatory. B4 does it in both directions over 32
repetitions at a plant noise of **3.7 e- per half-merge** — DERIVED, not chosen: a half-merge of
~16 accepted frames at 250 DN with `g = 1.14469 DN/e-` has a per-frame shot sd of 14.8 e-,
so 3.7 e- after averaging, plus a quarter of the 1.47 e- read noise.

- **Specificity**: two merges that differ only in noise realisation must read below
  `decision_threshold` in **>= 90%** of repetitions.
- **Sensitivity**: a real 10% MTF loss must read above `decision_threshold`, with the correct
  sign, in **>= 90%** of repetitions.

**Both, or the candidate dies.** This is the gate that makes fact 697 impossible to repeat: a
check that accepts everything fails specificity, and a check that accepts nothing fails
sensitivity. It is also the gate that killed the `constant` reference, which passes B1 and B2
— **proof that B1 and B2 alone are not sufficient.**

### B5 — sign and range contract.

- Every held-out cell returning `Status = Ok` must lie inside `declared_range`. **100%, no
  quantile.**
- The comparison denominator must be bounded away from zero in **every** cell; a candidate whose
  `d` is a ratio must declare `floor_ref` and demonstrate `|ref| > floor_ref` everywhere.
- A reading outside the admissible domain must return **`Status != Ok`, not a number**.

Provenance: fact 706. `sigpow` reads negative in 7 of 36 real cells, `d = (ref-test)/|ref|`
cannot be read when `ref < 0`, and A.4.2's sign rule silently inverts there — **under the split
the spec itself mandates**, not under abuse.

### B6 — the held-out real-data battery.

Named in §4. Each cell: form the parity half-merges `a, b`; the test pair is `blur(a), blur(b)`
at the reference signal step, so **the true ordering is known**. The cell passes if the
candidate detects the loss with the correct sign above `decision_threshold` **and** the
reference reading clears B9's null gate.

- **>= 90% of cells must pass** (`b6_quantile = 0.10` — the 10th-percentile cell must pass, not
  the median). Provenance: my six real cells under the old metric ranged 0.037 to 0.739 (fact
  696); a mean over cells hides failures that cluster in flat ROIs (facts 706, 707).
- **Zero cells may report the wrong direction above `decision_threshold`.** 100%, no quantile.
  A metric that is silent on 10% of ROIs is usable with care; one that confidently points the
  wrong way is not.

**Six cells across three stacks are NOT enough.** They were enough to refute, because one
counterexample refutes. They are not enough to accept: the spread across my six cells was larger
than any threshold worth setting, so a pass rate estimated from six cells has a standard error
of about 20 percentage points. **24 cells minimum: 6 stacks x 4 ROIs.**

### B7 — stability. The cheapest test in the corpus, and mandatory.

Vary **only** the Monte-Carlo repetition count over `1, 2, 4, 8, 16, 32, 64` and watch the
headline. Two kill conditions:
- the headline score moves by more than **0.05** across the sweep with everything else fixed;
- **or** the null term is within **2 standard errors of zero** at the largest repetition count
  while a ratio against it is quoted.

Provenance: fact 695. `S` read 0.770 / 0.976 / 0.937 / 0.972 at 1 / 8 / 32 / 64 reps on one
plant with nothing else changed. The second clause is the load-bearing one: it fires on both
`sigpow` and the passability probe in calibration even though their swings (0.015 and 0.024)
are inside the first clause's limit. **A separation score whose denominator is consistent with
zero is void however stable it looks.**

### B8 — calibration sensitivity. Applies only if `consumes_calibration` is non-empty.

Re-run every other battery with each declared constant scaled by **x0.5, x0.9, x1.1, x2.0**.
**Any change in any battery's verdict is a kill.** See Decision 1.2 for the defence of x2.0.

### B9 — null discipline. New, and it is the one I would keep if I could keep only one.

**Every real-data reading must be quoted with its roll-null z, and a reading at `|z| < 3.0` is
not a reading.** The null: 48 rolls of one input by >= 64 px in each axis, which preserves the
marginals, the window and the ring exactly and destroys pixel correspondence.

This is rule 39 made executable and it costs 48 FFT pairs. Its power is measured: on the same
development cell, `sigpow` reads **z = +34.74** and the band-ratio probe reads **z = +0.63** —
the probe's reading on a real merge pair is **indistinguishable from a reading on unrelated
images**, and no other battery caught that.

---

## 4. The held-out set — named now, before any candidate exists

**Six stacks, none used by M46 or by M55's attack, none of which I have scored.** Five of the
six directories were **renamed by the owner on 2026-08-23 while this milestone was running** —
same files, same counts, same bytes, new names. Both names are given so that no later reader
takes a pre-rename result for a different stack:

```
   stack            was         ARW     ISO   exp(1)   exp(n)      f  lens
   coffee-bean      -           105      50      4/5      5/8      8  FE 100mm F2.8 GM + 2x
   wrapped-text-1   131MSDCF    130     100     1/15     1/20   28/5  FE 100mm F2.8 GM + 2x
   wrapped-text-2   133MSDCF    120     400     1/40     1/40   28/5  FE 100mm F2.8 GM + 2x
   bee-1            134MSDCF    299     100      1/2      1/3   28/5  FE 100mm F2.8 GM + 2x
   bee-2            135MSDCF    299     400     1/20     1/25   28/5  FE 100mm F2.8 GM + 2x
   bee-3            136MSDCF    299     100      1/5      1/6   28/5  FE 100mm F2.8 GM + 2x
```

**MEASURED — I did not take the rename mapping on trust.** `src/e13_rename_check.py` re-read
EXIF from the new directories and matched each against the pre-rename fingerprints in the
already-committed `out/heldout.json`: frame count, ISO and exposure of the first *and* last
frame, f-number and lens. Those fingerprints are unique across all six stacks both before and
after, so the mapping is determined by the data rather than asserted. **All six agree with the
owner's stated mapping** (`out/e13_rename_check.log`). This is also a two-party EXIF cross-check:
my pre-rename read and the owner's post-rename read agree on every `n` and every ISO.

Three ISOs (50, 100, 400), five exposures, one optical configuration. First **64** frames of
each, **parity** split.

### 4.1 The rename revealed a defect in B6, and B6 is amended — MEASURED

The old numeric names concealed something that `bee-1 / bee-2 / bee-3` and
`wrapped-text-1 / wrapped-text-2` make obvious: **the six held-out stacks are only three
subjects.** B6 required six stacks and four ROIs each, 24 cells, and I wrote that requirement
believing six stacks meant six scenes. It does not. A pooled pass fraction over 24 cells can be
carried by one scene photographed three times.

Worse, on inspection forced by the rename: **`b6_min_stacks` and `b6_min_rois` were declared in
`TH` and in the prose kill condition and were read by no code at all.** `b6_rollup(cells)`
never received stack identity, so it would have accepted 24 cells from a single stack. That is
fact 711's disease — values pinned, properties not — reproduced *inside the spec written to
prevent it*. I found it only because the rename made me open the function.

Three amendments, all of which make B6 **strictly harder**:

- `TH["b6_min_subjects"] = 3`, and the pass fraction must hold **within each subject group**, not
  only pooled.
- Every cell must declare its `stack` and `roi`; a candidate that cannot supply them has not
  run B6.
- Coverage is now **enforced in `b6_rollup`**, not stated in prose.

**Power evidence, per rule 39 — a planted wrong answer is rejected.**
`src/e14_b6_rollup_test.py`, `out/e14_b6_rollup_test.log`, 7/7 assertions:

```
   PASS  planted: pooled 91.7% >= 90%, subject 'wrapped-text' 75% -> must KILL
          kill: subject groups below 90%: wrapped-text 75%
   PASS  24 cells from one stack -> KILL     kill: 1 stacks (need 6); 1 distinct subjects (need 3)
   PASS  cells that do not declare stack -> KILL
   PASS  one stack with only 3 ROIs -> KILL  kill: stacks with fewer than 4 ROIs: {'bee-2': 3}
   PASS  one wrong-sign cell -> KILL
   PASS  6 stack-slots but only 2 subjects -> KILL
```
The planted case is exactly the hole the rename exposed: **the pre-amendment code passed it.**

**The rule I used to decide the amendment was legitimate, and I propose it as a discipline.** A
pre-registered spec may be amended after registration only if (a) no candidate yet exists,
(b) the trigger is information from outside the candidate set — here, an owner's rename — and
(c) **the amendment can only tighten, never loosen.** All three hold. An amendment that could
loosen a threshold is indistinguishable from tuning, whatever its stated motive.

**What I could not fix.** Three subjects is the *ceiling* the corpus allows, not a target I
chose: every other stack is a development stack and is burned. B6 therefore cannot demonstrate
subject-generality beyond three scenes, and that is a stated limitation of this spec rather than
a solved problem. **A candidate that passes B6 has been shown to work on three subjects.**

### 4.2 A cross-ISO arm that the rename makes available — PRE-REGISTERED BUT CONDITIONAL

`bee-1` (ISO 100) and `bee-3` (ISO 100) against `bee-2` (ISO 400), and `wrapped-text-1` (100)
against `wrapped-text-2` (400), are matched-*subject* pairs straddling the sensor's dual-gain
boundary. If they are also matched *scenes*, they support a battery arm nothing else in the
corpus can support: **a candidate's verdict on the same subject must not change when only ISO
changes.** I pre-register it here, before any candidate exists, as **B6-ISO**, with the same
threshold as B6 and the same held-out status.

**It is conditional and I am not enabling it.** The owner has stated that whether the subject
and lighting held still between those captures is unknown and has asked. Exposures are not
matched either (ISO 100 at 1/2 s against ISO 400 at 1/20 s is 10x the light for 4x the gain), so
electron levels differ and equal signal must not be assumed. **B6-ISO is armed only if the owner
confirms the scene held still**; until then it is a named, dated, unexecuted arm, which is worth
recording precisely because it was written before the candidates.

### 4.3 A gear fact that arrived late, and what it can and cannot touch

Every frame in the corpus was shot through a **Breakthrough X4 CPL 67 mm circular polarizer**,
which was in no earlier brief. A polarizer suppresses specular highlights, so **clipping and
specular statistics on this corpus are not what a bare lens would give**. For this spec I
checked which of my constants could be affected and state the result rather than leave it open:
`b2_gain = 0.117` is a ratio between two merges of the *same* frames, so any fixed transmission
cancels; `b1_cap_frac = 0.004857` derives from **dark** frames, which have no light path at all.
Neither is exposed. The exposure of B5's range contract and B6's ROI content **is** — a ROI
that would clip on a bare lens may not clip here — and that is recorded as a limitation, not
measured.

**Development stacks, permanently excluded from B6:** `112MSDCF`, `113MSDCF`, `foam`,
`109MSDCF`, `119MSDCF`, `coffee-bubbles`. All six retain their original names.

**ROIs are fixed by a rule, not by choice** — four per stack, identical for every stack,
at fractions `(0.25,0.25) (0.75,0.25) (0.50,0.50) (0.50,0.80)` of the quad plane:
```
   [(458, 750, 512, 512), (1374, 750, 512, 512), (916, 1501, 512, 512), (916, 2402, 512, 512)]
```
No ROI can be selected on its result, by me or by anyone. Some will land on flat regions; that
is the point, and B9 will say so.

**I validated the substrate from EXIF and frame counts only** (`src/validate_heldout.py`,
`out/heldout.log`). No pixel of any held-out stack was decoded, merged or scored by me. **A
held-out set the spec's author has measured is not held out.**

---

## 5. What the battery measured about itself — calibration

`out/calibrate.log`, final run. `PASS`/`FAIL` are the battery's verdicts, not mine. **This
table has since been reproduced twice from scratch** -- `out/calibrate_rerun_after_recovery.log`
and `out/calibrate_after_rename.log` -- with no number differing in either.

```
   candidate                 B0    B1    B2    B4    B7   verdict
   sigpow-canonical       PASS  PASS  FAIL  FAIL  FAIL   REJECTED on B2, B4, B7
   constant               PASS  PASS  PASS  FAIL  FAIL   REJECTED on B4, B7
   ring-power-of-mean     PASS  PASS  FAIL  FAIL  PASS   REJECTED on B2, B4
   band-ratio-PROBE       PASS  PASS  PASS  FAIL  FAIL   REJECTED on B4, B7
```

**PR28 — power. MET.** All three known-bad references are killed.
**PR27 — passability. MET.** The probe passes B1 and B2, so the property gates are satisfiable.

Detail, verbatim:
```
   sigpow-canonical
        B2: an 11.7% one-sided gain (or a swap) moves |d| to 0.247689, 495.4x the no_claim_floor
        B4: specificity 0.25, sensitivity 1.00; both must be >= 0.90
        B7: ... the null is within 2 SE of zero at the largest REPS, so any ratio against it is void
        B1 inversion depth: B1a plain 0.0004018, B1c capped 0.0003902, B1b matched 0.13055
             (resolve threshold 0.0034321; cap amp 0.08618 DN, noise 3.7 e-, nrep 8)
        B2 degree: both-scaled +2.0000, one-scaled +1.0000;  swap d +0.000e+00
   constant
        B4: specificity 1.00, sensitivity 0.00; both must be >= 0.90
   band-ratio-PROBE
        B4: specificity 0.16, sensitivity 1.00; both must be >= 0.90
        B2 degree: both-scaled -0.0000, one-scaled -0.0000;  swap d +0.000e+00
```

---

## 6. Honest disclosures — the battery was revised twice during its own calibration

**Both revisions were forced by pre-registered falsifiers firing, and both logs are committed.**

### 6.1 Revision 1 — my own plant had rule 13's disease. Found by PR27.

The first calibration ran the plant at **zero noise**, which makes the two half-merges the
**same image** and silently degenerates every cross-power statistic into an auto-power. The
symptom was that `sigpow` and `ring-power-of-mean` — a correlation and a pure power — returned
the **identical** inversion depth of `0.128428`. Fixed by deriving a realistic plant noise
(3.7 e-, §B4) and turning it on in B1 and B2. Log preserved as `out/calibrate_v0_zeronoise.log`.

**Revision 2** followed immediately: with noise on and one realisation, three of the four
references (the `constant` excepted) "failed" B1a with inversions of 0.0025932, 0.0015306 and
0.0052401 where the noiseless value is exactly 0 — the battery
was manufacturing inversions out of noise and killing candidates on them. Fixed by averaging 8
realisations and requiring an inversion to exceed `max(no_claim_floor, 3 SE)`. Log preserved as
`out/calibrate_v1_1rep.log`. **This is the same defect I convicted fact 619 of, occurring in the
instrument written to prevent it, within an hour.** It is a general hazard, not a lapse of one
author, and I would not have caught it without a known-bad reference whose true answer I knew.

### 6.2 A protocol deviation, and it softens my own fact 703

**PR28 was pre-registered as requiring `sigpow` to be killed on B1.** After B1 was rebuilt with
a bounded threat model, `sigpow` **passes** B1: `B1a 0.00040`, `B1c 0.00039`, against a resolve
threshold of `0.00343`. The inversion survives only on the unbounded arm, `B1b 0.13055`.

The measurement behind the demotion: the shared-texture amplitudes that restore `hp_sd` in fact
703's adversary are **12.5 to 51.9 DN**, while the cap set by the sensor's own measured fixed
pattern is **0.086 DN**. **Fact 703's inversion requires a shared component 145x to 602x the
largest one a non-generative merge can produce.** So the correct scoping of fact 703 is: *the
inversion is real, and it is reachable only by a merge that injects structure common to both
half-stacks — a shared guide frame, a learned prior, a hallucinating denoiser — not by any
selector or linear estimator.* That is narrower than fact 703 as folded, it cuts against my own
headline, and it is what the measurement says.

**Every reference metric fails B1b, from 0.128 to 0.514.** B1b does not discriminate between
metrics; it characterises the class. That is why it is recorded as a declared blind spot rather
than a kill: a battery clause that every possible candidate fails removes no candidate and only
teaches the reader to ignore it.

**Risk I am flagging against myself:** changing a battery after seeing a known-bad reference's
result is tuning, and I did it. The mitigations are that every intermediate log is committed,
that both changes were driven by defects in the battery rather than by a candidate's score, and
that both made the battery **harder** to game (real noise, resolved inversions) even as they
made B1 easier to pass.

### 6.3 The passability probe is closer to a design than I would like

`REF_BANDRATIO` — cross-power at `f_sig` over cross-power at a low reference band — passes B1
and B2. I was told not to design candidates, and a reference that passes the property gates is
uncomfortably close to one. Three things reduce the discomfort and I state them rather than
hide the tension: it is **derivable in one step from fact 708** (a single-frequency probe is
blind, so use two); it **fails B3 at 10.91x on its own reference band and B9 at z = +0.63**, so
it is not a viable candidate; and it is labelled `PROBE` in the code. **M57 should not treat it
as a starting point, and if M57's design resembles it, that is convergent derivation from a
published fact, not leakage.**

### 6.4 Protocol incident — `spec_v1.py` was destroyed by my own tooling and rebuilt from bytecode

MEASURED. Partway through this milestone a patch script of mine opened
`experiments/M55-acceptance-spec/src/spec_v1.py` with an invalid `newline=` argument. CPython
truncates a file opened in `"w"` mode **before** it validates that argument, so the file went to
zero bytes and then raised. It was uncommitted; git held no copy. The battery in this document
is therefore not the file I originally typed.

It was recovered from `src/__pycache__/spec_v1.cpython-312.pyc`, written at 13:53:53, nineteen
seconds before the truncation, whose 16-byte header records a source size of 27874 bytes — the
final version. I reconstructed the source from the bytecode: every code object's
`co_firstlineno`, `co_consts`, `co_names`, `co_varnames`, default tuples and full disassembly.
Six code objects differed on the first attempt and each difference was diagnosed from the opcode
stream and repaired: `dict(...)` where the original had a dict literal (`BUILD_CONST_KEY_MAP`,
in `b1_monotonicity` and `run_plant_batteries`), an operator grouping in `Plant.pair`
(`* (noise_e * self.gain)`), an inverted conditional expression in `b0_declaration`, a chained
`name = version = None`, and `nuisances = {}` where I had written `None`.

The result is verified three ways and the third is the one that matters:

1. **Bytecode.** All 35 code objects compare equal on `co_code`, `co_names`, `co_varnames`,
   non-code `co_consts`, `co_stacksize`, `co_flags`, `co_argcount` and `co_firstlineno`. The
   only surviving difference is `co_linetable` in 15 objects — 42 instructions carry a
   different line span and 298 a different column span, i.e. some multi-line expressions are
   wrapped differently. Identical bytecode cannot execute differently; only a traceback's
   reported position can move. With the deliberately added `_summary()` / `__main__` block
   removed, the module object matches too.
2. **Line alignment.** All 44 top-level definitions land on their original line numbers, so
   every line reference in this document still resolves.
3. **Behaviour.** `calibrate.py` — untouched throughout — was re-run against the reconstruction,
   799 s, output at `out/calibrate_rerun_after_recovery.log`. Against the pre-truncation
   `out/calibrate.log` it differs on **3 of 83 lines, and no number differs on any of them**.
   The three are the print order of the `killed` dict, whose keys come from a Python **set**
   literal in `ref_metrics.py` and therefore depend on `PYTHONHASHSEED`; all three entries are
   `true` in both runs. Every threshold, every leverage ratio, every z, every verdict is
   character-identical.

Two things the reader is owed. **Comments are not the originals** — bytecode does not carry
them, so every comment in `spec_v1.py` was re-authored from the code it sits above. Docstrings
*are* original: they are constants and survived verbatim, which is why the `Candidate` contract
text and the kill conditions are the ones I wrote. And **the set-ordering nondeterminism found
by this comparison is a real, if harmless, defect in my own harness**: a battery that is meant
to be re-runnable by a third party should not serialise a set. It changes no value and no
verdict; it would change a byte-for-byte artefact comparison, and anyone re-running
`calibrate.py` should compare parsed JSON, not bytes.

---

## 7. Question 165, answered — and the question's premise was wrong

Question 165 asked why the flat-ROI contiguous penalty is K-independent, and the brief's worry
was that an unidentified mechanism operating on flat ROIs might mean the real-data battery
measures it rather than the candidate. **The worry was justified; the mechanism is not
specific to flat ROIs.**

**The answer (MEASURED, `out/e12_null.log`): a contiguous split of a real focus stack produces
two half-merges whose ring cross-power is statistically indistinguishable from that of two
unrelated images — on all six cells, detail ROIs included.** `|z| <= 1.91` everywhere. The
flat-ROI value is K-independent because it is not a measurement of anything, and the detail-ROI
value is not either. Facts 707's "something else operates on flat ROIs" dissolves: nothing
operates on flat ROIs, and nothing operates on detail ROIs under a contiguous split.

**I did not get there by the route I pre-registered, and my own falsifier fired twice on the
way.**
- **PR26 refuted.** I first measured the cross-**stack** cross-power — same ROI coordinates,
  different subjects — and found it at **148%, 118% and 28%** of the within-stack parity value,
  which reads like a large sensor-fixed floor. It is not: **PR30 refuted my own reading.**
  `sd(NULL)/mode-SE` over 12 cells is min 0.9x, median 1.4x, max 2.5x — the mode-scatter
  standard error is adequate, and those cross-stack numbers are simply draws from a wide null.
- **PR31's criterion was not met as written.** I had pre-registered that flat ROIs would sit
  inside the null while detail ROIs sat outside. Detail ROIs are inside too. The criterion
  failed because it presupposed a contrast that does not exist, and the absence of the contrast
  is the stronger finding. I am recording the criterion as **not met** rather than relabelling it.

**Consequence for the battery:** B9 exists because of this, and B6 pins parity because of this.
The residual risk the brief named — that a real-data battery measures an unidentified nuisance
rather than the candidate — is now **detectable per cell at the cost of 48 FFT pairs**.

### 7.1 A reconciliation the corpus needs: fact 707's numbers depend on a definitional choice

`e9` and `e11` disagreed on 113MSDCF's flat K-table. The cause (PR32, `out/e12_null.log`):
```
   113MSDCF flat: E9 best-focus frame 38; E11 best-focus frame 39
   e9_grad       K= 8 +0.3502   K=16 +0.3528   K=32 +0.3568
   e11_coarse    K= 8 +0.1636   K=16 +0.1698   K=32 +0.1224
```
E9 takes best focus as the argmax of a gradient on the ROI; E11 as the argmax of the coarse
focus field. **One frame's difference moves the published numbers by a factor of two.** Fact
707's qualitative claim — no trend toward 1.0 as K narrows — replicates under both. Its numbers
should be quoted as approximately 0.15 to 0.36, not to four figures. Both scripts are correct;
the quantity is definition-dependent, which §7's answer explains: they are all null readings.

---

## 8. Proposed facts

Numbers are placeholders; the orchestrator assigns them.

- **P30 (MEASURED).** A contiguous half-stack split produces two half-merges whose ring
  cross-power is inside an empirical roll-null on **6 of 6 real cells** (`z` = +0.53, +0.84,
  −1.25, +1.45, +1.91, +1.28), detail ROIs as well as flat, while a parity split gives
  `z` = +2.18 to +34.74. **Facts 641/702's contiguous readings are null readings, so the ratios
  built on them — including A.3.2's split gradient — were ratios taken inside the null.**
- **P31 (MEASURED).** A roll of one input by >= 64 px gives a usable empirical null for any
  pairwise image statistic at a cost of 48 FFT pairs, and it discriminates: on one real cell
  `sigpow` reads `z = +34.74` and a two-band ratio reads `z = +0.63`.
- **P32 (MEASURED).** A within-ring mode-scatter standard error is **adequate** for this
  statistic: `sd(roll-null)/mode-SE` is 0.9x to 2.5x, median 1.4x, over 12 cells. My own
  suspicion that it understated the null is refuted.
- **P33 (MEASURED).** **M46's 0.05 px reference blur is a 0.376% MTF loss at `f_sig`.** A 10%
  MTF loss is 0.2645 px. Every separation number in facts 619/640 was conditioned on a signal
  step three tenths of one percent in the quantity being measured.
- **P34 (MEASURED, and it softens fact 703).** The shared-texture amplitude that restores
  `hp_sd` in fact 703's adversary is **12.5 to 51.9 DN**; the cap implied by the sensor's own
  measured fixed pattern (fact 698) is **0.086 DN**. **Fact 703's inversion needs a shared
  component 145x-602x anything a non-generative merge can inject.** Under a bounded threat model
  `sigpow` is monotone (`B1a 0.00040`, `B1c 0.00039` against a 0.00343 resolve threshold); the
  inversion is reachable only by a merge that injects structure common to both half-stacks.
- **P35 (MEASURED).** **A.4.2's +-0.003 decision threshold has a 75% false-alarm rate** at a
  realistic merge noise of 3.7 e-: `sigpow` specificity **0.25** over 32 repetitions, sensitivity
  1.00. A two-band ratio scores 0.16. **Sensitivity was never the problem; specificity is.**
- **P36 (MEASURED).** On a real development cell, against a 10% MTF loss, **the choice of which
  ring to evaluate has leverage 2.05x** and the choice of ring binning 1.00x. Combined with
  fact 705's split leverage (5.21x here), a ring metric's three configuration choices each
  outweigh the signal.
- **P37 (MEASURED).** A metric that returns a **constant** passes a monotonicity battery and a
  homogeneity battery. **Monotonicity and homogeneity gates alone cannot reject a metric that
  measures nothing;** only a two-sided power test can.
- **P38 (MEASURED, against my own instrument).** An acceptance battery run at zero plant noise
  makes both half-merges the same image and degenerates every cross-power into an auto-power:
  a cross-power and a pure power returned the identical inversion depth `0.128428`. Run at one
  noise realisation, it manufactured inversions of 0.0026-0.0052 where the true value is 0.
  **Both defects appeared in the instrument written to prevent them, within an hour.**
- **P39 (MEASURED).** Fact 707's numbers move by a factor of two on the definition of
  "best-focus frame" (frame 38 vs 39): 0.3502/0.3528/0.3568 against 0.1636/0.1698/0.1224. The
  qualitative claim replicates under both definitions.
- **P40 (MEASURED, AMENDED after the 2026-08-23 rename -- see P44).** The held-out substrate
  exists: six unused stacks, 105-299 frames each, three ISOs, one optical configuration,
  validated from EXIF without decoding a pixel. I originally wrote "and is adequate".
  **That word is withdrawn:** the six stacks are only three subjects.
- **P41 (MEASURED).** The mid-milestone rename of five corpus directories was verified from the
  data, not accepted on assertion: each new directory's EXIF fingerprint (frame count, ISO and
  exposure of the first *and* last frame, f-number, lens) matches exactly one pre-rename entry
  in the already-committed `out/heldout.json`, and those fingerprints are unique across all six
  held-out stacks. All six agree with the owner's stated mapping. Two independent EXIF reads,
  different days, different code, agree on every `n` and every ISO.
- **P42 (MEASURED, against my own instrument, again).** B6's coverage kill condition -- "fewer
  than 6 stacks or fewer than 4 ROIs per stack" -- was declared in `TH` and in prose and was
  **read by no code**. `b6_rollup(cells)` never received stack identity and would have accepted
  24 cells from one stack. **Fact 711's disease reproduced inside the spec written to prevent
  it.** After repair, a planted set with pooled pass fraction 91.7% (above the 90% gate) and one
  subject group at 75% is **killed**; the pre-repair code passes it. 7/7 property assertions,
  `out/e14_b6_rollup_test.log`.
- **P43 (MEASURED).** The repair is numerically inert, pre-registered before the run: a full
  re-run of `calibrate.py` (833.8 s) differs from the pre-edit run on **4 of 83 lines** -- one
  is the held-out name line that was the point of the edit, three are the known
  `PYTHONHASHSEED` set-ordering block. **Parsed JSON compares equal order-insensitively: not one
  number moved.** `out/calibrate_after_rename.log`.
- **P44 (MEASURED, and it weakens P40).** The six held-out stacks are **three subjects**:
  `bee-1/-2/-3` are one, `wrapped-text-1/-2` are another, `coffee-bean` is the third. Six stacks
  is not six scenes, and three is the ceiling the corpus allows because every other stack is a
  burned development stack. **A candidate that passes B6 has been shown to work on three
  subjects, not six.**
- **P45 (DERIVED).** Within the held-out set, subject and ISO are crossed on two subjects:
  `bee-1`/`bee-3` at ISO 100 against `bee-2` at ISO 400, and `wrapped-text-1` at 100 against
  `wrapped-text-2` at 400. Exposures are not matched (10x the light for 4x the gain), so equal
  electron level must not be assumed. Whether the scene held still between captures is
  **unverified**, so the cross-ISO arm B6-ISO is registered and left disarmed.

## 9. Proposed disciplines

- **Build the null by permuting the data, not by resampling the statistic's internals.** A roll,
  a rotation or a subject swap answers "what would this read on data that cannot contain the
  effect?". Quote every real-data reading with its null z. A reading that a null reproduces is
  not a reading, whatever its standard error says.
- **Fix a signal step in the physical quantity, never in the operator's units.** "0.05 px of
  blur" sounds small and is: 0.376% of MTF. "A 10% MTF loss" is checkable against a lens.
- **A threshold without a specificity measurement is a wish.** Before publishing a decision
  threshold, feed it pairs that differ only in noise and count how often it fires.
- **Pin a nuisance in the spec AND measure its leverage anyway.** Pinning stops it being chosen
  wrong; it does not stop it being implemented wrong.
- **Calibrate an acceptance battery against a known-bad reference and a passability probe before
  publishing it, and commit the intermediate logs.** A gauntlet nothing can pass is not a
  gauntlet; a gauntlet everything passes has no power. Both directions must be measured, and the
  revision history is part of the evidence.
- **State the threat model a monotonicity claim is made under.** An adversary that requires an
  amplitude 145x anything the physical system can produce characterises a class of statistics;
  it does not disqualify one member of it.
- **Golden vectors pin values; they do not pin properties.** A frozen spec must freeze
  monotonicity, homogeneity, swap invariance and the negative branch as executable assertions.
- **A corpus rename is a silent-failure event, not a cosmetic one.** A `glob` on a directory
  that no longer exists returns `[]` and raises nothing, so a measurement that reads zero files
  reports zero problems. After any corpus change, grep every script for hardcoded stack names
  before the next run, and verify the mapping from EXIF rather than from the announcement.
- **A pre-registered spec may be amended only if it can be shown that the amendment could not
  have been tuned.** Three conditions, all checkable by a third party: no candidate yet exists,
  the trigger is external to the candidate set, and the amendment can only **tighten**. An
  amendment that could loosen a threshold is indistinguishable from tuning whatever its motive.
- **A kill condition that no code reads is prose.** Every threshold in a spec's constant table
  must be traceable to a line that enforces it, and the enforcement must be shown rejecting a
  planted violation. Two of this spec's own thresholds sat unenforced until a directory rename
  forced the function open.
- **An executable spec must be bit-reproducible by a third party, so never serialise a set.**
  Re-running this battery produced output identical in every number and different in three lines,
  purely because a `set` literal's iteration order follows `PYTHONHASHSEED`. Found only because
  the run was diffed against its own earlier log; a spec whose artefacts are compared by hash
  would have reported a false regression.
- **Treat an uncommitted experiment file as already lost.** `open(p, "w")` truncates before it
  validates its own arguments, so a script that fails on line 1 can still destroy its input.
  Commit before patching, or patch via a temp file and `os.replace`.

## 10. Proposed questions

- Is there any statistic that passes B4's **specificity** clause at 3.7 e- with a threshold small
  enough to pass B6's sensitivity clause? Both references fail at 0.16-0.25, and it is not
  obvious the pair of constraints is simultaneously satisfiable at one frequency.
- What upper bound can be put on the shared structure a **non-generative** merge injects between
  two disjoint half-stacks? P34 uses the sensor fixed pattern, which is the only measured term.
  A shared guide frame or a shared prior is not bounded by it, and `strehl`'s own merge should be
  audited for one.
- Since a contiguous split reads inside the null (P30), **is a parity split's `z = +34` measuring
  delivered detail or shared latent?** Both halves see the same subject at the same focus; the
  battery cannot yet separate "the merge preserved detail" from "the two halves saw the same
  thing".
- What is the smallest number of held-out cells that can *accept* a metric at a stated
  confidence? I set 24 by argument, not by a power calculation.

---

## 11. What a candidate must deliver

1. A `Candidate` subclass with all ten B0 fields.
2. An executable `property_tests` file asserting monotonicity, homogeneity, swap invariance and
   the negative branch — not golden vectors.
3. A declared `decision_threshold` that passes B4 in **both** directions.
4. A declared normalisation if either homogeneity degree is non-zero.
5. A declared threat model saying whether it claims safety against generative merges (B1b).
6. `consumes_calibration`, complete; B8 will perturb every entry by x2.
7. The full battery output, including the roll-null z of every held-out cell.

**Nothing in this file may be relaxed to admit a candidate. If a threshold here is wrong, the
argument for changing it must be made without reference to any candidate's score, and the
change must be committed before the candidate is re-run.**

---

## Appendix — evidence

| Script | Output | Purpose |
|---|---|---|
| `experiments/M55-acceptance-spec/src/e11_q165.py` | `out/e11_q165.log/.json` | PR25, PR26, PR29 |
| `src/e12_null.py` | `out/e12_null.log/.json` | PR30, PR31, PR32 — the roll-null |
| `src/spec_v1.py` | — | the executable specification |
| `src/ref_metrics.py` | — | four references: three known-bad, one passability probe |
| `src/calibrate.py` | `out/calibrate.log/.json` | PR27, PR28 — final |
| " | `out/calibrate_v0_zeronoise.log/.json` | revision 1 disclosure (6.1) |
| " | `out/calibrate_v1_1rep.log/.json` | revision 2 disclosure (6.1) |
| `src/validate_heldout.py` | `out/heldout.log/.json` | substrate only; no pixel decoded |

Every number in this document is quoted verbatim from those logs. `e11_q165.py` contains a
disclosed defect in its standard error (a division by a possibly-negative half-plane sum,
producing `inf` in three cells); it is **not** edited, per rule 15, and `e12_null.py` supersedes
it. All scripts have a `__main__` guard. No file under `crates/`,
`experiments/m46-detail-metric/` or `experiments/m41-r3-kill/` was modified.
