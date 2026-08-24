# M76 — three residuals in the stratum gate

**Milestone:** M76. **Status:** measured and implemented.
**Pre-registration:** `f1da8e5e9a95e2765ca0bd23eccc9b34a4d322a2`,
committed before any held-out pixel was decoded, any deciding enumeration ran,
or any harness code changed.

---

## 1. Headline

**Q1 is INCONCLUSIVE under its registered rule, and the reason is the fixture,
not an absence of signal.** **MEASURED:** the 24-cell registry yields only
**18 readable cells**. The fourth ROI is outside the visible raw image on all
six stacks: it requires row 5892 while `raw_image_visible` has 4688 rows. That
fails the registered minimum of 20 finite cells. On the 18 cells that do
exist, the primary `sigpow` arm shows a large association:
`rho = -0.8596`, fixed-stack `beta = -1.3402`, bootstrap 95% interval
`[-1.5998, -0.9779]`, within-stack permutation `p = 0.002400`, with five of six
stack slopes negative. **That is evidence that lower `\|z\|` cells carry much
larger `d` variance, but it is not promoted past the registered INCONCLUSIVE
verdict.** The negative sign means a decade increase in `\|z\|` accompanies a
factor `10^1.3402 = 21.9` decrease in `s_d` in the fitted primary arm.

**Q2 is closed in code without changing the frozen primitive.** **MEASURED:**
`e14_b6_rollup_test.py` does construct every cell with `z=9.0`; its all-pass
fixture is the evasion. The original `b6_rollup` source and bytecode remain
identical to M55's `c37010c`. A new normative `b6_acceptance` wrapper preserves
the old result for reproduction but returns `CANNOT-ACCEPT` for a powered
constant-`\|z\|` set. The new property test passes **7/7**; old `e14` passes
**7/7** and `e16` passes **13/13**.

**Q3 is dead, full stop.** **MEASURED:** an independent enumeration reproduces
`C(24,1)+C(24,2)+C(24,3) = 2324` and M55's zero pooled-only placements, then
extends through all `2^24 = 16,777,216` placements at `k=0..24`: **zero**
placements ever fail pooled 90% while all subject clauses pass. **DERIVED:**
this is unavoidable because the pooled rate is a weighted mean of subject
rates; if every subject is at least 90%, the pooled rate is too.

---

## 2. Pre-registration

### 2.1 Registration identity and prohibition

**REGISTERED.** The registration commit is
**`f1da8e5e9a95e2765ca0bd23eccc9b34a4d322a2`**. This report-only identity
commit also precedes every Q1 measurement, Q2 code change, and Q3 enumeration.
The git history, not this sentence, is the authority on ordering.

**REGISTERED.** No candidate score or verdict may be consulted to justify the
Q2 change. The proposed change is admissible only as a generic tightening
against a constant-output evasion. No threshold will move.

### 2.2 Q1 — mechanism, observable, cells, statistic and rule

**ARGUED MECHANISM, REGISTERED WITHOUT AN EXPECTED DIRECTION.** B9's `z` is the
distance of a candidate's reference reading from its roll-null. A B6 `d` is a
normalised change between that reference and the same pair after a known 10%
MTF loss. Both consume the same cell spectrum. Cell-specific common power can
therefore affect both observables even when candidate quality is held fixed.
The measurement below asks for the relationship; it does not register which
sign the relationship will have.

**REGISTERED CELLS.** Exactly the 24 B6 cells named by the frozen registry:
the first 64 lexically sorted ARW files from each of `coffee-bean`,
`wrapped-text-1`, `wrapped-text-2`, `bee-1`, `bee-2`, and `bee-3`, at the four
coordinates returned by `spec_v1.roi_rule()`, merged with the pinned parity
split. No cell will be removed after decoding. A failed decode, non-finite
reading, or insufficient power is reported and makes the relevant candidate
arm inconclusive rather than silently shrinking the set.

