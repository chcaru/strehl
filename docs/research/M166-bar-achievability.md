# M166 — scorecard-bar achievability audit

## Question and scope

This audit asks whether an admissible implementation can satisfy each owner gate as
written. It does **not** ask whether the current strehl build passes, whether evidence
exists, or whether a missing capture can be acquired.

The governing working copy was
`docs/proposals/2026-09-sota-scorecard.md`, status
`SPEC / PRE-REGISTRATION v1.7 (2026-09-03)`, SHA-256
`2D919CF22786FFCE371A8CF9952383A543F2EA495AF0492DB06A34FF72AB10FC`.
The audit locates requirements by heading and quoted anchor rather than by line
number because that file was being amended concurrently.

The scorecard's heading `## 3. Scorecard at a glance` defines M1, M2, M3, M8, M9,
M10 and M11 as owner gates. Section `## 0.2 Joint anti-cheat constraints` additionally
retains only M4's same-output median `Q_flat<=1.00` and M12's common-merge
1/2/4/8/16-worker byte identity. The rest of M4–M7 and M12 is mandatory disclosure,
not an independent owner gate. M11's product-native timing bars are also a separately
reported product result and do not determine publication.

No capture, render, bulk decode, or timing run was performed for this audit.
The orchestrator's independently verified M8-O `bilinear_aggregate` counts are
accepted as supplied below; this lane did not recompute them.

## Verdict rule

- **ACHIEVABLE** means this report gives a construction whose accepted set is
  nonempty.
- **IMPOSSIBLE** means a required admissible case forces failure for every possible
  implementation.
- **UNDETERMINED** means the scorecard text does not determine one executable
  predicate, or the available text cannot establish either construction.

A collection of numerically compatible inequalities is not enough to earn
`ACHIEVABLE` when the scorecard leaves the population, reduction, truth predicate, or
comparison representation open. Such a bar is reported as `UNDETERMINED` and also
listed as a well-definedness failure.

## Deterministic-representation and degraded-pass check

The M8-O failure suggests two distinct failure modes: a checker can reject every
clean implementation because it omits a mandatory deterministic transform, or it can
reward a degraded implementation because it does not measure the claimed construct.
The following pass was therefore applied separately from numerical feasibility:

| Axis/component | Deterministic representation check | Degraded-output check |
|---|---|---|
| M1 | No active measured value exists, so there is no representation path to audit. | The withdrawn candidates rewarded sharpening or tone changes; this is why they are not bars. |
| M2 | Final-u16 quantisation creates no exact-zero contradiction because both limits have finite margin. | **Broken in the opposite direction:** the specified residual improves to `0.571215x` under blur, so the card correctly declares the instrument void. |
| M3 | The quantities are normalized residuals with nonzero tolerances; a source-coherent construction survives final serialization. | The former whole-band veil mean rewarded a one-sided defect; the current side maximum removes that demonstrated invariance, but unresolved aggregation prevents declaring the complete bar healthy. |
| Retained M4 | No exact representability conflict was found; a constant serialized image still has zero band numerator. | **Directionally non-specific alone:** blur, denoising, or a constant output can reduce `Q_flat` while destroying detail; the card assigns that opposition to M1, which currently has no bar. |
| M8 | v1.4 omitted the mandatory output-domain transform; v1.5 includes intermediate quantisation, clamps, normalization, and final serialization. | A source selection can pass while being a poor focus stack, but that does not defeat M8's deliberately narrow no-invention claim; other axes carry quality and coverage. |
| M9 | The representation and quantisation of certificate values and intervals are not frozen, so their boundary effect cannot be audited. | Refusal and overclaim are opposed in intent, but the absent truth predicate prevents demonstrating that the implemented checker rejects either degraded strategy. |
| M10 | The depth product's encoding, quantisation, invalid sentinel, and decode-to-physical-units rule are not frozen. | A hard-coded plane can pass the ruler alone; the synthetic target is intended to reject it, but undefined layer-confusion/boundary semantics prevent proving that it does. |
| M11 | Timing has no exact-value representability demand; timer resolution does not create an empty interval around the stated inequalities. | Omitted work and degraded output are intended to fail the end-to-end and quality-qualification rules, but the quality qualifier is currently non-executable. |
| Retained M12 identity | The compared representation is explicitly the highest-precision delivered byte stream. | A deterministically wrong image can pass identity, but identity licenses only reproducibility and is joined to M11 rather than presented as an image-quality claim. |

