# M194e author preregistration

2026-09-07. **Prospective design. No code, generated array or render exists from
this author at registration.** Root must review and commit this and the
independent design before implementation. The companion
[implementation-plan](implementation-plan.md) fixes the equation, scene,
quadrature, work limits, API and emission semantics; it is part of this record.

## Question and possible outcomes

Can the specified two-layer geometric integral be implemented with shared-pupil
visibility, cell integration and the fixed numerical budget, then bound to a
small explicit noiseless CFA fixture? This commissions a mathematical software
model, not real optics. M25's failed optical/occlusion validation stays failed;
M87's propagation/unmixing and M63's depth-inference questions are not rerun.
There is no new merge-quality gate or M194d retuning.

Possible terminal outcomes: `COMMISSIONED_GEOMETRIC_SCOPE`,
`UNCOMMISSIONED_NUMERICS`, or `INSTRUMENT_INVALID`. Missing a fixed budget,
work ceiling or live control preserves the original scene and artifacts and
withholds the dependent CFA package. Passing cannot establish diffraction,
camera calibration, attainable EDOF, real-scene transfer, default promotion,
performance or SOTA. Numerical f64 reference evaluation does not change
production f32 arithmetic or u16 storage.

## Exact controls and their failure inputs

| Control | Fixed positive/null and incorrect input that must fail |
|---|---|
| Same-ray discrete covariance | Direct ray evaluator at a foreground edge, two equally weighted pupil rays, foreground30, background pair(10,20), visibility(1,0): joint25; reverse only background pair to(20,10): joint20. Separate layer expectations give22.5 in both and must be rejected. Use actual scene/ray definitions; arbitrary precomputed outputs alone are not path evidence. A constant background is the covariance-zero companion. |
| Continuous shared-pupil covariance | Foreground half-plane through a declared noncentral point, constant foreground and a background affine along its normal at between-layer focus. The half-disc first moment gives the signed additional term `2*gradient*d_background/(3*pi)` with the visibility side accounted for. The independent reviewer freezes different geometry and values. Separate means remove this term; absolute defocus changes its sign; both must fail. This commissions the continuous quadrature separately from the discrete evaluator. |
| DC, full and absent foreground | Constants0,10000,20000 electrons shared by both layers must remain constant across all registered focus values and mask states. Full foreground ignores an independently changed background; absent foreground ignores an independently changed foreground. At least one partial-visibility textured control must change, so a renderer returning a constant cannot pass the set. |
| Disc-segment coverage | A constant foreground over constant background at point offsets0, .3 and-.4 of the defocus radius along the mask normal must match independently integrated circular segment area. Replacing the pupil by its center or uniform-radius weights must fail at a noncentral offset. The central symmetric half-disc alone has no power against these defects. |
| Layer order | Reverse the layer order in a test-only evaluator: complete background now nearest must obscure foreground entirely and disagree with the registered partial-visibility result. Production API rejects unordered positive depths. Changing array order without declared depth/order binding must not silently change the model. |
| Focus and signed displacement | At each layer's inverse-depth focus its own displacement is zero. At inverse-focus.75, foreground/background displacements are opposite. Replacing them by individual absolute values must fail the affine shared-pupil control. Global reversal of both must be an inert pupil-coordinate substitution; it is not a signed-model positive control. |
| Pupil-zero cell coupling | At K0, integrate the foreground mask/radiance and background jointly inside each cell. A fractional edge and affine background have an exact polygon-area/first-moment oracle. Point-center sampling and multiplying separate cell means must disagree with it. Constant layers/equal radiance supply the no-effect controls. |
| Independent coordinate transform | Re-choose a nonidentity forward similarity and fractional native cell. Its inverse transforms both cell footprint and pupil displacement. Chief-ray-only inverse mapping and a forward/inverse swap must fail; identity must be unchanged. No fitted alignment or full track is inferred. |
| Radial primitive | Constant, affine and cosine terms at beta0, ±1e-8, ±.01, ±.3, ±3 and ±9, over intervals[0,1], [.17,.81] and[.5,.5], agree with independently integrated scalar functions. Sign reversal of beta with corresponding phase and zero interval are inert controls; dropping the radial r Jacobian is live. Absolute primitive tolerance1e-8 electrons at amplitudes up to20000; tighter numerical accounting remains required for complete images. |
| Full numerical commission | All five64×48 intended floating frames, every pixel and fixed8-pixel edge band, compare with independently refined Cartesian integration. Max discrepancy≤.004e and RMS≤.0008e separately for full frame and edge band. Pupil/cell refinement differences≤.001e each; independent self-refinement≤.0005e. No quantization, excluded edge pixels or relative-only error can hide a failure. |
| Underresolved destroyer | Pupil-center-only evaluation at the noncentral segment case and cell-center-only evaluation at the fractional edge must exceed the same numeric budget. A fixed coarse grid shifted relative to the edge is retained as a further diagnostic. Two nested midpoint grids agreeing do not commission the integral. |
| Work and storage | Error/work/depth limit exhaustion returns nonzero with explicit status, preserving partial uncommissioned evidence. Different N retains at most one frame and bounded node batches; instrument actual ndarray lifetimes/bytes. Tile8/16 and reordered frame enumeration are byte-identical after restoring frame indices. Source/focus/mask changes must change powered floats/CFA. No RSS or runtime claim follows. |
| Noiseless CFA | An exact small scalar field and nonunit factors[.75,1,.6] independently check RGGB parity, integer site coordinates, black512, gain.25 and ties-to-even conversion. A shifted CFA phase, incorrect factor, offset or omitted gain must fail. The emitted values must match the bound float arrays; changing a float file after commissioning refuses. Quantization tolerance is separate from integration error. |
| Manifest/refusal | Unknown schema/keys, duplicate JSON keys, nonfinite values, false frame order/dimensions/length/hash, incompatible ray sign/T/pupil law, wrong source/commission binding and negative scale refuse. Original complete manifest and filename-preserving copies are valid companions. Candidate-selected self-hashes cannot replace the externally supplied commission binding. |

