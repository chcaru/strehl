# M164 — what a qualified `GX` result can claim

Status: **SCOPED M1 CLAIM COMPATIBLE WITH SOTA; NOT THE COMPLETE SOTA VERDICT;
COMPARATOR BLOCKERS UNCHANGED**

## 0. Ruling

**SCOPED CLAIM IS SOTA-compatible as the detail clause.** It is not by itself
the program's full SOTA verdict.

**INFERRED BY READING.** The governing definition in
`docs/proposals/2026-08-sota-path.md` section 1 is:

> **SOTA = a pre-registered scorecard, versus named comparators, on axes with
> commissioned instruments.**

The scorecard then makes the publication decision conjunctive over seven
gates: `M1`, `M2`, `M3`, `M8`, `M9`, `M10` and `M11`. A qualified `GX`
instrument can supply the missing M1 meaning without claiming absolute object
truth. It cannot make the other six publication gates pass.

The plan should therefore change its unqualified detail wording, not abandon
the SOTA goal. If “resolves detail” is intended to mean absolute recovery of
unknown object radiance `X`, the achievable result is below that stronger
goal. The plan's written definition does not require that stronger claim.

## 1. The paper's detail sentence

Use this sentence only after every named comparator arm and every M1 gate has
passed:

> **On the preregistered macro-subject population and licensed
> frequency-orientation cells for which the independent reference arm passed
> REFERENCE_INFORMATION_DOMINANCE, Strehl resolved more scene-linked detail,
> measured as greater recoverable covariance information about GX—the scene
> structure transmitted through the measured non-null passband common to the
> registered Sony FE 100mm F2.8 Macro GM OSS optical paths—than licensed Zerene
> Stacker PMax, licensed Zerene Stacker DMap, and the commit-pinned
> best-known-source fork and, when obtainable under the preregistration,
> licensed Helicon Focus methods A/B/C on identical inputs, without worse
> reference-relative attenuation, overshoot, phase error, or unexplained
> repeatable structure; this is a comparative claim about that camera, optic,
> reference path and licensed band, not a claim to recover absolute object
> detail removed by or artifacts shared through G, and not a claim about other
> optical configurations.**

Here `G` is the effective pre-sensor transfer shared by the reference and
scored optical paths after the registered field, focus, aperture, wavelength
and geometry restrictions. “Non-null passband” means exactly the cells that
clear the frozen reference-support, conditioning and
REFERENCE_INFORMATION_DOMINANCE gates.

The reader must not infer:

- recovery of frequencies annihilated or unresolved by `G`;
- correctness of structure produced identically by a shared lens ghost, flare
  or aberration;
- absolute object-space MTF or absolute object radiance;
- performance at another lens, converter state, aperture, field point,
  magnification, target population or frequency band; or
- that every possible sharpening or hallucination family has been excluded.

## 2. Does this satisfy the plan's SOTA definition?

**Yes, conditionally.** The sentence satisfies the *form* of the plan's detail
requirement because it:

1. is evaluated by a preregistered scorecard;
2. names the required shipping and source comparator modes;
3. uses a commissioned M1 instrument;
4. states the population and passband; and
5. says exactly what its external reference identifies.

The plan does not define SOTA as recovery of unknowable absolute `X`. It
defines SOTA procedurally and comparatively. A reference-conditional
measurement can satisfy that definition just as a benchmark-conditional
measurement can, provided the condition is in the headline rather than buried
in limitations.

**No, if presented alone.** The scorecard says SOTA is not “wins most axes.”
The detail sentence is only M1. The complete product claim still requires all
seven publication gates and all mandatory disclosures. Until those pass, the
paper may call the M1 result a state-of-the-art detail result on the registered
task, but it may not call the whole stacker state of the art under this plan.

The plan's current end-state phrase, “resolves detail at or beyond the best
shipping comparator,” is safe only if immediately qualified by the `GX`
sentence above. Without that qualification, a hostile reader can reasonably
read it as absolute object resolution, which the experiment does not identify.

## 3. What `GX` loses

`GX` cannot answer several questions a careful reader may reasonably ask:

1. **Was object detail outside the shared passband present?** A common optical
   zero maps different objects to the same observations.
2. **Did both paths reproduce the same lens artifact rather than the object?**
   Shared flare, ghosting and aberration can enter `GX` as if they were truth.
