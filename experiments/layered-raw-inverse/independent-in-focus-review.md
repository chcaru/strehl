# Independent fixed in-focus consumer review

SOURCE REVIEW ONLY; no numerical execution by this reviewer. No material blocker in the frozen consumer, independent controls/plans, or root wrapper. This authorizes the specified commissioning and saved-output comparison, not a quality verdict.

The output question is explicitly different from the rejected pinhole reconstructions. The consumer calls frozen `model._blur` once on each full96x96 composed pinhole, latent truth and latent far-only comparator. It uses the supplied f32 sigma0.7, radius3, normalized seven coefficients and CUDA f32 convolution with TF32 disabled. Saved composition is consumed directly; sheets are not separately filtered. Observed mean/donor NPY files are copied byte-for-byte with zero extra PSF applications. Their old source choices remain frozen, and the donor is not described as optimal for this new target.

The controls independently construct the coefficients and use SciPy y-then-x zero-padded convolution, reversing the model's x-then-y order. They compare whole outputs, constants, an impulse, signed fields and input immutability. The final controls also compare the frozen generator's nearest-padded PSF on full96 truth, both templates and both separately filtered absent backgrounds, restricted afterward to the original16:80 support. The boundary conventions cannot reach that support with radius3. The fixed arithmetic tolerance is separate from quality guards. The additional one-layer witness is correctly focused: saved focus_coordinates[0] and inverse_depths[1] both equal0; `single_depth` samples the supplied near image at zero pupil shift before the same optical PSF.

Choice checks are fail-capable. A source impulse outside the scored crop exposes cropped filtering; alternating coverage exposes filtering sheets before composition. Each genuine component is independently halved in each colour and tested with the actual capped0.98 component predicate. The double-PSF destroyer must violate that predicate for both components against the ideal once-PSF target. This is an instrument commission, not a candidate comparison against ideal recovery: actual arms instead use filtered visibility1. Failure records an inadequate detail instrument and the wrapper stops before delivery. Wrong colour also has a live component rejection. No sigma, threshold, ROI or donor search is present.

Actual scoring retains all four inverse arms, flat first, absolute observed-baseline bars, strict paired core/ridge RGB **and chroma**, and per-colour component protection. The templates and absent backgrounds are filtered separately with full context; observed-donor projections are recomputed in that target domain. Projection overshoot receives no extra credit. This narrows the tested frequency content; it does not establish why the earlier fine colour error arose. Held-out predictions, stationarity status, original pinhole verdicts and physical inadequacy remain distinct and visible. There is no photographic admission.

The root wrapper's CLI matches both scripts. It verifies the matrix frozen-source chain, binds all four latent outputs/receipts/old scores plus truth/far-only/observed artifacts and new sources, requires commissioning `passed` before delivery, and checks source hashes after each separately capped60-second stage. The scorer verifies all16 output mappings, shapes, actual kernel bytes, single/zero application semantics and immutable source/output files. Existing legacy score schemas contain the retained fields it reads.

Frozen SHA256 bindings:

- Consumer: `3e75c94dbf0c2f4665f25161751ec28c6ef162ebdd06c5f4f4681b4a1f0fc013`.
- Consumer plan: `8825ed6e9898787531c5a2e868dc4a6f99e0e9f2f5fff591ba07bb96e3cae7ad`.
- Controls: `bc6d59d5a2bcc94fe3a12359a13d671957e5eda0347325217d3619b701401524`.
- Independent plan: `b6a91b5a13279ba9e9e6f6da966b210bd5f28acd1ee661811f52b2e4b936a956`.
- Wrapper: `2c2e16eb72fff8bd32d9fd40cdd60a6deeff7c2490a2239df061e8fc7f673060`.

## Serialization repair before in-focus-2

SOURCE REVIEW ONLY. Compared the controls with preserved revision `6f24e3c2`: the sole executable change wraps the already computed result in the frozen `control.jsonable` helper immediately before `control.save`. That recursive helper converts NumPy scalars with `.item()` and arrays/tensors to ordinary JSON-compatible values; it does not rerun or alter comparisons, filters, thresholds or image arithmetic. The repaired controls SHA256 is `8aa5850574c9882aa6bb252bb21299a1e3625e45240850cd519a3e0649559891`.

No blocker to rerunning the same recipe into the separate `in-focus-2` directory. The failed `in-focus-1` serialization attempt and its incomplete JSON remain failed artifacts; this source review does not treat them as a completed commissioning result. No execution by this reviewer.
