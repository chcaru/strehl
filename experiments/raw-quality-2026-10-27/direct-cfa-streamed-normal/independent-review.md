# Independent streamed-normal review

2026-10-27. **VERIFIED / source and saved-result review.** Root alone executed
the controls. No RAW read, reconstruction fit, CUDA execution or new numerical
experiment was performed by this reviewer; artifact hashes and recorded
quantities were checked. This checkpoint does not reverse the prior flat/noise
or64-step convergence failures.

## Source contract

Reviewed producer identities:

- Bands: `d837961600d327d8aa3b5438565c357dd01327c1e6f6ffc4dc4b445b021cf1be`.
- Normal: `0b6d8d2110ae62ddc493cd8f1d2540830884ea1257a1ec2d910208461aa3b269`.
- Solver: `e98dbfd8201785ce4f3e068508939d0815c6d3e500085ba0ed875512db8d9c88`.
- Paired measurement: `0adbba770b06305b8bbf26a497b9b1f1ab95332edc28037634362232ebe09023`.

Haar extraction preserves physical R/G1/G2/B offsets, odd carries and the
frozen x-then-y packing/inverse. The injected variance, replicated3x3 admission
and factor order are preserved. Haar variance is still the inherited diagonal
surrogate; correlated coefficients have not become independent observations.
Clipping is an explicit observation omission, including the actual AC admission
neighborhood, with common N counting all original sensels. Invalid metrics are
zero before the common maximum. No clipped inequalities or replacement
radiance are claimed to be used.

The normal uses actual T=B*C and color-disjoint Gram entries, with both green
phases belonging to one color constant. G=B-transpose*T occupies one global
HWC field. Each source's nuisance subtraction precedes its adjoint; it is not
a subtraction of two large accumulated images. Actual A(ones) is measured,
including odd-Haar detail terms. The paired ABI preserves pointer/shape/map
ordering and current Torch context/stream lifetime. It recompiles an appended
translation unit, so old-file preservation alone is not old-PTX equivalence.

Final residuals use the frozen arithmetic `(factor*d)-(factor*H(Ax))`.
The normal CG source retains64 maximum iterations, no restart/preconditioner,
and explicit nonpositive/nonfinite refusal. Intermediate residuals are
recursive; final true full/projected normal and objective checks remain
separate. Source review is not runtime commissioning of this solver: the
mechanical controls deliberately execute no fit or RGB delivery.

## Controls2 verified

The actual command and environment are in
[invocation.json](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-controls-2/invocation.json):
Python3.12 `-B -X faulthandler`, the bound `controls.py --out` entry, four CPU
workers, f32 and TF32/autocast off. The process exits0 in10.938s, with
18.265625s process-tree CPU,2,646,200,320B peak host job commitment and no
remaining/terminated processes. Torch peaks687,616B allocated/2,097,152B
reserved are not whole-device accounting.

The strengthened controls are SHA
`87639a616aa8222b5c363b9e6d27994f2b51b8adfdcac5e462520b11c99c9494`;
plan72be0302 remains unchanged. Forty artifact/dependency references,
797,684B, were freshly rehashed. Completion is
`a74d860b8bae7f4c0349599fae0b4c4c320c060f8005a018fe0106484b3dbeae`;
[scientific receipt](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-controls-2/output/receipt.json)
is `0869d2a258d792c44099109235f87d7a9da898dc93dd5c9fe2463a3ae6bb7622`.
Original u16 arrays and dependencies remain unchanged.

- All six paired comparisons match the separately instantiated frozen A and
  A(ones) exactly. This anchors the combined PTX0851d8c2 to the separately
  compiled frozen f5c6e06f producer on the fixed cases.
- All789 Haar/noise/admission/factor/inverse comparisons pass; largest relative
  error is2.935e-7. This population exercises rectangular odd phases and four
  actual decomposition levels, not an independently measured full-size7-level
  workload.
- Actual CPU projected-normal error is1.863e-10 against a2.471e-7 allowance;
  RHS error9.202e-7 against1.571e-4. Both satisfy the additional signal-
  resolvability requirement. Near-constant error1.488e-7 is below9.268e-6;
  symmetry error1.126e-8 and positive curvature pass. No floor1 masks these
  small normal quantities.
- Original threshold and impulse-derived support masks match exactly.
  Replicated3x3 dependency expansion adds174 omissions. Poisoned admitted
  coefficients, variance, admission, metric and common scale are unchanged;
  normal/RHS comparisons pass. Missing red constant support is refused.
- Actual wrong-phase, missing-projection and unexpanded-mask errors are
  respectively1.05936,1.11695 and0.41048, versus1.571e-4,9.268e-6 and8.706e-5
  allowances. They fail numerically, not merely because a reference is marked
  unresolved.

Controls1 ran the earlier de3eb8c0 source before the final foil classification
was strengthened. Its executed source is recovered byte-exact at
[controls-executed.py](../../../outputs/raw-quality-2026-10-27/direct-cfa-streamed-controls-1/controls-executed.py).
Only three foil Boolean tests changed; actual earlier errors already exceeded
the same bars. Controls2 is the authoritative strengthened commission.

## Complete weighted-normal cost source review

No blocker found in `full-cost.py` checkpoint2cef7e9 and its notes. It binds the
verified all299 union domain and literal source149/0 maps, generates exactly
two complete7032x4688 read-only u16 planes, and checks their hashes before/after.
The loader returns those original arrays; producing code copies to f32 before
black subtraction. A fixed clipped block activates omission. These are
workload signals, not photographs or an optical/noise realization.

External synchronized QPC intervals distinguish constructor work, one complete
weighted normal, and the RHS clone. Constructor includes actual source qmax,
constants/G and projected RHS construction. At full width, measurement calls
split into32 strips of at most149 rows; Haar remains over the entire source.
Expected source preparations are six during construction and two more for
the normal. Counters must be checked after execution, not inferred from a
parseable receipt alone.

The7200-second scenario scales constructor plus64 normal applications by299/2.
It is explicitly a planning scenario: global work is not exactly linear in
source count, and actual data, source I/O/export, solver updates, final audits
and development remain unmeasured. Passing would not admit a fit or quality
claim. A complete weighted cost observation is appropriate; no full-image
feasibility conclusion follows yet from these small mechanical controls.