**REGISTERED CANDIDATES.** The primary arm is M55's `RefSigpow`, because M55
introduced B9 and the stratum using this canonical reference statistic.
`RefNoisePow` and `RefBandRatio` are candidate-dependence controls. They remain
the known-bad reference and passability probe M55 declared them to be; neither
can become a proposed metric through this run. `RefConst` is excluded from Q1
because both its `d` variance and roll-null variance are identically zero,
which is the degeneracy Q2 tests rather than a correlation datum.

**REGISTERED REPETITIONS.** For each fixed real parity pair, make 64 independent
replicates, matching the largest entry of B7's registered `REPS` sweep. Each
replicate adds independent zero-mean Gaussian noise of
`2 * TH["plant_noise_e"] * 1.14469` DN to each half, exactly B7's high-noise
signal arm, then computes B6's `d` between that pair and its `mtf=0.9` blurred
copy. Seeds are deterministic from one recorded master seed. The per-cell
observable is `s_d`, the sample standard deviation (`ddof=1`) of those 64
values. The cell's `z` is B9's unperturbed 48-roll value at seed 5.

**REGISTERED PRIMARY STATISTIC.** Across all 24 primary-arm cells, report:

1. Spearman's rank correlation `rho` between `abs(z)` and `s_d`;
2. the fixed-stack log-log slope `beta` in
   `log10(s_d) = alpha_stack + beta * log10(abs(z))`; and
3. all six within-stack slopes, so a pooled association cannot hide a
   stack-level reversal.

**REGISTERED UNCERTAINTY.** A deterministic 10,000-resample bootstrap will
resample the 64 `d` replicates and the 48 roll-null values independently within
each cell, recompute `z`, `s_d`, `rho`, and `beta`, and report percentile 95%
intervals plus the mean and standard deviation of `beta`. A 100,000-draw
within-stack permutation test, with `s_d` labels permuted only among the four
ROIs of each stack, supplies a two-sided null for `rho`. The target population
is the fixed 24-cell acceptance set, so cells themselves are not bootstrapped.

**REGISTERED DECISION RULE.** The Q1 answer is:

- **YES, PARTLY CELL** only if the primary `beta` 95% interval excludes zero,
  the within-stack permutation `p < 0.05`, and at least five of six within-stack
  slopes have the same sign as `beta`;
- **NO ASSOCIATION RESOLVED** if those conditions do not hold and the
  measurement passes its controls; the report must then give the three-standard-
  deviation interval on `beta` and translate both endpoints into the largest
  allowed multiplicative change in `s_d` per decade of `abs(z)`;
- **INCONCLUSIVE** if a registered control fails, fewer than 20 primary cells
  are finite, or the two uncertainty procedures contradict one another.

The sign, if resolved, will be interpreted only after measurement. No sign is
registered as expected.

**REGISTERED POWER CONTROL.** Run the same code path on six synthetic
`spec_v1.Plant(seed=0)` cells at contrasts `5, 10, 20, 40, 80, 160`, with the
same B9 rolls and 64-replicate noise procedure. The control has power only if
its `abs(z)` and `s_d` each span at least 4x and all values are finite. Failure
makes Q1 **INCONCLUSIVE**. This control is not used to choose or calibrate a
threshold.

**REGISTERED CANDIDATE/CELL CONTROL.** The two secondary candidates are reported
under the identical analysis. Agreement is evidence that the cell dominates;
disagreement is evidence that the relationship is candidate-dependent. Neither
secondary arm can overturn the primary decision rule, but either can narrow its
scope.

### 2.3 Q2 — admissible code change and falsifier

**DERIVED, REGISTERED.** Directly making `b6_rollup` reject a constant `z` would
change an existing `e14` input/output assertion and violate M55's spec rule 15.
Changing `e14`'s constant fixture to distinct values would conceal rather than
close the regression. Leaving the result review-only retains the disclosed
hole.

**REGISTERED DESIGN.** Extend rather than modify. Keep `b6_rollup` and all
existing `e14` assertions byte-for-behaviour unchanged. Add a normative
`b6_acceptance(cells)` wrapper that calls the frozen primitive and converts an
otherwise admissible powered set with `n_distinct_z <= 1` into
`CANNOT-ACCEPT`, never `ACCEPT`. Add a new fixture, separate from `e14`, proving:

