# Independent complete-chip interpretation

2026-09-25. **VERIFIED numerical refusal, not a photographic failure or improvement.**
The prescribed whole-chip candidate was not admitted. The fixed reconstruction
is closed without changing the norm, 32-iteration cap or 0.02 camera-DN RMS bar.

I independently read `full-1/completion.json`, `output/receipt.json`,
`output/solver-results.json`, `output/observer-placebo.json`, `process.json`,
and `controls-2/historical-comparison.json`. I inspected the output directory
with `Get-ChildItem -Force` and independently hashed both observer TIFFs with
`Get-FileHash -Algorithm SHA256`. No solver, RAW decode or render was repeated.
The executed command is retained in `full-results.md` and the process receipt.

| Plane | Iterations | Recorded RMS bound, camera DN | Prescribed decision |
| --- | --- | --- | --- |
| R | 6 | 0.0128669964 | Admit |
| G1 | 32 | 0.0281794635 | Refuse: iteration cap |
| G2 | 32 | 0.0278118051 | Refuse: iteration cap |
| B | 6 | 0.0099752423 | Admit |

These four decisions agree with the unchanged all-plane admission rule.
Both green planes have very small relative residuals (approximately
1.37e-6), but their absolute image-error bounds still exceed the fixed bar.
Relative residual alone would therefore have licensed a result that the
registered admission refuses. An above-bar bound does **not** establish an
above-bar true error. These are exact-linear bounds numerically commissioned
against the earlier f32 oracle controls, not interval-certified f32 guarantees.
The full coefficient objective decreased for every plane; that is not evidence
of image quality. The earlier generated glint and far-detail harms remain.

The run consumed all 299 sources with reference 149 and crop
`[133,89,3250,2166]`, yielding the current `6500x4332` gauge. It completed
successfully in 202.188 seconds; this is an operational receipt, not a speed
benchmark. Current production RGB16 hash
`fbeeda70e45be91086e5d6400b642054df908a87ae4021815ad493940960298c`
and ICC identity passed the retained validator. The receipt preserves exact
held coefficient/accumulator/input-bound state, actual tone, and source metadata.
The independently recomputed whole-file SHA256 of both observer off/on TIFFs is
`84fbf88efe111f1b36d75fc5df80a8bdfd00cee98c8fb4f2cd804248e36cfefb`.
This supplies the actual observer non-perturbation check.

`candidate_valid` is false and status is `NUMERICAL_REFUSAL`. There is no
`candidate.tiff`, `candidate-cache.json`, or `candidate-planes.f32` in the
output directory. Candidate output/cache hashes are null. Accepted R/B
pre-hull hashes and all four last-iterate diagnostics remain as numerical
records; they are not a partial candidate image. The complete canonical
coefficient cache remains available, but no further solve is authorized here.

The new build reproduced the generated screen byte for byte at SHA256
`63ea41b7eb9be8bc6e8e4450c0649fddff87865773fdd69f76a1844203c59ac0`.
Preservation, general qualification and photographic admission remain false.
There is no complete candidate or native-pair visual verdict, and no production
promotion or transfer claim. Root's `full-results.md` correctly reflects this
distinction.
