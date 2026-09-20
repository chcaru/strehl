# Independent attribution observer controls

Fixed before execution. Root runs; the observer author does not verify it.
One small test uses the existing independently authored89x73 odd-domain,
three-source/four-plane u16 fixture and actual BandMerge. Reuse its required
FrameWorkspace reset. Inject the existing fixed variance; no calibration or
new photographic quality metric is introduced.

The independent test owns `independent-attribution-controls.rs`, included as
a child of the existing controls module. Intended filter:
`merge_cmd::donor_consistency::independent_controls::attribution_controls::`.
Run from the fresh CLI test executable with `--nocapture --test-threads=1`.
Keep all STREHL source/merge overrides at the preceding mechanical-control
baseline. No originals are read. Expected cost is subsecond to seconds, with
the root's existing180s bounded control runner as the ceiling, not a benchmark.

Use two overlapping, spatially varying masks and different focused/late donors.
Independently build each donor Pyramid from original consumed planes. Use
actual resolved baseline coefficients, already cross-checked against ordinary
finish and the independent mean of fresh source bases by the parent controls.
For each band construct zero-filled pyramids holding only that band, then
collapse them with the public production kernel to form an independent oracle
for baseline, retained baseline and each prescribed donor contribution.

Collect observer fields for a whole odd89x73 domain and two interior crops
with different x/y parity. Each crop must equal the corresponding slice of
the whole-domain observer; no decomposition is restarted on a crop. Compare
every returned plane/band against the independent isolated-band oracle.
Signed contributions must be retained; negative values are not clamped away.

Required failures and guards:

- A missing band, replaced terminal base, swapped colour plane, wrong crop
  phase, altered donor or zeroed negative contribution must fail an identity.
  Assert nonzero baseline remainder, candidate and late donor contributions,
  and positive/negative coefficient contributions are actually exercised.
  Require more than10 same-pixel retained/donor pairs with opposed signs and
  cancellation greater than0.003DN; signed terms somewhere in an image alone
  would not exercise cancellation at the observed pixel.
- Sum all baseline AC contributions plus terminal base to actual baseline
  pre-hull reconstruction. Sum all retained AC plus candidate/late donor AC
  plus terminal base to each actual candidate/late pre-hull reconstruction.
  Add the signed hull residual to recover actual post-hull output. Also compare
  post-hull against independently input-bounded original coefficients.
- Require the existing shared-pin/all-ones donor construction to exercise
  actual pre-hull excursions; the observer's hull residual must be nonzero and
  reproduce the exact final clamp. An output-only observer cannot claim this
  path by subtracting two identical arrays.
- Explicitly compare `Expand(m*C)` against the false shortcut
  `Expand(m)*Expand(C)` for a nonconstant mask and a live nonzero AC band.
  Require the two to differ by more than0.003DN somewhere. The observer must
  match the former, not read an expanded mask as an image-pixel source weight.
- Hash all three actual final outputs before and after observing, including
  the different late-donor arm; require exact equality. Preserve original u16
  and consumed f32 arrays. Hash equality is a neutrality check, not a quality
  assessment. Root separately binds full-triplet off/on RGB16 equality.

Exact bits are required for output neutrality, input immutability and cropped
field extraction. Independent f32 coefficient/collapse comparison retains the
preceding0.003DN limit. Sums of separately collapsed fields may accumulate
different rounding from collapse of their sum: permit at most0.02DN absolute
reconstruction error and print the worst value. These tolerances are below one
stored u16 count and are not permitted to change after observing the result.
The final clamp witness and late-arm difference must be live, not merely finite.

No positive fraction or absolute-energy sum of these signed fields is a source
ownership probability. Cancellation, final InputRange limiting, MHC and tone
must remain explicit in the subsequent photographic interpretation. Passing
commissions the observer; it does not prove why a visible ray remains.
