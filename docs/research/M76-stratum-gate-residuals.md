# M76 — three residuals in the stratum gate

**Milestone:** M76. **Status:** PRE-REGISTERED; measurement not yet run.
**Pre-registration commit:** recorded in §2 after the path-scoped registration
commit exists and before any deciding command is run.

---

## 1. Headline

**ARGUED, BEFORE MEASUREMENT.** This milestone asks whether the lowest-`\|z\|`
stratum is partly a cell-noise gate, whether constant `\|z\|` can be made
non-admissible without changing M55's frozen results, and whether B6's pooled
90% clause can ever bind. No outcome is claimed here. The registered result
branches include association, bounded null, inconclusive measurement, and
refutation of the proposed code remedy.

**MEASURED BY SOURCE INSPECTION, BEFORE THE CODE CHANGE.** The observation in
the commissioning brief is correct: `e14_b6_rollup_test.py` constructs every
cell with `z=9.0`, and its first assertion requires the complete constant-`z`
fixture to pass. That fixture is an instance of the evasion under test.

**ARGUED, BEFORE THE CODE CHANGE.** M55's spec rule 15 is the freeze/comparability
rule used in the report to leave a measuring script unmodified after it has
produced committed evidence and to supersede or import it instead. This is not
root `AGENTS.md` rule 15, which governs terminology. This report will always
write **M55's spec rule 15** when referring to the freeze.

---

## 2. Pre-registration

### 2.1 Registration identity and prohibition

**REGISTERED.** The registration commit is **`PENDING-FIRST-COMMIT`**. A second,
report-only commit will replace that token with the first commit's SHA. Both
commits will precede every Q1 measurement, Q2 code change, and Q3 enumeration.
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

**PENDING MEASUREMENT.**

---

## 5. Q2 — constant-`\|z\|` evasion

**PENDING CODE CHANGE AND TESTS.**

---

## 6. Q3 — pooled-clause enumeration

**PENDING ENUMERATION.**

---

## 7. Candidate facts

**PENDING.** Report-local facts will be numbered `P1`, `P2`, and so on after
the registered work runs. Facts that damage the headline will be included.

---

## 8. What this milestone did not measure

**REGISTERED LIMITATION.** Nothing is claimed yet. The final report will
distinguish measurements not made from measurements that proved inconclusive.