Among current gate calculations, M2's specified-but-void residual and retained M4
when viewed alone have a degraded-output pass direction. The withdrawn M1 candidates
and superseded M3 whole-band reduction are historical examples, not current
predicates. M2 is already declared void. Retained M4 is explicitly a joint
anti-cheat component rather than a standalone quality claim, but its intended
opposing M1 gate is presently absent.

## Gate inventory and verdicts

| Axis/component | Verdict | Short basis |
|---|---|---|
| M1 | **UNDETERMINED** | The card expressly has no admitted statistic and no success bar. |
| M2 | **UNDETERMINED** | The numerical region is nonempty, but no licensed replacement instrument, ROI/cross-fit aggregation, or RGB reduction is frozen. |
| M3 | **UNDETERMINED** | An ideal source-coherent boundary is a pass construction, but “paired p99,” percentile aggregation, and the required M1 qualification are unresolved in the governing card. |
| Retained M4 median `Q_flat<=1.00` | **UNDETERMINED** | `noise_floor` is an undefined operand of `Q_flat`; the retained gate therefore has no unique value. |
| M8-R | **ACHIEVABLE** | A convex bilinear or direct-copy gather remains within the discrete support hull at every sample. |
| M8 crop/reference identity | **ACHIEVABLE** | Integer identity placement implemented as a source copy is equal within `tau_R`. |
| Historical M8-O v1.4 | **IMPOSSIBLE** | Required census coordinates have `lo-tolerance>1`, while every normalized-u16 output is at most one. |
| Prospective M8-O v1.5 | **ACHIEVABLE** | Its transformed hull is in the representable domain and nearest-u16 serialization is covered by the exact half-code tolerance. |
| M9 | **UNDETERMINED** | Its numerical tuple has a constructive pass point, but `truth_valid`, deciles, and variance aggregation depend on an unspecified future instrument. |
| M10 | **UNDETERMINED** | An exact truth map is a numerical pass construction, but “valid,” layer confusion, and associated populations/reductions are not defined. |
| M11 common-merge speed | **UNDETERMINED** | The ratio's comparator set is selected through M1/M2 predicates that currently do not exist as executable gates. |
| Retained M12 cross-worker identity | **ACHIEVABLE** | Worker-independent arithmetic and canonical output ordering can make all five outputs byte-identical. |
| M11 product-native tuple (non-gating) | **UNDETERMINED** | The live time origin and replay/state contract conflict or are absent, and the cold owner/reset contract is incomplete. |

## M1 — no admitted bar

The card's unique anchors are `### M1 — WITHDRAWN: no admissible detail instrument`
and `**Success.** There is deliberately no active numeric success bar.` There is no
quantity, population, direction, or threshold to which an implementation can be
compared. Requirements for admitting a future instrument are not themselves a
success predicate.

This is not an impossible numerical target. It is an absent target, so neither a
passing nor a failing implementation can be exhibited from the bar text.

**Verdict: UNDETERMINED (not well defined).**

**What would settle / repair kind (diagnostic only):** admission of one complete M1
statistic, population, aggregation rule, and numeric success predicate would make the
gate decidable.

## M2 — flat/defocused-ground noise

### The inequalities are not contradictory

For an unbiased output mean `O` from 16 independent Gaussian frames and an
independent held-out 16-frame mean `R`, the population residual scale is

```text
sd(O-R) = sigma_1 * sqrt(2/16).
```

The normal-consistent MAD therefore has population `eta=1`, and a finite symmetric
residual construction can be chosen inside `eta<=1.10`. The comparison limb also has
a nonempty numerical region: for example, candidate/comparator residual ratio `0.90`
satisfies it. There is no representation-bound contradiction analogous to M8-O
v1.4.

### The scorecard does not define one verdict

The same metric card states
`Instrument status: INSTRUMENT VOID; current axis verdict UNMEASURED` and says no
M1-independent replacement instrument exists. Even within the retired computation,
`eta` is produced for each ROI, cross-fit direction and colour channel, while
`**Success.**` gives one `eta` and one upper confidence bound without specifying:

- the reduction over ROIs and the two reversed cross-fits;
- the reduction over R/G/B;
- whether the quietest comparator is selected per ROI, per capture, or globally; or
- the licensed featureless/defocused truth and information guard that determines
  comparator eligibility.

Different competent reductions can return different pass/fail outcomes from
identical per-ROI values. The known blur challenge at `0.571215x` independently shows
that the old statistic cannot stand in for the missing licensed instrument.

**Verdict: UNDETERMINED (not well defined), not IMPOSSIBLE.**

**What would settle / repair kind (diagnostic only):** a commissioned replacement
instrument plus frozen ROI, cross-fit, channel, confidence, and comparator-selection
reductions would make M2 decidable.