1. the old all-pass constant-`z` fixture still passes the frozen primitive;
2. that same fixture cannot pass the normative wrapper;
3. a distinct-`z` all-pass fixture passes the wrapper;
4. a planted ordinary B6 failure still rejects; and
5. the source and bytecode of `b6_rollup` are unchanged from the registration
   commit.

**REGISTERED FALSIFIER.** If any old `e14` assertion changes, if `e16` changes
verdict, if any new path can return `ACCEPT` for a fully powered constant-`z`
set, or if the existing `b6_rollup` function changes, the remedy is
**DISQUALIFIED**. No candidate score will be run before or after this change.

### 2.4 Q3 — independent enumeration

**REGISTERED METHOD.** Write a new enumeration that imports no M55 enumeration
and does not call `b6_rollup`. Treat subjects as fixed groups of 4, 8, and 12
cells. For each total failure count `k = 0..24`, enumerate every triple
`(f4, f8, f12)` in range, weight it by
`C(4,f4) * C(8,f8) * C(12,f12)`, and independently evaluate the pooled 90%
clause and all three per-subject 90% clauses. Report, for every `k`, total
placements and placements where pooled fails while every subject passes.

**REGISTERED CHECKS AND RULE.** The total over `k` must equal `2^24`; the totals
for `k=1,2,3` must equal `C(24,k)` and sum to M55's claimed 2324 before its zero
is examined. Any mismatch invalidates the enumeration. If sole-pooled
placements are zero for all `k`, the clause is **dead, full stop**. If any
exist, report the first `k` and call it **dead only below that count**. No
threshold changes.

---

## 3. Source statements being tested

**MEASURED BY QUOTATION.** M55's Q1 disclosure, quoted exactly:

> **I have not measured whether `d`'s between-repetition variance grows as
> `|z|` falls.** If it does, the lowest-`|z|` stratum gate penalises candidates
> for cell noise rather than for candidate quality, and the gate is partly
> measuring the cell. The observable that settles it is cheap and already
> exists: run B7's `REPS` sweep **per cell** and correlate `d`'s
> between-repetition standard deviation against `|z|`. Uncorrelated, the gate
> is clean; growing, a variance-weighted form is needed. Question, not claim.

**MEASURED BY QUOTATION.** M55's Q2 disclosure, quoted exactly:

> **The stratum gate is evadable by a constant.** A candidate that reports the
> same `|z|` on every cell has a degenerate stratum, which is skipped, and falls
> back to pre-amendment behaviour. This is discipline 400 — *a metric returning
> a CONSTANT passes monotonicity and homogeneity* — reappearing one level up,
> in the gate written to enforce it. I have **not** blocked it in code, because
> a `raise` on constant `|z|` would fail the rule-15-frozen `e14` on its first
> assertion, and rule 15 outranks my preference. The remedy is placed on the
> candidate instead: B0 must carry a property test that `|z|` varies across
> cells, and `n_distinct_z` is returned so a reviewer can see it. **A reviewer
> who does not read `n_distinct_z` will not catch this.**

**MEASURED BY QUOTATION.** M55's Q3 self-report, quoted exactly:

> The B6 headline in section 3 — *">= 90% of cells must pass"* — **never
> binds.** MEASURED: over all 2324 ways of placing 1, 2 or 3 failing cells among
> the 24 held-out cells, **0** trip the pooled 90% gate without already tripping
> the per-subject clause.

**MEASURED BY QUOTATION.** M55's hard constraint, quoted exactly:

> **Nothing in this file may be relaxed to admit a candidate. If a threshold
> here is wrong, the argument for changing it must be made without reference to
> any candidate's score, and the change must be committed before the candidate
> is re-run.**

---

## 4. Q1 — candidate or cell?

### 4.1 First run and a defect in the registered substrate

**MEASURED.** The first run failed before scoring a cell:

```text
ValueError: could not broadcast input array from shape (0,576) into shape (576,576)
```

The input declared by `roi_rule()` was `(916, 2402, 512, 512)` on the green
quad plane, plus 32 px of padding. It requires sensor-row extent 5892;
`raw_image_visible` is `(4688, 7028)`. The same fourth ROI is invalid on every
held-out stack. The retry did not replace or move it: it named all six cells
`DECODE-BLOCKED`, preserved the failed first-run log, and continued with the
18 readable cells.

