# Independent pre-run review

SOURCE-REVIEWED only; no build, generated execution, RAW decode or photographic result by this reviewer. The fixed controls are independent of the numerical author. Their admission bars are in `independent-plan.md`; a later result must preserve both failed instruments and failed quality gates.

The proposed order addresses a real source-level distinction: current MHC has cross-colour terms before the composed per-channel CA pull. Applying CA to the output RGB cannot in general reverse that earlier mixing. The new source uses original same-colour CFA samples in the source-native gauge, retains native RGGB offsets in the half-resolution lattice coordinates, applies WB before the unchanged MHC stencil, then gathers the common alignment only. The staged-after arm performs the old MHC once, then colour correction and common alignment separately; it does not accidentally apply MHC twice. Both extra stages remain f32 until the old rounded-u16 consumer. Zero CA calls the old GPU run literally.

The explicit generated pull is `C(T(p))`, about the original active centre, rather than `T(C(p))` or a crop-relative centre. The independent fixture inverts C first, then T. Its realistic local intercept is eps times `(5984,560)-(3516,2344)` in native pixels, converted to quad translation. Radial slopes are the shipped values; they are supplied constants in this operator plant and cannot validate those values on real optics. The original profile was fitted on delivered images, so a photographic change under this different operator also cannot retrospectively calibrate it.

The actual BandWorker and its original-CFA gate-floor probe execute within the same scoped mode/pulls. There is a new worker for each arm, so no cached old beta is carried between them. Before stages all CFA colours even for a green-only probe: R/B terms in reconstructed green must participate. Staged-after's green CA is identity and must preserve its guide, probe, variance and final G1/G2 exactly; the controls assert this. New support failures propagate as NaN through MHC/Catmull, become uncovered output and refuse the selected crop. No cropped black fill is scored. No aligned N-source RGB volume or altered merge rule is introduced.

Choice protections: current, before and staged-after see the same noisy original u16 frames. The nearly achromatic chip scene cannot stand in for genuine colour; separate chromatic edges and live fine R/G/B components are mandatory. Added interpolation can suppress chroma and sensor noise while deleting detail, so the screen requires truth error and truth-capped component retention, with half-detail, extra-blur and desaturation destroyers. Staged-after is a useful order/two-stage comparison, not a transfer-matched blur control. No winner is selected from a parameter sweep. Identity and fractional/rotated pulls plus an independently shifted crop phase are retained separately.

Runtime requirements: root runs the operator test first, then the 20-case quality screen using `STREHL_GPU_GATHER=on`, `STREHL_FULLRES_GATHER=1`, `STREHL_DIRECT_PLANES=rounded`, `STREHL_PROBE_GATHER=green`, measured gate floor, no local placement and Malvar. The source-bound runner must provide these flags. Tests are `merge_cmd::ca_before_mhc::independent_controls::independent_operator_controls` and `...::independent_quality_screen`; output is `STREHL_CA_BEFORE_MHC_OUT`. Full-image before/after remains required if the generated screen admits a photographic test; a generated pass is neither a real-image improvement nor a product promotion.

Reviewed checkpoints (SHA256):

- `gpu.rs`: `3f100b6bc281eee0e0632c1630bed419e4e8995312eda087b73773a0011a5623`
- `prepass.wgsl`: `dd9708f1128878eb614c3dc4a9fb59a922bcf436ebb1832d73c53960c311d235`
- `integration.rs`: `5f58a3f34a4c6d8bbcf5fc8028ed32647561ead40d2acb36dabd03190a0baf31`
- `implementation.rs`: `f7b3f120ceabf336674c1a52102d289ff2a7c90756a5de0ac6b5293afaee92ac`
- `plan.md`: `40553517493133f0b8bd15fd46245602444660e097a2dfbd8d0532205c87ff03`
- `independent-controls.rs`: `1ef303461cf31239d7e3abdcd4ca0b1a7ca3910bf0aadee325fe000c5d1e7bad`
- `independent-fixtures.rs`: `aef778e81e991ea6f5865ff4d21af54405f9d9d9843aa6f59b85743ee1c5143a`
- `independent-plan.md`: `929392fdbf25d2e255ac3e9b82507f80ed2a8db6db0d1d2302a5d23512cdaf41`

One requested integration safeguard is separate from the intended arithmetic: an explicit non-rounded direct-call argument must refuse when this candidate is selected, rather than silently falling back to the CPU path. The held rounded route does not enter that branch. Root/author should retain the final integration hash after applying that narrow guard.

Pre-build addendum: the author applied that one-line refusal. Read back and source-reviewed at `experiments/native-gpu-gather/integration.rs` SHA256 `df7a402f114bda6fe15752a0a7f3d1ca818d3089263c3e375529310846cdb944`; intended rounded arithmetic is unchanged. The root runner now supplies the required route flags. No remaining source blocker identified for the fixed screen.