## M3 — occlusion halo and broad veil

### Constructive numerical pass point

A source-coherent ideal boundary has

```text
h_e = 0
v_e = 0
affected-edge count = 0
edge-width ratio = 1
rho_edge = 1.
```

The comparator limb permits equality, so a zero paired statistic tied with a clean
comparator also passes. The registered 500-site pooled population would give a
zero-event one-sided 95% Wilson upper bound of
`0.005381964629841942`, below `0.02`. M161's input-only census also found 1,233
full-reach eligible edges, so the minimum population is not itself contradictory.

### Missing binding semantics

The governing card separately defines p99 of `h_e` and p99 of `v_e`, then requires
“strehl's paired p99” to be no greater than the best comparator's. It never says
whether that singular quantity is:

- `max(p99(h_e),p99(v_e))`;
- `p99(max(h_e,v_e))`; or
- another paired reduction.

Unlike M7's explicitly named nearest-rank p99, M3 freezes no percentile convention.
The global rule that each capture passes and a pooled confidence bar also passes does
not say which M3 reductions are per-capture versus pooled. Finally, the M3 control
requires the build to pass an independently commissioned M1 gate, but M1 has no
admitted predicate.

`experiments/M161-m3-ratification/m3-checker-definition-v2.json` demonstrates that
these choices can be specified consistently — it chooses nearest-rank
`p99(max(h_e,v_e))` and a pooled Wilson bound — but the audited scorecard does not
bind that file.

**Verdict: UNDETERMINED (not well defined), not IMPOSSIBLE.**

**What would settle / repair kind (diagnostic only):** binding the paired statistic,
quantile/per-capture aggregation, and an executable treatment of the M1 dependency
would make M3 decidable.

## Retained M4 component — median `Q_flat<=1.00`

Full M4 is a mandatory disclosure. The only owner-gating component is the same-output
median `Q_flat<=1.00`, where the metric card defines

```text
Q_flat = RMS(BP_20-60(O)) / max(B99, noise_floor).
```

`noise_floor` has no definition anywhere in the scorecard. Its unit, estimator,
population and zero handling are absent. A constant clean output on a constant input
would have a zero numerator and is a conditional numerical pass construction for any
positive finite denominator, so there is no proof of an empty pass set; nevertheless,
the bar cannot be computed uniquely as written.

**Verdict: UNDETERMINED (not well defined).**

**What would settle / repair kind (diagnostic only):** defining `noise_floor` and the
flat-site/median aggregation completely would make the retained M4 component
decidable.

## M8 — source-hull certificate

### M8-R: ACHIEVABLE

Use direct copy at integer coordinates or a bilinear gather with nonnegative weights
summing to one. Every gathered value is then a convex combination of its discrete
source support and lies in `[lo_k,hi_k]`; `tau_R` only widens that interval.
Therefore every M8-R census item passes.

This is also an observed discriminating construction rather than a vacuous argument:
the scorecard records `0 / 6,131,678,976` M8-R violations for the support-clamped arm,
whereas the shipping Catmull-Rom result was nonzero.

**Verdict: ACHIEVABLE.**

### Crop/reference identity: ACHIEVABLE

For the one-frame integer-identity arm, implement the crop as a direct copy from
source coordinate `(x+x0,y+y0)` to TIFF coordinate `(x,y)`. Equality is exact before
serialization and therefore within `tau_R`.

**Verdict: ACHIEVABLE.**

### Historical M8-O v1.4: IMPOSSIBLE

The v1.4 rule compares normalized-u16 output directly with an unprojected source
hull. At any required census coordinate for which

```text
lo_O - tolerance > 1,
```

every admissible encoded value `e` obeys

```text
O = e / 65535 <= 1 < lo_O - tolerance.
```

The lower-bound test therefore fails regardless of the merge, resampler, clamp, or
choice of `e`. M136's frozen bilinear census contains 977,684 such
`full_rail_below_hull` coordinates. One is sufficient to make the required exact
zero-violation result unattainable on that census.

The supplied, source-verified `bilinear_aggregate` chain is:

```text
denominator                              74,173,536
raw violations                             980,097
full_rail_below_hull                        977,684
projected_hull_violations                     2,413
projected_plus_internal_quant_violations          0
```

The first projection removes the representation-only rail contradiction; modelling
the fixed intermediate quantizer removes the remaining 2,413 bilinear residues.

**Verdict: IMPOSSIBLE.**

This verdict applies to the **v1.4 statement as written**, not to the intended
zero-invention property: the v1.5 clean-bilinear zero below constructively shows that
the intent remains achievable.

