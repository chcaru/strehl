# Independent review: tangent-coordinate amendment2

2026-09-07. **DERIVED map/coverage result; VERIFIED source/count-scope audit;
prospective implementation controls remain UNRUN.** Reviewed author proposal
`numerical-amendment-2.md` SHA
`b2cb29b6843a8acb93f1108f99038b03629a2d31e7a00c16a8cc51d0d10f3b37`.
No numerical author source, frozen reference, scene, tolerance or depth changes
were made by this review. The current full campaign remains uncommissioned.

## What the failure does and does not establish

The retained full-run record stops at completed_cells230 in tile8 order,
independently identifying native cell(30,4), frame3/inverse-focus.875. The
frozen independent full-cell reference is15204.412150777305 electrons; primary
and refined independent references differ there by9.82e-11 electrons. This
does not certify a value from the author, which refused before returning one.

The author trace locates an area.002855699588816 leaf at depth6, with two
vertices on the pupil tangency. Its4/8 cell-rule difference3.84878e-6 exceeds
the allocated2.14177e-6, while weighted pupil indicators are approximately
3e-15 and4e-15. That is observed cell-order indicator dominance at tangency.
It is not an independently measured true error of either leaf rule, nor proof
that a looser acceptance bar would be valid.

Two independent local diagnostic attempts are retained. Attempt1 failed its
own incorrectly specified affine null before reading the target: equal affine
fields at different depths still couple through different visible pupil
positions. Attempt2 corrects only that component control to K0; all five
constant/affine/clipping/Fourier checks pass, then the generalized tiny-triangle
reference itself refuses with a quadrature warning. It establishes no leaf
truth. Root explicitly declined expanding this into another general-triangle
reference commission. The already valid whole-cell and complete-image
references remain the decisive consumer measurements.

## Re-derived maps, Jacobians and coverage

Let e(u)=(1-u)a+ub, triangle area A>0 and0≤u,r≤1. For a tangent edge a,b,
p=(1-r)e(u)+rc. The determinant magnitude is2A(1-r): the edge derivative
shrinks by1-r while the transverse derivative spans the triangle. Applying
r=t² and dr/dt=2t yields **4At(1-t²)**. The integral over the unit square is
4A(1/2-1/4)=A.

For a tangent vertex c, p=(1-r)c+re(u). The determinant is2Ar, hence the
same substitution yields **4At³** and integral4A/4=A. Both maps cover the
closed triangle; interiors are one-to-one, while the collapsed boundary has
zero area. Their positive quadrature weights require no renormalization.
Absolute determinant handles clockwise inputs; signed area must not make
negative weights. Permuting vertices while retaining their incidence labels
must not change the represented domain.

For a uniform pupil near tangency, the disappearing cap has leading distance
power3/2. At a tagged edge, normal distance is a constant times r. At a
tagged vertex it is r times an affine positive function of u; both other
vertices must be on the same strict side unless the edge case applies.
Substitution makes this leading distance factor t³. Smooth radiance does not
remove the original fractional endpoint; a constant/affine moment check alone
would miss its numerical effect. This is a principled coordinate change, not
a proof that all remaining wave integrals meet their error indicators.

## Incidence conditions that the implementation must retain

Tags must come from the clipping construction, including represented exact
zeros. Newly created intersections receive the generating line tag plus tags
shared by their parent edge endpoints. A bisection midpoint receives only the
intersection of endpoint tags; union would falsely mark an interior point as
tangent. Tags must travel with vertices through permutations and subdivisions.

Tagging selects quadrature coordinates only. Generated intersections can have
tiny residuals when h is re-evaluated in floating arithmetic; provenance is not
a statement that every algebraically equivalent expression is exactly zero.
Do not project, snap, drop a sliver or enlarge the pupil to enforce a tag.
Even an unhelpful tag must leave the integration domain intact, with the usual
numerical refusal protecting accuracy.