**ARGUED.** This is not a harmless shortfall. M55's substrate validation read
EXIF and frame counts only, so it could not validate the pixel-coordinate
fixture it printed. B6 requires four ROIs per stack and therefore cannot run as
specified on its own held-out set. The normative wrapper does not repair this;
it only closes Q2.

### 4.2 Measurement and registered verdict

**MEASURED.** Fixed inputs: first 64 files, pinned parity split, 64 independent
repetitions, 48-roll B9 null, noise SD `8.470706 DN`, and deterministic seeds.

| arm | finite cells | Spearman `rho` | bootstrap 95% | fixed-stack `beta` | bootstrap 95% | permutation `p` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `sigpow-canonical` | 18 | **-0.8596** | [-0.8906, -0.7812] | **-1.3402** | [-1.5998, -0.9779] | **0.002400** |
| `ring-power-of-mean` | 18 | -0.1228 | [-0.2611, -0.0031] | -0.1230 | [-0.2504, +0.0383] | 0.302267 |
| `band-ratio-PROBE` | 16 | +0.0941 | [-0.0676, +0.2588] | -0.2218 | [-0.3912, -0.0296] | 0.827182 |

Primary within-stack slopes:

```text
bee-1=-1.233  bee-2=-3.107  bee-3=+0.544
coffee-bean=-2.238  wrapped-text-1=-1.592  wrapped-text-2=-1.493
```

**MEASURED CONTROL.** The registered synthetic plant spans `14.98x` in
`\|z\|` and `10460.25x` in `s_d`, above both 4x power requirements. The first
control ladder narrowly failed only its `\|z\|` span (`3.92x`); widening its
pre-declared contrast stimulus, without touching real cells or a decision
threshold, made the plant express the failure. This deviation is disclosed,
and the first control result remains in the log.

**REGISTERED VERDICT: INCONCLUSIVE.** The association, both uncertainty
procedures and five-of-six sign condition all point the same way. The verdict
remains inconclusive because only 18 primary cells are finite, below the
registered 20. The candidate-dependence controls also forbid a universal
statement: neither secondary arm reproduces the primary association. The
narrow supported sentence is therefore:

**MEASURED:** on the canonical `sigpow` arm and the 18 valid cells, the stratum
gate is strongly associated with cell-conditioned `d` variance. **UNMEASURED:**
whether that generalises to an admissible candidate or to a corrected 24-cell
fixture.

---

## 5. Q2 — constant-`\|z\|` evasion

### 5.1 The frozen test does contain the evasion

**MEASURED BY SOURCE INSPECTION.** `e14_b6_rollup_test.py:11-14` defines
`cell(..., z=9.0, ...)`; `full()` never overrides `z`. Its first assertion is
therefore a fully powered, all-pass, constant-`\|z\|` set and requires
`b6_rollup` to pass it. The brief's observation is correct.

**ARGUED.** M55's spec rule 15 is the report's freeze/comparability rule:
preserve a script or result-producing primitive after it has generated
committed evidence and extend or supersede rather than rewriting the evidence.
It is not root `AGENTS.md` rule 15, which governs terminology. M55 did not
publish a separately numbered list of "spec rules"; the phrase refers to that
repeated freeze convention. The namespace must therefore stay qualified.

### 5.2 Extension, not modification

**BUILT.** `spec_v1.b6_acceptance(cells)` is now the normative entry point. It
calls the frozen `b6_rollup` and, when at least three cells are powered and
`n_distinct_z <= 1`, returns:

```text
verdict=CANNOT-ACCEPT
blocked=powered |z| is constant across cells; the lowest-|z| stratum is undefined and B6 cannot ACCEPT
```

It does not raise: `CANNOT-ACCEPT` preserves M55's three-verdict taxonomy and
correctly describes an instrument that cannot apply its own stratum. It does
not change a threshold or consult a candidate score.

**MEASURED.** Actual output:

```text
old constant=ACCEPT  primitive constant=ACCEPT  normative constant=CANNOT-ACCEPT
normative varied=ACCEPT  normative planted=REJECT
  PASS registered constant fixture passed
  PASS frozen primitive still passes it
  PASS normative wrapper blocks it
  PASS distinct-z fixture remains passable
  PASS ordinary B6 failure still rejects
  PASS b6_rollup source unchanged
  PASS b6_rollup bytecode unchanged
  -> 7/7 assertions hold
```

**MEASURED.** Existing tests:

```text
python experiments\M55-acceptance-spec\src\e14_b6_rollup_test.py
   PASS  complete, all pass -> PASS
   PASS  planted: pooled 91.7% >= 90%, subject 'wrapped-text' 75% -> must KILL
   PASS  24 cells from one stack -> KILL
   PASS  cells that do not declare stack -> KILL
   PASS  one stack with only 3 ROIs -> KILL
   PASS  one wrong-sign cell -> KILL
   PASS  6 stack-slots but only 2 subjects -> KILL
   -> 7/7 property assertions hold

python experiments\M55-acceptance-spec\src\e16_pr35_nopower_test.py
   PASS  OBS2: no configuration is newly ACCEPTed (strictly tightening)
   PASS  OBS2: the amendment is not inert -- it blocks at least one case the old code accepted
   PASS  OBS3: the planted answer PASSES the old code (the test has power)
   PASS  OBS3: the planted answer is CANNOT-ACCEPT under the new code
   PASS  OBS3: CANNOT-ACCEPT is not REJECT and not ACCEPT
   PASS  OBS4: the stratum plant PASSES the old code (the test has power)
   PASS  OBS4: the stratum plant is REJECTed by the new code
   PASS  OBS4 control: the same single failure in the HIGHEST stratum -> ACCEPT, so the stratum gate is about WHERE the failure is, not how many there are
   PASS  a cell that does not declare z_pass blocks (B9 was not run)
   PASS  a complete, powered, all-passing set is still ACCEPTed (the battery is passable)
   PASS  the verdict and the kill string do not depend on the order the cells are supplied in (20 shuffles)
   PASS  the pooled 90% gate is never the binding constraint at these subject sizes -- the per-subject clause is strictly stronger
   PASS  with every |z| identical the stratum is DEGENERATE and is skipped, not silently applied to an arbitrary third
   -> 13/13 property assertions hold
```

**ARGUED.** Option (a) wins. Directly rejecting inside `b6_rollup` would alter
the frozen assertion. Option (b), a separate driver-only check, would leave
library callers exposed. The wrapper gives the existing primitive a
reproducibility role and gives certification a hard, machine-enforced path.
Option (c) remains weaker because it relies on a reviewer reading a field.

---

## 6. Q3 — pooled-clause enumeration

### 6.1 Independent method

**MEASURED.** `e19_m76_pooled_enumeration.py` imports neither `spec_v1` nor
M55's enumeration. It enumerates failure-count triples over subject sizes
4, 8, and 12 and weights each triple by its binomial multiplicity.

```text
  PASS all placements sum to 2^24
  PASS k=1 total is C(24,1)
  PASS k=2 total is C(24,2)
  PASS k=3 total is C(24,3)
  PASS k=1..3 sum is 2324
  PASS pooled-only count is zero at every k
  first k with a pooled-only placement: None
  -> 6/6 assertions hold
```

**MEASURED.** At `k=1`, 12 of 24 placements already fail a subject clause and
none fails pooled. At `k=2`, all 276 fail a subject clause and none fails
pooled. At `k=3`, all 2024 fail both. For every `k=4..24`, every placement that
fails pooled also fails at least one subject clause. The pooled-only count is
zero for every count.

**DERIVED.** Let subject pass rates be `r_g`, sizes `n_g`, and
`N = sum(n_g)`. The pooled rate is `sum(n_g r_g)/N`. If every `r_g >= 0.90`,
their positive-weighted mean is at least 0.90. Therefore pooled failure implies
at least one subject failure for every composition, not merely 4/8/12. The
advertised pooled clause is **dead, full stop**.

---

## 7. Candidate facts