### Prospective M8-O v1.5: ACHIEVABLE

The scorecard makes M136 section `## 6. Replacement bar text` normative. For every
valid frame it maps the tolerated support interval through the exact monotone
representation path, including intermediate rounding/clamping and final saturation,
then forms `[L,H]` in `[0,1]`. Choose any represented source value
`y in [L,H]` and serialize it to the nearest u16 code. The decoded code is at most

```text
q = 0.5 / 65535
```

from `y`, so it cannot satisfy `O<L-q` or `O>H+q`. Applying this construction at
every coordinate yields `V=0`; paired with the convex M8-R construction and direct
identity copy, the active M8 conjunction has a nonempty pass set.

The bar remains discriminating: the registered diagnostic has zero bilinear
violations but 31,148 shipping Catmull-Rom violations after the same projected-hull
and deterministic-transform accounting. The clean bilinear zero holds independently
in R, G and B.

**Verdict: ACHIEVABLE.**

The v1.5 high/low unrepresentable-support rail census is a mandatory disclosure, not
another gate.

**Repair kind (diagnostic only):** the v1.4 defect is a mismatch between the audited
source domain and mandatory output representation; v1.5 is the already-registered
representation-domain treatment.

## M9 — certificate calibration

### Constructive numerical pass point

The four inequalities are jointly consistent. For example:

1. Use 500 claimed-valid cells that are all independently truth-valid, plus any
   desired invalid cells that are not claimed.
2. False certifications are `0/500`; with the scorecard's one-sided 95% Wilson rule,
   the upper bound is `0.005381964629841942 < 0.01`.
3. True-band coverage is 100%, above 90%.
4. Construct 1,000 interval trials with exactly 950 held-out references inside their
   nominal intervals, giving 95% coverage.
5. In each of ten populated variance deciles, report the independently measured
   repeat variance, giving empirical/predicted ratio one in every decile.

This proves that the numeric tuple has no internal M8-like contradiction.

### Missing truth and reductions

The card defines `truth_valid` only as “the independently commissioned truth
instrument's condition,” then says no such empirical acuity truth exists. It also
does not freeze:

- the truth predicate or licensed band produced by that future instrument;
- how cells are assigned to `n_eff`/variance deciles across captures, tiles and
  bands;
- the empirical variance estimator and within-decile reduction; or
- the reported interval construction whose coverage is tested.

Those choices can change every denominator and the final verdict.

**Verdict: UNDETERMINED (not well defined), not IMPOSSIBLE.**

**What would settle / repair kind (diagnostic only):** binding an independent truth
predicate and complete cell, decile, variance, and interval-coverage reductions would
make M9 decidable.

## M10 — physical depth product

### Constructive numerical pass point

The scorecard itself requires the exact-truth-map control to pass every bar. Such an
output gives:

```text
valid fraction = 1
Spearman rho = 1
median and p95 absolute error = 0
ruler slope error = 0
flat-null p95 range = 0
two-layer confusion = 0.
```

Thus the stated numerical bounds are jointly nonempty.

### Missing predicates

The card does not define:

- what makes a target pixel “valid” rather than merely producer-declared valid;
- the depth product's storage representation, quantisation, invalid sentinel, and
  decode-to-physical-units rule;
- the percentile convention/population for flat-null p95 range;
- the classification rule, exclusion band, and denominator for synthetic
  “layer confusion”; or
- any pass threshold for the separately required boundary-bias report.

The rationale also names uncertainty, but the computation and success tuple contain
no uncertainty quantity or gate. That absence must not be silently converted into a
passing uncertainty claim.

**Verdict: UNDETERMINED (not well defined), not IMPOSSIBLE.**

**What would settle / repair kind (diagnostic only):** executable validity,
percentile, layer-confusion, boundary-bias, and any intended uncertainty semantics
would make the scope and verdict unique.

## M11 and retained M12 identity

### M11 common-merge speed: UNDETERMINED

The timing inequalities have no algebraic contradiction. M161's feasibility audit
also found measured decode and storage rates below, rather than above, the physical
budgets. That establishes absence of a known lower-bound contradiction, not an
admitted passing implementation.

The publication ratio nevertheless has no current denominator. Under M11 exact
computation item 7, the “best comparator” is the fastest mode passing M1, M2, M3 and
M8 plus retained M4. M1 has no bar, M2 has no licensed instrument, M3 has unresolved
aggregation, and retained M4 contains an undefined operand. Consequently no
comparator can currently be classified as qualifying from the scorecard text, and
two implementations cannot compute the registered ratio.

**Verdict: UNDETERMINED (not well defined), not IMPOSSIBLE.**

