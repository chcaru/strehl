# Independent current V3 adapter review

VERIFIED by source inspection and the root-run controls receipt; no reviewer inference, RAW decoding or new numerical job. No blocking mismatch found for the bounded external RGB comparison. This is not a native-RAW reconstruction or a photographic-quality admission.

## Bound sources

| File | SHA256 |
| --- | --- |
| model-adapter.py | 9df9936740f4781c9cc492b29a2fa678723beca71309aa61465a399eb5696416 |
| controls.py | 48f35b8a53e410030a4f265aed252c2765d3ca794d3978a10dbf5741a20a39df |
| input-bridge.py | 306f87d6d5ffd2de997cbe4743b7c8d3c238faffbb18324a4e1785f22be2da0c |
| worker.py, including phase logs | f0515af01f82d9933f80516978d23b9d7239e44949f01f507cada4b9c567c4af |
| run.py | be17f84e6f53ca028f126dbfeff0afd9af71a7026d54255f837c223db32aa705 |
| comparison-protocol.md | 44f841dab6060d48a4b8860e0893d154acc4ec61194dbf80e876500ac6e1d418 |

The inspected MIT upstream is commit `6e1d7211f7634f60245706ebe3b839b320df9d00`. The adapter checks literal source/checkpoint hashes before importing it, uses `torch.load(weights_only=True)` without the upstream compatibility fallback, strictly loads the fixed architecture, and fixes float32/eval, scales 1 and 0.75, K=1, nonadaptive operation and disabled TF32/autocast. Importing `fuse.py` does not invoke its downloader/main. Minor isolated-process hygiene limitation: upstream import inserts its directory into `sys.path`, so the adapter's single final pop does not completely restore the previous path; the remaining directory is the already verified upstream, not an unbound implementation. This does not block this isolated worker.

## Geometry and producing path

DERIVED: ignoring masked wrap leakage, the fixed two attention rounds contain four spatial window blocks and four pooled inter-source blocks. Tracing their one-dimensional dependencies through the quarter-resolution stem gives a maximum 83-native-pixel displacement at scale 1. Scaling that support by 1/0.75, then including resampling and the radius-2 final Gaussian, fits inside the fixed 128-pixel plugin halo. Context origins are multiples of 128: after 0.75 resize they are multiples of 96, preserving quarter-resolution window and pooling phases. The pinned padded photograph is 6912x4608, divisible by 256; no fractional global resize-size mismatch is introduced.

The source implements the actual global right/bottom reflection, rather than independently reflecting interior tile boundaries. It crops probability maps to the true physical image before the unchanged sigma-0.5 smoothing, matching upstream edge semantics. Nevertheless the upstream shifted-window mask is -100, not negative infinity. Therefore strict finite support and bit-exact full/tile identity are not mathematical guarantees; this route needs the declared numerical comparison.

RGB16 input is explicitly reversed to BGR before the upstream uint16 OpenCV grayscale conversion. The final common source probabilities weight all three original RGB channels; no independent channel donor is selected. All 299 sources attend jointly within each bounded context. The bridge uses the held reference-149 geometry and declared OpenCV cubic interpolation, not native Catmull parity. Developed, tone-encoded TIFF samples and pre-merge development remain material workflow differences from native reconstruction.

## Exercised falsifiers and limits

MEASURED by root: [controls receipt](../../../outputs/raw-quality-2026-10-27/stackmff-v3-controls-1/output/receipt.json). The exact command actually run is retained in its `command` array and the [process record](../../../outputs/raw-quality-2026-10-27/stackmff-v3-controls-1/process.json): Python 3.12 with `-B -X faulthandler`, this lane's `controls.py`, `--upstream` pointing to `stackmff-v3-upstream-2`, and `--out` to `stackmff-v3-controls-1/output`, all as absolute paths. Exit 0, 3.687 seconds whole job, 2,938,761,216 bytes peak job commit. All mechanical checks passed. Official small-path probabilities and RGB16 output matched exactly. Center/outer-edge tile probability maximum differences were 2.265e-6/2.354e-6; normalized RGB maximum was 1.192e-7 for each, within the predeclared 1e-4 maximum/1e-5 RMS bounds. The zero-halo foil failed with probability maximum 0.20445 and RGB maximum 0.005962. Wrong source mapping and wrong coordinate/channel controls also rejected; source order, source hull, constant299 and identical-source checks passed.

Generated image guards passed, including flat-first and separate near/far/color/glint regions. They are selection stresses, not a physical defocus/occlusion model; the color-region RMSE does not independently establish preservation of its weak 80-code green component. The two-source context test and 299-source constant test do not prove full-photograph quality or full-size attention cost.

The runner uses fresh outputs, bound source/dependency receipts and terminal job checks. Worker input hashes bracket execution, the original ICC is retained, and PyTorch's allocator is capped at 24 GiB; this is not a bound on every CUDA allocation outside that allocator. Cost projection explicitly excludes startup, hashing, model loading and full export. A complete 299-source photograph and matched display review remain required before any photographic conclusion.