`P1` **MEASURED.** The 24-cell B6 registry contains six invalid cells: its
fourth quad-plane ROI requires row 5892, beyond the 4688-row visible raw image.
B6's required four-ROI-per-stack held-out battery cannot run as specified.

`P2` **MEASURED.** On the 18 valid `sigpow` cells, `s_d` is strongly associated
with `\|z\|`: Spearman `rho=-0.8596`; fixed-stack `beta=-1.3402`, bootstrap 95%
`[-1.5998,-0.9779]`; within-stack permutation `p=0.002400`; five of six stack
slopes are negative.

`P3` **MEASURED, AGAINST THE HEADLINE.** Q1's registered verdict is
**INCONCLUSIVE**, not yes: 18 finite primary cells miss the registered minimum
of 20, and two secondary candidate arms do not reproduce the primary
association. The data support a `sigpow`-specific warning, not a universal one.

`P4` **MEASURED.** The Q1 positive control can express the failure: `\|z\|`
spans 14.98x and `s_d` spans 10460.25x. Its first contrast ladder missed the
registered `\|z\|` span by 2% (`3.92x` against 4x); the widened plant-only
ladder is disclosed.

`P5` **MEASURED.** `e14`'s all-pass fixture is constant `z=9.0` on every cell.
The frozen golden test is itself an instance of the evasion it prevents
`b6_rollup` from rejecting.

`P6` **BUILT AND MEASURED.** The normative `b6_acceptance` wrapper blocks a
powered constant-`\|z\|` set with `CANNOT-ACCEPT` while the frozen primitive
retains its old `ACCEPT`. A distinct-`\|z\|` set accepts and a planted failure
rejects; 7/7 new assertions, 7/7 `e14`, and 13/13 `e16` hold.

`P7` **MEASURED.** The original `b6_rollup` source and bytecode are identical
to M55's `c37010c`. Q2 closes by extension rather than modification, preserving
M55's spec rule 15 evidence.

`P8` **MEASURED.** Independent enumeration reproduces 2324 placements for one
through three failures and zero pooled-only failures, then finds zero
pooled-only failures over all `2^24` placements.

`P9` **DERIVED.** The pooled clause is dead for every subject composition:
the pooled rate is a positive-weighted mean of per-subject rates, so it cannot
fall below 90% while every component is at least 90%.

---

## 8. What this milestone did not measure

1. **UNMEASURED.** Q1 does not cover the missing six cells, because their
   registered coordinates are outside the image. No replacement ROI was chosen
   after seeing results.
2. **UNMEASURED.** Q1 does not establish the relationship for an admissible
   shipping candidate. M55's references are known-bad/probe instruments, and
   M57 produced no candidate that survived.
3. **UNMEASURED.** Q1 adds Gaussian noise to fixed half-merges. It does not
   re-run the whole focus merge under new sensor draws, which would require
   independent repeated captures of the same stack.
4. **UNMEASURED.** The experiment does not separate texture, ISO, subject, and
   common spectral power causally. Fixed-stack regression removes between-stack
   levels but has only three valid ROIs per stack.
5. **UNMEASURED.** No candidate verdict or score was run before versus after
   Q2. That omission is deliberate: the tightening was required to be argued
   independently of candidate performance.
6. **NOT CHANGED.** No threshold, held-out cell, `SYNTHESIS.md`, or existing
   M55 test was edited.

---

## Appendix — evidence and commands

| artifact | purpose |
| --- | --- |
| `src/e17_m76_stratum_variance.py` | Q1 held-out run, bootstrap, within-stack permutation, controls |
| `out/e17_m76_stratum_variance.log/.json` | Q1 output and all 64 `d` replicates / 48 null values per cell |
| `out/e17_m76_stratum_variance_first_run.log` | preserved out-of-bounds first run |
| `src/e18_m76_constant_z_test.py` | Q2 planted evasion, passable control, frozen-source comparison |
| `out/e18_m76_constant_z_test.log` | Q2 7/7 output |
| `src/e19_m76_pooled_enumeration.py` | Q3 independent all-count enumeration |
| `out/e19_m76_pooled_enumeration.log` | Q3 6/6 output |

All Python commands were run with `PYTHONIOENCODING=utf-8`.