The h0 clipping line separates distinct positive/negative tangencies. Preserve
explicit refusal for dual incidence, three tangent vertices in a nonzero-area
triangle, or coalesced represented ±R lines when R is nonzero. R0 is a focused
mask edge, not two pupil tangencies: retain its original split/rule. Full and
absent foreground cases must remain valid untagged domains. Untagged triangles
must retain the exact old rule and ordering, not merely a numerically close
replacement. A tag-selected change of variable is valid for either sign of
the tangent and for the inverse-similarity native footprint.

## Independently chosen implementation falsifiers

After release, use triangle a=(2.25,-1.5), b=(4.25,-2.25), c=(3.25,0), whose
area is exactly15/8 and centroid(3.25,-1.25). These binary-representable choices
differ from the author's failed leaf and avoid a target-derived area oracle.
All six permutations must preserve attached tags and the following integrals:

- Constant1:15/8. A missing factor2 in either Jacobian fails this immediately.
- Positive affine10000+3x-2y:18772.96875. This tests spatial moments, not only
  normalized weight sum.
- Tagged edge a,b, lambda=the barycentric coordinate of c: integral of
  lambda^(3/2) is **3/7**. The transformed integrand has degree6 in t, so the
  existing4-point Gauss rule can integrate this component exactly in real
  arithmetic. The unchanged linear Duffy rule is the retained destroyer.
- Tagged vertex c, lambda=1 minus that barycentric coordinate: integral of
  lambda^(3/2) is **15/14**, again polynomial after the proposed substitution.

Use1e-10 absolute tolerance for area/cusp components and1e-8 for the affine
integral; these are local analytic controls, not changed full-cell bars.
Require nonnegative weights and nodes inside the original triangle. An
incorrect Jacobian and a tag-blind linear-rule ablation must fail the applicable
powered checks. Preserve any unexpectedly inert destroyer as a control failure;
do not tune its exponent or threshold.

Exercise actual clipping/bisection tag propagation, both tangent signs,
focused/full/absent companions, contradictory-tag refusal and the untagged
old-rule byte control. A direct wrapper may record selected edge/vertex/none
rules without changing their output; prove that observer's null by hash.
For actual renderer accuracy, rerun the unchanged complete31+336 API population
and the original whole-cell failure. This already contains independently chosen
nonidentity transforms and shifted/tilted boundaries. Additionally assert that
both edge and vertex maps are actually exercised by that population or the
failed-cell control; if not, report the unpowered branch rather than claiming
coverage from the parameter name. Do not commission a general tiny-triangle
numerical oracle as a prerequisite to these whole-cell checks.

All fifteen new whole images, full-frame and fixed edge-band errors, primary
versus each refinement, and the original independent self-refinement remain
mandatory at their unchanged thresholds. A passing local substitution control
cannot substitute for any image or authorize CFA.

## Work audit and conclusion

The geometry-only counter executes the proposed tags and mapped node locations,
then counts the existing signed-chief-ray angular ladder without evaluating
radiance. Its result SHA is
`b75db0d7e5a7a25397a3facd42abfba87aa5d4e23b4990b48a36f4fc02a318ec`.
The published maxima55,707,072 /111,414,144 /223,782,048 angular nodes are
nominal, before adaptation. The changed map leaves the triangle and nominal
point counts unchanged; its node locations can change angular interval counts,
so counting those actual proposed locations is necessary. The counter does so.
Its np.linalg.norm and production math.hypot are byte-equal for this fixed
identity-scene normal(1,-.15); this observation does not generalize that equality
to arbitrary normals. Source receipt and changed-method nominal counts must
remain bound to the actual implementation after release.

The substitution itself adds neither a node order nor a frame volume. Tag
storage, temporary arrays, adaptive visits and elapsed time still need actual
bounded-run receipts. No nominal count guarantees the600CPU/1200wall or
32MiB limits. Keep4m point/600m angular ceilings and original adaptive depths.

**The proposal is mathematically sound and has executable falsifiers. No
design blocker remains**, conditional on the stated incidence/refusal rules
and actual unchanged-budget whole-cell/full-image checks. It remains a
geometric numerical-method proposal, with no optical, capture, merge-quality,
performance, default-promotion or SOTA conclusion.