3. **What is the absolute object-space transfer?** Without known input,
   individual `|H_R|` and `|H_S|` retain the scale gauge proved in
   `M164-reference-dominance.md`.
4. **Did the renderer recover valid super-resolution beyond the reference
   support?** The reference cannot certify information it did not carry.
5. **Does the result generalize to another optical configuration or subject
   class?** Nothing in the pair licenses that extrapolation.
6. **Is every visible high-frequency feature genuine?** The claim excludes
   registered transfer and common-mode failures; it is not an unrestricted
   semantic-hallucination theorem.

### 3.1 Comparison with published claims

**INFERRED BY READING, source pages retrieved 2026-09-04.**

- Zerene's official page advertises “Highest quality output images” and says
  it “Preserves low contrast detail and avoids ‘stacking mush’ with deep
  stacks.” It supplies no independently calibrated absolute-object reference
  for those statements
  (`https://zerenesystems.com/cms/stacker`).
- Helicon's official help says it produces a “fully focused image by combining
  the sharpest areas” and advertises “theoretically unlimited depth of field.”
  It does not claim or validate recovery of absolute `X`
  (`https://www.heliconsoft.com/focus/help/english/HeliconFocus.html`).
- Araujo, Ponce and Mairal's real-burst paper describes its target as
  **pseudo ground truth computed using commercial software** and reports
  qualitative parity with commercial solutions, not absolute physical truth
  (arXiv `2311.17846`; also summarized in
  `docs/research/B-algorithms-sota.md` section 3.3).
- MFIFB reports a comparative benchmark of 30 algorithms, 105 image pairs and
  20 metrics. It is benchmark truth, not an optical measurement of unknown
  natural-scene `X` (arXiv `2005.01116`).

Some papers use broader words such as “reconstruct all-in-focus images,” and
synthetic benchmarks can know their digital source image exactly. That is not
an absolute physical-object claim on real macro bursts.

**The honest `GX` claim is not weaker than any validated absolute-object claim
made by the named comparators, because none of the named comparators validates
absolute `X`.** It is narrower than their marketing language and stronger in
measurement provenance.

## 4. Third routes to absolute `X`

Absolute `X` is not impossible in principle. It requires information that
fixes the latent scale and transfer rather than another unknown optical image.

### 4.1 Known-input nonperiodic calibration

The cleanest route is a physically characterized nonperiodic target whose
complex coefficients or cell powers are known independently at finer
resolution than every claimed band. With repeated raw observations,

```text
H_hat_P,k =
    sum_j P_bar,jk conj(X_jk)
    -------------------------
          sum_j |X_jk|^2
```

identifies the end-to-end complex transfer for each path. Independent repeats,
featureless controls and the same common-mode charges then identify noise and
residual structure.

The owner's existing calibration slide is useful only if its physical pattern,
contrast and fabrication transfer are independently characterized in every
licensed cell. A nominal grid, USAF chart, or unknown photographic print can
measure selected MTF features but is not a known nonperiodic input for a
natural-detail claim.

**INFERRED BY READING.** M135's existing planning estimates are:

- high-resolution silver-halide photoplot: `$50-150`;
- rigid carrier: `$20-75`; and
- binary chrome-on-glass mask: `$250-800`.

Those are planning ranges, not quotations. Owner effort is procurement and
metrology of the target plus a dedicated development qualification and sealed
measurement session. This report deliberately specifies no capture order,
frame count or magnification.

**Recommendation:** do not request new hardware merely to satisfy the current
plan. Qualified `GX` can satisfy its M1 clause, and no named comparator has an
absolute-`X` result to beat. Ask for the known-input target only if:

1. the owner wants the stronger words “absolute object detail”;
2. the current reference fails dominance in a claim-critical cell; or
3. a reviewer-facing super-resolution claim extends beyond the shared
   objective's certified passband.

For that stronger goal, the chrome-on-glass random-code mask is the defensible
request. The cheaper photoplot is a development screen unless its fabrication
transfer is independently certified.

### 4.2 Independently calibrated transfer

A wavefront/MTF measurement that fixes `H_R` and `H_S` over the entire licensed
band can also break the gauge. An ideal-Airy assumption does not: real
aberration, focus error, converter transfer and field dependence are exactly
the unknowns being tested.

