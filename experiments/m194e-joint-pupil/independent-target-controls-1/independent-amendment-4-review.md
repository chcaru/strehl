# Independent review: cell-consumed pupil targets

2026-09-07. Prospective; implementation and trials wait for root's committed
release. Reviewed final author amendment SHA
`2a5b73161a4ec50957fd2a1bc147955000b2fe43182f29d9987f0357de1cba26`,
including the relative-mass revision. This review follows
`independent-coupled-budget-audit.md` and the
independently verified complete full3 diagnostic frontiers. No old failure,
reference array or global accuracy limit is changed.

## Allocation and refinement meaning

The family-wide inner target is a justified response to the observed nested
indicator floor. Write Cmin=.0001875 and T=Cmin/4=.000046875. Primary and
cell-refined use T; angle-refined uses T/4=.00001171875. This preserves the
intended isolated cell refinement: primary/cell-refined have identical pupil
orders and consumed target. My earlier per-arm min(P,C/4) alternative was
budget-compatible but would have coupled the cell arm to tighter angular
integration. The shared-family design is preferable here.

The standalone point/global pupil caps remain separately meaningful. The new
`cell_point_tolerance` field must reach both actual low/high batches through
the new keyword, controlling both interval budgets and final per-point summed
indicator checks. A serialized value alone does not commission this behavior.
The default `render_point` call must retain its original target and exact
value/indicator bits on unchanged inputs. Custom targets exceeding the relevant
standalone cap or C/4 are unsupported at cell consumption, not a request to
silently widen another setting.

## Floating mass reservation

For a native triangle area A, positive low/high weights with relative mass
error at most1e-12 each give weighted pupil indicators at most
T*A*(1+1e-12 mass)*(1+1e-12 point slack), before final finite summation rounding.
The separate geometric partition check permits total area at most1+1e-11.
Thus the two terms over a unit cell have upper reservation

```text
2*T*(1+1e-12)^2*(1+1e-11)
  = approximately (Cmin/2)*(1+1.2e-11)
```

Finite double-precision dot/fsum rounding adds a much smaller allowance under
the bounded positive rules (at most256 weights per batch). It must not be
silently treated as exact arithmetic. The reservation is slightly greater
than Cmin/2, by approximately1.13e-15e before those rounding terms, and remains
far below Cmin. This is a compatibility argument for indicators, not a rigorous
bound on physical or quadrature true error.

Use the actual positive finite quadrature weights and area in
`abs(fsum(weights)/area-1)<=1e-12`; reject zero/nonfinite area, nonpositive or
nonfinite weights, and false mass. Do not renormalize. An absolute1e-11 mass
test would be ineffective for tiny triangles whose whole area is below that
number, so it is not a substitute. Keep the geometric partition's distinct
absolute1e-11 check and original coordinates.

Continue evaluating actual E=D+PL+PH and separate PH against their unchanged
global caps. Do not add a new D<=C/2 admission requirement; unused observed
pupil budget can legitimately serve D. Preserve the existing reported E+PH
indicator, including the second PH term, and all finite/coverage/depth/work
refusals. The old reported standalone cap must not masquerade as the newly
consumed inner target in receipts or source-bound contracts.

## Independently re-chosen controls before execution

The following are fixed before candidate implementation. No point/threshold
sweep, reference rerender or full-layer fast path is included.

1. Use an absent foreground mask with foreground8000, background
   `10000+2700*cos(2*pi*(.11*x+.073*y)+.47)`, depths(1.3,2.5), K13,
   inverse-focus.71 and identity transform. At native point(11.375,7.625),
   compare the actual standalone default and explicit-default path to the
   archived a22d source by scalar and indicator bits. Also use points
   (3.125,9.875), (19.625,2.375), and (6.875,17.125), all positive radiance.
   This is a new smooth analytic caller fixture, not a new photograph.
2. On the first same point, explicit target1e-18 must either consume strictly
   more angular nodes than the default or reach an unchanged numerical refusal.
   This powers actual target consumption independently of metadata. A returned
   value is checked against the uniform-disc sinusoid integral
   `DC+amplitude*cos(phase_at_chief_ray)*2*J1(a)/a`, with
   `a=2*pi*abs(dB)*hypot(fx,fy)`, using the existing .02e analytic API tolerance.
   No unexpectedly inert point is replaced after observing it.
3. Run cell integration at that same re-chosen fractional centre for all three
   arms, tracing actual low/high point-batch keyword values and batch sizes.
   Require the intended T/T/quarter-T relationship on calls, not just config
   equality. A count hook and a same-call placebo must preserve scalar and
   indicator bytes. The trace must witness both low/high batch sizes.
4. Omit the target only on the low batch, then only on the high batch, through
   a test-local wrapper around the real consuming function. The independent
   call-argument checker must reject both even if returned scalars happen to
   be close. Restore the valid wrapper as the companion. Also retain the
   actual old-policy/full3(4,0) refusal; record any same-source old-cap ablation
   disposition without choosing another point to recover a preferred outcome.
5. At actual leaf consumption, corrupt low weights by one negative weight,
   a zero weight, NaN or infinity; separately multiply all low weights by.5
   and all high weights by(1+2^-20). These must refuse. Unmodified rules on the
   same fixed constant/affine domains pass. A tiny positive triangle, the
   previously registered area2^-51 component, must retain a relative mass
   check with the half-mass destroyer, not pass through an absolute tolerance.
6. Negative, zero, NaN, infinite, boolean and too-large explicit/config targets
   must refuse at their applicable boundary, paired with T and default valid
   calls. Use a primary inner target of.0002 as a finite unsupported C/4
   example and a standalone explicit target of.0003 above its.00025 cap.
   Errors from a different boundary do not prove the intended guard.

Direct test hooks remain test-local and restoration is mandatory after every
call; previous observer-wrapper lifecycle failures remain in the record.
The original367 API cases,400 map controls,62 allocation controls and32
observer/traversal controls are then rebound/refreshed to the new source,
with any interface-only adaptation stated. Full-array transport controls and
root/Socrates's metadata checks separately reject stale or rehashed targets.

## Admission and remaining limits

The numerical amendment leaves nominal geometry/node counts unchanged; tighter
inner targets can still require more adaptive angular work and hit the original
ceilings. No performance prediction or extra resource budget is justified.
Standalone and cell APIs may now intentionally have different inner effort;
their target semantics must remain visible.

Only a fresh complete fifteen-array campaign can satisfy the original full
image/edge .004e maximum/.0008e RMS and separate refinement bars. All twelve
successful full3 arrays and all earlier failures remain retained evidence,
not reusable pieces of the new campaign. No CFA authority follows from these
component controls or from a close scalar diagnostic.

**No design blocker remains.** The final relative tolerance also applies to
tiny normal/subnormal rules: underflowed zero area/weights or a failed relative
check explicitly refuses. No renormalization, size exemption or truth waiver
is introduced. This prospective review does not assert that the implementation
or subsequent full campaign will pass. Root's committed release is still
required before implementation and execution.