### Retained M12 cross-worker byte identity: ACHIEVABLE

Partition work independently by output coordinate, use exact integer/fixed-point
accumulators or a fixed canonical reduction tree whose grouping does not depend on
worker count, and serialize in canonical coordinate order. The 1/2/4/8/16-worker
executions then produce identical highest-precision delivered bytes. This construction
does not require serial execution.

The bar is discriminating: the scorecard's `Revision 1.5` records out-of-protocol
evidence that fixed-worker determinism holds while cross-worker scaling invariance
fails.

**Verdict: ACHIEVABLE.**

### Product-native tuple: UNDETERMINED, but not a publication gate

The CPU `<=0.15 s/frame`, hybrid `<=0.06 s/frame`, cold `<=warm+20 s`, live
`<=10 s`, and candidate/default `<=2.00` values must be reported, but the current
scorecard expressly says they cannot satisfy, rescue, or alter M11's publication
verdict.

Their reporting protocol is not unique in any event: the at-a-glance table starts the
live interval “after last shutter,” while the metric card starts it after
`DSC00100.ARW` becomes available; cadence, process initial state, permitted
pre-availability work, file-availability semantics, and initial cache state are not
frozen. “Equivalent machine-wide cache reset” has no acceptance rule, and the cold
bar does not identify whether CPU, hybrid, or both settings own it.

**Verdict: UNDETERMINED (not well defined); non-gating product report only.**

**What would settle / repair kind (diagnostic only):** executable comparator
qualification for the common arm and a single bound time origin, replay/state, and
cold-reset contract for the separately reported product arm would remove M11's
definition gaps.

## Mandatory disclosures that are not additional owner gates

Per `## 3. Scorecard at a glance` and `## 0.2 Joint anti-cheat constraints`:

- M4's failed-site, ghost-ratio, and comparator values are disclosures; only median
  `Q_flat` crosses into the owner gate.
- Full M5, M6 and M7 are disclosures, including M7's boundary-seam component.
- Full M12 memory, fixed-worker determinism, N-scaling and N-mod-4 values are
  disclosures; only cross-worker byte identity crosses into M11.
- M8 v1.5 rail/headroom counts are disclosures.
- M10 boundary bias is required to be reported but has no success threshold.
- M11 product-native values are separately reported product bars, not publication
  gates.

No tri-state gate verdict is assigned to these disclosure-only components.

## Well-definedness failures

The following owner-gating predicates are incomplete enough that competent
implementers can compute different verdicts, or no verdict at all:

1. **M1:** no active statistic or bar.
2. **M2:** no licensed instrument; ROI/cross-fit/RGB/comparator reductions are
   unfrozen.
3. **M3:** singular paired-p99 referent and percentile/per-capture aggregation are
   unfrozen; its mandatory M1 predicate is absent.
4. **Retained M4:** `noise_floor` is undefined.
5. **M9:** independent truth, certificate representation, and
   decile/variance/interval reductions are unfrozen.
6. **M10:** depth encoding, validity, flat-p95 and layer-confusion semantics are
   incomplete; boundary bias has no threshold and uncertainty has no scored
   component.
7. **M11:** quality-qualified comparator selection depends on the undefined gates
   above; the non-gating live/cold report also lacks one operational contract.

M8-R, M8 identity, historical M8-O v1.4, prospective M8-O v1.5, and retained M12
cross-worker identity are sufficiently specified to receive non-`UNDETERMINED`
verdicts.

## Healthy discriminating bars

- **M8-R:** convex/clamped gathering reaches zero while the shipping Catmull-Rom
  diagnostic is nonzero.
- **M8-O v1.5:** bilinear reaches `0 / 74,173,536`, independently zero in R, G and B,
  while the shipping Catmull-Rom diagnostic retains 31,148 violations.
- **Retained M12 cross-worker identity:** a worker-independent reduction construction
  passes while the scorecard records current diagnostic evidence of cross-worker
  failure.

Historical M8-O v1.4 is not healthy: its required census contains an empty accepted
set. M1, M2, M3, retained M4, M9, M10 and M11 are not called healthy because their
current text does not define one executable gate, even where their numerical
inequalities are demonstrably consistent.

## Conclusion

The audit finds one impossible historical bar: **M8-O v1.4**. The active prospective
M8-O v1.5 bar, M8-R, the crop/reference identity arm, and retained M12 cross-worker
identity are achievable. Every other owner-gating component is **UNDETERMINED because
its governing predicate is incomplete**, not because the numerical target has been
shown impossible. No current strehl failure or missing measurement was promoted into
an impossibility claim.
