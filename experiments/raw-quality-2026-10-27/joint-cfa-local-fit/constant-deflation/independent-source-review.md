# Constant-deflation source review

2026-10-27. **VERIFIED source structure; execution unverified.** Read the complete adapter, API, independent controller and root runner. No imports of the numerical operator, fits, RAW reads or builds were performed. This supports only the bounded neutral-flat checkpoint after the mechanical report-writing correction below.

Operator SHA`8fad7b79049b2fcb0e649eea62e6b1657a387b32b2c1c9c1a47796c55f3ccf90`; API`0d384f71dae57d756d23aac4039fd8acb51a349113eb346a8bab6e995fced99f`. The frozen parent SHA`536aa09456bd8c11b4f53abcb312c75def379077147fe232b4ad38c151f415ac` is checked before import and after fitting. A/H, observations, noise, focus weights and the64-step CGLS source are inherited unchanged.

## Algebra and numerical interpretation

The three columns are actual weighted B applied to unit R, G and B fields over the complete latent domain, including the apron. One G field covers both physical green phases. Actual support disjointness and cross-Gram zeros are checked; each positive finite column norm and its normalized scalar Gram are retained. Projection and coefficient restoration divide by that measured scalar Gram, rather than presuming perfect unit normalization or using an unchecked inverse. The producing paths are PB and B-transpose P, with projected RHS Pb.

The inherited initial normal is therefore the projected initial normal. Final checks use the same denominator construction, independently evaluate restored physical X, and retain the original objective, full/projected normal and constant-direction residual. Numerical admission additionally requires both restored relative normals at most1e-5 and original objective no greater than the measured constant-only initializer. It can refuse because f32 restoration leaves residual even when projected CGLS passes; the finite restored image and exact refusal remain available. No tolerance or iteration change was found.

The original minimizer set is preserved in exact arithmetic. The zero-start minimum-correction solution need not be the old minimum-full-image-norm member of a rank-deficient set. Both code and API disclose this. Per-iteration histories are labeled correction-z histories; only initial/final physical objectives are evaluated. They are not misrepresented as physical-X histories. No known scene truth enters the fitting API.

Preparation adds three original B calls. Final restoration and checks add four B and four B-transpose calls. The parent integrates correction z once and the adapter integrates restored X once; only the latter is the delivered result. These additional costs are disclosed and included in wall time, though outside the inherited projected-call timing lists.

## Independent controls and runner

The controller checks literal B(C), independently evaluated projection, Gram support, symmetry/idempotence/annihilation, projected adjoint, restored residual/objective equivalence, and a live one-sided-projection foil. Its frozen-weight DC-offset control is algebraic and performs no second fit; it does not establish equivalence after recomputing shot variance or admission. The real zero-RHS fit checks the zero-denominator/zero-iteration path. Unchanged analytic fixtures and all ten actual product baseline identities, consumed noise bits and source order are reused; image guards are not replaced with convergence.

Source review found one mechanical blocker: the controller initially wrote `projection-mechanics.json` twice through a create-new writer. The author was asked to preserve the preliminary observation under a distinct filename before writing the combined record. This requires no algorithm or acceptance change. Final source hashes and its correction are recorded in the freeze note below.

The runner uses fixed prior fixture/baseline receipts, a fresh output folder, four numerical workers and a120s/480CPU-second/4GiB first checkpoint. Full release additionally requires the actual flat quality guard, mechanical/model adequacy and the prospective cost projection, with an independent300s bound. Numerical and quality outcomes remain distinct. No photograph, parameter sweep or production promotion follows from this source review.

Final freeze: controller`d3ef782c9eafa1b8f0ad1b3a4b3130dc0cdde150523d197abf2ed7c1c85975b5` writes the preliminary algebra receipt as `projection-algebra.json` and the combined mechanics receipt once; runner`d4ede3808c7bdddf6977984218cbfd8600a5a8662e0cdd1eea7f5ed02dd6be5b` checks the exact complete status and14/10 result counts for full execution, retains cost mechanical refusal, and includes model adequacy in the later release decision. No remaining source blocker was found for the first bounded checkpoint. Numerical execution remains root-owned and unverified here.
