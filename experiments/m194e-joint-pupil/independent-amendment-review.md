# Independent review of numerical amendment1

**ARGUED acceptance for a prospective numerical-method experiment**, before
its implementation. The original method remains `UNCOMMISSIONED_NUMERICS` as
recorded in [the retained outcome](original-numerics-outcome.md). This review
does not commission the replacement or alter any model/scene/error/resource
bar. The completed Cartesian reference arrays and their source bindings stay
unchanged.

## Crossing equation and signed geometry

Let M be the native-to-canonical linear map, n the canonical foreground normal,
and d_F the signed native foreground displacement. Set

```text
v = d_F * transpose(M) * n
R = norm(v), alpha = arg(v)
h = n dot T(native_point) - mask_offset.
```

At a radial level r the foreground boundary satisfies
`h + r*R*cos(theta-alpha) = 0`. Alpha must include the sign of d_F; using
the unsigned mask normal's angle without carrying that sign separately is a
different crossing equation.

For `0 < eta=abs(h)/R < r`, define `s=sign(h)` and
`delta=asin(eta/r)`. The two angular roots are

```text
alpha + pi/2 + s*delta
alpha + 3*pi/2 - s*delta,
```

wrapped into the existing full-period interval. Negative h places the root on
the side seen in the preserved diagnostic. Positive h reverses the offset
direction. At h=0 the normal-perpendicular cuts suffice; at eta>=r there is no
additional interior radial crossing. R=0 is the focused-foreground case and
must not divide by zero. These statements are derived from the declared model,
not optical validation.

The proposed fixed r=2^-j ladder is a defensible deterministic way to partition
the narrow transition. It depends on geometry, not on which results improved.
It leaves the radial primitive, visibility order and both joint sample
coordinates unchanged.

## Finite ladder and numerical evidence

The32-level cap truncates the choice of subdivision points, **not** the pupil
integral. The complete angular intervals still cover the full pupil, retain
their length-proportional tolerance shares and use the original error/depth
refusal. There is no unreported missing-radius term to call zero. The finite
ladder is not a proof that every scene will now resolve within depth10.

Reuse precisely the same computed chief-ray h in the cuts and radial crossing
evaluation. The old algebraically equivalent native linear expression need not
have identical rounding. Clamping the asin ratio against rounding is distinct
from snapping a nonzero h to zero, which is not authorized. Exact represented
endpoint deduplication is acceptable; nonempty intervals must not disappear
under a proximity tolerance. If midpoint subdivision cannot produce a distinct
floating point while the interval fails its budget, refuse. Absolute-angle
rounding near a normal-projection zero remains a numerical limitation to test;
a passed low/high indicator alone is not a rigorous floating-point enclosure.

The geometry-only count traverses every nominal low/high cell node in all five
frames and three arms. Its point/node totals establish nominal headroom under
the existing ceilings, not runtime or adaptive feasibility. The counter must
use the same chief-ray h arithmetic as the proposed cuts, or qualify its
numbers as counts from the original algebraic expression. Represented endpoint
deduplication may reduce a combinatorial upper count. Adaptation can increase
work and must still refuse at the original limits.

Reviewer correction: an initial message incorrectly said the count script did
not increment its triangle counter. Re-reading the source and saved JSON found
the increment and nonzero6478/6476/6256 counts. That objection is withdrawn;
it was a reviewer misread, not an instrument defect. The h-arithmetic alignment
is a separate, valid provenance point.

## Required interpretation and follow-through

The same first failed cell, complete340-case API population, all author
analytic controls and all five complete frames in each of the three numerical
arms must be rechecked. No successful subset supplies a full-frame RMS or
permission to emit CFA. The existing independent refined arrays are the
comparison reference; unchanged references need not be rerendered.

The amendment includes both extra geometric cuts and consistent h evaluation.
The archived original refusal is a valid limitation control but does not alone
isolate which of those changes matters. A success should be attributed to the
amended method as a whole, unless a separately named same-h/no-ladder ablation
establishes a narrower cause. Such an ablation cannot replace any required
acceptance case or change the model/precision contract.

No scientific blocker remains to implementing this bounded proposal after
root commits it. A new refusal is an admissible negative result. Genuine
external float/model authority remains withheld until the actual replacement
passes every required check, and final CFA validation remains a separate stage.
