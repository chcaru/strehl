# Fixed spatial witness accounting

Root executes `python -X faulthandler experiments/donor-consistency/spatial-witness-analysis.py --witness <receipt-directory> --out <new-directory>`.
Read only the completed immutable witness and its completed full-triplet output;
no RAW, source nomination, fitting, sweep or quality score. Verify witness
artifact hashes and full-output hashes against their receipt, f32 layout,
geometry, finite values and source PAD4 central identity. Preserve the two
frozen384-native windows and all four CFA values in numerical reports.

Keep the previously frozen facet core2624,2906 / fan2602,2945 /
rim2760,2998 and dark core3080,2150 / fan3102,2203 /
structure3240,2070. Add exactly one **post-failure visual-location witness**,
dark tail3080,2212, independently located in the existing native spatial
candidate. This point is selected after seeing the failure; it is not an
independent quality gate and must not justify adjusting a mask. Root's rough
3085,2210 prompted the location review but is not another searched point.

Show complete native384 photographs and actual2D coverage, source AC,
retained baseline AC, donor sum, shared-base minus donor-base and hull fields.
Do not reduce the interpretation to the original fan point, whose mask1 may
not cover the visible residual. Keep axes in original output-native coordinates
and mark the post-failure point distinctly. Scalar field views use nearest
display of the actual192-quad array; photographed source views crop the
392-native held-development TIFF at[4,4,384,384], with no interpolation or
retone. Signed fields use two fixed display spans, +/-64 and +/-512 source DN;
colormap clipping is explicitly display-only. Report all source25/28/33/69
values numerically, including the different-depth structure control.

Check source=AC+base; baseline_pre=baseline_AC+baseline_base;
candidate_pre=retained_AC+donor_sum+baseline_base;
post=pre+hull and post=clamp(pre,lo,hi), with0.02DN separate-collapse tolerance.
Also compare actual donor sum with region-ordered source AC and masks, respecting
native source arrival25/28/33 (regions2/0/1) and late69 region order0/1/2.
Require matching common fields across candidate/late and dimensionless masks
identical across CFA planes. These are accounting checks, not source ownership.

At every point retain the actual containing quad, coverage/mask centre and
3x3-quad ranges/means, plus signed means for all source/finish fields and the
shared-base mismatch for each source. Three-by-three means reduce single-site
presentation noise but may cross a mask transition; report that transition
instead of evaluating a scalar weight at the centre and applying it to the
whole patch. No brightness conservation, clipping or photon-noise inference
is licensed by developed RGB. White display pixels are not sensor clipping.

Potential decisive observations are: the actual gathered donor already carries
the tail; the tail occupies low mask coverage; a nonzero shared-base offset
reintroduces it; or original-hull correction changes it. These possibilities
can coexist. If the consumed donor photograph disagrees with the previously
centre-mapped source, CA/resampling/second MHC remain explicit confounds. The
signed accounting does not identify an optical cause or validate an automatic
source selector. Root separately proves complete off/on output neutrality.