The exact independent affine/segment/cell geometry and its analytic values
belong to the independent design and must freeze before implementation. These
choices may differ from the author case; the evaluator must support both within
the declared restricted model, not special-case the intended image.

## Numerical budget, refinement and refusal

The stringent budget is an engineering commissioning requirement. Its physical
truth scope is unchanged even if numerical errors are tiny. Indicator agreement
is neither proof nor permission to omit independent evaluation. The registered
primary integral, separate angle refinement and separate cell refinement all
remain reported; no arm is selected on the basis of a favorable result.

Maximum adaptive depths are angular10 and cell6; maximum point-integral calls
4,000,000 and angular nodes600,000,000 per frame per registered arm. The primary
pupil/cell indicator targets are.00025/.00075 electrons. Refined arms tighten
only the selected stage tolerance by4 and change Gauss orders16/32→32/64 for
angles or4/8→8/16 for cell coordinates. No additional unregistered refinement
is a passing result; a failure may motivate a separately reviewed later design.

**Pre-run arithmetic correction:** the first uncommitted draft's200m angular
ceiling was too small for a conservative nominal cell-refinement count:
`2*(8^2+16^2)*3072*4*(16+32)=377,487,360`. Root approved600m before any code/run.
Fully visible/hidden point domains use one full angular interval; partial
domains have at most4. The higher ceiling covers this conservative nominal
count with bounded headroom, not unlimited adaptation. Numerical pass lines
are unchanged. Each complete five-frame arm additionally stops its own work at
600 process-CPU seconds or1200 wall seconds, checked between bounded batches.

Pupil indicators propagate through nonnegative native-area cell weights.
The cell indicator includes both weighted low/high pupil indicators plus
piecewise absolute quadrature differences (≤.00075e); final reported error
adds the weighted high pupil indicator (≤.00025e). No unweighted accumulation
of point errors or visible-area renormalization. The plan defines the full
piece/interval allocation; all pixels retain their own receipt.

The floating frames are comparison artifacts before CFA quantization. At the
declared gain, .004e=.001rawDN; after any later WB the applicable factor must be
reported rather than assuming the same DN scale. This commission has no
post-WB product output. No budget is imported from M194b's older approximation.

## Execution and artifact order after authorization

1. Implement only within `experiments/m194e-joint-pupil/`, preserving all prior
   code and inputs. Freeze source and exact environment/command receipts.
2. Run the analytic, wrong-model, schema and allocation controls before the
   intended frame commission. Retain all failed attempts with source hashes.
3. Render one f64 scalar frame at a time into explicitly uncommissioned work;
   record full arrays, settings, evaluation/error counts and streaming hashes.
   Complete all five declared focuses without dropping a difficult frame.
4. The independently owned evaluator checks the complete arrays, analytic
   controls, refinements and its re-chosen scene. Author success is not
   independent verification. A successful external commission binds every
   relevant source, numerical contract and float artifact. This is the
   `m194e-float-commission-v1` receipt, not final CFA approval.
5. Only then emit five noiseless u16 CFA files, one at a time, and the new
   `m194e-joint-pupil-v1` manifest marked `float-commissioned-cfa-unverified`.
   Independently check actual quantization/parity and input binding in a
   separate `m194e-cfa-commission-v1` receipt; no circular approval or falsely
   commissioned partial bundle.
6. Root adjudicates the bounded model commission. A production bridge or new
   quality comparison is a separate reviewed scope. No RAW/holdout access,
   ordinary CLI option, noise repeat population, calibration, SYNTHESIS fold,
   scorecard change or Git mutation is part of this author task.

No image-quality conclusion may use these proposed numbers before the commands
run. A numerical failure and a rejected wrong-model control must be reported as
different outcomes; a deliberately wrong model failing is necessary power, not
failure of the commissioned integral.