A second optic can provide complementary support where the Sony objective has
a null, but a different lens is not truth by itself. Its transfer still needs
independent calibration. Buying one before the current passband gate fails
would not be justified.

### 4.3 Restricted `K`

If the claim restricts `K` to a preregistered finite-dimensional family, such
as bounded-support LSI filters, then M164's common-transfer machinery can
estimate or veto that family on supported modes. This breaks the ambiguity
only conditionally on the family. It cannot support the unrestricted
sharpening-safe claim because nonlinear, spatially varying and
content-adaptive operators remain outside it.

### 4.4 Validated generative prior

A separately validated signal/noise prior can produce a posterior ranking.
That result is model-conditional rather than impossible, but its claim must
name the prior and its validation population. It is weaker than a known-input
physical calibration for adversarial detail claims.

## 5. Comparator cost of the scoped claim

**INFERRED BY READING.** Section 3.1 of
`docs/proposals/2026-09-sota-scorecard.md` defines blocker `(d)` as unavailable
common-input output from licensed Zerene PMax, licensed Zerene DMap, or the
fresh commit-pinned best-known-source fork.

The literal `(d)` marker appears on exactly seven readiness rows:

```text
M1 M2 M3 M4 M5 M6 M7
```

That count is correct. It is not the whole operational story: M11's class cell
omits `(d)`, but its prose says “required common-input comparator outputs” are
absent and its status is `UNMEASURED_COMPARATOR_QUALIFICATION`. M11 is
therefore an eighth semantic comparator dependency. This reconciles the
governing plan's Amendment 2 count of eight with the seven literal tags in the
scorecard table.

The required comparator set remains:

- licensed Zerene Stacker PMax;
- licensed Zerene Stacker DMap; and
- a fresh commit-pinned and executable-hash-pinned rebuild of the
  best-known-source fork.

Helicon A/B/C is additional when obtainable, not mandatory.

`GX` changes **none** of those dependencies. It can eventually repair M1
blocker `(a)` and qualify comparator modes under the replacement-M1 rule. It
does not produce missing comparator bytes, replace a licence, or permit
product-native results to be spliced into the common-input track.

Therefore:

```text
explicit blocker-(d) axes removed by GX scope: 0 of 7
semantic comparator dependencies removed:      0 of 8
```

This is not an immediate comparator unlock.

### 5.1 Scorecard defect to route, not edit

M11's readiness row is semantically blocked by `(d)` but omits the marker.
For consistency with its own prose and the plan's count of eight, replace its
class cell with:

> **DEFINED; `UNMEASURED_COMPARATOR_QUALIFICATION`; absolute timing
> QUARANTINED; (d)**

No other blocker marker changes because of `GX`.

## 6. Reproducible source audit

The source audit is:

- `experiments/M164-gx-sota-claim/audit.py`;
- `experiments/M164-gx-sota-claim/audit.json`; and
- `experiments/M164-gx-sota-claim/verify.py`.

It reads only the governing plan and scorecard, pins their hashes, extracts the
publication-gate set and section 3.1 rows, and checks the claim's comparator
and scope language.

**VERIFIED BY RUNNING.**

```text
PASS: 12/12 checks; explicit_d=7 (M1,M2,M3,M4,M5,M6,M7); semantic_comparator=M1,M2,M3,M4,M5,M6,M7,M11; gx_removed=0
TOTAL: PASS 9/9 passed; 0 failed; 0 skipped
```

Deleting M7's in-memory `(d)` marker produces the commissioned red result:

```text
FAIL: 8/12 checks; explicit_d=6 (M1,M2,M3,M4,M5,M6); semantic_comparator=M1,M2,M3,M4,M5,M6,M11; gx_removed=0
```

The red run exits `1`; the mutation never touches the scorecard on disk.

## 7. Strategic recommendation

Change the program's detail claim, not its SOTA definition:

1. replace unqualified “resolves detail” with the literal `GX` sentence;
2. keep the seven-axis conjunctive publication rule;
3. do not represent `GX` as absolute object truth;
4. do not buy another optic unless the measured shared-passband gate fails;
   and
5. do not expect this scope correction to remove any comparator acquisition.

The achievable result is worth the program: it is a real, independently
referenced, adversarially commissioned detail comparison against named
shipping tools. Its value comes from saying exactly what was measured, not
from pretending the common objective was absent.
